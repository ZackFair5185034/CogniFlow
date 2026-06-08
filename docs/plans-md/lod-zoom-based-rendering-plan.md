# 规则引擎节点画布 LOD 分级渲染方案

基于缩放级别 + 节点密度的动态细节渲染 · 2026-06-08

---

## 1. 背景与目标

### 1.1 现有架构

`RuleCanvas.vue` 当前已具备以下基础：

| 模块 | 状态 | 文件 |
|---|---|---|
| `v-memo: [id, status, summaryText, category]` | ✅ 拖动期间 0 patch | `RuleNode.vue:9` |
| `useCogniFlowDrag` 直写 DOM transform | ✅ 0 响应式写入 | `composables/useCogniFlowDrag.ts` |
| `only-render-visible-elements="true"` | ✅ 视口外节点不渲染 | `RuleCanvas.vue:397` |
| `largeGraphMode` 样式降级 | ✅ 关阴影/动画 | `RuleCanvas.vue:748` |
| 右侧属性面板（NodeConfigEditor 751 行） | ⚠️ 占用 360px，遮挡 handle | `RuleCanvas.vue` |

### 1.2 改造目标

**把属性配置从右侧面板迁到节点内（重型节点设计），同时通过 LOD 机制防止性能塌方。**

### 1.3 关键约束

- 不破坏现有 v-memo 优化
- 100 节点首屏 < 1s
- 50 节点拖拽仍 60fps
- 与 useCogniFlowDrag / only-render-visible-elements 兼容

---

## 2. LOD 分级矩阵

| 级别 | 缩放 | 节点标题 | 摘要 | 端口 | 配置 | 节点高度 |
|---|---|---|---|---|---|---|
| **LOD 0** | zoom < 0.3 | ✓ | – | 极小点 | – | 40px |
| **LOD 1** | 0.3 ≤ zoom < 0.7 或 节点 > 80 | ✓ | ✓ | ✓ | – | 80px |
| **LOD 2** | zoom ≥ 0.7 且 节点 ≤ 80 | ✓ | ✓ | ✓ | ✓ | 200-400px |

**强制 LOD 2 覆盖**：
- 选中节点（`node.selected === true`）
- 拖动中（避免 LOD 抖动）
- 配置已展开（`node.data.configExpanded`）

---

## 3. 实施步骤

### Step 1：store 暴露 viewport zoom（0.5h）

**文件**：`webui/src/stores/ruleEngine.ts`

```ts
// 在 store setup 中新增
const viewportZoom = ref(1)

function setViewportZoom(z: number) {
  // 节流到 100ms，避免每帧写入
  if (Math.abs(z - viewportZoom.value) > 0.01) {
    viewportZoom.value = z
  }
}

return { viewportZoom, setViewportZoom, ... }
```

**文件**：`webui/src/views/RuleCanvas.vue` 同步

```ts
// handleZoom 中写入
function handleZoom({ zoom }: { zoom: number; event: unknown }) {
  // ... 现有逻辑
  store.setViewportZoom(zoom)
  // ... zoomLevel 文本更新
}
```

### Step 2：计算全局 LOD map（0.5h）

**文件**：`webui/src/stores/ruleEngine.ts`

```ts
import { computed } from 'vue'

const lodLevelMap = computed<Map<string, 0 | 1 | 2>>(() => {
  const map = new Map<string, 0 | 1 | 2>()
  const zoom = viewportZoom.value
  const count = nodes.value.length
  const isLodLocked = isNodeDragging.value || isSelectionDragging.value

  for (const n of nodes.value) {
    // 强制 LOD 2 覆盖：选中 / 拖动中 / 配置已展开
    if (n.selected) { map.set(n.id, 2); continue }
    if (n.data?.configExpanded) { map.set(n.id, 2); continue }
    if (isLodLocked) {
      // 拖动中保持拖动前级别
      map.set(n.id, map.get(n.id) ?? 1)
      continue
    }
    // 按缩放 + 节点密度
    if (zoom < 0.3) map.set(n.id, 0)
    else if (zoom < 0.7 || count > 80) map.set(n.id, 1)
    else map.set(n.id, 2)
  }
  return map
})

function getLodLevel(nodeId: string): 0 | 1 | 2 {
  return lodLevelMap.value.get(nodeId) ?? 1
}
```

### Step 3：RuleNode 模板分三级 v-if（1.5h）

**文件**：`webui/src/components/rule-engine/RuleNode.vue`

