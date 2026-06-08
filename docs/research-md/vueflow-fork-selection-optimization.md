# VueFlow Fork — 框选性能优化（process-skip 方案）

**日期**: 2026-06-08
**作用域**: `packages/core/src/container/Pane/Pane.vue`（仅 1 个文件）
**仓库**: `/home/wanglei/vue-flow`（forked from `bcakmakoglu/vue-flow` v1.48.2）

---

## 1. 问题描述

用户报告：规则引擎画布框选过程中，**鼠标移动时每帧都触发 O(N) 包围盒检测 + 选中状态变化 emit**。期望"只希望最终结束时才计算"。

50 节点画布拖框时，从框选开始到结束的 ~500ms 内会触发约 30 帧（60Hz），每帧都跑全节点命中检测 + 选中状态差异计算 + emit `nodes-change` 事件。

## 2. 根因分析

VueFlow 1.48.2 Pane.vue `onPointerMove` 的框选逻辑（line 145-203）：

```ts
function onPointerMove(event) {
  // ... 计算 nextUserSelectRect

  const prevSelectedNodeIds = selectedNodeIds.value

  // ❌ 每帧 O(N) 包围盒检测
  selectedNodeIds.value = new Set(
    getNodesInside(nodes.value, nextUserSelectRect, viewport.value, selectionMode.value === SelectionMode.Partial, true)
      .map(node => node.id)
  )

  // ... 遍历 connectionLookup 算选中边

  // ❌ 选中集合变了才 emit，但只要节点进出包围盒就触发
  if (!areSetsEqual(prevSelectedNodeIds, selectedNodeIds.value)) {
    const changes = getSelectionChanges(nodeLookup.value, selectedNodeIds.value, true) as NodeChange[]
    emits.nodesChange(changes)  // 触发前端 @nodes-change
  }
  // ... 边同上

  userSelectionRect.value = nextUserSelectRect  // 视觉
}
```

**关键观察**：
- `getNodesInside` 遍历所有节点，O(N) 包围盒检测
- `getSelectionChanges` 再次 O(N) 对比前后选中集合，emit `select` 类型 change
- 用户的"框选过程中节点高亮跟随"是产品需求，但 **节点进出选区是 mousemove 期间的"中间态"**，不是最终态
- 前端 `isBatchDragging` 拦截了 `@nodes-change` 写入 store，但 **VueFlow 内部 O(N) 计算开销无法避免**

**调用栈**：

```
pointermove (60Hz × 框选持续时间)
  → onPointerMove
    → getNodesInside()                  // O(N) 包围盒检测
    → selectedNodeIds.value = new Set   // 写入 VueFlow 内部 ref
    → connectionLookup 遍历              // O(E) 边相关
    → getSelectionChanges                // O(N) 再次 diff
    → emits.nodesChange(changes)         // 触发前端 @nodes-change
  → UserSelection 组件渲染                // 视觉
```

## 3. 解决方案

**process-skip**: 在 `onPointerMove` 期间**完全跳过 O(N) 命中检测**，只更新选区矩形（视觉）；所有命中计算搬到 `onPointerUp` 一次性执行。

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

-  // ❌ 每帧 O(N) 包围盒检测
-  const prevSelectedNodeIds = selectedNodeIds.value
-  const prevSelectedEdgeIds = selectedEdgeIds.value
-
-  selectedNodeIds.value = new Set(
-    getNodesInside(nodes.value, nextUserSelectRect, viewport.value, selectionMode.value === SelectionMode.Partial, true).map(
-      (node) => node.id,
-    ),
-  )
-
-  // ... 边连接遍历 + getSelectionChanges + emit (省略 ~30 行)

+  // === CogniFlow 性能优化 (Phase B-2): 框选拖拽过程跳过 O(N) 包围盒检测 ===
+  // 原始实现：每帧 60Hz 调 getNodesInside() 跑全节点命中检测 + getSelectionChanges()
+  //           + emit nodes-change，前端无论是否拦截都要承担 VueFlow 内部开销。
+  // 新实现：pointermove 期间只更新选区矩形 (供 UserSelection 视觉反馈)，
+  //         命中检测 / emit 全部推迟到 onPointerUp 一次性执行。
   userSelectionRect.value = nextUserSelectRect
   userSelectionActive.value = true
   nodesSelectionActive.value = false
 }

