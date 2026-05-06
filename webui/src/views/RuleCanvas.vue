<template>
  <div class="rule-canvas-fullscreen">
    <!-- 顶部工具栏 -->
    <header class="canvas-header">
      <div class="header-left">
        <button class="icon-btn back-btn" @click="goBack" title="返回规则列表">
          <SvgIcon name="back" />
        </button>
        <div class="rule-name-section">
          <input
            type="text"
            class="rule-name-input"
            v-model="graphName"
            @blur="handleNameChange"
            @keyup.enter="$event.target.blur()"
            placeholder="规则名称..."
          />
          <span class="rule-status-badge" :class="{ active: graph?.is_active }">
            {{ graph?.is_active ? '运行中' : '已停止' }}
          </span>
        </div>
      </div>

      <div class="header-center">
        <div class="tool-group">
          <button class="icon-btn" @click="handleUndo" :disabled="!canUndo" title="撤销 (Ctrl+Z)">
            <SvgIcon name="undo" />
          </button>
          <button class="icon-btn" @click="handleRedo" :disabled="!canRedo" title="重做 (Ctrl+Y)">
            <SvgIcon name="redo" />
          </button>
        </div>

        <div class="tool-divider"></div>

        <div class="tool-group">
          <button class="icon-btn" @click="zoomIn" title="放大">
            <SvgIcon name="zoom-in" />
          </button>
          <span class="zoom-level">{{ Math.round(zoomLevel * 100) }}%</span>
          <button class="icon-btn" @click="zoomOut" title="缩小">
            <SvgIcon name="zoom-out" />
          </button>
          <button class="icon-btn" @click="fitView" title="适应画布">
            <SvgIcon name="fit-view" />
          </button>
        </div>

        <div class="tool-divider"></div>

        <div class="tool-group">
          <button class="icon-btn" :class="{ active: showGrid }" @click="showGrid = !showGrid" title="显示网格">
            <SvgIcon name="grid" />
          </button>
          <button class="icon-btn" :class="{ active: snapGrid }" @click="snapGrid = !snapGrid" title="网格吸附">
            <SvgIcon name="snap" />
          </button>
          <button class="icon-btn" :class="{ active: showMiniMap }" @click="showMiniMap = !showMiniMap" title="小地图">
            <SvgIcon name="minimap" />
          </button>
        </div>
      </div>

      <div class="header-right">
        <button class="action-btn secondary" @click="handleValidate">
          <SvgIcon name="check" />
          校验
        </button>
        <button class="action-btn secondary" @click="handleSave" :disabled="saving">
          <SvgIcon name="save" />
          {{ saving ? '保存中...' : '保存' }}
        </button>
        <button class="action-btn primary" @click="handleExecute" :disabled="executing || !hasNodes">
          <SvgIcon name="play" />
          {{ executing ? '执行中...' : '执行' }}
        </button>
      </div>
    </header>

    <!-- 主体区域 -->
    <div class="canvas-body">
      <!-- 左侧节点面板 -->
      <aside class="node-palette" :class="{ collapsed: !showPalette }">
        <div class="palette-header">
          <h3 v-if="showPalette">节点库</h3>
          <button class="collapse-btn" @click="showPalette = !showPalette">
            <SvgIcon name="chevron-left" :class="{ rotated: !showPalette }" />
          </button>
        </div>

        <div class="palette-content" v-show="showPalette">
          <div
            v-for="category in nodeCategories"
            :key="category.name"
            class="node-category"
          >
            <div class="category-header" @click="category.expanded = !category.expanded">
              <div class="category-icon-wrapper" :class="category.name">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <component :is="category.icon" />
                </svg>
              </div>
              <span class="category-name">{{ category.label }}</span>
              <span class="category-count">{{ category.nodes.length }}</span>
              <SvgIcon class="chevron" :class="{ expanded: category.expanded }" name="chevron" />
            </div>

            <div v-show="category.expanded" class="node-list">
              <div
                v-for="node in category.nodes"
                :key="node.type"
                class="node-item"
                draggable="true"
                @dragstart="handleDragStart($event, node)"
                @dblclick="quickAddNode(node)"
              >
                <div class="node-icon-wrapper" :class="category.name">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <component :is="category.icon" />
                  </svg>
                </div>
                <div class="node-info">
                  <span class="node-label">{{ node.label }}</span>
                  <span class="node-type-hint">{{ node.description || node.type }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </aside>

      <!-- 画布区域 -->
      <div class="canvas-wrapper" ref="canvasWrapper">
        <!-- 顶部标尺 -->
        <div class="ruler ruler-horizontal" v-if="showRulers">
          <div class="ruler-content" :style="{ width: canvasWidth + 'px', transform: `translateX(${-panX}px)` }">
            <span v-for="i in Math.ceil(canvasWidth / rulerStep)" :key="i" class="ruler-mark" :style="{ left: (i - 1) * rulerStep + 'px' }">
              {{ (i - 1) * rulerStep }}
            </span>
          </div>
        </div>

        <!-- 左侧标尺 -->
        <div class="ruler ruler-vertical" v-if="showRulers">
          <div class="ruler-content" :style="{ height: canvasHeight + 'px', transform: `translateY(${-panY}px)` }">
            <span v-for="i in Math.ceil(canvasHeight / rulerStep)" :key="i" class="ruler-mark" :style="{ top: (i - 1) * rulerStep + 'px' }">
              {{ (i - 1) * rulerStep }}
            </span>
          </div>
        </div>

        <!-- VueFlow 画布 -->
        <div
          class="flow-container"
          ref="flowContainer"
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
            :snap-to-grid="snapGrid"
            :snap-grid="[gridSize, gridSize]"
            fit-view-on-init
            @node-click="handleNodeClick"
            @node-drag-stop="handleNodeDragStop"
            @pane-click="handlePaneClick"
            @connect="handleConnect"
            @move="handlePan"
            @zoom="handleZoom"
            @nodes-change="handleNodesChange"
            @edges-change="handleEdgesChange"
            @node-context-menu="(event: any, node: any) => handleContextMenu(event, node, 'node')"
            @pane-context-menu="(event: any) => handleContextMenu(event, null, 'pane')"
            @edge-context-menu="(event: any, edge: any) => handleContextMenu(event, edge, 'edge')"
            :pan-on-scroll="true"
            :zoom-on-scroll="true"
            :min-zoom="0.1"
            :max-zoom="4"
            :nodes-draggable="true"
            :nodes-connectable="true"
            :elements-selectable="true"
            :select-nodes-on-drag="true"
          >
            <!-- 点阵背景 -->
            <Background
              v-if="showGrid"
              :pattern-color="gridColor"
              :gap="gridSize"
              :size="gridSize"
            />

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
          <div class="empty-state" v-if="nodes.length === 0 && !isLoading">
            <div class="empty-icon">
              <SvgIcon name="stream" />
            </div>
            <h3>开始设计规则流程</h3>
            <p>从左侧拖拽节点到画布，或双击节点快速添加</p>
            <div class="quick-add-nodes">
              <button
                v-for="node in quickAddNodes"
                :key="node.type"
                class="quick-add-btn"
                @click="quickAddNode(node)"
              >
                <span class="btn-icon" :class="node.category">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <component :is="getCategoryIcon(node.category)" />
                  </svg>
                </span>
                {{ node.label }}
              </button>
            </div>
          </div>

          <!-- 加载状态 -->
          <div class="loading-state" v-if="isLoading">
            <div class="spinner"></div>
            <span>加载规则图...</span>
          </div>
        </div>
      </div>

      <!-- 右侧属性面板 -->
      <aside class="properties-panel" :class="{ visible: selectedNode }">
        <template v-if="selectedNode">
          <div class="panel-header">
            <div class="panel-title">
              <span class="panel-icon" :class="selectedNode.category">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <component :is="getCategoryIcon(selectedNode.category)" />
                </svg>
              </span>
              <div class="panel-title-text">
                <span class="node-name">{{ selectedNode.label }}</span>
                <span class="node-type-label">{{ selectedNode.type }}</span>
              </div>
            </div>
            <button class="close-btn" @click="selectedNode = null">
              <SvgIcon name="close" />
            </button>
          </div>

          <div class="panel-body">
            <!-- 节点描述 -->
            <div class="config-section" v-if="selectedNode.description">
              <div class="section-label">描述</div>
              <p class="node-description">{{ selectedNode.description }}</p>
            </div>

            <!-- 参数配置 -->
            <div class="config-section">
              <div class="section-label">参数配置</div>
              <div class="config-form">
                <div
                  v-for="(schema, key) in selectedNode.configSchema?.properties || {}"
                  :key="key"
                  class="form-field"
                >
                  <label class="field-label">{{ schema.title || key }}</label>

                  <!-- 字符串输入 -->
                  <div class="field-input-wrapper">
                    <input
                      v-if="schema.type === 'string' && !schema.enum"
                      type="text"
                      :value="nodeConfig[key]"
                      @input="updateConfig(key, ($event.target as HTMLInputElement).value)"
                      class="field-input"
                      placeholder="请输入..."
                    />
                    <button
                      class="var-btn"
                      @click="showVariableMenu(key, $event)"
                      title="插入变量"
                    >📎</button>
                  </div>

                  <!-- 数字输入 -->
                  <div class="field-input-wrapper">
                    <input
                      v-else-if="schema.type === 'number' || schema.type === 'integer'"
                      type="number"
                      :min="schema.minimum"
                      :max="schema.maximum"
                      :step="schema.type === 'integer' ? 1 : 0.1"
                      :value="nodeConfig[key]"
                      @input="updateConfig(key, Number(($event.target as HTMLInputElement).value))"
                      class="field-input"
                    />
                    <button
                      class="var-btn"
                      @click="showVariableMenu(key, $event)"
                      title="插入变量"
                    >📎</button>
                  </div>

                  <!-- 布尔选择 -->
                  <select
                    v-else-if="schema.type === 'boolean'"
                    :value="String(nodeConfig[key])"
                    @change="updateConfig(key, ($event.target as HTMLSelectElement).value === 'true')"
                    class="field-select"
                  >
                    <option value="true">是</option>
                    <option value="false">否</option>
                  </select>

                  <!-- 枚举选择 -->
                  <select
                    v-else-if="schema.enum"
                    :value="nodeConfig[key]"
                    @change="updateConfig(key, ($event.target as HTMLSelectElement).value)"
                    class="field-select"
                  >
                    <option v-for="opt in schema.enum" :key="opt" :value="opt">{{ opt }}</option>
                  </select>

                  <!-- 数组输入 -->
                  <div v-else-if="schema.type === 'array'" class="array-field">
                    <div
                      v-for="(item, idx) in (nodeConfig[key] || [])"
                      :key="idx"
                      class="array-item"
                    >
                      <input
                        type="text"
                        :value="item"
                        @input="updateArrayItem(key, idx, ($event.target as HTMLInputElement).value)"
                        class="field-input"
                      />
                      <button class="remove-btn" @click="removeArrayItem(key, idx)">
                        <SvgIcon name="close" />
                      </button>
                    </div>
                    <button class="add-item-btn" @click="addArrayItem(key)">
                      <SvgIcon name="plus" />
                      添加
                    </button>
                  </div>

                  <span class="field-default" v-if="schema.default !== undefined">
                    默认: {{ JSON.stringify(schema.default) }}
                  </span>
                </div>
              </div>
            </div>

            <!-- 连接信息 -->
            <div class="config-section">
              <div class="section-label">连接</div>
              <div class="ports-display">
                <div class="ports-row" v-if="selectedNode.inputs?.length">
                  <div
                    v-for="input in selectedNode.inputs"
                    :key="input.name"
                    class="port-item"
                  >
                    <span class="port-chip input">{{ input.label || input.name }}</span>
                    <template v-if="getInputConnection(input.name)">
                      <span class="port-connected">
                        → {{ getInputConnection(input.name)?.sourceNode?.label || getInputConnection(input.name)?.sourceNode?.type }}
                      </span>
                      <button class="port-disconnect" @click="disconnectInput(input.name)" title="断开连接">×</button>
                    </template>
                    <span v-else class="port-disconnected">[未连接]</span>
                  </div>
                </div>
                <div class="ports-row" v-if="selectedNode.outputs?.length">
                  <div
                    v-for="output in selectedNode.outputs"
                    :key="output.name"
                    class="port-item"
                  >
                    <span class="port-chip output">{{ output.label || output.name }}</span>
                    <span class="port-outgoing">→</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </template>

        <div class="no-selection" v-else>
          <SvgIcon name="alert" />
          <p>选择画布上的节点<br>查看和编辑属性</p>
        </div>
      </aside>
    </div>

    <!-- 执行日志面板 -->
    <div class="execution-panel" :class="{ expanded: showExecutionPanel }">
      <div class="execution-header" @click="showExecutionPanel = !showExecutionPanel">
        <div class="execution-title">
          <SvgIcon name="file-text" />
          <span>执行日志</span>
          <span class="execution-status" :class="executionStatus">{{ executionStatusText }}</span>
        </div>
        <div class="execution-actions">
          <button class="icon-btn small" @click.stop="clearLogs" v-if="showExecutionPanel">
            <SvgIcon name="trash" />
          </button>
          <SvgIcon class="expand-icon" :class="{ expanded: showExecutionPanel }" name="chevron" />
        </div>
      </div>

      <div class="execution-content" v-show="showExecutionPanel">
        <!-- 进度条 -->
        <div class="progress-bar-wrapper" v-if="executionStatus === 'running'">
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: executionProgress + '%' }"></div>
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
            <span class="log-node" v-if="log.node_type">{{ log.node_type }}</span>
            <span class="log-message">{{ log.message }}</span>
          </div>
          <div v-if="executionLogs.length === 0" class="no-logs">
            暂无执行日志
          </div>
        </div>
      </div>
    </div>

    <!-- Toast 提示 -->
    <transition name="toast">
      <div class="toast-notification" v-if="toast.show" :class="toast.type">
        {{ toast.message }}
      </div>
    </transition>

    <!-- 右键菜单 -->
    <div
      v-if="contextMenu.show"
      class="context-menu"
      :style="{ left: contextMenu.x + 'px', top: contextMenu.y + 'px' }"
      @contextmenu.prevent
    >
      <template v-if="contextMenu.targetType === 'node'">
        <div class="context-menu-item" @click="handleContextAction('copy')">
          <SvgIcon name="copy" /> 复制
        </div>
        <div class="context-menu-item" @click="handleContextAction('cut')">
          <SvgIcon name="cut" /> 剪切
        </div>
        <div class="context-menu-item danger" @click="handleContextAction('delete')">
          <SvgIcon name="delete" /> 删除
        </div>
        <div class="context-menu-divider" />
      </template>
      <template v-if="contextMenu.targetType === 'edge'">
        <div class="context-menu-item danger" @click="handleContextAction('delete')">
          <SvgIcon name="delete" /> 删除连线
        </div>
        <div class="context-menu-divider" />
      </template>
      <div class="context-menu-item" @click="handleContextAction('paste')">
        <SvgIcon name="paste" /> 粘贴
      </div>
      <div class="context-menu-item" @click="handleContextAction('selectAll')">
        <SvgIcon name="select" /> 全选
      </div>
    </div>

    <!-- 点击其他区域隐藏右键菜单 -->
    <div v-if="contextMenu.show" class="context-menu-overlay" @click="hideContextMenu" @contextmenu.prevent="hideContextMenu" />

    <!-- 变量绑定菜单 -->
    <div
      v-if="varMenu.show"
      class="var-menu"
      :style="{ left: varMenu.x + 'px', top: varMenu.y + 'px' }"
      @click.stop
    >
      <div class="var-menu-title">插入变量</div>
      <div class="var-menu-item" @click="insertVariable('counter')">📌 counter</div>
      <div class="var-menu-item" @click="insertVariable('timestamp')">📌 timestamp</div>
      <div class="var-menu-item" @click="insertVariable('confidence')">📌 confidence</div>
      <div class="var-menu-item" @click="insertVariable('image_path')">📌 image_path</div>
      <div class="var-menu-item" @click="insertVariable('result_count')">📌 result_count</div>
    </div>
    <div v-if="varMenu.show" class="var-menu-overlay" @click="hideVariableMenu" />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onBeforeUnmount, markRaw, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { VueFlow, useVueFlow, Position, MarkerType } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import { MiniMap } from '@vue-flow/minimap'
