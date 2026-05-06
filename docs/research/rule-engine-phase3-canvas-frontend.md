# Phase 3 技术实现文档：画布交互基础（前端）

> ⚠️ **实现前审核状态：** 待老大评审
> 文档版本：v1.0
> 基于调研：canvas-editor-research-2026-05-06.md
> 阶段：Phase 3
> 创建时间：2026-05-06

---

## 1. 阶段目标

**目标：** 基于 Vue Flow 实现完整的画布交互，包括节点拖拽、边连接、选择复制删除等基础功能。

**验收标准：**
- [ ] 从左侧面板拖拽节点到画布，节点正确创建
- [ ] 两节点间连线，类型匹配时允许，类型不匹配时拒绝并提示
- [ ] 选中节点按 Delete 可删除
- [ ] Ctrl+C/V 可复制粘贴节点（ID 重新生成）
- [ ] Ctrl+Z/Y 可撤销/重做（至少 20 步）
- [ ] 画布支持缩放（滚轮）、平移（拖拽空白处）
- [ ] 右键菜单显示正确

---

## 2. Vue Flow 集成

### 2.1 安装依赖

```bash
cd webui
pnpm add @vue-flow/core @vue-flow/background @vue-flow/controls @vue-flow/minimap
```

### 2.2 基础配置

```typescript
// webui/src/components/rule-canvas/CanvasRenderer.vue

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
      ref="vueFlowRef"
    >
      <!-- 背景 -->
      <Background :variant="BackgroundVariant.Dots" :gap="16" />

      <!-- 控制按钮 -->
      <Controls />

      <!-- 小地图 -->
      <MiniMap
        v-if="showMiniMap"
        :node-color="minimapNodeColor"
        :node-stroke-width="2"
      />

      <!-- 自定义连接线 -->
      <template #connection-line="{ connection }">
        <svg style="position: absolute; width: 100%; height: 100%; pointer-events: none">
          <path
            :d="connectionPath(connection)"
            fill="none"
            stroke="#00f0FF"
            stroke-width="2"
          />
        </svg>
      </template>
    </VueFlow>
  </div>
</template>

<script setup lang="ts">
import { VueFlow, useVueFlow, Position, ConnectionMode, MarkerType } from '@vue-flow/core'
import { Background, BackgroundVariant } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import { MiniMap } from '@vue-flow/minimap'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import '@vue-flow/controls/dist/style.css'
import '@vue-flow/minimap/dist/style.css'

// 导入自定义节点组件
import InputNode from './nodes/InputNode.vue'
import DetectionNode from './nodes/DetectionNode.vue'
import ProcessingNode from './nodes/ProcessingNode.vue'
import ActionNode from './nodes/ActionNode.vue'
import LogicNode from './nodes/LogicNode.vue'
import OutputNode from './nodes/OutputNode.vue'

// 节点类型映射
const nodeTypes = {
  ImageCapture: InputNode,
  VideoCapture: InputNode,
  ScreenCapture: InputNode,
  YOLOModel: DetectionNode,
  ObjectDetector: DetectionNode,
  CategoryEncode: ProcessingNode,
  Filter: ProcessingNode,
  MouseClick: ActionNode,
  KeyPress: ActionNode,
  Notification: ActionNode,
  Condition: LogicNode,
  Timer: LogicNode,
  ActionOutput: OutputNode,
  SaveResult: OutputNode
}

// 默认边样式
const defaultEdgeOptions = {
  type: 'smoothstep',
  animated: false,
  markerEnd: MarkerType.ArrowClosed
}

// 连接线样式
const connectionLineStyle = {
  stroke: '#00f0FF',
  strokeWidth: 2
}
</script>
```

---

## 3. 节点拖拽添加

### 3.1 节点面板（左侧）

