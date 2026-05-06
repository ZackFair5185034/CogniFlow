# Web 版无限画布 / 规则引擎 / 节点编辑器技术调研报告

> 调研时间：2025-05-06 02:30

## 概述

本报告系统调研了当前主流 Web 端节点编辑器/无限画布技术，重点参考 **ComfyUI**（与 CogniFlow 场景最接近的"检测→处理→动作"流程），同时涵盖 React Flow、Vue Flow、Node-RED 等成熟方案。报告按 8 个维度组织设计思路，供 CogniFlow 规则引擎画布编辑器实现参考。

---

## 一、页面布局

### 1.1 典型布局结构

| 区域 | 说明 | 参考方案 |
|------|------|---------|
| **左侧面板** | 节点分类/节点库 | ComfyUI: 节点分类抽屉；Node-RED: 可折叠节点面板 |
| **中间画布** | 无限画布核心区 | 所有方案一致 |
| **右侧面板** | 属性配置/节点参数 | ComfyUI: 浮动参数面板；Node-RED: 侧边栏 |
| **顶部工具栏** | 操作按钮/缩放控制 | React Flow: miniMap + Controls |
| **底部/顶部队列** | 执行状态/队列管理 | ComfyUI: 底部队列栏 |

**布局设计方案（可直接参考）:**

```
┌──────────────────────────────────────────────────────────┐
│  工具栏 (保存/加载/执行/撤销/重做)                        │
├────────────┬─────────────────────────────┬───────────────┤
│            │                             │               │
│  节点面板   │        无限画布              │   参数配置     │
│  (可折叠)   │                             │   面板        │
│            │    ┌─────┐   ┌─────┐        │               │
│  📁 输入    │    │节点A│──▶│节点B│        │  [节点属性]   │
│  📁 处理    │    └─────┘   └─────┘        │  input: xxx  │
│  📁 输出    │                             │  threshold:  │
│            │                             │               │
├────────────┴─────────────────────────────┴───────────────┤
│  队列/状态栏                                              │
└──────────────────────────────────────────────────────────┘
```

### 1.2 响应式设计

- **移动端**: 隐藏节点面板（通过汉堡菜单触发）；画布支持触控缩放/平移
- **平板端**: 节点面板可收起为图标模式
- **桌面端**: 完整三栏布局

**建议（可直接参考）:** 使用 CSS Grid/Flexbox 配合 `resize` 事件动态调整面板宽度

### 1.3 多标签/多画布支持

- 浏览器 Tab 天然支持多标签
- 画布内部多画布（如多个工作流）通过 **Tab 栏** 切换
- 每个画布独立 `graph` 状态

---

## 二、样式设计

### 2.1 节点外观

| 特征 | 推荐方案 |
|------|---------|
| **形状** | 圆角矩形（`border-radius: 8px`），ComfyUI/Node-RED 均采用 |
| **大小** | 宽度自适应内容，最小 `180px × 60px` |
| **颜色** | 按节点类型着色（如输入=蓝色系，处理=绿色系，输出=橙色系） |
| **图标** | 左侧类型图标，右侧状态图标（运行中=旋转，加载=脉冲） |

**节点 CSS 样式示例（可直接参考）:**

```css
.node {
  background: var(--bg-node);
  border: 2px solid var(--border-node);
  border-radius: 8px;
  min-width: 180px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
  transition: border-color 0.2s, box-shadow 0.2s;
}
.node.selected {
  border-color: var(--accent-cyan);
  box-shadow: 0 0 0 3px rgba(0,255,255,0.2);
}
.node.running {
  border-color: var(--accent-yellow);
  animation: pulse 1.5s infinite;
}
```

### 2.2 连线样式

| 类型 | 适用场景 | 实现难度 |
|------|---------|---------|
| **贝塞尔曲线** | 通用，推荐默认 | 中等 |
| **直线** | 简单图/调试 | 简单 |
| **直角/阶梯形** | 流程图风格 | 中等 |

**贝塞尔控制点计算（可直接参考）:**
- 水平连接：控制点水平偏移 `Math.min(50, Math.abs(targetX - sourceX) / 2)`
- 垂直连接：根据源/目标端口位置动态调整

### 2.3 状态视觉反馈

| 状态 | 视觉反馈 |
|------|---------|
| **默认** | 灰边框，深色背景 |
| **选中** | 青色高亮边框 + 光晕 |
| **运行中** | 边框颜色变为黄色 + 脉冲动画 |
| **完成** | 绿色边框 + 勾号图标 |
| **错误** | 红色边框 + 错误图标 |
| **禁用** | 降低透明度 50% |

