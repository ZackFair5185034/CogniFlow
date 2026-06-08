# CogniFlow 规则引擎文档索引

> 📅 最后更新：2026-06-07 | 🔄 源格式：HTML → Markdown 自动转换

CogniFlow 规则引擎是一个**可视化编排**的视觉感知处理引擎，允许用户通过节点编辑器定义"检测→处理→动作"的完整流程。参考对象是 **ComfyUI**（最成熟的 AI 节点编辑器）和 **Node-RED**（工业级流程编排工具）。

---

## 📚 文档导航

### 🏗️ 架构设计 (`docs/research-md/`)

| 文档 | 内容 |
|------|------|
| [**项目入口**](./规则引擎项目入口.md) | 整体概览、阶段规划、Phase 1-6 + A-H 完整索引 |
| [**API 设计**](./规则引擎API设计.md) | RESTful API 端点规范 |
| [**数据模型**](./规则引擎数据模型.md) | Pydantic 模型 + ORM 映射 |
| [**数据结构设计**](./节点图数据结构设计.md) | 节点图序列化格式、Command Pattern |
| [**开发规范**](./规则引擎开发规范.md) | 开发流程、命名约定、提交规范 |
| [**交互规范**](./规则引擎交互规范.md) | UI/UX 交互规范 |

### 🔧 技术调研 (`docs/research-md/`)

| 文档 | 内容 |
|------|------|
| [**技术调研**](./规则引擎技术调研.md) | ComfyUI/Node-RED 架构对比、方案选型 |
| [**画布编辑器调研-0506**](./画布编辑器调研-0506.md) | Canvas/VueFlow/Rete.js 调研 |
| [**画布编辑器调研-0507**](./画布编辑器调研-0507.md) | 补充调研（性能、大规模节点） |
| [**VueFlow Fork — 拖拽性能优化**](./vueflow-fork-drag-optimization.md) | fork 源码修改：skipTrigger 方案解决多节点拖拽卡顿 |
| [**VueFlow Fork — 框选性能优化**](./vueflow-fork-selection-optimization.md) | fork 源码修改：process-skip 方案解决框选过程 O(N) 包围盒检测 |

### 🎨 前端重构 (`docs/research-md/`)

| 文档 | 内容 |
|------|------|
| [**前端重构设计方案 v2.2**](./规则引擎前端重构设计方案.md) | 自定义 RuleNode 组件、配置面板、撤销重做 |

### 📖 使用指南 (`docs/guides-md/`)

| 文档 | 内容 |
|------|------|
| [**快速开始教程**](../../guides-md/快速开始教程.md) | 新手入门，5 分钟搭建第一个规则 |
| [**规则引擎编辑器使用指南**](../../guides-md/规则引擎编辑器使用指南.md) | 编辑器详细使用说明（最权威） |
| [**项目分析报告**](../../guides-md/项目分析报告.md) | 项目现状与迭代计划 |

### 📋 迭代计划 (`docs/plans-md/`)

| 文档 | 内容 |
|------|------|
| [**规则引擎迭代计划 v2**](../../plans-md/规则引擎迭代计划v2.md) | 整体迭代路线图 |
| [**规则引擎待办清单**](../../plans-md/规则引擎待办清单.md) | 当前待办事项清单 |
| [**节点编辑修复计划**](../../plans-md/rule-engine-node-editing-plan.md) | 节点编辑功能修复方案 |
| [**前端架构重构 - VueFlow Store**](../../plans-md/前端架构重构-vueflow-store-refactor.md) | Pinia Store 重构方案 |

### 🗄️ 归档文档 (`docs/archives-md/`)

#### Phase 1-6 实施文档（已完成的旧阶段）

| 文档 | 内容 |
|------|------|
| [**Phase 1 - 节点注册表**](../../archives-md/规则引擎Phase1-节点注册表.md) | 节点类型系统设计 |
| [**Phase 2 - 执行引擎**](../../archives-md/规则引擎Phase2-执行引擎.md) | Kahn 拓扑执行引擎 |
| [**Phase 3 - 画布前端**](../../archives-md/规则引擎Phase3-画布前端.md) | VueFlow 画布实现 |
| [**Phase 4 - 属性面板**](../../archives-md/规则引擎Phase4-属性面板.md) | 属性配置面板设计 |
| [**Phase 5 - WebSocket**](../../archives-md/规则引擎Phase5-WebSocket.md) | 实时通信协议 |
| [**Phase 6 - 触发机制**](../../archives-md/规则引擎Phase6-触发机制.md) | 触发器系统设计 |

#### 架构研究

