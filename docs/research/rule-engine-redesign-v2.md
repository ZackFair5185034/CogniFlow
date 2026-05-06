# CogniFlow 规则引擎 - 重构设计方案 v2.2

> **文档版本：** v2.2
> **创建时间：** 2026-05-06
> **最后更新：** 2026-05-06
> **状态：** Phase A-D 已完成，Phase C/D 修复已推送，Phase E 验证中
> **Phase 2 执行引擎：** ✅ Kahn拓扑排序 + 层内并行，47测试通过

---

## 一、现状问题

老大原话："规则引擎前端根本没法用，节点没有可配置的东西，节点样式难看"

| 维度 | 问题 |
|------|------|
| 节点可配置性 | 每个节点没有实际参数，config_schema 基本为空 |
| 节点样式 | 面板是文字列表，画布节点用 VueFlow 默认样式，缺乏层次感 |
| 属性面板 | 表单简陋，无类型化输入 |
| 交互体验 | 复制粘贴、撤销重做不完整 |

---

## 二、设计规范

### 2.1 节点结构（画布节点）

**左进右出 — 数据从左向右流动**

```
┌─────────────────────────────────────────────────────────────────┐
│  ■■■ [🔬]  YOLO 检测 v2                        [⋮]            │  ← 顶部3px色条 + 标题
├─────────────┬──────────────────────────────┬───────────────────┤
│             │                              │                   │
│  ● image    │  model:  [yolov8n.pt   ▼]  │  ● image         │
│  ● trigger  │  conf:   [====●====] 0.5   │  ● bboxes         │
│             │  iou:    [====●====] 0.45  │  ● scores         │
│             │  max_d:  [____300____]      │  ● categories     │
│             │  device: [auto       ▼]     │  ● count          │
│             │                              │                   │
└─────────────┴──────────────────────────────┴───────────────────┘
  ← INPUT端口          配置控件区            OUTPUT端口 →

┌─────────────────────────────────────────────────────────────────┐
│ ⚙️ yolov8n.pt | conf: 0.50 | iou: 0.45 | 5 objs                 │  ← 底部摘要
└─────────────────────────────────────────────────────────────────┘
```

**设计要点：**
1. 顶部 3px 色条 — 类别标识（绿:input / 青:detection / 黄:processing / 橙:action / 紫:logic / 红:output）
2. 标题栏 — 图标 + 显示名 + 菜单按钮
3. 左侧 — INPUT 端口（接收上游数据）
4. 中间 — 配置控件（slider / dropdown / text / checkbox 等）
5. 右侧 — OUTPUT 端口（流向下游）
6. 底部 — 关键配置摘要（一眼能看到最重要参数）

### 2.2 节点端口规则

**不是所有节点都有进有出，按类型区分：**

| 节点类型 | INPUT端口 | OUTPUT端口 | 例子 |
|---------|:--------:|:----------:|------|
| **INPUT** | ✗ | ✓ | ImageCapture / VideoCapture |
| **TRIGGER** | ✗ | ✓ | Timer / Webhook |
| **PROCESSING** | ✓ | ✓ | YOLO / Resize / Filter |
| **ACTION** | ✓ | 可选 | Notification / Save |
| **LOGIC** | ✓ | ✓ | Condition / Delay |
| **OUTPUT** | ✓ | ✗ | Log（纯终端） |

> 实际端口数量完全由 `definition.inputs` / `definition.outputs` 决定，前端按需渲染。

### 2.3 节点面板（侧边栏）

```
┌──────────────────────────────┐
│ 🔍 搜索节点...           [×] │
├──────────────────────────────┤
│ ┌─ 📥 INPUT ──────────────┐  │
│ │ ┌────────────────────┐ │  │
│ │ │ 🖼 Image Input    │ │  │ ← 卡片式节点预览
│ │ │ 外部图片输入        │ │  │   带色条、图标、名称
│ │ └────────────────────┘ │  │
│ │ ┌────────────────────┐ │  │
│ │ │ 📹 Video Feed     │ │  │
│ │ └────────────────────┘ │  │
│ └────────────────────────┘  │
│ ┌─ 🎯 DETECTION ─────────┐  │
│ │ ┌────────────────────┐ │  │
│ │ │ 🔬 YOLO 检测      │ │  │
│ │ └────────────────────┘ │  │
│ └────────────────────────┘  │
│           ...                 │
└──────────────────────────────┘
```

### 2.4 属性面板（右侧）

