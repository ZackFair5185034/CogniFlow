# 规则引擎节点连接设计规范

> **设计原则：** 能相互连接的端口使用相同的颜色标识，用户通过颜色即可直观判断两个端口是否兼容。
>
> 参考 Blender 的节点编辑器设计哲学——Socket 颜色代表数据类型，同色可连。

---

## 1. 端口类型体系

### 1.1 完整端口类型

前端 `PortType` 枚举缺失部分类型，与后端实际使用的类型不一致，需要统一。

| 端口类型 | 语义 | 当前后端枚举 | 当前前端验证 | 当前前端 CSS |
|---------|------|-------------|-------------|-------------|
| `IMAGE` | 图片数据 | ✅ | ✅ | ✅ |
| `BBOX` | 检测框坐标 | ✅ | ✅ | ✅ |
| `MASK` | 分割掩码 | ✅ | ✅ | ✅ |
| `SCORES` | 置信度分数 | ✅ | ✅ | ✅ |
| `TRIGGER` | 触发信号 | ✅ | ✅ | ✅ |
| `CONTROL` | 控制流信号 | ✅ | ✅ | ✅ |
| `MODEL` | 模型引用 | ✅ | ✅ | ❌ |
| `ANY` | 任意类型 | ✅ | ✅ | ✅ |
| `INT` | 整数值 | ❌ | ❌ | ❌ |
| `FLOAT` | 浮点值 | ❌ | ❌ | ❌ |
| `BOOLEAN` | 布尔值 | ❌ | ❌ | ✅（CSS 有但无 PortType） |
| `STRING` | 字符串 | ❌ | ❌ | ❌ |
| `ARRAY` | 数组/列表 | ❌ | ❌ | ✅（CSS 有但无 PortType） |
| `OBJECT` | 对象/字典 | ❌ | ❌ | ❌ |

### 1.2 整改要求

**后端 `models.py`** 补充完整类型，前端 `RuleCanvas.vue` 的 `PORT_TYPES` 数组同步更新：

```python
class PortType(str, Enum):
    """端口数据类型枚举。"""
    IMAGE = "IMAGE"
    BBOX = "BBOX"
    MASK = "MASK"
    SCORES = "SCORES"
    TRIGGER = "TRIGGER"
    CONTROL = "CONTROL"
    MODEL = "MODEL"
    ANY = "ANY"
    INT = "INT"          # 新增
    FLOAT = "FLOAT"      # 新增
    BOOLEAN = "BOOLEAN"  # 新增
    STRING = "STRING"    # 新增
    ARRAY = "ARRAY"      # 新增
    OBJECT = "OBJECT"    # 新增
```

---

## 2. 端口颜色体系

### 2.1 颜色映射表

核心原则：**同色可连**。颜色完全由端口类型决定，与节点类别无关。

```css
/* 执行流 — 紫色系 */
.type-trigger  { border-color: #DC4FDC; }  /* 触发信号 ↦ 触发、控制 */
.type-control  { border-color: #DC4FDC; }  /* 控制流  ↦ 控制 */

/* 视觉数据 — 绿色系 */
.type-image    { border-color: #4CFF4C; }  /* 图片数据 ↦ 图片 */

/* 检测数据 — 蓝色/橙色系 */
.type-bbox     { border-color: #00f0FF; }  /* 检测框 ↦ 检测框 */
.type-mask     { border-color: #00f0FF; }  /* 掩码 ↦ 掩码 */
.type-scores   { border-color: #FF7F4C; }  /* 置信度 ↦ 置信度 */

/* 集合数据 — 黄色系 */
.type-array    { border-color: #FFFF4C; }  /* 列表/数组 ↦ 列表 */
.type-object   { border-color: #FFFF4C; }  /* 对象/字典 ↦ 对象 */

/* 基本类型 — 红/蓝色系 */
.type-boolean  { border-color: #FF4C4C; }  /* 布尔值 ↦ 布尔 */
.type-int      { border-color: #3B82F6; }  /* 整数 ↦ 整数 */
.type-float    { border-color: #14B8A6; }  /* 浮点数 ↦ 浮点 */
.type-string   { border-color: #8B5CF6; }  /* 字符串 ↦ 字符串 */

/* 泛型 — 灰色系 */
.type-model    { border-color: #888888; }  /* 模型引用 ↦ 模型 */
.type-any      { border-color: #E0E0E0; }  /* 任意类型 ↦ 任意类型 */
```