| 文档 | 内容 |
|------|------|
| [**Node-RED 编辑器架构研究**](../../archives-md/Node-RED编辑器架构研究.md) | Node-RED 架构参考 |
| [**无限画布性能优化研究**](../../archives-md/无限画布性能优化研究.md) | 大规模节点性能 |
| [**规则引擎端口连接设计**](../../archives-md/规则引擎端口连接设计.md) | 端口类型系统 |
| [**规则引擎开发计划**](../../archives-md/规则引擎开发计划.md) | 早期开发计划 |

#### 功能设计

| 文档 | 内容 |
|------|------|
| [**WebUI 升级设计**](../../archives-md/WebUI升级设计.md) | WebUI 整体升级方案 |
| [**多格式硬件加速计划**](../../archives-md/多格式硬件加速计划.md) | ONNX/TensorRT/FP16 加速 |
| [**系统托盘功能设计**](../../archives-md/系统托盘功能设计.md) | 系统托盘集成 |
| [**视频检测功能优化方案**](../../archives-md/视频检测功能优化方案.md) | 视频流优化 |
| [**视频流推理设计**](../../archives-md/视频流推理设计.md) | 视频流架构 |

#### 节点参考 (`docs/dev-md/`)

| 文档 | 内容 |
|------|------|
| [**规则引擎节点参考**](../../dev-md/规则引擎节点参考.md) | 34 已注册节点完整参数手册 |

### 🌐 顶级入口

| 文档 | 内容 |
|------|------|
| [**文档中心**](../../文档中心.md) | CogniFlow 文档体系总览 |

---

## 🎯 核心功能目标

- **可视化编排** — 无限画布上通过拖拽、连接节点来构建规则流程
- **节点类型化** — 输入、检测、处理、动作、逻辑、输出六类节点，类型安全连接
- **智能执行** — Kahn 拓扑排序 + 层内并行，支持条件分支
- **实时反馈** — WebSocket 推送执行进度，支持中断
- **持久化** — 规则图保存/加载，支持版本管理

---

## 🏛️ 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                          前端 Vue3                              │
├────────────┬───────────────────────────────┬────────────────────┤
│  节点面板   │        Vue Flow 画布          │   属性配置面板     │
│  (Palette) │   (节点/边/缩放/平移/选择)     │   (节点参数编辑)   │
├────────────┴───────────────────────────────┴────────────────────┤
│                     Pinia Store (状态管理)                      │
│                   WebSocket Client (实时通信)                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ HTTP + WebSocket
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                          后端 FastAPI                            │
├────────────────┬──────────────────────────┬─────────────────────┤
│  GraphManager  │   RuleGraphExecutor       │  NodeRegistry      │
│  (CRUD+校验)   │   (Kahn排序+层并行)       │  (节点定义+执行器)  │
├────────────────┴──────────────────────────┴─────────────────────┤
│                     WebSocket Manager (进度推送)                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        数据存储层                                │
│   SQLite (规则图/执行记录) + 文件系统 (上传/模型/输出)            │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🧩 节点类型体系（6 类 34 个已注册）

| 类别 | 颜色 | 节点数 | 节点 |
|------|------|------|------|
| **输入 INPUT** | 🟢 绿 #4CFF4C | 9 | ImageCapture, VideoCapture, ScreenCapture, ManualTrigger, TimerTrigger, CronTrigger, WebhookTrigger, ApiTrigger, YOLOTrigger |
| **检测 DETECTION** | 🔵 青 #00F0FF | 2 | YOLOModel, ObjectDetector |
| **处理 PROCESSING** | 🟡 黄 #FFFF4C | 6 | ImagePreprocessor, Filter, Tracker, CategoryEncode, Template, MergeDetections, RoiExtract |
| **动作 ACTION** | 🟠 橙 #FF7F4C | 5 | KeyboardAction, MouseAction, WaitAction, HttpRequestAction, LogAction |
| **逻辑 LOGIC** | 🟣 紫 #DC4FDC | 8 | Branch, ParallelBranch, Delay, SetVariable, Counter, ObjectExistsCondition, ConfidenceThresholdCondition, VariableCondition |
| **输出 OUTPUT** | 🔴 红 #FF4C4C | 3 | SaveResult, Notification, Display |

> 📊 **总计：34 个已注册**（截至 2026-06-06，Phase 15 推进后）。条件类节点在 `NodeCategory` 枚举中归入 LOGIC（枚举共 6 类），故此处不单列 CONDITION。

---

## 📊 现状评估（2026-06-03）