import { ruleEngineApi } from '@/api'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import '@vue-flow/controls/dist/style.css'
import '@vue-flow/minimap/dist/style.css'

// 图标 - 6色分类体系 (按设计文档)
const InputIcon = () => h('path', { d: 'M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' })  // input (#4CFF4C)
const DetectionIcon = () => h('circle', { cx: '12', cy: '12', r: '10', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' })  // detection (#00f0FF)
const ProcessingIcon = () => h('polygon', { points: '13 2 3 14 12 14 11 22 21 10 12 10 13 2', fill: 'currentColor' })  // processing (#FFFF4C)
const ActionIcon = () => h('polygon', { points: '5 3 19 12 5 21 5 3', fill: 'currentColor' })  // action (#FF7F4C)
const LogicIcon = () => h('rect', { x: '3', y: '3', width: '7', height: '7', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' })  // logic (#DC4FDC)
const OutputIcon = () => h('path', { d: 'M22 11.08V12a10 10 0 1 1-5.93-9.14M22 4L12 14.01l-3-3', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' })  // output (#FF4C4C)

import { h } from 'vue'

const router = useRouter()
const route = useRoute()
const { fitView, addNodes, removeNodes, addEdges, setCenter, screenToFlowCoordinate, getZoom, getPan } = useVueFlow()

// 常量
const gridSize = 20
const gridColor = '#1a1a2e'
const rulerStep = 100
const showRulers = ref(true)

// 状态
const graphId = computed(() => Number(route.params.id))
const graph = ref<any>(null)
const graphName = ref('')
const nodes = ref<any[]>([])
const edges = ref<any[]>([])
const nodeDefinitions = ref<any[]>([])
const selectedNode = ref<any>(null)
const nodeConfig = ref<any>({})
const isLoading = ref(false)
const saving = ref(false)
const executing = ref(false)
const showPalette = ref(true)
const showMiniMap = ref(true)
const snapGrid = ref(true)
const showGrid = ref(true)
const showExecutionPanel = ref(false)
const executionLogs = ref<any[]>([])
const executionStatus = ref<'idle' | 'running' | 'success' | 'failed'>('idle')
const executionProgress = ref(0)
const executionId = ref<number | null>(null)
const flowContainer = ref<HTMLElement | null>(null)
const vueFlowRef = ref<any>(null)
const canvasWrapper = ref<HTMLElement | null>(null)
const canvasWidth = ref(5000)
const canvasHeight = ref(5000)
const panX = ref(0)
const panY = ref(0)
const zoomLevel = ref(1)
const isPanning = ref(false)
const lastMousePos = ref({ x: 0, y: 0 })

// 节点执行状态: nodeId -> 'pending' | 'running' | 'success' | 'failed'
const nodeStates = ref<Record<string, string>>({})

// 复制粘贴
const clipboard = ref<any[]>([])
const clipboardMode = ref<'copy' | 'cut'>('copy')

// 右键菜单
const contextMenu = reactive({
  show: false,
  x: 0,
  y: 0,
  target: null as any,
  targetType: null as 'node' | 'edge' | 'pane'
})

// 变量绑定菜单
const varMenu = reactive({
  show: false,
  x: 0,
  y: 0,
  fieldKey: '' as string
})

// 撤销/重做
const historyStack = ref<{ nodes: any[], edges: any[] }[]>([])
const historyIndex = ref(-1)
const canUndo = computed(() => historyIndex.value > 0)
const canRedo = computed(() => historyIndex.value < historyStack.value.length - 1)

// 节点分类 - 6色体系 (按设计文档)
const nodeCategories = computed(() => [
  { name: 'input', label: '输入', icon: markRaw(InputIcon), expanded: true, nodes: [] as any[] },
  { name: 'detection', label: '检测', icon: markRaw(DetectionIcon), expanded: true, nodes: [] as any[] },
  { name: 'processing', label: '处理', icon: markRaw(ProcessingIcon), expanded: true, nodes: [] as any[] },
  { name: 'action', label: '动作', icon: markRaw(ActionIcon), expanded: true, nodes: [] as any[] },
  { name: 'logic', label: '逻辑', icon: markRaw(LogicIcon), expanded: true, nodes: [] as any[] },
  { name: 'output', label: '输出', icon: markRaw(OutputIcon), expanded: true, nodes: [] as any[] },
].map(cat => ({
  ...cat,
  nodes: nodeDefinitions.value.filter((d: any) => d.category === cat.name)
})))

// 快速添加
const quickAddNodes = computed(() => nodeDefinitions.value.slice(0, 4))

// 是否有节点
const hasNodes = computed(() => nodes.value.length > 0)

// 执行状态文本
const executionStatusText = computed(() => ({
  idle: '等待执行',
  running: '执行中...',
  success: '执行成功',
  failed: '执行失败'
}[executionStatus.value]))

// 默认边样式
const defaultEdgeOptions = {
  type: 'smoothstep',
  animated: true,
  markerEnd: MarkerType.ArrowClosed,
  style: { stroke: '#00f0ff', strokeWidth: 2 }
}

// 连接线样式
const connectionLineStyle = {
  stroke: '#00f0ff',
  strokeWidth: 2
}

// 节点类型
const nodeTypes = {}

// 小地图颜色 - 6色分类体系
function miniMapNodeColor(node: any) {
  const colors: Record<string, string> = {
    input: '#4CFF4C',      // input (#4CFF4C)
    detection: '#00f0FF',  // detection (#00f0FF)
    processing: '#FFFF4C', // processing (#FFFF4C)
    action: '#FF7F4C',     // action (#FF7F4C)
    logic: '#DC4FDC',      // logic (#DC4FDC)
    output: '#FF4C4C'       // output (#FF4C4C)
  }
  return colors[node.category] || '#888'
}

// 获取分类图标
function getCategoryIcon(category: string) {
  const icons: Record<string, any> = {
    input: markRaw(InputIcon),
    detection: markRaw(DetectionIcon),
    processing: markRaw(ProcessingIcon),
    action: markRaw(ActionIcon),
    logic: markRaw(LogicIcon),
    output: markRaw(OutputIcon)
  }
  return icons[category] || icons.action
}

// Toast
const toast = reactive({ show: false, message: '', type: 'info' as 'success' | 'error' | 'info' })

function showToast(message: string, type: 'success' | 'error' | 'info' = 'info') {
  toast.message = message
  toast.type = type
  toast.visible = true
  setTimeout(() => { toast.visible = false }, 3000)
}

// WebSocket 连接（Phase 5 实时推送）
let ws: WebSocket | null = null
let wsReconnectTimer: ReturnType<typeof setTimeout> | null = null

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
      // 订阅该 execution_id
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
      // 自动重连
      if (wsReconnectTimer) clearTimeout(wsReconnectTimer)
      wsReconnectTimer = setTimeout(() => {
        if (executionStatus.value === 'running' && executionId.value) {
          connectWebSocket(executionId.value)
        }
      }, 3000)
    }

    ws.onclose = () => {
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
      nodeStates.value[msg.node_id] = 'running'
      break
    case 'node_executed':
      nodeStates.value[msg.node_id] = 'success'
      break
    case 'node_failed':
      nodeStates.value[msg.node_id] = 'failed'
      showToast(`节点执行失败: ${msg.error}`, 'error')
      break
    case 'execution_progress':
      executionProgress.value = msg.progress
      break
    case 'execution_complete':
      executionStatus.value = msg.status === 'completed' ? 'success' : 'failed'
      executionProgress.value = 100
      showToast(
        msg.status === 'completed' ? '执行成功' : `执行失败: ${msg.error || ''}`,
        msg.status === 'completed' ? 'success' : 'error'
      )
      // 重置节点状态
      setTimeout(() => { nodeStates.value = {} }, 2000)
      disconnectWebSocket()
      break
  }
}

// 右键菜单操作
function saveHistory() {
  historyStack.value = historyStack.value.slice(0, historyIndex.value + 1)
  historyStack.value.push({
    nodes: JSON.parse(JSON.stringify(nodes.value.map((n: any) => ({ ...n, selected: false, dragging: false })))),
    edges: JSON.parse(JSON.stringify(edges.value))
  })
  historyIndex.value = historyStack.value.length - 1
  if (historyStack.value.length > 50) {
    historyStack.value.shift()
    historyIndex.value--
  }
}

// 键盘事件处理
function handleKeyDown(event: KeyboardEvent) {
  // 忽略输入框内的按键
  const target = event.target as HTMLElement
  if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable) {
    return
  }

  const isCtrl = event.ctrlKey || event.metaKey

  // Ctrl+C: 复制
  if (isCtrl && event.key === 'c') {
    event.preventDefault()
    handleCopy()
    return
  }

  // Ctrl+X: 剪切
  if (isCtrl && event.key === 'x') {
    event.preventDefault()
    handleCut()
    return
  }

  // Ctrl+V: 粘贴
  if (isCtrl && event.key === 'v') {
    event.preventDefault()
    handlePaste()
    return
  }

  // Ctrl+Z: 撤销
  if (isCtrl && event.key === 'z' && !event.shiftKey) {
    event.preventDefault()
    handleUndo()
    return
  }

  // Ctrl+Y / Ctrl+Shift+Z: 重做
  if (isCtrl && (event.key === 'y' || (event.key === 'z' && event.shiftKey))) {
    event.preventDefault()
    handleRedo()
    return
  }

  // Delete / Backspace: 删除选中
  if (event.key === 'Delete' || event.key === 'Backspace') {
    event.preventDefault()
    handleDelete()
    return
  }
}

// 复制
function handleCopy() {
  const selected = nodes.value.filter((n: any) => n.selected)
  if (selected.length === 0) {
    showToast('请先选择要复制的节点', 'info')
    return
  }
  clipboard.value = selected.map((n: any) => JSON.parse(JSON.stringify(n)))
  clipboardMode.value = 'copy'
  showToast(`已复制 ${selected.length} 个节点`, 'info')
}

// 剪切
function handleCut() {
  const selected = nodes.value.filter((n: any) => n.selected)
  if (selected.length === 0) {
    showToast('请先选择要剪切的节点', 'info')
    return
  }
  clipboard.value = selected.map((n: any) => JSON.parse(JSON.stringify(n)))
  clipboardMode.value = 'cut'
  // 立即删除
  removeNodes(selected.map((n: any) => n.id))
  edges.value = edges.value.filter((e: any) =>
    !selected.some((n: any) => n.id === e.source || n.id === e.target)
  )
  selected.forEach((n: any) => {
    const idx = nodes.value.findIndex((node: any) => node.id === n.id)
    if (idx !== -1) nodes.value.splice(idx, 1)
  })
  showToast(`已剪切 ${selected.length} 个节点`, 'info')
}

// 粘贴
function handlePaste() {
  if (clipboard.value.length === 0) {
    showToast('剪贴板为空', 'info')
    return
  }

  const container = flowContainer.value
  if (!container) return

  const rect = container.getBoundingClientRect()
  const offsetX = 50
  const offsetY = 50

  const newNodes = clipboard.value.map((n: any) => ({
    ...JSON.parse(JSON.stringify(n)),
    id: `node_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`,
    position: {
      x: n.position.x + offsetX,
      y: n.position.y + offsetY
    },
    selected: false
  }))

  // 如果是剪切模式，清除原选中节点
  if (clipboardMode.value === 'cut') {
    clipboard.value = []
  }

  addNodes(newNodes)
  saveHistory()
  showToast(`已粘贴 ${newNodes.length} 个节点`, 'info')
}

// 删除选中
function handleDelete() {
  const selectedNodes = nodes.value.filter((n: any) => n.selected)
  const selectedEdges = edges.value.filter((e: any) => e.selected)

  if (selectedNodes.length === 0 && selectedEdges.length === 0) {
    return
  }

  // 删除节点时同步删除关联的边
  const nodeIds = selectedNodes.map((n: any) => n.id)
  edges.value = edges.value.filter((e: any) =>
    !nodeIds.includes(e.source) && !nodeIds.includes(e.target) && !e.selected
  )

  // 删除节点
  selectedNodes.forEach((n: any) => {
    const idx = nodes.value.findIndex((node: any) => node.id === n.id)
    if (idx !== -1) nodes.value.splice(idx, 1)
  })

  selectedEdges.forEach((e: any) => {
    const idx = edges.value.findIndex((edge: any) => edge.id === e.id)
    if (idx !== -1) edges.value.splice(idx, 1)
  })

  selectedNode.value = null
  saveHistory()
  showToast(`已删除 ${selectedNodes.length} 个节点`, 'info')
}

// 右键菜单
function handleContextMenu(event: MouseEvent, target: any, type: 'node' | 'edge' | 'pane') {
  event.preventDefault()
  event.stopPropagation()
  contextMenu.show = true
  contextMenu.x = event.clientX
  contextMenu.y = event.clientY
  contextMenu.target = target
  contextMenu.targetType = type
}

// 隐藏右键菜单
function hideContextMenu() {
  contextMenu.show = false
}

// 获取输入端口的连接信息
function getInputConnection(inputName: string) {
  const edge = edges.value.find(
    (e: any) => e.target === selectedNode.value?.id && e.targetHandle === inputName
  )
  if (!edge) return null
  const sourceNode = nodes.value.find((n: any) => n.id === edge.source)
  return {
    edge,
    sourceNode
  }
}

// 断开连接
function disconnectInput(inputName: string) {
  const edge = edges.value.find(
    (e: any) => e.target === selectedNode.value?.id && e.targetHandle === inputName
  )
  if (!edge) return
  const idx = edges.value.findIndex((e: any) => e.id === edge.id)
  if (idx !== -1) edges.value.splice(idx, 1)
  saveHistory()
  showToast('已断开连接', 'info')
}

// 显示变量绑定菜单
function showVariableMenu(key: string, event: MouseEvent) {
  event.preventDefault()
  event.stopPropagation()
  varMenu.show = true
  varMenu.x = event.clientX
  varMenu.y = event.clientY
  varMenu.fieldKey = key
}

// 隐藏变量菜单
function hideVariableMenu() {
  varMenu.show = false
}

// 插入变量到字段
function insertVariable(varName: string) {
  if (!varMenu.fieldKey) return
  const currentValue = nodeConfig.value[varMenu.fieldKey] || ''
  // 如果当前值已包含 {{}}，则追加；否则添加 {{varName}}
  if (currentValue.includes('{{') && currentValue.includes('}}')) {
    nodeConfig.value[varMenu.fieldKey] = currentValue + `{{${varName}}}`
  } else {
    nodeConfig.value[varMenu.fieldKey] = `{{${varName}}}`
  }
  updateConfig(varMenu.fieldKey, nodeConfig.value[varMenu.fieldKey])
  hideVariableMenu()
}

// 右键菜单操作
function handleContextAction(action: string) {
  hideContextMenu()
  switch (action) {
    case 'copy':
      if (contextMenu.targetType === 'node') {
        nodes.value.forEach((n: any) => { n.selected = n.id === contextMenu.target?.id })
        handleCopy()
      }
      break
    case 'paste':
      handlePaste()
      break
    case 'delete':
      if (contextMenu.targetType === 'node') {
        nodes.value.forEach((n: any) => { n.selected = n.id === contextMenu.target?.id })
      } else if (contextMenu.targetType === 'edge') {
        edges.value.forEach((e: any) => { e.selected = e.id === contextMenu.target?.id })
      }
      handleDelete()
      break
    case 'selectAll':
      nodes.value.forEach((n: any) => { n.selected = true })
      edges.value.forEach((e: any) => { e.selected = true })
      break
  }
}

// 撤销
function handleUndo() {
  if (canUndo.value) {
    historyIndex.value--
    const state = historyStack.value[historyIndex.value]
    nodes.value = JSON.parse(JSON.stringify(state.nodes))
    edges.value = JSON.parse(JSON.stringify(state.edges))
  }
}

// 重做
function handleRedo() {
  if (canRedo.value) {
    historyIndex.value++
    const state = historyStack.value[historyIndex.value]
    nodes.value = JSON.parse(JSON.stringify(state.nodes))
    edges.value = JSON.parse(JSON.stringify(state.edges))
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
  await loadGraph()
  await loadNodeDefinitions()
  saveHistory()
  // 键盘事件
  window.addEventListener('keydown', handleKeyDown)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleKeyDown)
})

// 加载规则图
async function loadGraph() {
  isLoading.value = true
  try {
    const res = await ruleEngineApi.getGraphDetail(graphId.value)
    graph.value = res.data
    graphName.value = graph.value.name

    nodes.value = (graph.value.nodes || []).map((n: any) => ({
      id: n.id,
      type: n.type,
      position: n.position || { x: 0, y: 0 },
      data: { ...n.data },
      category: getNodeCategory(n.type)
    }))

    edges.value = (graph.value.edges || []).map((e: any) => ({
      id: e.id,
      source: e.source,
      target: e.target,
      sourceHandle: e.source_handle,
      targetHandle: e.target_handle,
      type: 'smoothstep',
      animated: true,
      markerEnd: MarkerType.ArrowClosed
    }))
  } catch (err) {
    console.error('加载规则图失败:', err)
    showToast('加载规则图失败', 'error')
  } finally {
    isLoading.value = false
  }
}

// 加载节点定义
async function loadNodeDefinitions() {
  try {
    const res = await ruleEngineApi.getNodeDefinitions()
    nodeDefinitions.value = res.data
  } catch (err) {
    console.error('加载节点定义失败:', err)
  }
}

// 获取节点分类
function getNodeCategory(type: string): string {
  const def = nodeDefinitions.value.find((d: any) => d.type === type)
  return def?.category || 'action'
}

// 返回
function goBack() {
  router.push('/rule-engine')
}

// 名称修改
async function handleNameChange() {
  if (graphName.value !== graph.value?.name) {
    try {
      await ruleEngineApi.updateGraph(graphId.value, { name: graphName.value })
      graph.value.name = graphName.value
      showToast('名称已更新', 'success')
    } catch (err) {
      showToast('更新名称失败', 'error')
    }
  }
}

// 拖拽
function handleDragStart(event: DragEvent, nodeDef: any) {
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

  // 吸附到网格
  if (snapGrid.value) {
    position.x = Math.round(position.x / gridSize) * gridSize
    position.y = Math.round(position.y / gridSize) * gridSize
  }

  const newNode = {
    id: `node_${Date.now()}`,
    type: nodeDef.type,
    position,
    data: {},
    category: nodeDef.category,
    label: nodeDef.label,
    description: nodeDef.description,
    configSchema: nodeDef.config_schema,
    inputs: nodeDef.inputs,
    outputs: nodeDef.outputs
  }

  addNodes([newNode])
  saveHistory()
}

// 快速添加
function quickAddNode(nodeDef: any) {
  const centerX = (flowContainer.value?.clientWidth || 800) / 2 / zoomLevel.value
  const centerY = (flowContainer.value?.clientHeight || 600) / 2 / zoomLevel.value

  const newNode = {
    id: `node_${Date.now()}`,
    type: nodeDef.type,
    position: {
      x: centerX + Math.random() * 100 - 50,
      y: centerY + Math.random() * 100 - 50
    },
    data: {},
    category: nodeDef.category,
    label: nodeDef.label,
    description: nodeDef.description,
    configSchema: nodeDef.config_schema,
    inputs: nodeDef.inputs,
    outputs: nodeDef.outputs
  }

  addNodes([newNode])
  saveHistory()
  showToast(`已添加 ${nodeDef.label}`, 'info')
}

// 节点点击
function handleNodeClick(event: any) {
  const nodeId = event.node.id
  const node = nodes.value.find(n => n.id === nodeId)
  if (node) {
    selectedNode.value = node
    nodeConfig.value = { ...node.data }
  }
}

// 节点拖拽
function handleNodeDragStop() {
  saveHistory()
}

// 画布点击
function handlePaneClick() {
  selectedNode.value = null
}

// 端口类型兼容性检查
const PORT_TYPES = ['IMAGE', 'BBOX', 'MASK', 'SCORES', 'TRIGGER', 'CONTROL', 'MODEL', 'ANY']

function isPortCompatible(sourceType: string, targetType: string): boolean {
  // ANY 可以连接任何类型
  if (sourceType === 'ANY' || targetType === 'ANY') return true
  // 相同类型可以连接
  if (sourceType === targetType) return true
  // TRIGGER 可以连接到 TRIGGER 或 CONTROL
  if (sourceType === 'TRIGGER' && (targetType === 'TRIGGER' || targetType === 'CONTROL')) return true
  // CONTROL 只能连接到 CONTROL
  if (sourceType === 'CONTROL' && targetType === 'CONTROL') return true
  return false
}

function getNodePortType(nodeId: string, handleId: string | null, isSource: boolean): string | null {
  const node = nodes.value.find(n => n.id === nodeId)
  if (!node) return null
  const ports = isSource ? node.outputs : node.inputs
  if (!ports) return null
  // handleId 可以是端口名或端口ID
  if (handleId && ports[handleId]) {
    return ports[handleId].type || 'ANY'
  }
  // 如果没有指定handle，返回第一个端口的类型
  const firstKey = Object.keys(ports)[0]
  return firstKey ? (ports[firstKey]?.type || 'ANY') : 'ANY'
}

function validateConnection(params: any): { valid: boolean; error?: string } {
  const { source, target, sourceHandle, targetHandle } = params
  
  // 获取源节点和目标节点
  const sourceNode = nodes.value.find(n => n.id === source)
  const targetNode = nodes.value.find(n => n.id === target)
  
  if (!sourceNode || !targetNode) {
    return { valid: false, error: '节点不存在' }
  }
  
  // 禁止自己连接自己
  if (source === target) {
    return { valid: false, error: '不能连接到自己' }
  }
  
  // 获取端口类型
  const sourceType = getNodePortType(source, sourceHandle, true)
  const targetType = getNodePortType(target, targetHandle, false)
  
  if (sourceType === null || targetType === null) {
    return { valid: false, error: '端口定义缺失' }
  }
  
  // 类型兼容性检查
  if (!isPortCompatible(sourceType, targetType)) {
    return { valid: false, error: `类型不兼容: ${sourceType} → ${targetType}` }
  }
  
  return { valid: true }
}

// 连接
function handleConnect(params: any) {
  // 验证连接类型兼容性
  const validation = validateConnection(params)
  if (!validation.valid) {
    showToast(validation.error || '连接失败', 'error')
    return
  }
  
  addEdges([{
    ...params,
    type: 'smoothstep',
    animated: true,
    markerEnd: MarkerType.ArrowClosed,
    id: `e-${params.source}-${params.target}-${Date.now()}`
  }])
  saveHistory()
}

// 节点/边变化
function handleNodesChange(changes: any[]) {
  // 只在外部变化时保存历史
}

function handleEdgesChange(changes: any[]) {
  // 只在外部变化时保存历史
}

// 画布平移
function handlePan(pan: { x: number, y: number }) {
  panX.value = -pan.x
  panY.value = -pan.y
}

// 缩放
function handleZoom(zoom: number) {
  zoomLevel.value = zoom
}

// 鼠标滚轮缩放
function handleWheel(event: WheelEvent) {
  if (event.ctrlKey) {
    event.preventDefault()
  }
}

// 画布拖拽平移
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
    panX.value += dx
    panY.value += dy
    lastMousePos.value = { x: event.clientX, y: event.clientY }
  }
}

