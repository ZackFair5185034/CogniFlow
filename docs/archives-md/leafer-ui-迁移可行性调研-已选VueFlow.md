# leafer-ui 迁移可行性调研

> **生成日期**: 2026-06-07
> **调研主题**: CogniFlow 规则引擎画布（@vue-flow/core 1.48.2）底层是否可迁移到 leafer-ui
> **结论先行**: **不建议在当前阶段迁移**。leafer-ui 是通用 2D Canvas 图形引擎，**不是**节点图编辑器；CogniFlow 所需的节点图语义（Handle、Port、Edge 路由、Box Select、Undo/Redo、Element Plus 控件内嵌）全部需自实现，工作量 2-4 月单人，且会丢失 VueFlow 现成的 DOM/a11y 优势。性能上 80 节点 60fps 已达成，迁移无明显收益。
> **如果确需升级画布栈**: **AntV X6 3.x** 是最对位的替代（同 MIT、Vue 3 官方绑定、内置虚拟渲染+正交路由），迁移成本可降至 1-2 周。

---

## 1. 调研背景

CogniFlow 规则引擎画布当前使用 VueFlow（@vue-flow/core 1.48.2），经过 4 轮优化（commit `9fbab4cf` `817b2ec8` `5882437e` `dcc00ad5`）后，已在 80 节点规模下达到 60fps。

考虑到未来扩展到 200-500 节点，需要评估**更换底层图形引擎**的可行性。本报告针对社区关注的 **leafer-ui**（国产 Canvas 引擎，号称"百万交互层"）做完整调研。

---

## 2. 调研方法

| 维度 | 数据源 |
|---|---|
| 许可证原文 | leafer-ui GitHub LICENSE 文件（MIT 标准文本，逐字核对） |
| 包元数据 | npm registry（30+ 包，全部 MIT@2.1.4） |
| 商业化 | PxGrow 官网（pxgrow.com） |
| 维护信号 | shields.io GitHub badges / npm 周下载 |
| 竞品对比 | AntV X6 / LogicFlow / VueFlow / Konva / PixiJS 官方仓库 |
| CogniFlow 现状 | 本地源码 + git log（最近 10 个画布 commit） |
| 替代品 | 蚂蚁 X6 / 滴滴 LogicFlow GitHub + 官方文档 |

所有引用见各章节末。

---

## 3. 核心结论速览

| 维度 | 结论 |
|---|---|
| **许可证** | ✅ MIT，与 CogniFlow 兼容；商业功能在独立 PxGrow 包 |
| **维护状态** | ✅ v2.1.4 (2026-06)，周下载 ~240K，4.1k stars，最后 commit 上周 |
| **核心定位** | ❌ **通用 2D Canvas 引擎，不是节点图编辑器** |
| **节点图原语** | ❌ 无 Handle / Port / Edge 路由 / Box Select / MiniMap，需自实现 |
| **Vue 3 集成** | ⚠️ 无官方 @leafer-ui/vue，需手动 onMounted/onBeforeUnmount |
| **性能优势** | ⚠️ vendor 自报"百万层"，无第三方基准 |
| **迁移成本** | ❌ 单人 2-4 月；最大隐性成本是重写 RuleNode.vue（1156 行） |
| **推荐** | ❌ 不迁移。若需升级，**AntV X6 3.x** 是最对位替代 |

---

## 4. leafer-ui 项目档案

### 4.1 基本信息

| 项 | 值 | 来源 |
|---|---|---|
| 仓库 | github.com/leaferjs/leafer-ui（monorepo） | GitHub |
| 最新版本 | **leafer-ui 2.1.4**（2026-06-02） | npm registry |
| 内部包 | 30+ 子包（@leafer-ui/core/draw/display/data/render/event/interaction/platform-*...） | npm |
| 关联包 | `leafer`（核心）、`leafer-in`（官方插件）、`leafer-x`（社区插件）、`code`（示例）、`docs` | GitHub org |
| 许可证 | **MIT**（核心永久开源） | LICENSE 文件 |
| Stars | leafer-ui **4.1k** / leafer 核心 334 / leafer-in 29 | shields.io |
| npm 周下载 | ~240K（所有子包合计） | npm |
| 商业公司 | 像素生长（北京）科技中心 / PxGrow | pxgrow.com |
| 单点风险 | 主要作者 Chao Wan，bus factor = 1 | shields.io |

