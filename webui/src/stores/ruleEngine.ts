// -*- coding: utf-8 -*-
/**
 * 规则引擎状态管理 - Pinia Store
 *
 * 提供规则引擎的全局状态管理，作为唯一数据源（Single Source of Truth）。
 * RuleCanvas（画布视图）和 RuleNode（节点组件）均从此读取/写入状态。
 * VueFlow 通过 storeToRefs 绑定的 writable ref 与 store 保持同步。
 */

import { defineStore } from 'pinia'
import { ref, computed, shallowRef, triggerRef } from 'vue'
import { ruleEngineApi, modelApi } from '@/api'
import type {
  NodeDefinition as NodeDefinitionBase,
  GraphNode as GraphNodeBase,
  GraphEdge as GraphEdgeBase,
  VariableDefaultValue as VariableDefaultValueBase,
  ConfigSchemaProperty,
  RuleNodeData,
  VariableType
} from '@/types/api'
import type { Node, Edge } from '@vue-flow/core'
import { MarkerType } from '@vue-flow/core'

// ============ 类型别名（兼容旧代码）============

export type VariableDefaultValue = VariableDefaultValueBase
export { ConfigSchemaProperty, RuleNodeData, VariableType }
export type NodeDefinition = NodeDefinitionBase
export type GraphNode = GraphNodeBase
export type GraphEdge = GraphEdgeBase

export interface Variable {
  name: string
  type: VariableType
  defaultValue?: VariableDefaultValue
  description?: string
}

/** 规则图元数据 */
export interface GraphMeta {
  id: number
  name: string
  description?: string
  is_active: boolean
  version?: string
  thumbnail?: string
}

/** 执行状态 */
export interface ExecutionState {
  status: 'idle' | 'running' | 'success' | 'failed'
  progress: number
  executionId: number | null
  logs: Array<{
    level: string
    timestamp: string
    node_type?: string
    message: string
    duration_ms?: number
    /** 节点输出指标（如 detections 数量、数据量等） */
    metrics?: Record<string, number>
  }>
  nodeStates: Record<string, string>
}

// ============ Store 定义 ============

