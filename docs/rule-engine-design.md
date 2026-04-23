# VisionGame 可视化规则引擎设计文档

## 1. 概述

### 1.1 项目目标

设计一款可视化规则引擎，对接 VisionGame 项目，实现基于 YOLO 识别结果触发复杂多变的处理规则。参考 Dify、Blender Node Editor、Unity Visual Scripting、Node-RED 等成熟节点工具的设计理念。

### 1.2 核心需求

```
最终目标: YOLO 检测 → 触发复杂业务规则 → 执行动作

示例场景:
- 检测到 "开始按钮" → 等待 2 秒 → 点击按钮
- 检测到 "血量条" + 血量 < 20% → 发送 HTTP 告警 → 自动喝药
- 检测到 "敌人" + 距离 < 100px → 按下 A 键 → 连续按 3 次
```

---

## 2. 技术架构

### 2.1 系统架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                        前端 (Vue3 + TypeScript)                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  节点编辑器   │  │  节点面板    │  │  调试面板    │          │
│  │  (Canvas)    │  │  (Node List) │  │  (Console)   │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└────────────────────────────┬────────────────────────────────────┘
                             │ WebSocket / HTTP
┌────────────────────────────▼────────────────────────────────────┐
│                        后端 (FastAPI)                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  规则引擎     │  │  执行引擎    │  │  检测服务    │          │
│  │  (Graph)     │  │  (Executor)  │  │  (Detector)  │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                     VisionGame Core                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  YOLO 检测   │  │  输入模拟    │  │  数据输入    │          │
│  │  (Detector)  │  │  (Control)  │  │  (Capture)  │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 前端技术栈

- **构建工具**: Vite 8.x
- **框架**: Vue 3.4+ (Composition API)
- **语言**: TypeScript 5.3+
- **状态管理**: Pinia
- **节点编辑器**: Vue Flow (React Flow 的 Vue3 移植版本)
- **UI 组件**: Element Plus 2.5+
- **样式**: UnoCSS (沿用现有配置)

### 2.3 后端技术栈

- **框架**: FastAPI
- **节点执行**: 异步图遍历 + 线程池并发执行
- **持久化**: SQLite (复用现有数据库)
- **实时通信**: WebSocket
- **依赖注入**: 异步任务队列 (asyncio)

### 2.4 技术选型详细对比

#### 2.4.1 节点编辑器方案对比

| 方案 | React Flow 12.x | Vue Flow 1.x | 自研 Canvas | 说明 |
|------|-----------------|--------------|-------------|------|
| **最新版本** | 12.10.2 (2026-03) | 1.48.2 (2026-03) | - | 两项目同步更新，共享同一核心 |
| **维护状态** | 活跃 (2024-2025 持续更新) | 活跃 (与 React Flow 同步) | 需要团队自行维护 | Vue Flow 是 React Flow 的 Vue 移植版 |
| **自定义程度** | 高 | 高 | 最高 | 自研可完全控制，但开发成本大 |
| **性能** | 优 (WebGL 渲染) | 优 (WebGL 渲染) | 依赖实现 | 12.x 版本优化了大图渲染性能 |
| **生态系统** | 丰富 (插件、主题、Pro版) | 中等 | 无 | React Flow 企业用户多，生态成熟 |
| **学习成本** | 中 | 中 | 高 | 自研需要深入理解 Canvas API |
| **与 Vue3 集成** | 需 wrapper | 原生 | 原生 | Vue Flow 与 Vue3 响应式系统无缝集成 |
| **SSR/SSG 支持** | 原生支持 | Vue 3 原生支持 | 自实现 | 两框架均支持 |

**推荐方案**: Vue Flow 1.x (与 React Flow 12.x 同步更新)

**选型理由**:
1. Vue3 原生支持，与现有项目技术栈一致
2. WebGL 渲染支持大规模节点图性能优化
3. 内置 MiniMap、Controls、Background、Node Toolbar 等组件
4. 支持自定义节点、边、连接桩、slots
5. 活跃的社区和持续的版本更新 (每月约 2-3 个版本)
6. TypeScript 类型完善，API 设计现代
7. 支持 Sub Flows、Multiplayer、Whiteboard 等高级功能

#### 2.4.1.1 Vue Flow 1.x / React Flow 12.x 最新特性 (2025-2026)

根据官方文档和发布记录，最新版本核心特性：

**渲染性能优化**:
- `shallowRef` 支持：避免深度响应式开销，使用 `shallowRef` 存储节点和边
- 虚拟化渲染：仅渲染视口内可见节点，大幅降低 DOM 节点数量
- 边的动画优化：默认禁用边动画，使用 `smoothstep` 边类型替代贝塞尔曲线
- MiniMap 优化：支持自定义样式和节点过滤

**状态管理最佳实践**:
```typescript
// ❌ 不推荐：在组件内直接访问 nodes 数组
const nodes = useStore((state) => state.nodes);
const selectedNodeIds = nodes.filter((node) => node.selected).map((node) => node.id);

// ✅ 推荐：使用独立的选择状态字段
const selectedNodeIds = useStore((state) => state.selectedNodeIds);
```

**节点折叠优化**:
```typescript
// 使用 hidden 属性动态折叠大型节点树
const handleNodeClick = (targetNode) => {
  if (targetNode.data.children) {
    setNodes((prevNodes) =>
      prevNodes.map((node) =>
        targetNode.data.children.includes(node.id)
          ? { ...node, hidden: !node.hidden }
          : node
      )
    );
  }
};
```

**Multiplayer 实时协作**:
- 支持多人同时编辑同一画布
- 内置 WebSocket 状态同步
- 光标位置和节点锁定机制

**Whiteboard 白板功能**:
- Free-form 拖拽和绘制
- 无限画布支持
- 钉选和注释

#### 2.4.2 执行引擎架构对比

| 架构模式 | 描述 | 适用场景 | 性能 | 复杂度 |
|---------|------|---------|------|-------|
| **同步 DFS** | 深度优先同步执行 | 简单规则、小规模图 | 中 | 低 |
| **异步事件驱动** | 基于 asyncio 事件循环 | 中等复杂度 | 高 | 中 |
| **线程池并发** | 多线程并行执行独立分支 | 多分支并行、CPU密集 | 最高 | 高 |
| **进程池分离** | 子进程执行隔离任务 | Python 代码执行、安全隔离 | 高 | 高 |

#### 2.4.3 竞品分析: Dify 架构参考

Dify 作为 LLM 应用开发平台，其节点编排设计值得参考：

| 特性 | Dify | 本设计 | 说明 |
|------|------|--------|------|
| 节点类型 | 应用节点、LLM 节点、工具节点 | 触发器、条件、动作、逻辑 | Dify 更偏重 LLM，本设计偏重游戏自动化 |
| 执行模型 | DAG + 异步执行 | DAG + 线程池并发 | 架构相似 |
| 状态管理 | 应用级上下文 | 执行上下文 | 设计一致 |
| API 设计 | REST + WS | REST + WebSocket | 一致 |
| 扩展方式 | 插件系统 | 节点执行器注册 | 本设计更轻量 |

**Dify 关键启发**:
1. 节点定义与执行器分离，便于扩展
2. 支持变量插值和模板渲染
3. 执行日志详细，便于调试
4. 支持版本管理和回滚

#### 2.4.3.1 Dify 最新架构设计 (2024-2025)

根据 Dify 官方文档，其工作流架构核心概念：

**两种工作流模式**:
- **Workflow**: 运行一次从开始到结束，适合自动化报告生成、数据处理流水线
- **Chatflow**: 支持多轮对话交互，适合客服机器人、助手类应用

**节点分类体系**:
- **Logic**: 条件分支、变量赋值、迭代器
- **AI**: LLM 调用、意图识别
- **Tools**: HTTP 请求、代码执行、知识库检索
- **Knowledge**: 知识库节点
- **Media**: 图片生成、图片理解、音频处理
- **Files**: 文件处理节点

**执行模型特点**:
- 基于状态机的工作流执行
- 支持节点级别的重试和超时配置
- 执行历史完整记录，支持回滚
- 断点调试和单步执行支持

**与本设计对应关系**:
| Dify 概念 | 本设计对应 | 说明 |
|-----------|-----------|------|
| LLM Node | 执行Python节点 | 代码执行能力 |
| HTTP Request | 发送HTTP节点 | 外部 API 调用 |
| Conditional Branch | 条件分支节点 | 逻辑分支 |
| Variable Assignment | 变量设置节点 | 状态管理 |
| Template | 模板渲染节点 | 字符串模板 |

#### 2.4.4 竞品分析: Node-RED 优化参考

Node-RED 的执行引擎优化方案：

| 优化点 | Node-RED 方案 | 本设计采用 | 说明 |
|--------|--------------|-----------|------|
| 消息流控制 | 消息队列 + 背压 | asyncio.Queue | 架构一致 |
| 并发控制 | 线程池 (可配置) | ThreadPoolExecutor | 本设计更灵活 |
| 子流程 | Subflow 复用 | 分组节点 | 设计一致 |
| 性能监控 | 运行时统计 | 待实现 | 计划 Phase 4 |

**Node-RED 关键启发**:
1. 节点间消息传递采用队列，避免阻塞
2. 支持消息重试和死信队列
3. 运行时可动态修改节点配置
4. 丰富的社区节点库

#### 2.4.4.1 Node-RED 执行引擎优化方案

**消息队列与背压控制**:
```
Node-RED 使用 internal:wire for wire connections,消息通过队列传递
当节点处理速度低于接收速度时，队列积压触发背压
可配置队列大小和溢出处理策略
```

**节点执行策略**:
- **Automatic**: 收到消息立即处理
- **Manual**: 等待显式触发
- **Hybrid**: 支持两种模式切换

**线程池配置**:
```javascript
// nodes/settings.js
module.exports = {
  // 节点执行线程池大小
  nodeThreadPoolSize: 10,
  // 消息队列默认大小
  messageQueueDepth: 1000,
  // 超时默认时间(ms)
  defaultTimeout: 30000
}
```

**性能监控指标**:
- 节点执行时间
- 消息队列深度
- 内存使用量
- 线程池利用率

---

## 3. 节点类型设计

### 3.1 节点分类

```
┌────────────────────────────────────────────────────────────────┐
│                       节点分类体系                               │
├────────────────────────────────────────────────────────────────┤
│  1. 触发器 (Trigger)      - 规则执行的起点                       │
│  2. 条件 (Condition)      - 逻辑判断与过滤                       │
│  3. 动作 (Action)         - 执行具体操作                        │
│  4. 逻辑 (Logic)          - 控制流与循环                        │
│  5. 工具 (Utility)        - 辅助功能                            │
└────────────────────────────────────────────────────────────────┘
```

### 3.2 节点详细定义 (实际实现)

#### 3.2.1 触发器节点 (Trigger) ✅ 已实现

| 节点类型标识 | 显示名称 | 功能描述 | 输出端口 | 配置参数 |
|------------|---------|---------|---------|---------|
| `yolo_trigger` | YOLO 触发器 | 当检测到指定目标时触发 | `triggered`, `detections` | `class_names`, `min_confidence`, `max_objects` |
| `timer_trigger` | 定时器触发器 | 按固定时间间隔触发 | `triggered`, `timestamp` | `interval`, `enabled` |
| `manual_trigger` | 手动触发器 | 手动触发规则执行 | `triggered` | - |

#### 3.2.2 条件节点 (Condition) ✅ 已实现

| 节点类型标识 | 显示名称 | 功能描述 | 输入端口 | 输出端口 | 配置参数 |
|------------|---------|---------|---------|---------|---------|
| `object_exists_condition` | 目标存在 | 检查是否检测到指定目标 | `detections` | `true`, `false` | `class_names`, `min_count`, `comparison` |
| `confidence_threshold_condition` | 置信度阈值 | 检查检测置信度是否满足要求 | `detections` | `true`, `false` | `min_confidence` |
| `variable_condition` | 变量条件 | 检查变量的值是否满足条件 | - | `true`, `false` | `variable_name`, `expected_value`, `comparison` |

#### 3.2.3 动作节点 (Action) ✅ 已实现

| 节点类型标识 | 显示名称 | 功能描述 | 输入端口 | 输出端口 | 配置参数 |
|------------|---------|---------|---------|---------|---------|
| `keyboard_action` | 键盘动作 | 模拟键盘按键 | `trigger` | `next` | `keys`, `hold_duration`, `interval` |
| `mouse_action` | 鼠标动作 | 模拟鼠标操作 | `trigger` | `next` | `action`, `x`, `y`, `button`, `scroll_amount` |
| `wait_action` | 等待 | 等待指定时间 | `trigger` | `next` | `duration` |
| `http_request_action` | HTTP 请求 | 发送 HTTP 请求 | `trigger` | `next`, `response` | `url`, `method`, `headers`, `body`, `timeout` |
| `log_action` | 日志 | 记录日志信息 | `trigger` | `next` | `message`, `level` |

#### 3.2.4 逻辑节点 (Logic) ✅ 已实现

| 节点类型标识 | 显示名称 | 功能描述 | 输入端口 | 输出端口 | 配置参数 |
|------------|---------|---------|---------|---------|---------|
| `branch` | 分支 | 根据条件选择执行分支 | `input`, `condition` | `true`, `false` | - |
| `parallel_branch` | 并行分支 | 同时执行多个分支 | `trigger` | `branch_1~3`, `completed` | `max_concurrent` |
| `loop` | 循环 | 循环执行节点 | `trigger` | `iteration`, `completed` | `max_iterations`, `continue_on_error` |
| `delay` | 延迟 | 延迟后继续执行 | `input` | `output` | `delay` |
| `set_variable` | 设置变量 | 设置执行上下文中的变量 | `trigger` | `next` | `variable_name`, `value`, `value_type` |

#### 3.2.5 待实现节点 (规划中)

