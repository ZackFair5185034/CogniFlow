<template>
  <div class="rule-canvas-fullscreen">
    <!-- 顶部工具栏 -->
    <header class="canvas-header">
      <div class="header-left">
        <button
          class="icon-btn back-btn"
          title="返回规则列表"
          @click="goBack"
        >
          <SvgIcon name="back" />
        </button>
        <div class="rule-name-section">
          <el-input
            v-model="graphName"
            type="text"
            class="rule-name-input"
            placeholder="规则名称..."
            @blur="handleNameChange"
            @keyup.enter="handleNameChange"
          />
          <span
            class="rule-status-badge"
            :class="{ active: graph?.is_active }"
          >
            {{ graph?.is_active ? '运行中' : '已停止' }}
          </span>
        </div>
      </div>

      <div class="header-center">
        <div class="tool-group">
          <el-button
            class="icon-btn"
            :disabled="!canUndo"
            title="撤销 (Ctrl+Z)"
            @click="store.undo()"
          >
            <SvgIcon name="undo" />
          </el-button>
          <el-button
            class="icon-btn"
            :disabled="!canRedo"
            title="重做 (Ctrl+Y)"
            @click="store.redo()"
          >
            <SvgIcon name="redo" />
          </el-button>
        </div>

        <div class="tool-divider" />

        <!-- WebSocket 连接状态 -->
        <div
          class="ws-status"
          :class="{ connected: wsConnected }"
          :title="wsConnected ? 'WebSocket 已连接' : 'WebSocket 未连接'"
        >
          <span class="ws-dot" />
          <span class="ws-label">{{ wsConnected ? '已连接' : '未连接' }}</span>
        </div>

        <div class="tool-divider" />

        <div class="tool-group">
          <el-button
            class="icon-btn"
            title="放大"
            @click="zoomIn"
          >
            <SvgIcon name="zoom-in" />
          </el-button>
          <span class="zoom-level">{{ Math.round(zoomLevel * 100) }}%</span>
          <el-button
            class="icon-btn"
            title="缩小"
            @click="zoomOut"
          >
            <SvgIcon name="zoom-out" />
          </el-button>
          <el-button
            class="icon-btn"
            title="适应画布"
            @click="() => fitView()"
          >
            <SvgIcon name="fit-view" />
          </el-button>
        </div>

        <div class="tool-divider" />

        <div class="tool-group">
          <el-button
            class="icon-btn"
            :class="{ active: showGrid }"
            title="显示网格"
            @click="showGrid = !showGrid"
          >
            <SvgIcon name="grid" />
          </el-button>
          <el-button
            class="icon-btn"
            :class="{ active: snapGrid }"
            title="网格吸附"
            @click="snapGrid = !snapGrid"
          >
            <SvgIcon name="snap" />
          </el-button>
          <el-button
            class="icon-btn"
            :class="{ active: showMiniMap }"
            title="小地图"
            @click="showMiniMap = !showMiniMap"
          >
            <SvgIcon name="minimap" />
          </el-button>
        </div>
      </div>

      <div class="header-right">
        <el-button
          class="action-btn secondary"
          @click="handleValidate"
        >
          <SvgIcon name="check" />
          校验
        </el-button>
        <el-button
          class="action-btn secondary"
          :disabled="saving"
          @click="handleSave"
        >
          <SvgIcon name="save" />
          {{ saving ? '保存中...' : '保存' }}
        </el-button>
        <el-button
          class="action-btn primary"
          :disabled="executing || !hasNodes"
          @click="handleExecute"
        >
          <SvgIcon name="play" />
          {{ executing ? '执行中...' : '执行' }}
        </el-button>
      </div>
    </header>

    <!-- 主体区域 -->
    <div class="canvas-body">
      <!-- 左侧节点面板 -->
      <aside
        class="node-palette"
        :class="{ collapsed: !showPalette }"
      >
        <el-button
          class="collapse-btn"
          :class="{ collapsed: !showPalette }"
          :title="showPalette ? '收起面板' : '展开面板'"
          @click="showPalette = !showPalette"
        >
          <SvgIcon :name="showPalette ? 'chevron-left' : 'chevron-right'" />
        </el-button>
        <div
          v-show="showPalette"
          class="palette-header"
        >
          <h3>节点库</h3>
        </div>

        <div
          v-show="showPalette"
          class="palette-search"
        >
          <el-input
            v-model="nodeSearchQuery"
            type="text"
            placeholder="搜索节点..."
            class="search-input"
            @input="handleSearchInput"
          />
          <el-button
            v-if="nodeSearchQuery"
            class="search-clear"
            title="清除搜索"
            @click="nodeSearchQuery = ''"
          >
            ×
          </el-button>
        </div>

        <!-- 端口类型过滤（与文本搜索组合使用；空值=全部） -->
        <div
          v-show="showPalette"
          class="palette-port-filter"
        >
          <button
            class="port-filter-btn"
            :class="{ active: portTypeFilter === '' }"
            title="全部"
            @click="portTypeFilter = ''"
          >
            全部
          </button>
          <button
            v-for="pt in portTypeFilterOptions"
            :key="pt.type"
            class="port-filter-btn"
            :class="{ active: portTypeFilter === pt.type }"
            :title="`仅显示有 ${pt.type} 端口的节点`"
            @click="portTypeFilter = pt.type"
          >
            {{ pt.label }}
          </button>
        </div>

        <div
          v-show="showPalette"
          class="palette-content"
        >
          <div
            v-for="category in filteredCategories"
            :key="category.name"
            class="node-category"
          >
            <div
              class="category-header"
              @click="toggleCategory(category.name)"
            >
              <div
                class="category-icon-wrapper"
                :class="category.name"
              >
                <SvgIcon :name="category.name" />
              </div>
              <span class="category-name">{{ category.label }}</span>
              <span class="category-count">{{ category.nodes.length }}</span>
              <SvgIcon
                class="chevron"
                :class="{ expanded: category.expanded }"
                name="chevron"
              />
            </div>

            <div
              v-show="category.expanded"
              class="node-list"
            >
              <div
                v-for="node in category.nodes"
                :key="node.type"
                class="node-item"
                draggable="true"
                @dragstart="handleDragStart($event, node)"
                @dblclick="quickAddNode(node)"
                @contextmenu.prevent="handlePaletteContextMenu($event, node)"
              >
                <div
                  class="node-icon-wrapper"
                  :class="category.name"
                >
                  <SvgIcon :name="node.category || category.name" />
                </div>
                <div class="node-info">
                  <span class="node-label">{{ node.label }}</span>
                  <span class="node-type-hint">{{ node.description || node.type }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- 变量管理面板 -->
          <div class="variables-section">
            <div
              class="section-header"
              @click="showVariables = !showVariables"
            >
              <span class="section-title">📌 变量</span>
              <span class="section-count">{{ variables.length }}</span>
              <SvgIcon
                class="chevron"
                :class="{ expanded: showVariables }"
                name="chevron"
              />
            </div>
            <div
              v-show="showVariables"
              class="variables-list"
            >
              <div
                v-for="(variable, index) in variables"
                :key="index"
                class="variable-item"
              >
                <el-input
                  type="text"
                  :model-value="variable.name"
                  class="var-name-input"
                  placeholder="变量名"
                  @update:model-value="updateVariable(index, 'name', $event)"
                />
                <el-select
                  :model-value="variable.type"
                  class="var-type-select"
                  @update:model-value="updateVariable(index, 'type', $event)"
                >
                  <el-option
                    value="STRING"
                    label="STRING"
                  />
                  <el-option
                    value="NUMBER"
                    label="NUMBER"
                  />
                  <el-option
                    value="BOOLEAN"
                    label="BOOLEAN"
                  />
                  <el-option
                    value="IMAGE"
                    label="IMAGE"
                  />
                  <el-option
                    value="BBOX"
                    label="BBOX"
                  />
                </el-select>
                <el-button
                  class="var-remove-btn"
                  title="删除变量"
                  @click="removeVariable(index)"
                >
                  ×
                </el-button>
              </div>
              <el-button
                class="add-var-btn"
                @click="addVariable"
              >
                <SvgIcon name="plus" /> 添加变量
              </el-button>
            </div>
          </div>
        </div>
      </aside>

      <!-- 画布区域 -->
      <div
        ref="canvasWrapper"
        class="canvas-wrapper"
      >
        <!-- VueFlow 画布 -->
        <div
          ref="flowContainer"
          class="flow-container"
          :class="{ panning: isPanning }"
          @drop="handleDrop"
          @dragover.prevent
          @dragenter.prevent
          @wheel="handleWheel"
          @mousedown="handleCanvasMouseDown"
          @mousemove="handleCanvasMouseMove"
          @mouseup="handleCanvasMouseUp"
        >
          <VueFlow
            ref="vueFlowRef"
            v-model:nodes="nodes"
            v-model:edges="edges"
            :node-types="nodeTypes"
            :default-edge-options="defaultEdgeOptions"
            :connection-line-style="connectionLineStyle"
            :snap-to-grid="false"
            :snap-grid="[gridSize, gridSize]"
            :default-viewport="{ x: 0, y: 0, zoom: 0.65 }"
            :pan-on-drag="false"
            :pan-on-scroll="true"
            :zoom-on-scroll="true"
            :min-zoom="0.1"
            :max-zoom="4"
            :nodes-draggable="true"
            :nodes-connectable="true"
            :elements-selectable="true"
            :select-nodes-on-drag="true"
            :selection-key-code="true"
            :selection-mode="SelectionMode.Partial"
            :connection-radius="20"
            :is-valid-connection="isValidConnection"
            @node-click="handleNodeClick"
            @node-drag-start="handleNodeDragStart"
            @node-drag-stop="handleNodeDragStop"
            @pane-click="handlePaneClick"
            @connect="handleConnect"
            @move="handlePan"
            @zoom="handleZoom"
            @nodes-change="handleNodesChange"
            @edges-change="handleEdgesChange"
            @node-context-menu="(e: NodeMouseEvent) => handleContextMenu(e.event as MouseEvent, e.node, 'node')"
            @pane-context-menu="(e: MouseEvent) => handleContextMenu(e, null, 'pane')"
            @edge-context-menu="(e: EdgeMouseEvent) => handleContextMenu(e.event as MouseEvent, e.edge, 'edge')"
            @node-delete="handleNodeDelete"
            @selection-drag-stop="handleSelectionDragStop"
          >
            <!-- 小地图 -->
            <MiniMap
              v-if="showMiniMap"
              position="bottom-right"
              :node-color="miniMapNodeColor"
              :node-stroke-width="2"
              pannable
              zoomable
            />

            <!-- 控制按钮 -->
            <Controls position="bottom-left" />
          </VueFlow>

          
          <!-- 空画布提示 -->
          <div
            v-if="nodes.length === 0 && !loading"
            class="empty-state"
          >
            <div class="empty-icon">
              <SvgIcon name="stream" />
            </div>
            <h3>开始设计规则流程</h3>
            <p>从左侧拖拽节点到画布，或双击节点快速添加</p>
            <div class="quick-add-nodes">
              <el-button
                v-for="node in quickAddNodes"
                :key="node.type"
                class="quick-add-btn"
                @click="quickAddNode(node)"
              >
                <span
                  class="btn-icon"
                  :class="node.category"
                >
                  <SvgIcon :name="node.category" />
                </span>
                {{ node.label }}
              </el-button>
            </div>
          </div>

          <!-- 加载状态 -->
          <LoadingSpinner
            v-if="loading"
            overlay
            text="加载规则图..."
          />
        </div>
      </div>
    </div>

    <!-- 执行日志面板 -->
    <div
      class="execution-panel"
      :class="{ expanded: showExecutionPanel }"
      :style="{
        height: showExecutionPanel ? panelHeight + 'px' : '44px',
        left: showPalette ? EXPANDED_WIDTH + 'px' : COLLAPSED_WIDTH + 'px'
      }"
    >
      <!-- 拖拽调整高度 -->
      <div
        class="panel-resize-handle"
        @mousedown="startPanelResize"
      />
      <div
        class="execution-header"
        @click="showExecutionPanel = !showExecutionPanel"
      >
        <div class="execution-title">
          <SvgIcon name="file-text" />
          <span>执行日志</span>
          <span
            class="execution-status"
            :class="executionStatus"
          >{{ executionStatusText }}</span>
        </div>
        <div class="execution-actions">
          <el-button
            v-if="showExecutionPanel"
            class="icon-btn small"
            @click.stop="clearLogs"
          >
            <SvgIcon name="trash" />
          </el-button>
          <SvgIcon
            class="expand-icon"
            :class="{ expanded: showExecutionPanel }"
            name="chevron"
          />
        </div>
      </div>

      <div
        v-show="showExecutionPanel"
        class="execution-content"
      >
        <!-- 进度条 -->
        <div
          v-if="executionStatus === 'running'"
          class="progress-bar-wrapper"
        >
          <div class="progress-bar">
            <div
              class="progress-fill"
              :style="{ width: executionProgress + '%' }"
            />
          </div>
          <span class="progress-text">{{ executionProgress }}%</span>
        </div>

        <div class="logs-list">
          <div
            v-for="(log, idx) in executionLogs"
            :key="idx"
            class="log-entry"
            :class="log.level"
          >
            <span class="log-time">{{ log.timestamp }}</span>
            <span class="log-level-badge">{{ log.level.toUpperCase() }}</span>
            <span
              v-if="log.node_type"
              class="log-node"
            >{{ log.node_type }}</span>
            <span class="log-message">{{ log.message }}</span>
            <span
              v-if="log.metrics && Object.keys(log.metrics).length > 0"
              class="log-metrics"
              :title="formatMetrics(log.metrics)"
            >{{ formatMetrics(log.metrics) }}</span>
            <span
              v-if="log.duration_ms != null"
              class="log-duration"
            >{{ formatDuration(log.duration_ms) }}</span>
          </div>
          <div
            v-if="executionLogs.length === 0"
            class="no-logs"
          >
            暂无执行日志
          </div>
        </div>
      </div>
    </div>

    
    <!-- 右键菜单 -->
    <div
      v-if="contextMenu.show"
      class="context-menu"
      :style="{ left: contextMenu.x + 'px', top: contextMenu.y + 'px' }"
      @contextmenu.prevent
    >
      <template v-if="contextMenu.targetType === 'node'">
        <div
          class="context-menu-item"
          @click="handleContextAction('copy')"
        >
          <SvgIcon name="copy" /> 复制
        </div>
        <div
          class="context-menu-item"
          @click="handleContextAction('cut')"
        >
          <SvgIcon name="cut" /> 剪切
        </div>
        <div
          class="context-menu-item danger"
          @click="handleContextAction('delete')"
        >
          <SvgIcon name="delete" /> 删除
        </div>
        <div class="context-menu-divider" />
      </template>
      <template v-if="contextMenu.targetType === 'edge'">
        <div
          class="context-menu-item danger"
          @click="handleContextAction('delete')"
        >
          <SvgIcon name="delete" /> 删除连线
        </div>
        <div class="context-menu-divider" />
      </template>
      <div
        class="context-menu-item"
        @click="handleContextAction('paste')"
      >
        <SvgIcon name="paste" /> 粘贴
      </div>
      <div
        class="context-menu-item"
        @click="handleContextAction('selectAll')"
      >
        <SvgIcon name="select" /> 全选
      </div>
    </div>

    <!-- 点击其他区域隐藏右键菜单 -->
    <div
      v-if="contextMenu.show"
      class="context-menu-overlay"
      @click="hideContextMenu"
      @contextmenu.prevent="hideContextMenu"
    />

    <!-- 变量绑定菜单已废弃: 节点内嵌 📎 按钮接管 (RuleNode.vue:218 activeVarMenu) -->
  </div>