| 维度 | 现状 | 完成度 |
|------|------|--------|
| 后端 API | 20 个端点（CRUD + 验证 + 激活 + Webhook + 执行 + 取消） | ✅ 100% |
| 节点定义 | NodeRegistry 统一管理，34 节点全部注册 | ✅ 100% |
| 执行引擎 | Kahn 拓扑排序 + 层内 `asyncio.gather()` 并行 | ✅ 100% |
| WebSocket | 6 种事件（started/executed/failed/timeout/progress/complete） | ✅ 100% |
| 单元测试 | 202/202 通过（100%，含 10 个 cv2 依赖 skip） | ✅ |
| 节点配置 schema | 34/34 = 100% 覆盖 | ✅ |
| 变量系统 | `{{var}}` 插值 + 变量面板 | ✅ |
| 撤销重做 | 50 步历史 | ✅ |
| **属性面板 UI** | 数据绑定有，模板无 drawer | ⚠️ 缺口 |
| **YOLO 触发对接** | 框架有，未对接推理服务 | ⚠️ 缺口 |
| **节点实现 TODO** | 5 处（键盘/鼠标/视频/屏幕/通知） | ⚠️ 缺口 |

---

## 🚦 阶段规划

### Phase 1-6：核心功能（后端为主）

- **Phase 1** ✅ — 节点注册表（34 节点、6 类、Pydantic 模型）
- **Phase 2** ✅ — 执行引擎（Kahn 拓扑、环检测、并行执行）
- **Phase 3** ✅ — 画布交互（拖拽/连线/选择/复制/删除/撤销重做）
- **Phase 4** ⚠️ — 属性配置面板（数据层完成，UI 待补）
- **Phase 5** ✅ — WebSocket 实时通信（6 种事件、自动重连）
- **Phase 6** ✅ — 规则触发机制（手动/定时/Webhook/Cron/API）

### Phase A-H：前端专项重构

- **Phase A** ✅ — 34/34 节点 `config_schema` 补全
- **Phase B** ✅ — 自定义 `RuleNode.vue` 组件（ComfyUI 风格）
- **Phase C** ✅ — 节点内嵌配置控件（slider/dropdown/checkbox）
- **Phase D** ✅ — 属性面板完善（动态表单、变量绑定、断连）
- **Phase E** ✅ — 复制粘贴/撤销重做/右键菜单
- **Phase F** ✅ — 变量系统 UI
- **Phase G** ✅ — Toast/MiniMap/搜索优化
- **Phase H** ✅ — UI 样式优化（el-button、深色主题）

### Phase 9-12：端到端完善

- **Phase 9** ✅ — 节点编辑修复 + 前端架构重构（Pinia 单源）
- **Phase 10** ✅ — 端到端 Bug 修复 + 节点级 timeout
- **Phase 10.1** ✅ — 节点执行指标端到端链路
- **Phase 10.2** ✅ — 执行超时保护增强
- **Phase 11** ✅ — 节点面板端口类型过滤
- **Phase 11.1** ✅ — 逐节点前端验证计划
- **Phase 12** ✅ — `template` 节点 + Region 模型
- **Phase 12.1/2/3** ✅ — Phase 13 节点扩展
- **Phase 13** ✅ — `merge_detections` + `roi_extract` + Atlas 对话框 + 4 Bug 修复
- **Phase 14** ✅ — VueFlow 格式校验修复 + class_names 动态化 + logs API List 格式
- **Phase 15** ✅ — 8 项画布性能优化（shallowRef + VueFlow manual control + JSON 路线 + 历史栈瘦身 + updateNodeConfig 内变 + widget v-memo + 缩略图 idle + 节点重绘隔离）
- **Phase 15 验收**：后端 208 passed / vue-tsc 0 错误 / Playwright 0 console errors / 远端已同步
- **Phase 15 后续用户报告 Bug** ✅ — el-select popper z-index 修复（YOLO检测下拉可见）+ Atlas↔Model 双向关系 + YOLO 节点 device 字段透传 + model_id 类型 integer
- **Phase 16** ✅ — 4 个候选补登（端口类型多选 16.1 / 节点状态高亮 16.2 / class_names 自动拉取 16.3 / YOLO 触发器对接文档确认 16.4）

---

## 🎨 设计规范

### 节点结构（画布节点）

**端口方向：左进右出**（左侧=INPUT 接收，右侧=OUTPUT 流出）

```
┌────────────────────────────────────────────────────┐
│ ■■■ [图标]  节点标题                    [⋮]菜单   │  ← 顶部 3px 色条
├─────────────┬────────────────────────┬────────────┤
│  ← INPUT   │     配置控件区          │  OUTPUT →  │
│  ● source  │  [slider/dropdown/...]  │  ● result  │
│             │                        │            │
└─────────────┴────────────────────────┴────────────┘
```

### Widget 类型规范