```vue
<!-- webui/src/components/rule-canvas/NodePalette.vue -->

<template>
  <div class="node-palette" :class="{ collapsed: !showPalette }">
    <div class="palette-header">
      <h3 v-if="showPalette">节点库</h3>
      <button class="collapse-btn" @click="showPalette = !showPalette">
        <SvgIcon :name="showPalette ? 'chevron-left' : 'chevron-right'" />
      </button>
    </div>

    <div class="palette-content" v-show="showPalette">
      <div
        v-for="category in categories"
        :key="category.name"
        class="node-category"
      >
        <div
          class="category-header"
          @click="category.expanded = !category.expanded"
        >
          <span
            class="category-dot"
            :style="{ backgroundColor: category.color }"
          ></span>
          <span class="category-name">{{ category.display_name }}</span>
          <SvgIcon
            name="chevron-down"
            :class="{ rotated: !category.expanded }"
          />
        </div>

        <div class="category-nodes" v-show="category.expanded">
          <div
            v-for="node in category.nodes"
            :key="node.type"
            class="palette-node"
            :style="{ borderColor: category.color }"
            draggable="true"
            @dragstart="onDragStart($event, node)"
            @dragend="onDragEnd"
          >
            <SvgIcon :name="node.icon" />
            <span>{{ node.display_name }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

const props = defineProps<{
  categories: CategoryInfo[]
  nodes: NodeDefinition[]
}>()

const emit = defineEmits<{
  (e: 'drag-start', event: DragEvent, nodeType: string): void
  (e: 'drag-end'): void
}>()

const showPalette = ref(true)

// 按类别分组节点
const categories = computed(() => {
  return props.categories.map(cat => ({
    ...cat,
    expanded: true,
    nodes: props.nodes.filter(n => n.category === cat.name)
  }))
})

function onDragStart(event: DragEvent, node: NodeDefinition) {
  event.dataTransfer?.setData('nodeType', node.type)
  event.dataTransfer!.effectAllowed = 'move'
  emit('drag-start', event, node.type)
}

function onDragEnd() {
  emit('drag-end')
}
</script>

<style scoped>
.node-palette {
  width: 240px;
  background: var(--bg-secondary);
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  transition: width 0.2s;
}

.node-palette.collapsed {
  width: 40px;
}

.palette-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px;
  border-bottom: 1px solid var(--border-color);
}

.palette-header h3 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
}

.collapse-btn {
  background: none;
  border: none;
  cursor: pointer;
  padding: 4px;
}

.category-header {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  cursor: pointer;
  gap: 8px;
}

.category-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.category-name {
  flex: 1;
  font-size: 13px;
  font-weight: 500;
}

.category-nodes {
  padding: 4px 12px;
}

.palette-node {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  margin: 4px 0;
  background: var(--bg-card);
  border: 1px solid;
  border-radius: 6px;
  cursor: grab;
  font-size: 12px;
  transition: background 0.2s;
}

.palette-node:hover {
  background: var(--bg-hover);
}

.palette-node:active {
  cursor: grabbing;
}
</style>
```

### 3.2 拖放处理

```typescript
// webui/src/components/rule-canvas/CanvasRenderer.vue

import { useVueFlow, VueFlow } from '@vue-flow/core'
import { ref, onMounted, onUnmounted } from 'vue'

const {
  onDrop,
  onDragOver,
  project,
  fitView,
  zoomIn,
  zoomOut,
  getViewport
} = useVueFlow()

// 拖放处理
function onDragOver(event: DragEvent) {
  event.preventDefault()
  if (event.dataTransfer) {
    event.dataTransfer.dropEffect = 'move'
  }
}

function onDropEvent(event: DragEvent) {
  event.preventDefault()

  const nodeType = event.dataTransfer?.getData('nodeType')
  if (!nodeType) return

  // 获取放置位置（转换为画布坐标）
  const { left, top } = (event.target as HTMLElement).getBoundingClientRect()
  const position = project({
    x: event.clientX - left,
    y: event.clientY - top
  })

  // 创建新节点
  const newNode = createNode(nodeType, position)

  // 添加到画布
  nodes.value = [...nodes.value, newNode]

  // 更新保存状态
  markDirty()
}

// 创建节点
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

// 获取节点定义
function getNodeDefinition(type: string): NodeDefinition {
  // 从 store 或 props 获取
  return nodeDefinitions.value.find(n => n.type === type)!
}

// 获取默认参数
function getDefaultParams(definition: NodeDefinition): Record<string, any> {
  const params: Record<string, any> = {}

  for (const [key, port] of Object.entries(definition.inputs)) {
    if (!port.required && port.default !== null) {
      params[key] = port.default
    }
  }

  for (const [key, port] of Object.entries(definition.outputs)) {
    // 初始化输出
  }

  return params
}
```

