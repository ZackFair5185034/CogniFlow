# Phase 3 技术实现文档：画布交互基础（前端）
基于 Vue Flow 实现完整的画布交互，包括节点拖拽、边连接、选择复制删除等基础功能

---

## 一、阶段目标
**目标：**基于 Vue Flow 实现完整的画布交互，包括节点拖拽、边连接、选择复制删除等基础功能。

**验收标准：**

 
- 从左侧面板拖拽节点到画布，节点正确创建 
- 两节点间连线，类型匹配时允许，类型不匹配时拒绝并提示 
- 选中节点按 Delete 可删除 
- Ctrl+C/V 可复制粘贴节点（ID 重新生成） 
- Ctrl+Z/Y 可撤销/重做（至少 20 步） 
- 画布支持缩放（滚轮）、平移（拖拽空白处） 
- 右键菜单显示正确 

## 二、Vue Flow 集成

### 2.1 安装依赖

```text
cd webui
pnpm add @vue-flow/core @vue-flow/background @vue-flow/controls @vue-flow/minimap
```

### 2.2 基础配置

```vue
<template>
  <div class="rule-canvas">
    <VueFlow
      v-model:nodes="nodes"
      v-model:edges="edges"
      :node-types="nodeTypes"
      :default-edge-options="defaultEdgeOptions"
      :connection-line-style="connectionLineStyle"
      :connection-mode="ConnectionMode.Strict"
      :snap-to-grid="snapGrid"
      :snap-grid="[16, 16]"
      @connect="onConnect"
      @nodes-change="onNodesChange"
      @edges-change="onEdgesChange"
      @node-click="onNodeClick"
      @pane-click="onPaneClick"
      @pane-context-menu="onPaneContextMenu"
      @node-context-menu="onNodeContextMenu"
      @edge-context-menu="onEdgeContextMenu"
      @keydown="onKeyDown"
    >
      <Background :variant="BackgroundVariant.Dots" :gap="16" />
      <Controls />
      <MiniMap v-if="showMiniMap" :node-color="minimapNodeColor" />
    </VueFlow>
  </div>
</template>
```

*节点类型映射：`ImageCapture` / `YOLOModel` / `Condition` 等对应自定义 Vue 组件*

## 三、节点拖拽添加

### 3.1 节点面板（左侧）
节点面板按类别分组，支持拖拽到画布：

 
- 每个类别显示为可折叠区块，带颜色标识圆点 
- 节点卡片带图标和名称，支持 `draggable` 属性 
- `dragstart` 事件携带 `nodeType` 数据 

### 3.2 拖放处理

```javascript
function onDropEvent(event: DragEvent) {
  const nodeType = event.dataTransfer?.getData('nodeType')
  if (!nodeType) return

  // 获取放置位置（转换为画布坐标）
  const { left, top } = (event.target as HTMLElement).getBoundingClientRect()
  const position = project({
    x: event.clientX - left,
    y: event.clientY - top
  })

  const newNode = createNode(nodeType, position)
  nodes.value = [...nodes.value, newNode]
  markDirty()
}

function createNode(type: string, position: { x: number; y: number }): CanvasNode {
  const id = `node_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  const definition = getNodeDefinition(type)

  return {
    id,
    type,
    position,
    data: {
      label: definition.display_name,
      params: getDefaultParams(definition),
      inputs: {},
      outputs: {}
    }
  }
}
```

## 四、边连接与类型检查

### 4.1 类型兼容性矩阵

```typescript
const TYPE_COMPATIBILITY: Record<string, string[]> = {
  "IMAGE": ["IMAGE", "MASK"],
  "BBOX": ["BBOX"],
  "MASK": ["MASK"],
  "SCORES": ["SCORES"],
  "CLASS_IDS": ["CLASS_IDS"],
  "TRIGGER": ["TRIGGER", "BBOX", "IMAGE", "MASK", "SCORES", "CLASS_IDS", "CONTROL"],
  "CONTROL": ["CONTROL"],
  "MODEL": ["MODEL"],
  "ANY": ["IMAGE", "BBOX", "MASK", "SCORES", "CLASS_IDS", "TRIGGER", "CONTROL", "MODEL", "ANY"]
}
```

### 4.2 连接事件处理

```text
async function onConnect(params: Connection) {
  const sourceType = getOutputType(params.source, params.sourceHandle)
  const targetType = getInputType(params.target, params.targetHandle)

  if (!sourceType || !targetType) {
    ElMessage.warning('连接失败：端口类型未知')
    return
  }

  if (!canConnect(sourceType, targetType)) {
    ElMessage.warning({
      message: `类型不匹配：${sourceType} 无法连接到 ${targetType}`,
      type: 'warning'
    })
    return
  }

  const newEdge = { ...params, id: `edge_${Date.now()}`, type: 'smoothstep' }
  addEdges([newEdge])
  markDirty()
}
```

## 五、节点选择与操作

### 5.1 复制粘贴

```text
// 复制
const clipboard = ref<CanvasNode[]>([])

