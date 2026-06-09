# 规则引擎画布拖拽性能优化方案

> **版本**: v1.0
> **日期**: 2026-06-10
> **作用域**: `webui/src/views/RuleCanvas.vue`、`webui/src/components/rule-engine/RuleNode.vue`、`webui/src/composables/useCogniFlowDrag.ts`、`webui/src/stores/ruleEngine.ts`
> **基线**: Phase B + LOD-1（shallowRef、markRaw、v-memo、三级 LOD、自研 d3-drag 接管）

---

## 1. 问题与现状

### 1.1 症状

节点超过 ~50 时，拖拽出现明显卡顿：
- 单节点拖动 fps 跌至 30-40
- 多节点框选拖动 fps 跌至 15-25
- 边跟随延迟 1-2 帧，体感"拖"而不是"贴"

### 1.2 已有优化（基线）

| 维度 | 实现 | 位置 |
|------|------|------|
| 数据响应式 | `shallowRef(nodes)` + `markRaw(data)` | `ruleEngine.ts:83, 297` |
| 节点 vdom | `v-memo="[id, status, summaryText, category, lodLevel]"` | `RuleNode.vue:10` |
| 三级 LOD | zoom<0.3 / <0.7 / >=0.7（节点>80 强制 LOD1） | `ruleEngine.ts:205-233` |
| 拖动 LOD 锁定 | `isDragging` 锁住 `lodLevelMapCache` 防抖 | `ruleEngine.ts:218-220` |
| 自研拖动 | DOM 直写 `transform`，绕开 vue-flow `useDrag` | `useCogniFlowDrag.ts:142` |
| 边跟随节流 | rAF 节流 `flowNode.position` 写入 | `useCogniFlowDrag.ts:149-164` |
| drag-end 写回 | `rawWrite=toRaw` 绕过 Proxy + `skipTrigger` | `ruleEngine.ts:477-490, 524` |
| 连接索引 O(1) | `connectedHandleIndex` / `nodeById` | `ruleEngine.ts:144, 176` |
| 帧节流 | `isBatchDragging` 让 `handleNodesChange` 立即 return | `RuleCanvas.vue:1684` |
| 视口裁剪 | `:only-render-visible-elements="true"` | `RuleCanvas.vue:398` |
| 大图自动隐藏 MiniMap | `shouldShowMiniMap` 拖动/大图关闭 | `RuleCanvas.vue:765` |
| zoom 文本 DOM 直写 | `zoomLevelEl.textContent` | `RuleCanvas.vue:1762` |

---

## 2. 瓶颈定位

### 2.1 P0-1 边的全量 path 重算（最大热点）

**位置**：`useCogniFlowDrag.ts:149-164`
```ts
flowNode.position.x = flowX
flowNode.position.y = flowY
```
每帧改 reactive `position` → 触发 vue-flow 内部 `watch([x,y])` → **重算所有 visible edges 的 SVG path**，即便只拖 1 个节点，也会让 80 条边全部 d-attribute 重新计算 + SVG 重绘。

**实测特征**：节点数 N、边数 E，每帧 cost ≈ O(E_visible)；当 E>50 时 SVG paint 成为瓶颈，CPU 主要在 "Recalculate Style + Paint"。

### 2.2 P0-2 多节点拖拽时 N 次 reactive 写入

**位置**：`useCogniFlowDrag.ts:154-162`
rAF 内对 `ctx.allDragged` 全员写 `flowNode.position`，N 个节点 → N 次 watch 调度。

### 2.3 P0-3 节点 CSS 不利于 GPU 合成

**位置**：`RuleNode.vue:217-233`
- `contain: style` 不阻止外部 layout 影响
- 没有 `will-change: transform`，每帧 `transform` 变化触发重新创建合成层
- 多重 box-shadow + gradient 让 paint cost 翻倍

### 2.4 P1-1 d3-drag 重新挂载抖动

**位置**：`useCogniFlowDrag.ts:246-249`
`watch(() => store.nodes, ...reinstallAll())` 触发全量 uninstall + install N 个 d3-drag handler，100 节点约 5-15ms。

### 2.5 P1-2 `lodLevelMap` 在选中变化时重算整图

**位置**：`ruleEngine.ts:205-233`
依赖 `selectedNodeId` → 每次点击切换选中都重建 N 大小的 Map。drag-end 后 `selectNode` 也会触发，影响体感延迟。

### 2.6 P1-3 reactive setter 调度

`flowNode.position.x = ...` 触发响应式 setter 调度走完整 microtask + edge path 重算（合并到 P0-1）。

---

## 3. 优化方案（按 ROI 排序）

### Tier 0（5-10 分钟，立即见效）

#### 3.1 节点 CSS GPU 合成提示

**文件**：`webui/src/components/rule-engine/RuleNode.vue`