---

## 4. 边连接与类型检查

### 4.1 连接处理

```typescript
// webui/src/components/rule-canvas/CanvasRenderer.vue

import { useVueFlow } from '@vue-flow/core'
import { ElMessage } from 'element-plus'

const { addEdges, removeEdges } = useVueFlow()

// 类型兼容性检查（参考调研报告 3.5）
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

function canConnect(sourceType: string, targetType: string): boolean {
  const compatible = TYPE_COMPATIBILITY[sourceType]
  return compatible?.includes(targetType) ?? false
}

// 获取输出端口类型
function getOutputType(nodeId: string, handleId: string): string | null {
  const node = nodes.value.find(n => n.id === nodeId)
  if (!node) return null

  const definition = getNodeDefinition(node.type)
  return definition.outputs[handleId]?.type ?? null
}

// 获取输入端口类型
function getInputType(nodeId: string, handleId: string): string | null {
  const node = nodes.value.find(n => n.id === nodeId)
  if (!node) return null

  const definition = getNodeDefinition(node.type)
  return definition.inputs[handleId]?.type ?? null
}

// 连接事件处理
async function onConnect(params: Connection) {
  // 获取源和目标节点定义
  const sourceNode = nodes.value.find(n => n.id === params.source)
  const targetNode = nodes.value.find(n => n.id === params.target)

  if (!sourceNode || !targetNode) {
    ElMessage.warning('连接失败：节点不存在')
    return
  }

  const sourceDef = getNodeDefinition(sourceNode.type)
  const targetDef = getNodeDefinition(targetNode.type)

  // 获取端口类型
  const sourceType = sourceDef.outputs[params.sourceHandle || '']?.type
  const targetType = targetDef.inputs[params.targetHandle || '']?.type

  if (!sourceType || !targetType) {
    ElMessage.warning('连接失败：端口类型未知')
    return
  }

  // 类型检查
  if (!canConnect(sourceType, targetType)) {
    ElMessage.warning({
      message: `类型不匹配：${sourceType} 无法连接到 ${targetType}`,
      type: 'warning'
    })
    return
  }

  // 类型匹配，创建边
  const newEdge = {
    ...params,
    id: `edge_${Date.now()}`,
    type: 'smoothstep',
    animated: false
  }

  addEdges([newEdge])

  // 更新节点数据中的连接信息
  updateNodeConnection(params.target, params.targetHandle, {
    node_id: params.source,
    output: params.sourceHandle
  })

  markDirty()
}

// 更新节点的连接信息
function updateNodeConnection(
  nodeId: string,
  handle: string | null,
  connection: { node_id: string; output: string }
) {
  const nodeIndex = nodes.value.findIndex(n => n.id === nodeId)
  if (nodeIndex === -1) return

  const node = nodes.value[nodeIndex]

  nodes.value[nodeIndex] = {
    ...node,
    data: {
      ...node.data,
      inputs: {
        ...node.data.inputs,
        [handle || '']: connection
      }
    }
  }
}
```

### 4.2 断开连接

```typescript
// 删除边时更新节点连接信息
function onEdgesChange(changes: EdgeChange[]) {
  for (const change of changes) {
    if (change.type === 'remove') {
      const edge = edges.value.find(e => e.id === change.id)
      if (edge) {
        // 清除目标节点的连接信息
        clearNodeConnection(edge.target, edge.targetHandle)
      }
    }
  }
}

function clearNodeConnection(nodeId: string, handle: string | null) {
  const nodeIndex = nodes.value.findIndex(n => n.id === nodeId)
  if (nodeIndex === -1) return

  const node = nodes.value[nodeIndex]

  const newInputs = { ...node.data.inputs }
  delete newInputs[handle || '']

  nodes.value[nodeIndex] = {
    ...node,
    data: {
      ...node.data,
      inputs: newInputs
    }
  }
}
```

---

## 5. 节点选择与操作

### 5.1 选择状态