| 节点类型标识 | 显示名称 | 功能描述 | 说明 |
|------------|---------|---------|------|
| `websocket_trigger` | WebSocket 触发器 | 接收外部消息触发 | 待实现 |
| `http_trigger` | HTTP 触发器 | 接收 HTTP 请求触发 | 待实现 |
| `object_not_exists_condition` | 目标不存在 | 检查是否不存在指定目标 | 待实现 |
| `region_condition` | 区域判断 | 目标是否在指定区域内 | 待实现 |
| `expression_condition` | 表达式条件 | 自定义条件表达式 | 待实现 |
| `python_code_action` | 执行 Python | 执行自定义 Python 代码 | 待实现 |
| `websocket_action` | 发送 WebSocket | 发送 WebSocket 消息 | 待实现 |
| `timeout_logic` | 超时 | 设置节点执行超时 | 待实现 |
| `priority_queue_logic` | 优先级队列 | 按优先级顺序执行 | 待实现 |
| `variable_get` | 变量获取 | 获取上下文变量 | 待实现 |
| `data_transform` | 数据转换 | 转换数据结构 | 待实现 |
| `template_render` | 模板渲染 | 渲染字符串模板 | 待实现 |
| `coordinate_transform` | 坐标转换 | 转换检测框坐标 | 待实现 |

### 3.3 节点数据结构

```typescript
// ============================================
// 核心类型定义
// ============================================

// 节点分类枚举
type NodeCategory = 'trigger' | 'condition' | 'action' | 'logic' | 'utility';

// 端口类型枚举
type PortType = 'trigger' | 'data' | 'boolean' | 'control';

// 配置字段类型
type ConfigFieldType = 'string' | 'number' | 'boolean' | 'select' | 'code' | 'expression' | 'json';

// 节点执行状态
type NodeStatus = 'idle' | 'running' | 'success' | 'failed' | 'skipped';

// ============================================
// 节点定义
// ============================================

/**
 * 节点定义 - 描述节点类型的元数据
 */
interface NodeDefinition {
  type: string;                    // 节点类型标识 (唯一)
  category: NodeCategory;           // 节点分类
  name: string;                     // 显示名称
  description: string;              // 节点描述
  icon?: string;                    // 图标名称 (可选)
  inputs: PortDefinition[];         // 输入端口列表
  outputs: PortDefinition[];        // 输出端口列表
  config: ConfigField[];            // 配置字段列表
  defaultConfig: Record<string, unknown>;  // 默认配置值
  // Vue Flow 特定配置
  vueFlow?: {
    template?: string;             // Vue 模板字符串
    style?: Record<string, string>; // 节点样式
    class?: string;                // 节点类名
  };
}

/**
 * 端口定义 - 描述节点的输入/输出端口
 */
interface PortDefinition {
  id: string;                       // 端口标识 (唯一)
  name: string;                     // 端口名称 (显示用)
  type: PortType;                   // 端口类型
  description?: string;              // 端口描述 (tooltip)
  required?: boolean;               // 是否必填 (仅对输入端口有效)
  defaultValue?: unknown;           // 默认值 (仅对输入端口有效)
  // 条件端口的关联字段
  conditionField?: string;          // 关联的条件字段名
}

/**
 * 配置字段 - 节点配置面板中的字段定义
 */
interface ConfigField {
  id: string;                       // 配置项标识
  name: string;                     // 配置项名称 (显示用)
  type: ConfigFieldType;           // 配置项类型
  default: unknown;                 // 默认值
  options?: SelectOption[];         // 下拉选项 (select 类型用)
  required?: boolean;               // 是否必填
  validation?: ValidationRule;     // 验证规则
  placeholder?: string;             // 占位文本
  tooltip?: string;                 // 提示信息
  hidden?: ConditionalDisplay;     // 条件显示
  // 高级配置
  advanced?: boolean;               // 是否为高级选项
  group?: string;                   // 配置分组
}

/**
 * 下拉选项
 */
interface SelectOption {
  label: string;                   // 显示文本
  value: unknown;                   // 值
  description?: string;             // 选项描述
}

/**
 * 验证规则
 */
interface ValidationRule {
  pattern?: string;                 // 正则表达式
  min?: number;                     // 最小值 (number 类型)
  max?: number;                     // 最大值 (number 类型)
  maxLength?: number;               // 最大长度 (string 类型)
  custom?: string;                  // 自定义验证函数名
  errorMessage?: string;            // 错误提示信息
}

/**
 * 条件显示配置
 */
interface ConditionalDisplay {
  field: string;                    // 依赖的字段名
  operator: 'eq' | 'neq' | 'in' | 'nin' | 'exists';  // 操作符
  value?: unknown;                  // 期望值
}

// ============================================
// Vue Flow 特定类型
// ============================================

import type { Node, Edge, Connection, XYPosition, Viewport } from '@vue-flow/core';
import type { Component } from 'vue';

/**
 * Vue Flow 节点数据
 */
interface FlowNodeData {
  definition: NodeDefinition;       // 节点定义
  config: Record<string, unknown>;  // 用户配置
  label?: string;                   // 自定义标签
  // 运行时状态
  runtime?: {
    status: NodeStatus;
    error?: string;
    lastExecution?: number;
    outputData?: unknown;
  };
}

/**
 * Vue Flow 节点
 */
type FlowNode = Node<FlowNodeData>;

/**
 * 自定义节点组件类型
 */
type CustomNodeComponent = Component<{
  id: string;
  data: FlowNodeData;
  selected: boolean;
  dragging: boolean;
}>;

/**
 * Vue Flow 边
 */
interface FlowEdge extends Edge {
  sourcePort: string;               // 源端口 ID
  targetPort: string;               // 目标端口 ID
  edgeType?: 'trigger' | 'data' | 'boolean';
}

/**
 * Vue Flow 连接 (拖拽时)
 */
type FlowConnection = Connection & {
  sourcePort?: string;
  targetPort?: string;
};

/**
 * 边样式选项
 */
interface EdgeStyleOptions {
  stroke?: string;
  strokeWidth?: number;
  animated?: boolean;
  dashArray?: string;
  label?: string;
}

/**
 * 节点位置信息 (带尺寸)
 */
interface NodePosition extends XYPosition {
  width?: number;
  height?: number;
}

// ============================================
// 规则图类型
// ============================================

/**
 * 规则图 - 完整的图结构
 */
interface RuleGraph {
  id: string;                       // 图唯一标识
  name: string;                    // 图名称
  description?: string;             // 图描述
  nodes: FlowNode[];                // 节点列表
  edges: FlowEdge[];                // 连接列表
  variables: VariableDefinition[];  // 全局变量
  metadata: GraphMetadata;         // 元数据
  // Vue Flow 布局信息
  viewport?: ViewportState;
}

/**
 * 视口状态 (保存画布缩放和位置)
 */
interface ViewportState {
  x: number;
  y: number;
  zoom: number;
}

/**
 * 图节点 - 画布上的节点实例
 */
interface GraphNode {
  id: string;                       // 节点唯一标识
  type: string;                     // 节点类型
  position: XYPosition;             // 画布位置 { x, y }
  label?: string;                   // 自定义标签
  config: Record<string, unknown>;  // 节点配置
}

/**
 * 图连接 - 节点间的连接
 */
interface GraphEdge {
  id: string;                       // 连接唯一标识
  source: string;                   // 源节点 ID
  sourcePort: string;               // 源端口 ID
  target: string;                   // 目标节点 ID
  targetPort: string;               // 目标端口 ID
  type?: 'trigger' | 'data' | 'boolean';
  // 边的样式配置
  style?: EdgeStyleOptions;
}

/**
 * 变量定义
 */
interface VariableDefinition {
  key: string;                      // 变量名
  type: 'string' | 'number' | 'boolean' | 'object' | 'array';
  defaultValue?: unknown;           // 默认值
  description?: string;            // 变量描述
}

/**
 * 元数据
 */
interface GraphMetadata {
  version: string;                  // 图版本
  createdAt: string;                // 创建时间
  updatedAt: string;                // 更新时间
  author?: string;                  // 作者
  tags?: string[];                 // 标签
  // 统计信息
  stats?: {
    nodeCount: number;
    edgeCount: number;
    executionCount: number;
  };
}

// ============================================
// 执行上下文类型
// ============================================

/**
 * 执行上下文 - 图执行时的运行时状态
 */
interface ExecutionContext {
  graphId: string;                  // 执行的图 ID
  executionId: string;              // 执行实例 ID
  variables: Record<string, unknown>;  // 变量快照
  detections: Detection[];         // 当前检测结果
  nodeStates: Record<string, NodeRuntimeState>;  // 节点状态
  startTime: number;                // 开始时间戳 (Unix ms)
  logs: ExecutionLog[];             // 执行日志
  // 调试支持
  debug?: {
    stepMode: boolean;
    breakpoints: Set<string>;
    currentNode?: string;
  };
}

/**
 * 节点运行时状态
 */
interface NodeRuntimeState {
  status: NodeStatus;
  startTime?: number;
  endTime?: number;
  error?: string;
  inputData?: unknown;
  outputData?: unknown;
}

/**
 * 检测结果 (对接 YOLO)
 */
interface Detection {
  bbox: [number, number, number, number];  // x1, y1, x2, y2
  score: number;                   // 置信度 (0-1)
  label: string;                  // 类别名称
  labelId: number;                // 类别 ID
  timestamp: number;              // 检测时间戳
  // 扩展字段
  classId?: number;
  mask?: number[][];              // 分割掩码 (可选)
  features?: number[];            // 特征向量 (可选)
}

/**
 * 执行日志
 */
interface ExecutionLog {
  timestamp: number;
  level: 'debug' | 'info' | 'warning' | 'error';
  nodeId?: string;
  nodeName?: string;
  message: string;
  data?: unknown;
}

// ============================================
// API 请求/响应类型
// ============================================

/**
 * 创建规则图请求
 */
interface CreateGraphRequest {
  name: string;
  description?: string;
  variables?: VariableDefinition[];
}

/**
 * 更新规则图请求
 */
interface UpdateGraphRequest {
  name?: string;
  description?: string;
  nodes?: FlowNode[];
  edges?: FlowEdge[];
  variables?: VariableDefinition[];
}

// ============================================
// API 请求/响应类型 (与后端 schemas.py 对应)
// ============================================

/**
 * 创建规则图请求
 */
interface CreateRuleGraphRequest {
  name: string;
  description?: string;
  nodes_json?: string;      // JSON 字符串
  edges_json?: string;      // JSON 字符串
  variables_json?: string;  // JSON 字符串
  version?: string;
  is_active?: boolean;
}

/**
 * 更新规则图请求
 */
interface UpdateRuleGraphRequest {
  name?: string;
  description?: string;
  nodes_json?: string;
  edges_json?: string;
  variables_json?: string;
  is_active?: boolean;
  thumbnail?: string;        // Base64 缩略图 (实际实现新增)
}

/**
 * 执行请求 (实际实现)
 */
interface ExecuteGraphRequest {
  graph_id: number;
  trigger_type?: string;      // yolo/timer/manual/http
  trigger_data?: object;      // 触发时的数据
}

/**
 * 执行响应 (实际实现)
 */
interface ExecuteGraphResponse {
  execution_id: number;
  status: string;
  result?: {
    success: boolean;
    logs: ExecutionLog[];
    duration: number;
  };
}

/**
 * 执行历史响应 (实际实现)
 */
interface ExecutionHistoryResponse {
  id: number;
  graph_id: number;
  status: string;
  start_time: string;
  end_time?: string;
  trigger_type?: string;
  result_json?: string;
  logs_json?: string;
}

/**
 * 节点执行记录 (实际实现)
 */
interface NodeExecutionLog {
  id: number;
  execution_id: number;
  node_id: string;
  node_type: string;
  status: string;
  input_data_json?: string;
  output_data_json?: string;
  error_message?: string;
  start_time: string;
  end_time?: string;
}

/**
 * WebSocket 执行状态消息
 */
interface ExecutionStatusMessage {
  type: 'status' | 'log' | 'node_complete' | 'error' | 'breakpoint';
  executionId: string;
  data: unknown;
}

// ============================================
// Vue Flow Store 类型 (Pinia)
// ============================================

/**
 * 规则引擎 Store 状态
 */
interface RuleEngineState {
  // 图数据
  currentGraph: RuleGraph | null;
  graphs: RuleGraph[];
  // 节点和边
  nodes: FlowNode[];
  edges: FlowEdge[];
  // 选择状态
  selectedNodeIds: string[];
  selectedEdgeIds: string[];
  // 视口状态
  viewport: ViewportState;
  // 执行状态
  isExecuting: boolean;
  currentExecutionId: string | null;
  // 节点运行时状态
  nodeStatuses: Record<string, NodeStatus>;
  // UI 状态
  showMinimap: boolean;
  showControls: boolean;
  snapToGrid: boolean;
  snapGridSize: number;
}

/**
 * 规则引擎 Store Actions
 */
interface RuleEngineActions {
  // 图操作
  loadGraph: (graphId: string) => Promise<void>;
  saveGraph: () => Promise<void>;
  createGraph: (name: string) => Promise<string>;
  deleteGraph: (graphId: string) => Promise<void>;
  
  // 节点操作
  addNode: (type: string, position: XYPosition) => void;
  updateNodeConfig: (nodeId: string, config: Record<string, unknown>) => void;
  removeNode: (nodeId: string) => void;
  
  // 边操作
  addEdge: (connection: FlowConnection) => void;
  removeEdge: (edgeId: string) => void;
  
  // 执行操作
  executeGraph: (triggerType: string, triggerData?: unknown) => Promise<string>;
  cancelExecution: (executionId: string) => Promise<void>;
  
  // 视口操作
  setViewport: (viewport: ViewportState) => void;
  fitView: () => void;
}

/**
 * 规则引擎 Store Getters
 */
interface RuleEngineGetters {
  nodeCount: number;
  edgeCount: number;
  triggerNodes: FlowNode[];
  conditionNodes: FlowNode[];
  actionNodes: FlowNode[];
  selectedNodes: FlowNode[];
  isDirty: boolean;
}
```

---

## 4. 图数据结构

### 4.1 规则图定义

```typescript
interface RuleGraph {
  id: string;                       // 图唯一标识
  name: string;                     // 图名称
  description?: string;            // 图描述
  nodes: GraphNode[];               // 节点列表
  edges: GraphEdge[];              // 连接列表
  variables: VariableDefinition[]; // 全局变量
  metadata: GraphMetadata;         // 元数据
}

// 图节点
interface GraphNode {
  id: string;                       // 节点唯一标识
  type: string;                     // 节点类型
  position: { x: number; y: number };  // 画布位置
  label?: string;                  // 自定义标签
  config: Record<string, any>;     // 节点配置
}

// 图连接
interface GraphEdge {
  id: string;                       // 连接唯一标识
  source: string;                   // 源节点 ID
  sourcePort: string;               // 源端口 ID
  target: string;                   // 目标节点 ID
  targetPort: string;               // 目标端口 ID
  type?: 'trigger' | 'data' | 'boolean';
}

// 变量定义
interface VariableDefinition {
  key: string;                      // 变量名
  type: 'string' | 'number' | 'boolean' | 'object';
  defaultValue?: any;              // 默认值
  description?: string;            // 变量描述
}

// 元数据
interface GraphMetadata {
  version: string;                  // 图版本
  createdAt: string;                 // 创建时间
  updatedAt: string;                 // 更新时间
  author?: string;                  // 作者
  tags?: string[];                  // 标签
}
```

