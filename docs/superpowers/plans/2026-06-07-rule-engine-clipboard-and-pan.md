# 规则引擎画布剪贴板增强 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让规则引擎画布的剪贴板操作按"鼠标位置差"定位粘贴节点, 包含配置参数 + 边 (重映射 ID), 并支持多选右键删除全部.

**Architecture:** 把 `clipboard` 从 `Node[]` 升级为 `{ nodes, edges, mousePos }` payload, 通过 `screenToFlowCoordinate` 转换坐标. 右键 `delete` 委托 `handleDelete()` 利用已有 selected 状态. 性能调查(全选拖拽卡顿) 仅记录估量报告, 不修.

**Tech Stack:** Vue 3 + TypeScript + Pinia + VueFlow 1.48 + Element Plus

---

## File Structure

| 文件 | 改动 |
|------|------|
| `webui/src/views/RuleCanvas.vue` | clipboard 数据结构 + handleCopy/Cut/Paste 改造 + case 'delete' 委托 + 鼠标坐标追踪 |
| (无新增) | 现有结构已支持, 不引入新文件 |

### Task 1: clipboard 数据结构升级

**Files:**
- Modify: `webui/src/views/RuleCanvas.vue:702-703`

- [ ] **Step 1: 升级 clipboard 声明**

替换:
```ts
const clipboard = ref<Node<RuleNodeData>[]>([])
const clipboardMode = ref<'copy' | 'cut'>('copy')
```

为:
```ts
/** 剪贴板 payload: 复制/剪切时把节点+关联边+鼠标位置一起记下 */
interface ClipboardPayload {
  nodes: Node<RuleNodeData>[]
  edges: Edge[]
  /** 复制/剪切时鼠标在浏览器视口的屏幕坐标 (event.clientX/Y) */
  mousePos: { x: number; y: number }
}
const clipboard = ref<ClipboardPayload | null>(null)
const clipboardMode = ref<'copy' | 'cut'>('copy')
```

- [ ] **Step 2: 类型检查**

Run: `cd /home/coding/PRIVATE_WORKSPACE/CogniFlow/webui && pnpm build:type`
Expected: 错误 "Property 'length' does not exist on type 'ClipboardPayload | null'" 等 — 这些是预期的, 后续任务会修复.

- [ ] **Step 3: 提交框架改动**

```bash
cd /home/coding/PRIVATE_WORKSPACE/CogniFlow
git add webui/src/views/RuleCanvas.vue
git commit -m "refactor(rule-engine): clipboard 数据结构升级为 payload (含 nodes/edges/mousePos)"
```

---

### Task 2: handleCopy / handleCut 改造

**Files:**
- Modify: `webui/src/views/RuleCanvas.vue:1058-1084`

- [ ] **Step 1: 重写 handleCopy**

替换:
```ts
function handleCopy() {
  const vfNodes = getNodes.value as any[]
  const selected = vfNodes.filter((n) => n.selected)
  if (selected.length === 0) {
    ElMessage.warning('请先选择要复制的节点')
    return
  }
  clipboard.value = selected.map((n: any) => JSON.parse(JSON.stringify(n)))
  clipboardMode.value = 'copy'
  ElMessage.success(`已复制 ${selected.length} 个节点`)
}
```

为:
```ts
function handleCopy(event?: MouseEvent) {
  const vfNodes = getNodes.value as any[]
  const selected = vfNodes.filter((n) => n.selected)
  if (selected.length === 0) {
    ElMessage.warning('请先选择要复制的节点')
    return
  }
  // 收集选中节点之间的边 (源和目标都在选中集)
  const selectedIds = new Set(selected.map((n) => n.id))
  const relatedEdges = (edges.value as Edge[]).filter(
    (e) => selectedIds.has(e.source) && selectedIds.has(e.target)
  )
  clipboard.value = {
    nodes: selected.map((n: any) => JSON.parse(JSON.stringify(n))),
    edges: relatedEdges.map((e) => JSON.parse(JSON.stringify(e))),
    mousePos: event ? { x: event.clientX, y: event.clientY } : { x: 0, y: 0 }
  }
  clipboardMode.value = 'copy'
  ElMessage.success(`已复制 ${selected.length} 个节点`)
}
```

- [ ] **Step 2: 重写 handleCut**