| widget | 表单类型 | 说明 |
|--------|---------|------|
| `text` | 单行文本 | 默认 |
| `number` | 数字输入框 | 整数/小数 |
| `slider` | 滑块+数字 | 带 min/max/step |
| `dropdown` | 下拉选择 | enum 列表 |
| `model-select` | 模型选择器 | 动态加载模型列表 |
| `checkbox` | 开关 toggle | boolean |
| `file-path` | 路径输入+浏览 | 文件选择 |
| `textarea` | 多行文本 | 长文本 |
| `code` | 代码编辑器 | 表达式 |

### 变量绑定表达式

**格式**：`{{variable_name}}` — 插值引用变量

**内置变量**：
- `{{trigger_type}}` — 触发器类型（manual/timer/cron/webhook）
- `{{timestamp}}` — 当前 Unix 时间戳
- `{{graph_id}}` — 当前图 ID
- `{{execution_id}}` — 当前执行 ID

---

## 🔄 执行状态机

### 节点状态

| 状态 | 说明 | 触发条件 |
|------|------|---------|
| `idle` | 空闲/等待执行 | 初始状态 / 执行完成后重置 |
| `running` | 执行中 | 节点开始处理 |
| `success` | 执行成功 | 节点正常完成 |
| `failed` | 执行失败 | 节点处理出错 |

### 图执行流程

1. 找出所有 INPUT/TRIGGER 节点（无上游依赖）
2. 并行执行这些节点
3. 节点完成后，通知依赖它的下游节点
4. 下游节点检查所有输入是否就绪
5. (全部就绪) 执行下游节点
6. 重复直到所有节点完成或遇到错误
7. 图执行结束，更新执行状态

---

## ✅ 验收清单（截至 2026-06-03）

| 阶段 | 验收项 | 状态 |
|------|--------|------|
| Phase 1 | GET /api/rule-engine/nodes/definitions 返回完整 6 类节点定义 | ✅ |
| Phase 1 | 节点面板能够按类别分组展示 | ✅ |
| Phase 2 | 规则图执行顺序与拓扑依赖关系一致 | ✅ |
| Phase 2 | 无环图正常执行，有环图报错并返回环节点信息 | ✅ |
| Phase 2 | 单层内多节点并行执行，总耗时 ≈ 最慢节点耗时 | ✅ |
| Phase 3 | 从左侧面板拖拽节点到画布 | ✅ |
| Phase 3 | 两节点间连线，类型匹配时允许，类型不匹配时拒绝 | ✅ |
| Phase 3 | Ctrl+Z/Y 可撤销/重做（至少 20 步） | ✅ |
| Phase 4 | 选中节点后，右侧面板正确显示节点类型、ID、名称 | ✅ |
| Phase 5 | 执行规则时，前端收到逐节点推送 | ✅ |
| Phase 5 | 连接断开时自动重连 | ✅ |
| Phase 6 | 手动触发、定时触发、Webhook 触发 | ✅ |
| Phase 7-12 | 端到端完善（见上方阶段规划） | ✅ |

---

## ⚠️ 风险识别

| 风险 | 可能性 | 影响 | 应对措施 |
|------|--------|------|---------|
| Vue Flow 功能限制，无法满足复杂交互 | 中 | 高 | 考虑混用 Canvas 自绘节点（参考 ComfyUI） |
| 节点并行执行导致竞态条件 | 中 | 高 | 使用 asyncio.Lock 保护共享资源 |
| 大规模节点（100+）性能下降 | 中 | 中 | 虚拟化渲染 + Web Worker |
| WebSocket 断连重连 | 高 | 低 | 自动重连 + 消息缓冲 |
| 定时任务与服务器重启 | 低 | 中 | APScheduler + 数据库持久化 |

---

## 🔗 外部参考

- **ComfyUI 架构** — github.com/comfyanonymous/ComfyUI
- **Vue Flow** — vueflow.dev
- **Node-RED** — nodered.org

---

## 🛠️ 文档维护

- **统一格式**：所有设计文档均为 Markdown（`.md`）
- **目录结构**：
  - `docs/research-md/` — 架构设计、技术调研
  - `docs/guides-md/` — 使用指南
  - `docs/plans-md/` — 迭代计划
  - `docs/archives-md/` — 已完成阶段归档
  - `docs/dev-md/` — 开发参考（节点手册等）
  - `docs/文档中心.md` — 顶级入口
- **转换器**：`scripts/docs/html_to_md.py`（基于 `html.parser`，支持标题/表格/列表/代码块/加粗/多语言嗅探）
- **语言标签**：自动嗅探（python/typescript/javascript/vue/html/bash/yaml/sql/json/text）

> ⚠️ **本批次为最终转换**：所有 HTML 源已清空。未来更新直接编辑 MD，不再回退 HTML。