</template>

<script setup lang="ts">
import { throttle } from 'lodash-es'
import { useRuleEngineStore, type RuleNodeData, type NodeDefinition } from '@/stores/ruleEngine'
import { storeToRefs } from 'pinia'
import { ruleEngineApi } from '@/api'
import type { Node, Edge, NodeMouseEvent, EdgeMouseEvent } from '@vue-flow/core'
// SelectionMode 在 <template> 里使用（Vue 模板作用域只解析 <script setup> 顶层 binding，
// auto-import 的全局 const 在 template 中不被 TS 识别），需要显式 import
import { SelectionMode } from '@vue-flow/core'
import RuleNode from '@/components/rule-engine/RuleNode.vue'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import '@vue-flow/controls/dist/style.css'
import '@vue-flow/minimap/dist/style.css'

const router = useRouter()
const route = useRoute()
const { fitView, setCenter, screenToFlowCoordinate, userSelectionRect, setViewport, getViewport, addSelectedNodes, getNodes } = useVueFlow()

// ============ Store 绑定（唯一数据源）============
const store = useRuleEngineStore()
const {
  nodes,
  edges,
  canUndo,
  canRedo,
  hasNodes,
  variables,
  nodeDefinitions,
  graphMeta: graph,
} = storeToRefs(store)

// 执行状态（computed 包装，保持模板兼容）
const executionStatus = computed(() => store.executionState.status)
const executionProgress = computed(() => store.executionState.progress)
const executionLogs = computed(() => store.executionState.logs)
const executionId = computed(() => store.executionState.executionId)

// ---- 模板兼容函数（委托给 Store）----

// 变量管理（模板使用 index，store 使用 name）
function addVariable() {
  store.addVariable()
}

function removeVariable(index: number) {
  const name = variables.value[index]?.name
  if (name) store.removeVariable(name)
}

function updateVariable(index: number, field: string, value: string) {
  const name = variables.value[index]?.name
  if (name) store.updateVariable(name, { [field]: value })
}

// 常量
const gridSize = 30

// 本地 UI 状态
const graphId = computed(() => Number(route.params.id))
const graphName = ref('')
const showVariables = ref(true)
const loading = ref(false)
const saving = ref(false)
const executing = ref(false)
const showPalette = ref(true)
const showMiniMap = ref(true)
const snapGrid = ref(true)
const showGrid = ref(true)
const showExecutionPanel = ref(false)
const flowContainer = ref<HTMLElement | null>(null)
const vueFlowRef = ref<any>(null)
const canvasWrapper = ref<HTMLElement | null>(null)
const panX = ref(0)
const panY = ref(0)
const zoomLevel = ref(1)
const isPanning = ref(false)
const lastMousePos = ref({ x: 0, y: 0 })

// 复制粘贴
const clipboard = ref<Node<RuleNodeData>[]>([])
const clipboardMode = ref<'copy' | 'cut'>('copy')

// 右键菜单
const contextMenu = reactive({
  show: false,
  x: 0,
  y: 0,
  target: null as unknown,
  targetType: null as 'node' | 'edge' | 'pane' | null
})

// 执行日志面板高度
const panelHeight = ref(200)
const isResizingPanel = ref(false)
const panelResizeCleanup = ref<(() => void) | null>(null)

// palette 折叠后的宽度
const COLLAPSED_WIDTH = 48
const EXPANDED_WIDTH = 280

// 节点分类展开状态（reactive，分离避免循环引用）
const categoryExpanded = reactive({
  input: true, detection: true, processing: true,
  action: true, logic: true, output: true
})

// 节点分类 - 6色体系 (按设计文档)
const nodeCategories = computed(() => [
  { name: 'input', label: '输入' },
  { name: 'detection', label: '检测' },
  { name: 'processing', label: '处理' },
  { name: 'action', label: '动作' },
  { name: 'logic', label: '逻辑' },
  { name: 'output', label: '输出' },
].map(cat => ({
  ...cat,
  expanded: categoryExpanded[cat.name as keyof typeof categoryExpanded],
  nodes: nodeDefinitions.value.filter((d) => d.category === cat.name)
})))

