# 规则引擎节点编辑配置修复计划
从原型到可用 — 逐节点闭环验证 · 2026-05

---

## 现状：三层断裂的执行链路
当前规则引擎 30 个节点的后端定义、单元测试均已通过（72/72 passed），但从前端画布配置 → 保存 → 加载 → 执行的端到端链路完全断裂。经全链路追踪，发现以下三个核心断裂点：

### 断裂点 1：节点格式不匹配（list vs dict）
         
| 环节 | 格式 | 代码位置 |
| --- | --- | --- |
| 前端保存 nodes_json | `[{id, type:"rule-node", data:{type, config, ...}}]` | ruleEngine.ts saveGraph() |
| parse_graph_data() 返回 | `{"nodes": [{id, ...}]}` | graph_manager.py:227 |
| _execute_node() 读取 | `context.config["nodes"].get(node_id)` ← **列表没有 .get()** | executor.py:555 |

### 断裂点 2：节点类型从错误字段读取

### 断裂点 3：配置路径不匹配
         
| 环节 | 读取路径 | 实际存在路径 |
| --- | --- | --- |
| 前端存储 | node.data.config = {interval: 5} | ✅ data.config |
| Executor 读取 | node_data.get("params", {}) | ❌ 应为 data.config |
| 各节点执行器 | self.config.get("params", {}).get("interval") | 需包装为 `{"params": {interval: 5}}` |

****``````

---

## Phase 0：修复执行器基础设施（P0）
修复核心执行链路，确保从前端配置到节点执行器的完整数据流畅通。这是所有后续工作的前提。

### 0.1 统一 nodes 格式：list → dict
在 `execute()` 方法中增加 nodes 格式统一逻辑：

### 0.2 修正 node_type 读取路径
VueFlow 节点 `node.type === "rule-node"`，实际执行器类型在 `node.data.type`：

### 0.3 修正 config 读取路径
前端存储 `data.config`，各节点执行器需要 `self.config = {"params": {...}}`：

### 0.4 执行器集成测试
新增端到端执行器测试（使用前端实际格式）：

 
- 测试 nodes 为 `list` 格式时执行器正常 
- 测试 `data.config` 扁平配置正确传递到节点 
- 测试 `data.type` 正确识别节点类型 
- 测试 `list` + `dict` 两种 nodes 格式均正常 
- 验证简单图：ManualTrigger → LogAction 完整执行 
****``****

---

## Phase 1：逐节点配置修复与验证（P0-P1）
按功能类别分组，逐节点检查 config_schema、widget 类型、参数默认值的正确性，并在前端验证编辑效果。

****

### 1.1 触发器组（5 节点）
           
| 节点 | 问题 | 修复 | 优先级 |
| --- | --- | --- | --- |
| 手动触发 | 无配置项，正常 | 无需修复，验证即可 | P1 |
| 定时器触发 | `enabled`: type=boolean + widget=dropdown + enum=["true","false"]布尔字段用字符串枚举，前端选"true"传字符串，执行器读为字符串而非布尔 | 改为 type=string + enum=["true","false"] 保持一致性；或改 widget=toggle + type=boolean | P1 |
| Cron 触发 | 正常 | 验证即可 | P1 |
| Webhook 触发 | 正常 | 验证即可 | P1 |
| API 触发 | 正常 | 验证即可 | P1 |

### 1.2 输入组（3 节点）
         
| 节点 | 问题 | 修复 | 优先级 |
| --- | --- | --- | --- |
| 图片输入 | source 默认空字符串，用户不清楚该填什么 | 优化 placeholder 描述，给出示例路径 | P2 |
| 视频输入 | source 默认 "video0" 不直观，fps 默认 30 | source 默认 "" + placeholder 提示 "/dev/video0 或文件路径" | P2 |
| 屏幕截图 | region 配置项未暴露在 schema 中 | 当前 widget=dropdown 只选了 source，region 暂不暴露（P2） | P2 |

### 1.3 检测组（3 节点）
         