```typescript
// 选择状态由 Vue Flow 内置处理
// 通过 @node-click 事件处理选择逻辑

const selectedNodes = ref<string[]>([])

function onNodeClick(event: NodeMouseEvent) {
  if (event.event.shiftKey) {
    // Shift + 点击：多选
    const nodeId = event.node.id
    if (selectedNodes.value.includes(nodeId)) {
      selectedNodes.value = selectedNodes.value.filter(id => id !== nodeId)
    } else {
      selectedNodes.value = [...selectedNodes.value, nodeId]
    }
  } else {
    // 单击：单选
    selectedNodes.value = [event.node.id]
  }
}

function onPaneClick() {
  // 点击空白处：取消选择
  selectedNodes.value = []
}
```

### 5.2 删除选中

```typescript
const { removeNodes, removeEdges } = useVueFlow()

function deleteSelected() {
  if (selectedNodes.value.length === 0) return

  // 删除选中的节点
  for (const nodeId of selectedNodes.value) {
    // 同时删除与该节点相连的边
    const connectedEdges = edges.value.filter(
      e => e.source === nodeId || e.target === nodeId
    )
    removeEdges(connectedEdges)
  }

  removeNodes(selectedNodes.value)

  // 清空选择
  selectedNodes.value = []

  markDirty()
}

// 键盘事件
function onKeyDown(event: KeyboardEvent) {
  if (event.key === 'Delete' || event.key === 'Backspace') {
    // 防止在输入框中误删
    if ((event.target as HTMLElement).tagName === 'INPUT') return
    deleteSelected()
  }
}
```

### 5.3 复制粘贴

```typescript
// 剪贴板
const clipboard = ref<CanvasNode[]>([])

async function copySelected() {
  if (selectedNodes.value.length === 0) return

  clipboard.value = nodes.value
    .filter(n => selectedNodes.value.includes(n.id))
    .map(n => ({
      ...n,
      id: '', // 粘贴时生成新 ID
      data: {
        ...n.data,
        inputs: {} // 清空连接信息
      }
    }))

  ElMessage.success(`已复制 ${clipboard.value.length} 个节点`)
}

async function pasteClipboard() {
  if (clipboard.value.length === 0) return

  const viewport = getViewport()
  const newNodes: CanvasNode[] = []

  for (const node of clipboard.value) {
    const newId = `node_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`

    // 偏移粘贴位置
    const newPosition = {
      x: node.position.x + 50,
      y: node.position.y + 50
    }

    newNodes.push({
      ...node,
      id: newId,
      position: newPosition
    })
  }

  addNodes(newNodes)

  // 选中新粘贴的节点
  selectedNodes.value = newNodes.map(n => n.id)

  markDirty()
  ElMessage.success(`已粘贴 ${newNodes.length} 个节点`)
}

// 快捷键
function onKeyDown(event: KeyboardEvent) {
  if (event.ctrlKey || event.metaKey) {
    switch (event.key) {
      case 'c':
        copySelected()
        break
      case 'v':
        pasteClipboard()
        break
      case 'a':
        selectAll()
        break
    }
  }
}
```

---

## 6. 撤销/重做

### 6.1 UndoManager 实现

```typescript
// webui/src/stores/undoManager.ts

import { ref } from 'vue'

interface Command {
  type: string
  data: any
  undo: () => void
  redo: () => void
}

export class UndoManager {
  private undoStack: Command[] = []
  private redoStack: Command[] = []
  private maxSize: number

  constructor(maxSize = 50) {
    this.maxSize = maxSize
  }

  execute(command: Command) {
    command.do?.()
    this.undoStack.push(command)
    this.redoStack = [] // 清空重做栈

    // 限制栈大小
    if (this.undoStack.length > this.maxSize) {
      this.undoStack.shift()
    }
  }

  undo(): boolean {
    const command = this.undoStack.pop()
    if (!command) return false

    command.undo()
    this.redoStack.push(command)
    return true
  }

  redo(): boolean {
    const command = this.redoStack.pop()
    if (!command) return false

    command.redo()
    this.undoStack.push(command)
    return true
  }

  canUndo(): boolean {
    return this.undoStack.length > 0
  }

  canRedo(): boolean {
    return this.redoStack.length > 0
  }

  clear() {
    this.undoStack = []
    this.redoStack = []
  }
}
```