### 2.4 暗色主题适配

所有主流方案均支持暗色主题，核心通过 CSS 变量实现：

```css
:root {
  --bg-canvas: #1a1a2e;
  --bg-node: #16213e;
  --bg-panel: #0f0f23;
  --border-color: #2d3748;
  --text-primary: #e2e8f0;
  --accent-cyan: #00d4ff;
  --accent-green: #10b981;
  --accent-yellow: #f59e0b;
  --accent-red: #ef4444;
}
```

---

## 三、节点数据结构

### 3.1 节点定义

**JSON Schema 设计（可直接参考 ComfyUI 的节点结构）:**

```json
{
  "id": "node_001",
  "type": "YOLODetector",
  "position": { "x": 100, "y": 200 },
  "data": {
    "label": "YOLO 检测器",
    "config": {
      "model": "yolov8n.pt",
      "confidence": 0.5,
      "iou_threshold": 0.45
    },
    "inputs": [
      { "name": "image", "type": "image", "required": true }
    ],
    "outputs": [
      { "name": "boxes", "type": "array" },
      { "name": "scores", "type": "array" }
    ]
  },
  "width": 220,
  "height": 160
}
```

### 3.2 边的数据结构

**边 JSON Schema（可直接参考）:**

```json
{
  "id": "edge_001",
  "source": "node_001",
  "sourceHandle": "output_0",
  "target": "node_002",
  "targetHandle": "input_0",
  "type": "smoothstep",
  "animated": false,
  "data": {
    "connectionType": "dataflow"
  }
}
```

### 3.3 图的序列化格式

**完整工作流 JSON（可直接参考）:**

```json
{
  "version": "1.0",
  "name": "检测处理流程",
  "nodes": [...],
  "edges": [...],
  "viewport": {
    "x": 0,
    "y": 0,
    "zoom": 1
  },
  "metadata": {
    "created": "2025-05-06T02:00:00Z",
    "modified": "2025-05-06T02:30:00Z",
    "author": "user_001"
  }
}
```

### 3.4 节点嵌套/子图

两种方案：
1. **子图作为节点**: 子图包装为 `SubgraphNode`，展开时进入子画布
2. **分组/注释**: 使用 `Group` 实体包含多个节点，仅做视觉组织

**建议（需改造）:** 初期使用分组方案（简单），后期支持子图展开

---

## 四、数据库设计

### 4.1 图数据持久化

**推荐表结构（可直接参考）:**

```sql
-- 工作流表
CREATE TABLE workflows (
  id UUID PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  description TEXT,
  graph_data JSONB NOT NULL,  -- 完整的 nodes + edges
  thumbnail TEXT,              -- 缩略图 base64
  version INTEGER DEFAULT 1,
  is_deleted BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- 工作流版本表
CREATE TABLE workflow_versions (
  id UUID PRIMARY KEY,
  workflow_id UUID REFERENCES workflows(id),
  version INTEGER NOT NULL,
  graph_data JSONB NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);
```

### 4.2 执行记录存储

```sql
-- 执行记录表
CREATE TABLE executions (
  id UUID PRIMARY KEY,
  workflow_id UUID REFERENCES workflows(id),
  status VARCHAR(50),  -- 'running', 'completed', 'failed', 'cancelled'
  started_at TIMESTAMP,
  completed_at TIMESTAMP,
  node_states JSONB,   -- 每个节点的执行状态
  error_message TEXT,
  execution_log JSONB  -- 详细日志
);

-- 节点中间结果缓存
CREATE TABLE execution_cache (
  id UUID PRIMARY KEY,
  execution_id UUID REFERENCES executions(id),
  node_id VARCHAR(255),
  cache_key VARCHAR(255),
  cache_value JSONB,
  created_at TIMESTAMP DEFAULT NOW()
);
```

### 4.3 版本管理

- 每次保存生成新版本记录
- 支持版本对比（diff）和回滚
- 自动清理超过 30 天的历史版本

---

## 五、交互设计

### 5.1 拖拽节点到画布

| 步骤 | 实现方式 |
|------|---------|
| 1. 拖拽开始 | `onDragStart` 记录节点类型 |
| 2. 拖拽中 | 跟随鼠标，实时更新画布预览 |
| 3. 拖拽结束 | `onDrop` 计算放置位置，调用 `addNode` |