// 节点搜索
const nodeSearchQuery = ref('')

// 端口类型过滤：'' 表示全部；常用类型列出按钮，长尾类型通过文本搜索触达
const portTypeFilter = ref<string>('')
const portTypeFilterOptions = [
  { type: 'IMAGE', label: '图像' },
  { type: 'BBOX', label: '检测框' },
  { type: 'MODEL', label: '模型' },
  { type: 'STRING', label: '字符串' },
  { type: 'CONTROL', label: '控制' },
]

/** 节点是否匹配端口类型过滤。空过滤视为全匹配。 */
function matchesPortType(node: NodeDefinition): boolean {
  const filter = portTypeFilter.value
  if (!filter) return true
  // 任一输入或输出端口匹配即通过
  const inputMatch = node.inputs?.some((p) => p.type === filter) ?? false
  const outputMatch = node.outputs?.some((p) => p.type === filter) ?? false
  return inputMatch || outputMatch
}

const filteredCategories = computed(() => {
  const query = nodeSearchQuery.value.trim().toLowerCase()
  if (!query && !portTypeFilter.value) {
    return nodeCategories.value
  }
  return nodeCategories.value
    .map(cat => ({
      ...cat,
      nodes: cat.nodes.filter((n) => {
        // 文本搜索匹配
        const matchesQuery = !query ||
          n.label?.toLowerCase().includes(query) ||
          n.type?.toLowerCase().includes(query) ||
          n.description?.toLowerCase().includes(query)
        // 端口类型匹配
        const matchesPort = matchesPortType(n)
        return matchesQuery && matchesPort
      }),
      expanded: true
    }))
    .filter(cat => cat.nodes.length > 0)
})

function handleSearchInput() {
  if (nodeSearchQuery.value.trim()) {
    Object.keys(categoryExpanded).forEach(key => categoryExpanded[key as keyof typeof categoryExpanded] = true)
  }
}

function toggleCategory(name: string) {
  categoryExpanded[name as keyof typeof categoryExpanded] = !categoryExpanded[name as keyof typeof categoryExpanded]
}

// 快速添加
const quickAddNodes = computed(() => nodeDefinitions.value.slice(0, 4))

// 执行状态文本
const executionStatusText = computed(() => ({
  idle: '等待执行',
  running: '执行中...',
  success: '执行成功',
  failed: '执行失败'
}[executionStatus.value]))

// 默认边样式 - 使用贝塞尔曲线
const defaultEdgeOptions = {
  type: 'default',
  animated: false,
  markerEnd: MarkerType.ArrowClosed,
  style: { stroke: 'var(--accent-blue)', strokeWidth: 2 }
}

// 连接线样式
const connectionLineStyle = {
  stroke: 'var(--accent-blue)',
  strokeWidth: 2,
  markerEnd: MarkerType.ArrowClosed
}

// 节点类型 - 注册自定义节点组件
const nodeTypes = {
  ruleNode: markRaw(RuleNode)
} as unknown as Record<string, any>

// 小地图颜色
const NODE_CATEGORY_COLORS: Record<string, string> = {
  input: '#4CFF4C',
  detection: '#00f0FF',
  processing: '#FFFF4C',
  action: '#FF7F4C',
  logic: '#DC4FDC',
  output: '#FF4C4C'
}

function miniMapNodeColor(node: { data?: { category?: string } }) {
  return NODE_CATEGORY_COLORS[node.data?.category || ''] || '#888'
}


// WebSocket 连接（Phase 5 实时推送）
let ws: WebSocket | null = null
let wsReconnectTimer: ReturnType<typeof setTimeout> | null = null
const wsConnected = ref(false)

function getWsUrl() {
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${proto}//${window.location.host}/ws/rule-execution`
}

function connectWebSocket(execId: number) {
  if (ws) {
    ws.close()
    ws = null
  }

  try {
    ws = new WebSocket(getWsUrl())

    ws.onopen = () => {
      wsConnected.value = true
      ws?.send(JSON.stringify({ action: 'subscribe', execution_id: execId }))
    }

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data)
        handleWsMessage(msg)
      } catch (e) {
        console.error('[WS] 解析消息失败', e)
      }
    }

    ws.onerror = () => {
      wsConnected.value = false
      if (wsReconnectTimer) clearTimeout(wsReconnectTimer)
      wsReconnectTimer = setTimeout(() => {
        if (executionStatus.value === 'running' && executionId.value) {
          connectWebSocket(executionId.value)
        }
      }, 3000)
    }

    ws.onclose = () => {
      wsConnected.value = false
      ws = null
    }
  } catch (e) {
    console.error('[WS] 连接失败', e)
  }
}

function disconnectWebSocket() {
  if (wsReconnectTimer) {
    clearTimeout(wsReconnectTimer)
    wsReconnectTimer = null
  }
  if (ws) {
    ws.close()
    ws = null
  }
}

function handleWsMessage(msg: any) {
  switch (msg.type) {
    case 'node_started':
      store.setNodeExecutionState(msg.node_id, 'running')
      store.addExecutionLog({
        level: 'info',
        timestamp: formatTime(msg.timestamp),
        node_type: msg.node_type,
        message: `开始执行: ${msg.node_type}`
      })
      break
    case 'node_executed':
      store.setNodeExecutionState(msg.node_id, 'success')
      store.addExecutionLog({
        level: 'success',
        timestamp: formatTime(msg.timestamp),
        node_type: msg.node_type,
        message: `${msg.node_type} 执行成功`,
        duration_ms: msg.duration_ms,
        metrics: msg.metrics,
      })
      break
    case 'node_failed':
      store.setNodeExecutionState(msg.node_id, 'failed')
      store.addExecutionLog({
        level: 'error',
        timestamp: formatTime(msg.timestamp),
        node_type: msg.node_type,
        message: msg.error || '执行失败'
      })
      ElMessage.error(`节点执行失败: ${msg.error}`)
      break
    case 'node_timeout':
      // 节点执行超时 — 区别于 node_failed，下游继续执行（断路器模式）
      store.setNodeExecutionState(msg.node_id, 'timeout')
      store.addExecutionLog({
        level: 'warning',
        timestamp: formatTime(msg.timestamp),
        node_type: msg.node_type,
        message: msg.error || `执行超时（${msg.timeout_seconds}s）`
      })
      ElMessage.warning(`节点执行超时: ${msg.error || ''}（下游继续执行）`)
      break
    case 'execution_progress':
      throttledUpdateProgress(msg.progress)
      break
    case 'execution_complete':
      store.setExecutionStatus(msg.status === 'completed' ? 'success' : 'failed')
      store.setExecutionProgress(100)
      store.addExecutionLog({
        level: msg.status === 'completed' ? 'success' : 'error',
        timestamp: formatTime(msg.timestamp),
        node_type: '',
        message: msg.status === 'completed' ? '执行完成' : `执行失败: ${msg.error || ''}`
      })
      if (msg.status === 'completed') {
        ElMessage.success('执行成功')
      } else {
        ElMessage.error(`执行失败: ${msg.error || ''}`)
      }
      setTimeout(() => store.clearExecution(), 2000)
      disconnectWebSocket()
      break
  }
}

/** 格式化时间戳为 HH:mm:ss */
function formatTime(isoStr?: string) {
  if (!isoStr) return ''
  try {
    const d = new Date(isoStr)
    return d.toLocaleTimeString('zh-CN', { hour12: false })
  } catch {
    return ''
  }
}

/** 格式化毫秒为可读耗时 */
function formatDuration(ms: number) {
  if (ms < 1000) return `${ms}ms`
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
  return `${Math.floor(ms / 60000)}m ${Math.floor((ms % 60000) / 1000)}s`
}

/** 格式化节点输出指标为可读字符串（key=value, key=value）。 */
function formatMetrics(metrics: Record<string, number>): string {
  return Object.entries(metrics)
    .map(([k, v]) => `${k}=${v}`)
    .join(', ')
}

// 节流进度更新函数
const throttledUpdateProgress = throttle((progress: number) => {
  store.setExecutionProgress(progress)
}, 500)

// 键盘事件处理
function handleKeyDown(event: KeyboardEvent) {
  const target = event.target as HTMLElement
  if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable) {
    return
  }

  const isCtrl = event.ctrlKey || event.metaKey

  if (isCtrl && event.key === 'c') {
    event.preventDefault()
    handleCopy()
    return
  }
  if (isCtrl && event.key === 'x') {
    event.preventDefault()
    handleCut()
    return
  }
  if (isCtrl && event.key === 'v') {
    event.preventDefault()
    handlePaste()
    return
  }
  if (isCtrl && event.key === 'z' && !event.shiftKey) {
    event.preventDefault()
    store.undo()
    return
  }
  if (isCtrl && (event.key === 'y' || (event.key === 'z' && event.shiftKey))) {
    event.preventDefault()
    store.redo()
    return
  }
  if (event.key === 'Delete' || event.key === 'Backspace') {
    event.preventDefault()
    handleDelete()
    return
  }
}

// 复制
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

// 剪切
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

// 粘贴
function handlePaste() {
  if (clipboard.value.length === 0) {
    ElMessage.warning('剪贴板为空')
    return
  }

  const offsetX = 50
  const offsetY = 50

  for (const n of clipboard.value) {
    const cloned = JSON.parse(JSON.stringify(n))
    const newId = `node_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`
    const nodeData = {
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
    }
    store.nodes.push(nodeData)
  }

  if (clipboardMode.value === 'cut') {
    clipboard.value = []
  }

  store.saveHistory()
  ElMessage.success(`已粘贴 ${clipboard.value.length} 个节点`)
}