### 4.2 渲染模型

- **Canvas 2D** 为主，非 WebGL / 非 SVG
- 三层优化路径：`__drawFast`（直绘）→ `__draw`（复杂）→ `__drawShape`（特效）
- **脏矩形局部重绘**：`renderer.addBlock(bounds)` + `requestRender(change)` 只重绘变化区域
- 命中检测：路径式 + 像素式（`packages/hit/src/UIHit.ts`），无场景级空间索引
- 体积：核心 66KB min+gzip，零依赖

### 4.3 元素类型

```
Leaf (核心)
 └─ UI
     ├─ Rect / Ellipse / Polygon / Star / Line / Image / Text / Path / Canvas / Pen
     └─ Group
         ├─ Box → Frame
         └─ Leafer
```

---

## 5. 许可证深度核查

### 5.1 核心 LICENSE 原文（leafer-ui）

```
The MIT License (MIT)
Copyright (c) 2023-present, Chao (Leafer) Wan
[...标准 MIT 文本，无任何附加条款...]
```

**所有 30+ monorepo 包均使用同一份标准 MIT 文本**（npm registry 验证：2026-06-07）。

### 5.2 商业产品定位

- **核心永远 MIT**（README 明示："LeaferJS 永久开源 (MIT)：核心功能和基础插件始终保持开源与自由"）
- **商业功能在独立 PxGrow 产品**（不是 leafer-ui 的一部分）：

| 系列 | 内容 | 价格 |
|---|---|---|
| **Quantum Engine** | 极端性能引擎（最贵） | 报价制 |
| **Light-Speed Engine** | 视口/图像/矢量/区域 Lighter | 报价制 |
| **High-End Plugin** | Clipper / Tiler / Path Editor / Gradient Editor | 按需申请 |
| **Pro Plugin** | Scrollbar / Background Run / Film / Filter / **Linker**（连接线）/ Transition / Stroke Sides | 多数付费 |
| **Enhanced Plugin** | "采用宽松授权"（部分开源） | 不公开 |

**Linker（连接线）插件**对 CogniFlow 节点边绘制直接相关，但属于付费插件。

### 5.3 与替代品对比

| 库 | 最新版 | 许可证 | 备注 |
|---|---|---|---|
| **leafer-ui** | 2.1.4 | MIT | 核心免费 + PxGrow 商业插件 |
| Konva | 10.3.0 | MIT | 纯 MIT |
| Fabric.js | 7.4.0 | MIT | 纯 MIT |
| PixiJS | 8.19.0 | MIT | 纯 MIT |
| AntV X6 | 3.1.7 | MIT | 纯 MIT（蚂蚁） |
| LogicFlow | 2.2.3 | **Apache-2.0** | 含专利授权（滴滴） |
| VueFlow | 1.48.2 | MIT | 纯 MIT（CogniFlow 现用） |

**结论**：leafer-ui 核心 MIT 完全兼容 CogniFlow（也是 MIT）。无许可证风险。**但 PxGrow 的商业化是潜在演进风险**——如果未来核心功能（连接线、虚拟渲染等）改为付费，将是隐性迁移坑。

---

## 6. leafer-ui vs 节点图编辑器：根本定位差异

### 6.1 概念对照

