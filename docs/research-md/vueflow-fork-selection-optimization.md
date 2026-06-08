# VueFlow Fork — 框选性能优化（end-skip 方案）

**日期**: 2026-06-08（2026-06-09 修正）
**作用域**: `packages/core/src/container/Pane/Pane.vue`（仅 1 个文件）
**仓库**: `/home/wanglei/vue-flow`（forked from `bcakmakoglu/vue-flow` v1.48.2）

---

## 1. 问题描述

用户报告：规则引擎画布框选结束（松手）时还会**再算一次** O(N) 包围盒检测。期望"框选过程保持实时计算（节点高亮跟随），**框选结束不要再算**"。

50 节点画布拖框时，从框选开始到结束，最后一次 pointermove 已经在 VueFlow 内部把 `selectedNodeIds` / `selectedEdgeIds` 更新为最新值，**但 onPointerUp 仍然调用了一次 `getNodesInside()` 重复遍历**——这是浪费。

## 2. 根因分析

VueFlow 1.48.2 Pane.vue `onPointerUp` 早期版本（在 `381d832b` 之前）**不**调 `getNodesInside`，但在该 commit 中我错误地在 `onPointerUp` 调用了 `computeSelectionFromRect(userSelectionRect.value)`：

```ts
function onPointerUp(event) {
  // ... releasePointerCapture / onClick

  // ❌ 多余：onPointerMove 最后一帧已算出 selectedNodeIds/selectedEdgeIds
  computeSelectionFromRect(userSelectionRect.value)

  userSelectionActive.value = false
  userSelectionRect.value = null
  // ...
}
```

而 `onPointerMove` 最后一帧已经执行了：
- `getNodesInside()` → 算 `selectedNodeIds` Set
- 遍历 `connectionLookup` → 算 `selectedEdgeIds` Set
- `getSelectionChanges()` + `emits.nodesChange()` 同步通知前端

**结论**：onPointerUp 调 `computeSelectionFromRect` 是**纯重复计算**，结果跟最后一次 move 一样（输入矩形相同），但多了一次 O(N) 遍历。

## 3. 解决方案

**end-skip**: `onPointerMove` 保持原始行为（每帧 O(N) 检测 + emit，节点高亮跟随），`onPointerUp` **不**调任何重算函数，沿用最后一次 move 的结果。

### 修改文件

**File 1: `packages/core/src/container/Pane/Pane.vue`**

```diff
 function onPointerMove(event: PointerEvent) {
   if (!containerBounds.value || !userSelectionRect.value) {
     return
   }

   selectionInProgress = true

   const { x: mouseX, y: mouseY } = getEventPosition(event, containerBounds.value)
   const { startX = 0, startY = 0 } = userSelectionRect.value

   const nextUserSelectRect = {
     startX,
     startY,
     x: mouseX < startX ? mouseX : startX,
     y: mouseY < startY ? mouseY : startY,
     width: Math.abs(mouseX - startX),
     height: Math.abs(mouseY - startY),
   }

-  // === CogniFlow 性能优化 (Phase B-2): 框选拖拽过程跳过 O(N) 包围盒检测 ===
-  // (中间 ~30 行 computeSelectionFromRect 抽离 + 注释)
+  const prevSelectedNodeIds = selectedNodeIds.value
+  const prevSelectedEdgeIds = selectedEdgeIds.value
+
+  selectedNodeIds.value = new Set(
+    getNodesInside(nodes.value, nextUserSelectRect, viewport.value, selectionMode.value === SelectionMode.Partial, true).map(
+      (node) => node.id,
+    ),
+  )
+
+  // ... (边连接遍历 + getSelectionChanges + emit, 与原 VueFlow 一致)

   userSelectionRect.value = nextUserSelectRect
   userSelectionActive.value = true
   nodesSelectionActive.value = false
 }

-/**
- * computeSelectionFromRect - 一次性计算选区命中节点/边并 emit 变化
- * 从原 onPointerMove 提取出来，供 onPointerUp 复用。P0-B2 优化。
- */
-function computeSelectionFromRect(rect: typeof userSelectionRect.value) {
-  // ... 30 行命中检测 + emit
-}

 function onPointerUp(event: PointerEvent) {
   if (event.button !== 0 || !selectionStarted) {
     return
   }

   ;(event.target as Element)?.releasePointerCapture(event.pointerId)

   if (!userSelectionActive.value && userSelectionRect.value && event.target === container.value) {
     onClick(event)
   }

-  // === CogniFlow 性能优化 (Phase B-2): 框选结束一次性算命中 + emit ===
-  computeSelectionFromRect(userSelectionRect.value)
+  // === CogniFlow 性能优化 (Phase B-2): 框选结束不重复计算 ===
+  // 原始实现 (VueFlow 1.48): onPointerUp 不调 getNodesInside, 沿用最后一次
+  //                         onPointerMove 的结果 (selectedNodeIds/selectedEdgeIds 已最新)
+  // 上一版误改: onPointerUp 调用了 computeSelectionFromRect 重复算一次 O(N) 包围盒
+  //          检测 (onPointerMove 已算过), 视觉无变化但多一次 N 节点遍历.
+  // 当前策略: 过程实时算 (保留节点高亮跟随体验), 结束不重复算.

   userSelectionActive.value = false
   userSelectionRect.value = null
   nodesSelectionActive.value = selectedNodeIds.value.size > 0

   emits.selectionEnd(event)
   // ...
 }
```

