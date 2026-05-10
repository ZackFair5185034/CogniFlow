# 无限画布缩放/平移性能优化技术研究报告

## 一、渲染技术对比

### 1.1 Canvas vs SVG vs WebGL

| 维度 | SVG | Canvas 2D | WebGL |
|------|-----|-----------|-------|
| **适用场景** | 编辑器（节点数 <1000） | 数据可视化、图表 | 游戏、3D、大型可视化 |
| **DOM 事件** | 原生支持 | 需手动绑定 | 需射线投射 |
| **内存占用** | 高（每个元素是 DOM） | 低（位图） | 中等 |
| **重绘粒度** | 元素级 | 全量/区域 | 全量/区域 |
| **缩放质量** | 矢量无损 | 位图有锯齿 | 可过滤优化 |
| **实现复杂度** | 低 | 中 | 高 |
| **Node-RED 选用** | ✅ SVG | ❌ | ❌ |

**Node-RED 选择 SVG 的理由**：
- 节点数量通常 <500，不需要 WebGL 性能
- 编辑器需要细粒度事件（拖拽、连接桩）
- 开发成本低，调试方便

### 1.2 工业级画布库对比

| 库 | 渲染 | 虚拟化 | 缩放范围 | 移动端 |
|----|------|--------|---------|--------|
| **Konva** | Canvas | ✅ | 自定义 | ✅ |
| **Fabric.js** | Canvas | ✅ | 自定义 | ✅ |
| **D3.js** | SVG | ❌ | 依赖实现 | ✅ |
| **Leaflet** | Canvas/Image | ✅ | 有限 | ✅ |
| **PixiJS** | WebGL | ✅ | 任意 | ✅ |
| **Excalidraw** | Canvas | ❌ | 0.1x-10x | ✅ |

---

## 二、Node-RED 画布实现分析

### 2.1 固定空间画布

Node-RED 使用**固定 8000×8000 SVG 空间**，通过 CSS scroll 模拟平移：

```javascript
outer = d3.select("#red-ui-workspace-chart")
    .append("svg:svg")
    .attr("width", 8000)    // 固定画布尺寸
    .attr("height", 8000)
    .style("overflow", "scroll");  // CSS 滚动
```

**优点**: 实现简单，浏览器原生滚动
**缺点**: 大画布下 DOM 节点多，内存压力大

### 2.2 缩放实现（手动 scaleFactor）

```javascript
scaleFactor = 1;  // 初始缩放
scaleFactor = Math.min(2, Math.max(0.3, scaleFactor + delta));  // 限制范围

// 缩放时重绘所有节点
function redraw() {
    outer.selectAll(".red-ui-flow-node")
        .attr("transform", d => `translate(${d.x * scaleFactor}, ${d.y * scaleFactor})`);
}
```

### 2.3 dirty flag 优化

Node-RED 不计算 viewport 裁剪，而是用 **dirty flag** 避免不必要重绘：

```javascript
// 节点/连线变更时标记 dirty
node.dirty = true;
node.dirtyGroup = true;

// redraw() 只重绘脏区域（实际是全量重绘，但可优化为区域重绘）
if (node.dirty) {
    // 重绘该节点
}
```

---

## 三、性能优化技术

### 3.1 视口裁剪（Viewport Culling）原理

**核心思想**: 只渲染视口内可见的元素。

```javascript
function getVisibleNodes(viewport, nodes) {
    const { x, y, width, height, scale } = viewport;
    const viewBounds = {
        left: x / scale,
        right: (x + width) / scale,
        top: y / scale,
        bottom: (y + height) / scale
    };
    
    return nodes.filter(node => {
        const nodeBounds = getNodeBounds(node);
        return rectsIntersect(viewBounds, nodeBounds);
    });
}

function rectsIntersect(a, b) {
    return !(a.right < b.left || a.left > b.right || 
             a.bottom < b.top || a.top > b.bottom);
}
```

**性能收益**: 10000 节点场景下，视野内通常 <100 节点，DOM 操作减少 99%。

### 3.2 矩阵变换（缩放/平移数学）

**齐次坐标变换**:
```
[x'] = [scale  0    tx] [x]
[y'] = [0      scale ty] [y]
[1 ] = [0      0     1 ] [1]
```

**缩放变换**:
```javascript
function zoomAtPoint(viewport, newScale, centerScreen) {
    // 1. 将屏幕中心转为画布坐标（缩放前）
    const centerBefore = screenToCanvas(viewport, centerScreen);
    
    // 2. 应用新缩放
    viewport.scale = newScale;
    
    // 3. 将画布坐标转回屏幕坐标（缩放后）
    const centerAfter = screenToCanvas(viewport, centerScreen);
    
    // 4. 调整平移量保持中心点不变
    viewport.x += (centerAfter.x - centerBefore.x) * viewport.scale;
    viewport.y += (centerAfter.y - centerBefore.y) * viewport.scale;
}
```

### 3.3 虚拟化渲染（只渲染可见区域）

**LOD (Level of Detail) 策略**:

| 缩放级别 | 渲染内容 |
|---------|---------|
| > 50% | 完整节点 + 标签 |
| 20%-50% | 简化节点（无标签） |
| < 20% | 占位符方块 |