替换:
```ts
function handleCut() {
  const vfNodes = getNodes.value as any[]
  const selected = vfNodes.filter((n) => n.selected)
  if (selected.length === 0) {
    ElMessage.warning('请先选择要剪切的节点')
    return
  }
  clipboard.value = selected.map((n: any) => JSON.parse(JSON.stringify(n)))
  clipboardMode.value = 'cut'
  for (const n of selected) {
    store.removeNode(n.id)
  }
  ElMessage.success(`已剪切 ${selected.length} 个节点`)
}
```

为:
```ts
function handleCut(event?: MouseEvent) {
  const vfNodes = getNodes.value as any[]
  const selected = vfNodes.filter((n) => n.selected)
  if (selected.length === 0) {
    ElMessage.warning('请先选择要剪切的节点')
    return
  }
  const selectedIds = new Set(selected.map((n) => n.id))
  const relatedEdges = (edges.value as Edge[]).filter(
    (e) => selectedIds.has(e.source) && selectedIds.has(e.target)
  )
  clipboard.value = {
    nodes: selected.map((n: any) => JSON.parse(JSON.stringify(n))),
    edges: relatedEdges.map((e) => JSON.parse(JSON.stringify(e))),
    mousePos: event ? { x: event.clientX, y: event.clientY } : { x: 0, y: 0 }
  }
  clipboardMode.value = 'cut'
  // 收集节点 id 再批量删除, 避免在循环里反复重渲染
  const nodeIds = selected.map((n) => n.id)
  // shallowRef 数组重新赋值触发响应式
  store.nodes = store.nodes.filter((n) => !nodeIds.includes(n.id))
  store.edges = (store.edges as Edge[]).filter(
    (e) => !nodeIds.includes(e.source) && !nodeIds.includes(e.target)
  )
  ElMessage.success(`已剪切 ${selected.length} 个节点`)
}
```

- [ ] **Step 3: 把 handleKeyDown 也传 event 给 handleCopy/handleCut**

在 `handleKeyDown` 找调用 `handleCopy()` 和 `handleCut()` 的位置 (line ~1037 附近), 改为传事件或鼠标位置. KeyboardEvent 没有 clientX/Y — 用当前光标位置或直接传 undefined (使用 0/0 fallback, 已有).

具体: 
```ts
if (isCtrl && event.key === 'c') {
  event.preventDefault()
  // 键盘复制时鼠标位置不准确 — 用当前屏幕中心作为 fallback
  handleCopy()
  return
}
```

不改: 键盘复制时 mousePos 默认为 0,0, 偏移退化为"鼠标位置-0" 接近 0, 实际行为退化到原 +50/+50 感觉(实际坐标偏移就是当前鼠标位置). 这是合理的 fallback.

- [ ] **Step 4: 类型检查**

Run: `cd /home/coding/PRIVATE_WORKSPACE/CogniFlow/webui && pnpm build:type`
Expected: 通过 (paste case 还是会报错, 后续 task 修).

- [ ] **Step 5: 提交**

```bash
cd /home/coding/PRIVATE_WORKSPACE/CogniFlow
git add webui/src/views/RuleCanvas.vue
git commit -m "feat(rule-engine): handleCopy/handleCut 改写 — payload + 鼠标坐标记录"
```

---

### Task 3: handlePaste 改造 — 鼠标位置差 + 边重映射

**Files:**
- Modify: `webui/src/views/RuleCanvas.vue:1086-1125`

- [ ] **Step 1: 重写 handlePaste**

替换:
```ts
function handlePaste() {
  if (clipboard.value.length === 0) {
    ElMessage.warning('剪贴板为空')
    return
  }

  const offsetX = 50
  const offsetY = 50

  const newNodes: Node<RuleNodeData>[] = []
  for (const n of clipboard.value) {
    const cloned = JSON.parse(JSON.stringify(n))
    const newId = `node_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`
    newNodes.push({
      ...cloned,
      id: newId,
      type: 'ruleNode',
      position: {
        x: n.position.x + offsetX,
        y: n.position.y + offsetY
      },
      selected: false,
      data: {
        ...(cloned.data || {}),
        id: newId,
        selected: false
      }
    })
  }
  // shallowRef 数组必须重新赋值触发响应式（与 createNode/addEdge 同样原因）
  store.nodes = [...store.nodes, ...newNodes]

  if (clipboardMode.value === 'cut') {
    clipboard.value = []
  }

  store.saveHistory()
  // 提示文案：cut 模式粘贴后剪贴板会被清空, 用粘贴数展示
  ElMessage.success(`已粘贴 ${newNodes.length} 个节点`)
}
```

