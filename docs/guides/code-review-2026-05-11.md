# CogniFlow 规则引擎前端代码审查报告

**审查日期**: 2026-05-11
**审查文件**:
- `webui/src/views/RuleCanvas.vue` (3496 行)
- `webui/src/components/rule-engine/RuleNode.vue` (854 行)
- `webui/src/components/rule-engine/VariablePanel.vue` (343 行)
- `webui/src/stores/ruleEngine.ts` (437 行)

---

## 一、潜在 Bug（高优先级）

### 1.1 [高] `RuleCanvas.vue` - 变量绑定替换逻辑错误

**位置**: `RuleNode.vue` 第 341-347 行

```typescript
function bindVariable(key: string, varName: string) {
  const currentValue = nodeConfig.value[key] || ''
  const varRef = `{{${varName}}}`
  const newValue = currentValue
    ? currentValue + varRef   // 追加到末尾
    : varRef
  updateConfig(key, newValue)
  activeVarMenu.value = null
}
```

**问题**: 当字段已有值时，新变量追加到末尾而非插入光标位置，导致变量绑定顺序错误（如 `"threshold{{old}}{{new}}"` 而非 `"{{new}}threshold"`）。且没有检查是否已存在相同变量引用，会产生重复。

**建议**: 使用 `insertVariable` 在 RuleCanvas.vue 第 1139-1149 行的逻辑（检查 `{{}}` 包裹追加），或在绑定前检查是否已存在相同变量。

---

### 1.2 [高] `RuleCanvas.vue` - `handleContextAction` 状态更新滞后

**位置**: 第 1157-1177 行

```typescript
case 'delete':
  if (contextMenu.targetType === 'node') {
    (nodes.value as unknown as any[]).forEach(...)  // 先选中毒
  } else if (contextMenu.targetType === 'edge') {
    (edges.value as unknown as any[]).forEach(...)  // 先选中毒
  }
  handleDelete()  // 删除时才清空 selectedNode
  break
```

**问题**: `handleDelete` 中删除节点后 `selectedNode.value = null`，但右键菜单是异步隐藏的（`hideContextMenu()` 在 switch 开头），此时 `selectedNode` 已为 null，UI 可能短暂显示旧选中状态。

---

### 1.3 [中] `RuleCanvas.vue` - `handleCut` 重复删除节点

**位置**: 第 992-1010 行

```typescript
function handleCut() {
  clipboard.value = selected.map(...)
  removeNodes(selected.map((n: any) => n.id))           // VueFlow API 删除
  edges.value = edges.value.filter(...)               // 手动删除边
  selected.forEach((n: any) => {
    const idx = nodes.value.findIndex(...)
    if (idx !== -1) nodes.value.splice(idx, 1)         // 再次手动删除
  })
}
```

**问题**: `removeNodes` 已经删除了节点，之后的 `splice` 是冗余的。虽然有 `findIndex` 判断，但如果 `removeNodes` 同步性问题导致节点仍存在，会导致重复删除。

---

### 1.4 [中] `ruleEngine.ts` - `fetchGraph` 后未重置 `selectedNodeId`

**位置**: 第 151-175 行

```typescript
async function fetchGraph(id: number) {
  const res = await ruleEngineApi.getGraphDetail(id)
  currentGraph.value = res.data
  // ... 解析变量 ...
  saveToHistory()  // 初始化撤销栈
  return res.data
}
```

**问题**: `fetchGraph` 加载新图时，如果当前已有选中节点，`selectedNodeId` 不会被重置为 `null`，可能导致新图中显示旧选中节点的状态。应在 `fetchGraph` 开始时重置 `selectedNodeId`。

---

### 1.5 [中] `RuleCanvas.vue` - `graphName` 初始化可能为 undefined

**位置**: 第 641 行、1234 行

```typescript
const graphName = ref('')   // 初始为空

// loadGraph 中:
graphName.value = graph.value.name  // graph.value 可能是 undefined
```

