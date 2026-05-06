# CogniFlow 规则引擎 - 全面重构设计方案 v2

> **文档版本：** v2.0
> **创建时间：** 2026-05-06
> **状态：** 待老大评审后执行
> **基于：** 老大审核反馈 + ComfyUI 参考 + Phase 1-6 设计文档

---

## 一、问题诊断

### 1.1 老大原话

> "规则引擎这块前端根本没法用，节点一大堆但是根本没有完整的实现，每个节点都没有可配置的东西，节点样式很难看"

### 1.2 具体问题清单

| 维度 | 问题 | 影响 |
|------|------|------|
| **节点可配置性** | 节点只有 inputs/outputs，config_schema 全为空或无意义默认值 | 节点无法定制行为 |
| **节点样式** | 面板里的 node-item 只是文字列表，没有可视化卡片；画布节点用的是 VueFlow 默认样式 | 视觉粗糙，不专业 |
| **属性面板** | 配置表单简陋，没有类型化输入（滑块、开关、颜色选择器等） | 无法精细配置 |
| **节点外观** | 面板节点和画布节点都缺乏 ComfyUI 那样的层次感（标题栏+分类标签+端口组） | 难以一眼区分功能 |
| **交互体验** | 复制粘贴、撤销重做不完整；右键菜单内容少 | 效率低 |
| **变量系统** | `{{variable}}` 语法有，但 UI 支持粗糙 | 难以使用 |

---

## 二、参考标准：ComfyUI 节点设计

### 2.1 ComfyUI 节点结构（权威参考）

```
┌──────────────────────────────────────────┐
│ [titlebar - category color strip]        │  ← 顶部类别色条（3px）
│  🖼️ Image Load     [type: image_load]    │  ← 标题栏：图标 + 名称 + 类型标签
├──────────────────────────────────────────┤
│                                           │
│  OUTPUTS:        INPUTS:                  │
│  ┌────────┐     ┌────────┐               │
│  │ IMAGE  │────▶│ IMAGE  │ [Load Image]  │  ← 左侧输出/右侧输入端口 + 标签
│  └────────┘     └────────┘               │
│                  ┌────────┐               │
│                  │MASK(α)│               │
│                  └────────┘               │
│                                           │
├──────────────────────────────────────────┤
│ [PRIMARY TEXT]  [description text]       │  ← 底部：可选描述/次要信息
└──────────────────────────────────────────┘
```

**ComfyUI 节点视觉特征：**
1. 顶部 3px 类别色条（LOAD:灰色 / IMAGE:蓝色 / MASK:紫色 / etc.）
2. 标题栏包含图标 + 显示名 + 节点类型标签
3. 左侧为 OUTPUT 端口，右侧为 INPUT 端口（数据从左向右流动）
4. 端口带文字标签，鼠标悬停显示类型
5. 节点有圆角边框、淡阴影
6. 选中时有青色外发光
7. 运行中有脉冲动画

### 2.2 ComfyUI 类别颜色体系（参考）

```
LOAD        #888888  (灰)
IMAGE       #4488FF  (蓝)
MASK        #AA44FF  (紫)
CONDITIONING #FFAA44 (橙)
MODEL       #22DD22  (绿)
CLIP        #FF4488 (粉)
TEXT        #FFAAAA (浅红)
WIDGETS     #888888  (灰)
```

CogniFlow 应该有自己的体系（已有 6 色，但用得不够彻底/一致）。

---

## 三、重构设计方案

### 3.1 节点端口设计原则

**三种端口类型：**