function handleCanvasMouseUp() {
  isPanning.value = false
}

// 更新配置
function updateConfig(key: string, value: any) {
  nodeConfig.value[key] = value
  const node = nodes.value.find(n => n.id === selectedNode.value?.id)
  if (node) {
    node.data = { ...nodeConfig.value }
  }
}

// 数组操作
function addArrayItem(key: string) {
  if (!nodeConfig.value[key]) nodeConfig.value[key] = []
  nodeConfig.value[key] = [...nodeConfig.value[key], '']
  updateNodeData()
}

function removeArrayItem(key: string, index: number) {
  nodeConfig.value[key] = nodeConfig.value[key].filter((_: any, i: number) => i !== index)
  updateNodeData()
}

function updateArrayItem(key: string, index: number, value: string) {
  nodeConfig.value[key][index] = value
  updateNodeData()
}

function updateNodeData() {
  const node = nodes.value.find(n => n.id === selectedNode.value?.id)
  if (node) node.data = { ...nodeConfig.value }
}

// 保存
async function handleSave() {
  saving.value = true
  try {
    await ruleEngineApi.updateGraph(graphId.value, {
      nodes_json: JSON.stringify(nodes.value.map(n => ({
        id: n.id,
        type: n.type,
        position: n.position,
        data: n.data
      }))),
      edges_json: JSON.stringify(edges.value.map(e => ({
        id: e.id,
        source: e.source,
        target: e.target,
        source_handle: e.sourceHandle,
        target_handle: e.targetHandle
      })))
    })
    // 生成并保存缩略图
    await captureAndSaveThumbnail()
    showToast('保存成功', 'success')
    saveHistory()
  } catch (err) {
    console.error('保存失败:', err)
    showToast('保存失败', 'error')
  } finally {
    saving.value = false
  }
}