| | **VueFlow** | **leafer-ui** |
|---|---|---|
| 抽象 | `Node` / `Edge` / `Handle` / `Position` | `Rect` / `Line` / `Group` / `UI` |
| 编程模型 | 声明式 Vue SFC + slots；数据驱动 `ref<Node[]>` | 命令式 `leafer.add(rect)`；手动 mutation |
| 渲染目标 | SVG (default) + HTML overlay | Canvas 2D |
| 节点图原语 | **开箱即用**：Handle / Port / Edge 类型 / MiniMap / Controls / Resizer | **全部需自实现** |
| Vue 集成 | 一等公民，`<script setup>` + composables | 无官方绑定 |
| 语义 | **图感知**（边自动重路由、端口吸附、多选状态） | 通用形状编辑（移动/缩放/旋转/倾斜） |
| 性能机制 | 视口虚拟化 `only-render-visible-elements` | vendor 宣称"百万层"，脏矩形局部重绘 |
| 动画 | CSS / Vue transition / `animated: true` 边 | `@leafer-in/animate` `rect.animate()` |
| 维护方 | 社区（bcakmakoglu） | 单一作者 + PxGrow 商业支撑 |
| 许可证 | MIT | MIT |

### 6.2 关键差异：leafer-ui 的"图编辑器"在 PxGrow

leafer-ui **核心没有节点图概念**。要构建 VueFlow 等价能力，需组合：

- `@leafer-in/editor`：选择 + 变换（move/scale/rotate/skew per element，**不是图级端口**）
- `@leafer-in/animate`：动画
- `@leafer-in/viewport`：视口
- `@leafer-in/arrow`：箭头线
- `Line` / `Path`：直线与折线
- **@leafer-in/connect-line**：未在官方文档找到（uncertain）
- **@leafer-in/linker**：在 PxGrow 付费系列（连接线插件）

**graph data model（节点/边/视口/选中状态/历史栈/连接验证/Box select/MiniMap）全部需自己写**。

### 6.3 哲学对比

- **VueFlow** = **数据驱动**：`nodes[]` / `edges[]` 是 source of truth，框架负责 diff + 重渲染
- **leafer-ui** = **DOM-like 命令式**：`leafer.add(rect)` 后 mutate `rect.x = ...`，调用 `requestRender()`

这等价于 React 生态里 **React Flow（数据驱动） vs 裸 Canvas（命令式）** 的分歧。

---

## 7. CogniFlow 画布现状（基线）

| 项 | 现状 |
|---|---|
| 文件 | `RuleCanvas.vue` 3643 行 + `RuleNode.vue` 1156 行 + `ruleEngine.ts` 621 行 = **5420 行** |
| 节点数 | 80 节点 @ 60fps（优化后） |
| 节点类目 | 6 类别（input/detection/processing/action/logic/output） |
| 端口类型 | 14 种，每种独立色 |
| 边类型 | 单一 `default` + `MarkerType.ArrowClosed` |
| 节点结构 | 标题栏 + 端口区 + 8 种 widget + 状态指示器 |
| 节点 widget | slider / number / dropdown / multiselect / model-select / file-picker / textarea / code / toggle 等 |
| 控件库 | **Element Plus 2.5+**（el-slider / el-input / el-select 等）**内嵌于节点体** |
| 优化历史 | 4 轮：viewport 虚拟化、selection 过滤、rAF 节流、CSS 化选中视觉、outline 替代 border |
| 历史栈 | 20 步 |
| 撤销/重做 | JSON 序列化 + 12 个 VueFlow 内部字段 strip |
| 集成 | WebSocket 执行状态推送、Kahn 拓扑排序、变量 `{{name}}` 绑定、模型列表 API |

### 7.1 VueFlow API 实际使用面

| VueFlow 功能 | 引用位置 |
|---|---|
| `<VueFlow>` 组件 | RuleCanvas.vue:359-411 |
| `<MiniMap>` | RuleCanvas.vue:400-407 |
| `<Controls>` | RuleCanvas.vue:410 |
| `<Handle>` | RuleNode.vue:276, 291 |
| `useVueFlow()` 解构 11 个 API | fitView, setCenter, screenToFlowCoordinate, userSelectionRect, setViewport, getViewport, addSelectedNodes, addSelectedEdges, getNodes, applyNodeChanges, applyEdgeChanges |
| `Position` enum | RuleNode.vue:279, 294 |
| `MarkerType.ArrowClosed` | ruleEngine.ts:209 |
| `SelectionMode.Partial` | RuleCanvas.vue:382, 618 |
| 20+ props | `:only-render-visible-elements` `:pan-on-drag` `:pan-on-scroll` `:zoom-on-scroll` `:snap-to-grid` `:connection-radius` `:is-valid-connection` 等 |
| 16+ events | `@node-click` `@node-drag-start` `@nodes-change` `@edges-change` `@selection-drag-start/stop` 等 |

