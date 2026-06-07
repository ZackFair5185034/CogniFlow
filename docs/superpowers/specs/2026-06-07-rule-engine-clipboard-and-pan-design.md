# 规则引擎画布 — 剪贴板 + 性能估量

**日期**: 2026-06-07
**范围**: webui/src/views/RuleCanvas.vue + webui/src/components/rule-engine/RuleNode.vue

## 背景

用户报告 4 个问题:
1. 复制/粘贴位置不跟手 (固定 +50/+50)
2. 复制粘贴不包含连接点链接线
3. 多选后右键删除只删 1 个
4. 全选后拖拽画布明显卡顿

## 决策记录

| 决策点 | 选择 | 理由 |
|--------|------|------|
| 坐标偏移模式 | Figma 模式 (鼠标位置差) | 用户期望复制源点 + 当前鼠标位置 = 新节点位置, 视觉直观 |
| 复制粘贴边 | 包含, 重映射 source/target ID | 保持多节点关系, 不破坏选中集 |
| 右键删除多选 | 全部删除 | 与键盘 Delete 行为一致 |
| 全选拖拽卡顿 | 本次估量, 不修 | 风险评估后, 留到下迭代 |

## 改动

### 改动 1: 复制/粘贴坐标 = 鼠标位置差 (Figma 模式)

**当前行为** (handlePaste):
```ts
const offsetX = 50  // 固定
const offsetY = 50
```

**新行为**:
- 复制时记录 `clipboardMousePos: { x, y }` (浏览器屏幕坐标)
- 粘贴时计算: 偏移 = (当前鼠标屏幕坐标 - 复制时鼠标屏幕坐标) / 画布缩放
- 用 `useVueFlow().viewport.zoom` 转换

### 改动 2: 复制粘贴包含边 (重映射 ID)

**当前**: clipboard = Node[]

**新**: clipboard = `{ nodes: Node[], edges: Edge[], mousePos: {x,y} }`

粘贴时:
- 旧 ID → 新 ID 映射表
- 新节点列表 (同改动 1, 加偏移)
- 边过滤: 至少一端在复制集中 → 重映射 ID → 加到 store.edges

### 改动 3: 右键删除多选全部

**当前** (case 'delete'):
```ts
const targetId = contextMenu.target.id
store.removeNode(targetId)  // 只删 1 个
```

**新**:
```ts
case 'delete':
  handleDelete()  // 已支持 selected 多选删除
  hideContextMenu()
  break
```

### 改动 4: 估量全选拖拽卡顿 (不修)

**根因猜测**:
- 全选 N 节点后拖拽, `handleSelectionDragStop` 在拖动中持续 mutate store.nodes 字段 + triggerRef
- mousemove 每次重渲染整张图
- VueFlow 节点组件无 v-memo 包裹, 全部 30+ 节点 watcher 重算

**下迭代候选修复**:
- mousemove 用 `requestAnimationFrame` 节流
- 拖拽期间设 `isDragging` 标志, 跳过不必要的响应式
- 节点用 `v-memo="[data.id, data.category, data.status, selected]"` 减少重渲

## 改动文件

| 文件 | 改动 |
|------|------|
| `webui/src/views/RuleCanvas.vue` | clipboard 数据结构 + handleCopy/Cut/Paste 改造 + case 'delete' 委托 + (估量) 拖拽节流 |
| (无) | RuleNode.vue 无改动 |

## 测试

| 场景 | 期望 |
|------|------|
| 复制节点A → 移动鼠标 → 粘贴 | 新节点 = A + (currentMouse - copyMouse) / zoom |
| 复制节点A → 立刻粘贴 | 新节点 = A (offset≈0) |
| 复制 2 节点 + 2 边 → 粘贴 | 4 节点 + 2 边 (ID 重映射) |
| 复制节点 + 外部节点相连的边 | 外部边 (source 或 target 不在选中集) 也复制, 一端重映射 |
| 多选 3 节点 → 右键 → 删除 | 全部 3 节点 + 相关边删除 |
| 单选节点 → 右键 → 删除 | 1 节点删除 (行为不变) |
| 全选 + 拖拽 | (估量记录, 本次不修) |

## 数据结构

```ts
interface ClipboardPayload {
  nodes: Node<RuleNodeData>[]    // 完整节点 (含 data.config)
  edges: Edge[]                  // 选中节点相关的边
  mousePos: { x: number; y: number }  // 复制时鼠标屏幕坐标
}
```

cut 模式下粘贴后清空 `payload` (现有行为保留).

## 风险

- 边 ID 重命名不能冲突 (新 id 用 `edge_${Date.now()}_${rand}`)
- 复制剪贴板存在 store ref 里 (非全局), 切页面会清 — 当前如此, 保留
- 边可能被同 source/target 重复: 需 dedup 或保持简单 (允许悬空边, 警告即可)

---

## 估量报告: 全选后拖拽画布卡顿

**现象**: 全选 30+ 节点后 alt+左键平移画布, 鼠标移动明显卡顿.

**根因猜测** (3 个可能叠加):
1. `handleSelectionDragStop` (RuleCanvas.vue:1128-) 在拖拽中持续 mutate `store.nodes` 的 `selected` 字段, 配合 `shallowRef` 触发了大面积响应式更新.
2. `handleCanvasMouseMove` 每次 mousemove 直接调 `setViewport()`, 无 rAF 节流, 60Hz 触发 VueFlow 全图重渲染.
3. VueFlow 节点组件未包裹 `v-memo`, 整图所有 30+ 节点 watcher 都重算.

**非本次修复原因**:
- 涉及 VueFlow 内部 + 全局渲染优化, 改动面大, 风险高
- 性能基准不易立 (需复现具体卡顿场景)
- 留待下迭代配合虚拟化一并处理

**建议下迭代修复**:
- mousemove 用 `requestAnimationFrame` 节流
- 拖拽期间设 `isDragging` 标志, 跳过 `saveHistory` 等非关键响应式
- 节点用 `v-memo="[data.id, data.category, data.status, selected]"`
- 评估引入节点虚拟化 (vue-flow 1.48+)
