# 规则引擎画布视觉精细化 — 设计文档

**日期**：2026-06-06
**目标**：规则引擎画布 4 项 UI 精细化调整

## 决策记录

### 决策 1：节点类型面板"完全收纳"
- **方案 B**：折叠时面板 `display: none`，按钮放进顶部工具栏最右
- **icon**：Panel-Left（矩形 + 左侧分隔条，与项目 Lucide 风格一致）
- **按钮尺寸**：32×32（比普通 28px 略大）

### 决策 2：连接线选中/未选中亮度梯度（微妙对比）
- 未选中：`stroke-opacity: 0.35`
- 悬停：`stroke-opacity: 0.7`
- 选中：`stroke: #00f0ff`、`stroke-width: 3`、`filter: drop-shadow(0 0 4px #00f0ff)`

### 决策 3：Port type 14 色细粒度（沿用现状）
- 14 种 type 颜色表（image/bbox/mask/scores/trigger/control/int/float/boolean/string/array/object/model/any）保持 RuleNode.vue 1160-1173 已有配色
- 连接线 + 两端 Handle 同色
- Handle `connected` 状态：中心 `background: 当前 type 色` 填充（已连时填色）
- Handle `unconnected` 状态：仅边框类型色，背景保持深色

### 决策 4：节点选中边框按 category 色
- 6 个 category 色：input 绿 / detection 青 / processing 黄 / action 橙 / logic 品红 / output 红
- 选中态：`border: 2px solid 当前 category 色`（无外发光、无双层）

## 文件改动

| 文件 | 改动 |
|------|------|
| `webui/src/views/RuleCanvas.vue` | 删除 `.node-palette` 折叠时的 48px 轨道，改为 `display: none`；新增工具栏最右 `.palette-toggle-btn`（panel-left icon，32×32）；更新全局 `.vue-flow__edge-path` 三态样式 |
| `webui/src/components/rule-engine/RuleNode.vue` | 用 SCSS 嵌套把 `.rule-node.selected` 边框色按 `.category-${data.category}` 覆盖 6 色；扩展 `.vue-flow-handle-connected` 背景填充为 type 色 |
| `webui/src/style/_variables.scss` | 提取 14 type 颜色 + 6 category 颜色到 `:root` CSS 变量（可选 — 此次实现直接内联） |

## 验收标准

- [ ] 折叠面板后画布 100% 占用宽度，工具栏最右出现 panel-left icon
- [ ] 点击 panel-left 按钮恢复面板（280px），icon 状态切换
- [ ] 未选中边视觉上明显比选中边"淡"
- [ ] 选中边为青色 + 发光
- [ ] 拖动连接两个节点，Handle 中心自动填类型色
- [ ] 选中 input 节点边框为绿色；检测节点边框为青色；以此类推 6 色
- [ ] `pnpm build:type` + `pnpm lint` + `pnpm test` 全通过
- [ ] Playwright e2e：折叠/展开面板、选中不同类型节点检查边框色、连接节点后 handle 填色

## 风险

- 边 hover 效果（`vue-flow__edge:hover`）当前是 0.15 透明度 + 2.5 宽 — 与 35%/70% 梯度并存
- 节点选中态叠加执行态（`data-status='running'`）的边框色，优先级需明确
- `vue-flow-handle-connected` class 由 VueFlow 内部维护，需要确认是否在 handle type 改变时同步更新