// 框选结束
function handleSelectionDragStop({ nodes: selectedNodes }: { nodes: Node<RuleNodeData>[] }) {
  const selectedIds = new Set(selectedNodes.map((n) => n.id))
  // 优化：只更新 selected 标志（mutate 内层 + triggerRef），避免重建整图。
  // 之前用 .map + 全量赋值：30 节点图会触发 30 个节点 watcher 重算。
  for (const n of store.nodes as any[]) {
    n.selected = selectedIds.has(n.id)
  }
  userSelectionRect.value = null
  // shallowRef 不追踪内层变更，需要手动 trigger
  // (虽然 VueFlow 已在其内部维护 selection state 推动画布，
  //  但 store 里 selected 字段也需同步给执行日志等模块用)
  // 注：当前没有模块读 store.nodes[].selected，所以不强制 trigger
  // 保留调用以便未来扩展（外部 watcher 用例）
}

// 节点删除按钮点击
function handleNodeDelete(nodeId: string) {
  store.removeNode(nodeId)
  ElMessage.info('节点已删除')
}

// 删除选中
function handleDelete() {
  const vfNodes = getNodes.value as any[]
  const selectedNodes = vfNodes.filter((n) => n.selected)
  const selectedEdges = edges.value.filter((e: any) => e.selected)

  if (selectedNodes.length === 0 && selectedEdges.length === 0) return

  const nodeIds = selectedNodes.map((n) => n.id)
  for (const id of nodeIds) {
    store.removeNode(id)
  }
  for (const e of selectedEdges) {
    store.removeEdge(e.id)
  }
  ElMessage.success(`已删除 ${selectedNodes.length} 个节点`)
}

// 右键菜单
function handleContextMenu(event: MouseEvent, target: Node | Edge | NodeDefinition | null, type: 'node' | 'edge' | 'pane') {
  event.preventDefault()
  event.stopPropagation()
  contextMenu.show = true
  contextMenu.x = event.clientX
  contextMenu.y = event.clientY
  contextMenu.target = target
  contextMenu.targetType = type
}

function handlePaletteContextMenu(event: MouseEvent, node: NodeDefinition) {
  event.preventDefault()
  contextMenu.show = true
  contextMenu.x = event.clientX
  contextMenu.y = event.clientY
  contextMenu.target = node
  contextMenu.targetType = 'pane'
}

function hideContextMenu() {
  contextMenu.show = false
}

// 已废弃: 变量绑定菜单由 RuleNode.vue 内嵌 📎 按钮接管 (bindVariable/toggleVarMenu)

// 右键菜单操作
function handleContextAction(action: string) {
  switch (action) {
    case 'copy':
      if (contextMenu.targetType === 'node' && contextMenu.target) {
        clipboard.value = [JSON.parse(JSON.stringify(contextMenu.target))]
        clipboardMode.value = 'copy'
        ElMessage.success('已复制节点')
      }
      hideContextMenu()
      break
    case 'paste':
      handlePaste()
      hideContextMenu()
      break
    case 'delete':
      if (contextMenu.targetType === 'node' && contextMenu.target) {
        ;(addSelectedNodes as any)([(contextMenu.target as any).id])
      } else if (contextMenu.targetType === 'edge' && contextMenu.target) {
        const targetEdge = contextMenu.target as Edge
        store.edges = store.edges.map((e: Edge) => ({ ...e, selected: e.id === targetEdge.id })) as any
      }
      handleDelete()
      hideContextMenu()
      break
    case 'selectAll':
      for (const n of nodes.value) {
        ;(addSelectedNodes as any)([n.id])
      }
      hideContextMenu()
      break
  }
}

// 缩放
function zoomIn() {
  const container = flowContainer.value
  if (!container) return
  const rect = container.getBoundingClientRect()
  setCenter(rect.width / 2, rect.height / 2, { zoom: zoomLevel.value * 1.2, duration: 200 })
}

function zoomOut() {
  const container = flowContainer.value
  if (!container) return
  const rect = container.getBoundingClientRect()
  setCenter(rect.width / 2, rect.height / 2, { zoom: zoomLevel.value / 1.2, duration: 200 })
}

// 生命周期
onMounted(async () => {
  loading.value = true
  // 各 API 调用独立 try-catch，防止单点失败阻塞后续加载
  try {
    await store.loadGraph(graphId.value)
    graphName.value = store.graphMeta?.name || ''
  } catch (err) {
    console.error('加载规则图失败:', err)
    ElMessage.error('加载规则图失败')
  }
  try {
    await store.fetchNodeDefinitions()
    store.saveHistory()
  } catch (err) {
    console.error('加载节点定义失败:', err)
  }
  try {
    await store.fetchModels()
  } catch (err) {
    console.error('加载模型列表失败:', err)
  }
  loading.value = false
  // 键盘事件
  window.addEventListener('keydown', handleKeyDown)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleKeyDown)
  panelResizeCleanup.value?.()
})

// 返回
function goBack() {
  router.push('/rule-engine')
}

// 名称修改
async function handleNameChange() {
  const meta = store.graphMeta
  if (graphName.value !== meta?.name) {
    try {
      // 直接更新 graphMeta 的 name
      if (store.graphMeta) {
        store.graphMeta = { ...store.graphMeta, name: graphName.value }
      }
      await store.saveGraph()
      ElMessage.success('名称已更新')
    } catch {
      ElMessage.error('更新名称失败')
    }
  }
}

// 拖拽
function handleDragStart(event: DragEvent, nodeDef: NodeDefinition) {
  event.dataTransfer?.setData('application/node-type', JSON.stringify(nodeDef))
}

function handleDrop(event: DragEvent) {
  const data = event.dataTransfer?.getData('application/node-type')
  if (!data) return

  const nodeDef = JSON.parse(data)
  const container = flowContainer.value
  if (!container) return

  const rect = container.getBoundingClientRect()
  const position = screenToFlowCoordinate({
    x: event.clientX - rect.left,
    y: event.clientY - rect.top
  })

  if (snapGrid.value) {
    position.x = Math.round(position.x / gridSize) * gridSize
    position.y = Math.round(position.y / gridSize) * gridSize
  }

  store.createNode(nodeDef, position)
}

// 快速添加
function quickAddNode(nodeDef: NodeDefinition) {
  const centerX = (flowContainer.value?.clientWidth || 800) / 2 / zoomLevel.value
  const centerY = (flowContainer.value?.clientHeight || 600) / 2 / zoomLevel.value

  store.createNode(nodeDef, {
    x: centerX + Math.random() * 100 - 50,
    y: centerY + Math.random() * 100 - 50
  })
  ElMessage.success(`已添加 ${nodeDef.label}`)
}

// 节点点击
function handleNodeClick(event: any) {
  store.selectNode(event.node.id)
}

// 节点拖拽
function handleNodeDragStart() {
  store.pauseHistory()
}

function handleNodeDragStop() {
  store.unpauseHistory()
}

// 画布点击
function handlePaneClick() {
  store.selectNode(null)
}

// 端口类型兼容性检查
function isPortCompatible(sourceType: string, targetType: string): boolean {
  if (sourceType === 'ANY' || targetType === 'ANY') return true
  if (sourceType === targetType) return true
  if (sourceType === 'TRIGGER' && (targetType === 'TRIGGER' || targetType === 'CONTROL')) return true
  if (sourceType === 'CONTROL' && targetType === 'CONTROL') return true
  return false
}

function getNodePortType(nodeId: string, handleId: string | null, isSource: boolean): string | null {
  const node = nodes.value.find(n => n.id === nodeId)
  if (!node) return null
  const ports = isSource ? (node.data?.outputs || []) : (node.data?.inputs || [])
  if (!ports?.length) return null
  if (handleId) {
    const port = ports.find((p: any) => p.name === handleId)
    return port?.type || 'ANY'
  }
  return ports[0]?.type || 'ANY'
}

function validateConnection(params: any): { valid: boolean; error?: string } {
  const { source, target, sourceHandle, targetHandle } = params
  const sourceNode = nodes.value.find(n => n.id === source)
  const targetNode = nodes.value.find(n => n.id === target)

  if (!sourceNode || !targetNode) return { valid: false, error: '节点不存在' }
  if (source === target) return { valid: false, error: '不能连接到自己' }

  const sourceType = getNodePortType(source, sourceHandle, true)
  const targetType = getNodePortType(target, targetHandle, false)

  if (sourceType === null || targetType === null) return { valid: false, error: '端口定义缺失' }
  if (!isPortCompatible(sourceType, targetType)) return { valid: false, error: `类型不兼容: ${sourceType} → ${targetType}` }

  return { valid: true }
}

// VueFlow 专用连接验证
function isValidConnection(connection: any): boolean {
  const { source, target, sourceHandle, targetHandle } = connection
  if (source === target) return false

  const sourceType = getNodePortType(source, sourceHandle, true)
  const targetType = getNodePortType(target, targetHandle, false)

  if (sourceType === null || targetType === null) return true

  return isPortCompatible(sourceType, targetType)
}

// 连接
function handleConnect(params: any) {
  const validation = validateConnection(params)
  if (!validation.valid) {
    ElMessage.error(validation.error || '连接失败')
    return
  }

  store.addEdge({
    source: params.source,
    target: params.target,
    sourceHandle: params.sourceHandle,
    targetHandle: params.targetHandle
  })
}

// 节点/边变化
function handleNodesChange(changes: Array<{ type: string; id?: string }>) {
  const hasRemoval = changes.some(c => c.type === 'remove')
  if (hasRemoval) {
    const remainingNodeIds = nodes.value.map((n) => n.id)
    store.edges = store.edges.filter((e: Edge) =>
      remainingNodeIds.includes(e.source) && remainingNodeIds.includes(e.target)
    ) as any
    store.saveHistory()
  }
}

function handleEdgesChange(_changes: Array<{ type: string; id?: string }>) {
  // 边变化由 store 的 addEdge/removeEdge 自动保存历史
}