---

## 8. 迁移到 leafer-ui 的隐性成本

### 8.1 节点图原语需自实现

| 缺失原语 | Leafer 状态 | 重建成本 |
|---|---|---|
| **Box / 框选** | 无 | 高（射线检测 + 选中状态同步） |
| **节点 Handle / Port** | 无 | 高（端口类型 metadata + 拖拽手势） |
| **Bezier / 边路由** | `Line` 仅直线 | 高（手写 bezier 路径） |
| **连接验证** | 无 | 高（手写 `isValidConnection`） |
| **Auto-pan（拖拽近边）** | 无 | 中（rAF 循环） |
| **MiniMap** | 无 | 高（第二 canvas + 缩略场景） |
| **Undo/Redo** | 无 | 中（JSON 快照或 Command 模式） |
| **视口虚拟化** | 脏矩形≠视口剔除 | 中（自维护 visible-bounds） |
| **节点 Resizer** | 无（editor 插件仅变换） | 中（8 点 gizmo） |
| **Snap to grid** | 无 | 低（量化计算） |
| **a11y / 键盘导航** | 无 | 高（无 canvas a11y 模型） |
| **change pipeline** | 无 | 高（手写 `applyNodeChanges` 等价物） |
| **`<Handle>` 端口** | 无 | 高 |

**LoC 估算**: 实现上述原语需 **1500-2000 行 TS**（bare-bones 图编辑器） + **500-1000 行** 业务节点模板，总计 **2000-3000 行**。

### 8.2 Deal-breaker：RuleNode.vue 的 Vue 响应式

`RuleNode.vue` 1156 行：
- 内嵌 **Element Plus 控件**（el-slider / el-input / el-select）
- 端口元数据 `data.inputs/outputs` 驱动 `v-for` 渲染
- `v-memo="[data.id, data.status, data.config]"` 性能优化
- 26 处 `<el-*>` 组件

**Canvas 化方案**：

| 方案 | 问题 |
|---|---|
| **A. foreignObject** | Leafer 无文档化 API；为每个节点叠加 `<foreignObject>` 抵消 canvas 性能 |
| **B. 光栅化为 Image** | 控件失去交互（slider 不能拖、select 不能选） |
| **C. 混合 DOM overlay** | canvas 只画背景/边/网格，节点用 `<div>` 定位。**唯一可行方案，但失去 canvas 性能优势** |

**结论**：现有 `RuleNode.vue` 的 UX 几乎不可能"完全 canvas 化"。混合方案实际上把 leafer-ui 降级为"Canvas 网格背景 + VueFlow 节点"。

### 8.3 其它隐性成本

- **测试覆盖率为零**：项目无 Playwright 配置，唯一 canvas 相关测试是纯函数（`test_multiselect_filter.test.ts:13-30`）。迁移无安全网。
- **国内项目，英文 Q&A 少**：Stack Overflow 答案少，但 CLAUDE.md 要求中文注释这点对齐。
- **无 Vue 官方绑定**：无 `@leafer-ui/vue`，需 `onMounted` + `leafer.destroy()` 手动管理。
- **单点维护风险**：主要作者 Chao Wan，bus factor = 1。
- **视口虚拟化语义不同**：VueFlow 是 mount/unmount DOM 节点；leafer 脏矩形是局部重绘已渲染内容。两者在 500+ 节点时的行为不可类比。

---

## 9. 性能对比：理性看待"百万层"宣称

### 9.1 vendor 自报数据

> "LeaferJS significantly pushes the performance ceiling... creating 1 million interactive rectangles takes about 1.28 seconds with LeaferJS compared to 9-15 seconds for traditional Canvas libraries."

