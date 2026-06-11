<template>
  <div
  class="rule-canvas-fullscreen"
  :class="{ 'large-graph-mode': largeGraphMode, 'huge-graph-mode': hugeGraphMode }"
>
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
          <!--
            缩放比例: DOM 直写 (不走 Vue 响应式) - @zoom 每帧触发,
            走 ref 会触发整个父组件 re-render, 50-60Hz 缩放会爆调度
            缩放比例只是顶部工具栏一个 span 文本, 用 ref + textContent 直写
            完全够用, 跳过 Vue 调度
          -->
          <span
            ref="zoomLevelEl"
            class="zoom-level"
          >100%</span>
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
          class="palette-toggle-btn"
          :class="{ active: showPalette }"
          :title="showPalette ? '收起节点面板' : '展开节点面板'"
          @click="showPalette = !showPalette"
        >
          <SvgIcon name="panel-left" />
        </el-button>
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
      <!-- 左侧节点面板 (折叠时整段隐藏 — 完全收纳) -->
      <aside
        v-show="showPalette"
        class="node-palette"
      >
        <div
          class="palette-header"
        >
          <h3>节点库</h3>
        </div>

        <div
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
          class="palette-port-filter"
        >
          <button
            class="port-filter-btn"
            :class="{ active: portTypeFilter.size === 0 }"
            title="全部（清除过滤）"
            @click="portTypeFilter = new Set()"
          >
            全部
          </button>
          <button
            v-for="pt in portTypeFilterOptions"
            :key="pt.type"
            class="port-filter-btn"
            :class="{ active: portTypeFilter.has(pt.type) }"
            :title="portTypeFilter.has(pt.type) ? `点击取消 ${pt.type} 过滤` : `仅显示有 ${pt.type} 端口的节点`"
            @click="togglePortTypeFilter(pt.type)"
          >
            {{ pt.label }}
          </button>
        </div>

        <div
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
            :nodes="nodes"
            :edges="edges"
            :node-types="nodeTypes"
            :default-edge-options="defaultEdgeOptions"
            :connection-line-style="connectionLineStyle"
            :snap-to-grid="false"
            :snap-grid="[gridSize, gridSize]"
            :default-viewport="{ x: 0, y: 0, zoom: 0.65 }"
            :pan-on-drag="false"
            :pan-on-scroll="true"
            :zoom-on-scroll="true"
            :min-zoom="0.3"
            :max-zoom="1.5"
            :nodes-draggable="false"
            :nodes-connectable="true"
            :elements-selectable="true"
            :auto-connect="false"
            :only-render-visible-elements="true"
            :select-nodes-on-drag="false"
            :selection-key-code="true"
            :selection-mode="SelectionMode.Partial"
            :connection-radius="20"
            :is-valid-connection="isValidConnection"
            @node-click="handleNodeClick"
            @pane-click="handlePaneClick"
            @connect="handleConnect"
            @viewport-change="handleZoom"
            @nodes-change="handleNodesChange"
            @edges-change="handleEdgesChange"
            @node-double-click="handleNodeDoubleClick"
            @node-context-menu="(e: NodeMouseEvent) => handleContextMenu(e.event as MouseEvent, e.node, 'node')"
            @pane-context-menu="(e: MouseEvent) => handleContextMenu(e, null, 'pane')"
            @edge-context-menu="(e: EdgeMouseEvent) => handleContextMenu(e.event as MouseEvent, e.edge, 'edge')"
            @node-delete="handleNodeDelete"
            @selection-start="handleSelectionStart"
            @selection-end="handleSelectionEnd"
          >
            <!-- 小地图 (Phase B 任务5: shouldShowMiniMap 自动策略) -->
            <MiniMap
              v-if="shouldShowMiniMap"
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
          <!-- P1-H: 虚拟滚动 (vue-virtual-scroller RecycleScroller) —
               1000+ 日志滚动 60fps, 仅渲染可视区域 + 上下 buffer -->
          <RecycleScroller
            v-if="executionLogs.length > 0"
            class="logs-scroller"
            :items="executionLogs"
            :item-size="34"
            v-slot="{ item, index }"
          >
            <div
              :key="index"
              class="log-entry"
              :class="item.level"
            >
              <span class="log-time">{{ item.timestamp }}</span>
              <span class="log-level-badge">{{ item.level.toUpperCase() }}</span>
              <span
                v-if="item.node_type"
                class="log-node"
              >{{ item.node_type }}</span>
              <span class="log-message">{{ item.message }}</span>
              <span
                v-if="item.metrics && Object.keys(item.metrics).length > 0"
                class="log-metrics"
                :title="formatMetrics(item.metrics)"
              >{{ formatMetrics(item.metrics) }}</span>
              <span
                v-if="item.duration_ms != null"
                class="log-duration"
              >{{ formatDuration(item.duration_ms) }}</span>
            </div>
          </RecycleScroller>
          <div
            v-else
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
          @click="handleContextAction('copy', $event)"
        >
          <SvgIcon name="copy" /> 复制
        </div>
        <div
          class="context-menu-item"
          @click="handleContextAction('cut', $event)"
        >
          <SvgIcon name="cut" /> 剪切
        </div>
        <div
          class="context-menu-item danger"
          @click="handleContextAction('delete', $event)"
        >
          <SvgIcon name="delete" /> 删除
        </div>
        <div class="context-menu-divider" />
      </template>
      <template v-if="contextMenu.targetType === 'edge'">
        <div
          class="context-menu-item danger"
          @click="handleContextAction('delete', $event)"
        >
          <SvgIcon name="delete" /> 删除连线
        </div>
        <div class="context-menu-divider" />
      </template>
      <div
        class="context-menu-item"
        @click="handleContextAction('paste', $event)"
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
import { triggerRef, watch } from 'vue'
import { useRuleEngineStore, type RuleNodeData, type NodeDefinition } from '@/stores/ruleEngine'
import { storeToRefs } from 'pinia'
import { ruleEngineApi } from '@/api'
import type { Node, Edge, NodeMouseEvent, EdgeMouseEvent } from '@vue-flow/core'
// SelectionMode 在 <template> 里使用（Vue 模板作用域只解析 <script setup> 顶层 binding，
// auto-import 的全局 const 在 template 中不被 TS 识别），需要显式 import
import { SelectionMode } from '@vue-flow/core'
import RuleNode from '@/components/rule-engine/RuleNode.vue'
// Phase 17.1+: NodeConfigEditor 已不再用于右侧面板, 改由 RuleNode LOD 2 内嵌使用,
// RuleNode.vue 自行 import 该组件, RuleCanvas 不再 import.
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import '@vue-flow/controls/dist/style.css'
import '@vue-flow/minimap/dist/style.css'
import { RecycleScroller } from 'vue-virtual-scroller'
import 'vue-virtual-scroller/dist/vue-virtual-scroller.css'
import { useCogniFlowDrag } from '@/composables/useCogniFlowDrag'