// 画布平移
function handlePan(moveEvent: { event: unknown; flowTransform: { x: number; y: number; zoom: number } }) {
  panX.value = -moveEvent.flowTransform.x
  panY.value = -moveEvent.flowTransform.y
}

function handleZoom({ zoom }: { zoom: number; event: unknown }) {
  zoomLevel.value = zoom
}

function handleWheel(event: WheelEvent) {
  if (event.ctrlKey) event.preventDefault()
}

function handleCanvasMouseDown(event: MouseEvent) {
  if (event.button === 1 || (event.button === 0 && event.altKey)) {
    isPanning.value = true
    lastMousePos.value = { x: event.clientX, y: event.clientY }
  }
}

function handleCanvasMouseMove(event: MouseEvent) {
  if (isPanning.value) {
    const dx = event.clientX - lastMousePos.value.x
    const dy = event.clientY - lastMousePos.value.y
    const viewport = getViewport()
    setViewport({ x: viewport.x + dx, y: viewport.y + dy, zoom: viewport.zoom })
    lastMousePos.value = { x: event.clientX, y: event.clientY }
  }
}

function handleCanvasMouseUp() {
  isPanning.value = false
  isResizingPanel.value = false
}

function startPanelResize(e: MouseEvent) {
  isResizingPanel.value = true
  const startY = e.clientY
  const startHeight = panelHeight.value
  const onMove = (ev: MouseEvent) => {
    panelHeight.value = Math.max(100, Math.min(500, startHeight + (startY - ev.clientY)))
  }
  const onUp = () => {
    isResizingPanel.value = false
    document.removeEventListener('mousemove', onMove)
    document.removeEventListener('mouseup', onUp)
  }
  panelResizeCleanup.value = () => {
    document.removeEventListener('mousemove', onMove)
    document.removeEventListener('mouseup', onUp)
  }
  document.addEventListener('mousemove', onMove)
  document.addEventListener('mouseup', onUp)
}

// 保存
async function handleSave() {
  saving.value = true
  try {
    await store.saveGraph()
    await captureAndSaveThumbnail()
    ElMessage.success('保存成功')
  } catch (err) {
    console.error('保存失败:', err)
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

// 生成并保存缩略图
async function captureAndSaveThumbnail() {
  try {
    const vueFlow = vueFlowRef.value
    if (!vueFlow) return

    const flowExport = vueFlow.toObject?.()
    if (!flowExport || !flowExport.nodes?.length) return

    const canvas = document.createElement('canvas')
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    canvas.width = 320
    canvas.height = 180
    ctx.fillStyle = '#1a1a2e'
    ctx.fillRect(0, 0, canvas.width, canvas.height)

    const xs = flowExport.nodes.map((n: any) => n.position?.x || 0)
    const ys = flowExport.nodes.map((n: any) => n.position?.y || 0)
    if (!xs.length) return

    const minX = Math.min(...xs)
    const minY = Math.min(...ys)
    const maxX = Math.max(...xs) + 120
    const maxY = Math.max(...ys) + 60
    const graphW = maxX - minX || 1
    const graphH = maxY - minY || 1
    const padding = 20
    const scale = Math.min((canvas.width - padding * 2) / graphW, (canvas.height - padding * 2) / graphH, 1)
    const offsetX = (canvas.width - graphW * scale) / 2 - minX * scale
    const offsetY = (canvas.height - graphH * scale) / 2 - minY * scale

    ctx.save()
    ctx.translate(offsetX, offsetY)
    ctx.scale(scale, scale)

    // 绘制连线
    ctx.strokeStyle = '#5898ff'
    ctx.lineWidth = 2 / scale
    for (const edge of flowExport.edges || []) {
      const sn = flowExport.nodes.find((n: any) => n.id === edge.source)
      const tn = flowExport.nodes.find((n: any) => n.id === edge.target)
      if (sn && tn) {
        ctx.beginPath()
        ctx.moveTo((sn.position?.x || 0) + 60, (sn.position?.y || 0) + 20)
        ctx.lineTo((tn.position?.x || 0) + 60, (tn.position?.y || 0) + 20)
        ctx.stroke()
      }
    }

    // 绘制节点
    for (const node of flowExport.nodes || []) {
      const x = node.position?.x || 0
      const y = node.position?.y || 0
      let bgColor = '#2d2d4a'
      let borderColor = '#5898ff'
      if (node.data?.type?.includes('trigger')) {
        bgColor = '#1a3a4a'
      } else if (node.data?.type?.includes('condition') || node.data?.type?.includes('logic')) {
        bgColor = '#3a2d4a'
        borderColor = '#aa66ff'
      } else if (node.data?.type?.includes('action') || node.data?.type?.includes('yolo')) {
        bgColor = '#2d4a3a'
        borderColor = '#22c55e'
      }

      ctx.fillStyle = bgColor
      ctx.strokeStyle = borderColor
      ctx.lineWidth = 2 / scale
      ctx.beginPath()
      ctx.roundRect(x, y, 120, 40, 6 / scale)
      ctx.fill()
      ctx.stroke()

      ctx.fillStyle = '#fff'
      ctx.font = `${12 / scale}px sans-serif`
      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'
      ctx.fillText((node.data?.label || node.id || '').substring(0, 12), x + 60, y + 20)
    }

    ctx.restore()

    const dataUrl = canvas.toDataURL('image/png', 0.7)
    await ruleEngineApi.updateThumbnail(store.graphMeta?.id || graphId.value, dataUrl)
  } catch (err) {
    console.error('生成缩略图失败:', err)
  }
}

// 校验
async function handleValidate() {
  try {
    const res = await ruleEngineApi.validateGraph(graphId.value)
    if (res.data.valid) {
      ElMessage.success('规则图校验通过')
    } else {
      ElMessage.error(`校验失败: ${res.data.errors?.join(', ') || '未知错误'}`)
    }
  } catch {
    ElMessage.error('校验请求失败')
  }
}

// 执行
async function handleExecute() {
  await handleSave()

  executing.value = true
  store.setExecutionStatus('running')
  store.setExecutionProgress(0)
  store.clearExecution()
  showExecutionPanel.value = true

  try {
    const res = await ruleEngineApi.execute({
      graph_id: graphId.value,
      trigger_type: 'manual'
    })

    const execId = res.data.execution_id
    store.setExecutionId(execId)
    connectWebSocket(execId)
  } catch (err: any) {
    store.setExecutionStatus('failed')
    store.addExecutionLog({
      level: 'error',
      timestamp: new Date().toLocaleTimeString(),
      message: err?.response?.data?.detail || '执行失败'
    })
    ElMessage.error('执行失败')
    executing.value = false
  }
}

// 清空日志
function clearLogs() {
  store.clearExecution()
}
</script>

<style scoped lang="scss">
// 变量
$header-height: 44px;
$palette-width: 280px;
$panel-width: 320px;
$panel-header-height: 44px;

// 全屏布局
.rule-canvas-fullscreen {
  position: fixed;
  inset: 0;
  display: flex;
  flex-direction: column;
  background: #0a0a12;
  color: #e0e0e0;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  z-index: 9999;
  overflow: hidden;
}

// 顶部工具栏
.canvas-header {
  height: $header-height;
  background: linear-gradient(180deg, #0f0f18 0%, #0a0a10 100%);
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 12px;
  flex-shrink: 0;
  z-index: 100;

  .header-left,
  .header-center,
  .header-right {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .header-left {
    flex: 0 0 auto;
    min-width: 0;
  }
  .header-center {
    flex: 1 1 auto;
    min-width: 0;
    justify-content: center;
  }
  .header-right {
    flex: 0 0 auto;
    min-width: 0;
    gap: 8px;
  }
}

.rule-name-section {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: 10px;
  flex-shrink: 0;
  max-width: 100%;
  overflow: hidden;
  flex-wrap: nowrap;
}

.rule-name-input {
  background: transparent;
  padding: 4px 10px;
  border-radius: 5px;
  color: #d0d0e0;
  font-size: 13px;
  font-weight: 500;
  min-width: 140px;
  white-space: nowrap;
  transition: all 0.15s ease;

  &:hover {
    border-color: rgba(255, 255, 255, 0.14);
    background: rgba(255, 255, 255, 0.02);
  }

  &:focus {
    outline: none;
    border-color: var(--accent-blue);
    background: rgba(0, 240, 255, 0.04);
  }
}

.rule-status-badge {
  padding: 2px 8px;
  border-radius: 8px;
  font-size: 10px;
  font-weight: 500;
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.08);
  color: #666;
  letter-spacing: 0.3px;
  white-space: nowrap;
  transition: all 0.15s ease;

  &.active {
    background: rgba(0, 255, 136, 0.06);
    border-color: rgba(0, 255, 136, 0.2);
    color: var(--color-success);
  }
}

.tool-group {
  display: flex;
  align-items: center;
  gap: 1px;
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.05);
  padding: 2px 4px;
  border-radius: 6px;
}

.tool-divider {
  width: 1px;
  height: 16px;
  background: rgba(255, 255, 255, 0.06);
  margin: 0 4px;
}

.zoom-level {
  font-size: 11px;
  color: #666;
  min-width: 36px;
  text-align: center;
  font-family: 'JetBrains Mono', monospace;
}

.ws-status {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 2px 6px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.04);
  font-size: 10px;
  color: #555;

  .ws-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #444;
    transition: background 0.3s;
  }

  .ws-label {
    font-family: 'JetBrains Mono', monospace;
  }

  &.connected {
    color: var(--color-success);
    .ws-dot {
      background: var(--color-success);
      box-shadow: 0 0 6px rgba(0, 255, 136, 0.6);
    }
  }
}