```
┌─────────────────────────────────┐
│ 🧭 YOLO 检测               [×] │
├─────────────────────────────────┤
│ 节点名称   [YOLO 检测 v2____] │
│ 节点 ID    node_abc123         │
│ 节点类型   yolo_model          │
├─────────────────────────────────┤
│ ▼ 输入配置                      │
│ ● image     已连接 (node_1)  [断]│
│ ● trigger   未连接             │
├─────────────────────────────────┤
│ ▼ 参数配置                      │
│ model_id  [yolov8n.pt    ▼] 📎 │
│ conf:     [====●====] 0.5  📎 │
│ iou:      [====●====] 0.45 📎 │
│ max_det   [____300____]    📎 │
│ device    [auto        ▼]     │
├─────────────────────────────────┤
│ ▼ 输出配置                      │
│ ● bboxes    → node_3          │
│ ● scores    → [未连接]         │
├─────────────────────────────────┤
│ ▼ 执行状态                      │
│ [✓] 已执行  耗时: 123ms        │
│ 结果: 5 个目标                 │
├─────────────────────────────────┤
│ [删除节点]  [复制] [查看日志]  │
└─────────────────────────────────┘
```

### 2.5 配色体系

```
背景:
  画布背景     #0a0a0e
  面板背景     #12121a
  卡片背景     #1a1a24
  输入框背景   #0e0e16
  Hover态     #22222e

边框:
  默认         #2a2a3a
  选中/活跃    #00f0ff

类别色 (3px色条 + 面板):
  INPUT       #4CFF4C  (绿)
  DETECTION   #00f0ff  (青)
  PROCESSING  #FFFF4C  (黄)
  ACTION      #FF7F4C  (橙)
  LOGIC       #DC4FDC  (紫)
  OUTPUT      #FF4C4C  (红)

文字:
  主文字       #e0e0e8
  次文字       #8888aa
  弱文字       #555566
```

### 2.6 Widget 类型规范

| widget | 表单类型 | 说明 |
|--------|---------|------|
| `text` | 单行文本 | 默认 |
| `number` | 数字输入框 | 整数/小数 |
| `slider` | 滑块+数字 | 带min/max/step |
| `dropdown` | 下拉选择 | enum列表 |
| `model-select` | 模型选择器 | 动态加载模型列表 |
| `checkbox` | 开关toggle | boolean |
| `file-path` | 路径输入+浏览 | 文件选择 |
| `textarea` | 多行文本 | 长文本 |
| `code` | 代码编辑器 | 表达式 |

---

## 三、节点配置清单

### INPUT 类

```
ImageCaptureNode:
  - source:         dropdown [file/camera/url]  default: file
  - file_path:      file-path  visible when source=file
  - camera_id:      number    visible when source=camera  default: 0
  - interval:       number    visible when source=camera  default: 1.0

VideoCaptureNode:
  - source:         dropdown [file/stream]  default: file
  - file_path:      file-path  visible when source=file
  - stream_url:     text      visible when source=stream
  - fps:            number    default: 30

WebhookTriggerNode:
  - path:           text      required
  - method:         dropdown [GET/POST/ANY]  default: ANY
  - auth_type:      dropdown [none/bearer/basic]  default: none
```

### DETECTION 类

```
YOLOModelNode:
  - model_id:       model-select  required
  - confidence:     slider 0~1  default: 0.5
  - iou_threshold:  slider 0~1  default: 0.45
  - max_detections: number 1~1000  default: 300
  - device:         dropdown [auto/cuda/cpu]  default: auto

ObjectDetectorNode:
  - model_type:     dropdown [yolo/ssd/detectron2]  default: yolo
  - confidence:    slider 0~1  default: 0.5
  - labels:         textarea  (逗号分隔)

YOLOTriggerNode:
  - model_id:       model-select  required
  - target_labels:  textarea  (要触发检测的类别)
  - min_confidence: slider 0~1  default: 0.3
  - trigger_on:     dropdown [any/all]  default: any
```

### PROCESSING 类

```
CropNode:
  - mode:           dropdown [bbox/polygon/custom]  default: bbox
  - padding:        number  default: 10

ResizeNode:
  - width:          number  required
  - height:         number  required
  - mode:           dropdown [stretch/fit/fill]  default: fit
  - maintain_aspect: checkbox  default: true

NormalizeNode:
  - method:         dropdown [minmax/zscore]  default: minmax

FilterNode:
  - condition:      code  required  (如 "{{score}} > 0.5")
  - preview:        checkbox  default: false
```

### ACTION 类

```
MouseClickNode:
  - button:         dropdown [left/right/middle]  default: left
  - action_type:   dropdown [click/double-click/down/up]  default: click
  - x:              number
  - y:              number

KeyPressNode:
  - key:            text  required
  - action_type:   dropdown [press/down/up]  default: press

NotificationNode:
  - title:          text  required
  - message:        textarea  required
  - level:          dropdown [info/warning/error]  default: info
  - sound:          checkbox  default: true

SaveImageNode:
  - output_dir:     file-path  default: ./output
  - filename_template: text  default: {timestamp}_{index}
  - format:         dropdown [jpg/png/webp]  default: png
  - quality:        slider 1~100  default: 95

HttpRequestNode:
  - method:         dropdown [GET/POST/PUT/DELETE]  default: POST
  - url:            text  required
  - headers:        textarea  (JSON)
  - body_template:  textarea
  - timeout:        number  default: 30
```

### LOGIC 类