```
INPUT 节点（数据生产者）
┌──────────────────────────────────┐
│ ■■ [📥]  Image Input        [⋮] │  ← 顶部色条 + 标题
├──────────────────────────────────┤
│                                  │
│  采集来源: [File           ▼]   │  ← 配置控件
│  文件路径: [______________...]   │
│                                  │
│  image │                          ← 只有 OUTPUT 端口（右侧）
│  width │
│  height│
├──────────────────────────────────┤
│ 📷 file: img_001.jpg             │  ← 底部摘要
└──────────────────────────────────┘

PROCESSING 节点（处理者，左进右出）
┌────────────────────────────────────────────────────────────────┐
│ ■■ [🔧]  Resize                       [⋮]                   │
├─────────────┬──────────────────────────────┬──────────────────┤
│             │                              │                  │
│ ● image     │  width:  [____640___]      │ ● image         │
│ ● bbox      │  height: [____480___]      │ ● bbox          │
│             │  mode:   [fit          ▼]  │                  │
│             │                              │                  │
└─────────────┴──────────────────────────────┴──────────────────┘
左侧 INPUT                    右侧 OUTPUT

ACTION 节点（纯执行，左进无出）
┌──────────────────────────────────┐
│ ■■ [🔔]  Notification      [⋮] │
├──────────────────────────────────┤
│                                  │
│ ● title   ● message             │  ← 只有 INPUT 端口（左侧）
│                                  │
│  级别: [info ▼]   声音: [●]     │  ← 配置控件
│                                  │
└──────────────────────────────────┘

TRIGGER 节点（无进右出）
┌──────────────────────────────────┐
│ ■■ [⏱️]  Timer              [⋮] │
├──────────────────────────────────┤
│                                  │
│  间隔: [____1000___] ms         │  ← 配置控件
│  启动时执行: [●]                │
│                                  │
│                          ● tick │  ← 只有 OUTPUT 端口（右侧）
│                                  │
└──────────────────────────────────┘
```

**设计原则：**
1. **INPUT 节点** — 只有 OUTPUT 端口（如 Image/Video/RabbitMQ）
2. **ACTION 节点** — 只有 INPUT 端口（如 Notification/Save/Click）
3. **PROCESSING 节点** — 左侧 INPUT + 右侧 OUTPUT
4. **TRIGGER 节点** — 只有 OUTPUT 端口（如 Timer/Webhook/Cron）
5. **LOGIC 节点** — 左侧 INPUT + 右侧 OUTPUT（OUTPUT 代表分支）
6. **OUTPUT 节点** — 左侧 INPUT + 可选 OUTPUT（如 Log 节点无 OUTPUT）

> **注意：** 画布节点的实际端口数量和类型完全由节点的 `definition.inputs` 和 `definition.outputs` 决定，前端按需渲染，无需硬编码。

> ⚠️ **端口方向确认：左进右出**
> - **左侧 = INPUT** — 数据从其他节点流入
> - **右侧 = OUTPUT** — 数据从这里流出给下游
> - 数据从左向右流动，符合自然直觉

### 3.2 节点面板结构（侧边栏）

```
┌─────────────────────────────┐
│ 🔍 搜索节点...              │  ← 已有，需优化
├─────────────────────────────┤
│ ┌─ 📥 INPUT ────────────┐   │
│ │  ┌─────────────────┐ │   │
│ │  │ 🖼 Image Input   │ │   │  ← 节点卡片，带类别色条
│ │  │ 外部图片输入     │ │   │
│ │  └─────────────────┘ │   │
│ │  ┌─────────────────┐ │   │
│ │  │ 📹 Video Feed   │ │   │
│ │  └─────────────────┘ │   │
│ └────────────────────────┘   │
│ ┌─ 🎯 DETECTION ─────────┐   │
│ │  ┌─────────────────┐ │   │
│ │  │ 🔬 YOLO Detect  │ │   │  ← 检测节点，检测色条
│ │  └─────────────────┘ │   │
│ └────────────────────────┘   │
│          ...                 │
└─────────────────────────────┘
```

**设计要点：**
1. 每个节点用卡片展示，包含色条、图标、名称、描述
2. 拖拽时显示节点预览
3. 支持双击快速添加

### 3.3 属性面板结构（右侧）

```
┌───────────────────────────────┐
│ 🧭 YOLO 检测              [×] │
├───────────────────────────────┤
│                               │
│ 节点名称   [YOLO 检测 v2____] │
│ 节点 ID    node_abc123        │
│ 节点类型   yolo_model         │
│                               │
├─ 📥 输入配置 ─────────────────┤
│ image      ● 已连接 (node_1) │
│            [查看源] [断连]   │
│ confidence [0.5____] 📎 0.25~1│  ← slider + 变量按钮 + 范围提示
│ model_id   [yolov8n.pt___▼] │  ← dropdown
│ iou_thr    [0.45___] 📎     │
│ max_det    [300____] 📎     │
│                               │
├─ 📤 输出配置 ─────────────────┤
│ bboxes     → node_3          │
│ scores     → [未连接]        │
│ categories → [未连接]        │
│                               │
├─ ⚡ 执行状态 ─────────────────┤
│ [✓] 已执行  耗时: 123ms      │
│ 结果数量: 5 个目标           │
│                               │
├─ 🗑️ 操作 ────────────────────┤
│ [删除节点]  [复制] [查看日志]│
└───────────────────────────────┘
```