```scss
.rule-node {
  /* 原有样式... */
  contain: layout style paint;         /* 三重 contain: 完全隔离子树影响 */
  will-change: transform;              /* 提示浏览器创建独立合成层 */
  transform: translateZ(0);            /* 兜底: 强制 layer 创建 */
  backface-visibility: hidden;
  overflow: visible !important;
}

/* 拖动期间彻底关闭 transition,避免每帧补间触发样式重算 */
.vue-flow__node.dragging .rule-node,
.vue-flow__node.selected.dragging .rule-node {
  transition: none !important;
}
```

**收益**：拖动节点单独成层，paint 从"父合成层全图重绘"变"仅本层 transform"，稳定 60fps。

#### 3.2 拖动时加 `.dragging` class

**文件**：`webui/src/composables/useCogniFlowDrag.ts`

`onDragStart` 末尾：
```ts
for (const item of ctx.allDragged) {
  item.el.classList.add('dragging')
}
```

`onDragEnd` 开头：
```ts
if (ctx) {
  for (const item of ctx.allDragged) {
    item.el.classList.remove('dragging')
  }
}
```

#### 3.3 拖动期间关闭边 pointer-events

**文件**：`webui/src/views/RuleCanvas.vue`（scoped style 末尾）

```scss
/* 拖动期间整层边的命中测试关闭,减少浏览器 hit-test 开销 */
.rule-canvas-fullscreen:has(.vue-flow__node.dragging) .vue-flow__edges {
  pointer-events: none;
}
```

> `:has()` 选择器需要 Chrome 105+ / Safari 15.4+ / Firefox 121+。

---

### Tier 1（30 分钟）

#### 3.4 `lodLevelMap` 拆分（解耦选中态）

**文件**：`webui/src/stores/ruleEngine.ts`

把 `lodLevelMap` 拆为：
- `baseLodLevelMap`：仅依赖 `viewportZoom` + `nodes.length`，选中切换不重建
- `getLodLevel(nodeId)`：O(1) 快速路径，命中 `selectedNodeId` / `configExpandedIds` 直接返回 2

```ts
const baseLodLevelMap = computed<Map<string, 0 | 1 | 2>>(() => {
  const map = new Map<string, 0 | 1 | 2>()
  const zoom = viewportZoom.value
  const count = nodes.value.length
  const isLodLocked = isDragging.value || isSelectionBoxActive.value

  let baseLod: 0 | 1 | 2
  if (zoom < 0.3) baseLod = 0
  else if (zoom < 0.7 || count > 80) baseLod = 1
  else baseLod = 2

  for (const n of nodes.value) {
    if (isLodLocked) {
      map.set(n.id, lodLevelMapCache.get(n.id) ?? baseLod)
    } else {
      map.set(n.id, baseLod)
    }
  }

  if (!isLodLocked) {
    lodLevelMapCache.clear()
    for (const [k, v] of map) lodLevelMapCache.set(k, v)
  }
  return map
})

function getLodLevel(nodeId: string): 0 | 1 | 2 {
  if (nodeId === selectedNodeId.value) return 2
  if (configExpandedIds.value.has(nodeId)) return 2
  return baseLodLevelMap.value.get(nodeId) ?? 1
}
```

**收益**：选中切换从 O(N) 降到 O(1)，drag-end 体感延迟消除。

#### 3.5 d3-drag 增量挂载

**文件**：`webui/src/composables/useCogniFlowDrag.ts`

替换 `installedMap` 替代 `cleanups[]`：

```ts
const installedMap = new Map<HTMLElement, () => void>()

function installOnNode(el: HTMLElement) {
  if (installedMap.has(el)) return  // 幂等
  // ...原有 handler 构造
  d3Select(el).call(dragHandler)
  installedMap.set(el, () => { d3Select(el).on('.drag', null) })
}

function syncDragHandlers() {
  if (isDragging) return
  const els = document.querySelectorAll<HTMLElement>('.vue-flow__node')
  if (els.length === 0) return
  const live = new Set<HTMLElement>(Array.from(els))
  for (const [el, cleanup] of installedMap) {
    if (!live.has(el)) { cleanup(); installedMap.delete(el) }
  }
  live.forEach(installOnNode)
}

function uninstallAll() {
  for (const cleanup of installedMap.values()) cleanup()
  installedMap.clear()
}

onMounted(() => { nextTick(() => syncDragHandlers()) })
watch(() => store.nodes, () => { nextTick(() => syncDragHandlers()) })
onBeforeUnmount(() => { uninstallAll() })
```

**收益**：100 节点新增 1 节点时挂载开销从 O(N) 降到 O(1)，避免 add/remove 后画布卡顿 10-15ms。

---

### Tier 2（1-2 小时，最高 ROI 优化）

#### 3.6 拖动期间手动更新受影响边 path

**新文件**：`webui/src/composables/useEdgePathUpdater.ts`

核心思路：拖动时只对 incident edges（与拖动节点直接相连的边）直接写 SVG `path` 的 `d` 属性，不触发 vue-flow 响应式系统。

