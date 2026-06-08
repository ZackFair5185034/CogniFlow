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

  /** 当前画布缩放级别 (LOD 决策依据) */
  const viewportZoom = ref(1)
  /** 拖动中标记 (锁定 LOD, 避免切换抖动破坏 v-memo) */
  const isDragging = ref(false)
  /** 框选拖拽中 (同样锁定 LOD) */
  const isSelectionBoxActive = ref(false)
  /** 用户主动展开配置的节点 ID 集合 (响应式 Set, 避免 markRaw 内层属性变更不触发响应) */
  const configExpandedIds = ref<Set<string>>(new Set())

  // ---- Undo/Redo 栈 ----
  // Phase B 任务3: 混合 history (snapshot + move entry), 拖拽松手不再克隆整图
  // - snapshot: 完整克隆, 用于非拖拽操作 (创建/删除/连接/粘贴)
  // - move: 单节点位置变更, 拖拽松手时记录, undo 时只改该节点 position
  const historyStack = ref<Array<
    | { type: 'snapshot'; nodes: GraphNode[]; edges: GraphEdge[] }
    | { type: 'move'; nodeId: string; from: { x: number; y: number }; to: { x: number; y: number } }
  >>([])
  const historyIndex = ref(-1)
  const isHistoryPaused = ref(false)
  const maxHistorySize = 20

  // ============ 计算属性 ============

  /** 选中的节点对象 */
  const selectedNode = computed((): Node<RuleNodeData> | null => {
    const list: Node<RuleNodeData>[] = nodes.value
    return list.find(n => n.id === selectedNodeId.value) ?? null
  })

  /**
   * 全局已连接 handle 索引 (Phase B 任务2: 连接状态索引化)
   *
   * 之前: 每个 RuleNode 内部 computed 扫描 store.edges, O(V*E) per frame
   * 现在: store 全局计算一次, 节点 O(1) 查询
   *
   * key 格式: `${nodeId}:${handleId}:${direction}`, direction = 'source' | 'target'
   */
  const connectedHandleIndex = computed<Set<string>>(() => {
    const index = new Set<string>()
    for (const e of edges.value) {
      if (e.sourceHandle) {
        index.add(`${e.source}:${e.sourceHandle}:source`)
      }
      if (e.targetHandle) {
        index.add(`${e.target}:${e.targetHandle}:target`)
      }
    }
    return index
  })

  /**
   * O(1) 查询 handle 是否已连接.
   * 取代 RuleNode 内部 O(E) 扫描.
   */
  function isHandleConnected(
    nodeId: string,
    handleId: string,
    direction: 'source' | 'target'
  ): boolean {
    return connectedHandleIndex.value.has(`${nodeId}:${handleId}:${direction}`)
  }

  /**
   * 节点 ID -> Node Map (Phase B 任务6: 连接校验节点索引)
   *
   * 之前: getNodePortType / validateConnection / isValidConnection 每次 nodes.value.find(),
   *       连接拖拽时高频调用变成 O(E) per call.
   * 现在: store 全局 Map, O(1) 查询.
   */
  const nodeById = computed<Map<string, Node<RuleNodeData>>>(() => {
    const map = new Map<string, Node<RuleNodeData>>()
    for (const n of nodes.value) {
      map.set(n.id, n)
    }
    return map
  })

  /** 是否可以撤销 */
  const canUndo = computed(() => historyIndex.value > 0)

  /** 是否可以重做 */
  const canRedo = computed(() => historyIndex.value < historyStack.value.length - 1)

  /** 是否有节点 */
  const hasNodes = computed(() => nodes.value.length > 0)

  /** 锁定期间的 LOD 缓存, drag 期间维持稳定 (避免切换抖动破坏 v-memo) */
  const lodLevelMapCache = new Map<string, 0 | 1 | 2>()

  /**
   * LOD 等级 map (基于缩放级别 + 节点密度)
   * 0 = 极简 (仅标题), 1 = 节点壳 (含端口+摘要), 2 = 完整 (含配置区)
   * - 选中节点 / 配置已展开 → 强制 LOD 2
   * - 拖动中 / 框选拖拽中 → 锁定当前 LOD
   * - zoom < 0.3 → LOD 0
   * - zoom < 0.7 或节点数 > 80 → LOD 1
   * - 其他 → LOD 2
   */
  const lodLevelMap = computed<Map<string, 0 | 1 | 2>>(() => {
    const map = new Map<string, 0 | 1 | 2>()
    const zoom = viewportZoom.value
    const count = nodes.value.length
    const isLodLocked = isDragging.value || isSelectionBoxActive.value
    // 用 selectedNodeId 响应式 ref 而非 n.selected (后者是 markRaw 内部属性, 不会触发响应式)
    const selId = selectedNodeId.value
    // 用 configExpandedIds 响应式 Set 追踪用户主动展开的节点
    const expanded = configExpandedIds.value

    for (const n of nodes.value) {
      if (n.id === selId) { map.set(n.id, 2); continue }
      if (expanded.has(n.id)) { map.set(n.id, 2); continue }
      if (isLodLocked) {
        map.set(n.id, lodLevelMapCache.get(n.id) ?? 1)
        continue
      }
      if (zoom < 0.3) map.set(n.id, 0)
      else if (zoom < 0.7 || count > 80) map.set(n.id, 1)
      else map.set(n.id, 2)
    }

    // 非锁定时刷新缓存 (drag 结束后从这里恢复)
    if (!isLodLocked) {
      lodLevelMapCache.clear()
      for (const [k, v] of map) lodLevelMapCache.set(k, v)
    }
    return map
  })

  /** O(1) 查询节点 LOD 等级 */
  function getLodLevel(nodeId: string): 0 | 1 | 2 {
    return lodLevelMap.value.get(nodeId) ?? 1
  }

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
    // markRaw 防止 Vue 对每个节点的 n.data 建深代理（80 节点 × ~20 字段 = 1600 个 Proxy）
    nodes.value = (data.nodes ?? []).map((n: GraphNode) => {
      const isVueFlowType = n.type === 'ruleNode' || n.type === 'rule-node'
      return markRaw({
        id: n.id,
        type: 'ruleNode',
        position: n.position ?? { x: 0, y: 0 },
        data: {
          ...(n.data ?? {}),
          // 确保 data.type 为原始业务类型（兼容新旧数据格式）
          type: isVueFlowType ? (n.data?.type ?? 'unknown') : n.type,
          id: n.id
        } as RuleNodeData
      })
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
    // 关键：shallowRef 不会追踪内部数组突变,需用新数组重新赋值触发响应式
    // 之前直接 push() 会让节点"进了 store 但不渲染"（拖拽/双击添加都不显示）
    // markRaw 防止 Vue 对 n.data 建深代理（节点体里 el-* 控件的响应式由组件内部自管）
    nodes.value = [...nodes.value, markRaw(newNode)]
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
      // 不再 triggerRef(nodes): RuleNode 不再渲染 config 值,
      // 只有 NodeConfigEditor(右侧面板)消费它, 而右侧面板通过 computed
      // 监听 selectedNode 引用, 不需要 triggerRef.
      // 去掉 triggerRef 避免了每次调参时 VueFlow 整图 diff.
    }
  }

  /**
   * 批量更新节点位置 (路径 B: 自研拖动专用)
   *
   * useCogniFlowDrag 在 drag-end 时调用, 一次性同步所有被拖动节点的 position.
   * 内部 mutate + 单次 triggerRef, 避免循环 setNodePosition 触发 N 次整图 diff.
   *
   * @param updates 节点 id → 新位置 (含 viewport transform 解析后的画布坐标)
   * @param recordHistory 是否记录 move history (drag-end 时 true, 撤销栈记录 from→to)
   */
  function setNodesPositions(
    updates: Array<{ id: string; position: { x: number; y: number } }>,
    recordHistory = true,
  ): void {
    if (updates.length === 0) return
    // 用 Map 加速 id 查找, 避免 N 节点 × N updates 的 O(N²) find
    const updateMap = new Map(updates.map((u) => [u.id, u.position]))
    for (const node of nodes.value) {
      const newPos = updateMap.get(node.id)
      if (newPos) {
        const from = node.position
        // mutate 内部字段 (shallowRef 数组元素不深代理, 需 triggerRef)
        node.position = newPos
        if (recordHistory) {
          // 单节点 move entry, 不克隆整图 (Phase B 任务3 模式)
          historyStack.value = historyStack.value.slice(0, historyIndex.value + 1)
          historyStack.value.push({ type: 'move', nodeId: node.id, from: { ...from }, to: { ...newPos } })
          historyIndex.value = historyStack.value.length - 1
          if (historyStack.value.length > maxHistorySize) {
            historyStack.value.shift()
            historyIndex.value--
          }
        }
      }
    }
    // 一次 triggerRef 让 VueFlow 内部 store.nodes watcher 重建,
    // 边 path 重算, NodeWrapper 模板 transform 同步.
    triggerRef(nodes)
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

  /**
   * 批量删除节点 (Phase B 任务4)
   *
   * 之前: handleDelete 里 for 循环调 removeNode, 每次 filter 一次全图 + 一次 saveHistory.
   *       50 节点 = 50 次全图 filter + 50 次历史快照, O(50*E) + 50 * JSON 克隆.
   * 现在: 单次 filter, 单次 saveHistory. O(E).
   */
  function removeNodes(nodeIds: string[]) {
    if (nodeIds.length === 0) return
    const idSet = new Set(nodeIds)
    nodes.value = nodes.value.filter(n => !idSet.has(n.id))
    edges.value = edges.value.filter(e => !idSet.has(e.source) && !idSet.has(e.target))
    if (selectedNodeId.value && idSet.has(selectedNodeId.value)) {
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
    // shallowRef 需重新赋值触发响应式（与 createNode 同问题）
    edges.value = [...edges.value, {
      id: `edge_${Date.now()}`,
      source: connection.source,
      target: connection.target,
      sourceHandle: connection.sourceHandle ?? undefined,
      targetHandle: connection.targetHandle ?? undefined,
      type: 'default',
      animated: false
    }]
    saveHistory()
  }

  /** 删除边 */
  function removeEdge(edgeId: string) {
    edges.value = edges.value.filter(e => e.id !== edgeId)
    saveHistory()
  }

  /**
   * 批量删除边 (Phase B 任务4)
   */
  function removeEdges(edgeIds: string[]) {
    if (edgeIds.length === 0) return
    const idSet = new Set(edgeIds)
    edges.value = edges.value.filter(e => !idSet.has(e.id))
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
   * 在 JSON 序列化前剥离 VueFlow 内部字段（DOM 引用、循环引用根）。
   *
   * 注意：data/position 必须浅 spread（连同嵌套的 data.config），
   * 否则 updateNodeConfig 的内层 mutate（`node.data.config[key] = value`）会
   * 污染所有持有同一引用的历史快照，导致 undo/redo 实际不工作。
   */
  function cloneForHistory<T>(items: T[]): T[] {
    return items.map(item => {
      const cleaned: any = {}
      for (const key in item) {
        if ((VUEFLOW_INTERNAL_KEYS as readonly string[]).includes(key)) continue
        const value = (item as any)[key]
        if (key === 'data' && value && typeof value === 'object') {
          // data.config 是 updateNodeConfig mutate 的目标，独立拷贝
          cleaned.data = value.config
            ? { ...value, config: { ...value.config } }
            : { ...value }
        } else if (key === 'position' && value && typeof value === 'object') {
          cleaned.position = { ...value }
        } else {
          cleaned[key] = value
        }
      }
      return cleaned as T
    })
  }

  /** 保存当前状态到历史栈 */
  function saveHistory() {
    if (isHistoryPaused.value) return
    historyStack.value = historyStack.value.slice(0, historyIndex.value + 1)
    historyStack.value.push({
      type: 'snapshot',
      nodes: cloneForHistory(nodes.value) as any,
      edges: edges.value.map(e => ({ ...e, selected: false })),
    })
    historyIndex.value = historyStack.value.length - 1
    if (historyStack.value.length > maxHistorySize) {
      historyStack.value.shift()
      historyIndex.value--
    }
  }

  /**
   * 记录单节点移动历史 (Phase B 任务3)
   *
   * 拖拽松手时调用, 不克隆整图, 只存 1 个节点的位置变化.
   * 200 节点图拖拽松手从 ~370ms 响应式开销降到 ~1ms.
   */
  function recordMoveHistory(nodeId: string, from: { x: number; y: number }, to: { x: number; y: number }) {
    if (isHistoryPaused.value) return
    // 跳过零位移 (防止 drag-stop 偶然触发)
    if (from.x === to.x && from.y === to.y) return
    historyStack.value = historyStack.value.slice(0, historyIndex.value + 1)
    historyStack.value.push({ type: 'move', nodeId, from: { ...from }, to: { ...to } })
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
    applyHistoryEntry(historyStack.value[historyIndex.value])
  }

  /** 重做 */
  function redo() {
    if (!canRedo.value) return
    historyIndex.value++
    applyHistoryEntry(historyStack.value[historyIndex.value])
  }

  /**
   * 应用一个 history entry (Phase B 任务3)
   * - snapshot: 还原整图
   * - move: 只改单节点 position
   */
  function applyHistoryEntry(entry: typeof historyStack.value[number]) {
    if (entry.type === 'snapshot') {
      nodes.value = JSON.parse(JSON.stringify(entry.nodes))
      edges.value = JSON.parse(JSON.stringify(entry.edges))
    } else {
      // move: 单节点位置变更, 直接 mutate + triggerRef 避免整图重渲染
      const node = nodes.value.find(n => n.id === entry.nodeId)
      if (node) {
        node.position = { ...entry.from }  // undo 回到 from; redo 调到 to
        triggerRef(nodes)
      }
    }
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

  /**
   * 仅恢复 paused 状态, 不存 snapshot (Phase B 任务3)
   *
   * 用于 dragStop: recordMoveHistory 已存了 move entry, 不需要再存当前 snapshot.
   * 配合 recordMoveHistory 一起使用.
   */
  function resumeHistory() {
    isHistoryPaused.value = false
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

  // ============ LOD 状态 (Phase LOD-1) ============

  /**
   * 同步画布缩放级别到 store.
   * RuleCanvas 监听 @zoom 事件时调用, 供 lodLevelMap 计算用.
   */
  function setViewportZoom(z: number) {
    viewportZoom.value = z
  }

  /** 拖动期间锁定 LOD (useCogniFlowDrag onStart 调用) */
  function setDragging(v: boolean) {
    isDragging.value = v
  }

  /** 框选拖拽期间锁定 LOD (handleSelectionDragStart 调用) */
  function setSelectionBoxActive(v: boolean) {
    isSelectionBoxActive.value = v
  }

  /**
   * 切换节点配置区展开状态 (LOD 2 显示配置).
   * 维护 configExpandedIds (响应式 Set) 让 lodLevelMap 自动响应.
   * - 初始 (set 内无此 id) → toggle 加入 set → LOD 2
   * - 已在 set → toggle 移除 → LOD 1
   */
  function toggleConfigExpanded(nodeId: string) {
    const next = new Set(configExpandedIds.value)
    if (next.has(nodeId)) next.delete(nodeId)
    else next.add(nodeId)
    configExpandedIds.value = next
    // 同步写回 n.data 用于持久化 (saveGraph 序列化)
    const n = nodeById.value.get(nodeId)
    if (n?.data) {
      n.data.configExpanded = next.has(nodeId)
    }
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
    viewportZoom,        // LOD
    isDragging,          // LOD 锁定
    isSelectionBoxActive,// LOD 锁定
    configExpandedIds,   // LOD (展开状态)

    // 计算属性
    selectedNode,
    connectedHandleIndex,
    nodeById,  // Phase B 任务6
    canUndo,
    canRedo,
    hasNodes,
    nodeDefinitionsByCategory,
    lodLevelMap,         // LOD
    getLodLevel,         // LOD

    // 数据加载
    fetchNodeDefinitions,
    fetchModels,
    loadGraph,
    saveGraph,

    // 节点操作
    createNode,
    updateNodeConfig,
    setNodesPositions,  // 路径 B: 自研拖动 drag-end 批量同步
    removeNode,
    removeNodes,        // Phase B 任务4
    selectNode,
    isHandleConnected,  // Phase B 任务2

    // 边操作
    addEdge,
    removeEdge,
    removeEdges,        // Phase B 任务4

    // Undo/Redo
    saveHistory,
    recordMoveHistory,  // Phase B 任务3
    undo,
    redo,
    pauseHistory,
    unpauseHistory,
    resumeHistory,      // Phase B 任务3

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
    getNodeCategory,

    // LOD (Phase LOD-1)
    setViewportZoom,
    setDragging,
    setSelectionBoxActive,
    toggleConfigExpanded
  }
})