```vue
<template>
  <div
    v-memo="[data.id, data.status, data.summaryText, data.category, lodLevel]"
    :data-lod="lodLevel"
    class="rule-node"
    :class="[`category-${data.category}`, `lod-${lodLevel}`]"
    @contextmenu.prevent="emit('contextmenu', $event)"
  >
    <!-- LOD 0/1/2 通用: 标题 -->
    <div class="node-header">
      <div class="node-icon" :class="data.category">
        <SvgIcon :name="data.category" />
      </div>
      <div class="node-title">
        <span class="node-label">{{ data.label || data.type }}</span>
      </div>
    </div>

    <!-- LOD 1/2: 摘要 -->
    <div
      v-if="lodLevel >= 1 && data.summaryText"
      class="node-summary"
    >
      {{ data.summaryText }}
    </div>

    <!-- LOD 1/2: 端口 -->
    <div
      v-if="lodLevel >= 1 && ((data.inputs?.length || 0) > 0 || (data.outputs?.length || 0) > 0)"
      class="node-ports"
    >
      <div
        v-for="input in data.inputs"
        :key="'in-' + input.name"
        class="port-item port-in"
      >
        <Handle
          :id="input.name"
          type="target"
          :position="Position.Left"
          :class="['node-handle', `type-${(input.type ?? 'any').toLowerCase()}`]"
        />
        <span v-if="lodLevel >= 2" class="port-label">{{ input.label || input.name }}</span>
      </div>
      <div
        v-for="output in data.outputs"
        :key="'out-' + output.name"
        class="port-item port-out"
      >
        <span v-if="lodLevel >= 2" class="port-label">{{ output.label || output.name }}</span>
        <Handle
          :id="output.name"
          type="source"
          :position="Position.Right"
          :class="['node-handle', `type-${(output.type ?? 'any').toLowerCase()}`]"
        />
      </div>
    </div>

    <!-- LOD 2: 配置区 -->
    <div
      v-if="lodLevel >= 2 && configProperties && Object.keys(configProperties).length > 0"
      class="node-config"
      v-show="data.configExpanded !== false"
    >
      <!-- 委托给 NodeConfigEditor 内联版 -->
      <NodeConfigInline
        :node-id="data.id"
        :config-schema="configProperties"
        :config="data.config"
      />
    </div>

    <!-- 状态指示器（所有级别） -->
    <div
      v-if="data.status && data.status !== 'idle'"
      class="node-status"
    >
      <div
        class="status-indicator"
        :class="data.status"
        :title="statusTitle"
      />
    </div>
  </div>
</template>
```

**关键变更**：
- `v-memo` 依赖加入 `lodLevel` — 缩放切换时节点 vdom 增量更新
- `v-if` 切换不同 DOM 树 — 真正卸载配置区，释放内存
- 端口 label 仅 LOD 2 显示 — 减少 DOM
- 配置区使用 `v-show` 而不是 `v-if`（在 `v-if="lodLevel >= 2"` 内部），保留展开/折叠切换

### Step 4：CSS 分级降级（0.5h）

```scss
/* LOD 0: 极简节点 */
.rule-node.lod-0 {
  min-height: 36px;
  padding: 4px 8px;

  .node-header {
    padding: 0;
    border: none;
  }
  .node-label {
    font-size: 11px;
  }
  .vue-flow__handle {
    width: 6px; height: 6px;
  }
}

/* LOD 1: 节点壳（当前 130 行默认模板） */
.rule-node.lod-1 {
  width: 200px;
  /* ... 现有样式 ... */
}

/* LOD 2: 完整节点（带配置） */
.rule-node.lod-2 {
  width: 320px;  // 比 LOD 1 宽 120px
  /* 现有样式 + 配置区样式 */
  .node-config {
    padding: 8px 10px;
    border-top: 1px solid rgba(255, 255, 255, 0.04);
  }
}
```

### Step 5：NodeConfigInline 组件（1.5h，复用现有逻辑）

**新建文件**：`webui/src/components/rule-engine/NodeConfigInline.vue`

从 NodeConfigEditor.vue 抽出核心逻辑（不重复实现）：
- widget 路由（slider/number/dropdown/multiselect/model-select/text/checkbox）
- updateConfig 委托给 store
- dynamicEnumFor / loadModelCategories 等辅助

**最小可用版本**：仅支持 text/number/slider/dropdown 4 个 widget，覆盖 80% 节点。复杂 widget（multiselect、model-select）仍走右侧面板。

### Step 6：拖动期间锁定 LOD（0.5h）

**文件**：`webui/src/composables/useCogniFlowDrag.ts`