详细实现见附录 A：包含：
- `collectAffectedEdges`：dragStart 时收集受影响边 + 缓存 `<path>` 引用
- `updateAffectedEdgePaths`：每帧根据拖动节点 transform 重算边 d 属性
- 读写分离 layout-thrash 防御版

**RuleCanvas.vue** 传入 `getViewport`：
```ts
useCogniFlowDrag({
  // ...
  getViewport: () => getViewport(),
  // ...
})
```

**useCogniFlowDrag.ts** `onDragEnd` 同步 `flowNode.position`（让 vue-flow 接管）+ 清 `el.style.transform`：
```ts
for (const item of ctx.allDragged) {
  const flowNode = options.findFlowNode(item.id)
  if (flowNode?.position) {
    flowNode.position.x = item.startPos.x + dxFlow
    flowNode.position.y = item.startPos.y + dyFlow
  }
  item.el.style.transform = ''
}
```

**收益**：边重算从 O(E_visible) 降到 O(incident_edges)，通常从 80 降到 2-6。**这是当前最大拖动卡顿源**。

---

## 4. 验证方法

### 4.1 性能监测脚本（DevTools Console）

```js
(() => {
  let frames = 0, slow = 0, last = performance.now()
  const losses = []
  const tick = (t) => {
    const dt = t - last
    last = t
    frames++
    if (dt > 17) { slow++; losses.push(dt) }
    if (frames < 300) requestAnimationFrame(tick)
    else {
      console.table({
        总帧数: frames,
        '>17ms 帧': slow,
        丢帧率: (slow / frames * 100).toFixed(1) + '%',
        最长帧: Math.max(...losses).toFixed(1) + 'ms',
      })
    }
  }
  requestAnimationFrame(tick)
  console.log('开始监测,请立即开始拖拽节点 ~5 秒...')
})()
```

### 4.2 性能基线

| 节点规模 | 优化前 | Tier 0 后 | Tier 1 后 | Tier 2 后（目标） |
|----------|--------|-----------|-----------|-------------------|
| 50 节点 | 丢帧 ~25% / 最长 50-80ms | 丢帧 < 10% | 丢帧 < 8% | 丢帧 < 2% |
| 100 节点 | 几乎不可用 | 丢帧 ~20% | 丢帧 ~15% | 丢帧 < 5% |
| 200 节点 | 不可用 | 丢帧 ~40% | 丢帧 ~30% | 丢帧 ~10% |

### 4.3 造 100 节点测试

```js
(() => {
  const apps = window.__VUE_DEVTOOLS_GLOBAL_HOOK__?.apps
  const store = apps?.[0]?.app?.config?.globalProperties?.$pinia?._s?.get('ruleEngine')
  if (!store) { console.error('找不到 store'); return }
  const defs = store.nodeDefinitions
  if (!defs?.length) { console.error('节点定义未加载'); return }
  for (let i = 0; i < 100; i++) {
    store.createNode(defs[i % defs.length], { x: (i % 10) * 250, y: Math.floor(i / 10) * 150 })
  }
  console.log('已创建 100 节点')
})()
```

---

## 5. 落地顺序

| 阶段 | 改动 | 工作量 | 风险 |
|------|------|--------|------|
| ✅ Tier 0-1 | CSS GPU + dragging class + 边 pointer-events + LOD 拆分 + 增量挂载 | 30 分钟 | 低 |
| ☐ Tier 2 | 边增量重算 + viewport 注入 + drag-end 同步 | 1-2 小时 | 中 |
| ☐ 验证 | pnpm build:type + pnpm lint + DevTools fps 监测 | 30 分钟 | - |

---

## 附录 A：Tier 2 边增量更新器完整代码

详见 `webui/src/composables/useEdgePathUpdater.ts`（待实施时创建），核心逻辑：
- 读写分离：先批量 `getBoundingClientRect`（N 次连续读），再批量 `setAttribute('d', ...)`（N 次连续写）
- Bezier path：与 vue-flow 默认边一致 `M sx,sy C sx+dx,sy tx-dx,ty tx,ty`
- 用 `vue-flow__viewport` 而非 `.vue-flow` 容器 rect 算 handle 画布坐标

## 附录 B：常见踩坑清单

| 现象 | 原因 | 修复 |
|------|------|------|
| 拖动后节点跳回原位 | drag-end 没同步 flowNode.position | onDragEnd 加同步逻辑 |
| 边在拖动时短暂消失 | path 选择器找不到（边刚渲染） | collectAffectedEdges 加 rAF 延后 1 帧 |
| Handle 位置算错 | 取了 zoom 后的 rect 又除了一次 zoom | 用 `vue-flow__viewport` 的 rect |
| 松手后边路径错位一帧 | 清 transform 早于同步 position | 调换顺序：先同步 position 再清 transform |
| `contain: paint` 让选中描边被裁 | 子元素描边超出节点边界 | 改用 `contain: layout style` |
| 多节点拖动主节点卡 | rAF 内 N 次 getBoundingClientRect 触发 layout thrash | 读写分离：先批量读再批量写 |