### 4.2 执行上下文

```typescript
interface ExecutionContext {
  graphId: string;                   // 执行的图 ID
  executionId: string;              // 执行实例 ID
  variables: Record<string, any>;   // 变量快照
  detections: Detection[];          // 当前检测结果
  nodeStates: Record<string, NodeState>;  // 节点状态
  startTime: number;                // 开始时间戳
  logs: ExecutionLog[];             // 执行日志
}

// 检测结果 (对接 YOLO)
interface Detection {
  bbox: [number, number, number, number];  // x1, y1, x2, y2
  score: number;                   // 置信度
  label: string;                  // 类别名称
  labelId: number;                // 类别 ID
  timestamp: number;              // 检测时间戳
}

// 节点状态
interface NodeState {
  status: 'idle' | 'running' | 'success' | 'failed' | 'skipped';
  startTime?: number;
  endTime?: number;
  error?: string;
  outputData?: any;
}

// 执行日志
interface ExecutionLog {
  timestamp: number;
  level: 'debug' | 'info' | 'warning' | 'error';
  nodeId?: string;
  message: string;
  data?: any;
}
```

---

## 5. 执行引擎设计

### 5.1 执行模型

```
触发 → 图遍历 → 节点执行 → 状态更新 → 结果输出

执行模式:
1. 事件驱动: YOLO 检测到目标 → 触发图执行
2. 定时执行: Cron 表达式触发 → 图执行
3. 手动执行: 用户触发 → 图执行
4. 调试执行: 单步执行 → 节点逐个执行
```

### 5.2 执行流程

```python
# -*- coding: utf-8 -*-
"""规则引擎执行器 - 异步图遍历执行引擎。

模块功能：
- 图的加载和验证
- 节点执行调度
- 并发分支执行
- 执行状态管理
"""

import asyncio
import time
import uuid
from typing import Any, Callable, Optional
from dataclasses import dataclass, field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor

# ============================================
# 核心数据类
# ============================================

class NodeStatus(str, Enum):
    """节点执行状态枚举"""
    IDLE = 'idle'
    RUNNING = 'running'
    SUCCESS = 'success'
    FAILED = 'failed'
    SKIPPED = 'skipped'


class LogLevel(str, Enum):
    """日志级别枚举"""
    DEBUG = 'debug'
    INFO = 'info'
    WARNING = 'warning'
    ERROR = 'error'


@dataclass
class Detection:
    """检测结果数据类 (对接 YOLO)"""
    bbox: tuple[int, int, int, int]  # x1, y1, x2, y2
    score: float                      # 置信度
    label: str                        # 类别名称
    label_id: int                    # 类别 ID
    timestamp: float                 # 检测时间戳


@dataclass
class ExecutionLog:
    """执行日志数据类"""
    timestamp: float
    level: LogLevel
    node_id: Optional[str] = None
    node_name: Optional[str] = None
    message: str = ''
    data: Any = None


@dataclass
class ExecutionResult:
    """节点执行结果"""
    state: NodeStatus
    output: dict[str, Any] = field(default_factory=dict)
    propagate: bool = True
    error: Optional[str] = None


@dataclass
class NodeRuntimeState:
    """节点运行时状态"""
    status: NodeStatus = NodeStatus.IDLE
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    error: Optional[str] = None
    input_data: Any = None
    output_data: Any = None


@dataclass
class ExecutionContext:
    """执行上下文 - 图执行时的运行时状态"""
    graph_id: str
    execution_id: str
    variables: dict[str, Any] = field(default_factory=dict)
    detections: list[Detection] = field(default_factory=list)
    node_states: dict[str, NodeRuntimeState] = field(default_factory=dict)
    start_time: float = 0.0
    logs: list[ExecutionLog] = field(default_factory=list)
    # 调试支持
    debug_mode: bool = False
    breakpoints: set[str] = field(default_factory=set)
    # 内部状态
    _ws_manager: Any = None
    _input_control: Any = None
    _detector: Any = None


# ============================================
# 节点执行器基类
# ============================================

class BaseNodeExecutor:
    """节点执行器基类 - 所有节点执行器需继承此类"""

    # 类级别的执行器注册表
    _registry: dict[str, 'BaseNodeExecutor'] = {}

    @classmethod
    def register(cls, node_type: str):
        """装饰器：注册节点执行器

        使用方式:
            @BaseNodeExecutor.register('yolo_trigger')
            class YOLOTriggerExecutor(BaseNodeExecutor):
                pass
        """
        def decorator(executor_cls: type) -> type:
            cls._registry[node_type] = executor_cls()
            return executor_cls
        return decorator

    @classmethod
    def get_executor(cls, node_type: str) -> Optional['BaseNodeExecutor']:
        """获取节点执行器"""
        return cls._registry.get(node_type)

    @classmethod
    def get_all_executors(cls) -> dict[str, 'BaseNodeExecutor']:
        """获取所有注册的执行器"""
        return cls._registry.copy()

    async def execute(
        self,
        input_data: dict[str, Any],
        config: dict[str, Any],
        context: ExecutionContext
    ) -> ExecutionResult:
        """执行节点逻辑

        Args:
            input_data: 输入端口的数据
            config: 节点配置
            context: 执行上下文

        Returns:
            ExecutionResult: 执行结果
        """
        raise NotImplementedError("子类必须实现 execute 方法")

    def validate_config(self, config: dict[str, Any]) -> tuple[bool, Optional[str]]:
        """验证配置合法性

        Returns:
            (is_valid, error_message)
        """
        return True, None

    def get_output_data(
        self,
        output_port: str,
        result: ExecutionResult
    ) -> Any:
        """获取指定输出端口的数据

        Args:
            output_port: 输出端口 ID
            result: 执行结果

        Returns:
            端口对应的数据
        """
        return result.output.get(output_port)


# ============================================
# 执行引擎核心
# ============================================

class RuleGraphExecutor:
    """规则图执行器 - 管理和执行规则图"""

    def __init__(self):
        self._executors: dict[str, BaseNodeExecutor] = BaseNodeExecutor.get_all_executors()
        self._thread_pool = ThreadPoolExecutor(max_workers=4)
        self._running_executions: dict[str, ExecutionContext] = {}

    async def execute_graph(
        self,
        graph_id: str,
        trigger_data: dict[str, Any]
    ) -> dict[str, Any]:
        """执行规则图

        Args:
            graph_id: 图 ID
            trigger_data: 触发数据 { detections: [...], ... }

        Returns:
            执行结果
        """
        # 1. 创建执行上下文
        context = ExecutionContext(
            graph_id=graph_id,
            execution_id=str(uuid.uuid4()),
            variables={},
            detections=trigger_data.get('detections', []),
            start_time=time.time(),
        )
        self._running_executions[context.execution_id] = context

        try:
            # 2. 加载图数据
            graph = await self._load_graph(graph_id)
            if not graph:
                raise ValueError(f"Graph not found: {graph_id}")

            # 3. 查找触发器节点
            trigger_nodes = self._find_trigger_nodes(graph)

            if not trigger_nodes:
                raise ValueError(f"No trigger nodes found in graph: {graph_id}")

            # 4. 从触发器开始执行
            tasks = []
            for trigger_node in trigger_nodes:
                task = self._execute_node_recursive(trigger_node, context, graph)
                tasks.append(task)

            # 并发执行所有触发器路径
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 5. 处理异常结果
            errors = [r for r in results if isinstance(r, Exception)]
            if errors:
                context.logs.append(ExecutionLog(
                    timestamp=time.time(),
                    level=LogLevel.ERROR,
                    message=f"Execution completed with {len(errors)} errors"
                ))

            # 6. 返回执行结果
            return {
                'executionId': context.execution_id,
                'status': 'completed',
                'logs': [
                    {'timestamp': log.timestamp, 'level': log.level.value,
                     'nodeId': log.node_id, 'message': log.message}
                    for log in context.logs
                ],
                'duration': time.time() - context.start_time
            }

        finally:
            # 清理执行上下文
            self._running_executions.pop(context.execution_id, None)

    async def _execute_node_recursive(
        self,
        node: dict,
        context: ExecutionContext,
        graph: dict,
        input_data: Optional[dict] = None
    ) -> None:
        """递归执行节点 (深度优先)

        Args:
            node: 节点数据
            context: 执行上下文
            graph: 图数据
            input_data: 输入数据
        """
        node_id = node['id']
        node_type = node['type']
        node_config = node.get('config', {})

        # 1. 获取节点执行器
        executor = self._executors.get(node_type)
        if not executor:
            context.logs.append(ExecutionLog(
                timestamp=time.time(),
                level=LogLevel.ERROR,
                node_id=node_id,
                message=f"Unknown node type: {node_type}"
            ))
            return

        # 2. 更新节点状态为运行中
        context.node_states[node_id] = NodeRuntimeState(
            status=NodeStatus.RUNNING,
            start_time=time.time(),
            input_data=input_data
        )

        # 3. 发送 WebSocket 状态更新
        await self._send_ws_update(context, 'status', {
            'nodeId': node_id,
            'status': 'running'
        })

        try:
            # 4. 执行节点逻辑
            result = await executor.execute(input_data or {}, node_config, context)

            # 5. 更新节点状态
            context.node_states[node_id] = NodeRuntimeState(
                status=result.state,
                start_time=context.node_states[node_id].start_time,
                end_time=time.time(),
                output_data=result.output
            )

            # 6. 发送 WebSocket 状态更新
            await self._send_ws_update(context, 'node_complete', {
                'nodeId': node_id,
                'status': result.state.value,
                'output': result.output
            })

            # 7. 记录日志
            context.logs.append(ExecutionLog(
                timestamp=time.time(),
                level=LogLevel.INFO,
                node_id=node_id,
                message=f"Node executed: {result.state.value}"
            ))

            # 8. 如果需要传播，继续执行下游节点
            if result.propagate:
                # 查找下游连接
                out_edges = [e for e in graph.get('edges', []) if e['source'] == node_id]

                # 根据连接类型分发数据
                for edge in out_edges:
                    target_id = edge['target']
                    target_port = edge.get('targetPort', 'input')
                    target_node = self._find_node(graph, target_id)

                    if target_node:
                        # 构建下游输入数据
                        edge_type = edge.get('type', 'trigger')
                        next_input = self._route_output_to_input(
                            result.output, edge_type, target_port
                        )
                        # 递归执行下游节点
                        await self._execute_node_recursive(
                            target_node, context, graph, next_input
                        )

        except Exception as e:
            # 处理执行异常
            context.node_states[node_id] = NodeRuntimeState(
                status=NodeStatus.FAILED,
                start_time=context.node_states[node_id].start_time,
                end_time=time.time(),
                error=str(e)
            )
            context.logs.append(ExecutionLog(
                timestamp=time.time(),
                level=LogLevel.ERROR,
                node_id=node_id,
                message=f"Node execution failed: {str(e)}"
            ))

    async def _load_graph(self, graph_id: str) -> Optional[dict]:
        """从数据库加载图数据"""
        # TODO: 实现从数据库加载图
        pass

    def _find_trigger_nodes(self, graph: dict) -> list[dict]:
        """查找所有触发器节点"""
        return [
            node for node in graph.get('nodes', [])
            if self._get_node_category(node['type']) == 'trigger'
        ]

    def _find_node(self, graph: dict, node_id: str) -> Optional[dict]:
        """根据 ID 查找节点"""
        for node in graph.get('nodes', []):
            if node['id'] == node_id:
                return node
        return None

    def _get_node_category(self, node_type: str) -> str:
        """获取节点分类"""
        # 从注册的执行器推断分类
        executor = self._executors.get(node_type)
        if executor:
            return getattr(executor, 'category', 'action')
        return 'action'

    def _route_output_to_input(
        self,
        output: dict,
        edge_type: str,
        target_port: str
    ) -> dict:
        """将输出数据路由到目标输入端口"""
        if edge_type == 'trigger':
            return {'trigger': output}
        elif edge_type == 'data':
            return {target_port: output}
        elif edge_type == 'boolean':
            return {'condition': output}
        return output

    async def _send_ws_update(
        self,
        context: ExecutionContext,
        msg_type: str,
        data: dict
    ) -> None:
        """发送 WebSocket 状态更新"""
        if context._ws_manager:
            await context._ws_manager.send_message({
                'type': msg_type,
                'executionId': context.execution_id,
                'data': data
            })


# ============================================
# 内置节点执行器示例
# ============================================

@BaseNodeExecutor.register('yolo_trigger')
class YOLOTriggerExecutor(BaseNodeExecutor):
    """YOLO 检测触发器执行器"""

    category = 'trigger'

    async def execute(
        self,
        input_data: dict,
        config: dict,
        context: ExecutionContext
    ) -> ExecutionResult:
        """执行 YOLO 触发器

        配置参数:
            class_names: list[str] - 要检测的类别名称列表
            confidence: float - 最小置信度 (0-1)
            max_results: int - 最大结果数量
        """
        class_names = config.get('class_names', [])
        min_confidence = config.get('confidence', 0.5)
        max_results = config.get('max_results', 10)

        # 过滤检测结果
        matched = [
            d for d in context.detections
            if d.label in class_names and d.score >= min_confidence
        ][:max_results]

        return ExecutionResult(
            state=NodeStatus.SUCCESS,
            output={
                'detections': [
                    {
                        'bbox': d.bbox,
                        'score': d.score,
                        'label': d.label,
                        'labelId': d.label_id
                    }
                    for d in matched
                ],
                'count': len(matched)
            },
            propagate=len(matched) > 0
        )


@BaseNodeExecutor.register('keyboard_action')
class KeyboardActionExecutor(BaseNodeExecutor):
    """键盘动作执行器"""

    category = 'action'

    async def execute(
        self,
        input_data: dict,
        config: dict,
        context: ExecutionContext
    ) -> ExecutionResult:
        """执行键盘动作

        配置参数:
            key: str - 按键名称 (如 'a', 'enter', 'f1')
            hold_ms: int - 按住时长 (毫秒)
            repeat: int - 重复次数
        """
        key = config.get('key', '')
        hold_ms = config.get('hold_ms', 100)
        repeat = config.get('repeat', 1)

        if not key:
            return ExecutionResult(
                state=NodeStatus.FAILED,
                error="Key not specified"
            )

        # 通过输入控制服务执行
        if context._input_control:
            for _ in range(repeat):
                await context._input_control.press_key(key, hold_ms / 1000)
                if repeat > 1:
                    await asyncio.sleep(hold_ms / 1000)

        return ExecutionResult(
            state=NodeStatus.SUCCESS,
            output={'action': 'keyboard', 'key': key, 'repeat': repeat}
        )


@BaseNodeExecutor.register('condition_exists')
class ConditionExistsExecutor(BaseNodeExecutor):
    """条件判断 - 目标存在执行器"""

    category = 'condition'

    async def execute(
        self,
        input_data: dict,
        config: dict,
        context: ExecutionContext
    ) -> ExecutionResult:
        """判断检测结果中是否存在指定目标

        配置参数:
            class_name: str - 目标类别名称
            min_confidence: float - 最小置信度
        """
        class_name = config.get('class_name', '')
        min_confidence = config.get('min_confidence', 0.5)

        # 获取输入数据中的 detections
        detections = input_data.get('detections', context.detections)

        # 检查是否存在匹配的目标
        exists = any(
            d.label == class_name and d.score >= min_confidence
            for d in (Detection(**d) if isinstance(d, dict) else d for d in detections)
        )

        return ExecutionResult(
            state=NodeStatus.SUCCESS,
            output={'result': exists},
            propagate=True  # 总是传播，由分支节点决定路径
        )


@BaseNodeExecutor.register('http_action')
class HTTPActionExecutor(BaseNodeExecutor):
    """HTTP 请求动作执行器"""

    category = 'action'

    async def execute(
        self,
        input_data: dict,
        config: dict,
        context: ExecutionContext
    ) -> ExecutionResult:
        """发送 HTTP 请求

        配置参数:
            url: str - 请求 URL
            method: str - HTTP 方法 (GET, POST, PUT, DELETE)
            headers: dict - 请求头
            body: dict - 请求体
            timeout: int - 超时时间 (秒)
        """
        import httpx

        url = config.get('url', '')
        method = config.get('method', 'GET').upper()
        headers = config.get('headers', {})
        body = config.get('body', {})
        timeout = config.get('timeout', 30)

        if not url:
            return ExecutionResult(
                state=NodeStatus.FAILED,
                error="URL not specified"
            )

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                request_kwargs = {
                    'url': url,
                    'headers': headers,
                }

                if method in ('POST', 'PUT', 'PATCH'):
                    request_kwargs['json'] = body

                response = await client.request(method, **request_kwargs)

                return ExecutionResult(
                    state=NodeStatus.SUCCESS,
                    output={
                        'status': response.status_code,
                        'body': response.text,
                        'headers': dict(response.headers)
                    }
                )

        except httpx.TimeoutException:
            return ExecutionResult(
                state=NodeStatus.FAILED,
                error=f"HTTP request timeout: {url}"
            )
        except Exception as e:
            return ExecutionResult(
                state=NodeStatus.FAILED,
                error=f"HTTP request failed: {str(e)}"
            )


@BaseNodeExecutor.register('wait_action')
class WaitActionExecutor(BaseNodeExecutor):
    """等待动作执行器"""

    category = 'action'

    async def execute(
        self,
        input_data: dict,
        config: dict,
        context: ExecutionContext
    ) -> ExecutionResult:
        """等待指定时间

        配置参数:
            duration_ms: int - 等待时长 (毫秒)
        """
        duration_ms = config.get('duration_ms', 1000)
        await asyncio.sleep(duration_ms / 1000)

        return ExecutionResult(
            state=NodeStatus.SUCCESS,
            output={'waited_ms': duration_ms}
        )


@BaseNodeExecutor.register('branch_logic')
class BranchLogicExecutor(BaseNodeExecutor):
    """分支逻辑执行器"""

    category = 'logic'

    async def execute(
        self,
        input_data: dict,
        config: dict,
        context: ExecutionContext
    ) -> ExecutionResult:
        """根据条件选择分支

        输入端口:
            input: 触发输入
            condition: 条件判断结果 (boolean)

        输出端口:
            branch_a: 条件为 True 时输出
            branch_b: 条件为 False 时输出
        """
        condition = input_data.get('condition', False)

        # 分支执行器不自己传播，由调用方根据条件决定
        return ExecutionResult(
            state=NodeStatus.SUCCESS,
            output={'condition': condition},
            propagate=False  # 不自动传播，由图遍历器处理分支
        )


# ============================================
# 节点执行器注册表 (兼容旧代码)
// ============================================

class NodeExecutorRegistry:
    """节点执行器注册表 - 管理和执行各类节点 (兼容性别名)"""

    _executors: dict[str, BaseNodeExecutor] = {}

    @classmethod
    def register(cls, node_type: str, executor: BaseNodeExecutor):
        cls._executors[node_type] = executor

    @classmethod
    def get(cls, node_type: str) -> Optional[BaseNodeExecutor]:
        return cls._executors.get(node_type)

    @classmethod
    async def execute(
        cls,
        node_type: str,
        input_data: dict,
        config: dict,
        context: ExecutionContext
    ) -> ExecutionResult:
        executor = cls.get(node_type)
        if not executor:
            raise ValueError(f"Unknown node type: {node_type}")
        return await executor.execute(input_data, config, context)


# 初始化内置执行器
def init_builtin_executors():
    """初始化内置节点执行器"""
    # 确保装饰器注册的执行器被加载
    _ = [
        YOLOTriggerExecutor(),
        KeyboardActionExecutor(),
        ConditionExistsExecutor(),
        HTTPActionExecutor(),
        WaitActionExecutor(),
        BranchLogicExecutor(),
    ]


# ============================================
# 完整节点执行器示例 (新增强化版)
# ============================================

@BaseNodeExecutor.register('mouse_action')
class MouseActionExecutor(BaseNodeExecutor):
    """鼠标动作执行器 - 支持点击、移动、拖拽"""

    category = 'action'

    async def execute(
        self,
        input_data: dict,
        config: dict,
        context: ExecutionContext
    ) -> ExecutionResult:
        """执行鼠标动作

        配置参数:
            action: str - 动作类型 ('click', 'move', 'drag')
            x: int - X 坐标
            y: int - Y 坐标
            button: str - 鼠标按钮 ('left', 'right', 'middle')
            duration: int - 移动持续时间 (毫秒)
        """
        action = config.get('action', 'click')
        x = config.get('x', 0)
        y = config.get('y', 0)
        button = config.get('button', 'left')
        duration = config.get('duration', 100)

        if context._input_control:
            if action == 'click':
                await context._input_control.click_mouse(x, y, button)
            elif action == 'move':
                await context._input_control.move_mouse(x, y, duration / 1000)
            elif action == 'drag':
                # 拖拽: 按下 -> 移动 -> 释放
                start_x = config.get('start_x', x)
                start_y = config.get('start_y', y)
                await context._input_control.mouse.down(button, start_x, start_y)
                await context._input_control.mouse.move(x, y, duration / 1000)
                await context._input_control.mouse.up(button, x, y)

        return ExecutionResult(
            state=NodeStatus.SUCCESS,
            output={
                'action': action,
                'x': x,
                'y': y,
                'button': button
            }
        )


@BaseNodeExecutor.register('template_render')
class TemplateRenderExecutor(BaseNodeExecutor):
    """模板渲染执行器 - 支持变量插值"""

    category = 'utility'

    async def execute(
        self,
        input_data: dict,
        config: dict,
        context: ExecutionContext
    ) -> ExecutionResult:
        """渲染字符串模板

        配置参数:
            template: str - 模板字符串，支持 {{variable}} 插值
            example: "检测到 {{label}}，置信度 {{score}}"

        输入数据:
            context.variables: 全局变量
            input_data: 输入端口数据
        """
        template = config.get('template', '')

        if not template:
            return ExecutionResult(
                state=NodeStatus.FAILED,
                error="Template is empty"
            )

        # 合并变量: context.variables + input_data
        variables = {**context.variables, **input_data}

        # 简单的模板替换
        import re
        def replace_var(match):
            var_name = match.group(1).strip()
            # 支持嵌套属性访问如 {{detection.label}}
            if '.' in var_name:
                parts = var_name.split('.')
                value = variables.get(parts[0], {})
                for part in parts[1:]:
                    value = value.get(part, '')
                return str(value) if value is not None else match.group(0)
            return str(variables.get(var_name, match.group(0)))

        result = re.sub(r'\{\{([^}]+)\}\}', replace_var, template)

        return ExecutionResult(
            state=NodeStatus.SUCCESS,
            output={'result': result, 'template': template}
        )


@BaseNodeExecutor.register('loop_logic')
class LoopLogicExecutor(BaseNodeExecutor):
    """循环逻辑执行器"""

    category = 'logic'

    async def execute(
        self,
        input_data: dict,
        config: dict,
        context: ExecutionContext
    ) -> ExecutionResult:
        """循环执行直到条件满足

        配置参数:
            max_iterations: int - 最大迭代次数 (防止死循环)
            condition_expression: str - 终止条件表达式

        输入端口:
            input: 触发输入
            condition: 终止条件 (boolean)

        输出端口:
            loop_body: 循环体执行输出
            done: 循环完成输出
        """
        max_iterations = config.get('max_iterations', 100)
        iterations = 0
        condition_met = False

        # 执行循环
        while iterations < max_iterations and not condition_met:
            iterations += 1

            # 检查条件
            condition = input_data.get('condition', False)
            condition_met = bool(condition)

            if not condition_met:
                # 继续下一次迭代
                # 注意: 实际执行由图遍历器控制
                pass

        if iterations >= max_iterations:
            return ExecutionResult(
                state=NodeStatus.SUCCESS,
                output={
                    'iterations': iterations,
                    'reason': 'max_iterations_reached'
                },
                propagate=True
            )

        return ExecutionResult(
            state=NodeStatus.SUCCESS,
            output={
                'iterations': iterations,
                'reason': 'condition_met'
            },
            propagate=True
        )


@BaseNodeExecutor.register('parallel_execute')
class ParallelExecuteExecutor(BaseNodeExecutor):
    """并行执行器 - 同时执行多个分支"""

    category = 'logic'

    def __init__(self):
        super().__init__()
        self._executor = ThreadPoolExecutor(max_workers=4)

    async def execute(
        self,
        input_data: dict,
        config: dict,
        context: ExecutionContext
    ) -> ExecutionResult:
        """并行执行多个分支

        配置参数:
            branches: list[dict] - 分支配置列表
            timeout_ms: int - 超时时间 (毫秒)

        输入端口:
            input: 触发输入

        输出端口:
            output_1 ~ output_n: 各分支结果
        """
        branches = config.get('branches', [])
        timeout_ms = config.get('timeout_ms', 30000)

        if not branches:
            return ExecutionResult(
                state=NodeStatus.SUCCESS,
                output={'results': [], 'executed': 0}
            )

        # 并行执行所有分支
        tasks = []
        for branch in branches:
            task = self._execute_branch(branch, context)
            tasks.append(task)

        # 等待所有分支完成
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=timeout_ms / 1000
            )

            # 处理结果
            outputs = {
                f'output_{i}': r if not isinstance(r, Exception) else {'error': str(r)}
                for i, r in enumerate(results)
            }

            return ExecutionResult(
                state=NodeStatus.SUCCESS,
                output={
                    'results': outputs,
                    'executed': len(branches)
                }
            )

        except asyncio.TimeoutError:
            return ExecutionResult(
                state=NodeStatus.FAILED,
                error=f"Parallel execution timeout after {timeout_ms}ms"
            )

    async def _execute_branch(
        self,
        branch: dict,
        context: ExecutionContext
    ) -> dict:
        """执行单个分支"""
        # 分支执行逻辑
        # 实际由调用方控制
        return {'branch_id': branch.get('id'), 'status': 'executed'}
```