| 节点 | 问题 | 修复 | 优先级 |
| --- | --- | --- | --- |
| YOLO 检测 | model_id 设为 required=true，但 widget=model-select 可能加载不到模型列表 | 增加 model_path 作为备用配置项model_id 未选时给出明确提示 | P1 |
| YOLO 触发器 | **class_names 用了 multiselect，前端未实现**min_confidence slider 正常 | 需 Phase 2 补全 multiselect widget 后才可用 | P1 |
| 目标检测 | model_path 未暴露为配置项，但 execute() 需要 | config_schema 添加 model_path 字段 | P1 |

### 1.4 处理组（4 节点）
          
| 节点 | 问题 | 修复 | 优先级 |
| --- | --- | --- | --- |
| 类别编码 | class_mapping 是 text 类型，格式说明不清晰测试中用了 {"person":0,"car":1} 对象格式，但 schema 用字符串逗号分隔格式 | 统一为 JSON 对象文本输入，description 给出示例 | P2 |
| 结果过滤 | filter_by=class 时需要 class_names，但 class_names 未暴露 | 在 config_schema 添加 class_names（multi-select，需等 Phase 2） | P1 |
| 目标跟踪 | 正常（3 个 slider 均已配置） | 验证即可 | P1 |
| 图像预处理 | 正常（dropdown + number × 2） | 验证即可 | P1 |

### 1.5 动作组（5 节点）
           
| 节点 | 问题 | 修复 | 优先级 |
| --- | --- | --- | --- |
| 键盘动作 | **keys 用了 multiselect，前端未实现** | 需 Phase 2 补全 multiselect | P1 |
| 鼠标动作 | 正常 | 验证即可 | P1 |
| 等待 | 正常 | 验证即可 | P1 |
| HTTP 请求 | headers 字段用 JSON 文本，用户可能填写非法格式 | description 增加 JSON 格式示例 | P2 |
| 日志 | 正常 | 验证即可 | P1 |

### 1.6 逻辑组（5 节点）
           
| 节点 | 问题 | 修复 | 优先级 |
| --- | --- | --- | --- |
| 分支 | 正常（无配置项） | 验证即可 | P1 |
| 并行分支 | **execute() 中用到了 max_concurrent，但 get_config_schema() 未覆盖** | 补全 config_schema 暴露 max_concurrent | P1 |
| 延迟 | 正常 | 验证即可 | P1 |
| 设置变量 | value_type=dynamic 时从其他变量取值，逻辑不直观 | description 增加使用示例说明 | P2 |
| 计数器 | **reset_on_trigger 用了 toggle，前端未实现** | 需 Phase 2 补全 toggle widget | P1 |

### 1.7 条件组（3 节点，归入 LOGIC 类别）
         
| 节点 | 问题 | 修复 | 优先级 |
| --- | --- | --- | --- |
| 目标存在 | **class_names 用了 multiselect，前端未实现**enum 硬编码了 ["person","car","dog","cat","bicycle","truck","bus"] | 需 Phase 2 补全 multiselect；enum 列表应从实际模型类别获取 | P1 |
| 置信度阈值 | 正常 | 验证即可 | P1 |
| 变量条件 | expected_value 是 string 类型，与变量实际类型可能不匹配 | description 提示类型自动转换行为 | P2 |

### 1.8 输出组（3 节点）
         
| 节点 | 问题 | 修复 | 优先级 |
| --- | --- | --- | --- |
| 保存结果 | output_path 默认 "/tmp/rule_result.json" | 提示用户修改路径 | P2 |
| 发送通知 | recipients 是 text 但描述说 list，前端用户可能混淆 | description 明确格式：webhook 填URL，email 填邮箱地址 | P2 |
| 显示结果 | 正常 | 验证即可 | P1 |

---

## Phase 2：前端 Widget 补全（P1）
当前前端 RuleNode.vue 支持 10 种 widget： `slider`、`number`、`dropdown`、`model-select`、 `file-picker`、`textarea`、`code`、`checkbox`、 `multiselect` 新、 `toggle` 新， 以及默认的 `text`。