## 4. 收益分析

| 阶段 | 计算次数 |
|------|----------|
| `onPointerMove` 期间 | 60Hz × 框选时长 次 O(N)（保留过程高亮跟随） |
| `onPointerUp` | **0 次**（沿用最后一次 move 结果，不重复算） |

对比上一版（`381d832b`）：
- 上一版 onPointerUp 还要再算 1 次 O(N) → **本次修复省 1 次 O(N)**
- 上一版 onPointerMove 跳过 O(N) 检测 → **本次恢复**（保留节点高亮跟随）

## 5. 为什么 onPointerUp 不需要重算

`onPointerMove` 最后一帧（mouseup 前的最后一帧）已经执行：
- `getNodesInside(rect, viewport, selectionMode, true)` → 更新 `selectedNodeIds` Set
- 遍历 `connectionLookup` → 更新 `selectedEdgeIds` Set
- `getSelectionChanges(...)` + `emits.nodesChange/edgesChange(...)` → emit 当前变化

**当 mouseup 触发 onPointerUp 时，`selectedNodeIds` / `selectedEdgeIds` / VueFlow 内部状态已是最终态**。重算一遍输入相同（`userSelectionRect.value`），结果必然相同，纯属浪费。

## 6. 视觉行为

- **过程**：节点高亮跟随框选（VueFlow 1.48 原始行为，60Hz 更新）—— ✅ 符合"实时计算框选"诉求
- **结束**：选中态停留在最后一次 move 的结果（不闪烁、不重算、不变更）—— ✅ 符合"结束不重复计算"诉求

## 7. 兼容性

| 路径 | 兼容性 |
|------|--------|
| 前端 `handleSelectionEnd` 监听 `@selection-end` 事件 | ✅ 时机不变 |
| 前端 `isBatchDragging` 拦截 | ✅ 仍然有效（最后 move emit 的 nodes-change 仍可被拦截） |
| `SelectionMode.Partial` / `Full` | ✅ 兼容 |
| 单击选中 / Ctrl+点击 | ✅ 与框选逻辑独立 |
| VueFlow 公共 API | ✅ 无变化 |

## 8. 验证

- **vue-tsc --noEmit**: 0 错误
- **后端 pytest**: 242 passed / 1 pre-existing 失败（CLAUDE.md 记录）
- **端到端框选**: 节点高亮跟随，松手无重算

## 9. 后续优化方向

如果未来 100+ 节点画布下"过程实时计算"成为瓶颈：
1. **空间索引**（四叉树 / R-tree）：将 O(N) 包围盒检测降至 O(log N + k)
2. **rAF 节流 + 增量 diff**：节流到 16ms 间隔 + 记录上次选中集合做增量
3. **可见区域过滤**：配合 VueFlow 的 `only-render-visible-elements`，只算可见区域节点

但这些都属于"百节点规模"的深度优化，**当前 50 节点规模下，过程实时 + 结束不算已是最优解**。