### 5.3 节点执行器注册表

```python
# 节点执行器注册表

class NodeExecutorRegistry:
    """节点执行器注册表 - 管理和执行各类节点"""
    
    _executors: Dict[str, 'NodeExecutor'] = {}
    
    @classmethod
    def register(cls, node_type: str, executor: 'NodeExecutor'):
        cls._executors[node_type] = executor
    
    @classmethod
    def get(cls, node_type: str) -> 'NodeExecutor':
        return cls._executors.get(node_type)
    
    @classmethod
    async def execute(cls, node_type: str, input_data: dict, 
                      config: dict, context: ExecutionContext) -> ExecutionResult:
        executor = cls.get(node_type)
        if not executor:
            raise ValueError(f"Unknown node type: {node_type}")
        return await executor.execute(input_data, config, context)


# 示例: YOLO 触发器执行器
class YOLOTriggerExecutor(NodeExecutor):
    
    async def execute(self, input_data: dict, config: dict, 
                      context: ExecutionContext) -> ExecutionResult:
        # 从配置获取触发条件
        class_names = config.get('class_names', [])
        min_confidence = config.get('confidence', 0.5)
        
        # 过滤检测结果
        matched = [
            d for d in context.detections
            if d.label in class_names and d.score >= min_confidence
        ]
        
        return ExecutionResult(
            state=NodeState(status='success'),
            output={'detections': matched, 'count': len(matched)},
            propagate=len(matched) > 0  # 有匹配才传播
        )


# 示例: 键盘动作执行器
class KeyboardActionExecutor(NodeExecutor):
    
    async def execute(self, input_data: dict, config: dict, 
                      context: ExecutionContext) -> ExecutionResult:
        key = config.get('key')
        hold_ms = config.get('hold_ms', 100)
        repeat = config.get('repeat', 1)
        
        for _ in range(repeat):
            await keyboard_emulator.press_key(key, hold_ms / 1000)
            await asyncio.sleep(hold_ms / 1000)
        
        return ExecutionResult(
            state=NodeState(status='success'),
            output={'action': 'keyboard', 'key': key, 'repeat': repeat}
        )
```

---

## 6. 前端节点编辑器设计

### 6.1 画布功能