```
ConditionNode:
  - expression:     code  required  (如 "{{score}} > 0.5")
  - true_label:     text  default: "True"
  - false_label:    text  default: "False"

DelayNode:
  - delay_ms:       number  default: 1000
  - mode:           dropdown [wait/throttle]  default: wait

TimerNode:
  - interval_ms:   number  required
  - cron_expression: text  (可选，替代interval)
  - run_on_start:   checkbox  default: false
```

### OUTPUT 类

```
ActionOutputNode:
  - name:           text  required
  - description:    textarea

SaveResultNode:
  - output_type:    dropdown [json/csv/txt]  default: json
  - output_path:    file-path
  - include_metadata: checkbox  default: true

LogNode:
  - level:          dropdown [debug/info/warning/error]  default: info
  - message_template: text
  - prefix:         text
```

---

## 四、执行计划

### P0 — 必须做（阻塞级）

**[Phase A: 后端 config_schema 补全] ✅ 已完成**
- 重写 18 个节点的 `get_definition()`，补全 config_schema
- 制定 widget 类型规范
- 验收：GET /nodes/definitions 返回完整 schema

**[Phase B: 前端节点样式重构] ✅ 已完成**
- 创建自定义 RuleNode.vue 组件
- 节点面板卡片化（带色条、图标、名称）
- 节点状态样式（默认/选中/运行中/完成/错误）

### P1 — 核心体验

**[Phase C: 节点内嵌配置控件] ✅ 已完成**
- 根据 config_schema 动态渲染 slider/dropdown/number/checkbox/textarea/code
- 底部配置摘要
- 变量绑定按钮（📎）

**[Phase D: 属性面板完善] ✅ 已完成**
- 动态表单生成
- 变量绑定 UI（📎按钮插入 {{name}}）
- 断连/重连操作
- 执行状态展示

**[Phase E: 交互完善] ✅ 已完成**
- 复制粘贴（Ctrl+C/V）
- 撤销重做（20步）
- 右键菜单
- 快捷键

### P2 — 体验优化

**[Phase F: 变量系统] ⏳ 未开始**
- 变量 CRUD 面板
- 表达式求值

**[Phase G: 优化增强] ⏳ 未开始**
- Toast 通知
- MiniMap 类别色点
- 节点搜索优化

---

## 五、技术方案

### 5.1 自定义节点组件

```vue
<!-- RuleNode.vue -->
<template>
  <div class="rule-node" :class="[category, { selected, running }]">
    <div class="color-strip"></div>      <!-- 3px色条 -->
    <div class="node-titlebar">
      <NodeIcon :icon="icon" />
      <span class="node-title">{{ label }}</span>
      <button class="menu-btn">⋮</button>
    </div>
    <div class="node-body">
      <div class="ports-left">          <!-- INPUT端口，左侧 -->
        <div v-for="port in inputs" :key="port.name" class="port">
          <Handle type="target" :position="Position.Left" />
          <span>{{ port.label }}</span>
        </div>
      </div>
      <div class="node-widgets">        <!-- 配置控件 -->
        <WidgetRenderer :schema="configSchema" :values="config" />
      </div>
      <div class="ports-right">         <!-- OUTPUT端口，右侧 -->
        <div v-for="port in outputs" :key="port.name" class="port">
          <span>{{ port.label }}</span>
          <Handle type="source" :position="Position.Right" />
        </div>
      </div>
    </div>
    <div class="node-footer">{{ summary }}</div>
  </div>
</template>
```

### 5.2 节点配置存储

```
节点 data 结构:
{
  id: 'node_xxx',
  type: 'rule-node',
  position: { x, y },
  data: {
    type: 'yolo_model',
    label: 'YOLO 检测',
    category: 'detection',
    config: {
      model_id: 'yolov8n',
      confidence: 0.5,
      // ... 从 config_schema 驱动
    }
  }
}
```

### 5.3 前后端同步

1. 前端从 `GET /api/rule-engine/nodes/definitions` 获取 config_schema
2. 前端编辑 config，实时更新节点 data
3. 通过 `PUT /api/rule-engine/graphs/{id}` 保存完整图
4. 后端执行时从图数据读取 config

---

## 六、风险

| 风险 | 应对 |
|------|------|
| 自定义节点工作量大 | 先用 YOLO 节点验证方案，再批量复制 |
| 动态模型列表依赖后端 | model-select 先用静态 enum，后续迭代 |
| 现有图数据迁移 | v2 版本号，图数据加 version 字段 |

---

## 七、技术细节规范

### 6.1 SvgIcon 图标使用规范

**组件引入方式：**

```typescript
// 方式一：全局组件（已在 main.ts 注册，可直接使用）
// 无需 import，在模板中直接使用
<SvgIcon name="icon-name" />

// 方式二：需要显式引入 SvgIcon（如果 IDE 报类型错误）
import SvgIcon from '@/components/SvgIcon.vue'
```

**使用方式：**

```html
<!-- 基本用法 -->
<SvgIcon name="play" />
<SvgIcon name="zoom-in" />
<SvgIcon name="save" />

<!-- 指定尺寸 -->
<SvgIcon name="image" :size="20" />
<SvgIcon name="close" :size="16" />

<!-- 配合样式使用 -->
<SvgIcon name="chevron-right" class="breadcrumb-sep" />
```