**问题**: 如果 API 返回的 `graph.value` 结构异常，`graph.value.name` 会报错。

---

### 1.6 [中] `RuleNode.vue` - `configSchema` 嵌套结构不一致

**位置**: 第 270-272 行

```typescript
configSchema?: {
  properties?: Record<string, ConfigSchemaProperty>
}
```

**问题**: `NodeData.configSchema` 使用嵌套 `properties`，而 `ConfigSchemaProperty` 的 `visible` 字段（第 27 行 ruleEngine.ts）定义为 `"source=file"` 格式字符串，但代码中从未使用此字段实现条件可见性逻辑。

---

### 1.7 [低] `RuleCanvas.vue` - `insertVariable` 追加逻辑不检查重复

**位置**: 第 1142-1147 行

```typescript
if (currentValue.includes('{{') && currentValue.includes('}}')) {
  nodeConfig.value[varMenu.fieldKey] = `${currentValue}{{${varName}}}`
} else {
  nodeConfig.value[varMenu.fieldKey] = `{{${varName}}}`
}
```

**问题**: 追加模式下不检查 `varName` 是否已存在于当前值中，会产生 `{{var1}}{{var1}}` 重复引用。

---

### 1.8 [低] `ruleEngine.ts` - `saveGraph` 变量 JSON 默认值 null

**位置**: 第 188 行

```typescript
defaultValue: v.defaultValue ?? null,
```

**问题**: 如果 `defaultValue` 是合法的 `"null"` 字符串（作为字符串值而非空值），会被错误转换为 JSON null。建议区分空值和显式 null。

---

## 二、性能问题

### 2.1 [中] `RuleCanvas.vue` - `filteredCategories` 搜索时每次重建数组

**位置**: 第 731-749 行

```typescript
const filteredCategories = computed(() => {
  const query = nodeSearchQuery.value.trim().toLowerCase()
  if (!query) {
    return nodeCategories.value  // 引用传递
  }
  return nodeCategories.value.map(cat => ({
    ...cat,
    nodes: cat.nodes.filter(...),  // 每次创建新对象
    expanded: true
  })).filter(cat => cat.nodes.length > 0)
})
```

**问题**: 搜索模式下每次 computed 都创建新数组对象，当节点数量多时会产生 GC 压力。建议使用 `v-show` + 外部过滤逻辑替代。

---

### 2.2 [中] `RuleCanvas.vue` - `nodeCategories` computed 每次引用重建

**位置**: 第 716-727 行

```typescript
const nodeCategories = computed(() => [
  { name: 'input', label: '输入' },
  { name: 'detection', label: '检测' },
  // ...
].map(cat => ({
  ...cat,
  expanded: categoryExpanded[cat.name as keyof typeof categoryExpanded],
  nodes: nodeDefinitions.value.filter((d) => d.category === cat.name)
})))
```

**问题**: 每次访问都重新创建数组和对象，即使数据未变。建议拆分为常量数组 + 各分类节点的独立 computed。

---

### 2.3 [低] `RuleNode.vue` - `nodeConfig` computed 每次创建新对象

**位置**: 第 306-315 行

```typescript
const nodeConfig = computed((): Record<string, NodeConfigValue> => {
  const defaults: Record<string, NodeConfigValue> = {}
  // ... 每次都创建新 defaults 对象 + 展开运算符合并
  return { ...defaults, ...(props.data.config as ...) }
})
```

**问题**: 每次配置更新都会创建新对象，但配置项通常不多（<20），影响较小。

---

### 2.4 [低] `RuleCanvas.vue` - `captureAndSaveThumbnail` 每次保存都重新渲染 Canvas

**位置**: 第 1664-1777 行

**问题**: 缩略图渲染逻辑复杂，每次 `handleSave` 都调用。如果 save 操作频繁（自动保存场景），会有性能问题。建议增加防抖或只在节点变化时渲染。

---