---

## 四、节点可配置性设计

### 4.1 核心问题

目前后端节点定义返回的 `config_schema` 基本为空或仅有默认值，无法驱动前端渲染有意义的配置表单。

### 4.2 config_schema 规范（每个节点必须定义）

参考 JSON Schema + ComfyUI widgets:

```typescript
// 节点配置 schema 示例：YOLOModelNode
{
  "model_id": {
    "type": "string",
    "title": "模型",
    "description": "选择要使用的 YOLO 模型",
    "default": "",
    "enum": [],  // 动态从 /api/model/list 获取
    "widget": "model-select",  // 特殊 widget 类型
  },
  "confidence": {
    "type": "number",
    "title": "置信度阈值",
    "description": "只保留置信度 >= threshold 的检测结果",
    "default": 0.5,
    "minimum": 0,
    "maximum": 1,
    "step": 0.05,
    "widget": "slider",  // 滑块 + 数字输入
  },
  "iou_threshold": {
    "type": "number",
    "title": "IOU 阈值",
    "description": "NMS 的 IOU 阈值",
    "default": 0.45,
    "minimum": 0,
    "maximum": 1,
    "step": 0.05,
    "widget": "slider",
  },
  "max_detections": {
    "type": "integer",
    "title": "最大检测数",
    "description": "每张图最多检测多少个目标",
    "default": 300,
    "minimum": 1,
    "maximum": 1000,
    "step": 1,
    "widget": "number",
  },
  "device": {
    "type": "string",
    "title": "推理设备",
    "default": "auto",
    "enum": ["auto", "cuda", "cpu"],
    "widget": "dropdown",
  },
}
```

### 4.3 Widget 类型规范

| widget | 对应表单 | 说明 |
|--------|---------|------|
| `text` | 单行文本输入 | 默认 |
| `number` | 数字输入框 | 整数/小数 |
| `slider` | 滑块 + 数字输入 | 带范围 |
| `dropdown` | 下拉选择 | enum 列表 |
| `model-select` | 模型选择器 | 特殊，动态加载模型列表 |
| `checkbox` | 开关 toggle | boolean |
| `color-picker` | 颜色选择 | string hex |
| `file-path` | 文件路径输入 + 浏览 | 路径选择 |
| `textarea` | 多行文本 | 长文本 |
| `code` | 代码编辑器 | 表达式/正则 |

### 4.4 各节点配置项（完整清单）

#### Input 类（3个节点）
```
ImageCaptureNode:
  - source: dropdown [camera, file, url] default: file
  - file_path: file-path visible when source=file
  - camera_id: number visible when source=camera default: 0
  - interval: number (秒) visible when source=camera default: 1.0

VideoCaptureNode:
  - source: dropdown [stream, file] default: file
  - stream_url: text visible when source=stream
  - file_path: file-path visible when source=file
  - fps: number default: 30

WebhookTriggerNode:
  - path: text (URL 路径) required
  - method: dropdown [GET, POST, ANY] default: ANY
  - auth_type: dropdown [none, bearer, basic] default: none
```

#### Detection 类（4个节点）
```
YOLOModelNode:
  - model_id: model-select required
  - confidence: slider 0~1 default: 0.5
  - iou_threshold: slider 0~1 default: 0.45
  - max_detections: number 1~1000 default: 300
  - device: dropdown [auto, cuda, cpu] default: auto

ObjectDetectorNode:
  - model_type: dropdown [yolo, ssd, detectron2] default: yolo
  - confidence: slider 0~1 default: 0.5
  - labels: textarea (逗号分隔的类别名)

YOLOTriggerNode:
  - model_id: model-select required
  - target_labels: textarea (要触发检测的类别)
  - min_confidence: slider 0~1 default: 0.3
  - trigger_on: dropdown [any, all] default: any
```