function copySelected() {
  clipboard.value = nodes.value
    .filter(n => selectedNodes.value.includes(n.id))
    .map(n => ({ ...n, id: '', data: { ...n.data, inputs: {} } }))
}

// 粘贴（位置偏移 50px）
function pasteClipboard() {
  const newNodes = clipboard.value.map(n => ({
    ...n,
    id: `node_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
    position: { x: n.position.x + 50, y: n.position.y + 50 }
  }))
  addNodes(newNodes)
  selectedNodes.value = newNodes.map(n => n.id)
  markDirty()
}

// 快捷键
function onKeyDown(event: KeyboardEvent) {
  if (event.ctrlKey || event.metaKey) {
    if (event.key === 'c') copySelected()
    if (event.key === 'v') pasteClipboard()
  }
}
```

### 5.2 删除选中

```javascript
function deleteSelected() {
  for (const nodeId of selectedNodes.value) {
    const connectedEdges = edges.value.filter(
      e => e.source === nodeId || e.target === nodeId
    )
    removeEdges(connectedEdges)
  }
  removeNodes(selectedNodes.value)
  selectedNodes.value = []
  markDirty()
}

function onKeyDown(event: KeyboardEvent) {
  if (event.key === 'Delete' || event.key === 'Backspace') {
    if ((event.target as HTMLElement).tagName === 'INPUT') return
    deleteSelected()
  }
}
```

## 六、撤销/重做

### 6.1 UndoManager 实现
UndoManager 使用 Command 模式，支持 50 步撤销栈：

 
- `ADD_NODE` — 添加节点 
- `REMOVE_NODE` — 删除节点（含关联边） 
- `ADD_EDGE` — 添加边 
- `MOVE_NODE` — 移动节点 
- `UPDATE_NODE_DATA` — 更新节点数据 

```javascript
export class UndoManager {
  private undoStack: Command[] = []
  private redoStack: Command[] = []
  private maxSize: number

  execute(command: Command) {
    command.do?.()
    this.undoStack.push(command)
    this.redoStack = []
    if (this.undoStack.length > this.maxSize) this.undoStack.shift()
  }

  undo(): boolean { ... }
  redo(): boolean { ... }
  canUndo(): boolean { return this.undoStack.length > 0 }
  canRedo(): boolean { return this.redoStack.length > 0 }
}
```

## 七、右键菜单
右键菜单根据上下文显示不同选项：

       
| 上下文 | 菜单项 |
| --- | --- |
| 画布空白处 | 粘贴、全选、适应画布 |
| 节点 | 复制、复制并粘贴、删除 |
| 连线 | 删除连线 |

## 八、状态管理
使用 Pinia Store 管理画布状态：

 
- `nodes` / `edges` — 节点和边数据 
- `selectedNodeIds` — 当前选中节点 
- `snapGrid` / `showGrid` / `showMiniMap` — 画布配置 
- `isDirty` — 脏标记（是否有未保存更改） 
- `loadGraph()` / `getGraphData()` — 图数据序列化 

## 九、验收检查清单
                       
| 类别 | 验收项 |
| --- | --- |
| 拖拽交互 | 左侧面板显示 6 类节点 |
| 节点可拖拽到画布 |  |
| 放置位置正确（鼠标位置转换为画布坐标） |  |
| 新节点自动生成唯一 ID |  |
| 连接交互 | 从输出端口拖出连接线 |
| 类型匹配时允许连接 |  |
| 类型不匹配时显示警告 |  |
| 删除边时更新节点连接信息 |  |
| 操作交互 | Delete 键删除选中节点和连接的边 |
| Ctrl+C 复制选中节点 |  |
| Ctrl+V 粘贴节点（位置偏移） |  |
| Ctrl+Z/Y 撤销/重做（至少 20 步） |  |
| 画布交互 | 鼠标滚轮缩放 |
| 拖拽空白处平移画布 |  |
| 右键菜单正确显示 |  |
| 小地图可切换显示/隐藏 |  |
| 状态管理 | 节点/边变更后 isDirty = true |
| 保存后 isDirty = false |  |
| 离开页面时提醒未保存更改 |  |