### 2.2 颜色分组说明

| 色组 | 包含类型 | 互连规则 | 说明 |
|------|---------|---------|------|
| 紫色 `#DC4FDC` | TRIGGER, CONTROL | TRIGGER→TRIGGER/CONTROL, CONTROL→CONTROL | 执行链信号，触发信号可以启动控制流节点 |
| 绿色 `#4CFF4C` | IMAGE | IMAGE↔IMAGE | 视觉数据流 |
| 青色 `#00f0FF` | BBOX, MASK | BBOX↔BBOX, MASK↔MASK | 检测空间数据 |
| 橙色 `#FF7F4C` | SCORES | SCORES↔SCORES | 检测置信度 |
| 黄色 `#FFFF4C` | ARRAY, OBJECT | ARRAY↔ARRAY, OBJECT↔OBJECT | 集合/结构化数据（独立互连，不能跨类型） |
| 红色 `#FF4C4C` | BOOLEAN | BOOLEAN↔BOOLEAN | 真/假值 |
| 蓝色 `#3B82F6` | INT | INT↔INT | 整数值 |
| 青色系 `#14B8A6` | FLOAT | FLOAT↔FLOAT | 浮点值 |
| 紫色系 `#8B5CF6` | STRING | STRING↔STRING | 文本 |
| 灰色 `#888` | MODEL | MODEL↔MODEL | 模型引用 |
| 亮灰色 `#E0E0E0` | ANY | ANY↔ANY + ANY↔任意 | 通配类型 |

> **注意：** TRIGGER 和 CONTROL 共用紫色，因为 TRIGGER 可以连接 CONTROL（触发信号驱动控制流）。
> 但 CONTROL→TRIGGER 不允许（控制流完成不会反过来触发）。

---

## 3. 兼容性矩阵

```typescript
const TYPE_COMPATIBILITY: Record<string, string[]> = {
  IMAGE:    ['IMAGE'],
  BBOX:     ['BBOX'],
  MASK:     ['MASK'],
  SCORES:   ['SCORES'],
  TRIGGER:  ['TRIGGER', 'CONTROL'],
  CONTROL:  ['CONTROL'],
  BOOLEAN:  ['BOOLEAN'],
  INT:      ['INT'],
  FLOAT:    ['FLOAT'],
  STRING:   ['STRING'],
  ARRAY:    ['ARRAY'],
  OBJECT:   ['OBJECT'],
  MODEL:    ['MODEL'],
  ANY:      ['ANY', 'IMAGE', 'BBOX', 'MASK', 'SCORES', 'TRIGGER', 'CONTROL',
             'BOOLEAN', 'INT', 'FLOAT', 'STRING', 'ARRAY', 'OBJECT', 'MODEL'],
}
```

---

## 4. 全节点端口详表

### 4.1 `input` — 输入类（节点类别色：#4CFF4C）

#### ImageCaptureNode (`image_capture`)
| 方向 | 端口名 | 类型 | 必需 | 标签 | 说明 |
|------|-------|------|------|------|------|
| ➡输出 | image | `IMAGE` | — | 图片 | 采集到的图片数据 |
| ➡输出 | width | `INT` | — | 宽度 | 图片宽度（像素） |
| ➡输出 | height | `INT` | — | 高度 | 图片高度（像素） |

#### VideoCaptureNode (`video_capture`)
| 方向 | 端口名 | 类型 | 必需 | 标签 | 说明 |
|------|-------|------|------|------|------|
| ➡输出 | image | `IMAGE` | — | 帧图片 | 采集到的视频帧 |
| ➡输出 | frame_id | `INT` | — | 帧序号 | 帧序号 |
| ➡输出 | timestamp | `FLOAT` | — | 时间戳 | 时间戳（秒） |