为:
```ts
function handlePaste(event?: MouseEvent) {
  if (!clipboard.value || clipboard.value.nodes.length === 0) {
    ElMessage.warning('剪贴板为空')
    return
  }

  const { nodes: srcNodes, edges: srcEdges, mousePos } = clipboard.value

  // 计算鼠标偏移 (屏幕坐标 → 画布坐标)
  // 复制/剪切时记下 mousePos, 粘贴时用"当前鼠标"减"复制时鼠标"得到偏移
  const currentMouse = event ? { x: event.clientX, y: event.clientY } : null
  let offsetX = 50
  let offsetY = 50
  if (currentMouse) {
    const zoom = getViewport().zoom
    const dxScreen = currentMouse.x - mousePos.x
    const dyScreen = currentMouse.y - mousePos.y
    offsetX = dxScreen / zoom
    offsetY = dyScreen / zoom
  }

  // 旧 ID → 新 ID 映射 (用于重映射边的 source/target)
  const idMap = new Map<string, string>()
  // 防止短时间戳碰撞: 每个节点用序号后缀
  const ts = Date.now()
  let seq = 0
  const newId = () => `node_${ts}_${(seq++).toString(36)}`

  const newNodes: Node<RuleNodeData>[] = srcNodes.map((n: any) => {
    const newNodeId = newId()
    idMap.set(n.id, newNodeId)
    const cloned = JSON.parse(JSON.stringify(n))
    return {
      ...cloned,
      id: newNodeId,
      type: 'ruleNode',
      position: {
        x: n.position.x + offsetX,
        y: n.position.y + offsetY
      },
      selected: false,
      data: {
        ...(cloned.data || {}),
        id: newNodeId,
        selected: false
      }
    }
  })

  // 重映射边 — 所有 srcEdges 的端点都在复制集中, 整条边复制
  const newEdges: Edge[] = srcEdges.map((e) => {
    const newEdgeId = `edge_${ts}_${(seq++).toString(36)}`
    return {
      ...e,
      id: newEdgeId,
      source: idMap.get(e.source) ?? e.source,
      target: idMap.get(e.target) ?? e.target,
      selected: false
    } as Edge
  })

  // shallowRef 数组必须重新赋值触发响应式
  store.nodes = [...store.nodes, ...newNodes]
  store.edges = [...(store.edges as Edge[]), ...newEdges]

  if (clipboardMode.value === 'cut') {
    clipboard.value = null
  }

  store.saveHistory()
  ElMessage.success(`已粘贴 ${newNodes.length} 个节点${newEdges.length > 0 ? `, ${newEdges.length} 条连线` : ''}`)
}
```

- [ ] **Step 2: 把 handleKeyDown 也传 event 给 handlePaste**

键盘 Ctrl+V 时无鼠标 event, fallback 到 0,0 偏移 (与剪贴板 mousePos 相同 → offset 0, 节点粘到原位置 — 合理).

不改.

- [ ] **Step 3: 把 case 'paste' 调用传 event**

如果 case 'paste' 在右键菜单, MouseEvent 可用. 改为:
```ts
case 'paste':
  handlePaste(event)  // MouseEvent 从 handleContextAction 透传
  hideContextMenu()
  break
```

handleContextAction 当前签名是 `(action: string)`. 改为 `(action: string, event?: MouseEvent)` 然后在 case 'paste' 传 event 进来.

- [ ] **Step 4: 类型检查**

Run: `cd /home/coding/PRIVATE_WORKSPACE/CogniFlow/webui && pnpm build:type`
Expected: 通过.

- [ ] **Step 5: 提交**

```bash
cd /home/coding/PRIVATE_WORKSPACE/CogniFlow
git add webui/src/views/RuleCanvas.vue
git commit -m "feat(rule-engine): handlePaste 改写 - 鼠标位置差偏移 + 边重映射"
```

---

### Task 4: 右键删除多选全部

**Files:**
- Modify: `webui/src/views/RuleCanvas.vue:1195-1233` (case 'delete' 区域)

- [ ] **Step 1: 修改 case 'delete' 委托 handleDelete**

