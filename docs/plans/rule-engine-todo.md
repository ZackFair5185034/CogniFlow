# 规则引擎 UI 迭代计划 & TODO

> **当前阶段：** UI 问题修复 & 端口连接规范落地
> **更新时间：** 2026-05-09

---

## Phase 1: 端口连接规范落地（依据端口连接设计文档）

| # | 任务 | 文件 | 状态 |
|---|------|------|------|
| 1.1 | 后端 `PortType` 枚举补充完整 14 种类型 | `backend/services/rule_engine/models.py` | ✅ 已完成 |
| 1.2 | 前端 `PORT_TYPES` 添加缺失类型 | `webui/src/views/RuleCanvas.vue` | ✅ 已完成 |
| 1.3 | 前端 `isPortCompatible` 补全全部类型的兼容规则 | `webui/src/views/RuleCanvas.vue` | ✅ 已完成 |
| 1.4 | 前端 CSS 补充 `.type-int/.type-float/.type-string/.type-object/.type-model` 颜色 | `webui/src/components/rule-engine/RuleNode.vue` | ✅ 已完成 |
| 1.5 | Handle 模板添加动态类型 class | `webui/src/components/rule-engine/RuleNode.vue` | ✅ 已完成 |
| 1.6 | 已连接端口颜色不覆盖类型颜色 | `webui/src/components/rule-engine/RuleNode.vue` | ✅ 已完成 |

## Phase 2: P0 问题修复

| # | 任务 | 文件 | 状态 |
|---|------|------|------|
| 2.1 | 节点分类展开状态持久化（computed → reactive） | `webui/src/views/RuleCanvas.vue` | ✅ 已完成 |
| 2.2 | 框选功能修复（SelectionMode.Partial + handleSelectionChange） | `webui/src/views/RuleCanvas.vue` | ✅ 已完成 |
| 2.3 | 右键菜单冒泡修复 | `webui/src/components/rule-engine/RuleNode.vue` | ✅ 已完成 |
| 2.4 | 节点圆角溢出修复 | `webui/src/components/rule-engine/RuleNode.vue` | ✅ 已完成 |
| 2.5 | Handle 位置修正 | `webui/src/components/rule-engine/RuleNode.vue` | ✅ 已完成 |

## Phase 3: P1 改进

| # | 任务 | 文件 | 状态 |
|---|------|------|------|
| 3.1 | 连接功能修正（`getNodePortType` 数组 vs 对象 bug） | `webui/src/views/RuleCanvas.vue` | ✅ 已完成 |
| 3.2 | 工具栏重新规划 | `webui/src/views/RuleCanvas.vue` | ✅ 已完成 |
| 3.3 | 折叠按钮位置移动 | `webui/src/views/RuleCanvas.vue` | ✅ 已完成 |

## Phase 4: P2 体验优化

| # | 任务 | 文件 | 状态 |
|---|------|------|------|
| 4.1 | 控制台拖拽调整高度 | `webui/src/views/RuleCanvas.vue` | ✅ 已完成 |
| 4.2 | 侧栏收纳宽度适配 | `webui/src/views/RuleCanvas.vue` | ✅ 已完成 |

## Phase 5: 新增修复

| # | 任务 | 文件 | 状态 |
|---|------|------|------|
| 5.1 | 快捷添加栏（画布有节点后仍可快速添加） | `webui/src/views/RuleCanvas.vue` | ✅ 已完成 |
| 5.2 | 数据库路径修复（`data/database/engine.db`） | `backend/database.py` | ✅ 已完成 |

## Phase 6: UI 交互修复 (2026-05-09)

| # | 任务 | 文件 | 状态 | 说明 |
|---|------|------|------|------|
| 6.1 | 连接验证 `is-valid-connection` | `RuleCanvas.vue` | ✅ 已完成 | 添加 VueFlow 连接验证回调，解决连接线不易触发高亮问题 |
| 6.2 | 连接半径增加 | `RuleCanvas.vue` | ✅ 已完成 | `connection-radius=20` 提高连接灵敏度 |
| 6.3 | 折叠按钮样式修复 | `RuleCanvas.vue` | ✅ 已完成 | 参照 App.vue sidebar 样式，按钮位于面板右边缘 |
| 6.4 | 节点面板右键菜单 | `RuleCanvas.vue` | ✅ 已完成 | 添加 `@contextmenu` 处理 + 样式美化（固定宽度180px） |
| 6.5 | 框选状态同步 | `RuleCanvas.vue` | ✅ 已完成 | `handleSelectionChange` 正确同步选中状态到 nodes |
| 6.6 | 删除按钮点击修复 | `RuleNode.vue` | ✅ 已完成 | 改用 `props.onDelete` 直接调用 VueFlow `removeNodes` |
| 6.7 | overflow 溢出修复 | `RuleNode.vue` | ✅ 已完成 | 节点容器 `overflow: visible`，不裁剪连接点和删除按钮 |
| 6.8 | 边类型改为贝塞尔曲线 | `RuleCanvas.vue` | ✅ 已完成 | `smoothstep` → `default`，实线曲线连接 |
| 6.9 | 浮动工具栏移除 | `RuleCanvas.vue` | ✅ 已完成 | 有节点时不再显示快捷添加工具栏 |
| 6.10 | 端口间距增大 | `RuleNode.vue` | ✅ 已完成 | Handle 增大到 14px，端口间距增加 |
| 6.11 | 连接点边框定位 | `RuleNode.vue` | ✅ 进行中 | Handle 定位微调，输入类型节点右侧端口位置待优化 |

## Phase 7: 待优化项

| # | 任务 | 说明 |
|---|------|------|
| 7.1 | 输入类型节点输出端口位置 | 输入类型节点（如 ImageCapture、VideoCapture）的输出端口应该在右侧边框上居中，目前位置偏内 |

---

## 已完成

| 日期 | 内容 | 提交 |
|------|------|------|
| 2026-05-07 | 端口连接设计规范文档 | `ca46fea` |
| 2026-05-07 | UI 整改方案文档 | `ca46fea` |
| 2026-05-07 | RuleNode + RuleCanvas 代码提交（Handle/删除按钮/框选/右键菜单等） | `339496f` |
| 2026-05-08 | Phase 1 端口类型规范（14种类型+兼容性矩阵） | `944c9a8` |
| 2026-05-08 | Phase 2.1/2.3/2.4/2.5（分类展开/右键菜单/圆角/Handle位置） | `944c9a8` |
| 2026-05-08 | Phase 2.4/2.5/3.2/3.3/4.1/4.2（圆角溢出/控制台拖拽/侧栏宽度） | `9dcb6ec` |
| 2026-05-08 | Phase 2.2 框选功能（SelectionMode.Partial） | `8c3ff3b` |
| 2026-05-08 | Phase 5 快捷添加栏 + 数据库路径修复 | `23df2e2` |
| 2026-05-09 | Phase 6 UI交互修复（连接验证/折叠按钮/右键菜单/删除/overflow/贝塞尔曲线） | `待提交` |
