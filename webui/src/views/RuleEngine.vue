<template>
  <div class="rule-engine">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-info">
        <h2>规则引擎</h2>
        <span class="subtitle">可视化规则编排与执行</span>
      </div>
      <button class="vg-btn vg-btn-primary" @click="handleCreateGraph">
        <PlusIcon />
        新建规则图
      </button>
    </div>

    <!-- 主内容区 -->
    <div class="main-content">
      <!-- 左侧规则图列表 -->
      <div class="vg-card graph-list-panel">
        <div class="panel-header">
          <h3>规则图</h3>
        </div>
        <div class="graph-list">
          <div
            v-for="graph in graphs"
            :key="graph.id"
            class="graph-item"
            :class="{ active: selectedGraph?.id === graph.id }"
            @click="selectGraph(graph)"
          >
            <div class="graph-info">
              <span class="graph-name">{{ graph.name }}</span>
              <span class="graph-time">{{ formatDate(graph.updated_at) }}</span>
            </div>
            <div class="graph-status">
              <span v-if="graph.is_active" class="vg-tag vg-tag-green">启用</span>
              <span v-else class="vg-tag">停用</span>
            </div>
          </div>
          <div v-if="graphs.length === 0" class="empty-tip">
            暂无规则图，点击上方按钮创建
          </div>
        </div>
      </div>

      <!-- 中间节点编辑器 -->
      <div class="vg-card node-editor-panel">
        <div class="panel-header">
          <h3>{{ selectedGraph?.name || '节点编辑器' }}</h3>
          <div class="editor-actions">
            <button class="vg-btn vg-btn-icon" @click="fitView" title="适应视图">
              <FitIcon />
            </button>
            <button class="vg-btn vg-btn-icon" @click="toggleMiniMap" title="小地图">
              <MapIcon />
            </button>
            <button class="vg-btn" @click="handleSaveGraph" :disabled="saving">
              {{ saving ? '保存中...' : '保存' }}
            </button>
            <button class="vg-btn vg-btn-primary" @click="handleExecute" :disabled="!selectedGraph || executing">
              {{ executing ? '执行中...' : '▶ 执行' }}
            </button>
          </div>
        </div>

        <!-- Vue Flow 编辑器 -->
        <div class="flow-container" v-if="selectedGraph">
          <VueFlow
            v-model:nodes="nodes"
            v-model:edges="edges"
            :node-types="nodeTypes"
            :edge-types="edgeTypes"
            :default-edge-options="defaultEdgeOptions"
            :connection-line-style="connectionLineStyle"
            fit-view-on-init
            @node-click="handleNodeClick"
            @pane-click="handlePaneClick"
          >
            <Background pattern-color="#2a2a3a" :gap="20" />
            <Controls />
            <MiniMap v-if="showMiniMap" />
          </VueFlow>
        </div>
        <div v-else class="empty-editor">
          <div class="empty-content">
            <FlowIcon class="empty-icon" />
            <p>选择或创建一个规则图开始编辑</p>
          </div>
        </div>
      </div>

      <!-- 右侧节点面板 -->
      <div class="vg-card node-palette-panel">
        <div class="panel-header">
          <h3>节点面板</h3>
        </div>
        <div class="node-categories">
          <div v-for="category in nodeCategories" :key="category.name" class="node-category">
            <div class="category-header" @click="category.expanded = !category.expanded">
              <component :is="category.icon" class="category-icon" />
              <span>{{ category.label }}</span>
              <ChevronIcon :class="{ rotated: category.expanded }" />
            </div>
            <div v-show="category.expanded" class="node-list">
              <div
                v-for="node in category.nodes"
                :key="node.type"
                class="node-item"
                draggable="true"
                @dragstart="handleDragStart($event, node)"
              >
                <span class="node-label">{{ node.label }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 节点配置面板 -->
        <div v-if="selectedNode" class="node-config-panel">
          <div class="panel-header">
            <h3>节点配置</h3>
            <button class="vg-btn vg-btn-icon" @click="selectedNode = null">
              <CloseIcon />
            </button>
          </div>
          <div class="config-form">
            <div class="form-group">
              <label>节点类型</label>
              <span class="vg-badge">{{ selectedNode.type }}</span>
            </div>
            <div v-for="(schema, key) in selectedNode.configSchema?.properties || {}" :key="key" class="form-group">
              <label>{{ schema.title || key }}</label>
              <input
                v-if="schema.type === 'string' || schema.type === 'number'"
                :type="schema.type === 'number' ? 'number' : 'text'"
                :value="selectedNodeConfig[key]"
                @input="updateNodeConfig(key, ($event.target as HTMLInputElement).value)"
                class="vg-input"
              />
              <select
                v-else-if="schema.type === 'boolean'"
                :value="selectedNodeConfig[key]"
                @change="updateNodeConfig(key, ($event.target as HTMLSelectElement).value === 'true')"
                class="vg-input"
              >
                <option :value="true">是</option>
                <option :value="false">否</option>
              </select>
              <input
                v-else-if="schema.type === 'array'"
                type="text"
                :value="JSON.stringify(selectedNodeConfig[key] || [])"
                @blur="updateNodeConfig(key, JSON.parse(($event.target as HTMLInputElement).value || '[]'))"
                class="vg-input"
              />
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 执行日志面板 -->
    <div v-if="executionLogs.length > 0" class="execution-logs-panel vg-card">
      <div class="panel-header">
        <h3>执行日志</h3>
        <button class="vg-btn vg-btn-icon" @click="executionLogs = []">
          <CloseIcon />
        </button>
      </div>
      <div class="logs-list">
        <div v-for="(log, index) in executionLogs" :key="index" class="log-item" :class="log.level">
          <span class="log-time">{{ log.timestamp }}</span>
          <span class="log-level">{{ log.level }}</span>
          <span class="log-message">{{ log.message }}</span>
        </div>
      </div>
    </div>

    <!-- 创建规则图对话框 -->
    <div class="dialog-overlay" v-if="showCreateDialog" @click.self="showCreateDialog = false">
      <div class="dialog-panel vg-card">
        <div class="dialog-header">
          <h3>创建新规则图</h3>
          <button class="close-btn" @click="showCreateDialog = false">
            <CloseIcon />
          </button>
        </div>
        <div class="dialog-body">
          <div class="form-group">
            <label>规则图名称</label>
            <input type="text" v-model="createForm.name" placeholder="输入规则图名称" class="vg-input" />
          </div>
          <div class="form-group">
            <label>描述</label>
            <textarea v-model="createForm.description" rows="3" placeholder="输入描述（可选）" class="vg-input"></textarea>
          </div>
        </div>
        <div class="dialog-footer">
          <button class="vg-btn" @click="showCreateDialog = false">取消</button>
          <button class="vg-btn vg-btn-primary" @click="handleCreate" :disabled="creating">
            {{ creating ? '创建中...' : '创建' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, markRaw } from 'vue'
import { VueFlow, useVueFlow, Background, Controls, MiniMap } from '@vue-flow/core'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import { ruleEngineApi } from '@/api'
import { ElMessage } from 'element-plus'

// 图标组件
const PlusIcon = markRaw({
  template: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>'
})
const CloseIcon = markRaw({
  template: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>'
})
const ChevronIcon = markRaw({
  template: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>',
  props: ['rotated'],
  computed: { class() { return this.rotated ? 'rotated' : '' } }
})
const FitIcon = markRaw({
  template: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"/></svg>'
})
const MapIcon = markRaw({
  template: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6"/><line x1="8" y1="2" x2="8" y2="18"/><line x1="16" y1="6" x2="16" y2="22"/></svg>'
})
const FlowIcon = markRaw({
  template: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="5" cy="12" r="3"/><circle cx="19" cy="12" r="3"/><path d="M8 12h8M13 9l3 3-3 3"/></svg>'
})
const TriggerIcon = markRaw({
  template: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>'
})
const ConditionIcon = markRaw({
  template: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>'
})
const ActionIcon = markRaw({
  template: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg>'
})
const LogicIcon = markRaw({
  template: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>'
})

// 状态
const graphs = ref<any[]>([])
const selectedGraph = ref<any>(null)
const nodes = ref<any[]>([])
const edges = ref<any[]>([])
const nodeDefinitions = ref<any[]>([])
const saving = ref(false)
const executing = ref(false)
const showCreateDialog = ref(false)
const showMiniMap = ref(true)
const createForm = reactive({ name: '', description: '' })
const creating = ref(false)
const selectedNode = ref<any>(null)
const selectedNodeConfig = ref<any>({})
const executionLogs = ref<any[]>([])

// VueFlow
const { fitView, onConnect, addEdges, getViewport } = useVueFlow()

// 节点分类
const nodeCategories = computed(() => {
  const categories = [
    { name: 'trigger', label: '触发器', icon: markRaw(TriggerIcon), expanded: true, nodes: [] as any[] },
    { name: 'condition', label: '条件', icon: markRaw(ConditionIcon), expanded: true, nodes: [] as any[] },
    { name: 'action', label: '动作', icon: markRaw(ActionIcon), expanded: true, nodes: [] as any[] },
    { name: 'logic', label: '逻辑', icon: markRaw(LogicIcon), expanded: true, nodes: [] as any[] },
  ]

  nodeDefinitions.value.forEach((def: any) => {
    const cat = categories.find(c => c.name === def.category)
    if (cat) {
      cat.nodes.push(def)
    }
  })

  return categories
})

// 默认边样式
const defaultEdgeOptions = {
  type: 'smoothstep',
  animated: true,
  style: { stroke: '#00f0ff', strokeWidth: 2 }
}

// 连接线样式
const connectionLineStyle = {
  stroke: '#00f0ff',
  strokeWidth: 2
}

// 节点类型（后续扩展自定义节点）
const nodeTypes = {}
const edgeTypes = {}

// 生命周期
onMounted(async () => {
  await loadGraphs()
  await loadNodeDefinitions()
})

// 加载规则图列表
async function loadGraphs() {
  try {
    const res = await ruleEngineApi.listGraphs()
    graphs.value = res.data
  } catch (err) {
    console.error('加载规则图失败:', err)
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

// 选择规则图
async function selectGraph(graph: any) {
  selectedGraph.value = graph
  try {
    const res = await ruleEngineApi.getGraphDetail(graph.id)
    const data = res.data

    // 转换数据格式
    nodes.value = data.nodes.map((n: any) => ({
      id: n.id,
      type: n.type,
      position: n.position || { x: 0, y: 0 },
      data: n.data || {},
      label: n.type
    }))

    edges.value = data.edges.map((e: any) => ({
      id: e.id,
      source: e.source,
      target: e.target,
      sourceHandle: e.source_handle,
      targetHandle: e.target_handle,
      type: 'smoothstep',
      animated: true
    }))
  } catch (err) {
    console.error('加载规则图详情失败:', err)
  }
}

// 创建规则图
async function handleCreateGraph() {
  createForm.name = ''
  createForm.description = ''
  showCreateDialog.value = true
}

async function handleCreate() {
  if (!createForm.name.trim()) {
    ElMessage.warning('请输入规则图名称')
    return
  }

  creating.value = true
  try {
    const res = await ruleEngineApi.createGraph({
      name: createForm.name,
      description: createForm.description
    })
    graphs.value.unshift(res.data)
    showCreateDialog.value = false
    selectGraph(res.data)
    ElMessage.success('创建成功')
  } catch (err) {
    console.error('创建规则图失败:', err)
    ElMessage.error('创建失败')
  } finally {
    creating.value = false
  }
}

// 保存规则图
async function handleSaveGraph() {
  if (!selectedGraph.value) return

  saving.value = true
  try {
    await ruleEngineApi.updateGraph(selectedGraph.value.id, {
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
    ElMessage.success('保存成功')
  } catch (err) {
    console.error('保存规则图失败:', err)
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

// 执行规则图
async function handleExecute() {
  if (!selectedGraph.value) return

  executing.value = true
  executionLogs.value = []
  try {
    const res = await ruleEngineApi.execute({
      graph_id: selectedGraph.value.id,
      trigger_type: 'manual'
    })

    if (res.data.result?.logs) {
      executionLogs.value = res.data.result.logs
    }

    ElMessage.success(`执行完成: ${res.data.status}`)
  } catch (err) {
    console.error('执行规则图失败:', err)
    ElMessage.error('执行失败')
  } finally {
    executing.value = false
  }
}

// 拖拽开始
function handleDragStart(event: DragEvent, nodeDef: any) {
  event.dataTransfer?.setData('application/json', JSON.stringify(nodeDef))
}

// 节点点击
function handleNodeClick(event: any) {
  const nodeId = event.node.id
  const node = nodes.value.find(n => n.id === nodeId)
  if (node) {
    const def = nodeDefinitions.value.find((d: any) => d.type === node.type)
    selectedNode.value = { ...node, ...def }
    selectedNodeConfig.value = { ...node.data }
  }
}

// 画布点击
function handlePaneClick() {
  selectedNode.value = null
}

// 更新节点配置
function updateNodeConfig(key: string, value: any) {
  selectedNodeConfig.value[key] = value

  // 更新节点数据
  const node = nodes.value.find(n => n.id === selectedNode.value.id)
  if (node) {
    node.data = { ...selectedNodeConfig.value }
  }
}

// 切换小地图
function toggleMiniMap() {
  showMiniMap.value = !showMiniMap.value
}

// 格式化日期
function formatDate(dateStr: string) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// 边连接处理
onConnect((params: any) => {
  addEdges([{
    ...params,
    type: 'smoothstep',
    animated: true,
    id: `e-${params.source}-${params.target}-${Date.now()}`
  }])
})
</script>

<style scoped lang="scss">
.rule-engine {
  display: flex;
  flex-direction: column;
  height: 100%;
  gap: 16px;
  padding: 24px;
  overflow: hidden;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;

  .header-info {
    h2 {
      font-size: 20px;
      font-weight: 600;
      margin-bottom: 4px;
    }

    .subtitle {
      font-size: 13px;
      color: var(--text-secondary);
    }
  }
}

.main-content {
  display: flex;
  flex: 1;
  gap: 16px;
  overflow: hidden;
}

.graph-list-panel {
  width: 240px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;

  .panel-header {
    padding: 16px;
    border-bottom: 1px solid var(--border-color);

    h3 {
      font-size: 14px;
      font-weight: 600;
    }
  }

  .graph-list {
    flex: 1;
    overflow-y: auto;
    padding: 8px;
  }

  .graph-item {
    padding: 12px;
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.2s;
    margin-bottom: 4px;

    &:hover {
      background: var(--bg-hover);
    }

    &.active {
      background: var(--bg-hover);
      border: 1px solid var(--accent-cyan);
    }

    .graph-info {
      margin-bottom: 8px;
    }

    .graph-name {
      display: block;
      font-size: 13px;
      font-weight: 500;
      margin-bottom: 4px;
    }

    .graph-time {
      font-size: 11px;
      color: var(--text-muted);
    }
  }

  .empty-tip {
    padding: 20px;
    text-align: center;
    color: var(--text-muted);
    font-size: 13px;
  }
}

.node-editor-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;

  .panel-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 16px;
    border-bottom: 1px solid var(--border-color);

    h3 {
      font-size: 14px;
      font-weight: 600;
    }

    .editor-actions {
      display: flex;
      gap: 8px;
      align-items: center;
    }
  }

  .flow-container {
    flex: 1;
    background: var(--bg-secondary);
  }

  .empty-editor {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;

    .empty-content {
      text-align: center;
      color: var(--text-muted);

      .empty-icon {
        width: 64px;
        height: 64px;
        margin-bottom: 16px;
        opacity: 0.5;
      }

      p {
        font-size: 14px;
      }
    }
  }
}

.node-palette-panel {
  width: 280px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;

  .panel-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px;
    border-bottom: 1px solid var(--border-color);

    h3 {
      font-size: 14px;
      font-weight: 600;
    }
  }

  .node-categories {
    flex: 1;
    overflow-y: auto;
    padding: 8px;
  }

  .node-category {
    margin-bottom: 4px;

    .category-header {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 10px 12px;
      border-radius: 6px;
      cursor: pointer;
      transition: all 0.2s;
      color: var(--text-secondary);

      &:hover {
        background: var(--bg-hover);
        color: var(--text-primary);
      }

      .category-icon {
        width: 16px;
        height: 16px;
      }

      span {
        flex: 1;
        font-size: 13px;
        font-weight: 500;
      }

      svg {
        width: 16px;
        height: 16px;
        transition: transform 0.2s;

        &.rotated {
          transform: rotate(180deg);
        }
      }
    }

    .node-list {
      padding: 4px 0 8px 0;
    }

    .node-item {
      padding: 8px 12px 8px 32px;
      border-radius: 4px;
      cursor: grab;
      font-size: 12px;
      color: var(--text-secondary);
      transition: all 0.2s;

      &:hover {
        background: var(--bg-hover);
        color: var(--text-primary);
      }

      &:active {
        cursor: grabbing;
      }
    }
  }

  .node-config-panel {
    border-top: 1px solid var(--border-color);
    max-height: 50%;

    .panel-header {
      h3 {
        font-size: 13px;
      }
    }

    .config-form {
      padding: 12px;
      overflow-y: auto;
      max-height: 300px;
    }

    .form-group {
      margin-bottom: 12px;

      label {
        display: block;
        font-size: 11px;
        color: var(--text-secondary);
        margin-bottom: 4px;
      }

      .vg-badge {
        font-size: 11px;
      }
    }
  }
}

.execution-logs-panel {
  max-height: 200px;
  flex-shrink: 0;

  .panel-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 16px;
    border-bottom: 1px solid var(--border-color);

    h3 {
      font-size: 13px;
      font-weight: 600;
    }
  }

  .logs-list {
    padding: 8px 12px;
    max-height: 150px;
    overflow-y: auto;
  }

  .log-item {
    display: flex;
    gap: 12px;
    padding: 6px 0;
    font-size: 12px;
    border-bottom: 1px solid var(--border-color);

    &:last-child {
      border-bottom: none;
    }

    .log-time {
      color: var(--text-muted);
      flex-shrink: 0;
    }

    .log-level {
      flex-shrink: 0;
      padding: 2px 6px;
      border-radius: 3px;
      font-size: 10px;
      font-weight: 600;
    }

    &.info .log-level {
      background: rgba(0, 240, 255, 0.15);
      color: var(--accent-cyan);
    }

    &.warning .log-level {
      background: rgba(255, 221, 0, 0.15);
      color: var(--accent-yellow);
    }

    &.error .log-level {
      background: rgba(255, 0, 170, 0.15);
      color: var(--accent-magenta);
    }

    .log-message {
      flex: 1;
      color: var(--text-secondary);
    }
  }
}

.dialog-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.dialog-panel {
  width: 420px;
  max-width: 90vw;
  animation: dialogIn 0.2s ease;
}

.dialog-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-color);

  h3 {
    font-size: 16px;
    font-weight: 600;
  }

  .close-btn {
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: transparent;
    border: none;
    color: var(--text-muted);
    cursor: pointer;
    border-radius: 6px;
    transition: all 0.2s;

    &:hover {
      background: var(--bg-hover);
      color: var(--text-primary);
    }

    svg {
      width: 18px;
      height: 18px;
    }
  }
}

.dialog-body {
  padding: 24px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 24px;
  border-top: 1px solid var(--border-color);
}

.form-group {
  margin-bottom: 16px;

  label {
    display: block;
    font-size: 13px;
    color: var(--text-secondary);
    margin-bottom: 8px;
  }
}

:deep(.el-table) {
  --el-table-bg-color: var(--bg-card);
  --el-table-tr-bg-color: var(--bg-card);
  --el-table-header-bg-color: var(--bg-secondary);
  --el-table-text-color: var(--text-primary);
  --el-table-border-color: var(--border-color);
}

:deep(.vue-flow) {
  --vf-node-bg: var(--bg-card);
  --vf-node-text: var(--text-primary);
  --vf-node-border: var(--border-color);
  --vf-node-handle: var(--accent-cyan);
}
</style>
