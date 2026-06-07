# Node-RED 编辑器架构研究报告
SVG+D3 画布、自研缩放、dirty flag、Wire 二维数组、REST+WebSocket

---

## 一、源码架构概览
Node-RED 采用 monorepo 结构，核心包位于 packages/node_modules/@node-red/：

        
| 包名 | 职责 |
| --- | --- |
| editor-client | 前端编辑器 UI（SVG 画布、节点编辑对话框、侧边栏） |
| runtime | 后端运行时（消息流执行引擎、节点注册表） |
| registry | 节点模块的发现、加载、注册管理 |
| editor-api | 编辑器与后端通信的 REST API |

## 二、前端编辑器架构

### 2.1 技术选型
**编辑器核心：自研 + D3.js + Monaco**

 
- **画布渲染:** D3.js SVG（view.js）— 不是 Canvas，不是 WebGL 
- **节点编辑对话框:** 自研 + Monaco Editor（VS Code 内核） 
- **UI 框架:** jQuery + 原生 DOM 操作 
- **包管理:** 事件驱动架构（RED.events） 

### 2.2 画布实现（SVG + D3）
view.js 实现了 Node-RED 的画布，采用 D3.js + SVG 而非 Canvas/WebGL。

```text
outer = d3.select("#red-ui-workspace-chart")
    .append("svg:svg")
    .attr("width", 8000)   // 固定空间尺寸
    .attr("height", 8000)
    .attr("pointer-events", "all")
    .style("touch-action", "none");
```

### 2.3 SVG 层结构

```text
#red-ui-workspace-chart
 └─ <svg> "outer"
     └─ <g>
         ├─ <g>.red-ui-workspace-chart-event-layer   — 事件处理
         ├─ <rect>.red-ui-workspace-chart-background   — 背景
         ├─ <g>.red-ui-workspace-chart-grid          — 网格线
         ├─ <g> "groupLayer"                        — 节点组
         ├─ <g> "linkLayer"                          — 连接线
         ├─ <g> "junctionLayer"                      — 汇合点
         ├─ <g> "dragGroupLayer"                    — 拖拽层
         └─ <g> "nodeLayer"                          — 节点本体
```

### 2.4 缩放/平移实现（纯手动，非 D3 zoom）
Node-RED 使用自定义缩放逻辑，不依赖 D3 的 d3.zoomBehavior。缩放范围 [0.3, 2.0]，步进 0.1。

```text
scaleFactor = Math.min(2, Math.max(0.3, scaleFactor + delta));

function zoomView(factor) {
    var screenSize = [chart.width(), chart.height()];
    var scrollPos = [chart.scrollLeft(), chart.scrollTop()];
    var center = [(scrollPos[0] + screenSize[0]/2)/scaleFactor,
                  (scrollPos[1] + screenSize[1]/2)/scaleFactor];
    scaleFactor = factor;
    // 调整 scroll 保持中心点不变
    chart.scrollLeft(scrollPos[0]-delta[0]);
    chart.scrollTop(scrollPos[1]-delta[1]);
    redraw();
}
```

### 2.5 重绘机制（dirty flag 模式）
Node-RED 没有虚拟化渲染（不计算 viewport 裁剪），而是用 **dirty flag** 优化。

```javascript
function redraw() {
    if (arguments.length === 0) {
        // 全量重绘
        outer.selectAll(".red-ui-flow-node").attr("transform", ...);
        outer.selectAll(".red-ui-flow-link").attr("d", ...);
    }
}
node.dirty = true;  // 标记 dirty，触发重绘
```

## 三、节点类型系统

### 3.1 节点定义结构
节点通过 RED.nodes.registerType(type, constructor, opts) 注册：

```text
RED.nodes.registerType("my-node", function(n) {
    this.on("input", function(msg, send, done) {
        send(msg);
        done();
    });
}, {
    category: "function",      // Palette 分类
    defaults: {
        name: { value: "" },
        topic: { value: "", validate: RED.validators.number }
    },
    inputs: 1,
    outputs: 1,
    icon: "icon/file.svg",
    oneditprepare: function() {...},  // 编辑对话框准备
    oneditsave: function() {...},
    oneditcancel: function() {...}
});
```

### 3.2 节点注册表（Registry）
@node-red/registry 包负责：发现、加载、注册、库管理四大职责。

## 四、运行时执行引擎

### 4.1 边的数据结构（Wire）
wires 是**二维数组** [outputIndex][targetNodeIds]，支持多输出端口、分支、汇聚。

```text
// wires: 二维数组 [outputIndex][targetNodeIds]
node.wires = [
    ["node-id-1", "node-id-2"],   // output 0 的目标
    ["node-id-3"],                 // output 1 的目标
];
```

### 4.2 消息发送优化

```text
// 优化1: 单线连接 → 直接引用
if (this.wires.length === 1 && this.wires[0].length === 1) {
    this._wire = this.wires[0][0];  // 直接引用目标节点
    this.send = /* 快捷路径 */;
}
// 优化2: 无连接 → NOOP
if (wc === 0) {
    this.send = NOOP_SEND;
}
```

### 4.3 部署类型
        
| 类型 | 说明 |
| --- | --- |
| full | 完整部署（重启所有节点） |
| nodes | 仅重启修改的节点 |
| flows | 仅重启修改的流程 |
| reload | 重新加载（不重启） |

## 五、通信机制

### 5.1 Editor ↔ Runtime 通信
Node-RED 使用 **HTTP REST API + WebSocket 双向通信**。

          
| 端点 | 功能 |
| --- | --- |
| GET /flows | 获取当前流程配置 |
| POST /flows | 部署新流程 |
| GET /flow/:id | 获取单个流程 |
| PUT /flow/:id | 更新流程 |
| DELETE /flow/:id | 删除流程 |
| GET /nodes | 获取已注册节点列表 |

## 六、关键技术点总结
            
| 维度 | Node-RED 方案 | 备注 |
| --- | --- | --- |
| 画布渲染 | SVG + D3.js | 固定 8000×8000 空间，CSS scroll 滚动 |
| 缩放实现 | 纯手动 scaleFactor | 范围 [0.3, 2.0]，非 D3 zoom |
| 重绘优化 | dirty flag | 非虚拟化，无 viewport culling |
| 运行时 | Node.js 单线程 | 事件驱动 + async hooks |
| 消息路由 | Wire 二维数组 | 支持多输出/分支/汇聚 |
| 部署锁 | async-mutex | 保证部署原子性 |
| 节点注册 | registry 包 | 动态 require，运行时加载 |
| 编辑器通信 | HTTP REST + WebSocket | socket.io 双向事件 |

## 七、对 CogniFlow 的参考价值

 
- **画布技术选型:** Node-RED 用 SVG 适合节点编辑器（编辑态），但运行态（监控）可能需要 Canvas/WebGL 
- **消息流模型:** Wire 二维数组结构简单高效，支持多输出和分支汇聚 
- **节点注册:** 运行时动态加载机制值得借鉴（松耦合） 
- **Dirty Flag:** 比虚拟化更简单，适合中小规模流程（<1000 节点） 
- **Subflow 模式:** 可嵌套的子流程设计支持模块化 
- **部署粒度:** 四级部署策略（full/nodes/flows/reload）可借鉴 
- **编辑器-运行时分离:** REST API 解耦，支持分布式部署