## 三、代码重复

### 3.1 [中] 节点 ID 生成逻辑重复

**位置**:
- `ruleEngine.ts` 第 209 行: `id: node_${Date.now()}`
- `RuleCanvas.vue` 多处: `id: node_${Date.now()}` (第 1029, 1342, 1346, 1370, 1377 行)

**建议**: 抽取为工具函数:
```typescript
function generateNodeId(): string {
  return `node_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`
}
```

---

### 3.2 [中] 边 ID 生成逻辑重复

**位置**:
- `ruleEngine.ts` 第 274 行: `id: edge_${Date.now()}`
- `RuleCanvas.vue` 第 1506 行: `id: e-${params.source}-${params.target}-${Date.now()}`

**建议**: 抽取为 `generateEdgeId()` 工具函数。

---

### 3.3 [中] 节点创建逻辑重复

**位置**: `handleDrop` (第 1341-1358 行) 和 `quickAddNode` (第 1369-1389 行) 几乎完全相同的节点构建代码，仅 position 计算不同。

**建议**: 抽取为 `createNode(nodeDef, position)` 工具函数。

---

### 3.4 [中] 历史记录保存逻辑重复

**位置**:
- `ruleEngine.ts`: `saveToHistory()` (第 293-311 行)
- `RuleCanvas.vue`: `saveHistory()` (第 913-924 行)

两者实现几乎相同，Store 版本还额外处理了 `selected`/`dragging` 属性。

**建议**: 统一使用 Store 版本，或抽取共享工具函数。

---

### 3.5 [中] 变量插入逻辑在两处实现

**位置**:
- `RuleCanvas.vue` `insertVariable` (第 1139-1150 行)
- `RuleNode.vue` `bindVariable` (第 339-348 行)

两者逻辑略有不同（一个检查 `{{}}` 包裹，一个直接追加），行为不一致。

---

### 3.6 [低] `handleUndo`/`handleRedo` 在两处实现

**位置**: Store (`ruleEngine.ts` 第 316-333 行) 和组件 (`RuleCanvas.vue` 第 1181-1198 行) 各自实现了一套，且逻辑几乎相同。

---

## 四、安全问题

### 4.1 [低] XSS 风险 - 用户输入未转义

**位置**: 多处

- `RuleNode.vue` 第 16 行: `{{ data.label || data.type }}`
- `RuleCanvas.vue` 第 398-411 行空状态快速添加按钮

**问题**: 如果节点 label/description 包含恶意脚本，会被直接渲染。建议对用户输入内容使用 `v-html` 时确保已做转义，或在后端存储时限制格式。

**当前评估**: 节点数据来自后端 API 响应，如果后端做了输入校验，风险可控。

---

### 4.2 [低] WebSocket URL 拼接

**位置**: 第 823-826 行

```typescript
function getWsUrl() {
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${proto}//${window.location.host}/ws/rule-execution`
}
```

**问题**: 缺少 URL 协议验证，如果 `window.location.protocol` 异常，可能生成无效 URL。建议使用 `window.location.origin` 替代。

---

## 五、Vue 最佳实践问题

### 5.1 [中] 直接修改数组索引 - 反模式

**位置**: `RuleCanvas.vue` 多处

```typescript
// 第 1058 行
nodes.value.forEach((n: any) => { n.selected = false })  // 直接修改响应式元素

// 第 1074 行
nodes.value.splice(idx, 1)  // splice 直接操作

