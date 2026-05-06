# Web 版无限画布 / 规则引擎 / 节点编辑器技术调研

> 调研时间：2026-05-07 14:53（第二轮定时调研）
> 更新时间：2026-05-07 14:53

---

## 目录

1. [页面布局](#1-页面布局)
2. [样式设计](#2-样式设计)
3. [节点数据结构](#3-节点数据结构)
4. [数据库设计](#4-数据库设计)
5. [交互设计](#5-交互设计)
6. [性能优化](#6-性能优化)
7. [执行引擎](#7-执行引擎)
8. [ComfyUI 专项调研](#8-comfyui-专项调研)
9. [可直接落地的设计建议](#9-可直接落地的设计建议)

---

## 1. 页面布局

### 1.1 标准三栏布局（ComfyUI / Vue Flow 参考）

```
+---------------------------------------------------------------------+
|  顶部工具栏（Logo / 菜单 / 运行按钮 / 设置）                            |
+------------+--------------------------------+------------------------+
|            |                                |                        |
|  左侧面板   |        无限画布区域              |   右侧配置面板          |
|  节点分类   |   （可缩放/平移的节点编辑器）     |   节点属性配置          |
|  节点列表   |                                |                        |
|            |                                |                        |
+------------+--------------------------------+------------------------+
|  底部状态栏（队列 / 执行进度 / 缩放比例 / 小地图）                      |
+---------------------------------------------------------------------+
```

### 1.2 各区域功能定义

| 区域 | 位置 | 功能 | 状态 |
|------|------|------|------|
| 顶部工具栏 | 顶部固定 | Logo、菜单、运行/停止按钮、导入/导出 | 必需 |
| 左侧节点面板 | 左侧可折叠 | 节点分类树、搜索框、节点拖拽 | 必需 |
| 中央画布 | 主体区域 | 无限画布，支持缩放/平移/框选 | 核心 |
| 右侧属性面板 | 右侧可折叠 | 选中节点属性编辑、参数配置 | 必需 |
| 底部状态栏 | 底部固定 | 执行队列、进度条、小地图、缩放比例 | 推荐 |

### 1.3 响应式设计策略

**可直接参考的设计思路：**
- 移动端（<768px）：底部抽屉式面板替代左右侧栏
- 平板（768px-1024px）：单侧栏 + 浮动工具栏
- 桌面（>1024px）：完整三栏布局

**需改造的设计：**
- 桌面端三栏布局需要响应式收起/展开机制
- 触摸手势：双指缩放、单指平移、长按添加节点

### 1.4 多标签/多画布支持

**设计建议（可直接落地）：**
- 标签栏位于顶部工具栏下方
- 每个标签保存独立工作区状态（缩放比例、视口位置）
- 支持标签间拖拽节点
- 标签页右键菜单：关闭、关闭其他、导出当前

**参考实现：** VS Code 风格多标签页

---

## 2. 样式设计

### 2.1 节点外观设计

#### 节点结构

```
+-----------------------------+
|  ●  标题（节点类型名称）  [≡] |  <- 头部：图标 + 名称 + 菜单
+-----------------------------+
|  [输入端口]  输入参数          |  <- 身体：输入/输出端口 + 参数
|  [输入端口]  输入参数          |
+-----------------------------+
|  [输出端口]  输出参数          |
+-----------------------------+
```

#### 节点配色策略

| 节点类别 | 颜色方案 | 示例 |
|----------|----------|------|
| 触发器（Trigger） | 橙色 `#FF9800` | 开始按钮、定时器 |
| 检测器（Detector） | 蓝色 `#2196F3` | 目标检测、图像分类 |
| 处理器（Processor） | 绿色 `#4CAF50` | 图像处理、特征提取 |
| 动作（Action） | 红色 `#F44336` | 发送消息、执行命令 |
| 条件（Condition） | 紫色 `#9C27B0` | 分支判断、过滤 |

### 2.2 连线样式

**设计建议（可直接落地）：**

| 类型 | 适用场景 | 实现方式 |
|------|----------|----------|
| 贝塞尔曲线 | 通用连线 | Canvas quadraticCurveTo |
| 直线 | 简单连接 | Canvas lineTo |
| 直角（正交） | 流程图风格 | Canvas + 路由算法 |

**连线状态视觉反馈：**
- 默认：灰色细线
- 悬停：高亮加粗 + 动画
- 选中：青色 + 发光效果
- 执行中：流动动画
- 数据类型不匹配：红色虚线

### 2.3 暗色主题适配

**可直接参考的配色方案（ComfyUI 风格）：**
- 背景：`#1e1e1e`（深灰）
- 卡片：`#2d2d2d`（稍浅灰）
- 边框：`#3d3d3d`
- 文字：`#e0e0e0`
- 强调色：`#00bcd4`（青色）

---

## 3. 节点数据结构

### 3.1 节点定义

```typescript
// 节点定义
interface Node {
  id: string;                    // 唯一标识符
  type: string;                  // 节点类型名称
  position: { x: number; y: number };  // 画布坐标
  size?: { width: number; height: number };  // 节点尺寸
  inputs: Port[];                // 输入端口
  outputs: Port[];               // 输出端口
  data: Record<string, any>;     // 节点特定数据/参数
  widgets?: Widget[];            // 可编辑参数组件
  flags?: NodeFlags;             // 状态标记（collapsed/merged）
}

// 端口定义
interface Port {
  name: string;          // 端口名称
  type: string;          // 数据类型（IMAGE/BBOX/TRIGGER等）
  linked: boolean;       // 是否已连接
  multi: boolean;        // 是否支持多连接
}

// Widget（可编辑参数）
interface Widget {
  name: string;          // 参数名
  type: 'string' | 'number' | 'boolean' | 'select' | 'slider';
  value: any;
  options?: { min?: number; max?: number; step?: number };
}
```

### 3.2 边的数据结构

```typescript
// 边定义
interface Edge {
  id: string;                    // 唯一标识符
  source: string;                // 源节点 ID
  sourceHandle: string;           // 源端口名称
  target: string;                 // 目标节点 ID
  targetHandle: string;           // 目标端口名称
  type: string;                   // 连接数据类型
}

// ComfyUI 格式（特别推荐）
// links 对象：linkId -> [sourceId, sourceHandle, targetId, targetHandle, type]
interface ComfyUIWorkflow {
  version: string;
  nodes: Record<string, Node>;   // 节点字典
  links: Record<string, [string, string, string, string, string]>;  // 边
  config?: Record<string, any>;  // 配置
}
```

### 3.3 图的序列化格式

**ComfyUI JSON 格式（最佳参考）：**

```json
{
  "version": "0.4.2",
  "nodes": {
    "node_id_1": {
      "id": "node_id_1",
      "type": "ScreenCapture",
      "pos": [100, 200],
      "size": [200, 100],
      "flags": {},
      "order": 0,
      "outputs": [
        { "name": "IMAGE", "type": "IMAGE", "links": ["link_1"] }
      ],
      "inputs": {
        "prompt": { "name": "prompt", "type": "STRING", "link": null }
      },
      "widgets_data": ["1920x1080", 30, "image.png"]
    }
  },
  "links": {
    "link_1": ["node_id_1", 0, "node_id_2", 0, "IMAGE"]
  },
  "groups": {},
  "config": {},
  "extra": {}
}
```

**设计建议（可直接落地）：**
- 节点和边分开存储（类似 ComfyUI）
- 位置信息独立于节点定义
- 支持增量更新（diff 格式）

### 3.4 子图/嵌套图处理

**设计建议（需改造）：**
- 子图作为特殊节点类型封装
- 子图内部保持独立节点 ID 命名空间
- 支持递归展开/折叠
- 参考：Node-RED 的 Subflow 机制

---

## 4. 数据库设计

### 4.1 图数据持久化

**表结构设计建议：**

```sql
-- 图定义表
CREATE TABLE graphs (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT,
  data JSON NOT NULL,           -- 完整工作流 JSON
  version INTEGER DEFAULT 1,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  created_by TEXT,
  is_template BOOLEAN DEFAULT FALSE
);

-- 图版本历史
CREATE TABLE graph_versions (
  id TEXT PRIMARY KEY,
  graph_id TEXT REFERENCES graphs(id),
  version INTEGER NOT NULL,
  data JSON NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 执行记录
CREATE TABLE executions (
  id TEXT PRIMARY KEY,
  graph_id TEXT REFERENCES graphs(id),
  status TEXT NOT NULL,          -- pending/running/completed/failed
  started_at TIMESTAMP,
  completed_at TIMESTAMP,
  result JSON,                   -- 执行结果
  error_message TEXT
);
```

### 4.2 版本管理方案

**设计建议（可直接落地）：**
- Git-like 快照策略：每次保存创建新版本
- 增量 diff 可选存储（节省空间）
- 完整快照保证回滚可靠性
- 版本对比功能（可视化 diff）

### 4.3 执行记录存储

```sql
-- 节点执行记录
CREATE TABLE node_executions (
  id TEXT PRIMARY KEY,
  execution_id TEXT REFERENCES executions(id),
  node_id TEXT NOT NULL,
  status TEXT NOT NULL,
  input_data JSON,
  output_data JSON,
  started_at TIMESTAMP,
  completed_at TIMESTAMP,
  duration_ms INTEGER
);
```

---

## 5. 交互设计

### 5.1 拖拽节点到画布

**流程：**
1. 左侧面板节点列表，支持拖拽
2. 拖拽时显示半透明预览
3. 放置到画布时创建新节点
4. 自动分配唯一 ID

**代码实现思路：**
```typescript
// HTML5 Drag and Drop
nodeElement.addEventListener('dragstart', (e) => {
  e.dataTransfer.setData('nodeType', node.type);
});

canvas.addEventListener('drop', (e) => {
  const nodeType = e.dataTransfer.getData('nodeType');
  const position = screenToCanvas(e.clientX, e.clientY);
  createNode(nodeType, position);
});
```

### 5.2 节点连线

**交互流程：**
1. 鼠标悬停端口，显示连接预览
2. 拖拽创建临时连线
3. 悬停兼容端口时高亮提示
4. 释放时验证类型兼容性
5. 成功则创建永久边

**类型检查：**
```typescript
function canConnect(sourceType: string, targetType: string): boolean {
  const compatible = {
    'IMAGE': ['IMAGE'],
    'BBOX': ['BBOX', 'FILTER'],
    'TRIGGER': ['TRIGGER', 'ACTION'],
    // ...
  };
  return compatible[sourceType]?.includes(targetType) ?? false;
}
```

### 5.3 画布缩放/平移

**可直接参考的实现：**
- 缩放：鼠标滚轮 + Ctrl/Cmd
- 平移：鼠标中键拖拽 或 空格 + 左键拖拽
- 缩放范围：10% ~ 400%
- 双击节点：自动适应视口

### 5.4 多选/框选

**实现方式：**
- 框选：鼠标拖拽创建矩形选区
- 多选：Shift + 点击追加选择
- Ctrl + A：全选
- 选区内节点可批量移动/删除

### 5.5 撤销/重做

**Command Pattern 实现（可直接落地）：**
```typescript
interface Command {
  execute(): void;
  undo(): void;
}

class MoveNodeCommand implements Command {
  constructor(node, oldPos, newPos) { ... }
  execute() { this.node.position = this.newPos; }
  undo() { this.node.position = this.oldPos; }
}

// 维护 undo/redo 栈
const undoStack: Command[] = [];
const redoStack: Command[] = [];
```

### 5.6 快捷键支持

| 快捷键 | 功能 |
|--------|------|
| Ctrl + Z | 撤销 |
| Ctrl + Shift + Z | 重做 |
| Ctrl + A | 全选 |
| Ctrl + C | 复制 |
| Ctrl + V | 粘贴 |
| Delete | 删除选中 |
| Space + 拖拽 | 平移画布 |
| Ctrl + 滚轮 | 缩放 |
| F | 适应视口 |
| Ctrl + S | 保存 |

---

## 6. 性能优化

### 6.1 渲染技术选型

| 技术 | 适用场景 | 优点 | 缺点 |
|------|----------|------|------|
| SVG | <200 节点 | DOM 天然事件处理、样式灵活 | 节点多时性能差 |
| Canvas | 200-1000 节点 | 性能好、可精确控制 | 需要自己实现事件 |
| WebGL | >1000 节点 | GPU 加速 | 开发复杂 |
| Konva.js | 复杂交互 | Canvas + 事件封装 | 包体积大 |

**设计建议：**
- <500 节点：SVG（Vue Flow/React Flow）
- >500 节点：Canvas 或 Konva.js
- CogniFlow 目标用户场景：优先考虑 Canvas 实现

### 6.2 视口裁剪（Viewport Culling）

**原理：** 只渲染可见区域内的节点

```typescript
function getVisibleNodes(viewport, allNodes) {
  const { x, y, width, height, scale } = viewport;
  return allNodes.filter(node => {
    const [nx, ny] = node.position;
    const [nw, nh] = node.size || [200, 100];
    return (
      nx + nw > x / scale &&
      nx < (x + width) / scale &&
      ny + nh > y / scale &&
      ny < (y + height) / scale
    );
  });
}
```

**效果：** 大型图（500+ 节点）可减少 99% DOM 操作

### 6.3 虚拟化渲染

**分块加载策略：**
- 将画布划分为固定大小的块
- 只加载视口周围 N 个块
- 滚动时动态加载/卸载块

### 6.4 脏标记重绘（Dirty Flag）

```typescript
let needsRedraw = false;

function markDirty() {
  needsRedraw = true;
}

function renderLoop() {
  if (needsRedraw) {
    renderCanvas();
    needsRedraw = false;
  }
  requestAnimationFrame(renderLoop);
}
```

### 6.5 Web Workers

**适用场景：**
- 拓扑排序计算
- 路径规划（连线路由）
- 大型图布局计算
- 数据序列化/反序列化

### 6.6 性能基准参考

| 节点数量 | 技术方案 | 帧率目标 |
|----------|----------|----------|
| <100 | SVG | 60fps |
| 100-500 | SVG + 视口裁剪 | 30-60fps |
| 500-1000 | Canvas | 30fps |
| >1000 | Canvas + LOD | 30fps |

---

## 7. 执行引擎

### 7.1 图的遍历方式

**拓扑排序（Kahn 算法）：**

```python
def topological_sort(nodes, edges):
    in_degree = {n: 0 for n in nodes}
    adj_list = {n: [] for n in nodes}
    
    for src, tgt in edges:
        in_degree[tgt] += 1
        adj_list[src].append(tgt)
    
    queue = [n for n in nodes if in_degree[n] == 0]
    result = []
    
    while queue:
        node = queue.pop(0)
        result.append(node)
        for neighbor in adj_list[node]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)
    
    return result
```

### 7.2 执行层级

```typescript
function computeExecutionLevels(nodes, edges) {
  const levels = new Map<string, number>();
  
  function getLevel(nodeId: string): number {
    if (levels.has(nodeId)) return levels.get(nodeId)!;
    
    const deps = getDependencies(nodeId, edges);
    if (deps.length === 0) {
      levels.set(nodeId, 0);
      return 0;
    }
    
    const level = Math.max(...deps.map(d => getLevel(d))) + 1;
    levels.set(nodeId, level);
    return level;
  }
  
  nodes.forEach(n => getLevel(n.id));
  return levels;
}
```

### 7.3 并行执行

**同层节点可并行执行：**
```typescript
async function executeLevel(level, nodes) {
  const promises = nodes.map(n => executeNode(n));
  await Promise.all(promises);
}

// 按层级顺序执行，层级内并行
for (const [level, nodes] of Object.entries(groupedByLevel)) {
  await executeLevel(level, nodes);
}
```

### 7.4 断点/调试支持

**设计建议：**
- 节点支持设置断点
- 断点触发时暂停执行
- 显示当前节点输入/输出数据
- 支持单步执行（跳到下一个依赖节点）

### 7.5 执行状态管理

```typescript
interface ExecutionState {
  status: 'idle' | 'running' | 'paused' | 'completed' | 'failed';
  currentNode?: string;
  completedNodes: Set<string>;
  nodeResults: Map<string, any>;
  error?: string;
}
```

---

## 8. ComfyUI 专项调研

### 8.1 ComfyUI 前端架构

**技术栈（重要发现）：**
- **渲染引擎：自研 Canvas 实现**（非 React Flow / Vue Flow）
- 原因：完全控制性能、避免虚拟 DOM 开销、特殊交互需求
- 这与 CogniFlow 的需求高度匹配！

**自研 Canvas 的优势：**
- 精细的节点控制
- 自定义连线路由算法
- 优化的性能策略
- 完全按需渲染

### 8.2 ComfyUI 数据结构

```typescript
// ComfyUI Node
interface ComfyNode {
  id: string;
  type: string;
  pos: [number, number];
  size: [number, number];
  flags: Record<string, boolean>;
  order: number;
  outputs: Array<{
    name: string;
    type: string;
    links: string[];     // 连接的 link IDs
  }>;
  inputs: Record<string, {
    name: string;
    type: string;
    link: string | null;  // 连接到此输入的 link ID
  }>;
  widgets_data: any[];   // 可编辑参数的值
}

// ComfyUI Link
// [sourceId, sourceOutputIndex, targetId, targetInputIndex, type]
type ComfyLink = [string, number, string, number, string];

// ComfyUI Workflow
interface ComfyWorkflow {
  version: string;
  nodes: Record<string, ComfyNode>;
  links: Record<string, ComfyLink>;  // linkId -> ComfyLink
}
```

### 8.3 ComfyUI 节点类型系统

**核心类型：**
| 类型 | 说明 | 示例节点 |
|------|------|----------|
| IMAGE | 图像数据 | LoadImage, SaveImage |
| LATENT | 潜空间数据 | VAEEncode, VAEDecode |
| MODEL | 模型权重 | CheckpointLoader, UNET |
| CONDITIONING | 条件文本 | CLIPTextEncode |
| CONTROL_NET | 控制网 | ControlNetApply |
| MASK | 蒙版 | BoxMask, Segments |
| BBOX | 边界框 | BboxDetection |

**CogniFlow 可映射：**
| ComfyUI 类型 | CogniFlow 类型 |
|--------------|----------------|
| IMAGE | Frame（视频帧） |
| BBOX | Detection（检测结果） |
| MODEL | Model（模型权重） |
| MASK | Region（区域） |
| CONDITIONING | Rule（规则条件） |

### 8.4 ComfyUI 连接类型检查

```typescript
// 类型兼容性检查
const typeHierarchy = {
  'IMAGE': ['IMAGE'],
  'MASK': ['MASK'],
  'BBOX': ['BBOX'],
  'ANY': ['*'],  // 通配符
};

// 检查输出类型是否兼容输入类型
function canConnect(outputType: string, inputType: string): boolean {
  if (outputType === 'ANY' || inputType === 'ANY') return true;
  return typeHierarchy[outputType]?.includes(inputType) ?? false;
}
```

### 8.5 ComfyUI 执行调度

**Kahn 算法拓扑排序：**
1. 计算所有节点的入度
2. 入度为 0 的节点入队（起始节点）
3. 依次出队执行，执行后更新依赖节点入度
4. 新入度为 0 的节点入队
5. 重复直到队列为空

**并行执行：**
- 同层（同一 topological level）的节点可并行
- 使用 Promise.all 等待一层完成
- 然后执行下一层

### 8.6 ComfyUI 缓存机制

**多级缓存：**
1. **执行结果缓存**：节点输出结果缓存
2. **模型缓存**：LRU 内存缓存 + 磁盘缓存
3. **图片缓存**：已处理图像缓存

```typescript
class CacheManager {
  private memoryCache: LRU<string, any>;
  private diskCache: DiskCache;
  
  async get(key: string): Promise<any> {
    // 先查内存
    if (this.memoryCache.has(key)) {
      return this.memoryCache.get(key);
    }
    // 再查磁盘
    if (await this.diskCache.has(key)) {
      const value = await this.diskCache.get(key);
      this.memoryCache.set(key, value);
      return value;
    }
    return null;
  }
}
```

### 8.7 ComfyUI 后端 API

**FastAPI 技术栈：**

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/prompt` | POST | 提交工作流执行 |
| `/api/queue` | GET | 获取队列状态 |
| `/api/history` | GET | 获取执行历史 |
| `/api/view` | GET | 获取图片/结果 |
| `/api/system_stats` | GET | 系统状态 |

**执行流程：**
```
客户端 POST /api/prompt 
  → 服务器入队
  → WebSocket 推送 "executing"
  → 执行节点（拓扑排序 + 并行）
  → WebSocket 推送进度
  → 执行完成，WebSocket 推送 " executed"
  → 客户端获取结果 /api/view
```

### 8.8 ComfyUI 界面布局

```
+------------------------------------------------------------------+
|  ComfyUI  ●  [Queue Size: 0]  [Clear]  [View Queue]  [Running...] |
+--------+----------------------------------------------+-----------+
| GROUPS |                                              | OBJECT    |
| SEARCH |                                              | INFO      |
| ....   |                                              | ..........|
| ....   |         CANVAS                              | ..........|
|        |                                              | ..........|
| NODE   |                                              | ..........|
| TREE   |                                              | ..........|
| ....   |                                              | ..........|
|        |                                              | ..........|
+--------+----------------------------------------------+-----------+
|  Progress: [==========                    ] 45%  | Min: [+]   |
+------------------------------------------------------------------+
```

**CogniFlow 可直接参考的布局：**
- 左侧：节点分类树（可折叠）
- 中央：Canvas 画布
- 右侧：选中节点信息/配置
- 底部：进度条 + 小地图

---

## 9. 可直接落地的设计建议

### 9.1 架构选型

| 决策点 | 推荐方案 | 理由 |
|--------|----------|------|
| 前端框架 | Vue 3 + TypeScript | 已有 Vue3 前端 |
| 画布渲染 | 自研 Canvas | 参考 ComfyUI，完全控制性能 |
| 状态管理 | Pinia | Vue 3 官方推荐 |
| 图数据库 | 关系型 JSON 存储 | 简单够用，后续可迁移 |

### 9.2 核心数据结构

**可直接使用的 JSON 结构（参考 ComfyUI）：**

```typescript
interface CogniFlowWorkflow {
  version: string;
  nodes: Record<string, CogniNode>;
  links: Record<string, [string, string, string, string, string]>;
}

interface CogniNode {
  id: string;
  type: NodeType;  // 'trigger' | 'detector' | 'processor' | 'action' | 'condition'
  pos: [number, number];
  size?: [number, number];
  outputs: Array<{ name: string; type: string; links: string[] }>;
  inputs: Record<string, { name: string; type: string; link: string | null }>;
  widgets_data: any[];
}
```

### 9.3 执行引擎设计

**可直接参考的流程：**
1. Kahn 算法拓扑排序
2. 按层级执行，层级内并行 Promise.all
3. WebSocket 实时推送执行进度
4. 节点结果缓存（内存 + 磁盘）

### 9.4 性能优化策略

**分阶段实施：**
1. Phase 1（<200 节点）：Canvas 实现 + 脏标记重绘
2. Phase 2（200-500 节点）：视口裁剪
3. Phase 3（>500 节点）：Web Workers 布局计算 + LOD

### 9.5 界面布局建议

**立即可用的布局：**
```
+------------------------------------------------------------------+
|  [Logo] 规则引擎  [导入] [导出] [▶ 运行] [■ 停止]     [设置]       |
+--------+----------------------------------------------+-----------+
| 触发器 |                                              | 节点配置   |
|  检测  |                                              | ..........|
|  处理  |            无限画布 Canvas                    | ..........|
|  动作  |                                              | ..........|
|  条件  |                                              | ..........|
+--------+----------------------------------------------+-----------+
|  [队列: 0]  [进度 ████░░░░░░ 35%]  [缩放: 100%]  [小地图]         |
+------------------------------------------------------------------+
```

---

## 参考资料

1. [ComfyUI GitHub](https://github.com/comfyanonymous/ComfyUI)
2. [ComfyUI 文档](https://docs.comfy.org/)
3. [Node-RED 官方文档](https://nodered.org/)
4. [Vue Flow](https://vueflow.dev/)
5. [React Flow](https://reactflow.dev/)
6. [Konva.js](https://konvajs.org/)
7. [无限画布优化研究](./infinite-canvas-optimization.md)
8. [Node-RED 架构分析](./node-red-editor-architecture.md)
9. [节点图数据结构设计](./node-graph-data-structure-design.md)