**代码示例（可直接参考）:**

```typescript
const onDragOver = (event: React.DragEvent) => {
  event.preventDefault();
  event.dataTransfer.dropEffect = 'move';
};

const onDrop = (event: React.DragEvent) => {
  event.preventDefault();
  const nodeType = event.dataTransfer.getData('application/reactflow');
  const position = screenToFlowPosition({
    x: event.clientX,
    y: event.clientY,
  });
  const newNode = {
    id: `node_${Date.now()}`,
    type: nodeType,
    position,
    data: { label: nodeType, config: {} },
  };
  setNodes((nds) => nds.concat(newNode));
};
```

### 5.2 节点连线

| 交互 | 实现 |
|------|------|
| 拖拽连接点 | `onConnectStart` → 拖拽过程中绘制临时边 → `onConnectEnd` 完成连接 |
| 类型检查 | 连接前检查 `sourceHandle.type === targetHandle.type` |
| 断开连接 | 右键菜单或选中边按 Delete |

### 5.3 画布缩放/平移

| 操作 | 实现 |
|------|------|
| 鼠标滚轮缩放 | `onWheel` 事件，限制 `minZoom: 0.1, maxZoom: 2.0` |
| 拖拽平移 | `onPane` 拖拽事件 |
| 双击适应屏幕 | `fitView({ padding: 0.2 })` |

### 5.4 多选/框选

- **框选**: 按住鼠标拖拽创建选择框，`onSelectionChange` 获取选中节点
- **多选**: `Shift + Click` 添删节点
- **全选**: `Ctrl + A`
- **批量操作**: 选中后统一移动/删除/复制

### 5.5 撤销/重做

使用 **Command Pattern** 或 **Memento Pattern**:

```typescript
interface HistoryState {
  nodes: Node[];
  edges: Edge[];
}

// 简化实现：保存操作栈
const [history, setHistory] = useState<HistoryState[]>([]);
const [historyIndex, setHistoryIndex] = useState(-1);

// 每次操作后保存状态
const saveToHistory = (newState: HistoryState) => {
  setHistory(prev => [...prev.slice(0, historyIndex + 1), newState]);
  setHistoryIndex(prev => prev + 1);
};

// 撤销: historyIndex - 1
// 重做: historyIndex + 1
```

### 5.6 快捷键

| 快捷键 | 功能 |
|-------|------|
| `Ctrl + Z` | 撤销 |
| `Ctrl + Shift + Z` | 重做 |
| `Delete` / `Backspace` | 删除选中 |
| `Ctrl + A` | 全选 |
| `Ctrl + C` | 复制 |
| `Ctrl + V` | 粘贴 |
| `Ctrl + D` | 复制并偏移粘贴 |
| `Space + 拖拽` | 平移画布 |
| `Ctrl + 滚轮` | 缩放 |
| `F` | 适应屏幕 |

---

## 六、性能优化

### 6.1 大型图（500+ 节点）渲染优化

| 优化策略 | 说明 |
|---------|------|
| **视口裁剪** | 只渲染可见区域节点（React Flow 内置 `onlyRenderVisibleElements`） |
| **节点虚拟化** | 使用 `react-window` 或类似库 |
| **批量更新** | 使用 `React.memo` + `useMemo` 缓存节点组件 |
| **懒加载** | 节点配置面板懒加载 |

**React Flow 性能配置（可直接参考）:**

```typescript
<ReactFlow
  nodesDraggable={true}
  nodesConnectable={true}
  elementsLineType={ElementLineType.SmoothStep}
  onlyRenderVisibleElements={true}
  defaultViewport={{ x: 0, y: 0, zoom: 1 }}
  // 节点展开时才渲染内部内容
  nodeExtent={[
    [-5000, -5000],
    [5000, 5000],
  ]}
/>
```

### 6.2 边的绘制优化

- 边使用 SVG `<path>` 而非 DOM 元素
- 贝塞尔曲线计算使用 `memo` 缓存
- 断点边使用 Canvas 2D 渲染（而非 SVG）

### 6.3 视口裁剪/虚拟化

**核心思路:**
1. 计算可视区域 (`getViewport`)
2. 过滤出在可视区域内的节点
3. 只渲染这些节点
4. 拖拽/缩放时更新可视区域