const router = useRouter()
const route = useRoute()
const {
  fitView,
  setCenter,
  screenToFlowCoordinate,
  userSelectionRect,
  setViewport,
  getViewport,
  addSelectedNodes,
  addSelectedEdges,
  getNodes,
  getSelectedNodes,
  findNode,
  applyNodeChanges: applyVueFlowNodeChanges,
  applyEdgeChanges: applyVueFlowEdgeChanges,
} = useVueFlow()

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

// 路径 B: 自研拖动接管 (需在 storeToRefs 之后调用，确保 nodes ref 可用)
useCogniFlowDrag({
  nodesRef: nodes,
  getZoom: () => getViewport().zoom,
  findFlowNode: (id: string) => {
    // 拿 VueFlow 内部 reactive GraphNode, 改它 .position 触发 getEdges 80 边 path 重算
    // 不调 setNodes / createGraphNodes, 绕过 80 节点 vdom diff/patch
    const flowNode = findNode(id) as any
    return flowNode
  },
  onStart: () => {
    isNodeDragging.value = true
    isBatchDragging.value = true   // 拖动期间节流 handleNodesChange
    store.setDragging(true)         // LOD-1: 拖动期间锁定 LOD 等级
  },
  onEnd: () => {
    isNodeDragging.value = false
    isBatchDragging.value = false  // 恢复 handleNodesChange
    store.setDragging(false)        // LOD-1: 解除 LOD 锁定
  },
})

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
// 缩略图生成并发防护：连击"保存"时若上一次 captureAndSaveThumbnail 仍在跑，跳过本次。
// requestIdleCallback 100ms fallback 会让 200ms 内的多次保存都进队列，导致并发。
const thumbnailInflight = ref(false)
const executing = ref(false)
const showPalette = ref(true)
const showMiniMap = ref(true)

// Phase B 任务5: 大图渲染降级
const LARGE_GRAPH_NODE_THRESHOLD = 80
const HUGE_GRAPH_NODE_THRESHOLD = 200

const largeGraphMode = computed(() => nodes.value.length >= LARGE_GRAPH_NODE_THRESHOLD)
const hugeGraphMode = computed(() => nodes.value.length >= HUGE_GRAPH_NODE_THRESHOLD)
/** MiniMap 自动策略: 拖拽/框选/大图全部隐藏, 但用户手动 on 仍生效 */
const shouldShowMiniMap = computed(() => {
  if (isNodeDragging.value || isSelectionDragging.value) return false
  // 用户手动 on/off 优先; 默认 (true) 时按 largeGraphMode 自动
  return showMiniMap.value && !largeGraphMode.value
})
const snapGrid = ref(true)
const showGrid = ref(true)
const showExecutionPanel = ref(false)
const flowContainer = ref<HTMLElement | null>(null)
const vueFlowRef = ref<any>(null)
const canvasWrapper = ref<HTMLElement | null>(null)
const isNodeDragging = ref(false)
// zoomLevel: 仅作为内部值供 zoomIn/zoomOut/quickAddNode 读取, 不参与响应式
// 模板显示走 zoomLevelEl.textContent (DOM 直写), 见 P0-2
const zoomLevel = ref(1)
// zoomLevelEl: 缩放比例 DOM 引用, 走 textContent 直写不走 Vue 响应式
const zoomLevelEl = ref<HTMLElement | null>(null)
// 缓存当前显示值, 避免重复设置相同内容触发无谓的 DOM write
let lastZoomText = '100%'
const isPanning = ref(false)
const lastMousePos = ref({ x: 0, y: 0 })
/** 全局鼠标位置: 任何 mousemove 都更新, 用于快捷键 Ctrl+V 拿鼠标坐标 (KeyboardEvent 没 clientX/Y) */
const globalMousePos = ref({ x: 0, y: 0 })

// 复制粘贴
/** 剪贴板 payload: 复制/剪切时把节点+关联边+鼠标位置一起记下
 *
 * P1-G (Phase 17.1): 改用 JSON 字符串而非结构化对象 — 100 节点 1 次 stringify 替代 100 次,
 *                    粘贴时 1 次 parse 替代 100 次. 内存中存字符串避免 Vue 把节点数组做深代理.
 */
interface ClipboardPayload {
  nodesJson: string
  edgesJson: string
  /** 复制/剪切时鼠标在浏览器视口的屏幕坐标 (event.clientX/Y) */
  mousePos: { x: number; y: number }
}
const clipboard = ref<ClipboardPayload | null>(null)
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
const portTypeFilter = ref<Set<string>>(new Set())
/** 切换某端口类型过滤（多选模式：选多个端口类型时节点含任一即匹配） */
function togglePortTypeFilter(t: string) {
  const next = new Set(portTypeFilter.value)
  if (next.has(t)) {
    next.delete(t)
  } else {
    next.add(t)
  }
  portTypeFilter.value = next
}
const portTypeFilterOptions = [
  { type: 'IMAGE', label: '图像' },
  { type: 'BBOX', label: '检测框' },
  { type: 'MODEL', label: '模型' },
  { type: 'STRING', label: '字符串' },
  { type: 'CONTROL', label: '控制' },
]