#### ScreenCaptureNode (`screen_capture`)
| 方向 | 端口名 | 类型 | 必需 | 标签 | 说明 |
|------|-------|------|------|------|------|
| ➡输出 | image | `IMAGE` | — | 截图 | 屏幕截图 |
| ➡输出 | region | `OBJECT` | — | 区域 | 采集区域信息 |

#### ManualTriggerNode (`manual_trigger`)
| 方向 | 端口名 | 类型 | 必需 | 标签 | 说明 |
|------|-------|------|------|------|------|
| ➡输出 | triggered | `BOOLEAN` | — | 触发 | 是否触发 |

#### TimerTriggerNode (`timer_trigger`)
| 方向 | 端口名 | 类型 | 必需 | 标签 | 说明 |
|------|-------|------|------|------|------|
| ➡输出 | triggered | `BOOLEAN` | — | 触发 | 是否触发 |
| ➡输出 | timestamp | `FLOAT` | — | 时间戳 | 触发时间戳 |

#### CronTriggerNode (`cron_trigger`)
| 方向 | 端口名 | 类型 | 必需 | 标签 | 说明 |
|------|-------|------|------|------|------|
| ➡输出 | triggered | `BOOLEAN` | — | 触发 | 是否触发 |
| ➡输出 | timestamp | `FLOAT` | — | 时间戳 | 触发时间戳 |

#### WebhookTriggerNode (`webhook_trigger`)
| 方向 | 端口名 | 类型 | 必需 | 标签 | 说明 |
|------|-------|------|------|------|------|
| ➡输出 | triggered | `BOOLEAN` | — | 触发 | 是否触发 |
| ➡输出 | request_data | `ANY` | — | 请求数据 | HTTP 请求数据 |

#### ApiTriggerNode (`api_trigger`)
| 方向 | 端口名 | 类型 | 必需 | 标签 | 说明 |
|------|-------|------|------|------|------|
| ➡输出 | triggered | `BOOLEAN` | — | 触发 | 是否触发 |
| ➡输出 | api_response | `ANY` | — | API响应 | API 响应数据 |

---

### 4.2 `detection` — 检测类（节点类别色：#00f0FF）

#### YOLOModelNode (`yolo_model`)
| 方向 | 端口名 | 类型 | 必需 | 标签 | 说明 |
|------|-------|------|------|------|------|
| ←输入 | image | `IMAGE` | ✅ | 图片输入 | 待检测的图片 |
| ➡输出 | bboxes | `BBOX` | — | 检测框 | 检测到的目标框列表 |
| ➡输出 | scores | `SCORES` | — | 置信度 | 各检测框对应的置信度 |
| ➡输出 | class_ids | `ARRAY` | — | 类别ID | 各检测框对应的类别 ID |
| ➡输出 | class_names | `ARRAY` | — | 类别名称 | 各检测框对应的类别名称 |
| ➡输出 | count | `INT` | — | 检测数量 | 检测到的目标数量 |

#### YOLOTriggerNode (`yolo_trigger`)
| 方向 | 端口名 | 类型 | 必需 | 标签 | 说明 |
|------|-------|------|------|------|------|
| ←输入 | image | `IMAGE` | ❌ | 图片输入 | 待检测的图片（可选） |
| ➡输出 | triggered | `BOOLEAN` | — | 触发 | 是否满足触发条件 |
| ➡输出 | detections | `ARRAY` | — | 检测结果 | 检测到的目标列表 |

#### ObjectDetectorNode (`object_detector`)
| 方向 | 端口名 | 类型 | 必需 | 标签 | 说明 |
|------|-------|------|------|------|------|
| ←输入 | image | `IMAGE` | ✅ | 图片输入 | 待检测的图片 |
| ➡输出 | detections | `ARRAY` | — | 检测结果 | 检测到的目标列表 |
| ➡输出 | count | `INT` | — | 数量 | 检测数量 |

---

### 4.3 `processing` — 处理类（节点类别色：#FFFF4C）