```ts
let lodLocked = false

.on('start', (event) => {
  lodLocked = true
  store.lockLodDuringDrag()  // 告诉 store 锁定 LOD
  onDragStart(event, el)
})
.on('end', (event) => {
  onDragEnd(event, el)
  lodLocked = false
  store.unlockLodDuringDrag()
})
```

**store 实现**：
```ts
const isDragging = ref(false)
function lockLodDuringDrag() { isDragging.value = true }
function unlockLodDuringDrag() { isDragging.value = false }
```

**LOD 计算**：
```ts
if (isDragging.value) {
  // 保持当前 LOD 不变
  return map.get(n.id) ?? 1
}
```

### Step 7：可手动展开配置（0.5h）

```ts
// store
function toggleConfigExpanded(nodeId: string) {
  const n = nodeById.get(nodeId)
  if (n) n.data.configExpanded = !(n.data.configExpanded ?? true)
}
```

**RuleNode 模板**：
```vue
<!-- 折叠按钮 (LOD 1 显示，提示用户可展开) -->
<button
  v-if="lodLevel === 1 && hasConfig"
  class="node-expand-btn"
  @click.stop="expandConfig"
  title="展开配置"
>
  ⚙
</button>
```

---

## 4. 验证计划

### 4.1 单元验证

```bash
# TypeScript 类型检查
pnpm build:type 2>&1 | grep -E "error TS" | grep -v "AtlasList|ModelList" | head -5

# 现有测试不破坏
PYTHONPATH=. rtk pytest backend/tests/test_rule_engine/ -q 2>&1 | tail -5
```

### 4.2 浏览器验证（Playwright）

| 测试 | 验证 |
|---|---|
| 创建 50 节点，zoom 0.5 | DOM 数量 = 50 × LOD 1 |
| 缩放到 zoom 0.2 | DOM 数量 = 50 × LOD 0（应减少 60%+） |
| 缩放到 zoom 1.0 | DOM 数量 = 50 × LOD 2（应增加 3-4x） |
| 选中节点 | 单独该节点变 LOD 2 |
| 拖拽节点 | LOD 切换被锁定，无 v-memo 失效 |
| 配置控件响应 | 改 config 后 store 更新 |

### 4.3 性能预算

| 指标 | 当前 | LOD 目标 |
|---|---|---|
| 50 节点首屏 | ~500ms | ~600ms（增加 20% 但获得内嵌配置） |
| 50 节点 zoom 0.2 概览 | ~500ms | **~200ms**（-60%） |
| 拖拽 50 节点 FPS | 60 | 60（不变） |
| zoom 切换 50 节点 | ~80ms | ~100ms（v-memo 失效一次） |

---

## 5. 风险与回退

### 5.1 风险

| 风险 | 缓解 |
|---|---|
| v-memo 失效链引发 100 节点 patch 风暴 | 缩放切换是低频操作，瞬时性能影响可接受 |
| NodeConfigInline 控件状态丢失 | v-memo 依赖 id+lodLevel，节点缩放切换时 id 不变 → 状态保留 |
| 复杂 widget (multiselect/model-select) 内嵌有性能问题 | 简化为仅 4 种基础 widget，复杂 widget 仍走右侧面板 |
| 节点高度膨胀遮挡 handle | LOD 1 高度 80px 不变；LOD 2 高度 200-400px 已知 |

### 5.2 回退方案

LOD 是渐进增强：每步都可独立 commit。如果某步骤失败，可以：
- Step 3 失败 → 回退到摘要模式，不内嵌配置
- Step 5 失败 → 仅做 4 种基础 widget，复杂 widget 保持右侧面板
- 整体失败 → 保持当前架构 + 已修复的 3 个 bug

---

## 6. 交付物

| 项 | 状态 |
|---|---|
| 文档 | docs/plans-md/lod-zoom-based-rendering-plan.md |
| Step 1: viewportZoom store | ⏳ |
| Step 2: lodLevelMap | ⏳ |
| Step 3: RuleNode 模板分级 | ⏳ |
| Step 4: CSS 分级 | ⏳ |
| Step 5: NodeConfigInline | ⏳ |
| Step 6: 拖动锁定 | ⏳ |
| Step 7: 展开按钮 | ⏳ |
| 验证 | ⏳ |

---

## 7. 时间预估

| 步骤 | 工作量 |
|---|---|
| Step 1-2 (基础架构) | 1h |
| Step 3-4 (核心 LOD) | 2h |
| Step 5 (内联配置) | 1.5h |
| Step 6-7 (交互) | 1h |
| 验证调优 | 1h |
| **总计** | **~6.5h** |