#### Processing 类（4个节点）
```
CropNode:
  - mode: dropdown [bbox, polygon, custom] default: bbox
  - padding: number default: 10 (pixels)

ResizeNode:
  - width: number required
  - height: number required
  - mode: dropdown [stretch, fit, fill] default: fit
  - maintain_aspect: checkbox default: true

NormalizeNode:
  - method: dropdown [minmax, zscore] default: minmax

FilterNode:
  - condition: textarea (条件表达式，如 "score > 0.5")
  - preview: checkbox default: false
```

#### Action 类（5个节点）
```
MouseClickNode:
  - button: dropdown [left, right, middle] default: left
  - action_type: dropdown [click, double-click, down, up] default: click
  - x: number (屏幕坐标)
  - y: number

KeyPressNode:
  - key: text required
  - action_type: dropdown [press, down, up] default: press

NotificationNode:
  - title: text required
  - message: textarea required
  - level: dropdown [info, warning, error] default: info
  - sound: checkbox default: true

SaveImageNode:
  - output_dir: file-path default: ./output
  - filename_template: text default: {timestamp}_{index}
  - format: dropdown [jpg, png, webp] default: png
  - quality: slider 1~100 default: 95 (jpg/webp)

HttpRequestNode:
  - method: dropdown [GET, POST, PUT, DELETE] default: POST
  - url: text required
  - headers: textarea (JSON 格式)
  - body_template: textarea
  - timeout: number default: 30
```

#### Logic 类（3个节点）
```
ConditionNode:
  - expression: code required (如 "{{score}} > 0.5")
  - true_label: text default: "True"
  - false_label: text default: "False"

DelayNode:
  - delay_ms: number default: 1000
  - mode: dropdown [wait, throttle] default: wait

TimerNode:
  - interval_ms: number required
  - cron_expression: text (可选，替代 interval)
  - run_on_start: checkbox default: false
```

#### Output 类（3个节点）
```
ActionOutputNode:
  - name: text required
  - description: textarea

SaveResultNode:
  - output_type: dropdown [json, csv, txt] default: json
  - output_path: file-path
  - include_metadata: checkbox default: true

LogNode:
  - level: dropdown [debug, info, warning, error] default: info
  - message_template: text
  - prefix: text
```

---

## 五、UI 风格规范

### 5.1 配色体系（基于现有 6 色，完善比例）

```
背景色:
  --bg-canvas:      #0a0a0e   (画布背景)
  --bg-panel:       #12121a   (面板背景)
  --bg-card:        #1a1a24   (卡片/节点背景)
  --bg-input:       #0e0e16   (输入框背景)
  --bg-hover:       #22222e   (hover 态)

边框色:
  --border-default: #2a2a3a
  --border-hover:   #3a3a4a
  --border-active:  #00f0ff  (选中/活跃)

类别色 (节点色条 + 面板分类):
  --color-input:    #4CFF4C   (绿 - 输入)
  --color-detection: #00f0ff  (青 - 检测)
  --color-processing: #FFFF4C (黄 - 处理)
  --color-action:   #FF7F4C   (橙 - 动作)
  --color-logic:    #DC4FDC   (紫 - 逻辑)
  --color-output:    #FF4C4C   (红 - 输出)

功能色:
  --color-success:  #4cff4c
  --color-warning:  #ffaa44
  --color-error:    #ff4c4c
  --color-info:     #00f0ff

文字色:
  --text-primary:   #e0e0e8
  --text-secondary: #8888aa
  --text-muted:     #555566
```

### 5.2 字体规范

```
字体族:
  - UI: 'Inter', 'SF Pro Display', -apple-system, sans-serif
  - 代码/数字: 'JetBrains Mono', 'Fira Code', monospace

字号:
  - 节点标题: 13px / font-weight: 600
  - 节点标签: 11px / font-weight: 400
  - 配置标签: 12px / font-weight: 500
  - 配置值:   12px / font-weight: 400
  - 描述文字: 10px / font-weight: 400
```

### 5.3 间距规范

```
节点内:
  - 标题栏高度: 32px
  - 色条高度: 3px
  - 端口行高: 28px
  - 配置行高: 36px
  - 底部摘要高: 24px
  - 内边距: 8px 12px

面板:
  - 卡片内边距: 12px
  - 分类间距: 16px
  - 表单项间距: 12px

圆角:
  - 节点: 8px
  - 按钮: 6px
  - 输入框: 4px
  - 面板: 12px
```

