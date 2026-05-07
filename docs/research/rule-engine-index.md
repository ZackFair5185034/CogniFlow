# CogniFlow 规则引擎 - 项目入口

> **文档版本：** v2.2
> **创建时间：** 2026-05-06
> **最后更新：** 2026-05-08
> **Phase 1-6 状态：** ✅ 全部完成（Kahn拓扑排序 + 层内并行，47测试通过）
> **Phase A-G 状态：** ✅ 全部完成
> **Phase 5 (UI修复) 状态：** ✅ 全部完成
> **相关文档：** `rule-engine-redesign-v2.md`（前端重构详细设计）

---

## 一、项目概述

### 1.1 核心功能目标

CogniFlow 规则引擎是一个**可视化编排**的视觉感知处理引擎，允许用户通过节点编辑器定义"检测→处理→动作"的完整流程。参考对象是 **ComfyUI**（最成熟的 AI 节点编辑器）和 **Node-RED**（工业级流程编排工具）。

| 目标 | 描述 |
|------|------|
| **可视化编排** | 无限画布上通过拖拽、连接节点来构建规则流程 |
| **节点类型化** | 输入、检测、处理、动作、逻辑、输出六类节点，类型安全连接 |
| **智能执行** | Kahn 拓扑排序 + 层内并行，支持条件分支 |
| **实时反馈** | WebSocket 推送执行进度，支持中断 |
| **持久化** | 规则图保存/加载，支持版本管理 |

### 1.2 现状评估

| 维度 | 现状 | 差距 |
|------|------|------|
| 前端画布 | RuleCanvas.vue 基础布局已完成（2175行） | 缺少节点拖拽、类型检查、撤销重做 |
| 后端 API | CRUD + 执行接口已有 | 执行引擎是串行，缺拓扑排序和并行 |
| 节点定义 | 无统一类型系统 | 需要新建节点注册表 |
| 实时通信 | WebSocket 基础已有 | 缺执行进度推送 |
| 变量系统 | 有 `variables_json` 字段 | 缺表达式解析和绑定 UI |

---

## 二、文档体系

```
docs/research/
├── rule-engine-index.md                    ← 【本入口文档】项目整体索引
├── rule-engine-development-plan.md         ← 开发计划总览
│
├── 📐 架构设计
│   ├── rule-engine-api-design.md            API 设计文档
│   ├── rule-engine-data-models.md           数据模型文档
│   ├── rule-engine-dev-guide.md            开发规范
│   ├── rule-engine-port-connection-design.md  端口连接设计规范
│   └── rule-engine-ui-ux-spec.md          UI/UX 交互规范
│
├── 🔧 阶段实现（详细技术文档）
│   ├── rule-engine-phase1-node-registry.md    Phase 1: 节点注册表
│   ├── rule-engine-phase2-execution-engine.md  Phase 2: 执行引擎
│   ├── rule-engine-phase3-canvas-frontend.md  Phase 3: 画布前端
│   ├── rule-engine-phase4-property-panel.md   Phase 4: 属性面板
│   ├── rule-engine-phase5-websocket.md         Phase 5: WebSocket
│   └── rule-engine-phase6-trigger.md           Phase 6: 触发机制
│
└── 🎨 前端重构（Phase A-E）
    └── rule-engine-redesign-v2.md              前端专项重构详细设计
```

---

## 三、技术架构

### 3.1 系统架构图

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

### 3.2 节点类型体系

```
输入 ──→ 检测 ──→ 处理 ──→ 动作 ──→ 输出
         ↑
逻辑 ────┘（条件分支/循环）
```

| 类别 | 颜色代码 | 节点类型 | 说明 |
|------|---------|---------|------|
| **Input** | `#4CFF4C` | ImageCapture, VideoCapture | 外部数据采集 |
| **Detection** | `#00f0FF` | YOLOModel | 目标检测模型 |
| **Processing** | `#FFFF4C` | CategoryEncode, Filter | 数据处理变换 |
| **Action** | `#FF7F4C` | MouseClick, KeyPress, Notification | 外部操作执行 |
| **Logic** | `#DC4FDC` | Condition, Timer | 流程控制 |
| **Output** | `#FF4C4C` | ActionOutput, SaveResult | 结果输出 |

---

## 四、阶段规划