- 来源：leafer-ui README
- 官方基准页：`https://benchmark.leaferjs.com/leafer/leafer/`（**vendor 自营，未独立验证**）
- 优化机制：脏矩形局部重绘（`Leafer.forceRender(bounds?)`）

### 9.2 第三方基准

**未找到任何独立第三方对 leafer-ui / Konva / PixiJS 的 head-to-head 基准**。所有"快 10×"声明均为 vendor 自报。

### 9.3 CogniFlow 实际场景

| 场景 | VueFlow（当前） | leafer-ui（理论） |
|---|---|---|
| 50-200 节点 | 流畅 | 流畅 |
| 200-500 节点 | 需 `only-render-visible-elements` | 强（脏矩形保持低重绘） |
| 500-2000 节点 | VueFlow 挣扎 | 仍需自实现视口剔除 |
| 10K+ 节点 | 不现实 | 理论可行，无基准 |
| 拖拽启动微卡 | 43-123ms（VueFlow 内部 `applyVueFlowNodeChanges`） | 架构上可避免（脏矩形重绘） |

**但**：拖拽启动卡顿主要来自 Vue 响应式 diffing（200+ 节点时 43-123ms），leafer 通过绕过 Vue reactivity 确实能消除这部分。**这是 leafer-ui 在拖拽性能上的真实优势**。

但 CogniFlow 当前 80 节点 60fps 已达成，迁移到 leafer-ui 获得的拖拽优势**在 < 200 节点规模下不可测**。

### 9.4 性能问题的根因不在引擎

CogniFlow 最近的 4 轮优化（`9fbab4cf` `817b2ec8` `5882437e` `dcc00ad5`）已经把"应用层可控开销"压到 1.1% drop rate。**剩余的拖拽启动卡顿 43-123ms 来自 VueFlow 内部 `applyVueFlowNodeChanges` + 80 个组件 re-render**——这是 VueFlow 自身的问题，但已经在视口虚拟化后被控制到可接受范围。

**换引擎**才能彻底消除这 43-123ms 启动卡顿。但代价是重写 2000-3000 行图原语 + 1156 行 RuleNode。

---

## 10. 替代方案对比

| 库 | 许可证 | 节点图开箱即用 | Vue 3 一等公民 | 视口虚拟化 | 维护方 | 推荐度 |
|---|---|---|---|---|---|---|
| **VueFlow 1.48（当前）** | MIT | ✅ | ✅ | ✅ built-in | 社区 | ⭐⭐⭐⭐（保持） |
| **AntV X6 3.x** | MIT | ✅ 完整 | ✅ `@antv/x6-vue-shape` | ✅ `Scroller virtual:true` | 蚂蚁 | ⭐⭐⭐⭐⭐（若升级） |
| **LogicFlow 2.2.3** | Apache-2.0 | ✅ BPMN 优化 | ✅ `@logicflow/vue-node-registry` | ⚠️ 需评估 | 滴滴 | ⭐⭐⭐（BPMN 场景） |
| **leafer-ui 2.1.4** | MIT | ❌ 全部手写 | ❌ 无官方绑定 | ❌ 需自实现 | PxGrow | ⭐（不推荐） |
| **Konva** | MIT | ❌ 底层 | ⚠️ `vue-konva` | ❌ 需自实现 | 社区 | ⭐（不推荐） |
| **butterfly-dag** | MIT | ⚠️ DAG-only | ⚠️ 适配器 | ❌ 久未维护 | 阿里 | ⭐（不推荐） |

### 10.1 AntV X6 为何最优

- **节点图功能开箱即用**：Dnd / Selection / MiniMap / History / Snapline / Transform / **Scroller（视口虚拟化）** / 多种 router（manhattan / orth / metro）
- **`@antv/x6-vue-shape`** 提供 Vue 3 一等公民节点注册：`register({ shape, component })` + `TeleportContainer`
- **拖拽时路由降级**：`movingRouterFallback: 'orth'`（**直接对应 CogniFlow 9fbab4cf commit 解决的痛点**）
- 单一 npm 包 `@antv/x6` 3.x（不再有 plugin-* 拆分）
- MIT / 蚂蚁背书 / 文档中英文
- 迁移估算：**1-2 周**（替换 npm 依赖 + 重写 `useVueFlow` 调用 + 节点模板适配 TeleportContainer）