**已有图标清单（`webui/src/icons/`）：**

| 类别 | 图标名称 |
|------|----------|
| 导航 | `back`, `chevron-left`, `chevron-right`, `chevron-up`, `chevron-down`, `menu`, `home` |
| 操作 | `save`, `edit`, `delete/trash`, `copy`, `plus`, `close`, `refresh`, `upload`, `download` |
| 视图 | `zoom-in`, `zoom-out`, `fit-view`, `grid`, `minimap` |
| 状态 | `play`, `pause`, `stop`, `check`, `alert`, `star` |
| 文件 | `folder`, `file-text`, `image`, `video`, `tag` |
| 规则引擎专用 | `flow`, `trigger`, `condition`, `action`, `logic`, `brain`, `rocket` |
| 其他 | `clock`, `terminal`, `lightbulb`, `chart`, `box`, `eye`, `undo`, `redo`, `snap` |

**RuleNode 图标迁移方案：**

当前 `icons.ts` 使用 `h()` 渲染函数，需改为使用 `SvgIcon` 组件：

```typescript
// 修改前
import { h } from 'vue'
export const DetectionIcon = () => h('circle', {
  cx: '12', cy: '12', r: '10',
  fill: 'none', stroke: 'currentColor', 'stroke-width': '2'
})

// 修改后 - 复用 icons 目录下已有的 svg 文件
// 可新增专用图标到 icons/ 目录，或使用现有图标组合
```

**新增规则引擎专用图标建议：**

```bash
# webui/src/icons/ 目录下新增
input.svg      # 输入节点图标
detection.svg  # 检测节点图标（靶心）
processing.svg # 处理节点图标（齿轮）
action.svg    # 动作节点图标（闪电）
logic.svg     # 逻辑节点图标（分支）
output.svg    # 输出节点图标（下载）
```

**图标命名规范：**
- 使用 kebab-case 命名（如 `arrow-right.svg`）
- 名称应语义化，反映图标用途
- 避免使用数字或无意义字符

### 6.2 API 端点详细规格

#### 节点定义

```
GET /api/rule-engine/nodes/definitions

Response 200:
[
  {
    "type": "yolo_model",
    "category": "detection",
    "label": "YOLO 检测",
    "description": "使用 YOLO 模型进行目标检测",
    "icon": "detection",
    "inputs": [
      { "name": "image", "type": "image", "label": "图片" },
      { "name": "trigger", "type": "trigger", "label": "触发" }
    ],
    "outputs": [
      { "name": "bboxes", "type": "bbox[]", "label": "边界框" },
      { "name": "scores", "type": "number[]", "label": "置信度" },
      { "name": "categories", "type": "string[]", "label": "类别" }
    ],
    "config_schema": {
      "model_id": {
        "type": "string",
        "title": "模型",
        "widget": "model-select",
        "default": "yolov8n"
      },
      "confidence": {
        "type": "number",
        "title": "置信度阈值",
        "widget": "slider",
        "minimum": 0,
        "maximum": 1,
        "step": 0.05,
        "default": 0.5
      }
    }
  }
]
```

#### 规则图 CRUD

```
POST /api/rule-engine/graphs

Request Body:
{
  "name": "My Rule",
  "description": "规则描述",
  "nodes_json": "[{\"id\":\"n1\",\"type\":\"input\",\"position\":{\"x\":0,\"y\":0},\"data\":{}}]",
  "edges_json": "[]",
  "variables_json": "[]",
  "version": "2.0"
}

Response 201:
{
  "id": 1,
  "name": "My Rule",
  "description": "规则描述",
  "is_active": false,
  "version": "2.0",
  "created_at": "2026-05-06T00:00:00Z",
  "updated_at": "2026-05-06T00:00:00Z"
}
```

```
GET /api/rule-engine/graphs/{graph_id}

Response 200:
{
  "id": 1,
  "name": "My Rule",
  ...
}

GET /api/rule-engine/graphs/{graph_id}/detail

Response 200:
{
  "id": 1,
  "name": "My Rule",
  "nodes": [...],   # 解析后的节点数组
  "edges": [...],   # 解析后的边数组
  "variables": [...]  # 变量列表
}

PUT /api/rule-engine/graphs/{graph_id}

Request Body:
{
  "name": "Updated Name",
  "nodes_json": "...",
  "edges_json": "...",
  "is_active": true
}

DELETE /api/rule-engine/graphs/{graph_id}

Response 200:
{ "message": "规则图已删除" }
```

#### 规则图校验/激活

```
POST /api/rule-engine/graphs/{graph_id}/validate

Response 200:
{
  "valid": true,
  "error": null
}

POST /api/rule-engine/graphs/{graph_id}/activate

Response 200:
{
  "id": 1,
  "is_active": true,
  ...
}

POST /api/rule-engine/graphs/{graph_id}/deactivate

Response 200:
{
  "id": 1,
  "is_active": false,
  ...
}
```