### 5.4 阴影规范

```
节点默认:
  box-shadow: 0 2px 8px rgba(0,0,0,0.3)

节点选中:
  box-shadow: 0 0 0 2px var(--border-active),
              0 4px 20px rgba(0,240,255,0.15)

面板阴影:
  box-shadow: -4px 0 20px rgba(0,0,0,0.3)
```

---

## 六、执行计划

### Phase A: 节点可配置性（后端优先）

**目标：** 每个节点都有完整 config_schema，属性面板能渲染所有配置项。

| 步骤 | 内容 | 工作量 |
|------|------|--------|
| A1 | 制定 config_schema 规范（widget types + schema 格式） | 1天 |
| A2 | 重写所有 18 个节点的 get_definition()，补全 config_schema | 2天 |
| A3 | 新增 model-select / slider / dropdown / number / checkbox 5种 widget 的后端 schema | - |
| A4 | 后端 API 调整：model-select 节点需要动态加载模型列表 | 1天 |
| A5 | 后端验证：GET /nodes/definitions 返回完整 schema | - |

**验收：** 前端属性面板能渲染所有 18 个节点的配置表单，每个配置项有合适的输入控件。

---

### Phase B: 节点样式重构（前端优先）

**目标：** 画布节点和面板节点都达到 ComfyUI 的视觉水准。

| 步骤 | 内容 | 工作量 |
|------|------|--------|
| B1 | 创建自定义 VueFlow 节点组件 `RuleNode.vue`（色条+标题+端口+内嵌配置） | 2天 |
| B2 | 节点面板卡片重构：节点面板展示卡片而非文字列表 | 1天 |
| B3 | 画布节点内嵌配置控件渲染（根据 config_schema 动态渲染 slider/dropdown 等） | 2天 |
| B4 | 节点状态样式（默认/选中/运行中/完成/错误）全套 | 1天 |
| B5 | 复制/粘贴节点（Ctrl+C/V）功能实现 | 1天 |
| B6 | 撤销/重做（20步历史）完善 | 1天 |

**验收：** 从节点面板拖拽一个 YOLO 节点到画布，节点有完整色条+标题+配置控件，样式接近 ComfyUI。

---

### Phase C: 属性面板完善

**目标：** 右侧属性面板提供比节点内嵌更完整的配置体验。

| 步骤 | 内容 | 工作量 |
|------|------|--------|
| C1 | 属性面板重构：配置分组（输入/输出/执行/操作） | 1天 |
| C2 | 动态表单生成：根据 node.config_schema 渲染表单 | 1天 |
| C3 | 变量绑定 UI：📎 按钮弹出变量列表，点击插入 {{name}} | 0.5天 |
| C4 | 断连/重连操作：输入源查看 + 断连按钮 | 0.5天 |
| C5 | 执行状态展示：最近一次执行结果/耗时/输出预览 | 1天 |
| C6 | 右键菜单完善：复制/删除/查看源/查看日志 | 0.5天 |

---

### Phase D: 交互体验优化

| 步骤 | 内容 | 工作量 |
|------|------|--------|
| D1 | 画布右键菜单：粘贴/全选/适应画布/添加节点 | 1天 |
| D2 | 快捷键补全：Ctrl+D 复制偏移粘贴 | 0.5天 |
| D3 | MiniMap 优化：显示类别色点 | 0.5天 |
| D4 | Toast 通知：保存成功/执行完成/错误提示 | 0.5天 |
| D5 | 节点搜索优化：支持拼音/首字母搜索 | 0.5天 |
| D6 | 节点创建位置：拖拽时跟随鼠标而非固定画布中央 | 0.5天 |

---

### Phase E: 变量系统完善

| 步骤 | 内容 | 工作量 |
|------|------|--------|
| E1 | 变量 CRUD 面板：增删改变量（名/类型/默认值） | 1天 |
| E2 | 变量引用追踪：哪些节点用了某变量 | 0.5天 |
| E3 | 变量作用域：节点级 / 规则级 | 1天 |
| E4 | 表达式求值：{{var + 10}}、{{var > 5 ? 'a' : 'b'}} | 1天 |