#### CategoryEncodeNode (`category_encode`)
| 方向 | 端口名 | 类型 | 必需 | 标签 | 说明 |
|------|-------|------|------|------|------|
| ←输入 | class_names | `ARRAY` | ✅ | 类别名称 | 类别名称列表 |
| ➡输出 | class_ids | `ARRAY` | — | 类别ID | 类别 ID 列表 |
| ➡输出 | class_names | `ARRAY` | — | 类别名称 | 类别名称列表（带映射） |

#### FilterNode (`filter`)
| 方向 | 端口名 | 类型 | 必需 | 标签 | 说明 |
|------|-------|------|------|------|------|
| ←输入 | detections | `ARRAY` | ✅ | 检测结果 | 待过滤的检测结果 |
| ➡输出 | filtered | `ARRAY` | — | 过滤结果 | 过滤后的结果 |
| ➡输出 | count | `INT` | — | 数量 | 过滤后数量 |

#### TrackerNode (`tracker`)
| 方向 | 端口名 | 类型 | 必需 | 标签 | 说明 |
|------|-------|------|------|------|------|
| ←输入 | detections | `ARRAY` | ✅ | 检测结果 | 当前帧检测结果 |
| ➡输出 | tracked | `ARRAY` | — | 跟踪结果 | 带跟踪 ID 的结果 |
| ➡输出 | track_ids | `ARRAY` | — | 跟踪ID | 跟踪 ID 列表 |

#### ImagePreprocessorNode (`image_preprocessor`)
| 方向 | 端口名 | 类型 | 必需 | 标签 | 说明 |
|------|-------|------|------|------|------|
| ←输入 | image | `IMAGE` | ✅ | 图片 | 待处理的图片 |
| ➡输出 | image | `IMAGE` | — | 处理后图片 | 处理后的图片 |

---

### 4.4 `action` — 动作类（节点类别色：#FF7F4C）

#### KeyboardActionNode (`keyboard_action`)
| 方向 | 端口名 | 类型 | 必需 | 标签 | 说明 |
|------|-------|------|------|------|------|
| ←输入 | trigger | `TRIGGER` | ✅ | 触发 | 触发信号 |
| ➡输出 | success | `BOOLEAN` | — | 成功 | 是否执行成功 |
| ➡输出 | executed_keys | `ARRAY` | — | 按键列表 | 已执行的按键列表 |

#### MouseActionNode (`mouse_action`)
| 方向 | 端口名 | 类型 | 必需 | 标签 | 说明 |
|------|-------|------|------|------|------|
| ←输入 | trigger | `TRIGGER` | ✅ | 触发 | 触发信号 |
| ➡输出 | success | `BOOLEAN` | — | 成功 | 是否执行成功 |

#### WaitActionNode (`wait_action`)
| 方向 | 端口名 | 类型 | 必需 | 标签 | 说明 |
|------|-------|------|------|------|------|
| ←输入 | trigger | `TRIGGER` | ✅ | 触发 | 触发信号 |
| ➡输出 | completed | `BOOLEAN` | — | 完成 | 等待完成 |

#### HttpRequestActionNode (`http_request_action`)
| 方向 | 端口名 | 类型 | 必需 | 标签 | 说明 |
|------|-------|------|------|------|------|
| ←输入 | trigger | `TRIGGER` | ✅ | 触发 | 触发信号 |
| ➡输出 | success | `BOOLEAN` | — | 成功 | 请求是否成功 |
| ➡输出 | status_code | `INT` | — | 状态码 | HTTP 状态码 |
| ➡输出 | response | `ANY` | — | 响应 | 响应内容 |

#### LogActionNode (`log_action`)
| 方向 | 端口名 | 类型 | 必需 | 标签 | 说明 |
|------|-------|------|------|------|------|
| ←输入 | trigger | `TRIGGER` | ✅ | 触发 | 触发信号 |
| ➡输出 | logged | `BOOLEAN` | — | 已记录 | 是否记录成功 |

---

### 4.5 `logic` — 逻辑类（节点类别色：#DC4FDC）