// 生成并保存缩略图
async function captureAndSaveThumbnail() {
  try {
    const vueFlow = vueFlowRef.value
    if (!vueFlow) return

    // 调用 VueFlow 的 toObject 获取当前视图内容
    const flowExport = vueFlow.toObject?.()
    if (!flowExport || !flowExport.nodes?.length) return

    // 创建一个离屏 canvas 来渲染缩略图
    const canvas = document.createElement('canvas')
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    // 缩略图尺寸 320x180 (16:9)
    canvas.width = 320
    canvas.height = 180

    // 填充深色背景
    ctx.fillStyle = '#1a1a2e'
    ctx.fillRect(0, 0, canvas.width, canvas.height)

    // 获取所有节点的位置范围
    const xs = flowExport.nodes.map((n: any) => n.position?.x || 0)
    const ys = flowExport.nodes.map((n: any) => n.position?.y || 0)
    if (!xs.length) return

    const minX = Math.min(...xs)
    const minY = Math.min(...ys)
    const maxX = Math.max(...xs) + 120
    const maxY = Math.max(...ys) + 60
    const graphW = maxX - minX || 1
    const graphH = maxY - minY || 1

    // 计算缩放比例，完整容纳所有节点
    const padding = 20
    const availW = canvas.width - padding * 2
    const availH = canvas.height - padding * 2
    const scale = Math.min(availW / graphW, availH / graphH, 1)

    // 居中偏移
    const offsetX = (canvas.width - graphW * scale) / 2 - minX * scale
    const offsetY = (canvas.height - graphH * scale) / 2 - minY * scale

    ctx.save()
    ctx.translate(offsetX, offsetY)
    ctx.scale(scale, scale)

    // 绘制连线
    ctx.strokeStyle = '#00f0ff'
    ctx.lineWidth = 2 / scale
    for (const edge of flowExport.edges || []) {
      const sourceNode = flowExport.nodes.find((n: any) => n.id === edge.source)
      const targetNode = flowExport.nodes.find((n: any) => n.id === edge.target)
      if (sourceNode && targetNode) {
        const sx = (sourceNode.position?.x || 0) + 60
        const sy = (sourceNode.position?.y || 0) + 20
        const tx = (targetNode.position?.x || 0) + 60
        const ty = (targetNode.position?.y || 0) + 20
        ctx.beginPath()
        ctx.moveTo(sx, sy)
        ctx.lineTo(tx, ty)
        ctx.stroke()
      }
    }

    // 绘制节点
    for (const node of flowExport.nodes || []) {
      const x = node.position?.x || 0
      const y = node.position?.y || 0
      const w = 120
      const h = 40

      // 根据节点类型设置颜色
      let bgColor = '#2d2d4a'
      let borderColor = '#00f0ff'
      if (node.type?.includes('trigger')) {
        bgColor = '#1a3a4a'
        borderColor = '#00f0ff'
      } else if (node.type?.includes('condition') || node.type?.includes('logic')) {
        bgColor = '#3a2d4a'
        borderColor = '#aa66ff'
      } else if (node.type?.includes('action') || node.type?.includes('yolo')) {
        bgColor = '#2d4a3a'
        borderColor = '#00ff88'
      }

      ctx.fillStyle = bgColor
      ctx.strokeStyle = borderColor
      ctx.lineWidth = 2 / scale
      ctx.beginPath()
      ctx.roundRect(x, y, w, h, 6 / scale)
      ctx.fill()
      ctx.stroke()

      // 节点名称
      ctx.fillStyle = '#fff'
      ctx.font = `${12 / scale}px sans-serif`
      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'
      const label = node.data?.label || node.id || ''
      ctx.fillText(label.substring(0, 12), x + w / 2, y + h / 2)
    }

    ctx.restore()

    // 转换为 Base64
    const dataUrl = canvas.toDataURL('image/png', 0.7)
    // 上传到后端
    await ruleEngineApi.updateThumbnail(graphId.value, dataUrl)
  } catch (err) {
    console.error('生成缩略图失败:', err)
  }
}