```javascript
function renderNode(node, scale) {
    if (scale < 0.2) {
        // 占位符
        return `<rect width="100" height="30" fill="#ccc"/>`;
    } else if (scale < 0.5) {
        // 简化
        return `<rect width="100" height="30"/>`;
    } else {
        // 完整
        return `<g class="node">${nodeIcon} ${nodeLabel}</g>`;
    }
}
```

### 3.4 requestAnimationFrame 优化

```javascript
let rafId = null;
let pendingUpdate = false;

function scheduleRedraw() {
    if (!pendingUpdate) {
        pendingUpdate = true;
        rafId = requestAnimationFrame(() => {
            pendingUpdate = false;
            render(viewport);
        });
    }
}

// 触摸/拖拽时调用
chart.on("mousemove", () => scheduleRedraw());
```

### 3.5 Web Workers 在画布渲染中的应用

**Offload 计算密集任务到 Worker**:

```javascript
// main.js
const worker = new Worker("canvas-worker.js");

// 计算视口内可见节点（Worker 中执行）
worker.postMessage({ type: "culling", viewport, nodes });
worker.onmessage = (e) => {
    visibleNodes = e.data.visibleNodes;
    render(visibleNodes);  // 主线程只负责渲染
};

// canvas-worker.js
self.onmessage = (e) => {
    if (e.data.type === "culling") {
        const visible = computeVisibleNodes(e.data.viewport, e.data.nodes);
        self.postMessage({ type: "result", visibleNodes: visible });
    }
};
```

**适合放入 Worker 的任务**:
- 视口裁剪计算
- 连线路径计算（Bezier 曲线）
- 布局算法（dagre, elkjs）
- 搜索/过滤

### 3.6 移动端触摸手势

**Pinch-to-Zoom 实现**:

```javascript
let startTouchDistance = 0;
let startTouchCenter = [0, 0];
let startScale = 1;

element.addEventListener("touchstart", (e) => {
    if (e.touches.length === 2) {
        const [t0, t1] = e.touches;
        startTouchDistance = Math.hypot(t1.pageX - t0.pageX, t1.pageY - t0.pageY);
        startTouchCenter = [(t0.pageX + t1.pageX) / 2, (t0.pageY + t1.pageY) / 2];
        startScale = viewport.scale;
    }
});

element.addEventListener("touchmove", (e) => {
    if (e.touches.length === 2) {
        e.preventDefault();
        const [t0, t1] = e.touches;
        const currentDistance = Math.hypot(t1.pageX - t0.pageX, t1.pageY - t.t0Y);
        const currentCenter = [(t0.pageX + t1.pageX) / 2, (t0.pageY + t1.pageY) / 2];
        
        // 计算缩放比例
        const scale = startScale * (currentDistance / startTouchDistance);
        
        // 以 pinch 中心点缩放
        zoomAtPoint(viewport, scale, currentCenter);
        scheduleRedraw();
    }
}, { passive: false });
```

---

## 四、性能数据参考

### 4.1 不同规模下的渲染性能

| 节点数 | SVG 重绘 | Canvas 重绘 | WebGL 重绘 |
|-------|---------|------------|-----------|
| 100 | <5ms | <2ms | <1ms |
| 500 | <16ms | <5ms | <2ms |
| 1000 | <33ms | <10ms | <3ms |
| 5000 | >100ms | <50ms | <10ms |
| 10000 | >200ms | <100ms | <20ms |

### 4.2 优化后的性能目标

| 指标 | 目标帧率 | 实现 |
|------|---------|------|
| 平移 | 60fps | viewport culling + RAF |
| 缩放 | 30fps | scale 缓存 + RAF |
| 拖拽 | 60fps | 直接 DOM 操作 |
| 连接线 | 60fps | Bezier 路径缓存 |

---

## 五、实现方案推荐

### 5.1 编辑态（节点编辑器）

**推荐: Canvas 2D (Konva.js)**

- 优点: 性能好，支持绑定，API 友好
- 缺点: 失去 SVG 的可访问性
- 适用场景: 节点数 >500

```javascript
const stage = new Konva.Stage({
    container: "canvas-container",
    width: window.innerWidth,
    height: window.innerHeight
});

// 层级结构
const layer = new Konva.Layer();
const nodeLayer = new Konva.Layer();
stage.add(layer, nodeLayer);

// 缩放
stage.scale({ x: scale, y: scale });

// 平移
stage.position({ x: offsetX, y: offsetY });
```

### 5.2 运行态（监控/预览）

**推荐: 虚拟化 Canvas**

- 只渲染视口内元素
- Web Worker 处理裁剪计算
- 毫秒级响应

### 5.3 混合方案

| 场景 | 技术 |
|------|------|
| 节点编辑 | Konva (Canvas) |
| 流程监控 | Canvas 虚拟化 |
| 子流程预览 | WebGL (PixiJS) |
| 缩略图/小地图 | Canvas 降采样 |

---

## 六、CogniFlow 画布实现建议

基于 Node-RED 和业界实践，推荐：

1. **初期**: SVG + D3（类似 Node-RED），快速开发
2. **中期**: 引入 dirty flag + viewport culling
3. **后期**: Canvas (Konva) 迁移，支持大规模流程

**关键优化点**:
- 用 `requestAnimationFrame` 节流重绘
- Web Worker 处理布局计算
- 缩放时用 LOD 降级渲染细节
- 连线路径用 Path2D 缓存