// 第 1611 行
variables.value.splice(index, 1)  // 同上
```

**问题**: 在 Vue 3 中直接修改数组元素（`n.selected = false`）可能不会触发响应式更新。建议使用 `findIndex` + 替换或使用 Vue 的 `splice` 包装。

---

### 5.2 [中] `nodes` 和 `edges` 使用 `ref<any[]>` 而非 proper typing

**位置**: 第 642-643 行

```typescript
const nodes = ref<any[]>([])
const edges = ref<any[]>([])
```

**问题**: 使用 `any` 丢失了类型安全，与 Store 中定义的 `GraphNode`/`GraphEdge` 类型不一致。

---

### 5.3 [低] `watch` vs `watchEffect` 误用

**位置**: `RuleCanvas.vue` 无显式 watch，但部分逻辑依赖 computed 的惰性求值特性。

**建议**: 对于副作用逻辑，使用 `watch` 明确依赖。

---

### 5.4 [低] `reactive` 用于复杂状态

**位置**: 第 679-685 行

```typescript
const contextMenu = reactive({
  show: false,
  x: 0,
  y: 0,
  target: null as unknown,
  targetType: null as 'node' | 'edge' | 'pane' | null
})
```

**问题**: `reactive` 对象的属性替换（`contextMenu.targetType = 'node'`）会导致整个对象失去响应式。建议拆分为独立 `ref`。

---

## 六、UI/UX 问题

### 6.1 [中] 节点删除按钮仅 hover 显示，交互隐蔽

**位置**: `RuleNode.vue` 第 226-232 行

```typescript
.node-delete-btn {
  opacity: 0.7;
  .selected & { opacity: 0.9; }  // 选中时也只是 0.9
}
```

**问题**: 删除按钮即使在选中状态下也仅 90% 透明度，不够醒目。新用户可能找不到删除入口。建议选中时始终显示或增加背景色。

---

### 6.2 [中] 变量面板重复 - 两处实现

**位置**:
- `VariablePanel.vue` (独立组件)
- `RuleCanvas.vue` 内部也实现了变量列表 (第 246-316 行)

**问题**: 代码重复，且两者行为不完全一致。`VariablePanel.vue` 使用 `index` 作为 key（第 96 行），可能导致渲染问题（删除中间变量后 index 错位）。

---

### 6.3 [低] 缩略图渲染不支持中文/长文本截断

**位置**: 第 1764-1765 行

```typescript
ctx.fillText(label.substring(0, 12), x + w / 2, y + h / 2)
```

**问题**: 中文字符按字节截断可能只显示半个字，且 canvas 文字渲染不考虑换行。

---

### 6.4 [低] 执行面板位置计算可能越界

**位置**: 第 432-435 行

```typescript
:style="{
  height: showExecutionPanel ? panelHeight + 'px' : '44px',
  left: showPalette ? EXPANDED_WIDTH + 'px' : COLLAPSED_WIDTH + 'px'
}"
```

**问题**: 如果画布宽度小于 `EXPANDED_WIDTH + panelWidth`，面板会超出视口。缺少边界检查。

---

## 七、总结

| 严重程度 | 数量 | 说明 |
|---------|------|------|
| **高** | 2 | 变量绑定逻辑错误、状态更新时序问题 |
| **中** | 12 | 性能问题、代码重复、边界检查缺失 |
| **低** | 11 | XSS 风险较小、UX 改进空间 |

### 优先修复建议

1. **[高] 变量绑定追加逻辑** - 修复追加到末尾而非插入光标位置的问题
2. **[高] `fetchGraph` 重置选中状态** - 避免加载新图时残留旧状态
3. **[中] 节点 ID 生成函数抽取** - 减少重复代码
4. **[中] 变量面板重复** - 统一使用 `VariablePanel.vue`，修复 index 作为 key 的问题
5. **[中] `handleCut` 冗余删除** - 移除重复的 splice 操作
6. **[低] 删除按钮可见性** - 选中状态时始终显示删除按钮

### 架构建议

1. **统一状态管理**: `RuleCanvas.vue` 和 `ruleEngine.ts` 各维护一套 history/undo/redo，建议统一到 Store
2. **类型统一**: 组件内 `nodes`/`edges` 应使用 `GraphNode`/`GraphEdge` 类型而非 `any`
3. **工具函数库**: 抽取 `generateNodeId`、`generateEdgeId`、`createNode` 等为共享工具