```
┌────────────────────────────────────────────────────────────────┐
│  节点编辑器画布                                                 │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  ┌─────────────┐                    ┌─────────────┐          │
│  │ YOLO触发器   │──────────────────▶│  条件判断    │          │
│  │  [开始按钮]  │   detections       │  血量 < 20% │          │
│  └─────────────┘                    └──────┬──────┘          │
│                                           │ true             │
│  ┌─────────────┐                          ▼                  │
│  │   等待      │◀────────────────┐  ┌─────────────┐          │
│  │   2000ms   │                 │  │  发送HTTP   │          │
│  └──────┬─────┘                 │  │  告警接口   │          │
│         │                       │  └─────────────┘          │
│         │                       │                            │
│         └───────────────────────┘                            │
│                                                                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ MiniMap │  缩放: 100%  │  节点: 5  │  连接: 4  │  保存   │   │
│  └─────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────┘
```

### 6.2 节点面板

```
┌──────────────────┐
│  节点面板        │
├──────────────────┤
│ 🔍 搜索节点...   │
├──────────────────┤
│ ▼ 触发器         │
│   ├─ YOLO检测    │
│   ├─ 定时触发    │
│   └─ HTTP触发    │
├──────────────────┤
│ ▼ 条件           │
│   ├─ 目标存在    │
│   ├─ 数量判断    │
│   └─ 表达式      │
├──────────────────┤
│ ▼ 动作           │
│   ├─ 键盘按键    │
│   ├─ 鼠标点击    │
│   ├─ 发送HTTP    │
│   └─ 执行Python  │
├──────────────────┤
│ ▼ 逻辑           │
│   ├─ 分支        │
│   ├─ 并行执行    │
│   └─ 循环        │
└──────────────────┘
```

### 6.3 节点配置面板

```
┌──────────────────┐
│  节点配置        │
├──────────────────┤
│ YOLO检测触发器   │
│ ─────────────────│
│                  │
│ 触发条件          │
│ ┌──────────────┐ │
│ │ button      │ │  ← 类别名称
│ └──────────────┘ │
│                  │
│ 置信度阈值       │
│ ┌──────────────┐ │
│ │ 0.5         │ │
│ └──────────────┘ │
│                  │
│ 最大数量         │
│ ┌──────────────┐ │
│ │ 10          │ │
│ └──────────────┘ │
│                  │
│ [删除节点]       │
└──────────────────┘
```

### 6.4 组件结构

```
src/
├── views/
│   └── RuleEngine.vue              # 规则引擎主页面
├── components/
│   ├── rule-engine/
│   │   ├── NodeCanvas.vue           # 节点画布
│   │   ├── NodePalette.vue          # 节点面板
│   │   ├── NodeConfig.vue           # 节点配置面板
│   │   ├── EdgeHandle.vue           # 连接手柄
│   │   ├── MiniMap.vue              # 小地图
│   │   └── DebugPanel.vue           # 调试面板
│   └── common/
│       └── CodeEditor.vue           # 代码编辑器组件
├── stores/
│   └── ruleEngine.ts               # 规则引擎状态管理
├── api/
│   └── ruleEngine.ts               # API 调用封装
└── types/
    └── ruleEngine.ts                # TypeScript 类型定义
```

---

## 5. 后端 API 设计

### 5.1 API 端点 (实际实现)

```
规则图管理:
POST   /api/rule-engine/graphs              # 创建规则图
GET    /api/rule-engine/graphs              # 获取规则图列表
GET    /api/rule-engine/graphs/:id         # 获取规则图详情
GET    /api/rule-engine/graphs/:id/detail  # 获取规则图详情(含解析数据)
PATCH  /api/rule-engine/graphs/:id/thumbnail # 更新缩略图
PUT    /api/rule-engine/graphs/:id          # 更新规则图
DELETE /api/rule-engine/graphs/:id          # 删除规则图
POST   /api/rule-engine/graphs/:id/validate # 验证规则图
POST   /api/rule-engine/graphs/:id/activate # 激活规则图
POST   /api/rule-engine/graphs/:id/deactivate # 停用规则图

节点定义:
GET    /api/rule-engine/nodes/definitions    # 获取所有节点类型 (注意: 不是 /node-types)

执行管理:
POST   /api/rule-engine/execute              # 手动执行图 (注意: 不是 /execute/:graphId)
GET    /api/rule-engine/executions           # 获取执行历史
GET    /api/rule-engine/executions/:id     # 获取执行记录详情
GET    /api/rule-engine/executions/:id/logs # 获取执行日志详情
```

### 5.2 API 端点 (设计文档原始描述 - 已过时)

```

### 7.2 数据模型

```python
# Pydantic 模型

class GraphNodeModel(BaseModel):
    """图节点模型"""
    id: str
    type: str
    position_x: float
    position_y: float
    label: Optional[str] = None
    config: Dict[str, Any] = {}

class GraphEdgeModel(BaseModel):
    """图连接模型"""
    id: str
    source_id: str
    source_port: str
    target_id: str
    target_port: str

class VariableModel(BaseModel):
    """变量模型"""
    key: str
    type: str
    default_value: Any = None
    description: Optional[str] = None

class RuleGraphModel(BaseModel):
    """规则图模型"""
    id: int
    name: str
    description: Optional[str] = None
    nodes: List[GraphNodeModel] = []
    edges: List[GraphEdgeModel] = []
    variables: List[VariableModel] = []
    version: str = "1.0.0"
    is_active: bool = False
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
```

---

## 8. 数据库设计

### 8.1 表结构 (实际实现)

```sql
-- 规则图表 (表名: rule_graph)
CREATE TABLE rule_graph (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    nodes_json TEXT NOT NULL,           -- JSON 存储节点列表
    edges_json TEXT NOT NULL,           -- JSON 存储连接列表
    variables_json TEXT,                -- JSON 存储变量定义
    version VARCHAR(50) DEFAULT '1.0.0',
    is_active BOOLEAN DEFAULT FALSE,
    thumbnail TEXT,                      -- Base64 缩略图快照 (实际实现新增)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 执行历史表 (表名: execution_history)
CREATE TABLE execution_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    graph_id INTEGER NOT NULL,
    status VARCHAR(50) NOT NULL,        -- running, completed, failed
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    trigger_type VARCHAR(50),           -- yolo, timer, manual, http
    trigger_data_json TEXT,            -- 触发时的数据
    result_json TEXT,                   -- 执行结果
    logs_json TEXT,                     -- 执行日志
    FOREIGN KEY (graph_id) REFERENCES rule_graph(id)
);

-- 节点执行记录表 (表名: node_execution_log)
CREATE TABLE node_execution_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    execution_id INTEGER NOT NULL,
    node_id VARCHAR(255) NOT NULL,
    node_type VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL,        -- running, completed, failed
    input_data_json TEXT,
    output_data_json TEXT,
    error_message TEXT,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    FOREIGN KEY (execution_id) REFERENCES execution_history(id)
);
```

### 8.2 表结构 (设计文档原始描述 - 已过时)

```sql
-- 规则图表 (旧: rule_graphs，多了个 s)
CREATE TABLE rule_graphs (
    ...
);
```

---

## 9. 与 VisionGame 的集成

### 9.1 YOLO 检测集成

```python
# 检测服务集成

class DetectionService:
    """检测服务 - 对接 VisionGame YOLO 检测"""
    
    def __init__(self, detector: UIDetector):
        self.detector = detector
        self._callbacks: Dict[str, Callable] = {}
    
    async def start_listening(self, graph_id: str):
        """开始监听检测结果并触发规则"""
        # 这里会从 VisionGame 的数据输入模块获取检测结果
        # 并触发对应的规则图执行
        pass
    
    def on_detection(self, detections: List[Detection], frame):
        """检测回调 - 被 VisionGame 调用"""
        for graph_id, callback in self._callbacks.items():
            # 检查是否有规则图需要此检测结果
            graph = get_rule_graph(graph_id)
            if graph.is_active:
                asyncio.create_task(self._trigger_graph(graph, detections))
    
    async def _trigger_graph(self, graph_id: str, detections: List[Detection]):
        """触发规则图执行"""
        context = ExecutionContext(
            graph_id=graph_id,
            detections=detections
        )
        await execute_graph(graph_id, context)
```

### 9.2 输入控制集成

```python
# 输入模拟服务集成

class InputControlService:
    """输入控制服务 - 对接 VisionGame 输入模拟"""
    
    def __init__(self, controller: GameController):
        self.controller = controller
    
    async def press_key(self, key: str, duration: float = 0.1):
        """按下键盘按键"""
        await self.controller.keyboard.press(key, duration)
    
    async def click_mouse(self, x: int, y: int, button: str = 'left'):
        """点击鼠标"""
        await self.controller.mouse.click(x, y, button)
    
    async def move_mouse(self, x: int, y: int, duration: float = 0.1):
        """移动鼠标"""
        await self.controller.mouse.move(x, y, duration)
```

---

## 10. 实现计划

> ⚠️ **最后更新**: 2026-04-23 (feature/rule-engine 分支)

### 实现状态总览

> ⚠️ **最后更新**: 2026-04-23 (feature/rule-engine 分支与 origin/main 合并后)

| 模块 | 状态 | 说明 |
|------|------|------|
| **后端 API** | ✅ 已完成 | FastAPI 完整 CRUD + 执行接口，路由前缀 `/api/rule-engine` |
| **数据库模型** | ✅ 已完成 | `rule_graph`, `execution_history`, `node_execution_log` (表名单数) |
| **节点基类** | ✅ 已完成 | BaseNode, ExecutionContext, NodeResult |
| **节点注册表** | ✅ 已完成 | NodeRegistry + init_builtin_executors() |
| **图管理器** | ✅ 已完成 | GraphManager CRUD + validate_graph |
| **规则执行器** | ✅ 已完成 | RuleGraphExecutor 异步执行引擎 |
| **触发器节点** | ✅ 已完成 | YOLOTrigger, TimerTrigger, ManualTrigger (3个) |
| **条件节点** | ✅ 已完成 | ObjectExists, ConfidenceThreshold, Variable (3个) |
| **动作节点** | ✅ 已完成 | Keyboard, Mouse, Wait, HttpRequest, Log (5个) |
| **逻辑节点** | ✅ 已完成 | Branch, ParallelBranch, Loop, Delay, SetVariable (5个) |
| **前端 RuleList** | ✅ 已完成 | 列表页 + 卡片 + 缩略图 |
| **前端 RuleCanvas** | ✅ 已完成 | VueFlow 节点编辑器 |
| **WebSocket 实时通信** | ❌ 未实现 | 设计文档有描述，但实际代码未实现 |
| **VisionGame 集成** | 🔄 部分完成 | Keyboard/Mouse 节点有 TODO 标记待对接 core.control |

### API 端点 (实际实现 vs 设计文档)

| 功能 | 设计文档 | 实际实现 | 状态 |
|------|---------|---------|------|
| 节点定义 | `/node-types` | `/nodes/definitions` | ⚠️ 已更正 |
| 执行图 | `/execute/:graphId` | `/execute` (POST body 传 graph_id) | ⚠️ 已更正 |
| 规则图表名 | `rule_graphs` | `rule_graph` | ⚠️ 已更正 |
| 节点执行日志表名 | `node_execution_logs` | `node_execution_log` | ⚠️ 已更正 |
| WebSocket | `/ws/execution/:graphId` | ❌ 未实现 | ❌ |

### 待完成工作

1. **WebSocket 实时通信** - 执行状态实时推送 (代码未实现，文档有过时描述)
2. **VisionGame Core 集成** - KeyboardActionNode, MouseActionNode 需对接 `visiongame.core.control`
3. **循环节点完整实现** - LoopNode 需执行器支持迭代
4. **前端节点配置面板** - 节点详情编辑 UI
5. **执行历史页面** - 完整执行日志查看

```
backend/services/rule_engine/
├── __init__.py              # 导出 RuleGraphExecutor, NodeRegistry, GraphManager
├── graph_manager.py         # 图 CRUD + 验证
├── executor.py              # 异步图执行引擎
├── registry.py              # 节点注册表 + 内置节点初始化
└── nodes/
    ├── base.py              # BaseNode, NodeCategory, NodeStatus, ExecutionContext
    ├── triggers.py           # YOLOTrigger, TimerTrigger, ManualTrigger
    ├── conditions.py         # ObjectExists, ConfidenceThreshold, VariableCondition
    ├── actions.py            # Keyboard, Mouse, Wait, HttpRequest, Log
    └── logic.py              # Branch, ParallelBranch, Loop, Delay, SetVariable