// 按钮样式
.icon-btn {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  border-radius: 5px;
  color: #666;
  cursor: pointer;
  transition: all 0.15s ease;

  :deep(button) {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 0 !important;
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: inherit;
  }

  svg {
    width: 15px;
    height: 15px;
  }

  &:hover:not(:disabled) {
    background: rgba(255, 255, 255, 0.06);
    color: #c0c0d0;
  }

  &:active:not(:disabled) {
    background: rgba(255, 255, 255, 0.08);
    transform: scale(0.92);
  }

  &:disabled {
    opacity: 0.2;
    cursor: not-allowed;
  }

  &.active {
    background: rgba(0, 240, 255, 0.1);
    color: var(--accent-blue);
  }

  &.small {
    width: 24px;
    height: 24px;

    svg { width: 13px; height: 13px; }
  }
}

.back-btn {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  color: #888;

  :deep(button) {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 0 !important;
    color: inherit;
  }

  &:hover {
    background: rgba(0, 240, 255, 0.06);
    border-color: rgba(0, 240, 255, 0.2);
    color: var(--accent-blue);
  }
}

.action-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 0 16px;
  height: 30px;
  border: none;
  border-radius: 5px;
  font-size: 12px;
  font-weight: 500;
  letter-spacing: 0.4px;
  cursor: pointer;
  transition: all 0.15s ease;
  white-space: nowrap;
  flex-shrink: 0;

  :deep(button) {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 0 !important;
    width: 100%;
    height: 100%;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: inherit;
    color: inherit;
    font-size: inherit;
    font-weight: inherit;
    letter-spacing: inherit;
    white-space: inherit;
  }

  svg {
    width: 14px;
    height: 14px;
    flex-shrink: 0;
  }

  &:disabled {
    opacity: 0.3;
    cursor: not-allowed;
  }

  &.secondary {
    background: rgba(255, 255, 255, 0.06);
    color: #8888a8;
    border: 1px solid rgba(255, 255, 255, 0.06);

    &:hover:not(:disabled) {
      background: rgba(255, 255, 255, 0.09);
      color: #c0c0d0;
      border-color: rgba(255, 255, 255, 0.12);
    }

    &:active:not(:disabled) {
      background: rgba(255, 255, 255, 0.05);
    }
  }

  &.primary {
    background: var(--accent-blue);
    color: #060610;
    font-weight: 600;
    border: 1px solid rgba(0, 240, 255, 0.3);
    box-shadow: 0 0 12px rgba(0, 240, 255, 0.15);

    &:hover:not(:disabled) {
      background: #1af5ff;
      box-shadow: 0 0 18px rgba(0, 240, 255, 0.3);
    }

    &:active:not(:disabled) {
      background: #00d8e8;
      box-shadow: 0 0 8px rgba(0, 240, 255, 0.15);
    }
  }
}

// 主体区域
.canvas-body {
  flex: 1;
  display: flex;
  overflow: hidden;
  position: relative;
}

// 左侧节点面板
.node-palette {
  width: $palette-width;
  background: #0e0e14;
  border-right: 1px solid #1e1e2e;
  display: flex;
  flex-direction: column;
  transition: width 0.3s ease;
  flex-shrink: 0;
  z-index: 50;
  position: relative;
  overflow: visible;

  &.collapsed {
    width: 48px;

    .palette-content,
    .palette-search,
    .palette-header { display: none; }
  }
}

.palette-header {
  height: $panel-header-height;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 8px;
  border-bottom: 1px solid #1e1e2e;

  h3 {
    font-size: 13px;
    font-weight: 600;
    color: #888;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    flex: 1;
  }
}

.collapse-btn {
  position: absolute;
  right: -14px;
  top: 50%;
  transform: translateY(-50%);
  width: 14px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #0e0e14;
  border: 1px solid #1e1e2e;
  border-left: none;
  border-radius: 0 6px 6px 0;
  color: #666;
  cursor: pointer;
  z-index: 20;
  padding: 0;

  :deep(button) {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 0 !important;
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: inherit;
  }

  &:hover {
    color: var(--accent-blue);
    border-color: var(--accent-blue);
    border-left: none;
  }

  svg {
    width: 12px;
    height: 12px;
  }

  &.collapsed svg {
    transform: translateX(1px);
  }
}

.palette-search {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
  gap: 6px;

  .search-input {
    flex: 1;
    height: 30px;
    padding: 0 10px;
    border-radius: 6px;
    color: #b0b0c0;
    font-size: 12px;
    outline: none;
    transition: border-color 0.15s ease;

    &::placeholder {
      color: #555;
    }

    &:focus {
      border-color: var(--accent-blue);
      background: rgba(0, 240, 255, 0.04);
    }
  }

  .search-clear {
    width: 22px;
    height: 22px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 50%;
    color: #666;
    font-size: 12px;
    cursor: pointer;
    flex-shrink: 0;
    transition: all 0.15s ease;

    :deep(button) {
      background: transparent !important;
      border: none !important;
      box-shadow: none !important;
      padding: 0 !important;
      width: 100%;
      height: 100%;
      display: flex;
      align-items: center;
      justify-content: center;
      color: inherit;
    }

    &:hover {
      background: rgba(0, 240, 255, 0.08);
      border-color: rgba(0, 240, 255, 0.2);
      color: var(--accent-blue);
    }
  }
}

.palette-port-filter {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  padding: 6px 12px 8px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
}

.port-filter-btn {
  padding: 3px 8px;
  border-radius: 4px;
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.08);
  color: #888;
  font-size: 11px;
  cursor: pointer;
  transition: all 0.15s;

  &:hover {
    border-color: var(--accent-blue);
    color: var(--accent-blue);
  }

  &.active {
    background: var(--accent-blue);
    border-color: var(--accent-blue);
    color: #000;
    font-weight: 600;
  }
}