#### BranchNode (`branch`)
| 方向 | 端口名 | 类型 | 必需 | 标签 | 说明 |
|------|-------|------|------|------|------|
| ←输入 | condition | `BOOLEAN` | ✅ | 条件 | 分支条件 |
| ➡输出 | true | `CONTROL` | — | 条件成立 | 条件成立时的输出 |
| ➡输出 | false | `CONTROL` | — | 条件不成立 | 条件不成立时的输出 |

#### ParallelBranchNode (`parallel_branch`)
| 方向 | 端口名 | 类型 | 必需 | 标签 | 说明 |
|------|-------|------|------|------|------|
| ←输入 | trigger | `TRIGGER` | ✅ | 触发 | 触发信号 |
| ➡输出 | branch_1 | `CONTROL` | — | 分支1 | 分支1输出 |
| ➡输出 | branch_2 | `CONTROL` | — | 分支2 | 分支2输出 |
| ➡输出 | branch_3 | `CONTROL` | — | 分支3 | 分支3输出 |

#### DelayNode (`delay`)
| 方向 | 端口名 | 类型 | 必需 | 标签 | 说明 |
|------|-------|------|------|------|------|
| ←输入 | input | `CONTROL` | ✅ | 输入 | 输入信号 |
| ➡输出 | output | `CONTROL` | — | 输出 | 延迟后的输出 |

#### SetVariableNode (`set_variable`)
| 方向 | 端口名 | 类型 | 必需 | 标签 | 说明 |
|------|-------|------|------|------|------|
| ←输入 | trigger | `TRIGGER` | ❌ | 触发 | 触发信号 |
| ➡输出 | next | `CONTROL` | — | 完成 | 完成信号 |

#### CounterNode (`counter`)
| 方向 | 端口名 | 类型 | 必需 | 标签 | 说明 |
|------|-------|------|------|------|------|
| ←输入 | trigger | `TRIGGER` | ✅ | 触发 | 计数触发 |
| ➡输出 | count | `INT` | — | 计数 | 当前计数值 |
| ➡输出 | overflow | `BOOLEAN` | — | 溢出 | 是否达到上限 |

#### ObjectExistsConditionNode (`object_exists_condition`)
| 方向 | 端口名 | 类型 | 必需 | 标签 | 说明 |
|------|-------|------|------|------|------|
| ←输入 | detections | `ARRAY` | ✅ | 检测结果 | 检测结果列表 |
| ➡输出 | result | `BOOLEAN` | — | 结果 | 条件是否满足 |
| ➡输出 | matched_count | `INT` | — | 匹配数量 | 符合条件的数量 |

#### ConfidenceThresholdConditionNode (`confidence_threshold_condition`)
| 方向 | 端口名 | 类型 | 必需 | 标签 | 说明 |
|------|-------|------|------|------|------|
| ←输入 | detections | `ARRAY` | ✅ | 检测结果 | 检测结果列表 |
| ➡输出 | result | `BOOLEAN` | — | 结果 | 条件是否满足 |
| ➡输出 | max_confidence | `FLOAT` | — | 最大置信度 | 最高置信度值 |

#### VariableConditionNode (`variable_condition`)
| 方向 | 端口名 | 类型 | 必需 | 标签 | 说明 |
|------|-------|------|------|------|------|
| ➡输出 | result | `BOOLEAN` | — | 结果 | 条件是否满足 |
| ➡输出 | actual_value | `ANY` | — | 实际值 | 变量的实际值 |

---

### 4.6 `output` — 输出类（节点类别色：#FF4C4C）

#### SaveResultNode (`save_result`)
| 方向 | 端口名 | 类型 | 必需 | 标签 | 说明 |
|------|-------|------|------|------|------|
| ←输入 | data | `ANY` | ✅ | 数据 | 要保存的数据 |
| ➡输出 | success | `BOOLEAN` | — | 成功 | 是否保存成功 |
| ➡输出 | path | `STRING` | — | 文件路径 | 保存的文件路径 |

#### NotificationNode (`notification`)
| 方向 | 端口名 | 类型 | 必需 | 标签 | 说明 |
|------|-------|------|------|------|------|
| ←输入 | trigger | `TRIGGER` | ✅ | 触发 | 触发信号 |
| ➡输出 | sent | `BOOLEAN` | — | 已发送 | 是否发送成功 |