// 校验
async function handleValidate() {
  try {
    const res = await ruleEngineApi.validateGraph(graphId.value)
    if (res.data.valid) {
      showToast('规则图校验通过', 'success')
    } else {
      showToast(`校验失败: ${res.data.errors?.join(', ') || '未知错误'}`, 'error')
    }
  } catch (err) {
    showToast('校验请求失败', 'error')
  }
}

// 执行
async function handleExecute() {
  await handleSave()

  executing.value = true
  executionStatus.value = 'running'
  executionProgress.value = 0
  showExecutionPanel.value = true
  executionLogs.value = []
  nodeStates.value = {}

  try {
    const res = await ruleEngineApi.execute({
      graph_id: graphId.value,
      trigger_type: 'manual'
    })

    // Phase 5: WebSocket 实时推送
    const execId = res.data.execution_id
    executionId.value = execId
    connectWebSocket(execId)

    // 前端轮询作为降级（备用）
    pollExecutionStatus(execId)

  } catch (err: any) {
    executionStatus.value = 'failed'
    executionLogs.value.push({
      level: 'error',
      timestamp: new Date().toLocaleTimeString(),
      message: err?.response?.data?.detail || '执行失败'
    })
    showToast('执行失败', 'error')
    executing.value = false
  }
}

let pollTimer: ReturnType<typeof setInterval> | null = null