+/**
+ * computeSelectionFromRect - 一次性计算选区命中节点/边并 emit 变化
+ * 从原 onPointerMove 提取出来，供 onPointerUp 复用。P0-B2 优化。
+ */
+function computeSelectionFromRect(rect: typeof userSelectionRect.value) {
+  if (!rect) return
+
+  const prevSelectedNodeIds = selectedNodeIds.value
+  const prevSelectedEdgeIds = selectedEdgeIds.value
+
+  selectedNodeIds.value = new Set(
+    getNodesInside(nodes.value, rect, viewport.value, selectionMode.value === SelectionMode.Partial, true).map(
+      (node) => node.id,
+    ),
+  )
+
+  selectedEdgeIds.value = new Set()
+  const edgesSelectable = defaultEdgeOptions.value?.selectable ?? true
+
+  for (const nodeId of selectedNodeIds.value) {
+    const connections = connectionLookup.value.get(nodeId)
+    if (!connections) continue
+    for (const { edgeId } of connections.values()) {
+      const edge = edgeLookup.value.get(edgeId)
+      if (edge && (edge.selectable ?? edgesSelectable)) {
+        selectedEdgeIds.value.add(edgeId)
+      }
+    }
+  }
+
+  if (!areSetsEqual(prevSelectedNodeIds, selectedNodeIds.value)) {
+    const changes = getSelectionChanges(nodeLookup.value, selectedNodeIds.value, true) as NodeChange[]
+    emits.nodesChange(changes)
+  }
+
+  if (!areSetsEqual(prevSelectedEdgeIds, selectedEdgeIds.value)) {
+    const changes = getSelectionChanges(edgeLookup.value, selectedEdgeIds.value) as EdgeChange[]
+    emits.edgesChange(changes)
+  }
+}

 function onPointerUp(event: PointerEvent) {
   if (event.button !== 0 || !selectionStarted) {
     return
   }

   ;(event.target as Element)?.releasePointerCapture(event.pointerId)

   if (!userSelectionActive.value && userSelectionRect.value && event.target === container.value) {
     onClick(event)
   }

+  // === CogniFlow 性能优化 (Phase B-2): 框选结束一次性算命中 + emit ===
+  // 必须在清 userSelectionRect / emits.selectionEnd 之前完成计算。
+  computeSelectionFromRect(userSelectionRect.value)

   userSelectionActive.value = false
   userSelectionRect.value = null
   nodesSelectionActive.value = selectedNodeIds.value.size > 0

   emits.selectionEnd(event)
   // ...
 }
```

## 4. 收益分析

| 指标 | 修复前 | 修复后 |
|------|--------|--------|
| pointermove 期间 O(N) 包围盒检测 | 60Hz × 框选时长 | **0 次** |
| pointermove 期间 emit nodes-change | ~30 次（每次节点进出包围盒） | **0 次** |
| pointerup 时 O(N) 计算 | 1 次（最近一次 move） | 1 次（一次性最终） |
| 总 O(N) 包围盒检测次数 | 60Hz × 持续时间 + 1 | **1**（仅 pointerup） |
| 节点高亮跟随 | ✅ 实时 | ❌ 松手时一次性亮 |

## 5. 视觉代价与产品决策

**视觉代价**：框选过程中节点高亮不跟随（用户拖框时只看到选区矩形，不看到节点进出高亮）。松手瞬间所有命中节点同时高亮。

**为什么可接受**：
- 用户已明确反馈"**只希望最终结束时才计算**"——这是产品级决策，性能优先于过程视觉
- ComfyUI 风格编辑器常见做法：框选过程不显示命中高亮，松手时全选/高亮
- 50+ 节点画布上"实时高亮跟随"在 60Hz 下肉眼其实看不太清，过程视觉收益不抵性能损失

## 6. 兼容性影响

| 路径 | 兼容性 |
|------|--------|
| 前端 `handleSelectionEnd` 监听 `@selection-end` 事件 | ✅ 时机不变（`emits.selectionEnd(event)` 仍在 computeSelectionFromRect 之后调用） |
| 前端 `isBatchDragging` 拦截 | ✅ 仍然有效（VueFlow 内部 emit 仍发生在 selectionEnd 之前，命中拦截） |
| 单击选中（无 pointermove） | ✅ 走 `onClick` 路径，不受影响 |
| Ctrl+点击切换 | ✅ 走 `nodeClick` 事件，与框选逻辑独立 |
| `selectionMode` = `Full` | ✅ 兼容（`getNodesInside` 内部使用同一个 selectionMode 参数） |
| 多画布（多个 VueFlow 实例） | ✅ 兼容（修改限于单实例内部） |
| VueFlow 1.48.x 公共 API | ✅ 公共 API 未变（仅内部实现优化） |

## 7. 验证

- **vue-tsc --noEmit**: 0 错误
- **后端 pytest**: 242 passed / 1 pre-existing 失败（CLAUDE.md 记录）
- **pnpm build**: 8.08s 成功（无回归）

## 8. 后续优化方向

1. **空间索引**：50+ 节点画布仍需 O(N) 命中检测，引入四叉树 / R-tree 可降至 O(log N + k)
2. **过程视觉保留**（如未来产品需要）：pointermove 用 rAF 节流，rAF 内只算可见区域节点
3. **批量重测**：补前端 vitest 测试覆盖 `computeSelectionFromRect` 边界（多画布、空图、零节点、单节点）