#### DisplayNode (`display`)
| 方向 | 端口名 | 类型 | 必需 | 标签 | 说明 |
|------|-------|------|------|------|------|
| ←输入 | data | `ANY` | ✅ | 数据 | 要显示的数据 |
| ➡输出 | displayed | `BOOLEAN` | — | 已显示 | 是否显示成功 |

---

## 5. 端口类型在节点上的分布

按端口类型统计出现频率，确认颜色方案覆盖实际使用场景：

| 端口类型 | 出现次数 | 作为输入 | 作为输出 | 常见位置 |
|---------|---------|---------|---------|---------|
| `BOOLEAN` | 17 | 1 | 16 | 触发节点输出、动作结果、条件结果 |
| `INT` | 9 | 0 | 9 | 宽度/高度、计数、状态码 |
| `ARRAY` | 13 | 6 | 7 | 检测结果列表、类别列表、过滤/跟踪结果 |
| `TRIGGER` | 7 | 7 | 0 | 动作节点输入、逻辑节点输入 |
| `IMAGE` | 6 | 3 | 3 | 输入源→检测模型、图像预处理 |
| `CONTROL` | 6 | 1 | 5 | 分支输出、延迟输入/输出 |
| `FLOAT` | 4 | 0 | 4 | 时间戳、最大置信度 |
| `ANY` | 4 | 2 | 2 | Webhook数据、HTTP响应、变量值、保存数据 |
| `STRING` | 1 | 0 | 1 | 文件路径 |
| `BBOX` | 1 | 0 | 1 | 检测框（仅在YOLO模型输出） |
| `SCORES` | 1 | 0 | 1 | 置信度（仅在YOLO模型输出） |
| `MASK` | 0 | 0 | 0 | 预留，当前未使用 |
| `MODEL` | 0 | 0 | 0 | 预留，当前未使用 |
| `OBJECT` | 1 | 0 | 1 | 采集区域信息（ScreenCapture） |

### 端口类型频率分析

```
BOOLEAN  ■■■■■■■■■■■■■■■■■ 17
ARRAY    ■■■■■■■■■■■■■    13
INT      ■■■■■■■■■         9
TRIGGER  ■■■■■■■           7
IMAGE    ■■■■■■            6
CONTROL  ■■■■■■            6
FLOAT    ■■■■              4
ANY      ■■■■              4
BBOX     ■                  1
SCORES   ■                  1
STRING   ■                  1
OBJECT   ■                  1
MASK     (未使用)
MODEL    (未使用)
```

---

## 6. 典型连接模式

### 模式 1：采集→检测→处理

```
[ScreenCapture]────────IMAGE────────▶[YOLOModel]
                                       │
                              ARRAY ───┤──▶ [Filter] ──ARRAY──▶ [Tracker]
                                       │
                                     BBOX → (下游BBOX处理)
                                   SCORES → (下游SCORES处理)
```

**关键颜色链：**
- `IMAGE`（绿色）：ScreenCapture → YOLOModel
- `ARRAY`（黄色）：YOLOModel → Filter → Tracker
- `BBOX`（青色）：YOLOModel → （后续）
- `SCORES`（橙色）：YOLOModel → （后续）

### 模式 2：触发→动作链

```
[ManualTrigger]
       │
   BOOLEAN（红色）
       │
    [Branch]
    ┌──┴──┐
 CONTROL  CONTROL（紫色）
    │       │
[Keyboard] [MouseAction]
   TRIGGER    TRIGGER（紫色）
    │          │
[Wait]      [HttpRequest]
   TRIGGER     TRIGGER
    │          │
[LogAction]  [Notification]
```

**关键颜色链：**
- `BOOLEAN`（红色）：ManualTrigger → Branch
- `CONTROL` / `TRIGGER`（紫色）：Branch → Keyboard → Wait → Log

### 模式 3：条件检测