### 4.1 Phase 1-6：核心功能（后端为主）

| 阶段 | 名称 | 核心交付物 | 状态 |
|------|------|----------|------|
| **Phase 0** | 项目准备与环境搭建 | 4份架构文档 | ✅ 完成 |
| **Phase 1** | 节点类型系统（后端） | NodeRegistry + 6 类节点执行器 | ✅ 完成 |
| **Phase 2** | 执行引擎核心（后端） | Kahn 拓扑排序 + 层并行执行 | ✅ 完成 |
| **Phase 3** | 画布交互基础（前端） | Vue Flow 节点拖拽 + 连线 + 基本操作 | ✅ 完成 |
| **Phase 4** | 节点配置面板（前端） | 属性编辑表单 + 变量绑定 | ✅ 完成 |
| **Phase 5** | 实时通信（前后端） | WebSocket 进度推送 + 日志 | ✅ 完成 |
| **Phase 6** | 规则激活与触发 | 定时/手动/Webhook 触发机制 | ✅ 完成 |

### 4.2 Phase A-E：前端专项重构

| 阶段 | 名称 | 核心交付物 | 状态 |
|------|------|----------|------|
| **Phase A** | 后端 config_schema 补全 | 18 个节点完整 config_schema | ✅ 完成 |
| **Phase B** | 前端节点样式重构 | ComfyUI 风格自定义节点组件 | ✅ 完成 |
| **Phase C** | 节点内嵌配置控件 | 动态渲染 slider/dropdown/checkbox 等 | ✅ 完成 |
| **Phase D** | 属性面板完善 | 动态表单 + 变量绑定 + 执行状态 | ✅ 完成 |
| **Phase E** | 交互完善 | 复制粘贴 + 撤销重做(20步) + 右键菜单 | ✅ 完成 |
| **Phase F** | 变量系统 | Pinia Store + 表达式工具 + VariablePanel | ✅ 完成 |
| **Phase G** | 优化增强 | Toast 组件 + MiniMap 彩色节点 | ✅ 完成 |

---

## 五、设计规范（详见 rule-engine-redesign-v2.md）

### 5.1 节点结构（画布节点）

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

### 5.2 配色体系

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

### 5.3 Widget 类型规范

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

### 5.4 SvgIcon 使用规范

**组件引入方式：**

```typescript
// 方式一：全局组件（已在 main.ts 注册，可直接使用）
// 无需 import，在模板中直接使用
<SvgIcon name="icon-name" />

// 方式二：需要显式引入 SvgIcon（如果 IDE 报类型错误）
import SvgIcon from '@/components/SvgIcon.vue'
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

---

## 六、变量绑定表达式

### 6.1 变量引用格式

```
{{variable_name}}           # 引用简单变量
{{object.property}}         # 引用对象属性
{{array[index]}}            # 引用数组元素
{{object.property.nested}}  # 深層属性访问
```

### 6.2 内置变量

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `$now` | datetime | 当前时间戳 |
| `$graph.id` | number | 当前规则图 ID |
| `$execution.id` | number | 当前执行记录 ID |
| `$node.id` | string | 当前节点 ID |
| `$node.label` | string | 当前节点名称 |

### 6.3 表达式引擎要求

- 使用 JavaScript 表达式语法
- 支持基本的数学运算：`+`, `-`, `*`, `/`, `%`
- 支持比较运算：`==`, `===`, `!=`, `!==`, `>`, `<`, `>=`, `<=`
- 支持逻辑运算：`&&`, `||`, `!`
- 支持三元运算符：`condition ? true_val : false_val`
- 支持括号分组：`(a + b) * c`

---

## 七、执行状态机

### 7.1 节点状态

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

### 7.2 图执行流程

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

---

## 八、快速开始

### 1. 了解项目背景
阅读本入口文档，了解项目目标、架构设计、文档体系。

### 2. 查阅详细实现
各阶段技术实现文档包含：
- **数据结构**：关键数据结构的字段说明
- **API 接口**：输入输出格式、错误处理
- **实现流程**：关键函数的执行流程
- **边界情况**：空图、单节点、环回检测等的处理
- **验收清单**：可测试的验收标准

### 3. 开始开发
```bash
# 后端开发
cd backend
uvicorn app:app --reload