async function pollExecutionStatus(execId: number) {
  // WebSocket 足够可靠，仅在连接失败时启用轮询备用
}

// 清空日志
function clearLogs() {
  executionLogs.value = []
}
</script>

<style scoped lang="scss">
// 变量
$header-height: 56px;
$palette-width: 280px;
$panel-width: 320px;
$panel-header-height: 52px;

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
  background: linear-gradient(180deg, #12121a 0%, #0e0e14 100%);
  border-bottom: 1px solid #1e1e2e;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  flex-shrink: 0;
  z-index: 100;

  .header-left,
  .header-center,
  .header-right {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .header-left { flex: 1; }
  .header-center { flex: 0 0 auto; }
  .header-right { flex: 1; justify-content: flex-end; }
}

.rule-name-section {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-left: 12px;
}

.rule-name-input {
  background: transparent;
  border: 1px solid transparent;
  padding: 8px 14px;
  border-radius: 6px;
  color: #fff;
  font-size: 15px;
  font-weight: 600;
  min-width: 200px;
  transition: all 0.2s;

  &:hover {
    border-color: #2a2a3a;
    background: rgba(255,255,255,0.03);
  }

  &:focus {
    outline: none;
    border-color: #00f0ff;
    background: rgba(0, 240, 255, 0.05);
  }
}

.rule-status-badge {
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  background: #1e1e2e;
  color: #666;
  text-transform: uppercase;
  letter-spacing: 0.5px;

  &.active {
    background: rgba(0, 255, 136, 0.15);
    color: #00ff88;
  }
}

.tool-group {
  display: flex;
  align-items: center;
  gap: 4px;
  background: #1a1a24;
  padding: 4px;
  border-radius: 8px;
}

.tool-divider {
  width: 1px;
  height: 24px;
  background: #2a2a3a;
  margin: 0 4px;
}

.zoom-level {
  font-size: 12px;
  color: #888;
  min-width: 48px;
  text-align: center;
  font-family: 'JetBrains Mono', monospace;
}

// 按钮样式
.icon-btn {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  border-radius: 6px;
  color: #888;
  cursor: pointer;
  transition: all 0.2s;

  svg {
    width: 18px;
    height: 18px;
  }

  &:hover:not(:disabled) {
    background: #2a2a3a;
    color: #fff;
  }

  &:disabled {
    opacity: 0.3;
    cursor: not-allowed;
  }

  &.active {
    background: rgba(0, 240, 255, 0.15);
    color: #00f0ff;
  }

  &.small {
    width: 28px;
    height: 28px;

    svg { width: 14px; height: 14px; }
  }
}

.back-btn:hover {
  background: rgba(0, 240, 255, 0.1);
  color: #00f0ff;
}

.action-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border: none;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;

  svg {
    width: 16px;
    height: 16px;
  }

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  &.secondary {
    background: #1e1e2e;
    color: #ccc;

    &:hover:not(:disabled) {
      background: #2a2a3a;
      color: #fff;
    }
  }

  &.primary {
    background: linear-gradient(135deg, #00f0ff, #00aa88);
    color: #000;

    &:hover:not(:disabled) {
      box-shadow: 0 4px 20px rgba(0, 240, 255, 0.3);
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

  &.collapsed {
    width: 48px;

    .palette-content { display: none; }
  }
}

.palette-header {
  height: $panel-header-height;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 12px;
  border-bottom: 1px solid #1e1e2e;

  h3 {
    font-size: 13px;
    font-weight: 600;
    color: #888;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }
}

.collapse-btn {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  border-radius: 4px;
  color: #666;
  cursor: pointer;
  transition: all 0.2s;

  svg {
    width: 16px;
    height: 16px;
    transition: transform 0.2s;

    &.rotated { transform: rotate(180deg); }
  }

  &:hover {
    background: #1e1e2e;
    color: #fff;
  }
}

.palette-content {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
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
  background: #08080c;
}

.flow-container {
  width: 100%;
  height: 100%;
  position: relative;

  :deep(.vue-flow) {
    width: 100%;
    height: 100%;
    background: transparent;
  }

  :deep(.vue-flow__background) {
    background: #08080c;
  }

  :deep(.vue-flow__edge-path) {
    stroke: #00f0ff;
    stroke-width: 2;
  }

  :deep(.vue-flow__edge.animated .vue-flow__edge-path) {
    stroke-dasharray: 5;
    animation: dash 0.5s linear infinite;
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
      stroke: #00f0ff;
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
      border-color: #00f0ff;
      color: #fff;
    }
  }
}

.loading-state {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: rgba(8, 8, 12, 0.9);
  z-index: 10;

  .spinner {
    width: 40px;
    height: 40px;
    border: 3px solid #1e1e2e;
    border-top-color: #00f0ff;
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin-bottom: 16px;
  }

  span {
    color: #666;
    font-size: 13px;
  }
}

@keyframes spin {
  to { transform: rotate(360deg); }
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
      border-color: #00f0ff;
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
        border-color: #ff4466;
        color: #ff4466;
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
      border-color: #00f0ff;
      color: #00f0ff;
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
      color: #00f0ff;
      border: 1px solid rgba(0, 240, 255, 0.2);
    }

    &.output {
      background: rgba(0, 255, 136, 0.1);
      color: #00ff88;
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
    color: #00ff88;
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
  left: $palette-width;
  right: 0;
  background: #0e0e14;
  border-top: 1px solid #1e1e2e;
  z-index: 50;
  transition: transform 0.3s ease;

  &:not(.expanded) {
    .execution-content { display: none; }
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
    &.running { background: rgba(0, 240, 255, 0.15); color: #00f0ff; }
    &.success { background: rgba(0, 255, 136, 0.15); color: #00ff88; }
    &.failed { background: rgba(255, 0, 170, 0.15); color: #ff00aa; }
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
  background: linear-gradient(90deg, #00f0ff, #00ff88);
  border-radius: 2px;
  transition: width 0.3s ease;
}

.progress-text {
  font-size: 11px;
  color: #00f0ff;
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
    color: #00f0ff;
  }

  &.warning .log-level-badge {
    background: rgba(255, 221, 0, 0.15);
    color: #ffdd00;
  }

  &.error .log-level-badge {
    background: rgba(255, 0, 170, 0.15);
    color: #ff00aa;
  }

  .log-node {
    color: #555;
    flex-shrink: 0;
  }

  .log-message {
    color: #888;
    flex: 1;
  }
}

.no-logs {
  text-align: center;
  padding: 20px;
  color: #444;
  font-size: 13px;
}

// Toast
.toast-notification {
  position: fixed;
  bottom: 80px;
  left: 50%;
  transform: translateX(-50%);
  padding: 12px 24px;
  border-radius: 8px;
  font-size: 14px;
  z-index: 2000;
  animation: toastIn 0.3s ease;

  &.success {
    background: linear-gradient(135deg, #00ff88, #00aa66);
    color: #000;
  }

  &.error {
    background: linear-gradient(135deg, #ff4466, #cc0033);
    color: #fff;
  }

  &.info {
    background: #1e1e2e;
    border: 1px solid #2a2a3a;
    color: #ccc;
  }
}

@keyframes toastIn {
  from {
    opacity: 0;
    transform: translateX(-50%) translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateX(-50%) translateY(0);
  }
}

.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s ease;
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(20px);
}

/* 右键菜单 */
.context-menu {
  position: fixed;
  z-index: 9999;
  background: var(--bg-card, #1a1a2e);
  border: 1px solid var(--border-color, #2a2a4a);
  border-radius: 8px;
  padding: 4px 0;
  min-width: 140px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
}

.context-menu-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  cursor: pointer;
  font-size: 13px;
  color: var(--text-primary, #e0e0e0);
  transition: background 0.15s;
}

.context-menu-item:hover {
  background: var(--bg-hover, #2a2a4a);
}

.context-menu-item.danger {
  color: #ff4c4c;
}

.context-menu-item.danger:hover {
  background: rgba(255, 76, 76, 0.1);
}

.context-menu-divider {
  height: 1px;
  background: var(--border-color, #2a2a4a);
  margin: 4px 0;
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
      color: var(--accent, #00f0ff);
    }
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
      color: var(--accent, #00f0ff);
      border-color: var(--accent, #00f0ff);
    }
  }
}
</style>