### 10.2 LogicFlow 何时合适

- 如果 CogniFlow 未来要做 **BPMN 流程图**或与 Activiti 兼容导出
- 内置 `BpmnAdapter` 可与 bpmn-js 互操作
- Apache-2.0 提供专利授权（MIT 不含）

---

## 11. 迁移成本汇总

### 11.1 leafer-ui 迁移

| 项 | 估算 |
|---|---|
| **周期** | 2-4 月（单人） |
| **代码量** | 2000-3000 行新增 + 5420 行重构 |
| **风险** | R7 RuleNode.vue 改写是 deal-breaker；R4 节点图原语全部自实现；R8 a11y 倒退；R9 无测试保护 |
| **收益** | 80 节点场景无明显收益；200+ 节点场景未验证；理论可消除 43-123ms 启动卡顿 |
| **推荐度** | ❌ 不推荐 |

### 11.2 AntV X6 3.x 迁移（备选方案）

| 项 | 估算 |
|---|---|
| **周期** | 1-2 周（单人） |
| **代码量** | 100-300 行改动（替换 useVueFlow 调 + 节点 TeleportContainer + minimap/scroller 启用） |
| **风险** | 中（仍需回归测试） |
| **收益** | 内置 Scroller 视口虚拟化 + 正交路由拖拽降级 + Transform 节点 resizer（之前未用） |
| **推荐度** | ✅ 若需升级则推荐 |

### 11.3 保持现状

| 项 | 估算 |
|---|---|
| **周期** | 0（已落地 4 轮优化） |
| **代码量** | 0 |
| **风险** | 无 |
| **收益** | 80 节点 60fps 稳定；剩余卡顿来自 VueFlow 内部不可控路径 |
| **推荐度** | ✅ **当前阶段最稳** |

---

## 12. 何时应该重新考虑迁移

| 触发条件 | 推荐方案 |
|---|---|
| 节点数稳定 > 500，VueFlow 出现明显掉帧 | **AntV X6 3.x**（Scroller 虚拟渲染） |
| 需要 BPMN 兼容 / 流程图规范 | **LogicFlow 2.2.3** |
| 需要 Canvas 像素级编辑（图像标注/选区编辑） | **leafer-ui 2.x**（纯图形编辑场景） |
| 需要 AI 驱动的内容生成（leafer 自我定位） | 观望 leafer-ui 生态成熟度 |
| 单节点 widget 极简（无 Element Plus 控件内嵌） | leafer-ui 才有可能 |

**当前 CogniFlow 不命中任何一条**。建议保持 VueFlow 1.48，继续在小规模性能优化（如拆分 `NodeConfigField.vue` 子组件 + `keep-alive`，Stage 3 候选）上迭代。

---

## 13. 风险登记

| # | 风险 | 可能性 | 影响 | 备注 |
|---|---|---|---|---|
| R1 | leafer-ui 核心未来被改收费 | 低 | 高 | 商业化方向 PxGrow 较激进 |
| R2 | leafer-ui 维护中断（单点 bus factor） | 中 | 高 | 主要作者 1 人 |
| R3 | 迁移后性能未达预期 | 中 | 高 | vendor 数据无独立验证 |
| R4 | RuleNode.vue Element Plus 控件无法 canvas 化 | 极高 | **致命** | deal-breaker |
| R5 | 2-4 月迁移周期拖累其他功能 | 高 | 中 | 单人团队 |
| R6 | 无 a11y / 测试保护 | 中 | 中 | 迁移无安全网 |
| R7 | 失去 VueFlow 社区/StackOverflow 答案 | 中 | 低 | leafer 英文 Q&A 少 |

---

## 14. 结论与建议

### 14.1 总体结论

**不建议在当前阶段迁移到 leafer-ui**。