#### 执行

```
POST /api/rule-engine/execute

Request Body:
{
  "graph_id": 1,
  "trigger_type": "manual",
  "trigger_data": null
}

Response 202:
{
  "execution_id": 123,
  "status": "running",
  "result": { "message": "执行已启动" }
}

GET /api/rule-engine/executions?graph_id=1&limit=50

Response 200:
[
  {
    "id": 123,
    "graph_id": 1,
    "status": "success",
    "start_time": "2026-05-06T00:00:00Z",
    "end_time": "2026-05-06T00:00:05Z",
    "trigger_type": "manual"
  }
]

GET /api/rule-engine/executions/{execution_id}

Response 200:
{
  "id": 123,
  "graph_id": 1,
  "status": "success",
  "start_time": "...",
  "end_time": "...",
  "trigger_type": "manual"
}

GET /api/rule-engine/executions/{execution_id}/logs

Response 200:
{
  "execution": { ... },
  "node_logs": [
    {
      "node_id": "n1",
      "node_type": "image_input",
      "status": "success",
      "input_data": { ... },
      "output_data": { ... },
      "error_message": null,
      "start_time": "...",
      "end_time": "..."
    }
  ]
}
```

### 6.3 Pinia Store 设计

```typescript
// webui/src/stores/ruleEngine.ts

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { ruleEngineApi } from '@/api'

// ============ 类型定义 ============

interface NodeDefinition {
  type: string
  category: string
  label: string
  description?: string
  icon?: string
  inputs: Array<{ name: string; type: string; label?: string }>
  outputs: Array<{ name: string; type: string; label?: string }>
  config_schema: Record<string, ConfigSchemaProperty>
}

interface ConfigSchemaProperty {
  type: string
  title?: string
  description?: string
  default?: any
  minimum?: number
  maximum?: number
  step?: number
  enum?: string[]
  widget?: string
  visible?: string  // 条件可见，如 "source=file"
}

interface GraphNode {
  id: string
  type: string
  position: { x: number; y: number }
  data: {
    type: string
    label?: string
    category: string
    inputs?: Array<{ name: string; type: string; label?: string }>
    outputs?: Array<{ name: string; type: string; label?: string }>
    configSchema?: Record<string, ConfigSchemaProperty>
    config?: Record<string, any>
    status?: 'idle' | 'running' | 'success' | 'failed'
  }
}

interface GraphEdge {
  id: string
  source: string
  target: string
  source_handle?: string
  target_handle?: string
}

interface Variable {
  name: string
  type: string
  defaultValue?: any
  description?: string
}

// ============ Store 定义 ============

export const useRuleEngineStore = defineStore('ruleEngine', () => {
  // ---- 状态 ----
  const nodeDefinitions = ref<NodeDefinition[]>([])
  const currentGraph = ref<{
    id: number
    name: string
    description?: string
    is_active: boolean
    nodes: GraphNode[]
    edges: GraphEdge[]
    variables: Variable[]
  } | null>(null)
  const selectedNodeId = ref<string | null>(null)

  // 执行状态
  const executingGraphId = ref<number | null>(null)
  const executionHistory = ref<Array<{
    id: number
    status: string
    start_time: string
    end_time?: string
  }>>([])

  // Undo/Redo 栈
  const historyStack = ref<Array<{ nodes: GraphNode[]; edges: GraphEdge[] }>>([])
  const historyIndex = ref(-1)
  const maxHistorySize = 20

  // 变量列表
  const variables = ref<Variable[]>([])

  // ---- 计算属性 ----
  const selectedNode = computed(() =>
    currentGraph.value?.nodes.find(n => n.id === selectedNodeId.value) ?? null
  )

  const canUndo = computed(() => historyIndex.value > 0)
  const canRedo = computed(() => historyIndex.value < historyStack.value.length - 1)

  const nodeDefinitionsByCategory = computed(() => {
    const map: Record<string, NodeDefinition[]> = {}
    for (const def of nodeDefinitions.value) {
      if (!map[def.category]) map[def.category] = []
      map[def.category].push(def)
    }
    return map
  })

  // ---- Actions ----
  async function fetchNodeDefinitions() {
    const res = await ruleEngineApi.getNodeDefinitions()
    nodeDefinitions.value = res.data
    return res.data
  }

  async function fetchGraph(id: number) {
    const res = await ruleEngineApi.getGraphDetail(id)
    currentGraph.value = res.data
    // 初始化撤销栈
    saveToHistory()
    return res.data
  }

  async function saveGraph() {
    if (!currentGraph.value) return
    const nodesJson = JSON.stringify(currentGraph.value.nodes)
    const edgesJson = JSON.stringify(currentGraph.value.edges)
    const variablesJson = JSON.stringify(currentGraph.value.variables)

    await ruleEngineApi.updateGraph(currentGraph.value.id, {
      name: currentGraph.value.name,
      nodes_json: nodesJson,
      edges_json: edgesJson,
      variables_json: variablesJson,
    })
  }

  // ---- 节点操作 ----
  function addNode(def: NodeDefinition, position: { x: number; y: number }) {
    if (!currentGraph.value) return

    const id = `node_${Date.now()}`
    const newNode: GraphNode = {
      id,
      type: 'rule-node',
      position,
      data: {
        type: def.type,
        label: def.label,
        category: def.category,
        inputs: def.inputs,
        outputs: def.outputs,
        configSchema: def.config_schema,
        config: getDefaultConfig(def.config_schema),
        status: 'idle',
      },
    }

    currentGraph.value.nodes.push(newNode)
    saveToHistory()
    return id
  }

  function updateNodeConfig(nodeId: string, key: string, value: any) {
    const node = currentGraph.value?.nodes.find(n => n.id === nodeId)
    if (node) {
      node.data.config = node.data.config || {}
      node.data.config[key] = value
    }
  }

  function removeNode(nodeId: string) {
    if (!currentGraph.value) return
    currentGraph.value.nodes = currentGraph.value.nodes.filter(n => n.id !== nodeId)
    currentGraph.value.edges = currentGraph.value.edges.filter(
      e => e.source !== nodeId && e.target !== nodeId
    )
    if (selectedNodeId.value === nodeId) selectedNodeId.value = null
    saveToHistory()
  }

  function selectNode(nodeId: string | null) {
    selectedNodeId.value = nodeId
  }

  // ---- 边操作 ----
  function addEdge(edge: Omit<GraphEdge, 'id'>) {
    if (!currentGraph.value) return
    const id = `edge_${Date.now()}`
    currentGraph.value.edges.push({ ...edge, id })
    saveToHistory()
  }

  function removeEdge(edgeId: string) {
    if (!currentGraph.value) return
    currentGraph.value.edges = currentGraph.value.edges.filter(e => e.id !== edgeId)
    saveToHistory()
  }

  // ---- Undo/Redo ----
  function saveToHistory() {
    if (!currentGraph.value) return

    const snapshot = {
      nodes: JSON.parse(JSON.stringify(currentGraph.value.nodes)),
      edges: JSON.parse(JSON.stringify(currentGraph.value.edges)),
    }

    // 截断 redo 栈
    historyStack.value = historyStack.value.slice(0, historyIndex.value + 1)
    historyStack.value.push(snapshot)

    // 限制栈大小
    if (historyStack.value.length > maxHistorySize) {
      historyStack.value.shift()
    } else {
      historyIndex.value++
    }
  }

  function undo() {
    if (!canUndo.value || !currentGraph.value) return
    historyIndex.value--
    const snapshot = historyStack.value[historyIndex.value]
    currentGraph.value.nodes = JSON.parse(JSON.stringify(snapshot.nodes))
    currentGraph.value.edges = JSON.parse(JSON.stringify(snapshot.edges))
  }

  function redo() {
    if (!canRedo.value || !currentGraph.value) return
    historyIndex.value++
    const snapshot = historyStack.value[historyIndex.value]
    currentGraph.value.nodes = JSON.parse(JSON.stringify(snapshot.nodes))
    currentGraph.value.edges = JSON.parse(JSON.stringify(snapshot.edges))
  }

  // ---- 变量操作 ----
  function addVariable(variable: Variable) {
    variables.value.push(variable)
  }

  function removeVariable(name: string) {
    variables.value = variables.value.filter(v => v.name !== name)
  }

  function updateVariable(name: string, updates: Partial<Variable>) {
    const v = variables.value.find(var => var.name === name)
    if (v) Object.assign(v, updates)
  }

  // ---- 辅助函数 ----
  function getDefaultConfig(schema: Record<string, ConfigSchemaProperty>): Record<string, any> {
    const config: Record<string, any> = {}
    for (const [key, prop] of Object.entries(schema)) {
      if (prop.default !== undefined) {
        config[key] = prop.default
      }
    }
    return config
  }

  return {
    // 状态
    nodeDefinitions,
    currentGraph,
    selectedNodeId,
    executingGraphId,
    executionHistory,
    variables,

    // 计算属性
    selectedNode,
    canUndo,
    canRedo,
    nodeDefinitionsByCategory,

    // Actions
    fetchNodeDefinitions,
    fetchGraph,
    saveGraph,
    addNode,
    updateNodeConfig,
    removeNode,
    selectNode,
    addEdge,
    removeEdge,
    undo,
    redo,
    addVariable,
    removeVariable,
    updateVariable,
  }
})
```