export const useRuleEngineStore = defineStore('ruleEngine', () => {
  // ============ 状态 ============

  /** 节点定义列表（节点面板数据） */
  const nodeDefinitions = ref<NodeDefinition[]>([])

  /** 规则图元数据 */
  const graphMeta = ref<GraphMeta | null>(null)

  /** 规则图节点 - 唯一数据源，VueFlow 监听此 ref 变化。
   * 使用 shallowRef 避免对每个节点内部 (data/position/dimensions) 都建深代理：
   * 节点数据是 VueFlow 内部管理的异构树，深代理无意义且在 30+ 节点时
   * 严重拖累响应式追踪。改内部属性后需 triggerRef() 触发响应。
   */
  const nodes = shallowRef<Node<RuleNodeData>[]>([])

  /** 规则图边 - 同上原因用 shallowRef。 */
  const edges = shallowRef<Edge[]>([])

  /** 选中的节点 ID */
  const selectedNodeId = ref<string | null>(null)

  /** 变量列表 */
  const variables = ref<Variable[]>([])

  /** 可用模型列表（供 model-select widget 使用） */
  const availableModels = ref<Array<{ id: number; name: string }>>([])

  /** 执行状态 */
  const executionState = ref<ExecutionState>({
    status: 'idle',
    progress: 0,
    executionId: null,
    logs: [],
    nodeStates: {}
  })

  // ---- Undo/Redo 栈 ----
  const historyStack = ref<Array<{ nodes: GraphNode[]; edges: GraphEdge[] }>>([])
  const historyIndex = ref(-1)
  const isHistoryPaused = ref(false)
  const maxHistorySize = 20

  // ============ 计算属性 ============

  /** 选中的节点对象 */
  const selectedNode = computed((): Node<RuleNodeData> | null => {
    const list: Node<RuleNodeData>[] = nodes.value
    return list.find(n => n.id === selectedNodeId.value) ?? null
  })

  /** 是否可以撤销 */
  const canUndo = computed(() => historyIndex.value > 0)

  /** 是否可以重做 */
  const canRedo = computed(() => historyIndex.value < historyStack.value.length - 1)

  /** 是否有节点 */
  const hasNodes = computed(() => nodes.value.length > 0)

  /** 按类别分组的节点定义 */
  const nodeDefinitionsByCategory = computed(() => {
    const map: Record<string, NodeDefinition[]> = {}
    for (const def of nodeDefinitions.value) {
      if (!map[def.category]) map[def.category] = []
      map[def.category].push(def)
    }
    return map
  })

  // ============ 数据加载 ============

  /** 获取节点定义列表 */
  async function fetchNodeDefinitions() {
    try {
      const res = await ruleEngineApi.getNodeDefinitions()
      nodeDefinitions.value = res.data
      return res.data
    } catch (err) {
      console.error('加载节点定义失败:', err)
      return []
    }
  }

  /** 加载可用模型列表 */
  async function fetchModels() {
    try {
      const res = await modelApi.list()
      availableModels.value = res.data as Array<{ id: number; name: string }>
    } catch (err) {
      console.error('加载模型列表失败:', err)
    }
  }

  /**
   * 加载规则图 - 从 API 获取并解析为 VueFlow 可用的节点/边格式。
   *
   * 数据规范：
   * - n.type 始终归一化为 'ruleNode'（VueFlow 组件类型）
   * - 原始业务类型（如 yolo_model）存储在 n.data.type 中
   * - 兼容旧数据：旧版 n.type 可能为 'ruleNode'/'rule-node'
   */
  async function loadGraph(id: number) {
    const res = await ruleEngineApi.getGraphDetail(id)
    const data = res.data

    graphMeta.value = {
      id: data.id,
      name: data.name,
      description: data.description,
      is_active: data.is_active,
      version: data.version,
      thumbnail: data.thumbnail
    }

    // 解析节点：标准化 type 字段，补充必要属性
    nodes.value = (data.nodes ?? []).map((n: GraphNode) => {
      const isVueFlowType = n.type === 'ruleNode' || n.type === 'rule-node'
      return {
        id: n.id,
        type: 'ruleNode',
        position: n.position ?? { x: 0, y: 0 },
        data: {
          ...(n.data ?? {}),
          // 确保 data.type 为原始业务类型（兼容新旧数据格式）
          type: isVueFlowType ? (n.data?.type ?? 'unknown') : n.type,
          id: n.id
        } as RuleNodeData
      }
    })

    // 解析边
    edges.value = (data.edges ?? []).map((e: GraphEdge) => ({
      id: e.id,
      source: e.source,
      target: e.target,
      sourceHandle: e.source_handle,
      targetHandle: e.target_handle,
      type: 'default',
      animated: false,
      markerEnd: MarkerType.ArrowClosed
    }))

    // 解析变量
    if (data.variables_json) {
      try {
        const vars = JSON.parse(data.variables_json) as Record<string, {
          type?: string; defaultValue?: VariableDefaultValue; description?: string
        }>
        variables.value = Object.entries(vars).map(([name, config]) => ({
          name,
          type: (config.type as VariableType) ?? 'STRING',
          defaultValue: config.defaultValue ?? '',
          description: config.description ?? ''
        }))
      } catch {
        variables.value = []
      }
    } else if (data.variables) {
      // 后端返回 Record<string, {type, defaultValue, description}>
      const vars = data.variables as Record<string, {
        type?: VariableType
        defaultValue?: VariableDefaultValue
        description?: string
      }>
      variables.value = Object.entries(vars).map(([name, config]) => ({
        name,
        type: config.type ?? 'STRING',
        defaultValue: config.defaultValue,
        description: config.description ?? ''
      }))
    }

    saveHistory()
    return data
  }

  // ============ 保存 ============

  /**
   * 保存规则图 - 将节点/边序列化为 JSON 字符串写入后端。
   *
   * 保存规范：
   * - 只保存业务字段（id, position, data），不保存 VueFlow 内部字段
   * - type 保存原始业务类型（n.data.type），便于后续兼容
   */
  async function saveGraph() {
    if (!graphMeta.value) return

    const varsObj: Record<string, {
      type: VariableType; defaultValue: VariableDefaultValue; description: string
    }> = {}
    for (const v of variables.value) {
      varsObj[v.name] = {
        type: v.type,
        defaultValue: v.defaultValue ?? null,
        description: v.description ?? ''
      }
    }

    await ruleEngineApi.updateGraph(graphMeta.value.id, {
      name: graphMeta.value.name,
      nodes_json: JSON.stringify(nodes.value.map(n => ({
        id: n.id,
        type: n.data?.type ?? 'unknown',
        position: n.position,
        data: n.data
      }))),
      edges_json: JSON.stringify(edges.value.map(e => ({
        id: e.id,
        source: e.source,
        target: e.target,
        source_handle: e.sourceHandle,
        target_handle: e.targetHandle
      }))),
      variables_json: JSON.stringify(varsObj)
    })

    saveHistory()
  }

  // ============ 节点操作 ============

  /**
   * 创建并添加节点到画布。
   * - 使用 'ruleNode' 作为 VueFlow 组件类型
   * - 原始业务类型（如 yolo_model）存储在 data.type 中
   * - 自动从 configSchema 提取默认配置值
   */
  function createNode(
    def: NodeDefinition,
    position: { x: number; y: number }
  ): boolean {
    const id = `node_${Date.now()}`
    const newNode: Node<RuleNodeData> = {
      id,
      type: 'ruleNode',
      position: { ...position },
      data: {
        id,
        type: def.type,
        label: def.label,
        category: def.category,
        description: def.description,
        inputs: def.inputs,
        outputs: def.outputs,
        configSchema: def.config_schema,
        config: getDefaultConfig(def.config_schema),
        status: 'idle',
        selected: false
      } as unknown as RuleNodeData
    }
    nodes.value.push(newNode)
    saveHistory()
    return true
  }

  /**
   * 更新节点配置 - 内部 mutate + 手动 triggerRef。
   * 之前用 `node.data = {...}` 整体重建引用，触发 VueFlow diff 整节点。
   * 改为 mutate 内部 config 字段后 triggerRef，避免节点重渲染，
   * 仅触发布局（widget 自身 reactivity）。
   */
  function updateNodeConfig(nodeId: string, key: string, value: VariableDefaultValue) {
    const node = nodes.value.find(n => n.id === nodeId)
    if (node?.data) {
      if (!node.data.config) {
        node.data.config = {} as Record<string, VariableDefaultValue>
      }
      node.data.config[key] = value
      triggerRef(nodes)
    }
  }

  /**
   * 删除节点并清理关联边 / 选中状态 / 历史记录。
   */
  function removeNode(nodeId: string) {
    nodes.value = nodes.value.filter(n => n.id !== nodeId)
    edges.value = edges.value.filter(e => e.source !== nodeId && e.target !== nodeId)
    if (selectedNodeId.value === nodeId) {
      selectedNodeId.value = null
    }
    saveHistory()
  }

  /** 选中节点 */
  function selectNode(nodeId: string | null) {
    selectedNodeId.value = nodeId
  }

  // ============ 边操作 ============

  /** 添加边 */
  function addEdge(connection: {
    source: string; target: string
    sourceHandle?: string | null; targetHandle?: string | null
  }) {
    edges.value.push({
      id: `edge_${Date.now()}`,
      source: connection.source,
      target: connection.target,
      sourceHandle: connection.sourceHandle ?? undefined,
      targetHandle: connection.targetHandle ?? undefined,
      type: 'default',
      animated: false
    })
    saveHistory()
  }

  /** 删除边 */
  function removeEdge(edgeId: string) {
    edges.value = edges.value.filter(e => e.id !== edgeId)
    saveHistory()
  }

  // ============ Undo/Redo ============

  /** 序列化时需要丢弃的 VueFlow 内部字段（DOM 引用、计算尺寸等） */
  const VUEFLOW_INTERNAL_KEYS = [
    'selected', 'dragging', 'parentNode', 'dimensions', 'handleBounds',
    'internals', 'events', 'selectable', 'deletable', 'focusable',
    'updatable', 'resizing', 'initialized', 'resizer', 'dragHandle',
  ] as const

  /** 深拷贝节点/边用于历史快照 - 使用 JSON 路线避免 structuredClone 撞上 DOM/Proxy。
   * 在 JSON 序列化前剥离 VueFlow 内部字段（DOM 引用、循环引用根）。 */
  function cloneForHistory<T>(items: T[]): T[] {
    return items.map(item => {
      const cleaned: any = {}
      for (const key in item) {
        if ((VUEFLOW_INTERNAL_KEYS as readonly string[]).includes(key)) continue
        cleaned[key] = (item as any)[key]
      }
      return cleaned as T
    })
  }

  /** 保存当前状态到历史栈 */
  function saveHistory() {
    if (isHistoryPaused.value) return
    historyStack.value = historyStack.value.slice(0, historyIndex.value + 1)
    historyStack.value.push({
      nodes: cloneForHistory(nodes.value) as any,
      edges: edges.value.map(e => ({ ...e, selected: false })),
    })
    historyIndex.value = historyStack.value.length - 1
    if (historyStack.value.length > maxHistorySize) {
      historyStack.value.shift()
      historyIndex.value--
    }
  }

  /** 撤销 */
  function undo() {
    if (!canUndo.value) return
    historyIndex.value--
    const snapshot = historyStack.value[historyIndex.value]
    nodes.value = JSON.parse(JSON.stringify(snapshot.nodes))
    edges.value = JSON.parse(JSON.stringify(snapshot.edges))
  }

  /** 重做 */
  function redo() {
    if (!canRedo.value) return
    historyIndex.value++
    const snapshot = historyStack.value[historyIndex.value]
    nodes.value = JSON.parse(JSON.stringify(snapshot.nodes))
    edges.value = JSON.parse(JSON.stringify(snapshot.edges))
  }

  /** 暂停历史记录（拖拽等批量操作） */
  function pauseHistory() {
    isHistoryPaused.value = true
  }

  /** 恢复历史记录并保存快照 */
  function unpauseHistory() {
    isHistoryPaused.value = false
    saveHistory()
  }

  // ============ 变量操作 ============

  function addVariable(variable?: Partial<Variable>): Variable {
    const newVar: Variable = {
      name: variable?.name ?? `var_${variables.value.length + 1}`,
      type: variable?.type ?? 'STRING',
      defaultValue: variable?.defaultValue ?? '',
      description: variable?.description ?? ''
    }
    variables.value.push(newVar)
    return newVar
  }

  function removeVariable(name: string) {
    variables.value = variables.value.filter(v => v.name !== name)
  }

  function updateVariable(name: string, updates: Partial<Variable>) {
    const v = variables.value.find(item => item.name === name)
    if (v) {
      Object.assign(v, updates)
    }
  }

  function getVariable(name: string): Variable | undefined {
    return variables.value.find(v => v.name === name)
  }

  // ============ 执行管理 ============

  function setExecutionStatus(status: ExecutionState['status']) {
    executionState.value.status = status
  }

  function addExecutionLog(log: ExecutionState['logs'][0]) {
    executionState.value.logs.push(log)
  }

  function setExecutionProgress(progress: number) {
    executionState.value.progress = progress
  }

  function setNodeExecutionState(nodeId: string, state: string) {
    executionState.value.nodeStates[nodeId] = state
  }

  function clearExecution() {
    executionState.value = {
      status: 'idle',
      progress: 0,
      executionId: null,
      logs: [],
      nodeStates: {}
    }
  }

  function setExecutionId(id: number) {
    executionState.value.executionId = id
  }

  // ============ 辅助函数 ============

  /**
   * 从 config_schema 提取默认配置值。
   */
  function getDefaultConfig(
    schema: Record<string, ConfigSchemaProperty>
  ): Record<string, VariableDefaultValue> {
    const config: Record<string, VariableDefaultValue> = {}
    for (const [key, prop] of Object.entries(schema)) {
      if (prop.default !== undefined) {
        config[key] = prop.default
      }
    }
    return config
  }

  /**
   * 获取节点类型对应的分类名称。
   */
  function getNodeCategory(type: string): string {
    const def = nodeDefinitions.value.find(d => d.type === type)
    return def?.category ?? 'action'
  }

  // ============ 导出 ============
  return {
    // 状态
    nodeDefinitions,
    graphMeta,
    nodes,
    edges,
    selectedNodeId,
    variables,
    availableModels,
    executionState,
    historyStack,
    historyIndex,
    isHistoryPaused,
    maxHistorySize,

    // 计算属性
    selectedNode,
    canUndo,
    canRedo,
    hasNodes,
    nodeDefinitionsByCategory,

    // 数据加载
    fetchNodeDefinitions,
    fetchModels,
    loadGraph,
    saveGraph,

    // 节点操作
    createNode,
    updateNodeConfig,
    removeNode,
    selectNode,

    // 边操作
    addEdge,
    removeEdge,

    // Undo/Redo
    saveHistory,
    undo,
    redo,
    pauseHistory,
    unpauseHistory,

    // 变量操作
    addVariable,
    removeVariable,
    updateVariable,
    getVariable,

    // 执行管理
    setExecutionStatus,
    addExecutionLog,
    setExecutionProgress,
    setNodeExecutionState,
    clearExecution,
    setExecutionId,

    // 辅助函数
    getDefaultConfig,
    getNodeCategory
  }
})