# 前端开发
cd webui
pnpm dev
```

---

## 九、验收清单（2026-05-08 实测更新）

### Phase 1：节点类型系统（后端）
- [x] `GET /api/rule-engine/nodes/definitions` 返回完整的 6 类节点定义
- [x] 节点面板能够按类别分组展示（前端可验证）
- [x] 每个节点执行器能独立执行并返回输出（单元测试覆盖）
- [x] 新增节点只需注册到 `NodeRegistry`，无需修改其他代码

### Phase 2：执行引擎核心（后端）
- [x] 规则图执行顺序与拓扑依赖关系一致
- [x] 无环图正常执行，有环图报错并返回环节点信息
- [x] 单层内多节点并行执行，总耗时 ≈ 最慢节点耗时
- [x] 执行中途可取消，已执行的节点结果不丢失

### Phase 3：画布交互基础（前端）
- [x] 从左侧面板拖拽节点到画布，节点正确创建
- [x] 两节点间连线，类型匹配时允许，类型不匹配时拒绝并提示
- [x] 选中节点按 Delete 可删除
- [x] Ctrl+Z/Y 可撤销/重做（至少 20 步）

### Phase 4：节点配置面板（前端）
- [x] 选中节点后，右侧面板正确显示节点类型、ID、名称
- [x] 输入参数表单根据节点类型动态生成
- [ ] 变量下拉菜单能插入 `{{variable_name}}` 到输入框

### Phase 5：实时通信（前后端）
- [x] 执行规则时，前端收到 `node_started` → `node_executed` 逐节点推送
- [x] 进度条实时更新
- [x] 连接断开时自动重连

### Phase 6：规则激活与触发
- [x] 手动触发：点击按钮立即执行规则
- [x] 定时触发：可配置 Cron 表达式，按计划执行
- [x] Webhook 触发：提供 Webhook URL，外部请求触发执行

### Phase A-E：前端专项重构
- [x] Phase A: GET /api/rule-engine/nodes/definitions 返回完整 config_schema
- [x] Phase B: 节点显示 3px 色条、图标、标题、内嵌控件、底部摘要
- [x] Phase C: 根据 config_schema 自动渲染对应控件
- [x] Phase D: 属性面板支持变量绑定（📎按钮），显示执行状态
- [x] Phase E: Ctrl+Z 撤销、Ctrl+Y 重做、Ctrl+C/V 复制粘贴节点、右键菜单

---

## 十、风险识别

| 风险 | 可能性 | 影响 | 应对措施 |
|------|--------|------|---------|
| Vue Flow 功能限制，无法满足复杂交互 | 中 | 高 | 考虑混用 Canvas 自绘节点（参考 ComfyUI） |
| 节点并行执行导致竞态条件 | 中 | 高 | 使用 asyncio.Lock 保护共享资源 |
| 大规模节点（100+）性能下降 | 中 | 中 | 虚拟化渲染 + Web Worker |
| WebSocket 断连重连 | 高 | 低 | 自动重连 + 消息缓冲 |
| 定时任务与服务器重启 | 低 | 中 | APScheduler + 数据库持久化 |

---

## 十一、参考文档

| 文档 | 说明 |
|------|------|
| `canvas-editor-research-2026-05-06.md` | 调研报告 |
| `rule-engine-redesign-v2.md` | 前端重构详细设计（Phase A-E） |
| `rule-engine-api-design.md` | API 详细设计 |
| `rule-engine-data-models.md` | 数据模型设计 |
| `rule-engine-dev-guide.md` | 开发规范 |
| ComfyUI 架构 | https://github.com/comfyanonymous/ComfyUI |
| Vue Flow | https://vueflow.dev/ |

---

## 十二、变更记录

| 日期 | 版本 | 变更内容 | 变更人 |
|------|------|---------|-------|
| 2026-05-06 | v1.0 | 初始版本 | - |
| 2026-05-06 | v1.1 | 重新组织文档体系，添加索引文档 | - |
| 2026-05-06 | v1.2 | 统一节点类型清单；细化变量解析方案；明确执行器异步规范 | - |
| 2026-05-06 | v2.0 | 整合 rule-engine-redesign-v2.md，更新 Phase A-E 状态，同步设计规范 | - |
| 2026-05-08 | v2.2 | 更新验收清单为实测通过状态，新增 Phase 5 (UI修复) 记录 | - |