### 6.4 变量绑定表达式语法

#### 变量引用格式

```
{{variable_name}}           # 引用简单变量
{{object.property}}         # 引用对象属性
{{array[index]}}            # 引用数组元素
{{object.property.nested}}  # 深層属性访问
```

#### 支持的数据类型

| 类型 | 示例 | 说明 |
|------|------|------|
| `string` | `{{input_path}}` | 字符串变量 |
| `number` | `{{confidence}}` | 数字变量 |
| `boolean` | `{{enable_flag}}` | 布尔变量 |
| `image` | `{{image_data}}` | 图像数据 |
| `bbox[]` | `{{detections}}` | 边界框数组 |
| `trigger` | `{{trigger_signal}}` | 触发信号 |

#### 内置变量

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `$now` | datetime | 当前时间戳 |
| `$graph.id` | number | 当前规则图 ID |
| `$execution.id` | number | 当前执行记录 ID |
| `$node.id` | string | 当前节点 ID |
| `$node.label` | string | 当前节点名称 |

#### 表达式示例

```
# 条件判断
{{score}} > 0.5
{{label}} == "person"
{{enable_flag}} == true

# 数值计算
{{confidence}} * 100
{{min({{scores}})}}

# 字符串操作
{{filename}}.startsWith("img_")
{{path}}.split("/").last()

# 数组操作
{{bboxes}}.length > 0
{{labels}}[0] == "car"
```