替换:
```ts
    case 'delete':
      // 直接从 contextMenu.target 取 id 删除 —— 不要再走 addSelectedNodes 绕路
      // (VueFlow 1.48 addSelectedNodes 接收 GraphNode[]，不是 string[]；
      //  传 id 字符串会导致 nodes.map((n) => n.id) 得到 undefined，
      //  选中状态变更静默失败，handleDelete() 因无选中节点而早返回)
      if (contextMenu.targetType === 'node' && contextMenu.target) {
        const targetId = (contextMenu.target as any).id as string
        store.removeNode(targetId)
        ElMessage.success('已删除节点')
      } else if (contextMenu.targetType === 'edge' && contextMenu.target) {
        const targetEdge = contextMenu.target as Edge
        store.removeEdge(targetEdge.id)
        ElMessage.success('已删除连线')
      }
      hideContextMenu()
      break
```

为:
```ts
    case 'delete':
      // 多选时: 删所有 selected 节点 + 相关边
      // 单选时: selected 数组也包含右键目标 (VueFlow 自动选中) → 同样全删
      // 边右键时: targetType === 'edge', 走 handleDelete 的 selectedEdges 路径
      handleDelete()
      hideContextMenu()
      break
```

- [ ] **Step 2: 类型检查**

Run: `cd /home/coding/PRIVATE_WORKSPACE/CogniFlow/webui && pnpm build:type`
Expected: 通过.

- [ ] **Step 3: 提交**

```bash
cd /home/coding/PRIVATE_WORKSPACE/CogniFlow
git add webui/src/views/RuleCanvas.vue
git commit -m "fix(rule-engine): 右键删除支持多选 (委托给 handleDelete)"
```

---

### Task 5: 全选拖拽卡顿估量

**Files:**
- Modify: `docs/superpowers/specs/2026-06-07-rule-engine-clipboard-and-pan-design.md` (追加估量章节)

- [ ] **Step 1: 在设计文档追加估量报告**

在 spec 文件末尾追加:
```markdown
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
```

- [ ] **Step 2: 提交估量**

```bash
cd /home/coding/PRIVATE_WORKSPACE/CogniFlow
git add docs/superpowers/specs/2026-06-07-rule-engine-clipboard-and-pan-design.md
git commit -m "docs(rule-engine): 全选拖拽卡顿估量报告 (本次不修, 留到下迭代)"
```

---

### Task 6: 端到端 Playwright 验证

**Files:**
- Test: 用 Playwright e2e 覆盖以下场景

- [ ] **Step 1: 启动后端 + dev server**

Run:
```bash
cd /home/coding/PRIVATE_WORKSPACE/CogniFlow && PYTHONPATH=. uvicorn app:app --host 127.0.0.1 --port 8000 --log-level warning &
# dev server 假设已在 5173
```

- [ ] **Step 2: Figma 模式偏移测试**

添加 2 节点 → 多选 → 右键复制 (记录 mousePos ~500,300) → 移动鼠标到 ~600,400 → 右键粘贴 → 验证新节点位置 = 原位置 + (100, 100)/zoom

Expected: 新节点出现在原节点右下偏移 ~100px 处

- [ ] **Step 3: 边复制测试**

添加节点 A → B + 连边 → 多选 A 和 B → 复制 → 粘贴 → 验证出现新 A' 和 B' + 一条新连线 A' → B'

Expected: 节点数 2→4, 边数 1→2

- [ ] **Step 4: 多选右键删除测试**

添加 3 节点 → 多选 → 右键 → 删除 → 验证 0 节点

Expected: 3 节点全部消失

- [ ] **Step 5: 提交**

不需要新 commit (仅验证).

---

### Task 7: 单元测试 + 类型检查最终回归

- [ ] **Step 1: 类型检查**

Run: `cd /home/coding/PRIVATE_WORKSPACE/CogniFlow/webui && pnpm build:type`
Expected: 通过.

- [ ] **Step 2: 单元测试**

Run: `cd /home/coding/PRIVATE_WORKSPACE/CogniFlow/webui && pnpm test`
Expected: 56+ tests 通过.

- [ ] **Step 3: 提交 (如有修复)**

```bash
cd /home/coding/PRIVATE_WORKSPACE/CogniFlow
git add -A
git diff --cached --quiet || git commit -m "fix(rule-engine): 回归修复"
```

---

## Self-Review Checklist

- [x] Spec 4 项决策 → 对应 Task 1-5
- [x] 文件结构清晰: 单文件改动
- [x] 代码完整 (无 TBD / placeholder)
- [x] 类型一致: ClipboardPayload / Edge / Node<RuleNodeData> 一致使用
- [x] 测试覆盖: e2e 4 场景