```

### 待完成工作

1. **VisionGame Core 集成** - KeyboardActionNode, MouseActionNode 需对接 `visiongame.core.control`
2. **WebSocket 实时通信** - 执行状态实时推送
3. **循环节点完整实现** - LoopNode 需执行器支持迭代
4. **前端节点配置面板** - 节点详情编辑 UI
5. **执行历史页面** - 完整执行日志查看

---

#### Phase 1: 基础框架 (2-3 周) - ✅ 已完成

- [x] 后端 API 框架搭建 (FastAPI + 路由结构)
- [x] 数据库表设计 (rule_graphs, execution_history)
- [x] 基础节点执行器框架 (BaseNodeExecutor 基类)
- [x] 图执行引擎核心逻辑 (RuleGraphExecutor)
- [x] 节点定义注册表 (NodeDefinitionRegistry)
- [x] 单元测试基础覆盖 (pytest + pytest-asyncio)
- [x] 基础 API 端点 (CRUD + 执行触发)

**Phase 1 优化建议**:
- 增加图验证逻辑：确保图中没有孤立节点或循环引用 ✅ 已实现
- 添加执行器注册表初始化方法 `init_builtin_executors()` ✅ 已实现
- 实现基础的执行上下文持久化 ✅ 已实现

**交付物**: 可运行的最小化规则引擎后端服务 ✅

#### Phase 2: 前端节点编辑器 (3-4 周) - 🔄 部分完成

前端实现情况：
- [x] RuleList.vue - 规则图列表页 ✅
- [x] RuleCanvas.vue - VueFlow 节点编辑器 ✅
- [ ] 节点面板 (Palette) 组件实现 - 需检查
- [ ] 节点配置面板实现 - 需检查
- [x] 节点拖拽、连接、删除交互 ✅ (VueFlow 内置)
- [x] 画布缩放、平移、小地图 ✅ (VueFlow 内置)
- [x] 图的保存/加载 API 对接 ✅
- [ ] Undo/Redo 撤销重做支持 - 待确认
- [ ] 键盘快捷键支持 - 待确认

**Phase 2 优化建议**:
- 使用 `shallowRef` 存储 nodes/edges 避免深度响应式
- 实现节点折叠功能，减少大型图的渲染压力
- 使用 `useMemo` 和 `useCallback` 优化组件性能
- 添加节点搜索和过滤功能

**交付物**: 功能完整的可视化节点编辑器 - 🔄 进行中

#### Phase 3: 核心功能 (2-3 周) - 🔄 大部分完成

- [x] YOLO 触发器实现 ✅
- [x] 条件节点实现 ✅ (目标存在/置信度/变量条件)
- [x] 动作节点实现 ✅ (键盘、鼠标、HTTP、等待、日志)
- [x] 逻辑节点实现 ✅ (分支、并行执行、循环部分)
- [ ] 执行引擎完善 (WebSocket 状态推送) - 待完成
- [x] 基础调试功能 (执行日志查看) ✅
- [x] 变量管理和模板渲染 ✅

**Phase 3 优化建议**:
- 实现执行缓存机制，减少重复计算
- 添加节点执行超时控制
- 实现执行历史的分页查询

**交付物**: 完整的规则执行能力 - 🔄 大部分完成

#### Phase 4: 高级功能 (2-3 周)

- [ ] 循环节点实现 (支持最大迭代次数)
- [ ] 超时节点实现
- [ ] 优先级队列节点
- [ ] 高级调试功能 (断点、单步执行)
- [ ] 执行历史和日志管理
- [ ] 表达式求值器 (安全沙箱)
- [ ] 性能基准测试
- [ ] 执行结果缓存

**Phase 4 优化建议**:
- 实现表达式安全沙箱，支持白名单内置函数
- 添加节点执行统计面板
- 实现死信队列处理机制

**交付物**: 生产可用的规则引擎

#### Phase 5: 集成与完善 (2 周)

- [ ] 与 VisionGame 核心模块深度集成
- [ ] WebSocket 实时通信完善
- [ ] 错误处理和重试机制
- [ ] 节点执行统计和监控
- [ ] 用户手册和 API 文档
- [ ] 集成测试和 E2E 测试
- [ ] 部署脚本和配置

**Phase 5 优化建议**:
- 实现配置热加载，无需重启服务
- 添加规则图版本管理和回滚功能
- 实现规则图导入/导出功能

**交付物**: 稳定可部署的版本

**总工期预计**: 11-15 周

---

## 11. 性能优化

### 11.1 执行引擎优化

#### 11.1.1 异步并发执行

```python
# 分支并行执行优化
async def execute_parallel_branches(
    self,
    branches: list[dict],
    context: ExecutionContext,
    graph: dict
) -> list[Any]:
    """并行执行多个分支，提升整体吞吐量"""

    # 使用 asyncio.gather 并发执行独立分支
    tasks = [
        self._execute_node_recursive(branch, context, graph)
        for branch in branches
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # 处理异常
    return [r for r in results if not isinstance(r, Exception)]
```

#### 11.1.2 线程池隔离执行

```python
# CPU 密集型任务使用线程池隔离
from concurrent.futures import ThreadPoolExecutor
import asyncio

class IsolatedExecutor:
    """使用线程池隔离执行危险或有问题的代码"""

    def __init__(self, max_workers: int = 2):
        self._executor = ThreadPoolExecutor(max_workers=max_workers)

    async def execute_in_thread(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """在线程池中执行函数并返回结果"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            lambda: func(*args, **kwargs)
        )

# 使用示例: 执行用户自定义 Python 代码
class PythonCodeExecutor(IsolatedExecutor):
    """安全的 Python 代码执行器"""

    def __init__(self):
        super().__init__(max_workers=2)
        self._timeout = 5  # 代码执行超时 (秒)

    async def execute_code(
        self,
        code: str,
        context: dict
    ) -> ExecutionResult:
        """执行用户代码 (带超时和安全隔离)"""
        import signal

        def timeout_handler(signum, frame):
            raise TimeoutError("Code execution timeout")

        try:
            # 设置超时
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(self._timeout)

            # 在线程中执行代码
            result = await self.execute_in_thread(
                self._run_code,
                code,
                context
            )

            signal.alarm(0)  # 取消超时

            return ExecutionResult(
                state=NodeStatus.SUCCESS,
                output=result
            )

        except TimeoutError:
            return ExecutionResult(
                state=NodeStatus.FAILED,
                error="Code execution timeout"
            )
```

#### 11.1.3 节点执行结果缓存

```python
class ExecutionCache:
    """节点执行结果缓存 - 避免重复计算"""

    def __init__(self, max_size: int = 1000):
        self._cache: dict[str, tuple[Any, float]] = {}
        self._max_size = max_size
        self._access_times: dict[str, float] = {}

    def _make_key(
        self,
        node_id: str,
        input_data: dict,
        config: dict
    ) -> str:
        """生成缓存键"""
        import hashlib
        import json

        content = json.dumps({
            'node_id': node_id,
            'input': input_data,
            'config': config
        }, sort_keys=True)

        return hashlib.md5(content.encode()).hexdigest()

    async def get_or_execute(
        self,
        node_id: str,
        input_data: dict,
        config: dict,
        executor: BaseNodeExecutor,
        context: ExecutionContext,
        ttl: float = 60.0  # 缓存有效期 (秒)
    ) -> ExecutionResult:
        """获取缓存或执行节点"""

        key = self._make_key(node_id, input_data, config)

        # 检查缓存
        if key in self._cache:
            result, cached_time = self._cache[key]
            if time.time() - cached_time < ttl:
                return result

        # 执行节点
        result = await executor.execute(input_data, config, context)

        # 更新缓存
        if len(self._cache) >= self._max_size:
            # LRU 淘汰
            oldest_key = min(self._access_times, key=self._access_times.get)
            del self._cache[oldest_key]
            del self._access_times[oldest_key]

        self._cache[key] = (result, time.time())
        self._access_times[key] = time.time()

        return result
```

#### 11.1.4 消息队列与背压控制

```python
import asyncio
from collections import deque
from typing import Optional

class MessageQueue:
    """节点间消息队列 - 实现背压控制"""

    def __init__(self, max_size: int = 1000):
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=max_size)
        self._closed = False

    async def put(self, item: Any, timeout: Optional[float] = None) -> bool:
        """发送消息到队列

        当队列满时实现背压: 等待直到有空间或超时
        """
        if self._closed:
            return False

        try:
            await asyncio.wait_for(
                self._queue.put(item),
                timeout=timeout
            )
            return True
        except asyncio.TimeoutError:
            return False  # 队列满，背压信号

    async def get(self, timeout: Optional[float] = None) -> Optional[Any]:
        """从队列获取消息"""
        try:
            return await asyncio.wait_for(
                self._queue.get(),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            return None

    def close(self):
        """关闭队列"""
        self._closed = True
        # 清空队列
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break
```

### 11.2 前端性能优化

#### 11.2.1 Vue Flow 大型图优化

```typescript
// Vue Flow 性能优化配置
import { MarkAll, MiniMap, Controls } from '@vue-flow/core'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'

// 使用虚拟化优化大量节点渲染
const nodeExtent = ref([
  [-5000, -5000],  // 左上角
  [5000, 5000]     // 右下角
])

// 连接线优化
const defaultEdgeOptions = {
  type: 'smoothstep',
  animated: false,  // 禁用动画以提升性能
  style: {
    stroke: '#b1b1b1',
    strokeWidth: 2
  }
}

// 节点拖拽优化 - 使用 CSS transform
const nodeSnapGrid = ref(15)

// MiniMap 优化
const minimapStyle = {
  width: 200,
  height: 150,
  padding: 10
}

// ============================================
// Vue Flow 12.x 性能优化最佳实践
// ============================================

/**
 * 1. 使用 shallowRef 避免深度响应式
 */
import { shallowRef, triggerRef } from 'vue'

const nodes = shallowRef<FlowNode[]>([])
const edges = shallowRef<FlowEdge[]>([])

function updateNodes(newNodes: FlowNode[]) {
  nodes.value = newNodes
  // 手动触发更新 (仅在需要时)
  triggerRef(nodes)
}

/**
 * 2. 节点组件使用 memo 避免不必要的重渲染
 */
import { memo } from 'vue'

const CustomNode = memo(defineComponent({
  props: {
    data: { type: Object as PropType<FlowNodeData>, required: true },
    selected: { type: Boolean }
  },
  setup(props) {
    // 仅在 data.selected 变化时重渲染
    return () => h('div', { class: 'custom-node' }, props.data.label)
  }
}), (prevProps, nextProps) => {
  // 自定义比较函数
  return (
    prevProps.selected === nextProps.selected &&
    prevProps.data.status === nextProps.data.status
  )
})

/**
 * 3. 使用 computed 缓存复杂计算
 */
const nodesByCategory = computed(() => {
  const grouped = new Map<string, FlowNode[]>()

  for (const node of nodes.value) {
    const category = node.data?.definition?.category || 'other'
    if (!grouped.has(category)) {
      grouped.set(category, [])
    }
    grouped.get(category)!.push(node)
  }

  return grouped
})

/**
 * 4. 边的虚拟化 (大量边时)
 */
const visibleEdges = computed(() => {
  // 仅渲染可见区域内的边
  const viewport = viewpor.value
  return edges.value.filter(edge => {
    const sourceNode = findNode(edge.source)
    const targetNode = findNode(edge.target)
    return isNodeVisible(sourceNode, viewport) || isNodeVisible(targetNode, viewport)
  })
})

/**
 * 5. 使用 requestAnimationFrame 节流
 */
import { throttle } from 'lodash-es'

// 节点位置更新节流
const throttledUpdatePosition = throttle((nodeId: string, position: XYPosition) => {
  flowInstance.value?.setNodePosition(nodeId, position)
}, 16)  // ~60fps

// 边的更新节流
const throttledUpdateEdges = throttle((edges: FlowEdge[]) => {
  flowInstance.value?.setEdges(edges)
}, 16)

// 视口变化防抖
const debouncedViewportChange = debounce((viewport: Viewport) => {
  // 保存视口状态到 localStorage
  localStorage.setItem('flow-viewport', JSON.stringify(viewport))
}, 300)

/**
 * 6. 延迟加载非可见节点
 */
const lazyLoadNode = async (nodeId: string) => {
  const node = nodes.value.find(n => n.id === nodeId)
  if (node && node.data.definition.lazy) {
    // 懒加载节点数据
    node.data = await fetchNodeData(nodeId)
  }
}
```

#### 11.2.2 画布交互优化

```typescript
// 使用 requestAnimationFrame 节流

// 节点位置更新节流
const throttledUpdatePosition = throttle((nodeId: string, position: XYPosition) => {
  flowInstance.value?.setNodePosition(nodeId, position)
}, 16)  // ~60fps

// 边的更新节流
const throttledUpdateEdges = throttle((edges: FlowEdge[]) => {
  flowInstance.value?.setEdges(edges)
}, 16)

// 视口变化防抖
const debouncedViewportChange = debounce((viewport: Viewport) => {
  // 保存视口状态到 localStorage
  localStorage.setItem('flow-viewport', JSON.stringify(viewport))
}, 300)
```

#### 11.2.3 状态管理优化

```typescript
// 使用 Pinia 的 computed 缓存复杂计算
import { defineStore } from 'pinia'
import { computed, shallowRef } from 'vue'

export const useRuleEngineStore = defineStore('ruleEngine', () => {
  // 使用 shallowRef 避免深度响应式开销
  const nodes = shallowRef<FlowNode[]>([])
  const edges = shallowRef<FlowEdge[]>([])

  // 缓存计算属性
  const nodeCount = computed(() => nodes.value.length)
  const edgeCount = computed(() => edges.value.length)

  // 按分类分组的节点 (缓存)
  const nodesByCategory = computed(() => {
    const grouped = new Map<string, FlowNode[]>()

    for (const node of nodes.value) {
      const category = node.data?.definition?.category || 'other'
      if (!grouped.has(category)) {
        grouped.set(category, [])
      }
      grouped.get(category)!.push(node)
    }

    return grouped
  })

  // 触发器节点列表
  const triggerNodes = computed(() =>
    nodes.value.filter(n => n.data?.definition?.category === 'trigger')
  )

  return {
    nodes,
    edges,
    nodeCount,
    edgeCount,
    nodesByCategory,
    triggerNodes
  }
})
```

#### 11.2.4 大图性能优化策略

| 优化策略 | 说明 | 适用场景 |
|---------|------|---------|
| 节点分组 | 将相关节点分组折叠 | 复杂业务流程 |
| 边的优化 | 禁用动画、使用贝塞尔曲线 | 大量连接线 |
| 视口裁剪 | 仅渲染可见区域节点 | 超大图 (>500 节点) |
| 虚拟滚动 | 列表节点按需渲染 | 节点类型列表 |
| Web Worker | 将计算移至 Worker | 复杂布局算法 |
| Canvas 渲染 | 使用原生 Canvas 替代 SVG | 极高密度节点 |

#### 11.2.5 可视化节点编辑器专项优化方案

**1. 连接线渲染优化**

Vue Flow / React Flow 的边渲染是性能瓶颈之一：
```typescript
// 使用优化后的边选项
const defaultEdgeOptions = {
  type: 'smoothstep',  // 使用直角边替代贝塞尔曲线
  animated: false,      // 禁用动画
  style: {
    stroke: '#b1b1b1',
    strokeWidth: 2
  }
};

// 对于大量边，使用 PathReplacer 简化渲染
const simplifyEdges = (edges: Edge[]) => {
  return edges.map(edge => ({
    ...edge,
    data: { ...edge.data, simplify: true }
  }));
};
```

**2. 节点拖拽性能优化**

```typescript
// 使用 CSS transform 替代 top/left 定位
const nodeStyle = computed(() => ({
  transform: `translate(${position.x}px, ${position.y}px)`,
  position: 'absolute' as const,
  willChange: 'transform'  // 提示浏览器优化
}));

// 批量更新节点位置
const batchUpdateNodes = useThrottleFn((nodeId: string, position: XYPosition) => {
  flowInstance.value?.setNodePosition(nodeId, position)
}, 16);
```

**3. 视口变化防抖**

```typescript
import { debounce } from 'lodash-es';

// 视口变化时保存状态 (避免频繁写入)
const debouncedSaveViewport = debounce((viewport: Viewport) => {
  localStorage.setItem('flow-viewport', JSON.stringify(viewport))
}, 500);

// MiniMap 节点过滤
const minimapNodeFilter = (node: Node) => {
  // 仅显示关键节点在 MiniMap 上
  return node.data?.showInMinimap !== false
};
```

**4. 大型图虚拟化策略**

```typescript
// 实现视口裁剪，仅渲染可见节点
const visibleNodeIds = computed(() => {
  const viewport = viewport.value
  const padding = 100  // 视口外延展区域

  return nodes.value
    .filter(node => {
      const { x, y } = node.position
      const width = node.measured?.width ?? 200
      const height = node.measured?.height ?? 100

      return (
        x + width >= viewport.x - padding &&
        x <= viewport.x + viewport.width + padding &&
        y + height >= viewport.y - padding &&
        y <= viewport.y + viewport.height + padding
      )
    })
    .map(node => node.id)
})
```

### 11.3 数据库优化

```sql
-- 添加索引优化查询
CREATE INDEX idx_rule_graphs_active ON rule_graphs(is_active);
CREATE INDEX idx_execution_history_graph_id ON execution_history(graph_id);
CREATE INDEX idx_execution_history_status ON execution_history(status);
CREATE INDEX idx_execution_history_start_time ON execution_history(start_time DESC);

-- 执行历史分区表 (按月分区)
CREATE TABLE execution_history_partitioned (
    id INTEGER PRIMARY KEY,
    graph_id INTEGER NOT NULL,
    status VARCHAR(50) NOT NULL,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    trigger_type VARCHAR(50),
    trigger_data_json TEXT,
    result_json TEXT,
    logs_json TEXT
) PARTITION BY RANGE (start_time);

-- 图数据 JSON 字段优化
-- 使用 JSON_EXTRACT 避免全量解析
CREATE INDEX idx_execution_history_trigger_type
ON execution_history(JSON_EXTRACT(trigger_data_json, '$.type'));
```

---

## 12. 安全考虑

### 12.1 代码执行安全

```python
# Python 代码执行器安全防护
import ast
import sys
from io import StringIO

class SafePythonExecutor:
    """安全的 Python 代码执行器"""

    # 允许的内置函数白名单
    ALLOWED_BUILTINS = {
        'len', 'range', 'str', 'int', 'float', 'bool',
        'list', 'dict', 'tuple', 'set', 'min', 'max',
        'sum', 'abs', 'round', 'sorted', 'reversed',
        'enumerate', 'zip', 'map', 'filter', 'any', 'all'
    }

    # 禁止的关键字
    FORBIDDEN_KEYWORDS = {
        'import', 'from', 'exec', 'eval', 'compile',
        'open', 'file', 'input', 'print',  # I/O 操作
        '__import__', 'getattr', 'setattr',  # 属性访问
        'breakpoint', 'help'  # 调试相关
    }

    def validate_code(self, code: str) -> tuple[bool, Optional[str]]:
        """验证代码安全性"""
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return False, f"Syntax error: {e}"

        # 检查关键字
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                return False, "Import statements are not allowed"
            if isinstance(node, ast.ImportFrom):
                return False, "Import statements are not allowed"
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in self.FORBIDDEN_KEYWORDS:
                        return False, f"Function '{node.func.id}' is not allowed"

        return True, None

    def execute(self, code: str, context: dict) -> dict:
        """执行验证后的代码"""
        is_valid, error = self.validate_code(code)
        if not is_valid:
            raise SecurityError(error)

        # 创建安全的执行环境
        safe_globals = {
            '__builtins__': {name: __builtins__[name]
                          for name in self.ALLOWED_BUILTINS
                          if name in __builtins__},
            **context
        }

        # 捕获输出
        old_stdout = sys.stdout
        sys.stdout = StringIO()

        try:
            result = eval(code, safe_globals, {})
            output = sys.stdout.getvalue()
            return {'result': result, 'output': output}
        except Exception as e:
            return {'error': str(e)}
        finally:
            sys.stdout = old_stdout
```

### 12.2 HTTP 请求安全

```python
# HTTP 请求安全限制
class SafeHTTPExecutor:
    """安全的 HTTP 请求执行器"""

    # 允许的协议
    ALLOWED_PROTOCOLS = {'http', 'https'}

    # 禁止的 URL 模式
    FORBIDDEN_PATTERNS = [
        r'localhost',
        r'127\.0\.0\.1',
        r'0\.0\.0\.0',
        r'::1',
        r'169\.254\.169\.254',  # AWS 元数据
        r'\.internal\.',
        r'\.local\b'
    ]

    # 超时限制
    DEFAULT_TIMEOUT = 10  # 秒
    MAX_TIMEOUT = 30

    # 请求大小限制
    MAX_REQUEST_SIZE = 1024 * 1024  # 1MB

    def validate_url(self, url: str) -> tuple[bool, Optional[str]]:
        """验证 URL 安全性"""
        try:
            parsed = urlparse(url)

            # 检查协议
            if parsed.scheme not in self.ALLOWED_PROTOCOLS:
                return False, f"Protocol '{parsed.scheme}' is not allowed"

            # 检查禁止模式
            for pattern in self.FORBIDDEN_PATTERNS:
                if re.search(pattern, url):
                    return False, f"URL matches forbidden pattern: {pattern}"

            return True, None

        except Exception as e:
            return False, f"Invalid URL: {e}"
```

### 12.3 输入验证

```python
# 节点配置输入验证
class ConfigValidator:
    """节点配置验证器"""

    @staticmethod
    def validate_detection_config(config: dict) -> tuple[bool, Optional[str]]:
        """验证检测配置"""
        class_names = config.get('class_names', [])

        if not isinstance(class_names, list):
            return False, "class_names must be a list"

        if len(class_names) > 100:
            return False, "class_names too long (max 100)"

        confidence = config.get('confidence', 0.5)
        if not 0 <= confidence <= 1:
            return False, "confidence must be between 0 and 1"

        return True, None

    @staticmethod
    def validate_keyboard_config(config: dict) -> tuple[bool, Optional[str]]:
        """验证键盘配置"""
        key = config.get('key', '')

        # 允许的按键名称
        allowed_keys = {
            'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm',
            'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z',
            '0', '1', '2', '3', '4', '5', '6', '7', '8', '9',
            'enter', 'escape', 'space', 'tab', 'backspace',
            'f1', 'f2', 'f3', 'f4', 'f5', 'f6', 'f7', 'f8', 'f9', 'f10', 'f11', 'f12',
            'up', 'down', 'left', 'right',
            'ctrl', 'alt', 'shift', 'meta'
        }

        if key.lower() not in allowed_keys:
            return False, f"Unsupported key: {key}"

        repeat = config.get('repeat', 1)
        if not isinstance(repeat, int) or repeat < 1 or repeat > 100:
            return False, "repeat must be between 1 and 100"

        return True, None
```

### 12.4 WebSocket 安全

```python
# WebSocket 连接安全
from fastapi import WebSocket, WebSocketDisconnect
from typing import Set

class ConnectionManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        # 活跃连接
        self.active_connections: Set[WebSocket] = set()
        # 认证信息
        self.authenticated: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket, graph_id: str) -> bool:
        """接受连接并验证"""
        await websocket.accept()

        # 验证来源 (检查 referer 或 token)
        # if not self.validate_origin(websocket):
        #     await websocket.close(code=4001)
        #     return False

        self.active_connections.add(websocket)

        # 限制每个图的连接数
        if self.count_graph_connections(graph_id) > 10:
            await websocket.close(code=4002, reason="Too many connections")
            self.active_connections.discard(websocket)
            return False

        return True

    def disconnect(self, websocket: WebSocket):
        """断开连接"""
        self.active_connections.discard(websocket)
        self.authenticated.discard(websocket)

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """发送个人消息"""
        try:
            await websocket.send_json(message)
        except WebSocketDisconnect:
            self.disconnect(websocket)

    async def broadcast(self, message: dict, graph_id: str):
        """广播消息到指定图的连接"""
        disconnected = []

        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except WebSocketDisconnect:
                disconnected.append(connection)

        # 清理断开的连接
        for conn in disconnected:
            self.disconnect(conn)
```

### 12.5 执行超时与熔断机制

```python
class CircuitBreaker:
    """熔断器 - 防止级联失败"""

    def __init__(self, failure_threshold: int = 5, timeout: float = 60.0):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failures = 0
        self.last_failure_time: Optional[float] = None
        self.state = 'closed'  # closed, open, half_open

    def call(self, func: Callable, *args, **kwargs):
        """执行函数，带熔断保护"""
        if self.state == 'open':
            if time.time() - self.last_failure_time > self.timeout:
                self.state = 'half_open'
            else:
                raise CircuitOpenError("Circuit breaker is open")

        try:
            result = func(*args, **kwargs)
            if self.state == 'half_open':
                self.state = 'closed'
                self.failures = 0
            return result
        except Exception as e:
            self.failures += 1
            self.last_failure_time = time.time()
            if self.failures >= self.failure_threshold:
                self.state = 'open'
            raise

class ExecutionTimeout:
    """执行超时管理器"""

    def __init__(self, default_timeout: float = 30.0):
        self.default_timeout = default_timeout
        self.active_timers: dict[str, asyncio.Task] = {}

    async def execute_with_timeout(
        self,
        coro: coroutine,
        execution_id: str,
        timeout: Optional[float] = None
    ) -> Any:
        """执行协程，带超时控制"""
        timeout = timeout or self.default_timeout

        task = asyncio.create_task(coro)
        self.active_timers[execution_id] = task

        try:
            return await asyncio.wait_for(task, timeout=timeout)
        except asyncio.TimeoutError:
            task.cancel()
            raise ExecutionTimeoutError(f"Execution timed out after {timeout}s")
        finally:
            self.active_timers.pop(execution_id, None)

    def cancel(self, execution_id: str):
        """取消执行"""
        task = self.active_timers.get(execution_id)
        if task:
            task.cancel()
```

---

## 13. 与 VisionGame 集成的详细接口设计

### 13.1 核心接口定义

```python
# -*- coding: utf-8 -*-
"""VisionGame 规则引擎集成接口。

定义规则引擎与 VisionGame 核心模块之间的接口。
"""

from typing import Protocol, Optional, Callable
from dataclasses import dataclass
from enum import Enum

# ============================================
# 协议定义 (Protocol) - 接口规范
# ============================================

class DetectorProtocol(Protocol):
    """检测器协议 - VisionGame YOLO 检测器需实现此接口"""

    async def detect(self, frame: 'np.ndarray') -> list['Detection']:
        """检测画面中的目标

        Args:
            frame: 输入图像 (numpy array)

        Returns:
            检测结果列表
        """
        ...

    def get_classes(self) -> list[str]:
        """获取支持的类别列表"""
        ...


class InputControlProtocol(Protocol):
    """输入控制协议 - VisionGame 输入控制器需实现此接口"""

    async def press_key(self, key: str, duration: float = 0.1) -> None:
        """按下并释放按键

        Args:
            key: 按键名称
            duration: 按住时长 (秒)
        """
        ...

    async def click_mouse(
        self,
        x: int,
        y: int,
        button: str = 'left'
    ) -> None:
        """点击鼠标

        Args:
            x: X 坐标
            y: Y 坐标
            button: 鼠标按钮 ('left', 'right', 'middle')
        """
        ...

    async def move_mouse(self, x: int, y: int, duration: float = 0.1) -> None:
        """移动鼠标

        Args:
            x: 目标 X 坐标
            y: 目标 Y 坐标
            duration: 移动时长 (秒)
        """
        ...


class DataCaptureProtocol(Protocol):
    """数据捕获协议 - VisionGame 数据输入模块需实现此接口"""

    async def get_current_frame(self) -> 'np.ndarray':
        """获取当前画面"""
        ...

    async def get_screen_size(self) -> tuple[int, int]:
        """获取屏幕分辨率 (width, height)"""
        ...


# ============================================
# 服务注册与注入
# ============================================

class ServiceRegistry:
    """服务注册表 - 管理全局服务实例"""

    _instance: Optional['ServiceRegistry'] = None
    _services: dict[str, object] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def register(cls, name: str, service: object) -> None:
        """注册服务实例

        Args:
            name: 服务名称
            service: 服务实例
        """
        cls._services[name] = service

    @classmethod
    def get(cls, name: str) -> Optional[object]:
        """获取服务实例"""
        return cls._services.get(name)

    @classmethod
    def get_detector(cls) -> Optional[DetectorProtocol]:
        """获取检测器服务"""
        return cls._services.get('detector')

    @classmethod
    def get_input_control(cls) -> Optional[InputControlProtocol]:
        """获取输入控制服务"""
        return cls._services.get('input_control')

    @classmethod
    def get_data_capture(cls) -> Optional[DataCaptureProtocol]:
        """获取数据捕获服务"""
        return cls._services.get('data_capture')


# ============================================
# 事件定义
# ============================================

class RuleEngineEvent(str, Enum):
    """规则引擎事件类型"""
    GRAPH_STARTED = 'graph_started'
    GRAPH_COMPLETED = 'graph_completed'
    GRAPH_FAILED = 'graph_failed'
    NODE_STARTED = 'node_started'
    NODE_COMPLETED = 'node_completed'
    NODE_FAILED = 'node_failed'
    DETECTION_TRIGGERED = 'detection_triggered'


@dataclass
class RuleEngineEventData:
    """规则引擎事件数据"""
    event: RuleEngineEvent
    graph_id: str
    execution_id: str
    node_id: Optional[str] = None
    data: Optional[dict] = None
    timestamp: float = 0.0


# ============================================
# 事件监听器
# ============================================

RuleEngineEventListener = Callable[[RuleEngineEventData], None]


class RuleEngineEventEmitter:
    """规则引擎事件发射器"""

    def __init__(self):
        self._listeners: dict[RuleEngineEvent, list[RuleEngineEventListener]] = {}

    def on(self, event: RuleEngineEvent, listener: RuleEngineEventListener) -> None:
        """注册事件监听器"""
        if event not in self._listeners:
            self._listeners[event] = []
        self._listeners[event].append(listener)

    def off(self, event: RuleEngineEvent, listener: RuleEngineEventListener) -> None:
        """移除事件监听器"""
        if event in self._listeners:
            self._listeners[event].remove(listener)

    async def emit(self, event_data: RuleEngineEventData) -> None:
        """发射事件"""
        event = event_data.event
        if event in self._listeners:
            for listener in self._listeners[event]:
                try:
                    listener(event_data)
                except Exception:
                    # 日志记录但不影响主流程
                    pass


# ============================================
# 集成初始化
# ============================================

async def init_rule_engine_integration(
    detector: DetectorProtocol,
    input_control: InputControlProtocol,
    data_capture: Optional[DataCaptureProtocol] = None
) -> None:
    """初始化规则引擎集成

    在 VisionGame 启动时调用此函数注册服务

    Args:
        detector: YOLO 检测器实例
        input_control: 输入控制器实例
        data_capture: 数据捕获实例 (可选)
    """
    import time

    # 注册服务
    ServiceRegistry.register('detector', detector)
    ServiceRegistry.register('input_control', input_control)
    if data_capture:
        ServiceRegistry.register('data_capture', data_capture)

    # 初始化内置执行器
    from rule_engine.executor import init_builtin_executors
    init_builtin_executors()

    print(f"[RuleEngine] Integration initialized at {time.time()}")


# ============================================
# 检测触发集成
# ============================================

async def trigger_graph_on_detection(
    detections: list,
    frame: 'np.ndarray'
) -> None:
    """检测结果触发规则图

    当 VisionGame 检测到目标时调用此函数

    Args:
        detections: 检测结果列表
        frame: 对应画面
    """
    from rule_engine.executor import RuleGraphExecutor

    # 获取所有活跃的规则图
    active_graphs = await get_active_rule_graphs()

    executor = RuleGraphExecutor()

    for graph in active_graphs:
        # 检查是否有 YOLO 触发器
        if has_yolo_trigger(graph):
            await executor.execute_graph(
                graph_id=graph['id'],
                trigger_data={
                    'detections': detections,
                    'frame': frame
                }
            )
```

### 13.2 FastAPI 集成路由

```python
# -*- coding: utf-8 -*-
"""规则引擎 API 路由。

提供规则引擎的 HTTP API 接口。
"""

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from typing import Optional
import json

from rule_engine.schemas import (
    RuleGraphModel,
    GraphNodeModel,
    GraphEdgeModel,
    CreateGraphRequest,
    UpdateGraphRequest,
    ExecuteGraphRequest
)
from rule_engine.executor import RuleGraphExecutor
from rule_engine.service_registry import ServiceRegistry

router = APIRouter(prefix='/api/rule-engine', tags=['rule-engine'])

# 缓存执行器实例
_executor: Optional[RuleGraphExecutor] = None


def get_executor() -> RuleGraphExecutor:
    """获取执行器实例"""
    global _executor
    if _executor is None:
        _executor = RuleGraphExecutor()
    return _executor


# ============================================
# 规则图管理 API
# ============================================

@router.post('/graphs', response_model=dict)
async def create_graph(request: CreateGraphRequest) -> dict:
    """创建新规则图

    创建新的规则图，返回图 ID。
    """
    graph_id = await save_graph({
        'name': request.name,
        'description': request.description,
        'nodes': [],
        'edges': [],
        'variables': request.variables or []
    })

    return {'id': graph_id, 'status': 'created'}


@router.get('/graphs')
async def list_graphs() -> list[dict]:
    """获取规则图列表

    返回所有规则图的摘要信息。
    """
    graphs = await get_all_graphs()
    return [
        {
            'id': g['id'],
            'name': g['name'],
            'description': g.get('description'),
            'nodeCount': len(g.get('nodes', [])),
            'edgeCount': len(g.get('edges', [])),
            'isActive': g.get('is_active', False),
            'updatedAt': g.get('updated_at')
        }
        for g in graphs
    ]


@router.get('/graphs/{graph_id}')
async def get_graph(graph_id: str) -> dict:
    """获取规则图详情

    返回规则的完整数据，包括节点和连接。
    """
    graph = await get_graph_by_id(graph_id)
    if not graph:
        raise HTTPException(status_code=404, detail='Graph not found')
    return graph


@router.put('/graphs/{graph_id}')
async def update_graph(graph_id: str, request: UpdateGraphRequest) -> dict:
    """更新规则图

    更新规则的节点、连接和配置。
    """
    graph = await get_graph_by_id(graph_id)
    if not graph:
        raise HTTPException(status_code=404, detail='Graph not found')

    update_data = {}
    if request.name is not None:
        update_data['name'] = request.name
    if request.description is not None:
        update_data['description'] = request.description
    if request.nodes is not None:
        update_data['nodes'] = request.nodes
    if request.edges is not None:
        update_data['edges'] = request.edges
    if request.variables is not None:
        update_data['variables'] = request.variables

    await update_graph_by_id(graph_id, update_data)

    return {'id': graph_id, 'status': 'updated'}


@router.delete('/graphs/{graph_id}')
async def delete_graph(graph_id: str) -> dict:
    """删除规则图"""
    await delete_graph_by_id(graph_id)
    return {'id': graph_id, 'status': 'deleted'}


# ============================================
# 节点类型 API
# ============================================

@router.get('/node-types')
async def get_node_types() -> list[dict]:
    """获取所有节点类型定义

    返回所有可用的节点类型及其配置。
    """
    from rule_engine.nodes import get_all_node_definitions
    return get_all_node_definitions()


# ============================================
# 执行管理 API
# ============================================

@router.post('/execute/{graph_id}')
async def execute_graph(
    graph_id: str,
    request: ExecuteGraphRequest
) -> dict:
    """手动执行规则图

    触发规则图执行，返回执行 ID。
    """
    graph = await get_graph_by_id(graph_id)
    if not graph:
        raise HTTPException(status_code=404, detail='Graph not found')

    executor = get_executor()

    # 创建执行任务
    result = await executor.execute_graph(
        graph_id=graph_id,
        trigger_data={
            'triggerType': request.trigger_type,
            'detections': request.trigger_data.get('detections') if request.trigger_data else None,
            'payload': request.trigger_data.get('payload') if request.trigger_data else None
        }
    )

    return {
        'executionId': result['executionId'],
        'status': result['status']
    }


@router.get('/executions/{execution_id}')
async def get_execution_status(execution_id: str) -> dict:
    """获取执行状态

    返回执行的状态和结果。
    """
    execution = await get_execution_by_id(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail='Execution not found')

    return execution


@router.get('/executions')
async def list_executions(
    graph_id: Optional[str] = None,
    limit: int = 50
) -> list[dict]:
    """获取执行历史

    返回最近的执行记录。
    """
    executions = await get_recent_executions(graph_id=graph_id, limit=limit)
    return executions


# ============================================
# WebSocket 实时通信
# ============================================

class ConnectionManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, graph_id: str):
        await websocket.accept()
        if graph_id not in self.active_connections:
            self.active_connections[graph_id] = []
        self.active_connections[graph_id].append(websocket)

    def disconnect(self, websocket: WebSocket, graph_id: str):
        if graph_id in self.active_connections:
            self.active_connections[graph_id].remove(websocket)

    async def send_to_graph(self, graph_id: str, message: dict):
        if graph_id in self.active_connections:
            for connection in self.active_connections[graph_id]:
                try:
                    await connection.send_json(message)
                except:
                    pass


ws_manager = ConnectionManager()


@router.websocket('/ws/execution/{graph_id}')
async def websocket_execution(websocket: WebSocket, graph_id: str):
    """执行状态 WebSocket

    实时推送执行状态更新。
    """
    await ws_manager.connect(websocket, graph_id)
    try:
        while True:
            # 保持连接，接收客户端消息
            data = await websocket.receive_text()
            message = json.loads(data)

            # 处理客户端消息 (如取消执行)
            if message.get('type') == 'cancel':
                await cancel_execution(message.get('executionId'))

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, graph_id)


@router.websocket('/ws/debug/{graph_id}')
async def websocket_debug(websocket: WebSocket, graph_id: str):
    """调试模式 WebSocket

    支持单步执行和断点调试。
    """
    await ws_manager.connect(websocket, graph_id)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            if message.get('type') == 'step':
                # 单步执行
                await execute_step(graph_id, message.get('nodeId'))
            elif message.get('type') == 'continue':
                # 继续执行到下一个断点
                await continue_execution(graph_id)
            elif message.get('type') == 'set_breakpoint':
                # 设置断点
                await set_breakpoint(graph_id, message.get('nodeId'))
            elif message.get('type') == 'remove_breakpoint':
                # 移除断点
                await remove_breakpoint(graph_id, message.get('nodeId'))

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, graph_id)

### 13.3 集成测试与部署

#### 13.3.1 集成测试策略

```python
# -*- coding: utf-8 -*-
"""规则引擎集成测试。

测试规则引擎与 VisionGame 各模块的集成。
"""

import pytest
from unittest.mock import Mock, AsyncMock
import numpy as np

class TestRuleEngineIntegration:
    """规则引擎集成测试"""

    @pytest.fixture
    def mock_detector(self):
        """模拟检测器"""
        detector = Mock()
        detector.detect = AsyncMock(return_value=[
            Detection(
                bbox=(100, 100, 200, 200),
                score=0.95,
                label="button",
                label_id=1,
                timestamp=time.time()
            )
        ])
        detector.get_classes = Mock(return_value=["button", "enemy", "health_bar"])
        return detector

    @pytest.fixture
    def mock_input_control(self):
        """模拟输入控制器"""
        control = Mock()
        control.press_key = AsyncMock()
        control.click_mouse = AsyncMock()
        control.move_mouse = AsyncMock()
        return control

    @pytest.mark.asyncio
    async def test_yolo_trigger_integration(
        self,
        mock_detector,
        mock_input_control
    ):
        """测试 YOLO 触发器与检测器集成"""
        # 初始化集成
        await init_rule_engine_integration(
            detector=mock_detector,
            input_control=mock_input_control
        )

        # 模拟检测结果
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        detections = await mock_detector.detect(frame)

        # 触发规则图
        await trigger_graph_on_detection(detections, frame)

        # 验证检测器被调用
        mock_detector.detect.assert_called_once()

    @pytest.mark.asyncio
    async def test_keyboard_action_integration(
        self,
        mock_input_control
    ):
        """测试键盘动作与输入控制集成"""
        # 创建包含键盘动作的规则图
        graph = create_test_graph_with_keyboard_action()

        # 执行图
        executor = RuleGraphExecutor()
        result = await executor.execute_graph(
            graph_id=graph['id'],
            trigger_data={}
        )

        # 验证键盘动作被执行
        mock_input_control.press_key.assert_called()

    @pytest.mark.asyncio
    async def test_webhook_notification(
        self,
        mock_detector,
        mock_input_control
    ):
        """测试 HTTP 动作与外部服务集成"""
        # 创建包含 HTTP 动作的规则图
        graph = create_test_graph_with_http_action()

        # 使用 aioresponses 模拟 HTTP 响应
        # ... (测试代码)

        # 执行图并验证 HTTP 请求被发送
        result = await executor.execute_graph(
            graph_id=graph['id'],
            trigger_data={'detections': []}
        )

        # 验证 HTTP 节点执行成功
        assert result['status'] == 'completed'
```

#### 13.3.2 部署配置

```yaml
# docker-compose.yml for Rule Engine
version: '3.8'

services:
  rule-engine:
    build:
      context: .
      dockerfile: Dockerfile.rule-engine
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=sqlite:///./rule_engine.db
      - REDIS_URL=redis://cache:6379
      - LOG_LEVEL=INFO
    volumes:
      - ./rule_engine.db:/app/rule_engine.db
    depends_on:
      - redis
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped

volumes:
  redis_data:
```

```python
# gunicorn_config.py
import multiprocessing

bind = "0.0.0.0:8000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"
max_requests = 1000
max_requests_jitter = 50
timeout = 30
keepalive = 2
```
```

---

## 14. 参考资料

### 14.1 官方文档

| 项目 | 文档地址 | 说明 |
|------|---------|------|
| Vue Flow | https://vueflow.dev/guide/ | Vue Flow 官方指南 (v1.48.2) |
| React Flow | https://reactflow.dev/learn | React Flow 官方文档 (v12.x) |
| Dify | https://docs.dify.ai/ | Dify 工作流文档 |
| Node-RED | https://nodered.org/docs/ | Node-RED 官方文档 |
| FastAPI | https://fastapi.tiangolo.com/ | FastAPI 官方文档 |

### 14.2 技术博客与教程

| 资源 | 说明 |
|------|------|
| React Flow Performance | https://reactflow.dev/learn/advanced-use/performance - 官方性能优化指南 |
| Vue Flow Examples | https://vueflow.dev/examples/ - 官方示例集合 |
| React Flow Playground | https://play.reactflow.dev/ - 交互式在线体验 |

### 14.3 开源项目参考

| 项目 | 地址 | 说明 |
|------|------|------|
| Dify | https://github.com/langgenius/dify | LLM 应用开发平台，节点编排参考 |
| Node-RED | https://github.com/node-red/node-red | 物联网可视化编程工具 |
| Blender Geometry Nodes | https://docs.blender.org/manual/en/latest/modeling/geometry_nodes/ | 程序化建模节点 |
| Unity Visual Scripting | https://unity.com/visual-scripting | 可视化脚本系统 |
| xyflow | https://github.com/xyflow/xyflow | React Flow / Vue Flow 核心库 |

### 14.4 Python 异步编程

| 资源 | 说明 |
|------|------|
| Python asyncio | https://docs.python.org/3/library/asyncio.html - 异步编程官方文档 |
| Python concurrency | https://docs.python.org/3/library/concurrent.futures.html - 并发编程 |

---

## 15. 附录

### 15.1 术语表

| 术语 | 说明 |
|------|------|
| DAG | 有向无环图 (Directed Acyclic Graph)，节点编排的执行模型 |
| 触发器 | 规则执行的起点，响应 YOLO 检测或外部事件 |
| 执行上下文 | 图执行时的运行时状态，包含变量、检测结果、日志等 |
| 节点执行器 | 负责执行特定类型节点逻辑的组件 |
| 背压控制 | 当队列满时阻止继续发送消息的机制 |

### 15.2 变更日志

| 版本 | 日期 | 变更说明 |
|------|------|---------|
| 1.2.0 | 2026-04 | 完善 Vue Flow 1.x / React Flow 12.x 最新特性文档；增加 Dify 2024-2025 最新架构设计；增加 Node-RED 执行引擎优化方案详解；增加可视化节点编辑器专项优化方案；增加执行超时与熔断机制；增加集成测试与部署配置章节；Phase 1-5 计划增加优化建议 |
| 1.1.0 | 2026-04 | 增加技术选型详细对比、Dify/Node-RED 竞品分析、更新 Phase 计划、完善 TypeScript 类型定义、增强性能优化章节 |
| 1.0.0 | 2026-04 | 初始版本 |