.palette-content {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

// 变量管理面板
.variables-section {
  margin-top: 8px;
  padding: 8px;
  border-top: 1px solid var(--border-color, #3a3a5c);

  .section-header {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px;
    cursor: pointer;
    border-radius: 6px;
    transition: background 0.2s;

    &:hover {
      background: #1a1a24;
    }

    .section-title {
      font-size: 13px;
      font-weight: 500;
      color: var(--accent-blue);
    }

    .section-count {
      font-size: 11px;
      color: #888;
      background: #2a2a3a;
      padding: 2px 6px;
      border-radius: 10px;
    }

    .chevron {
      width: 14px;
      height: 14px;
      margin-left: auto;
      transition: transform 0.2s;

      &.expanded {
        transform: rotate(180deg);
      }
    }
  }

  .variables-list {
    padding: 4px 0;
  }

  .variable-item {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-bottom: 6px;

    .var-name-input {
      flex: 1;
      min-width: 0;
      padding: 6px 8px;
      background: #1a1a24;
      border: 1px solid #3a3a5c;
      border-radius: 4px;
      color: #e0e0e0;
      font-size: 12px;

      &:focus {
        outline: none;
        border-color: var(--accent-blue);
      }
    }

    .var-type-select {
      width: 80px;
      padding: 6px 4px;
      background: #1a1a24;
      border: 1px solid #3a3a5c;
      border-radius: 4px;
      color: #e0e0e0;
      font-size: 11px;

      &:focus {
        outline: none;
        border-color: var(--accent-blue);
      }
    }

    .var-remove-btn {
      width: 24px;
      height: 24px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: transparent;
      border: none;
      border-radius: 4px;
      color: #888;
      cursor: pointer;
      font-size: 14px;
      transition: all 0.2s;

      :deep(button) {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        padding: 0 !important;
        color: inherit;
      }

      &:hover {
        background: rgba(255, 76, 76, 0.2);
        color: #ff4c4c;
      }
    }
  }

  .add-var-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    width: 100%;
    padding: 8px;
    margin-top: 4px;
    background: transparent;
    border: 1px dashed #3a3a5c;
    border-radius: 6px;
    color: #888;
    font-size: 12px;
    cursor: pointer;
    transition: all 0.2s;

    :deep(button) {
      background: transparent !important;
      border: none !important;
      box-shadow: none !important;
      padding: 0 !important;
      color: inherit;
      font-size: inherit;
      font-weight: inherit;
    }

    &:hover {
      border-color: var(--accent-blue);
      color: var(--accent-blue);
      background: rgba(0, 240, 255, 0.05);
    }

    svg {
      width: 12px;
      height: 12px;
    }
  }
}

.node-category {
  margin-bottom: 4px;
}

.category-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: #1a1a24;
  }

  .category-icon-wrapper {
    width: 28px;
    height: 28px;
    border-radius: 6px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;

    svg { width: 16px; height: 16px; }

    &.input { background: rgba(76, 255, 76, 0.15); color: #4CFF4C; }
    &.detection { background: rgba(0, 240, 255, 0.15); color: #00f0FF; }
    &.processing { background: rgba(255, 255, 76, 0.15); color: #FFFF4C; }
    &.action { background: rgba(255, 127, 76, 0.15); color: #FF7F4C; }
    &.logic { background: rgba(220, 79, 220, 0.15); color: #DC4FDC; }
    &.output { background: rgba(255, 76, 76, 0.15); color: #FF4C4C; }
  }

  .category-name {
    flex: 1;
    font-size: 13px;
    font-weight: 500;
  }

  .category-count {
    font-size: 11px;
    padding: 2px 8px;
    background: #1e1e2e;
    border-radius: 10px;
    color: #666;
  }

  .chevron {
    width: 16px;
    height: 16px;
    color: #666;
    transition: transform 0.2s;

    &.expanded { transform: rotate(180deg); }
  }
}

.node-list {
  padding: 4px 0 8px 0;
}

.node-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px 10px 40px;
  border-radius: 6px;
  cursor: grab;
  transition: all 0.2s;

  &:hover {
    background: #1a1a24;
  }

  &:active {
    cursor: grabbing;
  }

  .node-icon-wrapper {
    width: 28px;
    height: 28px;
    border-radius: 6px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;

    svg { width: 14px; height: 14px; }

    &.input { background: rgba(76, 255, 76, 0.1); color: #4CFF4C; }
    &.detection { background: rgba(0, 240, 255, 0.1); color: #00f0FF; }
    &.processing { background: rgba(255, 255, 76, 0.1); color: #FFFF4C; }
    &.action { background: rgba(255, 127, 76, 0.1); color: #FF7F4C; }
    &.logic { background: rgba(220, 79, 220, 0.1); color: #DC4FDC; }
    &.output { background: rgba(255, 76, 76, 0.1); color: #FF4C4C; }
  }

  .node-info {
    display: flex;
    flex-direction: column;
    min-width: 0;

    .node-label {
      font-size: 13px;
      font-weight: 500;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .node-type-hint {
      font-size: 10px;
      color: #555;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
  }
}

// 画布区域
.canvas-wrapper {
  flex: 1;
  position: relative;
  overflow: hidden;
  background:
    radial-gradient(circle, #3a3a4a 1px, transparent 1px);
  background-size: 30px 30px;
  background-position: 0 0;
}

.flow-container {
  width: 100%;
  height: 100%;
  position: relative;

  &.panning {
    :deep(.vue-flow__pane) {
      cursor: grabbing !important;
    }
  }

  :deep(.vue-flow) {
    width: 100%;
    height: 100%;
    background: transparent;
  }

  :deep(.vue-flow) {
    width: 100%;
    height: 100%;
    background: transparent !important;
  }

  /* 默认画布鼠标样式为默认，只有按住空格/中键/alt才可平移 */
  :deep(.vue-flow__pane) {
    cursor: default;
  }

  :deep(.vue-flow__pane.draggable) {
    cursor: grab;
  }

  :deep(.vue-flow__pane.dragging) {
    cursor: grabbing;
  }

  /* 只有 selection 模式（框选）才显示十字光标 */
  :deep(.vue-flow__pane.selection) {
    cursor: crosshair;
  }

  /* 隐藏选中后的包裹矩形框 */
  :deep(.vue-flow__nodesselection-rect) {
    display: none;
  }

  :deep(.vue-flow__edge-path) {
    stroke: var(--accent-blue);
    stroke-width: 2;
    transition: stroke 0.15s ease, stroke-width 0.15s ease;
  }

  :deep(.vue-flow__edge.animated .vue-flow__edge-path) {
    stroke-dasharray: 5;
    animation: dash 0.5s linear infinite;
  }

  /* 连线选中态：橙色高亮 + 加粗 */
  :deep(.vue-flow__edge.selected .vue-flow__edge-path) {
    stroke: #ff7f4c;
    stroke-width: 3;
  }

  :deep(.vue-flow__edge.selected .vue-flow__edge-interaction) {
    stroke: #ff7f4c;
    stroke-width: 12;
    stroke-opacity: 0.15;
  }

  /* hover 态：轻量加亮（仅非选中时） */
  :deep(.vue-flow__edge:hover .vue-flow__edge-path) {
    stroke: #5898ff;
    stroke-width: 2.5;
  }

  :deep(.vue-flow__controls) {
    background: #12121a;
    border: 1px solid #1e1e2e;
    border-radius: 8px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.3);

    .vue-flow__controls-button {
      background: transparent;
      border: none;
      color: #888;
      width: 32px;
      height: 32px;

      &:hover {
        background: #1e1e2e;
        color: #fff;
      }

      svg {
        fill: currentColor;
        width: 14px;
        height: 14px;
      }
    }
  }

  :deep(.vue-flow__minimap) {
    background: #0e0e14;
    border: 1px solid #1e1e2e;
    border-radius: 8px;
  }
}

@keyframes dash {
  to { stroke-dashoffset: -10; }
}

// 标尺
.ruler {
  position: absolute;
  background: #0e0e14;
  z-index: 20;
  pointer-events: none;
}

.ruler-horizontal {
  top: 0;
  left: 0;
  right: 0;
  height: 24px;
  border-bottom: 1px solid #1e1e2e;
}

.ruler-vertical {
  top: 0;
  left: 0;
  bottom: 0;
  width: 24px;
  border-right: 1px solid #1e1e2e;
}

.ruler-content {
  position: relative;
}

.ruler-mark {
  position: absolute;
  font-size: 9px;
  color: #444;
  font-family: 'JetBrains Mono', monospace;
}

.ruler-horizontal .ruler-mark {
  top: 0;
  border-left: 1px solid #2a2a3a;
  padding-left: 3px;
}

.ruler-vertical .ruler-mark {
  left: 0;
  border-top: 1px solid #2a2a3a;
  padding-top: 2px;
}

// 空状态
.empty-state {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  pointer-events: none;
  z-index: 10;

  .empty-icon {
    width: 100px;
    height: 100px;
    margin-bottom: 24px;
    opacity: 0.2;

    svg {
      width: 100%;
      height: 100%;
      stroke: var(--accent-blue);
    }
  }

  h3 {
    font-size: 20px;
    font-weight: 600;
    color: #555;
    margin-bottom: 8px;
  }

  p {
    font-size: 14px;
    color: #444;
    margin-bottom: 32px;
  }

  .quick-add-nodes {
    display: flex;
    gap: 12px;
    pointer-events: auto;
  }

  .quick-add-btn {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 12px 20px;
    background: #12121a;
    border: 1px solid #2a2a3a;
    border-radius: 8px;
    color: #888;
    font-size: 13px;
    cursor: pointer;
    transition: all 0.2s;

    :deep(button) {
      background: transparent !important;
      border: none !important;
      box-shadow: none !important;
      padding: 0 !important;
      color: inherit;
      font-size: inherit;
      font-weight: inherit;
    }

    .btn-icon {
      width: 24px;
      height: 24px;
      border-radius: 4px;
      display: flex;
      align-items: center;
      justify-content: center;

      svg { width: 14px; height: 14px; }

      &.input { background: rgba(76, 255, 76, 0.1); color: #4CFF4C; }
      &.detection { background: rgba(0, 240, 255, 0.1); color: #00f0FF; }
      &.processing { background: rgba(255, 255, 76, 0.1); color: #FFFF4C; }
      &.action { background: rgba(255, 127, 76, 0.1); color: #FF7F4C; }
      &.logic { background: rgba(220, 79, 220, 0.1); color: #DC4FDC; }
      &.output { background: rgba(255, 76, 76, 0.1); color: #FF4C4C; }
    }

    &:hover {
      border-color: var(--accent-blue);
      color: #fff;
    }
  }
}

// 快捷添加工具栏（画布上有节点时显示）
.quick-add-toolbar {
  position: absolute;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  gap: 8px;
  padding: 8px 12px;
  background: rgba(18, 18, 26, 0.95);
  border: 1px solid #2a2a3a;
  border-radius: 12px;
  backdrop-filter: blur(8px);
  z-index: 10;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);

  .quick-add-toolbar-btn {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 8px 14px;
    background: #1a1a24;
    border: 1px solid #2a2a3a;
    border-radius: 8px;
    color: #888;
    font-size: 12px;
    cursor: pointer;
    transition: all 0.2s;
    white-space: nowrap;

    .btn-icon {
      width: 20px;
      height: 20px;
      border-radius: 4px;
      display: flex;
      align-items: center;
      justify-content: center;

      svg { width: 12px; height: 12px; }

      &.input { background: rgba(76, 255, 76, 0.15); color: #4CFF4C; }
      &.detection { background: rgba(0, 240, 255, 0.15); color: #00f0FF; }
      &.processing { background: rgba(255, 255, 76, 0.15); color: #FFFF4C; }
      &.action { background: rgba(255, 127, 76, 0.15); color: #FF7F4C; }
      &.logic { background: rgba(220, 79, 220, 0.15); color: #DC4FDC; }
      &.output { background: rgba(255, 76, 76, 0.15); color: #FF4C4C; }
    }

    .btn-label {
      color: #e0e0e8;
    }

    &:hover {
      border-color: var(--accent-blue);
      background: #22222e;
      transform: translateY(-2px);
      box-shadow: 0 4px 12px rgba(0, 240, 255, 0.15);
    }

    &:active {
      transform: translateY(0);
    }
  }
}

// 右侧属性面板
.properties-panel {
  width: 0;
  background: #0e0e14;
  border-left: 1px solid transparent;
  display: flex;
  flex-direction: column;
  transition: width 0.3s ease, border-color 0.3s ease;
  overflow: hidden;
  flex-shrink: 0;

  &.visible {
    width: $panel-width;
    border-left-color: #1e1e2e;
  }
}

.panel-header {
  height: $panel-header-height;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  border-bottom: 1px solid #1e1e2e;
  flex-shrink: 0;
}

.panel-title {
  display: flex;
  align-items: center;
  gap: 12px;

  .panel-icon {
    width: 36px;
    height: 36px;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;

    svg { width: 18px; height: 18px; }

    &.input { background: rgba(76, 255, 76, 0.15); color: #4CFF4C; }
    &.detection { background: rgba(0, 240, 255, 0.15); color: #00f0FF; }
    &.processing { background: rgba(255, 255, 76, 0.15); color: #FFFF4C; }
    &.action { background: rgba(255, 127, 76, 0.15); color: #FF7F4C; }
    &.logic { background: rgba(220, 79, 220, 0.15); color: #DC4FDC; }
    &.output { background: rgba(255, 76, 76, 0.15); color: #FF4C4C; }
  }

  .panel-title-text {
    display: flex;
    flex-direction: column;

    .node-name {
      font-size: 14px;
      font-weight: 600;
    }

    .node-type-label {
      font-size: 11px;
      color: #555;
      font-family: 'JetBrains Mono', monospace;
    }
  }
}

.close-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  border-radius: 6px;
  color: #666;
  cursor: pointer;
  transition: all 0.2s;

  svg { width: 16px; height: 16px; }

  &:hover {
    background: #1e1e2e;
    color: #fff;
  }
}

.panel-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.config-section {
  margin-bottom: 24px;

  .section-label {
    font-size: 11px;
    font-weight: 600;
    color: #555;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 12px;
  }
}

.node-description {
  font-size: 13px;
  color: #777;
  line-height: 1.5;
}

.config-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 6px;

  .field-label {
    font-size: 12px;
    color: #888;
  }

  .field-input,
  .field-select {
    background: #12121a;
    border: 1px solid #1e1e2e;
    border-radius: 6px;
    padding: 10px 12px;
    color: #fff;
    font-size: 13px;
    transition: all 0.2s;

    &:focus {
      outline: none;
      border-color: var(--accent-blue);
      background: rgba(0, 240, 255, 0.03);
    }

    &::placeholder {
      color: #444;
    }
  }

  .field-select {
    cursor: pointer;
  }

  .field-default {
    font-size: 11px;
    color: #444;
  }
}

.array-field {
  display: flex;
  flex-direction: column;
  gap: 8px;

  .array-item {
    display: flex;
    gap: 8px;

    .field-input {
      flex: 1;
    }

    .remove-btn {
      width: 36px;
      height: 36px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: transparent;
      border: 1px solid #1e1e2e;
      border-radius: 6px;
      color: #666;
      cursor: pointer;
      transition: all 0.2s;
      flex-shrink: 0;

      svg { width: 14px; height: 14px; }

      &:hover {
        border-color: var(--color-danger);
        color: var(--color-danger);
      }
    }
  }

  .add-item-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    padding: 8px;
    background: transparent;
    border: 1px dashed #2a2a3a;
    border-radius: 6px;
    color: #666;
    font-size: 12px;
    cursor: pointer;
    transition: all 0.2s;

    svg { width: 14px; height: 14px; }

    &:hover {
      border-color: var(--accent-blue);
      color: var(--accent-blue);
    }
  }
}

.ports-display {
  display: flex;
  flex-direction: column;
  gap: 8px;

  .ports-row {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .port-item {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-wrap: wrap;
  }

  .ports-title {
    font-size: 11px;
    color: #555;
    width: 40px;
    flex-shrink: 0;
    padding-top: 6px;
  }

  .ports-list {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }

  .port-chip {
    padding: 4px 10px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 500;
    flex-shrink: 0;

    &.input {
      background: rgba(0, 240, 255, 0.1);
      color: var(--accent-blue);
      border: 1px solid rgba(0, 240, 255, 0.2);
    }

    &.output {
      background: rgba(0, 255, 136, 0.1);
      color: var(--color-success);
      border: 1px solid rgba(0, 255, 136, 0.2);
    }
  }

  .port-connected {
    font-size: 11px;
    color: #888;
    flex: 1;
  }

  .port-disconnected {
    font-size: 11px;
    color: #444;
    font-style: italic;
  }

  .port-outgoing {
    font-size: 11px;
    color: var(--color-success);
  }

  .port-disconnect {
    background: rgba(255, 60, 60, 0.15);
    border: 1px solid rgba(255, 60, 60, 0.3);
    color: #ff6666;
    border-radius: 3px;
    width: 18px;
    height: 18px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    font-size: 12px;
    line-height: 1;
    padding: 0;
    transition: all 0.15s;

    &:hover {
      background: rgba(255, 60, 60, 0.3);
      color: #ff8888;
    }
  }
}

.no-selection {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #444;
  text-align: center;
  padding: 20px;

  svg {
    width: 64px;
    height: 64px;
    margin-bottom: 16px;
    opacity: 0.3;
  }

  p {
    font-size: 13px;
    line-height: 1.6;
  }
}

// 执行日志面板
.execution-panel {
  position: fixed;
  bottom: 0;
  right: 0;
  background: #0e0e14;
  border-top: 1px solid #1e1e2e;
  z-index: 50;
  transition: transform 0.3s ease;

  &:not(.expanded) {
    .execution-content { display: none; }
  }
}

.panel-resize-handle {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  cursor: ns-resize;
  z-index: 10;

  &:hover {
    background: rgba(0, 240, 255, 0.3);
  }
}

.execution-header {
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  cursor: pointer;
  user-select: none;
}

.execution-title {
  display: flex;
  align-items: center;
  gap: 10px;

  svg {
    width: 18px;
    height: 18px;
    color: #666;
  }

  span:nth-child(2) {
    font-size: 13px;
    font-weight: 500;
  }

  .execution-status {
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 600;

    &.idle { background: #1e1e2e; color: #666; }
    &.running { background: rgba(0, 240, 255, 0.15); color: var(--accent-blue); }
    &.success { background: rgba(0, 255, 136, 0.15); color: var(--color-success); }
    &.failed { background: rgba(255, 0, 170, 0.15); color: var(--accent-blue); }
  }
}

.execution-actions {
  display: flex;
  align-items: center;
  gap: 8px;

  .expand-icon {
    width: 20px;
    height: 20px;
    color: #666;
    transition: transform 0.2s;

    &.expanded { transform: rotate(180deg); }
  }
}

.execution-content {
  max-height: 200px;
  overflow-y: auto;
}

/* 执行进度条 */
.progress-bar-wrapper {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 16px;
  background: rgba(0, 240, 255, 0.03);
  border-bottom: 1px solid #1a1a24;
}

.progress-bar {
  flex: 1;
  height: 4px;
  background: #2a2a3a;
  border-radius: 2px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--accent-blue), var(--color-success));
  border-radius: 2px;
  transition: width 0.3s ease;
}

.progress-text {
  font-size: 11px;
  color: var(--accent-blue);
  min-width: 32px;
  text-align: right;
}

.logs-list {
  padding: 8px 16px;
}

.log-entry {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 0;
  border-bottom: 1px solid #1a1a24;
  font-size: 12px;

  &:last-child { border-bottom: none; }

  .log-time {
    color: #444;
    font-family: 'JetBrains Mono', monospace;
    flex-shrink: 0;
  }

  .log-level-badge {
    padding: 2px 6px;
    border-radius: 3px;
    font-size: 10px;
    font-weight: 700;
    flex-shrink: 0;
  }

  &.info .log-level-badge {
    background: rgba(0, 240, 255, 0.15);
    color: var(--accent-blue);
  }

  &.warning .log-level-badge {
    background: rgba(255, 221, 0, 0.15);
    color: var(--color-warning);
  }

  &.error .log-level-badge {
    background: rgba(255, 0, 170, 0.15);
    color: var(--accent-blue);
  }

  .log-node {
    color: #555;
    flex-shrink: 0;
  }

  .log-message {
    color: #888;
    flex: 1;
  }

  .log-metrics {
    color: #6a8;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    flex-shrink: 0;
    opacity: 0.85;
  }
}

.no-logs {
  text-align: center;
  padding: 20px;
  color: #444;
  font-size: 13px;
}

/* 右键菜单 */
.context-menu {
  position: fixed;
  z-index: 9999;
  background: var(--bg-secondary, #12121a);
  border: 1px solid var(--border-color, #2a2a3e);
  border-radius: 8px;
  padding: 6px 0;
  min-width: 180px;
  max-width: 220px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5);
}

.context-menu-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  cursor: pointer;
  font-size: 13px;
  color: var(--text-primary, #e0e0e0);
  transition: background 0.15s;

  svg {
    width: 14px;
    height: 14px;
    flex-shrink: 0;
    opacity: 0.7;
  }

  &:hover {
    background: var(--bg-hover, #1e1e2e);

    svg { opacity: 1; }
  }
}

.context-menu-item.danger {
  color: #ff4c4c;
}

.context-menu-item.danger:hover {
  background: rgba(255, 76, 76, 0.1);
}

.context-menu-divider {
  height: 1px;
  background: var(--border-color, #2a2a3e);
  margin: 6px 0;
}

.context-menu-overlay {
  position: fixed;
  inset: 0;
  z-index: 9998;
}

// 变量绑定菜单
.var-menu {
  position: fixed;
  z-index: 9999;
  background: var(--bg-secondary, #1e1e2e);
  border: 1px solid var(--border-color, #3a3a5c);
  border-radius: 8px;
  padding: 8px 0;
  min-width: 160px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);

  .var-menu-title {
    padding: 6px 12px;
    font-size: 12px;
    color: var(--text-secondary, #888);
    border-bottom: 1px solid var(--border-color, #3a3a5c);
    margin-bottom: 4px;
  }

  .var-menu-item {
    padding: 8px 12px;
    cursor: pointer;
    font-size: 13px;
    color: var(--text-primary, #e0e0e0);
    transition: background 0.15s;

    &:hover {
      background: var(--hover-bg, #2a2a4a);
      color: var(--accent, var(--accent-blue));
    }

    .var-type-tag {
      font-size: 10px;
      padding: 1px 5px;
      background: rgba(0, 240, 255, 0.15);
      color: var(--accent-blue);
      border-radius: 3px;
      margin-left: 6px;
    }
  }

  .var-menu-empty {
    padding: 12px;
    text-align: center;
    font-size: 12px;
    color: #888;
  }
}

.var-menu-overlay {
  position: fixed;
  inset: 0;
  z-index: 9998;
}

// 字段输入包装（带变量按钮）
.field-input-wrapper {
  display: flex;
  align-items: center;
  gap: 4px;

  .field-input {
    flex: 1;
  }

  .var-btn {
    padding: 4px 8px;
    background: transparent;
    border: 1px solid var(--border-color, #3a3a5c);
    border-radius: 4px;
    color: var(--text-secondary, #888);
    cursor: pointer;
    font-size: 12px;
    transition: all 0.15s;

    &:hover {
      background: var(--hover-bg, #2a2a4a);
      color: var(--accent, var(--accent-blue));
      border-color: var(--accent, var(--accent-blue));
    }
  }
}

</style>
