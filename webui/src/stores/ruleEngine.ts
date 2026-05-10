// -*- coding: utf-8 -*-
/**
 * 规则引擎状态管理 - Pinia Store
 *
 * 提供规则引擎的全局状态管理，包括节点定义、规则图、变量、撤销重做等。
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { ruleEngineApi } from '@/api'

// ============ 类型定义 ============

export interface ConfigSchemaProperty {
  type: string
  title?: string
  description?: string
  default?: any
  minimum?: number
  maximum?: number
  step?: number
  enum?: string[]
  widget?: string
  visible?: string  // 条件可见，如 "source=file"
}

export interface NodeDefinition {
  type: string
  category: string
  label: string
  description?: string
  icon?: string
  inputs: Array<{ name: string; type: string; label?: string }>
  outputs: Array<{ name: string; type: string; label?: string }>
  config_schema: Record<string, ConfigSchemaProperty>
}

export interface GraphNode {
  id: string
  type: string
  position: { x: number; y: number }
  data: {
    type: string
    label?: string
    category: string
    inputs?: Array<{ name: string; type: string; label?: string }>
    outputs?: Array<{ name: string; type: string; label?: string }>
    configSchema?: Record<string, ConfigSchemaProperty>
    config?: Record<string, any>
    status?: 'idle' | 'running' | 'success' | 'failed'
  }
}

export interface GraphEdge {
  id: string
  source: string
  target: string
  source_handle?: string
  target_handle?: string
}

export type VariableType = 'STRING' | 'NUMBER' | 'BOOLEAN' | 'IMAGE' | 'BBOX'

export interface Variable {
  name: string
  type: VariableType
  defaultValue?: any
  description?: string
}

// ============ Store 定义 ============

export const useRuleEngineStore = defineStore('ruleEngine', () => {
  // ---- 状态 ----

  /** 节点定义列表 */
  const nodeDefinitions = ref<NodeDefinition[]>([])

  /** 当前规则图 */
  const currentGraph = ref<{
    id: number
    name: string
    description?: string
    is_active: boolean
    nodes: GraphNode[]
    edges: GraphEdge[]
  } | null>(null)

  /** 选中的节点 ID */
  const selectedNodeId = ref<string | null>(null)

  /** 执行状态 - 正在执行的图 ID */
  const executingGraphId = ref<number | null>(null)

  /** 执行历史 */
  const executionHistory = ref<Array<{
    id: number
    status: string
    start_time: string
    end_time?: string
  }>>([])

  /** 变量列表 */
  const variables = ref<Variable[]>([])

  // ---- Undo/Redo 栈 ----
  const historyStack = ref<Array<{ nodes: GraphNode[]; edges: GraphEdge[] }>>([])
  const historyIndex = ref(-1)
  const maxHistorySize = 20

  // ---- 计算属性 ----

  /** 选中的节点 */
  const selectedNode = computed(() =>
    currentGraph.value?.nodes.find(n => n.id === selectedNodeId.value) ?? null
  )

  /** 是否可以撤销 */
  const canUndo = computed(() => historyIndex.value > 0)

  /** 是否可以重做 */
  const canRedo = computed(() => historyIndex.value < historyStack.value.length - 1)

  /** 按类别分组的节点定义 */
  const nodeDefinitionsByCategory = computed(() => {
    const map: Record<string, NodeDefinition[]> = {}
    for (const def of nodeDefinitions.value) {
      if (!map[def.category]) map[def.category] = []
      map[def.category].push(def)
    }
    return map
  })

  // ---- Actions ----

  /**
   * 获取节点定义列表
   */
  async function fetchNodeDefinitions() {
    const res = await ruleEngineApi.getNodeDefinitions()
    nodeDefinitions.value = res.data
    return res.data
  }

  /**
   * 获取规则图详情
   */
  async function fetchGraph(id: number) {
    const res = await ruleEngineApi.getGraphDetail(id)
    currentGraph.value = res.data

    // 解析变量
    if (res.data.variables_json) {
      try {
        const vars = JSON.parse(res.data.variables_json)
        variables.value = Object.entries(vars).map(([name, config]: [string, any]) => ({
          name,
          type: (config.type as VariableType) ?? 'STRING',
          defaultValue: config.defaultValue ?? '',
          description: config.description ?? ''
        }))
      } catch {
        variables.value = []
      }
    } else if (res.data.variables) {
      variables.value = res.data.variables
    }

    // 初始化撤销栈
    saveToHistory()
    return res.data
  }

  /**
   * 保存规则图
   */
  async function saveGraph() {
    if (!currentGraph.value) return

    // 构建变量 JSON
    const varsObj: Record<string, any> = {}
    for (const v of variables.value) {
      varsObj[v.name] = {
        type: v.type,
        defaultValue: v.defaultValue,
        description: v.description
      }
    }

    await ruleEngineApi.updateGraph(currentGraph.value.id, {
      name: currentGraph.value.name,
      nodes_json: JSON.stringify(currentGraph.value.nodes),
      edges_json: JSON.stringify(currentGraph.value.edges),
      variables_json: JSON.stringify(varsObj)
    })
  }

  // ---- 节点操作 ----

  /**
   * 添加节点到画布
   */
  function addNode(def: NodeDefinition, position: { x: number; y: number }): string | undefined {
    if (!currentGraph.value) return

    const id = `node_${Date.now()}`
    const newNode: GraphNode = {
      id,
      type: 'rule-node',
      position,
      data: {
        type: def.type,
        label: def.label,
        category: def.category,
        inputs: def.inputs,
        outputs: def.outputs,
        configSchema: def.config_schema,
        config: getDefaultConfig(def.config_schema),
        status: 'idle'
      }
    }

    currentGraph.value.nodes.push(newNode)
    saveToHistory()
    return id
  }

  /**
   * 更新节点配置
   */
  function updateNodeConfig(nodeId: string, key: string, value: any) {
    const node = currentGraph.value?.nodes.find(n => n.id === nodeId)
    if (node) {
      node.data.config = node.data.config ?? {}
      node.data.config[key] = value
    }
  }

  /**
   * 删除节点
   */
  function removeNode(nodeId: string) {
    if (!currentGraph.value) return

    currentGraph.value.nodes = currentGraph.value.nodes.filter(n => n.id !== nodeId)
    currentGraph.value.edges = currentGraph.value.edges.filter(
      e => e.source !== nodeId && e.target !== nodeId
    )

    if (selectedNodeId.value === nodeId) {
      selectedNodeId.value = null
    }

    saveToHistory()
  }

  /**
   * 选择节点
   */
  function selectNode(nodeId: string | null) {
    selectedNodeId.value = nodeId
  }

  // ---- 边操作 ----

  /**
   * 添加边
   */
  function addEdge(edge: Omit<GraphEdge, 'id'>) {
    if (!currentGraph.value) return
    const id = `edge_${Date.now()}`
    currentGraph.value.edges.push({ ...edge, id })
    saveToHistory()
  }

  /**
   * 删除边
   */
  function removeEdge(edgeId: string) {
    if (!currentGraph.value) return
    currentGraph.value.edges = currentGraph.value.edges.filter(e => e.id !== edgeId)
    saveToHistory()
  }

  // ---- Undo/Redo ----

  /**
   * 保存状态到历史记录
   */
  function saveToHistory() {
    if (!currentGraph.value) return

    const snapshot = {
      nodes: JSON.parse(JSON.stringify(currentGraph.value.nodes)),
      edges: JSON.parse(JSON.stringify(currentGraph.value.edges))
    }

    // 截断 redo 栈
    historyStack.value = historyStack.value.slice(0, historyIndex.value + 1)
    historyStack.value.push(snapshot)

    // 限制栈大小
    if (historyStack.value.length > maxHistorySize) {
      historyStack.value.shift()
    } else {
      historyIndex.value++
    }
  }

  /**
   * 撤销
   */
  function undo() {
    if (!canUndo.value || !currentGraph.value) return
    historyIndex.value--
    const snapshot = historyStack.value[historyIndex.value]
    currentGraph.value.nodes = JSON.parse(JSON.stringify(snapshot.nodes))
    currentGraph.value.edges = JSON.parse(JSON.stringify(snapshot.edges))
  }

  /**
   * 重做
   */
  function redo() {
    if (!canRedo.value || !currentGraph.value) return
    historyIndex.value++
    const snapshot = historyStack.value[historyIndex.value]
    currentGraph.value.nodes = JSON.parse(JSON.stringify(snapshot.nodes))
    currentGraph.value.edges = JSON.parse(JSON.stringify(snapshot.edges))
  }

  // ---- 变量操作 ----

  /**
   * 添加变量
   */
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

  /**
   * 删除变量
   */
  function removeVariable(name: string) {
    variables.value = variables.value.filter(v => v.name !== name)
  }

  /**
   * 更新变量
   */
  function updateVariable(name: string, updates: Partial<Variable>) {
    const v = variables.value.find(item => item.name === name)
    if (v) {
      Object.assign(v, updates)
    }
  }

  /**
   * 获取变量
   */
  function getVariable(name: string): Variable | undefined {
    return variables.value.find(v => v.name === name)
  }

  // ---- 辅助函数 ----

  /**
   * 从 config_schema 获取默认值
   */
  function getDefaultConfig(
    schema: Record<string, ConfigSchemaProperty>
  ): Record<string, any> {
    const config: Record<string, any> = {}
    for (const [key, prop] of Object.entries(schema)) {
      if (prop.default !== undefined) {
        config[key] = prop.default
      }
    }
    return config
  }

  // ---- 导出 ----
  return {
    // 状态
    nodeDefinitions,
    currentGraph,
    selectedNodeId,
    executingGraphId,
    executionHistory,
    variables,

    // 计算属性
    selectedNode,
    canUndo,
    canRedo,
    nodeDefinitionsByCategory,

    // Actions - 数据获取
    fetchNodeDefinitions,
    fetchGraph,
    saveGraph,

    // Actions - 节点操作
    addNode,
    updateNodeConfig,
    removeNode,
    selectNode,

    // Actions - 边操作
    addEdge,
    removeEdge,

    // Actions - Undo/Redo
    saveToHistory,
    undo,
    redo,

    // Actions - 变量操作
    addVariable,
    removeVariable,
    updateVariable,
    getVariable,

    // 辅助函数
    getDefaultConfig
  }
})