### 6.2 命令实现

```typescript
// 添加节点命令
function createAddNodeCommand(node: CanvasNode): Command {
  return {
    type: 'ADD_NODE',
    data: { node },
    undo: () => {
      removeNodes([node.id])
    },
    redo: () => {
      addNodes([node])
    }
  }
}

// 删除节点命令
function createRemoveNodeCommand(node: CanvasNode, edges: CanvasEdge[]): Command {
  return {
    type: 'REMOVE_NODE',
    data: { node, edges },
    undo: () => {
      addNodes([node])
      addEdges(edges)
    },
    redo: () => {
      removeEdges(edges)
      removeNodes([node.id])
    }
  }
}

// 添加边命令
function createAddEdgeCommand(edge: CanvasEdge): Command {
  return {
    type: 'ADD_EDGE',
    data: { edge },
    undo: () => {
      removeEdges([edge.id])
    },
    redo: () => {
      addEdges([edge])
    }
  }
}

// 移动节点命令
function createMoveNodeCommand(
  nodeId: string,
  oldPosition: { x: number; y: number },
  newPosition: { x: number; y: number }
): Command {
  return {
    type: 'MOVE_NODE',
    data: { nodeId, oldPosition, newPosition },
    undo: () => {
      updateNodePosition(nodeId, oldPosition)
    },
    redo: () => {
      updateNodePosition(nodeId, newPosition)
    }
  }
}

// 更新节点数据命令
function createUpdateNodeDataCommand(
  nodeId: string,
  oldData: any,
  newData: any
): Command {
  return {
    type: 'UPDATE_NODE_DATA',
    data: { nodeId, oldData, newData },
    undo: () => {
      updateNodeData(nodeId, oldData)
    },
    redo: () => {
      updateNodeData(nodeId, newData)
    }
  }
}
```

### 6.3 集成到画布

```typescript
// webui/src/components/rule-canvas/CanvasRenderer.vue

import { UndoManager, createAddNodeCommand, createRemoveNodeCommand } from '@/stores/undoManager'

const undoManager = new UndoManager(50)

// 快捷键处理
function onKeyDown(event: KeyboardEvent) {
  if (event.ctrlKey || event.metaKey) {
    switch (event.key) {
      case 'z':
        if (event.shiftKey) {
          undoManager.redo()
        } else {
          undoManager.undo()
        }
        event.preventDefault()
        break
      case 'y':
        undoManager.redo()
        event.preventDefault()
        break
    }
  }
}

// 添加节点时记录命令
function onDropEvent(event: DragEvent) {
  const nodeType = event.dataTransfer?.getData('nodeType')
  if (!nodeType) return

  const position = getDropPosition(event)
  const newNode = createNode(nodeType, position)

  // 执行添加命令
  const command = createAddNodeCommand(newNode)
  undoManager.execute(command)

  markDirty()
}

// 删除节点时记录命令
function deleteSelected() {
  if (selectedNodes.value.length === 0) return

  for (const nodeId of selectedNodes.value) {
    const node = nodes.value.find(n => n.id === nodeId)
    const connectedEdges = edges.value.filter(
      e => e.source === nodeId || e.target === nodeId
    )

    const command = createRemoveNodeCommand(node!, connectedEdges)
    undoManager.execute(command)
  }

  selectedNodes.value = []
  markDirty()
}
```

---

## 7. 右键菜单

### 7.1 ContextMenu 组件