理由：
1. **定位错配**：leafer-ui 是通用 Canvas 引擎，不是节点图编辑器。迁移需重写 2000-3000 行图原语。
2. **Deak-breaker**：现有 `RuleNode.vue` 内嵌 Element Plus 控件，canvas 化方案全部会牺牲交互或抵消性能优势。
3. **收益不显**：CogniFlow 80 节点 60fps 已达成，迁移无明显性能收益。
4. **替代更优**：若需升级，AntV X6 3.x 才是对位替代（1-2 周 vs 2-4 月）。

### 14.2 行动建议

| 优先级 | 行动 |
|---|---|
| **P0** | **保持 VueFlow 1.48.2**，继续小规模优化（NodeConfigField 拆分 + keep-alive） |
| **P1** | 持续观察 leafer-ui 生态（特别是 `@leafer-in/linker` 和图形编辑器插件成熟度） |
| **P2** | 如果未来命中"500+ 节点明显掉帧"或"需要 BPMN/流程图规范"——**评估 AntV X6 3.x 迁移**（1-2 周） |
| **P3** | leafer-ui 暂列"备选"——若某天 CogniFlow 转向"图像标注 / 选区编辑"等 Canvas 原生场景再重新评估 |

### 14.3 决策一句话

> 画布引擎迁移的 ROI 取决于"现有方案的瓶颈是不是引擎本身"。**CogniFlow 的瓶颈不是引擎，是 1156 行的 RuleNode.vue 与 3643 行的 RuleCanvas.vue**——换引擎只是把"熟悉的问题"换成"陌生但更困难的问题"。

---

## 附录 A — 参考资料

### leafer-ui
- 仓库：https://github.com/leaferjs/leafer-ui
- LICENSE：https://raw.githubusercontent.com/leaferjs/leafer-ui/main/LICENSE（标准 MIT）
- 商业化：https://www.pxgrow.com/
- 基准页：https://benchmark.leaferjs.com/leafer/leafer/（vendor 自营）
- DeepWiki 镜像：https://deepwiki.com/leaferjs/leafer-ui

### 替代品
- AntV X6：https://github.com/antvis/X6（3.x MIT，@antv/x6 + @antv/x6-vue-shape）
- LogicFlow：https://github.com/didi/logicflow（2.2.3 Apache-2.0，@logicflow/vue-node-registry）
- Konva：https://github.com/konvajs/konva（MIT）
- PixiJS：https://github.com/pixijs/pixijs（MIT）
- butterfly-dag：阿里 DAG 库（MIT，久未维护）
- VueFlow：https://github.com/bcakmakoglu/vue-flow（CogniFlow 现用，MIT）

### CogniFlow 内部资料
- 性能分析：`docs/research-md/规则引擎画布性能分析.md`
- 大规模节点瓶颈：`docs/research-md/规则引擎画布大规模节点性能分析.md`
- 架构对比：`docs/research-md/规则引擎技术调研.md`
- 重构方案：`docs/research-md/规则引擎前端重构设计方案.md`
- 交互规范：`docs/research-md/规则引擎交互规范.md`
- 索引：`docs/research-md/rule-engine-index.md`

### 关键 git commits
- `9fbab4cf` P0+P1 画布性能优化（视口虚拟化 + selection 跳过 + v-memo）
- `817b2ec8` 根除拖拽卡顿（CSS transition + contain + GPU 合成层）
- `5882437e` 根除框选卡顿（select changes 过滤 + 选中视觉 CSS 化）
- `dcc00ad5` outline 替代 border-width（消除框选 80 次强制 layout）
- `57f2f275` Ctrl+A 全选 + 拖拽 rAF 节流

## 附录 B — 缩写

- **MIT**: Massachusetts Institute of Technology 许可证
- **Apache-2.0**: Apache License 2.0（含专利授权条款）
- **SSOT**: Single Source of Truth
- **rAF**: requestAnimationFrame
- **DAG**: Directed Acyclic Graph
- **BPMN**: Business Process Model and Notation
- **P0/P1/P2**: 优先级分级
- **a11y**: Accessibility（无障碍）
