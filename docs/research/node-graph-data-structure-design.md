# 节点图数据结构设计研究报告

> 调研时间：2026-05-06
> 基于既有调研文档和 ComfyUI 源码分析

---

## 目录

1. [节点图数学定义](#1-节点图数学定义)
2. [图的序列化格式（JSON 结构设计）](#2-图的序列化格式)
3. [节点类型系统设计模式](#3-节点类型系统设计模式)
4. [输入/输出端口类型系统](#4-输入输出端口类型系统)
5. [边的连接规则（类型检查/兼容性）](#5-边的连接规则)
6. [子图/嵌套图的处理方式](#6-子图嵌套图的处理)
7. [图的版本管理和变更追踪](#7-版本管理和变更追踪)
8. [撤销/重做实现](#8-撤销重做实现)
9. [ComfyUI 专项分析](#9-comfyui-专项分析)

---

## 1. 节点图数学定义

### 1.1 图的数学形式化

```
G = (V, E, T) 是一个有向无环图（DAG）

其中：
- V = {v₁, v₂, ..., vₙ} 是节点集合
- E ⊆ V × V 是有向边集合
- T 是类型系统：V → Type 表示节点类型
```

### 1.2 节点定义

```
节点 v = (id, type, position, inputs, outputs, data)

- id: 唯一标识符 (string)
- type: 节点类型名称 (string) 
- position: 画布坐标 (x, y) ∈ ℝ²
- inputs: 输入端口映射 {port_name: ConnectionState}
- outputs: 输出端口定义 {port_name: PortType}
- data: 节点特定数据/参数
```

### 1.3 边定义

```
边 e = (id, source, sourceHandle, target, targetHandle, type)

- id: 唯一标识符
- source: 源节点 ID
- sourceHandle: 源端口名称
- target: 目标节点 ID  
- targetHandle: 目标端口名称
- type: 连接数据类型 (IMAGE, BBOX, TRIGGER, etc.)
```

### 1.4 执行依赖关系

```
依赖函数: deps(v) = {u ∈ V | ∃e ∈ E: e.source = u ∧ e.target = v}
执行层级: level(v) = 0 if deps(v) = ∅ else max(level(u) + 1 for u in deps(v))
```

---

## 2. 图的序列化格式

### 2.1 ComfyUI 工作流 JSON 格式（重点参考）

```json
{
  "version": "0.4.2",
  "nodes": [
    {
      "id": "node_id_1",
      "type": "ScreenCapture",
      "pos": [100, 200],
      "size": [200, 100],
      "flags": {},
      "order": 0,
      "properties": {
        "color": "#00d4ff",
        "bgcolor": "#2d2d2d"
      },
      "widgets": {
        "mode": "fullscreen",
        "fps": 30,
        "region": [0, 0, 1920, 1080]
      },
      "inputs": [
        { "name": "trigger", "type": "trigger", "link": null }
      ],
      "outputs": [
        { "name": "IMAGE", "type": "IMAGE", "links": [2] },
        { "name": "MASK", "type": "MASK", "links": null }
      ]
    }
  ],
  "links": {
    "1": ["node_id_1", "IMAGE", "node_id_2", "frame", "IMAGE"],
    "2": ["node_id_2", "output", null, null, "IMAGE"]
  },
  "groups": [],
  "config": {},
  "extra": {
    "ds": { "scale": 1, "offset": [0, 0] }
  }
}
```

**links 格式解析：**
```javascript
links = {
  linkId: [sourceId, sourceHandleName, targetId, targetHandleName, linkType]
}
// 例如：[node1, IMAGE, node2, frame, IMAGE]
```

### 2.2 CogniFlow 推荐 JSON 格式

```json
{
  "id": "workflow_001",
  "name": "目标检测流程",
  "version": 1,
  "nodes": {
    "node_001": {
      "id": "node_001",
      "type": "ImageCapture",
      "position": {"x": 100, "y": 200},
      "data": {
        "label": "摄像头输入",
        "params": {
          "source": "video0",
          "fps": 30
        }
      },
      "inputs": {
        "trigger": {"node_id": null, "output": null, "value": null}
      },
      "outputs": {
        "image": {"type": "IMAGE"}
      }
    }
  },
  "edges": [
    {
      "id": "edge_001",
      "source": "node_001",
      "source_handle": "image",
      "target": "node_002", 
      "target_handle": "image",
      "type": "IMAGE"
    }
  ],
  "variables": {
    "DEFAULT_CONFIDENCE": {"type": "float", "default": 0.5}
  }
}
```

### 2.3 序列化最佳实践

| 方案 | 优点 | 缺点 |
|------|------|------|
| JSON 文档存储 | 完整图结构便于传输/导入导出 | 更新复杂需整体替换 |
| 关系型存储 | 节点/边独立更新 | 查询需 JOIN |

**推荐：** JSON 文档存储为主（传输方便），关系型存储为辅（查询优化）

---

## 3. 节点类型系统设计模式

### 3.1 节点分类（CogniFlow 推荐）

```javascript
const COGNIFLOW_CATEGORIES = {
  '输入 Input': { 
    color: '#4CFF4C', 
    nodes: ['ScreenCapture', 'ImageInput', 'VideoInput'] 
  },
  '检测 Detect': { 
    color: '#00D4FF', 
    nodes: ['ObjectDetector', 'YOLONode', 'FaceDetector'] 
  },
  '处理 Process': { 
    color: '#FFFF4C', 
    nodes: ['ImagePreprocessor', 'Filter', 'Resize'] 
  },
  '动作 Action': { 
    color: '#FF7F4C', 
    nodes: ['MouseClick', 'KeyPress', 'HttpRequest'] 
  },
  '逻辑 Logic': { 
    color: '#DC4FDC', 
    nodes: ['Condition', 'Loop', 'Timer'] 
  },
  '输出 Output': { 
    color: '#FF4C4C', 
    nodes: ['SaveImage', 'Notify', 'RecordVideo'] 
  }
};
```

### 3.2 节点定义数据结构

```typescript
interface NodeDefinition {
  type: string;
  category: string;
  display_name: string;
  description: string;
  icon: string;
  color: string;
  inputs: Record<string, PortDefinition>;
  outputs: Record<string, PortDefinition>;
}

interface PortDefinition {
  name: string;
  type: string;  // IMAGE, BBOX, TRIGGER, etc.
  required: boolean;
  default: any;
  description: string;
}
```

### 3.3 ComfyUI 节点类型分类

| 分类 | 节点数 | 示例 |
|------|--------|------|
| image | 50+ | LoadImage, SaveImage, ImageBatch |
| latent | 20+ | VAEEncode, VAEDecode, EmptyLatentImage |
| sampling | 30+ | KSampler, KSamplerAdvanced |
| loaders | 15+ | CheckpointLoader, LoRALoader, ControlNetLoader |
| conditioning | 20+ | CLIPTextEncode, ControlNetApply |
| masks | 15+ | MaskBatch, InpaintMasked |
| video | 10+ | VideoCombine, VideoLoad |
| utils | 30+ | PrimitiveNode, Note |

---

## 4. 输入/输出端口类型系统

### 4.1 端口类型定义

```typescript
enum PortType {
  IMAGE = 'IMAGE',
  BBOX = 'BBOX', 
  TRIGGER = 'TRIGGER',
  MASK = 'MASK',
  LATENT = 'LATENT',
  MODEL = 'MODEL',
  CLIP = 'CLIP',
  VAE = 'VAE',
  CONDITIONING = 'CONDITIONING',
  CONTROL_NET = 'CONTROL_NET',
  CLASS_IDS = 'CLASS_IDS',
  SCORES = 'SCORES'
}
```

### 4.2 端口数据结构

```json
{
  "inputs": {
    "image": {
      "node_id": "node_001",
      "output": "image"
    },
    "confidence": {
      "value": 0.5
    }
  },
  "outputs": {
    "bboxes": {"type": "BBOX"},
    "scores": {"type": "SCORES"},
    "class_ids": {"type": "CLASS_IDS"}
  }
}
```

### 4.3 类型兼容性矩阵

| 源类型 | 可连接目标类型 |
|--------|---------------|
| IMAGE | IMAGE, MASK |
| MASK | MASK |
| LATENT | LATENT |
| MODEL | MODEL |
| CLIP | CLIP |
| VAE | VAE |
| CONDITIONING | CONDITIONING |
| CONTROL_NET | CONTROL_NET |
| * (trigger) | * (任意) |

---

## 5. 边的连接规则

### 5.1 连接规则验证

```python
def can_connect(source_port: Port, target_port: Port) -> bool:
    """检查两个端口是否可以连接"""
    # 触发器类型可以连接任意类型
    if source_port.type == 'TRIGGER' or target_port.type == 'TRIGGER':
        return True
    
    # 类型必须完全匹配
    return source_port.type == target_port.type
```

### 5.2 类型不兼容时的处理

- 端口显示红色
- 连接线显示红色
- 禁止创建连接

### 5.3 连接数据结构

```json
{
  "id": "edge_001",
  "source": "node_001",
  "source_handle": "image", 
  "target": "node_002",
  "target_handle": "frame",
  "type": "IMAGE"
}
```

---

## 6. 子图/嵌套图的处理

### 6.1 子图数据结构设计

```json
{
  "id": "subgraph_1",
  "type": "subgraph",
  "subgraphDefinition": {
    "nodes": [...],
    "links": [...],
    "inputPorts": [
      { "name": "trigger", "type": "trigger" }
    ],
    "outputPorts": [
      { "name": "result", "type": "image" }
    ]
  },
  "instanceInputs": { "trigger": null },
  "instanceOutputs": { "result": [] }
}
```

### 6.2 子图执行方式

| 方式 | 描述 |
|------|------|
| 编译时展开 | 将子图展开为普通节点 |
| 运行时求值 | 保持子图结构，递归执行 |

### 6.3 ComfyUI blueprints 方案

- 子图作为特殊节点类型
- 子图有独立输入/输出接口
- 双击子图节点进入子图画布编辑
- 支持子图复用（同一子图多次实例化）

---

## 7. 版本管理和变更追踪

### 7.1 数据库版本管理

```sql
CREATE TABLE workflow_versions (
  id VARCHAR(36) PRIMARY KEY,
  workflow_id VARCHAR(36) REFERENCES workflows(id),
  version INT NOT NULL,
  graph_data JSON NOT NULL,
  diff_data JSON,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  created_by VARCHAR(100),
  changelog TEXT
);
```

### 7.2 Git-like 版本控制

- 每次保存创建新版本，保留完整快照
- 支持版本对比（diff）
- 支持版本回滚
- 自动清理旧版本（可配置保留策略）

### 7.3 增量保存策略

```javascript
const saveWorkflowDiff = async (workflowId, changes) => {
  const patch = {
    workflowId,
    timestamp: Date.now(),
    operations: [
      { op: 'replace', path: '/nodes/0/pos', value: [100, 200] },
      { op: 'add', path: '/nodes/3', value: newNode }
    ]
  };
  await db.workflow_diffs.insert(patch);
};
```

---

## 8. 撤销/重做实现

### 8.1 Command Pattern 实现

```typescript
interface Command {
  execute(): void;
  undo(): void;
}

class MoveNodeCommand implements Command {
  constructor(
    private nodeId: string,
    private oldPosition: {x: number, y: number},
    private newPosition: {x: number, y: number}
  ) {}
  
  execute() {
    updateNodePosition(this.nodeId, this.newPosition);
  }
  
  undo() {
    updateNodePosition(this.nodeId, this.oldPosition);
  }
}

class CommandHistory {
  private undoStack: Command[] = [];
  private redoStack: Command[] = [];
  
  execute(command: Command) {
    command.execute();
    this.undoStack.push(command);
    this.redoStack = []; // 清空重做栈
  }
  
  undo() {
    const command = this.undoStack.pop();
    if (command) {
      command.undo();
      this.redoStack.push(command);
    }
  }
  
  redo() {
    const command = this.redoStack.pop();
    if (command) {
      command.execute();
      this.undoStack.push(command);
    }
  }
}
```

### 8.2 节点操作最小单元

| 操作 | 最小单元 |
|------|----------|
| 移动 | 单节点移动 |
| 属性修改 | 单属性修改 |
| 连接/断开 | 单边操作 |
| 增删 | 单节点/单边 |

### 8.3 Memento Pattern（备选）

```typescript
class WorkflowMemento {
  constructor(private state: WorkflowState) {}
  
  getState(): WorkflowState {
    return JSON.parse(JSON.stringify(this.state));
  }
}

class WorkflowOriginator {
  private state: WorkflowState;
  
  save(): WorkflowMemento {
    return new WorkflowMemento(this.state);
  }
  
  restore(memento: WorkflowMemento) {
    this.state = memento.getState();
  }
}
```

---

## 9. ComfyUI 专项分析

### 9.1 前端技术栈（重要发现）

**ComfyUI 使用纯原生 JavaScript + 少量库的方案：**

| 技术 | 用途 |
|------|------|
| 原生 JS | 核心框架 |
| Canvas API | 节点和边的渲染 |
| WebSocket | 实时通信 |
| Dragula | 节点拖拽 |
| vanilla-picker | 颜色选择 |

**关键发现：ComfyUI 并没有使用 React Flow 或 Vue Flow，而是完全自研的 Canvas 渲染引擎。**

### 9.2 ComfyUI 自研渲染引擎原因

1. 完全控制性能优化
2. 避免 React/Vue 虚拟 DOM 开销
3. 特殊交互需求（拖拽、连接线预览）
4. ComfyUI 选择自研 Canvas 的原因：

```javascript
// ComfyUI 渲染层
class CanvasRenderer {
  constructor(canvas) {
    this.ctx = canvas.getContext('2d');
    this.nodes = new Map();
    this.edges = [];
  }
  
  render() {
    this.ctx.clearRect(0, 0, width, height);
    
    // 绘制边（Canvas）
    this.edges.forEach(edge => this.drawEdge(edge));
    
    // 绘制节点（Canvas）
    this.nodes.forEach(node => this.drawNode(node));
  }
  
  handleDrag(e) {
    const node = this.hitTest(e);
    if (node) {
      node.x = e.clientX - node.dragOffsetX;
      node.y = e.clientY - node.dragOffsetY;
    }
  }
}
```

### 9.3 ComfyUI Backend API 设计

**核心 API 端点：**

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/workflow` | GET/POST | 获取/保存工作流 |
| `/api/prompt` | POST | 提交工作流执行 |
| `/api/queue` | GET | 获取队列状态 |
| `/api/history` | GET | 获取执行历史 |
| `/api/node_stats` | GET | 节点统计信息 |
| `/api/system_stats` | GET | 系统资源状态 |
| `/api/free` | GET | 显存释放 |

### 9.4 Prompt API 格式

```json
POST /api/prompt
{
  "prompt": {
    "node_001": {
      "class_type": "ScreenCapture",
      "inputs": {
        "mode": "fullscreen",
        "fps": 30
      }
    },
    "node_002": {
      "class_type": "ObjectDetector", 
      "inputs": {
        "image": ["node_001", 0]
      }
    }
  },
  "client_id": "abc123",
  "ExtraData": {}
}
```

### 9.5 执行调度流程

```
1. 前端序列化工作流 -> POST /api/prompt
2. 后端入队 -> 返回 queue_position
3. 执行引擎按拓扑排序执行
4. 实时推送进度 -> WebSocket
5. 执行完成 -> 输出缓存
```

### 9.6 WebSocket 实时协议

```javascript
// 客户端 -> 服务端
{ "type": "execution", "data": { "prompt_id": "xxx" } }
{ "type": "interrupt" }

// 服务端 -> 客户端  
{ "type": "execution_start", "data": { "prompt_id": "xxx" } }
{ "type": "node_executed", "data": { "node": "123", "output": {...} } }
{ "type": "execution_complete", "data": { "prompt_id": "xxx" } }
{ "type": "execution_error", "data": { "node": "123", "error": "..." } }
```

### 9.7 模型缓存策略

```python
class ModelCache:
    def __init__(self, max_size_gb=8):
        self.max_size = max_size_gb * 1024 * 1024 * 1024
        self.cache = LRUCache()  # 内存缓存
        self.disk_cache = DiskCache()  # 磁盘缓存
        
    def get(self, model_key):
        # 1. 查内存缓存
        if model_key in self.cache:
            return self.cache[model_key]
        
        # 2. 加载到内存
        model = self.load_model(model_key)
        
        # 3. 检查显存
        if self.get_mem_usage() + model.size > self.max_size:
            self.unload_lru()
            
        return model
```

### 9.8 拓扑排序实现（Kahn 算法）

```python
from collections import defaultdict, deque

def topological_sort(nodes, edges):
    """Kahn算法拓扑排序"""
    graph = defaultdict(list)
    in_degree = {node['id']: 0 for node in nodes}

    for edge in edges:
        source, target = edge['source'], edge['target']
        graph[source].append(target)
        in_degree[target] += 1

    queue = deque([node_id for node_id, degree in in_degree.items() if degree == 0])
    result = []

    while queue:
        node_id = queue.popleft()
        result.append(node_id)

        for neighbor in graph[node_id]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    if len(result) != len(nodes):
        raise ValueError("图存在循环依赖")

    return result
```

### 9.9 并行执行实现

```python
import asyncio

class ExecutionEngine:
    def __init__(self, max_workers=4):
        self.max_workers = max_workers
        
    async def execute_parallel(self, node_batch):
        """并行执行一批无依赖的节点"""
        tasks = []
        for node in node_batch:
            task = asyncio.create_task(self.execute_node(node))
            tasks.append(task)
        return await asyncio.gather(*tasks)

    async def execute_node(self, node):
        inputs = await self.get_node_inputs(node)
        result = await self.run_node(node, inputs)
        await self.cache_output(node.id, result)
        return result
```

### 9.10 ComfyUI 界面布局

```
+---------------------------------------------------------------------+
|  [设置] ComfyUI              [Queue: 0]  [VRAM: 4GB/8GB]  [设置]    |
+------------+----------------------------------------+----------------+
|  Node Tree |                                        | Properties     |
|  --------- |                                        | ---------      |
|  [Input]   |                                        | Node:          |
|   ScreenCap|              [Canvas Area]            |                |
|   FileLoad |      +--------+      +--------+        | FPS: 30        |
|  [Process] |      |LoadImg|----->|YOLODet|         |                |
|   YOLODet  |      +--------+      +--------+        |                |
|   Resize   |                                        |                |
|  [Output]  |                                        |                |
+------------+----------------------------------------+----------------+
|  Queue: 0 | Prompt: / | Batch: 1/1 | Memory: 4.2GB | [Run]         |
+---------------------------------------------------------------------+
```

---

## 参考资料

| 来源 | 链接 |
|------|------|
| Vue Flow | https://vueflow.dev/ |
| xyflow | https://xyflow.com/ |
| ComfyUI GitHub | https://github.com/comfyanonymous/ComfyUI |
| ComfyUI API Docs | https://docs.comfy.org/ |
| Node-RED | https://nodered.org/ |

---

*本文档由 CogniFlow 调研自动生成*
