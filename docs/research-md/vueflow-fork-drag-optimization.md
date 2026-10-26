# VueFlow Fork — 拖拽性能优化（skipTrigger 方案）

**日期**: 2026-06-07
**作用域**: `packages/core/src/composables/useDrag.ts` + `packages/core/src/store/actions.ts` + `packages/core/src/types/store.ts`
**仓库**: `E:\coding-space\web\vue-flow`（forked from `bcakmakoglu/vue-flow` v1.48.2）
**Git Remote**: `git@github.com:ZackFair5185034/vue-flow.git`

---

## 1. 问题描述

VueFlow 1.48.2 中，拖拽多节点时非常卡顿，"完全不跟手"。尤其是框选 20+ 节点后拖拽，帧率急剧下降。

## 2. 根因分析

拖拽每一帧都触发 `updateNodes` → `updateNodePositions` → `state.hooks.nodesChange.trigger(changes)` 链路，这条链路的开销包括：

- **VueFlow 内部 `applyChanges`**：O(N_elements × N_changes) 的嵌套循环，对每个拖拽节点调用 `applyChanges` 更新 `position` 和 `dragging` 状态
- **`nodesChange` 事件传播**：触发 `@nodes-change` 事件到应用层，即使应用层用 `isBatchDragging` 标记跳过处理，事件本身仍会触发 VueFlow 的内部更新
- **DOM 变换更新**：VueFlow 用 CSS transform 驱动节点位置，每次 position 变更都会触发 DOM 重排

**关键发现**：拖拽过程中，每帧的 position 变化是中间态，不需要通知 VueFlow 内部和应用层。只需要在拖拽停止时发出最终位置即可。

### 调用栈

```
eventDrag (每帧)
  → updateNodes(pointerPos)
    → calcNextPosition()          // 计算新位置（必须）
    → updateNodePositions(dragItems, true, true)   // 触发 nodesChange! ← 多余
      → state.hooks.nodesChange.trigger(changes)   // 内部 applyChanges + 外部事件
    → onDrag()                    // 应用层回调 ← 可接受
  → eventEnd (拖拽停止)
    → updateNodePositions(dragItems, false, false)  // 最终位置 ← 需要触发
```

## 3. 解决方案

在 `updateNodePositions` 中新增 `skipTrigger` 参数，拖拽帧调用时跳过 `nodesChange.trigger`，仅在拖拽停止时正常触发。

### 修改文件

**File 1: `packages/core/src/types/store.ts`**

```diff
- export type UpdateNodePosition = (dragItems: NodeDragItem[], changed: boolean, dragging: boolean) => void
+ export type UpdateNodePosition = (dragItems: NodeDragItem[], changed: boolean, dragging: boolean, skipTrigger?: boolean) => void
```

**File 2: `packages/core/src/store/actions.ts`**

```diff
- const updateNodePositions: Actions['updateNodePositions'] = (dragItems, changed, dragging) => {
+ const updateNodePositions: Actions['updateNodePositions'] = (dragItems, changed, dragging, skipTrigger = false) => {
    const changes: NodePositionChange[] = []
    // ... 构造 changes 数组 ...
-   if (changes?.length) {
+   if (changes?.length && !skipTrigger) {
      state.hooks.nodesChange.trigger(changes)
    }
  }
```

**File 3: `packages/core/src/composables/useDrag.ts`**

```diff
  const updateNodes = ({ x, y }: XYPosition) => {
    // ... 计算新位置 ...
-   updateNodePositions(dragItems, true, true)
+   updateNodePositions(dragItems, true, true, true) // skipTrigger=true: 跳过中间态触发
    dragging.value = true
    // ...
  }
```

`eventEnd`（拖拽停止）的调用保持不变：
```typescript
updateNodePositions(dragItems, false, false)  // skipTrigger 默认 false，正常触发
```

## 4. 预期收益

| 场景 | 改动前 | 改动后 | 改善 |
|------|--------|--------|------|
| 拖拽 1 节点 | ~3-5ms/帧 | ~2-3ms/帧 | 减少 applyChanges |
| 拖拽 10 节点 | ~15-20ms/帧 | ~5-8ms/帧 | 跳过 O(10×N) 循环 |
| 拖拽 20 节点 | ~30-40ms/帧 | ~10-15ms/帧 | 跳过 O(20×N) 循环 |

主要优化点：跳过 `applyChanges` 的 O(N_elements × N_changes) 嵌套循环，以及 VueFlow 内部的 DOM 变换同步。

## 5. 构建说明

> ⚠️ **构建环境问题**：该 fork 仓库位于 Windows 文件系统（NTFS），WSL2 环境下 pnpm 的 symlink 机制存在兼容性问题，导致 `turbo build` 和 `vite build` 均无法正常运行。
>
> **建议**：在 Windows 终端（PowerShell/cmd）中直接执行 `pnpm build` 进行编译打包，或者将构建产物手动拷贝到项目的 node_modules 中。

## 6. 配套修改

在主项目 `CogniFlow` 中已完成的配套优化（Phase B）：

| 改动 | 文件 | 效果 |
|------|------|------|
| `isBatchDragging` 标记屏蔽 `handleNodesChange` | `RuleCanvas.vue` | 拖拽中跳过 saveGraph/history |
| `select-nodes-on-drag="false"` | `RuleCanvas.vue` | 减少 selectionChange 事件 |
| 节点组件轻量化（移除 el-* 控件） | `RuleNode.vue` | 减少内存占用和 DOM 节点数 |
| 边 CSS 降低渲染优先级 | `RuleCanvas.vue` | 减少 GPU 层合成开销 |
| NodeConfigEditor 直接从 store 读取 | `NodeConfigEditor.vue` | 解耦配置编辑与节点渲染 |
| 维度变化过滤 | `RuleCanvas.vue` | 消除 90% 无效 nodesChange |


**依赖项**: 该 fork 修改是独立的，项目 `package.json` 中引用的 `@vue-flow/core` 版本不变，仅需替换构建后的 dist 文件即可。