/** 节点是否匹配端口类型过滤。空集合视为全匹配；多选时节点含任一即通过。 */
function matchesPortType(node: NodeDefinition): boolean {
  const filter = portTypeFilter.value
  if (filter.size === 0) return true
  // 任一输入或输出端口匹配任一选中类型即通过
  const inputMatch = node.inputs?.some((p) => filter.has(p.type)) ?? false
  const outputMatch = node.outputs?.some((p) => filter.has(p.type)) ?? false
  return inputMatch || outputMatch
}

const filteredCategories = computed(() => {
  const query = nodeSearchQuery.value.trim().toLowerCase()
  const hasFilter = query || portTypeFilter.value.size > 0
  if (!hasFilter) {
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

// 默认边样式 - 不设置内联 style（避免与 CSS 三态规则冲突），
// stroke / stroke-width / stroke-opacity 全部由 .vue-flow__edge-path CSS 控制
const defaultEdgeOptions = {
  type: 'default',
  animated: false,
  markerEnd: MarkerType.ArrowClosed,
}

// 连接线样式 (用户拖拽新连线时显示)
const connectionLineStyle = {
  stroke: 'var(--accent-blue)',
  strokeWidth: 2,
  strokeOpacity: 0.7,
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
  if (isCtrl && event.key === 'a') {
    event.preventDefault()
    // 全选所有节点 (VueFlow 1.48 addSelectedNodes 签名接收 GraphNode[] 对象数组)
    addSelectedNodes(nodes.value as any)
    return
  }
}

/**
 * 拿到当前已选节点的 bounding box 中心点 (屏幕坐标).
 * 用于快捷键复制/剪切: 粘贴时按"当前鼠标 - bbox 中心"算偏移.
 * 不用鼠标位置是因为 Ctrl+C 触发时鼠标可能在画布外, 而 bbox 中心
 * 永远在选中集内, 跟用户视觉感知一致.
 */
function getSelectionBboxCenter(): { x: number; y: number } {
  const selectedEls = document.querySelectorAll('.vue-flow__node.selected')
  if (selectedEls.length === 0) return { x: 0, y: 0 }
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity
  for (const el of selectedEls) {
    const r = el.getBoundingClientRect()
    if (r.left < minX) minX = r.left
    if (r.top < minY) minY = r.top
    if (r.right > maxX) maxX = r.right
    if (r.bottom > maxY) maxY = r.bottom
  }
  return { x: (minX + maxX) / 2, y: (minY + maxY) / 2 }
}

// 复制
function handleCopy(_event?: MouseEvent) {
  // 关键: 从 store.nodes 过滤 selected. 用 getNodes.value 是 VueFlow 内部 ref,
  // shallowRef 内层 mutation (selected = true) 不会传播到 VueFlow 内部,
  // 用 store.nodes 才是数据源, 反映用户当前选择
  const selected = (store.nodes as any[]).filter((n) => n.selected)
  if (selected.length === 0) {
    ElMessage.warning('请先选择要复制的节点')
    return
  }
  // 收集选中节点之间的边 (源和目标都在选中集)
  const selectedIds = new Set(selected.map((n) => n.id))
  const relatedEdges = (edges.value as Edge[]).filter(
    (e) => selectedIds.has(e.source) && selectedIds.has(e.target)
  )
  // 参考点用 selection bbox 中心 (屏幕坐标), 粘贴时用 (当前鼠标 - bbox 中心) / zoom 算偏移
  // 不用鼠标位置是因快捷键触发时鼠标可能在画布外
  // P1-G (Phase 17.1): 一次性 stringify 替代每节点独立 stringify+parse
  // 旧: selected.map(n => JSON.parse(JSON.stringify(n))) → 100 节点 100 次 serialize+deserialize
  // 新: 1 次 stringify 100 节点, 粘贴时 1 次 parse
  clipboard.value = {
    nodesJson: JSON.stringify(selected),
    edgesJson: JSON.stringify(relatedEdges),
    mousePos: getSelectionBboxCenter()
  }
  clipboardMode.value = 'copy'
  ElMessage.success(`已复制 ${selected.length} 个节点`)
}

// 剪切
function handleCut(_event?: MouseEvent) {
  const selected = (store.nodes as any[]).filter((n) => n.selected)
  if (selected.length === 0) {
    ElMessage.warning('请先选择要剪切的节点')
    return
  }
  const selectedIds = new Set(selected.map((n) => n.id))
  const relatedEdges = (edges.value as Edge[]).filter(
    (e) => selectedIds.has(e.source) && selectedIds.has(e.target)
  )
  clipboard.value = {
    nodesJson: JSON.stringify(selected),
    edgesJson: JSON.stringify(relatedEdges),
    mousePos: getSelectionBboxCenter()
  }
  clipboardMode.value = 'cut'
  // 批量删除节点 + 关联边, 避免循环里反复重渲染
  const nodeIds = selected.map((n) => n.id)
  store.nodes = store.nodes.filter((n) => !nodeIds.includes(n.id))
  store.edges = (store.edges as Edge[]).filter(
    (e) => !nodeIds.includes(e.source) && !nodeIds.includes(e.target)
  )
  ElMessage.success(`已剪切 ${selected.length} 个节点`)
}

// 粘贴
function handlePaste(event?: MouseEvent) {
  if (!clipboard.value || clipboard.value.nodesJson == null) {
    ElMessage.warning('剪贴板为空')
    return
  }

  // P1-G (Phase 17.1): 1 次 parse 100 节点, 替代逐节点 stringify+parse
  const cp = clipboard.value
  const srcNodes: any[] = JSON.parse(cp.nodesJson)
  const srcEdges: any[] = JSON.parse(cp.edgesJson || '[]')
  const mousePos = cp.mousePos
  if (srcNodes.length === 0) {
    ElMessage.warning('剪贴板为空')
    return
  }

  // 计算鼠标偏移 (屏幕坐标 → 画布坐标)
  // Figma 模式: 偏移 = (当前鼠标 - 复制时鼠标) / 缩放
  // 优先级: event.clientX/Y > globalMousePos (快捷键场景) > +50/+50 fallback
  const currentMouse = event
    ? { x: event.clientX, y: event.clientY }
    : (globalMousePos.value.x || globalMousePos.value.y
        ? globalMousePos.value
        : null)
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
    // P1-G: srcNodes 已是 deep cloned JSON, 直接 mutate position + 补充选中态
    return {
      ...n,
      id: newNodeId,
      type: 'ruleNode',
      position: {
        x: n.position.x + offsetX,
        y: n.position.y + offsetY
      },
      // 粘贴时把新节点置为 selected: 视觉高亮, 方便用户继续操作 (拖动/再次粘贴/删除)
      // 复制粘贴: 原节点保持未选, 粘贴项 selected → 用户一眼看出新增了哪些
      // 剪切粘贴: 原节点已删, 粘贴项 selected → 用户可立即拖到目标位置
      selected: true,
      data: {
        ...(n.data || {}),
        id: newNodeId,
        selected: true
      }
    }
  })

  // 重映射边 — srcEdges 的端点都在复制集中
  const newEdges: Edge[] = srcEdges.map((e: any) => {
    const newEdgeId = `edge_${ts}_${(seq++).toString(36)}`
    return {
      ...e,
      id: newEdgeId,
      source: idMap.get(e.source) ?? e.source,
      target: idMap.get(e.target) ?? e.target
    } as Edge
  })

  // shallowRef 数组必须重新赋值触发响应式
  // 取消选中所有原节点, 只保留粘贴项 selected: true
  for (const n of store.nodes as any[]) {
    n.selected = false
  }
  store.nodes = [...store.nodes, ...newNodes]
  store.edges = [...(store.edges as Edge[]), ...newEdges]

  if (clipboardMode.value === 'cut') {
    clipboard.value = null
  }

  store.saveHistory()
  ElMessage.success(`已粘贴 ${newNodes.length} 个节点${newEdges.length > 0 ? `, ${newEdges.length} 条连线` : ''}`)
}

/**
 * cachedSelectionRect - 框选矩形缓存 (关键精度问题)
 *
 * VueFlow 在 onPointerUp 里先清空 userSelectionRect (line 219), 才 emit selectionEnd (line 222).
 * 到 selectionEnd 事件触发时, userSelectionRect.value 已经是 null.
 * 因此需要 watch userSelectionRect 把拖框过程中最后一帧的矩形缓存下来.
 * Vue watch 回调在微任务执行, onPointerUp 的同步链里 lastUserSelectionRect 还保留着上一次 move 的矩形.
 *
 * P1-E (Phase 17.1): 存 plain 引用而非 ref + 浅复制.
 * 旧: ref<...> + watch 60Hz 浅复制 + ref.set, 100 节点框选 5s = 300 次浅复制 + 300 次 ref 写入.
 * 新: plain 变量存引用, 0 浅复制. 当前实现 cachedSelectionRect 只用于诊断, 实际逻辑不再读它.
 */
let lastUserSelectionRect: { x: number; y: number; width: number; height: number; startX?: number; startY?: number } | null = null
watch(userSelectionRect, (rect) => {
  if (rect) {
    // 不复制对象, 存引用 — handleSelectionEnd 同步链里读到的就是最后 move 帧的 rect
    lastUserSelectionRect = rect as any
  }
})

// 框选开始 - 设 isBatchDragging 使 handleNodesChange 跳过所有 change (不再 60Hz × N 处理 select)
function handleSelectionStart() {
  isSelectionDragging.value = true
  isBatchDragging.value = true  // P0: 框选期间节流, handleNodesChange 立即 return
  store.setSelectionBoxActive(true) // LOD-1: 框选期间锁定 LOD
  lastUserSelectionRect = null
}

// 框选结束 - 用 VueFlow 内部 getSelectedNodes (selectedNodeIds) 同步到 store.nodes[].selected.
// 之前误加: 自己重做包围盒命中 (n.position + dimensions), 单位混用 (position 画布 + dimensions 屏幕 像素),
//          导致框外擦边被选. VueFlow 内部 getNodesInside 的 paneRect 跟 nodeToRect 同方向混用,
//          碰巧等价于画布空间, 实际命中结果是对的.
function handleSelectionEnd() {
  isSelectionDragging.value = false
  isBatchDragging.value = false  // P0: 恢复 nodes-change 处理
  store.setSelectionBoxActive(false) // LOD-1: 解除框选 LOD 锁定

  // 把 VueFlow 内部 selectedNodeIds 同步到 store.nodes[].selected
  // (复制 handleCopy/handleCut 依赖 store.nodes.filter(n => n.selected))
  const selectedIds = new Set(getSelectedNodes.value.map((n: any) => n.id))
  let changed = false
  for (const n of store.nodes as any[]) {
    const wasSelected = !!n.selected
    const shouldSelected = selectedIds.has(n.id)
    if (wasSelected !== shouldSelected) {
      n.selected = shouldSelected
      changed = true
    }
  }
  if (changed) {
  // P0-B (Phase 17.1): triggerRef 替代数组引用重建
    // 旧: store.nodes = [...store.nodes] → VueFlow useVModel 浅 watch 检测到引用变 → 整图 80 节点 vdom diff
    // 新: 数组引用不变 → patchProps 浅比较过滤 → VueFlow 不重渲染
    triggerRef(nodes)
  }

  // P1-E (Phase 17.1): ref 删除, 改用 plain 变量 lastUserSelectionRect
  lastUserSelectionRect = null
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

  // Phase B 任务4: 批量删除一次性 (单次 filter + 单次 saveHistory)
  const nodeIds = selectedNodes.map((n) => n.id)
  const edgeIds = selectedEdges.map((e) => e.id)
  if (nodeIds.length > 0) store.removeNodes(nodeIds)
  if (edgeIds.length > 0) store.removeEdges(edgeIds)
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
function handleContextAction(action: string, event?: MouseEvent) {
  switch (action) {
    case 'copy':
      // 复制触发源: 右键时 clientX/Y 即 mousePos
      handleCopy(event)
      hideContextMenu()
      break
    case 'cut':
      handleCut(event)
      hideContextMenu()
      break
    case 'paste':
      handlePaste(event)
      hideContextMenu()
      break
    case 'delete':
      // 右键未选中节点/边时, VueFlow 不会自动加 selected 标志,
      // handleDelete() 依赖 selected 过滤 → 静默失败.
      // 先把右键目标对象加入 selected, 再委托给 handleDelete()
      // (VueFlow addSelectedNodes/addSelectedEdges 签名接收 GraphNode[]/Edge[],
      //  内部用 .id 取值, 传对象数组而非字符串 ID 数组)
      if (contextMenu.targetType === 'node' && contextMenu.target) {
        addSelectedNodes([contextMenu.target as any])
      } else if (contextMenu.targetType === 'edge' && contextMenu.target) {
        addSelectedEdges([contextMenu.target as any])
      }
      handleDelete()
      hideContextMenu()
      break
    case 'selectAll':
      // 直接传节点对象数组（VueFlow 1.48 签名 GraphNode[]，传 id 字符串会 .id 取值变 undefined 静默失败）
      addSelectedNodes(nodes.value as any)
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
  // 全局鼠标位置追踪 — 快捷键 Ctrl+V 没有 MouseEvent, 需要 lastMousePos
  window.addEventListener('mousemove', (e) => {
    globalMousePos.value = { x: e.clientX, y: e.clientY }
  })
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

// 节点点击 (Phase 17.1+: 不再选节点进右侧面板, 仅做选中视觉同步 + 高亮)
// 双击走 handleNodeDoubleClick 进入 LOD 2 内嵌配置
function handleNodeClick(event: any) {
  // 单击: 仅清空/保留 selected 状态, 真正的配置编辑靠双击
  // 这样避免误点击打开/关闭右侧面板的视觉跳变
  // (如果未来要支持"单击预览", 可在此处加 store.setSelectedId(event.node.id))
}

// 节点双击 → 切换 LOD 2 展开 (Phase 17.1+)
function handleNodeDoubleClick(event: any) {
  const nodeId = event?.node?.id
  if (nodeId) store.toggleNodeExpanded(nodeId)
}

// 节点拖拽 (路径 B: 由 useCogniFlowDrag composable 完全接管)
// 之前 @node-drag-start/@node-drag-stop + handleNodeDragStart/Stop + dragStartPositions
// 已删除: vue-flow 内部 useDrag 通过 :nodes-draggable="false" 关闭, 不再 emit 这些事件.
// 拖动行为由 useCogniFlowDrag (见下) 通过 d3-drag 直接接管节点 wrapper DOM,
// 拖动期间 0 次响应式写入, drag-end 一次性 setNodesPositions + recordMoveHistory.

// 画布点击
function handlePaneClick() {
  // 清除所有节点的选中态 (含 VueFlow 视觉 CSS)
  let changed = false
  for (const n of store.nodes as any[]) {
    if (n.selected) {
      n.selected = false
      changed = true
    }
  }
  // P0-B (Phase 17.1): triggerRef 替代数组引用重建 (避免 VueFlow 整图 diff)
  if (changed) triggerRef(nodes)
  // Phase 17.1+: 点空白收起所有展开的节点 (用户切回画布视角的常见操作)
  store.collapseAllExpanded()
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
  // Phase B 任务6: 用 store.nodeById O(1) 查询替换 nodes.value.find
  const node = store.nodeById.get(nodeId)
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
  // Phase B 任务6: 用 store.nodeById O(1) 查询
  const sourceNode = store.nodeById.get(source)
  const targetNode = store.nodeById.get(target)

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

  const edge = {
    source: params.source,
    target: params.target,
    sourceHandle: params.sourceHandle,
    targetHandle: params.targetHandle
  }
  store.addEdge(edge)
}

// 框选拖拽标志: 框选拖拽期间过滤 select changes (避免每帧全量替换 store.nodes)
// 单击选中/Ctrl+A 等其他场景仍需正常处理 select changes
const isSelectionDragging = ref(false)
/** P0 多节点拖拽节流: 拖拽中的 change 全部跳过, stop 统一同步。
 *  true 时 handleNodesChange 立即 return, 不进行任何拆分/循环/处理,
 *  消除多节点拖拽时 60Hz × N 节点的函数调用开销 */
const isBatchDragging = ref(false)

// 节点/边变化 - manual control 模式
// 拖拽中（dragging=true）的 position 变化不写回 store（每帧 60Hz 会爆）
// 框选拖拽中（isSelectionDragging）的 select 变化不写回 store（drag-stop 统一 sync）
// 仅在拖拽结束（dragging=false）或非 position/select 类型变更时应用
//
// P0-1 优化：drag-stop 的 position change 走轻量路径，**不调用** applyVueFlowNodeChanges。
// 旧实现: store.nodes = newNodes → 数组引用替换 → storeToRefs trigger → 父组件 re-render →
//         VueFlow 内部 useVModel 浅 watch 检测到 props.nodes 引用变 → 整图 80 节点 vdom diff。
// 新实现: mutate store.nodes[i].position + triggerRef(nodes) → 数组引用不变 →
//         Vue 父组件重渲染但 patchProps 浅比较发现引用未变 → VueFlow 不重渲染。
// 收益: 拖完 1 节点从 O(80) vdom diff 降到 O(1) 属性写入。
function handleNodesChange(changes: any[]) {
  if (changes.length === 0) return

  // === P0 多节点拖拽节流: 拖拽中(含框选拖拽)全部跳过, stop 统一同步 ===
  // 多节点拖拽时 VueFlow 每帧 emit N 个 position change (dragging=true),
  // 虽然当前代码已经跳过了 dragging=true 的 position, 但 change 数组的
  // 遍历/类型检查/循环本身在 60Hz × 50 节点下就是 ~3000 次/秒的函数调用.
  // isBatchDragging 让 handleNodesChange 立即 return, 零成本.
  if (isBatchDragging.value) return

  // === 阶段 1: 拆分三类 change ===
  // P0: dimensions change 不携带位置信息，忽略（节点初次渲染后尺寸稳定，
  //     即使微调也不影响画布拓扑，跳过可消除 80+ 节点时 90% 的全量 diff）
  // positionChanges: drag-stop 持久化（走轻量 mutate 路径，避免整图重渲染）
  // meaningful: add/remove/select，走 VueFlow 完整重算
  const positionChanges: any[] = []
  const meaningful: any[] = []
  for (const c of changes) {
    // 拖拽中 transient position —— VueFlow 内部自有管理，跳过
    if (c.type === 'position' && c.dragging === true) continue
    // 框选拖拽中 transient select —— handleSelectionDragStop 统一处理
    if (c.type === 'select' && isSelectionDragging.value) continue
    // 拖拽结束 position change —— 走轻量 mutate 路径
    if (c.type === 'position' && c.dragging === false) {
      positionChanges.push(c)
      continue
    }
    // P0: dimensions change —— 不影响拓扑/选中/删除，跳过全量重算
    if (c.type === 'dimensions') continue
    // 其他（add/remove/select 正常场景）走 VueFlow 完整重算
    meaningful.push(c)
  }

  // === 阶段 2: position 轻量持久化（drag-stop 路径，60Hz 不会触发这里）===
  // 关键: nodes.value.find().position 赋值是 O(1) 属性写入，不替换数组引用。
  // triggerRef 仅通知 deps（父组件 render effect），但 patchProps 浅比较会过滤掉引用未变的情况。
  if (positionChanges.length > 0) {
    // P0-D (Phase 17.1): O(1) Map 查询替代 O(N) Array.find
    // drag-stop 多节点拖动 → positionChanges.length = K, 改前 K×N 次比较 → 改后 K 次 Map.get
    for (const c of positionChanges) {
      const node = store.nodeById.get(c.id)
      if (node && c.position) {
        // 替换整个 position 对象（VueFlow 内部已存了完整 position 数据）
        node.position = c.position
      }
    }
    // 手动通知响应式 —— 不替换 .value 数组引用，避免 VueFlow useVModel 浅 watch 误判变化
    triggerRef(nodes)
    // 注意: 不调 saveHistory —— unpauseHistory 在 @node-drag-stop 时已记录 drag 前的旧 position，
    // 撤销回到 drag 前的位置是用户期望行为。
  }

  // === 阶段 3: 其他 change 走 VueFlow 完整重算路径（低频）===
  if (meaningful.length === 0) return
  const newNodes = applyVueFlowNodeChanges(meaningful)
  // remove 类型：附带清理孤立边 + 保存历史
  const hasRemoval = meaningful.some(c => c.type === 'remove')
  if (hasRemoval) {
    const remainingIds = new Set(newNodes.map(n => n.id))
    store.edges = store.edges.filter((e: Edge) =>
      remainingIds.has(e.source) && remainingIds.has(e.target)
    ) as any
    // Phase 17.1+: 同步清理展开状态 (删除节点时, 它的 LOD 2 展开态也得收)
    // 之前是清 selectedNodeId (右侧面板) — 现在是清 expandedNodeIds (内嵌配置)
    const removedIds = new Set(meaningful.filter(c => c.type === 'remove').map(c => c.id))
    if (removedIds.size > 0 && store.expandedNodeIds.size > 0) {
      let changed = false
      for (const id of removedIds) {
        if (store.expandedNodeIds.has(id)) {
          store.expandedNodeIds.delete(id)
          changed = true
        }
      }
      if (changed) triggerRef(store.expandedNodeIds)
    }
  }
  store.nodes = newNodes as any
  if (hasRemoval) store.saveHistory()
}

function handleEdgesChange(changes: any[]) {
  if (changes.length === 0) return
  const newEdges = applyVueFlowEdgeChanges(changes)
  const hasRemoval = changes.some(c => c.type === 'remove')
  store.edges = newEdges as any
  if (hasRemoval) store.saveHistory()
}

// P1-2: 原 handlePan 死代码 (panX/panY 从未被消费) 已删除

function handleZoom(viewport: { x: number; y: number; zoom: number }) {
  // P0-2: 缩放走 DOM textContent 直写, 不走模板响应式
  // 60Hz 触发不重渲染父组件, 仅一次 DOM 属性写入
  const { zoom } = viewport
  const text = `${Math.round(zoom * 100)}%`
  if (text !== lastZoomText) {
    lastZoomText = text
    if (zoomLevelEl.value) {
      zoomLevelEl.value.textContent = text
    }
  }
  // 同步 zoomLevel ref (供 zoomIn/zoomOut/quickAddNode 读, 不参与响应式)
  zoomLevel.value = zoom
  // LOD-1: 同步到 store, 触发 lodLevelMap 重新计算 (rAF 节流, 避免 60Hz 重建 80 entries Map)
  scheduleViewportZoomUpdate(zoom)
}

/** rAF 节流: 累积 zoom 值, 在下次 rAF 回调里一次性写入 store, 避免 60Hz 触发 80 entries Map 重建 */
let viewportZoomRafId = 0
let pendingZoom = 1
function scheduleViewportZoomUpdate(zoom: number) {
  pendingZoom = zoom
  if (!viewportZoomRafId) {
    viewportZoomRafId = requestAnimationFrame(() => {
      viewportZoomRafId = 0
      store.setViewportZoom(pendingZoom)
    })
  }
}

function handleWheel(event: WheelEvent) {
  if (event.ctrlKey) event.preventDefault()
}

function handleCanvasMouseDown(event: MouseEvent) {
  if (event.button === 1 || (event.button === 0 && event.altKey)) {
    isPanning.value = true
    lastMousePos.value = { x: event.clientX, y: event.clientY }
    // Phase 17.3: 拖动期间直接改 transformationpane transform, 绕过 vue-flow
    // 起点记下当前 viewport, mousemove 时算 dx/dy 累加, mouseup 时统一 setViewport
    const vp = getViewport()
    panStartViewport = { x: vp.x, y: vp.y, zoom: vp.zoom }
    // 锁光标 (CSS 拖动)
    document.body.style.cursor = 'grabbing'
    event.preventDefault()
  }
}

/**
 * 拖动起点 viewport 快照 — 用于 mousemove 时计算绝对 pan 位置
 * (相对位移用 lastMousePos 即可, 但需要起点 viewport 才能算出最终 setViewport 值)
 */
let panStartViewport: { x: number; y: number; zoom: number } = { x: 0, y: 0, zoom: 1 }

/** rAF 节流标志: 避免全选后拖拽时 mousemove 高频触发 setViewport 导致卡顿 */
let panningRafId = 0
/** 累积拖拽偏移 (在 rAF 回调里消费) */
const panAccum = { x: 0, y: 0 }

function handleCanvasMouseMove(event: MouseEvent) {
  if (isPanning.value) {
    const dx = event.clientX - lastMousePos.value.x
    const dy = event.clientY - lastMousePos.value.y
    lastMousePos.value = { x: event.clientX, y: event.clientY }
    panAccum.x += dx
    panAccum.y += dy
    // rAF 节流: 累积所有 mousemove 的偏移, 在一次 rAF 回调里批量消费,
    // 避免 60Hz 高频 setViewport 重排导致卡顿
    if (!panningRafId) {
      panningRafId = requestAnimationFrame(() => {
        panningRafId = 0
        // Phase 17.3: 直写 transformationpane transform 绕过 vue-flow
        // 不调用 setViewport (不走 d3-zoom.transform → 'zoom' 事件 → 整响应式链)
        // 拖动结束 (mouseup) 时再 setViewport 一次性同步 store
        const tp = document.querySelector<HTMLElement>('.vue-flow__transformationpane')
        if (tp) {
          const newX = panStartViewport.x + panAccum.x
          const newY = panStartViewport.y + panAccum.y
          tp.style.transform = `translate(${newX}px, ${newY}px) scale(${panStartViewport.zoom})`
        }
        panAccum.x = 0
        panAccum.y = 0
      })
    }
  }
}

function handleCanvasMouseUp() {
  if (isPanning.value) {
    // 拖动结束: 一次性 setViewport 同步 vue-flow 内部 viewport ref
    // (Transform.vue 的 transform computed 才能拿到正确 viewport 值)
    const tp = document.querySelector<HTMLElement>('.vue-flow__transformationpane')
    if (tp) {
      // 读当前实际 transform (被我们直写过), 解析 x/y
      const match = tp.style.transform.match(/translate\(([-\d.]+)px,\s*([-\d.]+)px\)\s*scale\(([-\d.]+)\)/)
      if (match) {
        const x = parseFloat(match[1])
        const y = parseFloat(match[2])
        const zoom = parseFloat(match[3])
        setViewport({ x, y, zoom })
      }
    }
    // 释放光标
    document.body.style.cursor = ''
  }
  isPanning.value = false
  isResizingPanel.value = false
  // 清除可能残留的 rAF + 重置累积偏移, 避免鼠标抬起后还触发 setViewport
  if (panningRafId) {
    cancelAnimationFrame(panningRafId)
    panningRafId = 0
    panAccum.x = 0
    panAccum.y = 0
  }
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
    // 缩略图生成较重（base64 编码 + HTTP），用 requestIdleCallback 推迟到
    // 浏览器空闲时执行，避免阻塞主流程的 ElMessage.success() 反馈
    // inflight 标志位：连击"保存"时若上一次 captureAndSaveThumbnail 仍在跑，跳过本次
    if (!thumbnailInflight.value) {
      thumbnailInflight.value = true
      const scheduleIdle: (cb: () => void) => void =
        (window as any).requestIdleCallback || ((cb) => setTimeout(cb, 100))
      scheduleIdle(async () => {
        try {
          await captureAndSaveThumbnail()
        } finally {
          thumbnailInflight.value = false
        }
      })
    }
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

    canvas.width = 80
    canvas.height = 60
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

// Phase B 任务5: 大图渲染降级
// ≥80 节点: 去除节点阴影 / transition / 边动画, 降低 paint 成本；
//           边半透明减淡 + 减细，减少 SVG path 对帧率的消耗
// ≥200 节点: 额外隐藏节点摘要 / 端口 label
.large-graph-mode {
  :deep(.rule-node) {
    box-shadow: none !important;
    transition: none !important;
  }

  :deep(.rule-node:hover) {
    box-shadow: none !important;
  }

  :deep(.vue-flow__edge-path) {
    transition: none !important;
    stroke-opacity: 0.2 !important;
    stroke-width: 1.5 !important;
  }

  :deep(.vue-flow__edge.animated .vue-flow__edge-path) {
    animation: none !important;
  }

  // hover 态同步降级，避免半透明边 hover 时突兀跳变
  :deep(.vue-flow__edge:hover .vue-flow__edge-path) {
    stroke-opacity: 0.4 !important;
    stroke-width: 1.5 !important;
  }

  // 连线选中态保持可辨识
  :deep(.vue-flow__edge.selected .vue-flow__edge-path) {
    stroke-opacity: 1 !important;
    stroke-width: 2.5 !important;
  }
}

.huge-graph-mode {
  :deep(.node-summary) {
    display: none !important;
  }

  :deep(.port-label) {
    display: none !important;
  }
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

// 左侧节点面板 (折叠时整段隐藏 — 完全收纳)
// Phase 17.1+: 删除了右侧 .properties-panel SCSS 块 (改用 RuleNode LOD 2 内嵌配置)
.node-palette {
  width: $palette-width;
  background: #0e0e14;
  border-right: 1px solid #1e1e2e;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  z-index: 50;
  position: relative;
  overflow: visible;
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

// 工具栏 panel-left 折叠按钮 (32x32，比普通 icon-btn 略大)
.palette-toggle-btn {
  width: 32px !important;
  height: 32px !important;
  margin-right: 4px !important;
  background: transparent !important;
  border: 1px solid transparent !important;
  border-radius: 6px !important;
  color: #888 !important;
  padding: 0 !important;
  display: flex !important;
  align-items: center;
  justify-content: center;
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
    width: 16px;
    height: 16px;
  }

  &:hover {
    background: rgba(0, 240, 255, 0.06) !important;
    color: #00f0ff !important;
    border-color: rgba(0, 240, 255, 0.2) !important;
  }

  &.active {
    background: rgba(0, 240, 255, 0.1) !important;
    color: #00f0ff !important;
    border-color: rgba(0, 240, 255, 0.3) !important;
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

  /* 拖拽性能优化: 为每个节点 wrapper 创建独立合成层,
     GPU 直接位移跳过 repaint, 与 CSS containment 配合隔离布局重算 */
  :deep(.vue-flow__node) {
    will-change: transform;
    contain: layout style;
  }

  /* 节点选中视觉效果 — 通过父 wrapper 的 .selected class 驱动 (纯 CSS, 不触发 RuleNode 重渲染)
     VueFlow 在框选/点击时自动给 .vue-flow__node 添加 .selected, 结束后移除。
     RuleNode.vue 的 v-memo 不含 selected → 选中态变化不触发 Element Plus widget 重渲染

     关键: 用 outline 替代 border-width 变化 (2px→1px)。
     border-width 改变盒模型 → 每次选中/取消选中强制 layout → 80 节点框选 = 80 次 layout
     outline 在盒模型外部绘制, 不触发布局, 配合 outline-offset: -1px 紧贴 border 内侧 */
  :deep(.vue-flow__node.selected .rule-node) {
    outline: 2px solid var(--accent-blue);
    outline-offset: -3px;
    border-radius: 6px;
    box-shadow:
      inset 0 1px 0 rgba(255,255,255,0.08),
      0 4px 16px rgba(0,0,0,0.4);
  }
  :deep(.vue-flow__node.selected .rule-node.category-input)      { outline-color: #4CFF4C; box-shadow: inset 0 1px 0 rgba(255,255,255,0.08), 0 0 0 1px rgba(76,255,76,0.3),   0 4px 16px rgba(0,0,0,0.4); }
  :deep(.vue-flow__node.selected .rule-node.category-detection)  { outline-color: #00f0FF; box-shadow: inset 0 1px 0 rgba(255,255,255,0.08), 0 0 0 1px rgba(0,240,255,0.3),  0 4px 16px rgba(0,0,0,0.4); }
  :deep(.vue-flow__node.selected .rule-node.category-processing) { outline-color: #FFFF4C; box-shadow: inset 0 1px 0 rgba(255,255,255,0.08), 0 0 0 1px rgba(255,255,76,0.3),  0 4px 16px rgba(0,0,0,0.4); }
  :deep(.vue-flow__node.selected .rule-node.category-action)     { outline-color: #FF7F4C; box-shadow: inset 0 1px 0 rgba(255,255,255,0.08), 0 0 0 1px rgba(255,127,76,0.3),  0 4px 16px rgba(0,0,0,0.4); }
  :deep(.vue-flow__node.selected .rule-node.category-logic)      { outline-color: #DC4FDC; box-shadow: inset 0 1px 0 rgba(255,255,255,0.08), 0 0 0 1px rgba(220,79,220,0.3),  0 4px 16px rgba(0,0,0,0.4); }
  :deep(.vue-flow__node.selected .rule-node.category-output)     { outline-color: #FF4C4C; box-shadow: inset 0 1px 0 rgba(255,255,255,0.08), 0 0 0 1px rgba(255,76,76,0.3),  0 4px 16px rgba(0,0,0,0.4); }

  /* 连接线：未选中 35% 蓝、悬停 70%、选中 100% 青色 + 发光 (决策 2) */
  :deep(.vue-flow__edge-path) {
    stroke: var(--accent-blue);
    stroke-width: 2;
    stroke-opacity: 0.35;
    transition: stroke 0.15s ease, stroke-width 0.15s ease, stroke-opacity 0.15s ease;
  }

  :deep(.vue-flow__edge.animated .vue-flow__edge-path) {
    stroke-dasharray: 5;
    animation: dash 0.5s linear infinite;
  }

  /* 连线选中态：100% 青色 + 加粗（去掉 12px interaction 感应层外圈高亮,
     只改 path 颜色和粗细, 跟节点选中态保持一致的"只改颜色"风格） */
  :deep(.vue-flow__edge.selected .vue-flow__edge-path) {
    stroke: #00f0ff !important;
    stroke-width: 3 !important;
    stroke-opacity: 1 !important;
  }

  /* 取消选中态 interaction 感应层的 12px 宽发光 (用户反馈"更宽的连续"多余视觉)
     关键: 拖动过程中 Tier 2 边增量更新器只写 path.d, 不写 interaction.d
     (interaction 的 d 保持陈旧旧值). 拖动中如果 interaction 有任何可见像素,
     就会看到"旧位置"的残影 (interaction d 没跟手). 必须强制完全隐藏:
     - display: none: 整个 path 元素不渲染 (最彻底, 不依赖 stroke)
     - !important: 覆盖 vue-flow 内部/attribute 优先级 */
  :deep(.vue-flow__edge.selected .vue-flow__edge-interaction) {
    display: none !important;
  }

  /* hover 态：70% 蓝过渡 */
  :deep(.vue-flow__edge:hover .vue-flow__edge-path) {
    stroke-opacity: 0.7;
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

// Phase 17.1+: 删除了 .properties-panel 块 (改用 RuleNode LOD 2 内嵌配置)


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
  display: flex;
  flex-direction: column;

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
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
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
  flex: 1;
  min-height: 0;
  position: relative;
}

.logs-scroller {
  width: 100%;
  height: 100%;
}

.log-entry {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 16px;
  border-bottom: 1px solid #1a1a24;
  font-size: 12px;
  height: 34px;
  box-sizing: border-box;

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
  padding: 20px 16px;
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

/* === Tier 0 性能优化: 拖动期间整层边的命中测试关闭 ===
   减少浏览器 hit-test 开销 (100 节点 + 200 边时 hit-test 占 1-2ms/帧)
   :has() 选择器需要 Chrome 105+ / Safari 15.4+ / Firefox 121+ */
.rule-canvas-fullscreen:has(.vue-flow__node.dragging) .vue-flow__edges {
  pointer-events: none;
}

</style>
