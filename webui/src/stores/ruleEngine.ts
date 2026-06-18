// -*- coding: utf-8 -*-
/**
 * 规则引擎状态管理 - Pinia Store
 *
 * 提供规则引擎的全局状态管理，作为唯一数据源（Single Source of Truth）。
 * RuleCanvas（画布视图）和 RuleNode（节点组件）均从此读取/写入状态。
 * VueFlow 通过 storeToRefs 绑定的 writable ref 与 store 保持同步。
 */

import { defineStore } from 'pinia'
import { ref, computed, shallowRef, triggerRef, toRaw } from 'vue'
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

  /**
   * 展开的节点 ID 集合 (LOD 2 节点内嵌配置)
   *
   * Phase 17.1+: 取代右侧 NodeConfigEditor 面板.
   * - 双击节点 → 加入此 Set → 该节点 LOD 强制升到 2 (无视 zoom)
   * - 再次双击 / 删除节点 / 点击空白 → 从 Set 移除 → 退回 zoom 决定的 LOD
   * - 多节点可同时展开 (用户编辑 2 个节点时, 对比配置很常见)
   */
  const expandedNodeIds = shallowRef<Set<string>>(new Set())

  /** 变量列表 */
  const variables = ref<Variable[]>([])

  /** 可用模型列表（供 model-select widget 使用） */
  const availableModels = ref<Array<{ id: number; name: string }>>([])

  /** 执行状态 (Phase 17.2 P1-H: shallowRef 避免 logs/nodeStates 深代理)
   *  - logs 高速推送 (YOLO 30FPS) 时, 深 ref 触发整对象深 watcher 链
   *  - 改 shallowRef 后, mutate 字段需手动 triggerRef 通知
   *  - addExecutionLog 走 100ms 批合并, 推送峰值帧耗不抖 */
  const executionState = shallowRef<ExecutionState>({
    status: 'idle',
    progress: 0,
    executionId: null,
    logs: [],
    nodeStates: {}
  })

  /** P1-H: 日志批合并 — 100ms 内多条 log 合成一次 triggerRef */
  let pendingLogs: ExecutionState['logs'] = []
  let logsFlushTimer: ReturnType<typeof setTimeout> | null = null
  const LOGS_BATCH_INTERVAL_MS = 100

  function flushPendingLogs() {
    if (pendingLogs.length === 0) return
    // 浅 ref: 直接 push 到内部数组, 然后 triggerRef
    executionState.value.logs.push(...pendingLogs)
    pendingLogs = []
    logsFlushTimer = null
    triggerRef(executionState)
  }

  /** 当前画布缩放级别 (LOD 决策依据) */
  const viewportZoom = ref(1)
  /** 拖动中标记 (锁定 LOD, 避免切换抖动破坏 v-memo) */
  const isDragging = ref(false)
  /** 框选拖拽中 (同样锁定 LOD) */
  const isSelectionBoxActive = ref(false)
  // ---- Undo/Redo 栈 ----
  // Phase B 任务3: 混合 history (snapshot + move entry), 拖拽松手不再克隆整图
  // - snapshot: 完整克隆, 用于非拖拽操作 (创建/删除/连接/粘贴)
  // - move: 单节点位置变更, 拖拽松手时记录, undo 时只改该节点 position
  const historyStack = ref<Array<
    | { type: 'snapshot'; nodes: GraphNode[]; edges: GraphEdge[] }
    | { type: 'move'; nodeId: string; from: { x: number; y: number }; to: { x: number; y: number } }
    | { type: 'groupMove'; moves: Array<{ nodeId: string; from: { x: number; y: number }; to: { x: number; y: number } }> }
  >>([])
  const historyIndex = ref(-1)
  const isHistoryPaused = ref(false)
  const maxHistorySize = 20

  // ============ 计算属性 ============

  /**
   * 全局已连接 handle 索引 (Phase 17.2 P1-F: 增量维护)
   *
   * 之前 (Phase B 任务2): computed 每次 edges.value 变化全量重建 Set
   * 现在: 手动维护 _connectedHandleIndex Set, addEdge/removeEdge/loadGraph/undo/redo
   *       显式 add/delete, 用 readonly() 暴露避免外部 mutate.
   *
   * key 格式: `${nodeId}:${handleId}:${direction}`, direction = 'source' | 'target'
   */
  const _connectedHandleIndex = new Set<string>()
  const _connectedHandleVersion = shallowRef(0)  // 触发 computed/下游依赖

  /**
   * 把一个 edge 的 source/target handle 加入索引
   */
  function _indexAddEdge(e: { source: string; target: string; sourceHandle?: string | null; targetHandle?: string | null }) {
    if (e.sourceHandle) {
      _connectedHandleIndex.add(`${e.source}:${e.sourceHandle}:source`)
    }
    if (e.targetHandle) {
      _connectedHandleIndex.add(`${e.target}:${e.targetHandle}:target`)
    }
  }

  /**
   * 从索引中移除一个 edge 的 source/target handle
   */
  function _indexRemoveEdge(e: { source: string; target: string; sourceHandle?: string | null; targetHandle?: string | null }) {
    if (e.sourceHandle) {
      _connectedHandleIndex.delete(`${e.source}:${e.sourceHandle}:source`)
    }
    if (e.targetHandle) {
      _connectedHandleIndex.delete(`${e.target}:${e.targetHandle}:target`)
    }
  }

  /**
   * 全量重建索引 (loadGraph / undo snapshot 路径调用)
   */
  function _indexRebuild() {
    _connectedHandleIndex.clear()
    for (const e of edges.value) {
      _indexAddEdge(e)
    }
  }

  /**
   * 暴露的只读 connectedHandleIndex — computed 包装避免外部直接 mutate
   * 但内部 _indexAddEdge/_indexRemoveEdge 仍然能改 _connectedHandleIndex
   */
  const connectedHandleIndex = computed<ReadonlySet<string>>(() => {
    // 依赖 _connectedHandleVersion 触发响应式
    void _connectedHandleVersion.value
    return _connectedHandleIndex
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
  const lodLevelMapCache = new Map<string, 0 | 1>()

  /**
   /**
    * 全局稳定的 LOD 等级 (Phase 19.3+: 单阈值两级)
    * - 升档 LOD 0 → 1: zoom ≥ 0.65
    * - 降档 LOD 1 → 0: zoom < 0.65
    * - 默认 LOD 1 (zoom 1.0 起步)
    * - 死区已删 (Phase 19.3 老大拍板, v-memo + computed 短路缓存已防抖动)
    *
    * 历史: Phase 19 C 曾用 hysteresis 死区 [0.65, 0.80), Phase 19.3 简化为单阈值 0.65.
    */
   const currentGlobalLod = ref<0 | 1>(1)

   /**
    * 基础 LOD 等级 map: 仅依赖 zoom + 节点总数.
    * 选中态 / 折叠态 → CSS-only .expanded 修饰符负责, 不影响 baseLod.
    *
    * 0 = 极简 (120px, 仅标题+图标, 端口隐藏)
    * 1 = 完整 (280px, 标题+端口+内嵌配置 NodeConfigEditor, 默认全展开)
    *   双击节点 -> 折叠到 200px (.expanded 修饰符激活, 配置区 hidden)
    *
    * - 拖动中 / 框选拖拽中 → 锁定当前 LOD (走 lodLevelMapCache)
    * - 折叠态 (CSS .expanded) 独立于 LOD 等级, 不影响 zoom 决策
    *
    * P0-A (Phase 17.1): 短路缓存 — 60Hz 缩放期间 baseLod 跨阈值才重建.
    * P0-C (Phase 17.1+): 内嵌配置 (取代右侧面板).
    * P0-D (Phase 19.3): expandedNodeIds 含义反转 = "已折叠节点".
    */
  /**
   * 桶化 zoom 值用于缓存命中 (Phase 17.3 修复 P0-A 短路 bug)
   *
   * 旧实现: `cachedBaseLodRef.zoom === zoom` — zoom 是连续小数, 几乎永远不 ==
   *        → 60Hz 缩放时永远走全量 Map 重建
   * 新实现: zoom 桶化到 0.1 精度 — 同一桶内复用 Map, 跨桶才重建
   *        实际 LOD 切换只依赖阈值 0.5 / 1.0, 桶化 0.1 已足够精确
   *        (LOD 阈值外的小数变化不会影响 autoLod 结果)
   */
  function bucketZoom(z: number): number {
    return Math.round(z * 10) / 10
  }

  let cachedBaseLodRef: { zoomBucket: number; zoom: number; expandedRef: typeof expandedNodeIds.value; nodesRef: typeof nodes.value; isLodLocked: boolean; globalLod: 0 | 1 } | null = null
  let cachedBaseLodMap: Map<string, 0 | 1> = new Map()
  const baseLodLevelMap = computed<Map<string, 0 | 1>>(() => {
    const zoom = viewportZoom.value
    const isLodLocked = isDragging.value || isSelectionBoxActive.value
    const expandedRef = expandedNodeIds.value
    const nodesRef = nodes.value

    // ===== Phase 19.3: 单阈值两级 LOD, 无死区 =====
    // LOD 0 → 1: zoom ≥ 0.65
    // LOD 1 → 0: zoom < 0.65
    //
    // 历史: Phase 19.2 曾用死区 [0.65, 0.80) 防抖动
    //       老大拍板去掉中间档后, 单阈值更简洁
    // 抖动源已由 v-memo + computed 缓存 (Phase 17.3 P0-A 短路) 解决
    //       无需 hysteresis 死区
    if (!isLodLocked) {
      const cur = currentGlobalLod.value
      let next: 0 | 1 = cur
      if (cur === 0 && zoom >= 0.65) next = 1
      else if (cur === 1 && zoom < 0.65) next = 0
      if (next !== cur) currentGlobalLod.value = next
    }
    const globalLod = currentGlobalLod.value

    // 短路: 输入未变化 (桶化 zoom) → 复用上次 Map
    // 关键: zoomBucket 相等 OR (zoom 在阈值 0.5/1.0 同侧 且 expanded/nodes 未变)
    const zoomBucket = bucketZoom(zoom)
    if (
      cachedBaseLodRef &&
      cachedBaseLodRef.zoomBucket === zoomBucket &&
      cachedBaseLodRef.isLodLocked === isLodLocked &&
      cachedBaseLodRef.nodesRef === nodesRef &&
      cachedBaseLodRef.expandedRef === expandedRef &&
      cachedBaseLodRef.globalLod === globalLod
    ) {
      return cachedBaseLodMap
    }

    // 重建 — 全部节点用 globalLod (除了展开节点强制 LOD 2)
    const map = new Map<string, 0 | 1>()
    for (const n of nodesRef) {
      if (isLodLocked) {
        // 锁定时维持上次 LOD (避免拖动期间样式跳变)
        const cached = lodLevelMapCache.get(n.id) as 0 | 1 | undefined
        map.set(n.id, cached ?? globalLod)
      } else {
        // 两级 LOD: 展开不影响 baseLod (CSS-only .expanded 修饰符负责)
        // 拖动期 isLodLocked 锁在前面已处理
        map.set(n.id, globalLod)
      }
    }

    // 非锁定时刷新缓存 (drag 结束后从这里恢复)
    if (!isLodLocked) {
      lodLevelMapCache.clear()
      for (const [k, v] of map) lodLevelMapCache.set(k, v)
    }
    cachedBaseLodRef = { zoomBucket, zoom, expandedRef, nodesRef, isLodLocked, globalLod }
    cachedBaseLodMap = map
    return map
  })

  /** 保留旧 lodLevelMap 名称作为兼容导出 (RuleNode.vue 等仍可能引用) */
  const lodLevelMap = baseLodLevelMap

  /** O(1) 查询节点 LOD 等级 */
  function getLodLevel(nodeId: string): 0 | 1 {
    return baseLodLevelMap.value.get(nodeId) ?? 1
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
    // P1-F: 全量重建 connectedHandleIndex
    _indexRebuild()
    triggerRef(_connectedHandleVersion)

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
      // 不再 triggerRef(nodes): RuleNode 不再渲染 config 值 (Phase 17.1+),
      // 只有 NodeConfigEditor (节点内嵌 LOD 2) 消费它, 而 Editor 通过 computed
      // 监听 store.nodeById.get(id) 引用, 不需要 triggerRef.
      // 去掉 triggerRef 避免了每次调参时 VueFlow 整图 diff.
    }
  }

  /** 批量更新节点位置 (路径 B: 自研拖动专用)
   * @param rawWrite - true: 用 toRaw 绕过 Vue Proxy, 零 watcher 触发 (dragEnd 专用) */
  function setNodesPositions(
    updates: Array<{ id: string; position: { x: number; y: number } }>,
    recordHistory = true,
    skipTrigger = false,
    rawWrite = false,
  ): void {
    if (updates.length === 0) return
    const updateMap = new Map(updates.map((u) => [u.id, u.position]))

    const moves: Array<{ nodeId: string; from: { x: number; y: number }; to: { x: number; y: number } }> = []
    let anyChange = false
    for (const node of nodes.value) {
      const newPos = updateMap.get(node.id)
      if (newPos) {
        if (rawWrite) {
          // 绕过 Vue Proxy: 直接写 raw object, 零 watcher 调度.
          // 拖动期间 VueFlow 内部 flowNode.position 已实时同步, store 只做持久化.
          const raw = toRaw(node.position)
          const oldX = raw.x
          const oldY = raw.y
          if (oldX !== newPos.x || oldY !== newPos.y) {
            raw.x = newPos.x
            raw.y = newPos.y
            anyChange = true
            if (recordHistory) {
              moves.push({ nodeId: node.id, from: { x: oldX, y: oldY }, to: { ...newPos } })
            }
          }
        } else {
          const fromX = node.position.x
          const fromY = node.position.y
          if (fromX !== newPos.x || fromY !== newPos.y) {
            // 原地变异 .x/.y: 保持 position 对象引用不变, 避免触发 Vue Proxy
            // position setter → 所有依赖 node.position 的 watcher 重新调度.
            // 原地改属性只触发 .x/.y 级别的 setter, 调度量少一个数量级.
            node.position.x = newPos.x
            node.position.y = newPos.y
            anyChange = true
            if (recordHistory) {
              moves.push({ nodeId: node.id, from: { x: fromX, y: fromY }, to: { ...newPos } })
            }
          }
        }
      }
    }
    if (!anyChange) return

    if (recordHistory && !isHistoryPaused.value && moves.length > 0) {
      historyStack.value = historyStack.value.slice(0, historyIndex.value + 1)
      historyStack.value.push({ type: 'groupMove', moves })
      historyIndex.value = historyStack.value.length - 1
      if (historyStack.value.length > maxHistorySize) {
        historyStack.value.shift()
        historyIndex.value--
      }
    }

    // triggerRef 触发 VueFlow 内部 store.nodes watcher 重建 (80 节点 createGraphNodes + 80 边 path 重算),
    // 对 drag-end 路径完全冗余 (拖动期间 flowNode.position 已实时同步到 VueFlow 内部),
    // 且同步 flush 100-200ms 阻塞后续事件循环, 导致二次拖动卡顿.
    // skipTrigger=true 跳过 triggerRef, 仅更新 store.nodes / history.
    if (!skipTrigger) {
      triggerRef(nodes)
    }
  }

  /**
   * 删除节点并清理关联边 / 选中状态 / 历史记录。
   */
  function removeNode(nodeId: string) {
    nodes.value = nodes.value.filter(n => n.id !== nodeId)
    edges.value = edges.value.filter(e => e.source !== nodeId && e.target !== nodeId)
    // 同步清理展开状态
    if (expandedNodeIds.value.has(nodeId)) {
      expandedNodeIds.value.delete(nodeId)
      triggerRef(expandedNodeIds)
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
    // P1-F: 先收集要删的 incident edges, 用于增量维护
    const removedEdges = edges.value.filter(e => idSet.has(e.source) || idSet.has(e.target))
    edges.value = edges.value.filter(e => !idSet.has(e.source) && !idSet.has(e.target))
    for (const e of removedEdges) _indexRemoveEdge(e)
    triggerRef(_connectedHandleVersion)
    // 同步清理展开状态
    if (expandedNodeIds.value.size > 0) {
      let changed = false
      for (const id of idSet) {
        if (expandedNodeIds.value.has(id)) {
          expandedNodeIds.value.delete(id)
          changed = true
        }
      }
      if (changed) triggerRef(expandedNodeIds)
    }
    saveHistory()
  }

  /**
   * 切换节点折叠状态 (Phase 19.3+: 语义反转)
   * - expandedNodeIds 集合名字保留, 但含义改为"已折叠节点" (双击加入 = 折叠)
   * - 默认 LOD 1 节点 280px 全展开 (端口+配置+标题)
   * - 双击节点 -> 加入 expandedNodeIds -> .expanded 修饰符激活 -> 折叠到 200px (隐藏配置)
   * - 再次双击 -> 移除 -> 回到全展开
   *
   * 历史: Phase 17.1~19.2 是 "未展开"→"展开" 语义, Phase 19.3 老大拍板反转默认.
   */
  function toggleNodeExpanded(nodeId: string) {
    if (expandedNodeIds.value.has(nodeId)) {
      expandedNodeIds.value.delete(nodeId)
    } else {
      expandedNodeIds.value.add(nodeId)
    }
    triggerRef(expandedNodeIds)
  }

  /**
   * 折叠状态清理 (Phase 19.3+: 语义反转)
   * - 旧语义: clear expandedNodeIds -> 所有节点回折叠 (Phase 19.2)
   * - 新语义: clear expandedNodeIds -> 所有节点回全展开 (Phase 19.3+, 默认 280px)
   * 适用场景: 画布空白点击 / 切换图 / "全展开" 工具按钮 (一键回到默认全展开)
   */
  function collapseAllExpanded() {
    if (expandedNodeIds.value.size > 0) {
      expandedNodeIds.value.clear()
      triggerRef(expandedNodeIds)
    }
  }

  /**
   * 同步展开状态 (Phase 19.7+: 修复外部 triggerRef(store.expandedNodeIds) 类型错)
   * - 原因: Pinia setup store 暴露 expandedNodeIds 是 Set<string> (已 unwrap)
   *        外部拿不到原 shallowRef, 无法直接 triggerRef
   * - 调用场景: nodes 删除时清理已折叠集合里的悬空 id, 再 triggerRef 通知
   * - 行为: 在外部 mutate Set 之后调用, 强制组件 watch 重新计算
   */
  function syncExpandedNodeIds() {
    triggerRef(expandedNodeIds)
  }

  /**
   * 折叠全部 (Phase 19.4+ 显示模式按钮)
   * - 全部节点加进 expandedNodeIds (反语义: 表示"已折叠")
   * - 配 setDisplayMode 用: 一次 set 全图折叠
   * 性能: shallowRef Set 一次性 add 所有 + 一次 triggerRef
   */
  function expandAll() {
    const allIds: string[] = []
    for (const n of nodes.value) allIds.push(n.id)
    if (allIds.length === 0) return
    const next = new Set(allIds)
    expandedNodeIds.value = next
  }

  // ============ 边操作 ============

  /** 添加边 */
  function addEdge(connection: {
    source: string; target: string
    sourceHandle?: string | null; targetHandle?: string | null
  }) {
    // shallowRef 需重新赋值触发响应式（与 createNode 同问题）
    const newEdge = {
      id: `edge_${Date.now()}`,
      source: connection.source,
      target: connection.target,
      sourceHandle: connection.sourceHandle ?? undefined,
      targetHandle: connection.targetHandle ?? undefined,
      type: 'default',
      animated: false
    }
    edges.value = [...edges.value, newEdge]
    // P1-F: 增量维护 connectedHandleIndex
    _indexAddEdge(newEdge)
    triggerRef(_connectedHandleVersion)
    saveHistory()
  }

  /** 删除边 */
  function removeEdge(edgeId: string) {
    const target = edges.value.find(e => e.id === edgeId)
    edges.value = edges.value.filter(e => e.id !== edgeId)
    // P1-F: 增量维护 connectedHandleIndex
    if (target) _indexRemoveEdge(target)
    triggerRef(_connectedHandleVersion)
    saveHistory()
  }

  /**
   * 批量删除边 (Phase B 任务4)
   */
  function removeEdges(edgeIds: string[]) {
    if (edgeIds.length === 0) return
    const idSet = new Set(edgeIds)
    // P1-F: 先收集要删的边, 用于增量维护
    const removed = edges.value.filter(e => idSet.has(e.id))
    edges.value = edges.value.filter(e => !idSet.has(e.id))
    for (const e of removed) _indexRemoveEdge(e)
    triggerRef(_connectedHandleVersion)
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
   * 应用一个 history entry
   * - snapshot: 还原整图
   * - move: 只改单节点 position
   * - groupMove: 批量改多节点 position (setNodesPositions 写入, GROUP 拖动 1 entry)
   *
   * undo/redo 复用 applyHistoryEntry: 通过 moveIndex 指针区分"还原方向"——
   *   entry.from = 还原目标 (undo 时) / entry.to = 还原目标 (redo 时)
   *   简化方案: 调用方传 toCurrent 标志, 这里根据 historyIndex 与 entry 在 stack 中位置
   *   关系判断方向.
   *
   *   实际实现: setNodesPositions 写 history 时是 "from -> to" (拖动结果),
   *   undo 时希望回到 from (恢复原位置), redo 时希望到 to.
   *   通过 setNodesPositions 反向传 updates 即可, 见 undo/redo 函数.
   */
  function applyHistoryEntry(entry: typeof historyStack.value[number]) {
    if (entry.type === 'snapshot') {
      nodes.value = JSON.parse(JSON.stringify(entry.nodes))
      edges.value = JSON.parse(JSON.stringify(entry.edges))
      // P1-F: 整体替换 edges 后全量重建索引
      _indexRebuild()
      triggerRef(_connectedHandleVersion)
    } else if (entry.type === 'move') {
      // 单节点位置变更, 直接 mutate + triggerRef 避免整图重渲染
      const node = nodes.value.find(n => n.id === entry.nodeId)
      if (node) {
        node.position = { ...entry.from }  // undo 回到 from; redo 调到 to
        triggerRef(nodes)
      }
    } else {
      // groupMove: 批量还原
      // 调用 setNodesPositions 把所有节点归位 (recordHistory=false 避免污染 history stack)
      const updates = entry.moves.map(m => ({ id: m.nodeId, position: { ...m.from } }))
      setNodesPositions(updates, false)
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
    // shallowRef: mutate 字段后手动 triggerRef
    executionState.value.status = status
    triggerRef(executionState)
  }

  function addExecutionLog(log: ExecutionState['logs'][0]) {
    // P1-H: 100ms 批合并 — YOLO 30FPS 推流时, 一次推送可能 N 条 log
    pendingLogs.push(log)
    if (logsFlushTimer === null) {
      logsFlushTimer = setTimeout(flushPendingLogs, LOGS_BATCH_INTERVAL_MS)
    }
  }

  function setExecutionProgress(progress: number) {
    // shallowRef: mutate 字段后手动 triggerRef
    executionState.value.progress = progress
    triggerRef(executionState)
  }

  function setNodeExecutionState(nodeId: string, state: string) {
    // shallowRef: mutate 字段后手动 triggerRef
    executionState.value.nodeStates[nodeId] = state
    triggerRef(executionState)
  }

  function clearExecution() {
    // 清理时先 flush 待推送日志, 避免状态错乱
    if (logsFlushTimer !== null) {
      clearTimeout(logsFlushTimer)
      logsFlushTimer = null
    }
    pendingLogs = []
    executionState.value = {
      status: 'idle',
      progress: 0,
      executionId: null,
      logs: [],
      nodeStates: {}
    }
    triggerRef(executionState)
  }

  function setExecutionId(id: number) {
    // shallowRef: mutate 字段后手动 triggerRef
    executionState.value.executionId = id
    triggerRef(executionState)
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
   * RuleCanvas 监听 @viewport-change 时调用, 供 lodLevelMap 计算用.
   *
   * Phase 17.3: 加自节流 — 同一帧内多次 setViewportZoom 合并为 1 次 ref.set
   * 60Hz 缩放下每帧只触发 1 次响应式 (而不是理论上 60 次).
   * rAF 之外基本无 zoom 事件, 节流主要保护 d3-zoom 内部抖动场景.
   */
  let setViewportZoomRafId = 0
  let pendingZoomValue = 1
  function setViewportZoom(z: number) {
    pendingZoomValue = z
    if (setViewportZoomRafId) return
    setViewportZoomRafId = requestAnimationFrame(() => {
      setViewportZoomRafId = 0
      viewportZoom.value = pendingZoomValue
    })
  }

  /** 拖动期间锁定 LOD (useCogniFlowDrag onStart 调用) */
  function setDragging(v: boolean) {
    isDragging.value = v
  }

  /** 框选拖拽期间锁定 LOD (handleSelectionDragStart 调用) */
  function setSelectionBoxActive(v: boolean) {
    isSelectionBoxActive.value = v
  }

  // ============ 导出 ============
  return {
    // 状态
    nodeDefinitions,
    graphMeta,
    nodes,
    edges,
    expandedNodeIds,    // LOD 2 展开集合 (Phase 17.1+: 取代右侧面板)
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

    // 计算属性
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
    toggleNodeExpanded, // Phase 17.1+: 双击节点展开 LOD 2
    collapseAllExpanded,// Phase 17.1+: 点空白收起所有展开
    syncExpandedNodeIds,// Phase 19.7+: 外部 Set mutate 后通知响应式
    expandAll,          // Phase 19.4+: 工具栏"全部折叠"按钮
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
    setSelectionBoxActive
  }
})