---

## 七、技术决策

### 7.1 画布节点渲染方案

**决策：自定义 VueFlow 节点组件**，而非依赖 VueFlow 默认节点。

**理由：**
- ComfyUI 级别的节点需要内嵌配置控件、顶部色条、底部摘要
- VueFlow 默认节点只支持简单 label + handles
- 自定义节点虽然维护成本略高，但能满足复杂交互需求

**实现方式：**
```vue
<!-- RuleNode.vue -->
<template>
  <div class="rule-node" :class="[category, { selected, running, error }]">
    <div class="node-titlebar">
      <div class="color-strip"></div>
      <NodeIcon :icon="icon" />
      <span class="node-title">{{ label }}</span>
      <span class="node-type-badge">{{ type }}</span>
    </div>
    <div class="node-body">
      <!-- 输出端口（左侧） -->
      <div class="ports-outputs">
        <div v-for="port in outputs" :key="port.name" class="port-item output">
          <Handle id="output" type="source" :position="Position.Left" />
          <span class="port-label">{{ port.label }}</span>
        </div>
      </div>
      <!-- 配置控件（中间） -->
      <div class="node-widgets">
        <template v-for="(schema, key) in configSchema" :key="key">
          <WidgetSlider v-if="schema.widget === 'slider'" :schema="schema" />
          <WidgetSelect v-else-if="schema.widget === 'dropdown'" />
          <!-- ... -->
        </template>
      </div>
      <!-- 输入端口（右侧） -->
      <div class="ports-inputs">
        <div v-for="port in inputs" :key="port.name" class="port-item input">
          <Handle id="input" type="target" :position="Position.Right" />
          <span class="port-label">{{ port.label }}</span>
        </div>
      </div>
    </div>
    <div class="node-footer">{{ footerSummary }}</div>
  </div>
</template>
```

### 7.2 节点配置存储方案

**决策：配置存储在节点 data 中，前端编辑实时更新，后端执行前同步。**

```typescript
// VueFlow 节点 data 结构
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
      // ...其他配置
    },
    // inputs/outputs 由前端从 definitions 查，不存冗余
  }
}
```

### 7.3 前后端配置同步

- 前端通过 `GET /api/rule-engine/nodes/definitions` 获取 config_schema
- 节点 data.config 在前端修改后，通过 `PUT /api/rule-engine/graphs/{id}` 保存完整图
- 后端执行时从图数据读取 config，不依赖 definitions

---

## 八、优先级排序

```
P0 (必须做，阻塞其他功能):
  1. Phase A: 18个节点 config_schema 补全（后端）
  2. Phase B: 自定义 RuleNode 组件 + 节点样式重构（前端）

P1 (核心体验，上线前必须完成):
  3. Phase B: 节点内嵌配置控件渲染
  4. Phase C: 属性面板重构
  5. Phase D: 复制粘贴 + 撤销重做完善

P2 (体验优化):
  6. Phase D: 右键菜单 + 快捷键补全
  7. Phase E: 变量系统 UI
  8. Phase B: MiniMap + Toast 通知

P3 (锦上添花):
  9. Phase E: 表达式求值
  10. 节点分组/注释
  11. 规则模板市场
```

---

## 九、风险与依赖

| 风险 | 影响 | 应对 |
|------|------|------|
| 自定义节点组件改动量大 | 时间 | 优先完成 A(YOLO/Pad)两个核心节点验证方案 |
| 动态模型列表需要后端支持 | 依赖A4 | 先用静态 enum，后续迭代动态加载 |
| config_schema 变更需要迁移 | 数据 | v2 版本号，图数据加 version 字段 |
| 画布性能（100+节点） | 扩展性 | Phase D 虚拟化渲染 |

---

## 十、结论

本次重构核心解决三个问题：

1. **节点可配置** — 补全所有 18 个节点的 config_schema，做到"每个节点都能调参"
2. **节点样式好看** — 参考 ComfyUI，做顶部色条+标题栏+内嵌控件+底部摘要的节点卡片
3. **属性面板实用** — 完整配置表单+变量绑定+执行状态+断连操作

建议先选 **YOLO 检测节点** 作为样例，从 Phase A 到 Phase B 走一遍完整流程，验证方案后再批量复制到其他 17 个节点。