#### 表达式引擎要求

- 使用 JavaScript 表达式语法
- 支持基本的数学运算：`+`, `-`, `*`, `/`, `%`
- 支持比较运算：`==`, `===`, `!=`, `!==`, `>`, `<`, `>=`, `<=`
- 支持逻辑运算：`&&`, `||`, `!`
- 支持三元运算符：`condition ? true_val : false_val`
- 支持括号分组：`(a + b) * c`

### 6.5 执行状态机

#### 节点状态

```
┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐
│  idle   │ ──> │ running │ ──> │ success │ ──> │  idle   │
└─────────┘     └─────────┘     └─────────┘     └─────────┘
     │               │               │
     │               │               │
     v               v               v
┌─────────────────────────────────────────┐
│                  failed                  │
└─────────────────────────────────────────┘
```

| 状态 | 说明 | 触发条件 |
|------|------|----------|
| `idle` | 空闲/等待执行 | 初始状态 / 执行完成后重置 |
| `running` | 执行中 | 节点开始处理 |
| `success` | 执行成功 | 节点正常完成 |
| `failed` | 执行失败 | 节点处理出错 |

#### 节点执行流程

```
1. 接收上游节点数据
   ↓
2. 检查必填输入端口是否已连接
   ↓ (未连接则 failed)
3. 从 config 读取节点配置
   ↓
4. 执行节点逻辑
   ↓
5. 产出生效数据到输出端口
   ↓
6. 通知下游节点数据就绪
```

#### 图执行流程

```
1. 找出所有 INPUT/TRIGGER 节点（无上游依赖）
   ↓
2. 并行执行这些节点
   ↓
3. 节点完成后，通知依赖它的下游节点
   ↓
4. 下游节点检查所有输入是否就绪
   ↓ (全部就绪)
5. 执行下游节点
   ↓
6. 重复直到所有节点完成或遇到错误
   ↓
7. 图执行结束，更新执行状态
```

#### WebSocket 进度推送

```typescript
// 连接 WebSocket
ws://host/api/rule-engine/ws/executions/{execution_id}

// 推送消息格式
{
  "type": "node_start" | "node_complete" | "node_error" | "execution_complete" | "execution_error",
  "execution_id": 123,
  "node_id": "n1",
  "data": { ... },
  "timestamp": "2026-05-06T00:00:00Z"
}

// node_start
{ "type": "node_start", "node_id": "n1", "timestamp": "..." }

// node_complete
{ "type": "node_complete", "node_id": "n1", "output_data": {...}, "duration_ms": 123, "timestamp": "..." }

// node_error
{ "type": "node_error", "node_id": "n1", "error": "Error message", "timestamp": "..." }

// execution_complete
{ "type": "execution_complete", "status": "success", "total_duration_ms": 1234, "timestamp": "..." }

// execution_error
{ "type": "execution_error", "status": "failed", "error": "Error message", "failed_node_id": "n1", "timestamp": "..." }
```

---

## 八、Phase A-G 详细实施步骤

### Phase A: 后端 config_schema 补全

**目标：** 补全 18 个节点的 `get_definition()`，完善 config_schema

**修改文件：**

| 文件 | 改动内容 |
|------|----------|
| `backend/services/rule_engine/nodes/input_nodes.py` | 补全 ImageCaptureNode, VideoCaptureNode, WebhookTriggerNode 的 config_schema |
| `backend/services/rule_engine/nodes/detection_nodes.py` | 补全 YOLOModelNode, ObjectDetectorNode, YOLOTriggerNode 的 config_schema |
| `backend/services/rule_engine/nodes/processing_nodes.py` | 补全 CropNode, ResizeNode, NormalizeNode, FilterNode 的 config_schema |
| `backend/services/rule_engine/nodes/actions.py` | 补全 MouseClickNode, KeyPressNode, NotificationNode, SaveImageNode, HttpRequestNode 的 config_schema |
| `backend/services/rule_engine/nodes/logic.py` | 补全 ConditionNode, DelayNode, TimerNode 的 config_schema |
| `backend/services/rule_engine/nodes/output_nodes.py` | 补全 ActionOutputNode, SaveResultNode, LogNode 的 config_schema |