****````````当前前端 RuleNode.vue 支持 8 种 widget： `slider`、`number`、`dropdown`、`model-select`、 `file-picker`、`textarea`、`code`、`checkbox`， 以及默认的 `text`。

需要新增的 widget：

### 2.1 multiselect 多选组件
**使用场景：**

 
- 键盘动作.keys — 从预定义按键列表中选择多个键 
- YOLO触发器.class_names — 选择要检测的类别 
- 目标存在.class_names — 选择要检查的类别 
**实现方案：**

获取到的值存储为数组 `[]`，后端各节点 execute() 中已正确处理数组格式。

### 2.2 toggle 开关组件
**使用场景：**

 
- 计数器.reset_on_trigger — 开关控制是否在触发时重置 
- （未来）定时器.enabled — 开关启用状态 
**实现方案：**

****
 
- multiselect：键盘动作节点可选择多个按键并正确保存为数组 
- toggle：计数器 reset_on_trigger 开关开/关后保存正确的 boolean 值 
- 所有现有 widget 仍正常工作 

---

## Phase 3：前端画布编辑面板完善（P1-P2）

### 3.1 右侧属性面板配置编辑
当前右侧属性面板（properties-panel）中 selectedNode 的 config 编辑区使用了独立的表单渲染逻辑。 需确保：

 
- 与 RuleNode.vue 内联编辑区 widget 渲染一致 
- 右侧面板修改后，节点内联编辑区同步更新 
- 修改自动触发 saveHistory（Undo 栈） 

### 3.2 配置修改即时同步
当前 `updateConfig` 函数（RuleCanvas.vue:1686）直接修改 `nodeConfig.value` 并手动同步到 `node.data.config`。需确认：

 
- RuleNode 内部 emit('update:config') 调用后，父组件能正确响应 
- 配置修改后节点底部的 configSummary 即时更新 
- 多次修改后的 Undo/Redo 正确 

---

## 逐节点闭环验证方案
每个节点的验证流程：

### 验证步骤

 
1. **后端 schema 检查**：确认 `get_config_schema()` 返回正确的 widget/type/enum/default 
1. **前端渲染检查**：确认画布上节点内联编辑区正确渲染对应 widget 
1. **配置修改保存**：修改配置值，确认 `node.data.config` 正确更新 
1. **图保存/加载**：保存规则图后重新加载，确认配置值持久化 
1. **执行验证**：触发规则图执行，确认节点 execute() 读到正确的配置值 
1. **边界测试**：空值、非法值、极值等输入处理 

### 节点验证对照表
                                     
| 节点 | Schema ✅ | Widget ✅ | 保存 ✅ | 执行 ✅ |
| --- | --- | --- | --- | --- |
| 手动触发 | — | — | — | ✅ |
| 定时器触发 | ✅ 已修 | ✅ | 待验 | ✅ |
| Cron 触发 | ✅ | ✅ | 待验 | 待验 |
| Webhook 触发 | ✅ | ✅ | 待验 | 待验 |
| API 触发 | ✅ | ✅ | 待验 | 待验 |
| 图片输入 | ✅ | ✅ | 待验 | 待验 |
| 视频输入 | ✅ | ✅ | 待验 | 待验 |
| 屏幕截图 | ✅ | ✅ | 待验 | 待验 |
| YOLO 检测 | ✅ | ✅ | 待验 | ✅ |
| YOLO 触发器 | ✅ | ✅ multiselect 已补 | 待验 | ✅ |
| 目标检测 | ✅ model_path 已补 | ✅ | 待验 | 待验 |
| 类别编码 | ✅ 格式兼容 | ✅ | 待验 | ✅ |
| 结果过滤 | ✅ class_names 已补 | ✅ | 待验 | ✅ |
| 目标跟踪 | ✅ | ✅ | 待验 | ✅ |
| 图像预处理 | ✅ | ✅ | 待验 | ✅ |
| 键盘动作 | ✅ | ✅ multiselect 已补 | 待验 | 待验 |
| 鼠标动作 | ✅ | ✅ | 待验 | ✅ |
| 等待 | ✅ | ✅ | 待验 | ✅ |
| HTTP 请求 | ✅ | ✅ | 待验 | 待验 |
| 日志 | ✅ | ✅ | 待验 | ✅ |
| 分支 | — | — | — | ✅ |
| 并行分支 | ✅ max_concurrent 已补 | — | — | 待验 |
| 延迟 | ✅ | ✅ | 待验 | ✅ |
| 设置变量 | ✅ | ✅ | 待验 | ✅ |
| 计数器 | ✅ | ✅ toggle 已补 | 待验 | 待验 |
| 目标存在 | ✅ | ✅ multiselect 已补 | 待验 | ✅ |
| 置信度阈值 | ✅ | ✅ | 待验 | ✅ |
| 变量条件 | ✅ | ✅ | 待验 | ✅ |
| 保存结果 | ✅ | ✅ | 待验 | 待验 |
| 发送通知 | ✅ | ✅ | 待验 | 待验 |
| 显示结果 | ✅ | ✅ | 待验 | ✅ |