```vue
<!-- webui/src/components/rule-canvas/ContextMenu.vue -->

<template>
  <Teleport to="body">
    <div
      v-if="visible"
      class="context-menu"
      :style="{ left: position.x + 'px', top: position.y + 'px' }"
      @click.stop
    >
      <!-- 画布菜单 -->
      <template v-if="context === 'pane'">
        <div class="menu-item" @click="onPaste">
          <SvgIcon name="paste" /> 粘贴
        </div>
        <div class="menu-item" @click="onSelectAll">
          <SvgIcon name="select-all" /> 全选
        </div>
        <div class="menu-divider"></div>
        <div class="menu-item" @click="onFitView">
          <SvgIcon name="fit-view" /> 适应画布
        </div>
      </template>

      <!-- 节点菜单 -->
      <template v-else-if="context === 'node'">
        <div class="menu-item" @click="onCopy">
          <SvgIcon name="copy" /> 复制
        </div>
        <div class="menu-item" @click="onDuplicate">
          <SvgIcon name="duplicate" /> 复制并粘贴
        </div>
        <div class="menu-divider"></div>
        <div class="menu-item danger" @click="onDelete">
          <SvgIcon name="delete" /> 删除
        </div>
      </template>

      <!-- 边菜单 -->
      <template v-else-if="context === 'edge'">
        <div class="menu-item danger" @click="onDeleteEdge">
          <SvgIcon name="delete" /> 删除连线
        </div>
      </template>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from 'vue'

const props = defineProps<{
  visible: boolean
  position: { x: number; y: number }
  context: 'pane' | 'node' | 'edge'
  targetId?: string
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'paste'): void
  (e: 'select-all'): void
  (e: 'fit-view'): void
  (e: 'copy'): void
  (e: 'duplicate'): void
  (e: 'delete'): void
  (e: 'delete-edge'): void
}>()

function onPaste() { emit('paste'); emit('close') }
function onSelectAll() { emit('select-all'); emit('close') }
function onFitView() { emit('fit-view'); emit('close') }
function onCopy() { emit('copy'); emit('close') }
function onDuplicate() { emit('duplicate'); emit('close') }
function onDelete() { emit('delete'); emit('close') }
function onDeleteEdge() { emit('delete-edge'); emit('close') }

// 点击其他地方关闭菜单
function onClickOutside(event: MouseEvent) {
  emit('close')
}

onMounted(() => {
  document.addEventListener('click', onClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', onClickOutside)
})
</script>

<style scoped>
.context-menu {
  position: fixed;
  z-index: 9999;
  min-width: 160px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 4px 0;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  font-size: 13px;
  cursor: pointer;
  transition: background 0.15s;
}

.menu-item:hover {
  background: var(--bg-hover);
}

.menu-item.danger {
  color: var(--accent-red);
}

.menu-divider {
  height: 1px;
  background: var(--border-color);
  margin: 4px 0;
}
</style>
```

### 7.2 右键事件处理

```typescript
// webui/src/components/rule-canvas/CanvasRenderer.vue

const contextMenu = ref({
  visible: false,
  position: { x: 0, y: 0 },
  context: 'pane' as 'pane' | 'node' | 'edge',
  targetId: ''
})

function onPaneContextMenu(event: MouseEvent) {
  event.preventDefault()
  contextMenu.value = {
    visible: true,
    position: { x: event.clientX, y: event.clientY },
    context: 'pane'
  }
}

function onNodeContextMenu(event: NodeContextMenuEvent) {
  event.preventDefault()
  contextMenu.value = {
    visible: true,
    position: { x: event.event.clientX, y: event.event.clientY },
    context: 'node',
    targetId: event.node.id
  }

  // 选中右键点击的节点
  selectedNodes.value = [event.node.id]
}

function onEdgeContextMenu(event: EdgeContextMenuEvent) {
  event.preventDefault()
  contextMenu.value = {
    visible: true,
    position: { x: event.event.clientX, y: event.event.clientY },
    context: 'edge',
    targetId: event.edge.id
  }
}

function closeContextMenu() {
  contextMenu.value.visible = false
}

// 节点右键菜单操作
async function onContextMenuCopy() {
  selectedNodes.value = [contextMenu.value.targetId!]
  copySelected()
}

async function onContextMenuDuplicate() {
  selectedNodes.value = [contextMenu.value.targetId!]
  await copySelected()
  await pasteClipboard()
}

function onContextMenuDelete() {
  selectedNodes.value = [contextMenu.value.targetId!]
  deleteSelected()
}

// 边右键菜单操作
function onContextMenuDeleteEdge() {
  const edge = edges.value.find(e => e.id === contextMenu.value.targetId)
  if (edge) {
    clearNodeConnection(edge.target, edge.targetHandle)
    removeEdges([edge.id])
    markDirty()
  }
}
```