**验收标准：** `GET /api/rule-engine/nodes/definitions` 返回所有节点的完整 config_schema

### Phase B: 前端节点样式重构

**目标：** 创建自定义 RuleNode.vue，节点面板卡片化

**修改文件：**

| 文件 | 改动内容 |
|------|----------|
| `webui/src/components/rule-engine/RuleNode.vue` | 重写节点模板，使用 SvgIcon，样式对齐设计规范 |
| `webui/src/components/rule-engine/icons.ts` | 迁移到使用 SvgIcon 组件 |
| `webui/src/icons/` | 新增 `detection.svg`, `processing.svg`, `action.svg`, `logic.svg`, `output.svg` |
| `webui/src/views/RuleCanvas.vue` | 适配新的节点组件，节点拖拽使用自定义节点类型 |

**验收标准：** 节点显示 3px 色条、图标、标题、内嵌控件、底部摘要

### Phase C: 节点内嵌配置控件

**目标：** 根据 config_schema 动态渲染控件

**修改文件：**

| 文件 | 改动内容 |
|------|----------|
| `webui/src/components/rule-engine/WidgetRenderer.vue` | 新建通用控件渲染组件 |
| `webui/src/components/rule-engine/RuleNode.vue` | 使用 WidgetRenderer 替代手写控件 |
| `webui/src/components/rule-engine/SliderWidget.vue` | 新建 slider 控件 |
| `webui/src/components/rule-engine/DropdownWidget.vue` | 新建下拉选择控件 |
| `webui/src/components/rule-engine/NumberWidget.vue` | 新建数字输入控件 |
| `webui/src/components/rule-engine/CheckboxWidget.vue` | 新建开关控件 |
| `webui/src/components/rule-engine/TextareaWidget.vue` | 新建多行文本控件 |
| `webui/src/components/rule-engine/CodeWidget.vue` | 新建代码编辑器控件 |
| `webui/src/components/rule-engine/ModelSelectWidget.vue` | 新建模型选择控件 |

**验收标准：** 根据 config_schema 自动渲染对应控件，支持 slider/dropdown/number/checkbox/textarea/code/model-select

### Phase D: 属性面板完善

**目标：** 完善右侧属性面板

**修改文件：**

| 文件 | 改动内容 |
|------|----------|
| `webui/src/components/rule-engine/PropertyPanel.vue` | 新建属性面板组件 |
| `webui/src/components/rule-engine/VariableBinder.vue` | 新建变量绑定组件 |
| `webui/src/components/rule-engine/ExecutionStatus.vue` | 新建执行状态展示组件 |
| `webui/src/views/RuleCanvas.vue` | 集成属性面板 |

**验收标准：** 属性面板显示选中节点的完整配置，支持变量绑定（📎按钮），显示执行状态

### Phase E: 交互完善

**目标：** 复制粘贴、撤销重做、右键菜单、快捷键

**修改文件：**

| 文件 | 改动内容 |
|------|----------|
| `webui/src/stores/ruleEngine.ts` | 实现 undo/redo 栈（已在本文档 6.3 节定义） |
| `webui/src/views/RuleCanvas.vue` | 添加 Ctrl+C/V 复制粘贴、右键菜单、快捷键监听 |

**验收标准：** 支持 Ctrl+Z 撤销、Ctrl+Y 重做、Ctrl+C/V 复制粘贴节点、右键菜单

### Phase F: 变量系统

**目标：** 变量 CRUD 面板、表达式求值

**修改文件：**

| 文件 | 改动内容 |
|------|----------|
| `webui/src/components/rule-engine/VariablePanel.vue` | 新建变量管理面板 |
| `webui/src/stores/ruleEngine.ts` | 变量相关状态和操作（已在本文档 6.3 节定义） |
| `webui/src/utils/variableExpression.ts` | 新建变量表达式解析/求值工具 |

**验收标准：** 可创建/编辑/删除变量，节点配置中可引用变量

### Phase G: 优化增强

**目标：** Toast 通知、MiniMap 类别色点、节点搜索优化

**修改文件：**

| 文件 | 改动内容 |
|------|----------|
| `webui/src/components/common/Toast.vue` | 复用或新建 Toast 通知组件 |
| `webui/src/views/RuleCanvas.vue` | MiniMap 显示类别色点 |

**验收标准：** 执行完成/失败有 Toast 通知，MiniMap 上显示彩色节点点

---

## 九、结论

本次重构解决三个核心问题：

1. **节点可配置** — 每个节点有完整 config_schema，能调参
2. **节点样式好看** — ComfyUI 风格：色条+标题+内嵌控件+底部摘要
3. **属性面板实用** — 动态表单+变量绑定+执行状态+断连操作

**建议先从 YOLO 检测节点走一遍完整流程（Phase A→B），验证方案后再批量复制到其他 17 个节点。**

**前端图标规范：** 统一使用 `SvgIcon` 组件，图标名称对应 `webui/src/icons/` 目录下的 SVG 文件名。