```typescript
const getVisibleNodes = (nodes: Node[], viewport: Viewport) => {
  const { x, y, zoom } = viewport;
  const padding = 100; // 额外渲染边界外的节点，避免抖动

  return nodes.filter(node => {
    const [nx, ny] = node.position;
    const width = node.width || 180;
    const height = node.height || 60;

    return (
      nx + width > -x - padding &&
      nx < -x + window.innerWidth / zoom + padding &&
      ny + height > -y - padding &&
      ny < -y + window.innerHeight / zoom + padding
    );
  });
};
```

---

## 七、执行引擎

### 7.1 图的遍历方式

| 算法 | 适用场景 | 说明 |
|------|---------|------|
| **拓扑排序 (Kahn's Algorithm)** | 有向无环图 (DAG) | 通用，推荐默认 |
| **DFS** | 简单遍历/调试 | 可能栈溢出 |
| **BFS** | 层级执行 | 适合并行化 |

**Kahn's Algorithm 实现（可直接参考）:**

```typescript
function topologicalSort(nodes: Node[], edges: Edge[]): Node[] {
  // 1. 计算入度
  const inDegree = new Map<string, number>();
  nodes.forEach(n => inDegree.set(n.id, 0));
  edges.forEach(e => {
    inDegree.set(e.target, (inDegree.get(e.target) || 0) + 1);
  });

  // 2. 入度为0的节点入队
  const queue = nodes.filter(n => inDegree.get(n.id) === 0);
  const result: Node[] = [];

  while (queue.length > 0) {
    const node = queue.shift()!;
    result.push(node);

    // 3. 更新依赖节点入度
    edges
      .filter(e => e.source === node.id)
      .forEach(e => {
        const newDegree = (inDegree.get(e.target) || 0) - 1;
        inDegree.set(e.target, newDegree);
        if (newDegree === 0) queue.push(nodes.find(n => n.id === e.target)!);
      });
  }

  return result;
}
```

### 7.2 节点执行顺序

1. **拓扑排序** → 得到执行顺序列表
2. **分组执行**: 同一"层级"的节点可并行执行
3. **依赖检查**: 执行前检查前置节点是否完成

### 7.3 并行执行

```typescript
async function executeGraph(nodes: Node[], edges: Edge[]) {
  const sorted = topologicalSort(nodes, edges);
  const levels = groupByLevel(sorted, edges); // 按层级分组

  for (const level of levels) {
    await Promise.all(
      level.map(node => executeNode(node))
    );
  }
}
```

### 7.4 断点/调试支持

| 功能 | 实现 |
|------|------|
| **断点** | 节点添加 `breakpoint: true` 标记，执行到断点暂停 |
| **单步执行** | `executeNextNode()` 仅执行一个节点 |
| **变量查看** | 执行时保存中间结果到 `execution_cache` 表 |
| **执行日志** | 每个节点 `console.log` + WebSocket 推送前端 |

---

## 八、ComfyUI 专项调研

> **重点参考**: ComfyUI 是目前最好的开源节点编辑器实现，其"图像生成流水线"与 CogniFlow 的"检测→处理→动作"流程高度相似。

### 8.1 ComfyUI 前端架构

**技术栈（可直接参考）:**
- **核心库**: 纯原生 JavaScript + 少量 DOM 操作（无 React/Vue 依赖）
- **画布渲染**: Canvas 2D API 绑定 SVG 边
- **节点定义**: JavaScript 对象（每个节点类型一个文件）
- **状态管理**: 自定义 `app` 对象 + 事件系统

**文件结构（可直接参考）:**
```
web/
├── index.html
├── js/
│   ├── app.js              # 主应用，节点图管理
│   ├── canvas.js           # 画布渲染（缩放/平移/选择）
│   ├── nodes/             # 节点类型定义
│   │   ├── loaders.js     # LoadImage, LoadCheckpoint
│   │   ├── image.js       # ImageWatermark, ImageCrop
│   │   ├── latent.js      # EmptyLatent, VAEEncode
│   │   └── ...
│   ├── graph.js           # 图数据结构
│   ├── graphInputs.js     # 输入/输出处理
│   └── ...
└── css/
    └── ...
```

### 8.2 ComfyUI 节点数据结构

**节点对象（JS 格式，直接可用）:**

```javascript
// 简化版节点定义
{
  id: "node_id_001",
  type: "LoadImage",
  pos: [100, 200],
  size: [200, 60],
  flags: {},
  order: 0,
  // 输入端口（类型化连接点）
  inputs: [
    { name: "image", type: "IMAGE", link: null }
  ],
  // 输出端口
  outputs: [
    { name: "IMAGE", type: "IMAGE", links: [edge_id_001] }
  ],
  properties: {},
  // 节点特定配置
  widgets_values: ["path/to/image.png"]
}
```

**连接类型（直接可用）:**
```javascript
const valid_connection_types = [
  "IMAGE", "MASK", "LATENT", "MODEL", "CLIP", "VAE",
  "CONDITIONING", " CONTROL_NET", "STYLE_MODEL", "UPSCALE_MODEL"
];
```

### 8.3 ComfyUI Backend API 设计

**API 端点（直接可用）:**

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/prompt` | POST | 提交工作流执行 |
| `/api/queue` | GET | 获取队列状态 |
| `/api/queue` | POST | 管理队列（清空等） |
| `/api/history` | GET | 获取执行历史 |
| `/api/object_info` | GET | 获取所有节点类型定义 |
| `/api/system_stats` | GET | 系统资源状态 |
| `/api/memory` | GET | 显存使用情况 |

**工作流提交格式（直接可用）:**

```json
POST /api/prompt
{
  "prompt": {
    "node_id_1": {
      "class_type": "LoadImage",
      "inputs": {
        "image": "path/to/image.png"
      }
    },
    "node_id_2": {
      "class_type": "CLIPTextEncode",
      "inputs": {
        "text": "a cat",
        "clip": [["node_id_3", 0]]
      }
    },
    "node_id_3": {
      "class_type": "CLIPLoader",
      "inputs": {
        "clip_path": "models/clip/xxx.bin"
      }
    }
  },
  "extra_data": {
    "extra_pnginfo": {
      "workflow": "完整工作流 JSON（用于前端恢复）"
    }
  }
}
```

### 8.4 ComfyUI 节点类型系统

| 类别 | 节点类型 | 说明 |
|------|---------|------|
| **加载器** | LoadImage, LoadCheckpoint, CLIPLoader, VAELoader | 加载资源 |
| **编码器** | CLIPTextEncode, ControlNetApply | 编码条件 |
| **模型** | CheckpointLoader, DiffusersLoader | 模型管理 |
| **图像处理** | ImageScale, ImageCrop, ImageWatermark | 图像操作 |
| **潜在空间** | EmptyLatent, VAEEncode, VAEDecode | Latent 操作 |
| **采样器** | KSampler, KSamplerAdvanced | 采样控制 |
| **输出** | SaveImage, PreviewImage | 结果输出 |

**CogniFlow 映射建议:**

| ComfyUI 类型 | CogniFlow 对应 | 说明 |
|-------------|---------------|------|
| LoadImage | ImageCapture / VideoCapture | 输入源 |
| LoadCheckpoint | YOLOModel / ModelLoader | 模型加载 |
| CLIPTextEncode | CategoryEncode | 类别编码 |
| KSampler | InferenceNode | 推理节点 |
| SaveImage | ActionOutput | 输出/动作执行 |

### 8.5 ComfyUI 连接类型检查

**类型兼容规则（直接可用）:**

```javascript
// 输出类型到输入类型的映射
const input_mapping = {
  "CLIP": ["CLIPTextEncode", "CLIPLoader", ...],
  "MODEL": ["KSampler", "ControlNetApply", ...],
  "IMAGE": ["ImageScale", "ImageWatermark", "VAEEncode", ...],
  "LATENT": ["VAEDecode", ...]
};

// 连接时检查
function canConnect(sourceType, targetType) {
  return input_mapping[sourceType]?.includes(targetType) ||
         input_mapping[targetType]?.includes(sourceType);
}
```

### 8.6 ComfyUI 执行调度

**执行流程（直接参考）:**

1. **前端提交**: `POST /api/prompt` 发送完整工作流
2. **队列管理**: 服务端将任务加入队列（`queue` 数组）
3. **拓扑排序**: 后端对节点进行排序
4. **逐节点执行**: 按顺序执行，更新 `node_id` 状态
5. **结果缓存**: 执行结果存入缓存供后续节点使用
6. **WebSocket 推送**: 实时推送执行进度到前端

**并行执行（需改造）:**
- ComfyUI 同一层级的独立节点可并行执行
- 通过 `Promise.all` + 层级分组实现

### 8.7 ComfyUI 缓存机制

| 缓存类型 | 实现 | 说明 |
|---------|------|------|
| **模型缓存** | `model_management` 模块 | VRAM 管理，模型共享 |
| **执行缓存** | `cache` 字典 | 每个节点的输出结果缓存 |
| **图像缓存** | 临时文件 + LRU | 避免重复加载相同图像 |

### 8.8 ComfyUI 界面布局

**三栏布局（直接参考）:**

```
┌─────────────────────────────────────────────────────────────┐
│  Queue: 0 | Memory: 4.2GB/8GB | VRAM: 2.1GB/8GB            │
├────────┬────────────────────────────────────────┬───────────┤
│        │                                        │           │
│ 节点库 │              画布区域                   │  参数面板  │
│        │                                        │           │
│ 📁 加载 │   ┌─────┐     ┌─────┐                 │ [节点配置] │
│   LoadImage │  │Load │────▶│CLIP │               │           │
│   LoadCheckpoint │ Image│     │Text │               │ model: xxx│
│   VAELoader │ └─────┘     │Encod│               │ thresh:   │
│            │             └─────┘                 │           │
│ 📁 图像处理│                                        │           │
│   ImageScale│                                       │           │
│   ImageCrop │                                        │           │
│            │                                        │           │
│ 📁 采样器  │                                        │           │
│   KSampler│                                        │           │
│            │                                        │           │
├────────┴────────────────────────────────────────┴───────────┤
│  Queue: [1] Generation 1 ✓  |  History ▶                   │
└─────────────────────────────────────────────────────────────┘
```

**关键 UI 组件:**
- **顶部状态栏**: 队列计数、显存/内存使用
- **左侧节点抽屉**: 按类别折叠的节点列表（支持搜索）
- **中间画布**: 节点编辑区域
- **右侧参数面板**: 当前选中节点的配置项
- **底部队列栏**: 执行状态、执行历史

---

## 九、可落地设计建议

### 9.1 优先级排序

| 优先级 | 功能 | 参考方案 | 备注 |
|-------|------|---------|------|
| **P0** | 画布渲染/缩放/平移 | React Flow | 成熟的无限画布库 |
| **P0** | 节点定义/渲染 | ComfyUI 节点结构 | 类型化输入输出 |
| **P0** | 连线交互/类型检查 | ComfyUI 连接类型 | 确保数据流正确 |
| **P1** | 拖拽放置节点 | React Flow examples | 节点面板 + DnD |
| **P1** | 属性配置面板 | ComfyUI 参数面板 | 右侧浮动面板 |
| **P1** | 执行引擎 | Kahn's Algorithm | 拓扑排序执行 |
| **P2** | 撤销/重做 | Command Pattern | 状态历史栈 |
| **P2** | 断点调试 | 执行状态可视化 | 节点状态颜色 |
| **P3** | 多画布/标签 | Tab 栏切换 | 后期功能 |

### 9.2 技术选型建议

**前端:**
- **画布库**: React Flow（Vue 项目用 Vue Flow）— 成熟、功能完整、文档好
- **状态管理**: Zustand（轻量）或 Pinia（Vue）
- **样式**: UnoCSS + CSS 变量

**后端:**
- **API 框架**: FastAPI（与 CogniFlow 后端一致）
- **执行引擎**: Python 异步 + 拓扑排序
- **缓存**: Redis（模型缓存、中间结果）
- **WebSocket**: 实时推送执行状态

### 9.3 快速验证路径

1. **Phase 1**: 集成 React Flow，用 ComfyUI 节点结构定义 CogniFlow 节点
2. **Phase 2**: 实现后端 API（提交工作流、查询状态）
3. **Phase 3**: 实现执行引擎（拓扑排序 + 节点执行）
4. **Phase 4**: 添加执行状态可视化（WebSocket 推送）
5. **Phase 5**: 添加撤销/重做、断点调试等高级功能

---

## 十、参考资料

1. [React Flow 文档](https://reactflow.dev/)
2. [Vue Flow 文档](https://vueflow.dev/)
3. [Node-RED 官方文档](https://nodered.org/)
4. [ComfyUI GitHub](https://github.com/comfyanonymous/ComfyUI)
5. [ComfyUI-UI GitHub](https://github.com/Comfy-Org/ComfyUI-frontend)
6. [xyflow (React Flow) GitHub](https://github.com/xyflow/xyflow)

---

*报告生成时间: 2025-05-06 02:30*
*下次调研时间: 2025-05-06 04:30（2小时后自动触发）*