---

## 8. 状态管理

### 8.1 Pinia Store

```typescript
// webui/src/stores/ruleCanvas.ts

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useVueFlow } from '@vue-flow/core'

export const useRuleCanvasStore = defineStore('ruleCanvas', () => {
  // 节点和边
  const nodes = ref<CanvasNode[]>([])
  const edges = ref<CanvasEdge[]>([])

  // 选择状态
  const selectedNodeIds = ref<string[]>([])

  // 画布配置
  const snapGrid = ref(true)
  const showGrid = ref(true)
  const showMiniMap = ref(true)
  const zoomLevel = ref(1)

  // 脏标记（是否有未保存的更改）
  const isDirty = ref(false)

  // 选中节点
  const selectedNodes = computed(() =>
    nodes.value.filter(n => selectedNodeIds.value.includes(n.id))
  )

  // 添加节点
  function addNode(node: CanvasNode) {
    nodes.value = [...nodes.value, node]
    isDirty.value = true
  }

  // 删除节点
  function removeNode(nodeId: string) {
    nodes.value = nodes.value.filter(n => n.id !== nodeId)
    edges.value = edges.value.filter(e => e.source !== nodeId && e.target !== nodeId)
    isDirty.value = true
  }

  // 更新节点
  function updateNode(nodeId: string, updates: Partial<CanvasNode>) {
    const index = nodes.value.findIndex(n => n.id === nodeId)
    if (index !== -1) {
      nodes.value[index] = { ...nodes.value[index], ...updates }
      isDirty.value = true
    }
  }

  // 添加边
  function addEdge(edge: CanvasEdge) {
    edges.value = [...edges.value, edge]
    isDirty.value = true
  }

  // 删除边
  function removeEdge(edgeId: string) {
    edges.value = edges.value.filter(e => e.id !== edgeId)
    isDirty.value = true
  }

  // 标记为脏
  function markDirty() {
    isDirty.value = true
  }

  // 标记为干净
  function markClean() {
    isDirty.value = false
  }

  // 加载规则图
  function loadGraph(graphData: RuleGraph) {
    nodes.value = Object.values(graphData.nodes)
    edges.value = graphData.edges
    isDirty.value = false
  }

  // 获取图数据
  function getGraphData(): { nodes: Record<string, CanvasNode>; edges: CanvasEdge[] } {
    const nodesRecord: Record<string, CanvasNode> = {}
    for (const node of nodes.value) {
      nodesRecord[node.id] = node
    }
    return {
      nodes: nodesRecord,
      edges: edges.value
    }
  }

  return {
    // 状态
    nodes,
    edges,
    selectedNodeIds,
    snapGrid,
    showGrid,
    showMiniMap,
    zoomLevel,
    isDirty,
    // 计算属性
    selectedNodes,
    // 方法
    addNode,
    removeNode,
    updateNode,
    addEdge,
    removeEdge,
    markDirty,
    markClean,
    loadGraph,
    getGraphData
  }
})
```

---

## 9. 验收检查清单

### 9.1 拖拽交互
- [ ] 左侧面板显示 6 类节点
- [ ] 节点可拖拽到画布
- [ ] 放置位置正确（鼠标位置转换为画布坐标）
- [ ] 新节点自动生成唯一 ID

### 9.2 连接交互
- [ ] 从输出端口拖出连接线
- [ ] 类型匹配时允许连接
- [ ] 类型不匹配时显示警告
- [ ] 删除边时更新节点连接信息

### 9.3 操作交互
- [ ] Delete 键删除选中节点和连接的边
- [ ] Ctrl+C 复制选中节点
- [ ] Ctrl+V 粘贴节点（位置偏移）
- [ ] Ctrl+Z 撤销（至少 20 步）
- [ ] Ctrl+Y 重做

### 9.4 画布交互
- [ ] 鼠标滚轮缩放
- [ ] 拖拽空白处平移画布
- [ ] 右键菜单正确显示
- [ ] 小地图可切换显示/隐藏

### 9.5 状态管理
- [ ] 节点/边变更后 isDirty = true
- [ ] 保存后 isDirty = false
- [ ] 离开页面时提醒未保存更改