```
[YOLOModel]────────ARRAY──▶[ObjectExistsCondition]──BOOLEAN──▶[Branch]
                ──ARRAY──▶[ConfidenceThreshold]    ──BOOLEAN──▶[Branch]
```

**关键颜色链：**
- `ARRAY`（黄色）：YOLOModel → 条件节点
- `BOOLEAN`（红色）：条件节点 → Branch（控制是否执行下游）

### 模式 4：图像预处理循环

```
[ScreenCapture]──IMAGE──▶[ImagePreprocessor]──IMAGE──▶[YOLOModel]
```

---

## 7. 设计规则总结

### 规则 1：颜色标识类型而非节点

端口颜色代表**数据类型**，与节点所属类别完全无关。节点标题栏颜色表示节点类别，端口颜色表示数据类型，二者独立。

### 规则 2：同色可连

两个端口如果颜色相同，表示它们是兼容类型，可以连接。例外是 `ANY`（亮灰色），它可以连接任何类型的端口，但 `ANY` 端口本身只接受 `ANY` 输入。

### 规则 3：TRIGGER/CONTROL 同色

`TRIGGER` 和 `CONTROL` 共用紫色，因为触发信号可以驱动控制流节点。但连接方向有限制：
- ✅ TRIGGER → CONTROL（触发信号启动控制流）
- ✅ TRIGGER → TRIGGER（触发信号链）
- ✅ CONTROL → CONTROL（控制流链接）
- ❌ CONTROL → TRIGGER（控制流完成不会触发）

### 规则 4：端口用圆点标识，类型用颜色标识

Handle 采用小圆点设计，宽度/高度 12px。颜色填充在边框上，已连接的端口边框变为绿色（`#00ff88`）。

### 规则 5：类继承与端口类型扩展

如需新增端口类型，必须在以下 4 处同步更新：
1. 后端 `models.py` 的 `PortType` 枚举
2. 后端 `TYPE_COMPATIBILITY` 兼容性矩阵
3. 前端 `RuleCanvas.vue` 的 `PORT_TYPES` 数组 + `isPortCompatible` 函数
4. 前端 `RuleNode.vue` 的 `.type-{name}` CSS 颜色

---

## 8. 当前问题与整改项

### 问题 1：PortType 枚举不完整

**现状：** 后端 `PortType` 只有 8 种（IMAGE, BBOX, MASK, SCORES, TRIGGER, CONTROL, MODEL, ANY），但节点定义实际使用了 INT, FLOAT, BOOLEAN, STRING, ARRAY, OBJECT。

**影响：** 前端验证 `isPortCompatible` 对这 6 种类型返回 `false`（默认走 `return false`），导致连接被错误拒绝。

**整改：** 在 `PortType` 枚举中补充全部类型，同步更新前端 `PORT_TYPES` 和 `isPortCompatible`。

### 问题 2：前端 CSS 缺少部分端口类型颜色

**现状：** `RuleNode.vue` 已有 `.type-image`、`.type-bbox` 等样式，但缺少 `.type-int`、`.type-float`、`.type-string`、`.type-object`、`.type-model`。

**影响：** 缺少 CSS 的端口类型不会显示正确颜色，用户无法通过颜色判断兼容性。

**整改：** 补充全部 14 种端口类型的 CSS 颜色定义。

### 问题 3：Handle 未应用端口类型 class

**现状：** `RuleNode.vue` 的 Handle 模板没有根据端口类型动态添加 CSS class。

```vue
<!-- 当前：缺少 type class -->
<Handle type="target" :position="Position.Left" :id="input.name" class="node-handle" />
```

**整改：** 添加动态类型 class：

```vue
<Handle
  type="target"
  :position="Position.Left"
  :id="input.name"
  :class="['node-handle', `type-${(input.type || 'any').toLowerCase()}`]"
/>
```

### 问题 4：已连接端口状态反馈不准确

**现状：** `.vue-flow-handle-connected` 将所有已连接端口标记为绿色，但此时端口原本的类型颜色丢失。

**整改：** 使用 `:class` 叠加类型颜色和连接状态，用内边框或高亮效果表示连接状态而非替换颜色。