---

## 执行计划与工作量评估
            
| 阶段 | 内容 | 涉及文件 | 预估工时 |
| --- | --- | --- | --- |
| **Phase 0** | 修复执行器基础设施 | executor.py | ✓ 已完成 |
| **Phase 1** | 逐节点配置修复（10 个节点需修改） | 各 nodes/*.py | ✓ 已完成 |
| **Phase 2** | 前端 widget 补全 | RuleNode.vue | ✓ 已完成 |
| **Phase 3** | 画布编辑面板完善 | RuleCanvas.vue | 待排期 |
| **验证** | 逐节点闭环验证 | 各相关文件 | 持续 |
| **已投入** | **~4h** |  |  |

---

## 附录：配置数据流图
************************````````````

---

## 附录 B：前端逐节点验证计划
以下为分 7 组进行的逐节点前端验证方案。每个节点按标准流程操作：

### 标准验证步骤

 
1. 从左侧节点面板拖到画布 
1. 观察节点内联配置区 — 各 widget 是否按预期渲染？ 
1. 修改每个配置项的值（slider 拖动、dropdown 选值、multiselect 多选、toggle 开关...） 
1. 观察底部 configSummary 是否实时更新 
1. 点击保存 → F5 刷新页面 → 检查配置值是否持久化 
1. 连接上下游节点 → 验证端口颜色匹配、连线可建立 
1. 点击执行 → 观察执行状态指示、WebSocket 进度推送 
                                            
| # | 节点 | 配置项 · widget | 验证重点 |
| --- | --- | --- | --- |
| **第 1 组：触发器（5 节点 — 规则入口）** |  |  |  |
| 1.1 | 手动触发 | （无配置项） | 拖放、选中、删除、端口连接 |
| 1.2 | API 触发 | `api_name` · text | text 输入框可编辑、回车保存 |
| 1.3 | Webhook 触发 | `path` · text, `method` · dropdown | dropdown 选值（GET/POST/PUT/DELETE） |
| 1.4 | Cron 触发 | `cron` · text, `timezone` · dropdown | timezone 下拉选时区，cron 输入表达式 |
| 1.5 | 定时器触发 | `interval` · slider, `enabled` · dropdown | **修复验证：**enabled 显示 true/false 下拉而非文本 |
| **第 2 组：输入采集（3 节点 — 数据源）** |  |  |  |
| 2.1 | 图片输入 | `source` · **file-picker** | 文件选择器按钮弹出，选择文件后路径回填 |
| 2.2 | 视频输入 | `source` · text, `fps` · number | number 控件的步进增减、手动输入 |
| 2.3 | 屏幕截图 | `source` · dropdown | 选 screen / window |
| **第 3 组：检测（3 节点 — 视觉识别）** |  |  |  |
| 3.1 | YOLO 检测 | `model_id` · **model-select**, `confidence` · slider, `iou_threshold` · slider, `max_detections` · number, `device` · dropdown | model-select 下拉加载模型列表；两个 slider 拖动；number 输入最大值 |
| 3.2 | YOLO 触发器 | `model_id` · model-select, `class_names` · **multiselect 🆕**, `min_confidence` · slider, `max_objects` · number, `device` · dropdown | **新 widget 验证：**multiselect 多选类别，标签折叠显示 |
| 3.3 | 目标检测 | `model_type` · dropdown, `model_path` · text 🆕, `confidence` · slider | **修复验证：**model_path 文本输入框已出现 |
| **第 4 组：处理（4 节点 — 数据变换）** |  |  |  |
| 4.1 | 类别编码 | `class_mapping` · text | 输入格式 `person:0,car:1` 验证后端解析 |
| 4.2 | 结果过滤 | `filter_by` · dropdown, `class_names` · text 🆕, `min_confidence` · slider, `min_count` · number, `max_count` · number | **修复验证：**class_names 文本输入出现；dropdown 切换过滤方式 |
| 4.3 | 目标跟踪 | `max_age` · slider, `min_hits` · slider, `iou_threshold` · slider | 三个 slider 分别拖到不同值 |
| 4.4 | 图像预处理 | `operation` · dropdown, `width` · number, `height` · number | 选 resize/crop/normalize；宽高输入联动 |
| **第 5 组：动作（5 节点 — 外部操作）** |  |  |  |
| 5.1 | 键盘动作 | `keys` · **multiselect 🆕**, `hold_duration` · number, `interval` · number | **新 widget 验证：**从 30+ 按键中多选，折叠标签显示；输入小数 |
| 5.2 | 鼠标动作 | `action` · dropdown, `x` · number, `y` · number, `button` · dropdown | 选 click/move/scroll；输入坐标值 |
| 5.3 | 等待 | `duration` · slider | slider 拖动调节等待秒数 |
| 5.4 | HTTP 请求 | `url` · text, `method` · dropdown, `headers` · text, `body` · textarea, `timeout` · number | textarea 多行输入 JSON；五种 widget 同节点 |
| 5.5 | 日志 | `message` · textarea, `level` · dropdown | 多行消息输入；选 debug/info/warning/error |
| **第 6 组：逻辑 + 条件（8 节点 — 流程控制）** |  |  |  |
| 6.1 | 分支 | （无配置项） | 连接 condition 输入（BOOLEAN）和 true/false 输出 |
| 6.2 | 并行分支 | `max_concurrent` · number 🆕 | **修复验证：**max_concurrent 数字输入框已出现 |
| 6.3 | 延迟 | `delay` · slider | slider 0.1–60s 范围 |
| 6.4 | 设置变量 | `variable_name` · text, `value` · text, `value_type` · dropdown | input 变量名；下拉选 static/dynamic |
| 6.5 | 计数器 | `variable_name` · text, `increment` · number, `reset_on_trigger` · **toggle 🆕**, `max_value` · number | **新 widget 验证：**toggle 开关可点击切换 开/关 |
| 6.6 | 目标存在 | `class_names` · **multiselect 🆕**, `min_count` · number, `comparison` · dropdown | **新 widget 验证：**多选类别；选比较方式 gte/lte/eq/gt/lt |
| 6.7 | 置信度阈值 | `min_confidence` · slider | slider 0–1 范围验证 |
| 6.8 | 变量条件 | `variable_name` · text, `expected_value` · text, `comparison` · dropdown | 变量名 + 期望值 + 比较方式完整配置 |
| **第 7 组：输出（3 节点 — 结果输出）** |  |  |  |
| 7.1 | 保存结果 | `output_path` · text, `format` · dropdown | 路径输入；选 json/csv |
| 7.2 | 发送通知 | `notification_type` · dropdown, `recipients` · text, `message` · text | 选 console/webhook/email/sms |
| 7.3 | 显示结果 | `title` · text | 标题文本输入 |

CogniFlow · 规则引擎节点编辑配置修复计划 · 2026-05 本文档对应实现分支：`feature/rule-engine-development`
