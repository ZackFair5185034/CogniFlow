# CogniFlow 规则引擎 - 重构设计方案 v2.2

> **文档版本：** v2.2
> **创建时间：** 2026-05-06
> **最后更新：** 2026-05-06
> **状态：** 待老大评审后执行

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

**Phase A: 后端 config_schema 补全**
- 重写 18 个节点的 `get_definition()`，补全 config_schema
- 制定 widget 类型规范
- 验收：GET /nodes/definitions 返回完整 schema

**Phase B: 前端节点样式重构**
- 创建自定义 RuleNode.vue 组件
- 节点面板卡片化（带色条、图标、名称）
- 节点状态样式（默认/选中/运行中/完成/错误）

### P1 — 核心体验

**Phase C: 节点内嵌配置控件**
- 根据 config_schema 动态渲染 slider/dropdown/number/checkbox
- 底部配置摘要

**Phase D: 属性面板完善**
- 动态表单生成
- 变量绑定 UI（📎按钮插入 {{name}}）
- 断连/重连操作
- 执行状态展示

**Phase E: 交互完善**
- 复制粘贴（Ctrl+C/V）
- 撤销重做（20步）
- 右键菜单
- 快捷键

### P2 — 体验优化

**Phase F: 变量系统**
- 变量 CRUD 面板
- 表达式求值

**Phase G: 优化增强**
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

## 七、结论

本次重构解决三个核心问题：

1. **节点可配置** — 每个节点有完整 config_schema，能调参
2. **节点样式好看** — ComfyUI 风格：色条+标题+内嵌控件+底部摘要
3. **属性面板实用** — 动态表单+变量绑定+执行状态+断连操作

**建议先从 YOLO 检测节点走一遍完整流程（Phase A→B），验证方案后再批量复制到其他 17 个节点。**
