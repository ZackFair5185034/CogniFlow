// -*- coding: utf-8 -*-
/**
 * 规则引擎图状态 (P1-A 拆分)
 *
 * 独立子 store — 管理画布与图相关的所有 state:
 *   - 节点定义 (nodeDefinitions, availableModels)
 *   - 图元数据 (graphMeta)
 *   - 节点/边 (nodes, edges) + 选中/连接索引 (connectedHandleIndex, nodeById)
 *   - 展开状态 (expandedNodeIds)
 *   - 禁用状态 (disabledNodeIds)
 *   - 画布交互 (viewportZoom, isDragging, isSelectionBoxActive)
 *   - LOD (currentGlobalLod, baseLodLevelMap)
 *   - 历史栈 (historyStack, historyIndex, isHistoryPaused, lastSavedHistoryIndex)
 *
 * 跨子 store 写入:
 *   - loadGraph / importFromJSON 解析 variables_json 后写入 variables store
 *   - saveGraph 读 variables store 写回 backend
 *   - duplicateAsNewGraph 同上
 */

import { defineStore } from 'pinia'
import { ref, computed, shallowRef, triggerRef, markRaw, toRaw } from 'vue'
import { ruleEngineApi, modelApi } from '@/api'
import type {
  NodeDefinition as NodeDefinitionBase,
  GraphNode as GraphNodeBase,
  GraphEdge as GraphEdgeBase,
  RuleNodeData,
  VariableType,
  VariableDefaultValue
} from '@/types/api'
import type { Node, Edge } from '@vue-flow/core'
import { MarkerType } from '@vue-flow/core'
import { getDefaultConfig, cloneForHistory } from './_helpers'
import { useRuleVariablesStore } from './variables'
import type { Variable } from './variables'

// ============ 类型别名（兼容旧代码）============

export type NodeDefinition = NodeDefinitionBase
export type GraphNode = GraphNodeBase
export type GraphEdge = GraphEdgeBase

/** 规则图元数据 */
export interface GraphMeta {
  id: number
  name: string
  description?: string
  is_active: boolean
  version?: string
  thumbnail?: string
}

/**
 * 对齐模式 (P1-2 2026-06-19)
 * - 'left' / 'right' / 'top' / 'bottom': 对齐到边界
 * - 'h-center' / 'v-center': 居中
 * - 'distribute-h' / 'distribute-v': 等距分布 (至少 3 个节点)
 */
export type AlignMode =
  | 'left' | 'right' | 'top' | 'bottom'
  | 'h-center' | 'v-center'
  | 'distribute-h' | 'distribute-v'

export const useRuleGraphStore = defineStore('ruleGraph', () => {
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
   *
   * Phase 19.3+: 语义反转 = "已折叠节点"
   */
  const expandedNodeIds = shallowRef<Set<string>>(new Set())

  /** 可用模型列表（供 model-select widget 使用） */
  const availableModels = ref<Array<{ id: number; name: string }>>([])

  // ---- Undo/Redo 栈 ----
  // Phase B 任务3: 混合 history (snapshot + move entry), 拖拽松手不再克隆整图
  // - snapshot: 完整克隆, 用于非拖拽操作 (创建/删除/连接/粘贴)
  // - move: 单节点位置变更, 拖拽松手时记录, undo 时只改该节点 position
  const historyStack = ref<Array<
    | { type: 'snapshot'; nodes: GraphNode[]; edges: GraphEdge[] }
    | { type: 'move'; nodeId: string; from: { x: number; y: number }; to: { x: number; y: number } }
    | { type: 'groupMove'; moves: Array<{ nodeId: string; from: { x: number; y: number }; to: { x: number; y: number } }> }
    | { type: 'addEdge'; edge: GraphEdge }
    | { type: 'removeEdge'; edge: GraphEdge }
    | { type: 'removeEdges'; edges: GraphEdge[] }
  >>([])
  const historyIndex = ref(-1)
  const isHistoryPaused = ref(false)
  const maxHistorySize = 20

  // P0-2 (2026-06-19): 最近一次成功保存对应的 history 索引.
  //   dirty = (historyIndex !== lastSavedHistoryIndex), 配合 beforeunload 提示 + 草稿自动保存.
  //   比"对比 nodes JSON 字符串"更便宜 — history 索引变化即可, 不必序列化.
  const lastSavedHistoryIndex = ref(-1)

  // ============ 画布交互状态 ============

  /** 当前画布缩放级别 (LOD 决策依据) */
  const viewportZoom = ref(1)
  /** 拖动中标记 (锁定 LOD, 避免切换抖动破坏 v-memo) */
  const isDragging = ref(false)
  /** 框选拖拽中 (同样锁定 LOD) */
  const isSelectionBoxActive = ref(false)

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

  /** PERF-8 (2026-06-19): 维护"已索引的 edge id"辅助 Set, 供 _indexRebuild diff 使用 */
  const _indexedEdgeIds = new Set<string>()

  // FIX (BUG-4 2026-06-19): 节点配置变更的响应式信号
  // 之前 updateNodeConfig 不 trigger, NodeConfigEditor (LOD 2 内嵌) 的 computed 链断裂.
  // 现在用独立 configVersion shallowRef, 精确触发 Editor, 不影响 VueFlow 整图 diff.
  const _configVersion = shallowRef(0)

  function _indexAddEdge(e: { id: string; source: string; target: string; sourceHandle?: string | null; targetHandle?: string | null }) {
    if (e.sourceHandle) {
      _connectedHandleIndex.add(`${e.source}:${e.sourceHandle}:source`)
    }
    if (e.targetHandle) {
      _connectedHandleIndex.add(`${e.target}:${e.targetHandle}:target`)
    }
    _indexedEdgeIds.add(e.id)
  }

  function _indexRemoveEdge(e: { id: string; source: string; target: string; sourceHandle?: string | null; targetHandle?: string | null }) {
    if (e.sourceHandle) {
      _connectedHandleIndex.delete(`${e.source}:${e.sourceHandle}:source`)
    }
    if (e.targetHandle) {
      _connectedHandleIndex.delete(`${e.target}:${e.targetHandle}:target`)
    }
    _indexedEdgeIds.delete(e.id)
  }

  /**
   * 全量重建索引 (loadGraph / undo snapshot 路径调用)
   * PERF-8 (2026-06-19): diff 模式 — 只 add/remove 变更的边, 不再 O(2E) clear + 重建
   */
  function _indexRebuild() {
    const oldIds = _indexedEdgeIds
    const newIds = new Set<string>()
    for (const e of edges.value) newIds.add(e.id)

    // 1) 移除被删的边
    for (const oldId of oldIds) {
      if (!newIds.has(oldId)) {
        const oldEdge = edges.value.find((e) => e.id === oldId)
        if (oldEdge) _indexRemoveEdge(oldEdge)
      }
    }
    // 2) 加入新增的边
    for (const e of edges.value) {
      if (!oldIds.has(e.id)) {
        _indexAddEdge(e)
      }
    }
  }

  /** 暴露的只读 connectedHandleIndex — computed 包装避免外部直接 mutate */
  const connectedHandleIndex = computed<ReadonlySet<string>>(() => {
    void _connectedHandleVersion.value
    return _connectedHandleIndex
  })

  /** O(1) 查询 handle 是否已连接. 取代 RuleNode 内部 O(E) 扫描. */
  function isHandleConnected(
    nodeId: string,
    handleId: string,
    direction: 'source' | 'target'
  ): boolean {
    return connectedHandleIndex.value.has(`${nodeId}:${handleId}:${direction}`)
  }

  /**
   * 节点 ID → node O(1) 查找 (computed)
   * 2026-06-21 修复: 去掉 lazy dirty 优化
   *   原实现用 _nodeByIdDirty flag, false 时直接 return 缓存 Map, 不访问 nodes.value,
   *   导致 Vue computed 依赖追踪断裂 — createNode 改 nodes.value 后 computed 不重算.
   */
  function _nodeByIdMarkDirty() { /* 空函数保留避免改动调用点 */ }
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

  /** P0-2 (2026-06-19): 当前是否有未保存改动 */
  const isDirty = computed(() => historyIndex.value !== lastSavedHistoryIndex.value)

  /** 是否有节点 */
  const hasNodes = computed(() => nodes.value.length > 0)

  /** 锁定期间的 LOD 缓存, drag 期间维持稳定 (避免切换抖动破坏 v-memo) */
  const lodLevelMapCache = new Map<string, 0 | 1>()

  /** 全局稳定的 LOD 等级 (Phase 19.3+: 单阈值两级) */
  const currentGlobalLod = ref<0 | 1>(1)

  /**
   * 桶化 zoom 值用于缓存命中 (Phase 17.3 修复 P0-A 短路 bug)
   * 旧实现 zoom 是连续小数几乎永远不 ==, 桶化到 0.1 精度后同桶复用.
   */
  function bucketZoom(z: number): number {
    return Math.round(z * 10) / 10
  }

  // PERF-2 修复 (2026-06-19): 缓存 key 改用 length + firstId + lastId 代替引用相等
  let cachedBaseLodRef: {
    zoomBucket: number
    zoom: number
    expandedRef: typeof expandedNodeIds.value
    nodesLength: number
    firstId: string | undefined
    lastId: string | undefined
    isLodLocked: boolean
    globalLod: 0 | 1
  } | null = null
  let cachedBaseLodMap: Map<string, 0 | 1> = new Map()
  const baseLodLevelMap = computed<Map<string, 0 | 1>>(() => {
    const zoom = viewportZoom.value
    const isLodLocked = isDragging.value || isSelectionBoxActive.value
    const expandedRef = expandedNodeIds.value
    const nodesRef = nodes.value

    if (!isLodLocked) {
      const cur = currentGlobalLod.value
      let next: 0 | 1 = cur
      if (cur === 0 && zoom >= 0.65) next = 1
      else if (cur === 1 && zoom < 0.65) next = 0
      if (next !== cur) currentGlobalLod.value = next
    }
    const globalLod = currentGlobalLod.value

    const zoomBucket = bucketZoom(zoom)
    if (
      cachedBaseLodRef &&
      cachedBaseLodRef.zoomBucket === zoomBucket &&
      cachedBaseLodRef.isLodLocked === isLodLocked &&
      cachedBaseLodRef.nodesLength === nodesRef.length &&
      cachedBaseLodRef.firstId === nodesRef[0]?.id &&
      cachedBaseLodRef.lastId === nodesRef[nodesRef.length - 1]?.id &&
      cachedBaseLodRef.expandedRef === expandedRef &&
      cachedBaseLodRef.globalLod === globalLod
    ) {
      return cachedBaseLodMap
    }

    const map = new Map<string, 0 | 1>()
    for (const n of nodesRef) {
      if (isLodLocked) {
        const cached = lodLevelMapCache.get(n.id) as 0 | 1 | undefined
        map.set(n.id, cached ?? globalLod)
      } else {
        map.set(n.id, globalLod)
      }
    }

    if (!isLodLocked) {
      lodLevelMapCache.clear()
      for (const [k, v] of map) lodLevelMapCache.set(k, v)
    }
    cachedBaseLodRef = {
      zoomBucket,
      zoom,
      expandedRef,
      nodesLength: nodesRef.length,
      firstId: nodesRef[0]?.id,
      lastId: nodesRef[nodesRef.length - 1]?.id,
      isLodLocked,
      globalLod,
    }
    cachedBaseLodMap = map
    return map
  })

  /** 保留旧 lodLevelMap 名称作为兼容导出 */
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

  // ============ 节点禁用 (P2-A 2026-06-19) ============

  /**
   * 禁用节点集合. 禁用的节点执行时被跳过 (后端 executor 已支持 skipped 机制).
   * 视觉: RuleNode.vue 检测 is-disabled 类, 半透明 + 灰边.
   */
  const disabledNodeIds = shallowRef<Set<string>>(new Set())

  /** O(1) 查询节点是否禁用 */
  function isNodeDisabled(nodeId: string): boolean {
    return disabledNodeIds.value.has(nodeId)
  }

  /** 切换节点禁用状态 */
  function toggleNodeDisabled(nodeId: string): boolean {
    const next = new Set(disabledNodeIds.value)
    let nowDisabled: boolean
    if (next.has(nodeId)) {
      next.delete(nodeId)
      nowDisabled = false
    } else {
      next.add(nodeId)
      nowDisabled = true
    }
    disabledNodeIds.value = next
    return nowDisabled
  }

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
      return markRaw({
        id: n.id,
        type: 'ruleNode',
        position: n.position ?? { x: 0, y: 0 },
        data: {
          ...(n.data ?? {}),
          type: isVueFlowType ? (n.data?.type ?? 'unknown') : n.type,
          id: n.id
        } as RuleNodeData
      })
    })
    _nodeByIdMarkDirty()

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
    _indexRebuild()
    triggerRef(_connectedHandleVersion)

    // P2-A: 从节点 data.disabled 恢复禁用状态
    const disabledIds = new Set<string>()
    for (const n of (data.nodes ?? []) as GraphNode[]) {
      const nodeData = (n as any).data ?? {}
      if (nodeData.disabled === true) {
        disabledIds.add(n.id)
      }
    }
    disabledNodeIds.value = disabledIds

    // 跨子 store: 解析 variables
    const variablesStore = useRuleVariablesStore()
    if (data.variables_json) {
      try {
        const vars = JSON.parse(data.variables_json) as Record<string, {
          type?: string; defaultValue?: VariableDefaultValue; description?: string
        }>
        variablesStore.setVariables(Object.entries(vars).map(([name, config]) => ({
          name,
          type: (config.type as VariableType) ?? 'STRING',
          defaultValue: config.defaultValue ?? '',
          description: config.description ?? ''
        })))
      } catch {
        variablesStore.setVariables([])
      }
    } else if (data.variables) {
      const vars = data.variables as Record<string, {
        type?: VariableType
        defaultValue?: VariableDefaultValue
        description?: string
      }>
      variablesStore.setVariables(Object.entries(vars).map(([name, config]) => ({
        name,
        type: config.type ?? 'STRING',
        defaultValue: config.defaultValue,
        description: config.description ?? ''
      })))
    }

    saveHistory()
    lastSavedHistoryIndex.value = historyIndex.value
    return data
  }

  // ============ 保存 ============

  /**
   * 保存规则图 - 将节点/边序列化为 JSON 字符串写入后端。
   */
  async function saveGraph() {
    if (!graphMeta.value) return

    const variablesStore = useRuleVariablesStore()
    const varsObj: Record<string, {
      type: VariableType; defaultValue: VariableDefaultValue; description: string
    }> = {}
    for (const v of variablesStore.variables) {
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
        data: {
          ...n.data,
          // P2-A: 把禁用状态持久化到 data.disabled
          disabled: disabledNodeIds.value.has(n.id),
        }
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
    lastSavedHistoryIndex.value = historyIndex.value
  }

  // ============ 草稿 (P0-2 2026-06-19) ============

  function saveDraftToLocalStorage(graphId: number): boolean {
    try {
      const variablesStore = useRuleVariablesStore()
      const payload = {
        nodes: nodes.value,
        edges: edges.value,
        variables: variablesStore.variables,
        graphName: graphMeta.value?.name,
        savedAt: Date.now(),
      }
      localStorage.setItem(`cogniflow:rule-graph:${graphId}:draft`, JSON.stringify(payload))
      return true
    } catch {
      return false
    }
  }

  function loadDraftFromLocalStorage(graphId: number): {
    nodes: Node<RuleNodeData>[]; edges: Edge[]; variables: Variable[]
    graphName?: string; savedAt: number
  } | null {
    try {
      const raw = localStorage.getItem(`cogniflow:rule-graph:${graphId}:draft`)
      if (!raw) return null
      const payload = JSON.parse(raw)
      if (!Array.isArray(payload.nodes)) return null
      return payload
    } catch {
      return null
    }
  }

  function clearLocalStorageDraft(graphId: number): void {
    try {
      localStorage.removeItem(`cogniflow:rule-graph:${graphId}:draft`)
    } catch {
      // 静默
    }
  }

  // ============ 导入导出 JSON (P1-3 2026-06-19) ============

  function exportToJSON(): string {
    const variablesStore = useRuleVariablesStore()
    const payload = {
      graphName: graphMeta.value?.name || 'untitled',
      graphDescription: graphMeta.value?.description,
      nodes: nodes.value.map((n) => ({
        id: n.id,
        type: n.data?.type ?? 'unknown',
        position: { x: n.position.x, y: n.position.y },
        data: n.data,
      })),
      edges: edges.value.map((e) => ({
        id: e.id,
        source: e.source,
        target: e.target,
        source_handle: e.sourceHandle,
        target_handle: e.targetHandle,
      })),
      variables: variablesStore.variables,
      exportedAt: new Date().toISOString(),
      version: '1.0.0',
    }
    return JSON.stringify(payload, null, 2)
  }

  function importFromJSON(text: string): string {
    const payload = JSON.parse(text)
    if (!Array.isArray(payload.nodes) || !Array.isArray(payload.edges)) {
      throw new Error('JSON 格式无效：缺少 nodes/edges 数组')
    }
    nodes.value = payload.nodes.map((n: any) =>
      markRaw({
        id: n.id,
        type: 'ruleNode',
        position: n.position ?? { x: 0, y: 0 },
        data: {
          ...(n.data ?? {}),
          type: n.type ?? n.data?.type ?? 'unknown',
          id: n.id,
        } as RuleNodeData,
      })
    )
    _nodeByIdMarkDirty()
    edges.value = payload.edges.map((e: any) => ({
      id: e.id,
      source: e.source,
      target: e.target,
      sourceHandle: e.source_handle ?? e.sourceHandle,
      targetHandle: e.target_handle ?? e.targetHandle,
      type: 'default',
      animated: false,
      markerEnd: MarkerType.ArrowClosed,
    }))
    _indexRebuild()
    triggerRef(_connectedHandleVersion)
    const variablesStore = useRuleVariablesStore()
    variablesStore.setVariables(Array.isArray(payload.variables) ? payload.variables : [])
    if (graphMeta.value && payload.graphName) {
      graphMeta.value = { ...graphMeta.value, name: payload.graphName }
    }
    saveHistory()
    return payload.graphName || 'untitled'
  }

  /**
   * 复制当前图为新图 (另存为)。
   */
  async function duplicateAsNewGraph(newName?: string): Promise<number> {
    const variablesStore = useRuleVariablesStore()
    const name = newName || `${graphMeta.value?.name || 'untitled'} (副本)`
    const res = await ruleEngineApi.createGraph({
      name,
      description: graphMeta.value?.description || undefined,
      nodes_json: JSON.stringify(nodes.value.map((n) => ({
        id: n.id,
        type: n.data?.type ?? 'unknown',
        position: n.position,
        data: n.data,
      }))),
      edges_json: JSON.stringify(edges.value.map((e) => ({
        id: e.id,
        source: e.source,
        target: e.target,
        source_handle: e.sourceHandle,
        target_handle: e.targetHandle,
      }))),
      variables_json: JSON.stringify(
        variablesStore.variables.reduce((acc: Record<string, any>, v) => {
          acc[v.name] = {
            type: v.type,
            defaultValue: v.defaultValue ?? null,
            description: v.description || '',
          }
          return acc
        }, {})
      ),
    })
    return (res.data as any).id as number
  }

  // ============ 自动布局 (P2-C 2026-06-19) ============

  /**
   * 简单 DAG 自动布局 (Sugiyama-lite):
   * 1. Kahn 拓扑分层
   * 2. 同层节点沿 X 轴均匀分布
   * 3. 不同层沿 Y 轴递增
   */
  function autoLayoutGraph(options?: {
    nodeSpacing?: number
    levelSpacing?: number
    startX?: number
    startY?: number
  }): Array<{ id: string; position: { x: number; y: number } }> {
    const NODE_W = options?.nodeSpacing ?? 320
    const LEVEL_H = options?.levelSpacing ?? 180
    const startX = options?.startX ?? 100
    const startY = options?.startY ?? 100

    const nodeArr = nodes.value
    if (nodeArr.length === 0) return []

    const adj = new Map<string, string[]>()
    const inDeg = new Map<string, number>()
    for (const n of nodeArr) {
      adj.set(n.id, [])
      inDeg.set(n.id, 0)
    }
    for (const e of edges.value) {
      if (adj.has(e.source) && adj.has(e.target)) {
        adj.get(e.source)!.push(e.target)
        inDeg.set(e.target, (inDeg.get(e.target) ?? 0) + 1)
      }
    }

    const levels: string[][] = []
    const remaining = new Map(inDeg)
    const placed = new Set<string>()
    while (placed.size < nodeArr.length) {
      const layer: string[] = []
      for (const [id, d] of remaining) {
        if (d === 0) layer.push(id)
      }
      if (layer.length === 0) {
        for (const [id] of remaining) layer.push(id)
      }
      layer.sort((a, b) => {
        const na = nodeArr.find((n) => n.id === a)
        const nb = nodeArr.find((n) => n.id === b)
        return (na?.position.y ?? 0) - (nb?.position.y ?? 0)
      })
      levels.push(layer)
      for (const id of layer) {
        placed.add(id)
        remaining.delete(id)
        for (const t of adj.get(id) ?? []) {
          if (remaining.has(t)) {
            remaining.set(t, remaining.get(t)! - 1)
          }
        }
      }
    }

    const maxLevelWidth = Math.max(...levels.map((l) => l.length)) * NODE_W
    const updates: Array<{ id: string; position: { x: number; y: number } }> = []
    for (let li = 0; li < levels.length; li++) {
      const layer = levels[li]
      const layerWidth = layer.length * NODE_W
      const offsetX = startX + (maxLevelWidth - layerWidth) / 2
      layer.forEach((id, idx) => {
        updates.push({
          id,
          position: {
            x: offsetX + idx * NODE_W,
            y: startY + li * LEVEL_H,
          },
        })
      })
    }
    return updates
  }

  function applyAutoLayout(): number {
    const updates = autoLayoutGraph()
    if (updates.length === 0) return 0
    setNodesPositions(updates, true, false, false)
    return updates.length
  }

  // ============ 节点操作 ============

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
    nodes.value = [...nodes.value, markRaw(newNode)]
    _nodeByIdMarkDirty()
    saveHistory()
    return true
  }

  /**
   * 更新节点配置 - 内部 mutate + 触发 _configVersion（精确信号）.
   * FIX (BUG-4 2026-06-19): 不 triggerRef(nodes), 仅精确触发 _configVersion
   */
  function updateNodeConfig(nodeId: string, key: string, value: VariableDefaultValue) {
    const node = nodes.value.find(n => n.id === nodeId)
    if (node?.data) {
      if (!node.data.config) {
        node.data.config = {} as Record<string, VariableDefaultValue>
      }
      node.data.config[key] = value
      _configVersion.value++
    }
  }

  /** 批量更新节点位置 (路径 B: 自研拖动专用) */
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

    if (!skipTrigger) {
      triggerRef(nodes)
    }
  }

  /**
   * 删除节点并清理关联边 / 选中状态 / 历史记录。
   */
  function removeNode(nodeId: string) {
    nodes.value = nodes.value.filter(n => n.id !== nodeId)
    _nodeByIdMarkDirty()
    edges.value = edges.value.filter(e => e.source !== nodeId && e.target !== nodeId)
    if (expandedNodeIds.value.has(nodeId)) {
      expandedNodeIds.value.delete(nodeId)
      triggerRef(expandedNodeIds)
    }
    saveHistory()
  }

  /** 批量删除节点 (Phase B 任务4) */
  function removeNodes(nodeIds: string[]) {
    if (nodeIds.length === 0) return
    const idSet = new Set(nodeIds)
    nodes.value = nodes.value.filter(n => !idSet.has(n.id))
    _nodeByIdMarkDirty()
    const removedEdges = edges.value.filter(e => idSet.has(e.source) || idSet.has(e.target))
    edges.value = edges.value.filter(e => !idSet.has(e.source) && !idSet.has(e.target))
    for (const e of removedEdges) _indexRemoveEdge(e)
    triggerRef(_connectedHandleVersion)
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

  /** 切换节点折叠状态 (Phase 19.3+: 语义反转) */
  function toggleNodeExpanded(nodeId: string) {
    if (expandedNodeIds.value.has(nodeId)) {
      expandedNodeIds.value.delete(nodeId)
    } else {
      expandedNodeIds.value.add(nodeId)
    }
    triggerRef(expandedNodeIds)
  }

  /**
   * 收起全部节点 (点击画布空白处触发)。
   *
   * ⚠️ expandedNodeIds 存的是「**已折叠**的节点 id」(名字与语义相反, 见 Phase 19.3+ 反转,
   *   消费端确认见 RuleNode.vue `isCollapsed = expandedNodeIds.has(id)`)。
   *   所以「收起全部」= 把所有节点 id 都放进去, **不是** clear()。
   *
   * 修复 (2026-09-12): 原实现是 clear(), 等于「全部展开」, 与函数名恰好相反。
   *   用户点空白本意是收起所有展开的节点以切回画布视角, 实际却把所有节点都展开了。
   */
  function collapseAllExpanded() {
    if (nodes.value.length === 0) return
    let changed = false
    for (const n of nodes.value) {
      if (!expandedNodeIds.value.has(n.id)) {
        expandedNodeIds.value.add(n.id)
        changed = true
      }
    }
    // 原地变更 + triggerRef: 与 removeNode / removeNodes / toggleNodeExpanded 一致,
    // 避免重新赋值导致外部捕获的 Set 引用失效
    if (changed) triggerRef(expandedNodeIds)
  }

  function syncExpandedNodeIds() {
    triggerRef(expandedNodeIds)
  }

  /**
   * 展开全部节点。
   *
   * 同上语义反转: 「展开全部」= 清空「已折叠」集合。
   *
   * 修复 (2026-09-12): 原实现是 new Set(所有节点 id), 等于「全部收起」, 与函数名相反。
   *   这两个函数体此前正好互换 (collapseAllExpanded 做了展开、expandAll 做了收起)。
   */
  function expandAll() {
    if (expandedNodeIds.value.size === 0) return
    expandedNodeIds.value.clear()
    triggerRef(expandedNodeIds)
  }

  // ============ 边操作 ============

  /** 添加边 */
  function addEdge(connection: {
    source: string; target: string
    sourceHandle?: string | null; targetHandle?: string | null
  }): boolean {
    if (connection.source === connection.target) return false
    const dup = edges.value.some((e) =>
      e.source === connection.source &&
      e.target === connection.target &&
      (e.sourceHandle ?? null) === (connection.sourceHandle ?? null) &&
      (e.targetHandle ?? null) === (connection.targetHandle ?? null)
    )
    if (dup) return false
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
    _indexAddEdge(newEdge)
    triggerRef(_connectedHandleVersion)
    _recordEdgeAddHistory(newEdge)
    return true
  }

  function removeEdge(edgeId: string) {
    const target = edges.value.find(e => e.id === edgeId)
    edges.value = edges.value.filter(e => e.id !== edgeId)
    if (target) _indexRemoveEdge(target)
    triggerRef(_connectedHandleVersion)
    if (target) _recordEdgeRemoveHistory(target)
  }

  function removeEdges(edgeIds: string[]) {
    if (edgeIds.length === 0) return
    const idSet = new Set(edgeIds)
    const removed = edges.value.filter(e => idSet.has(e.id))
    edges.value = edges.value.filter(e => !idSet.has(e.id))
    for (const e of removed) _indexRemoveEdge(e)
    triggerRef(_connectedHandleVersion)
    if (removed.length > 0) _recordEdgesRemoveHistory(removed)
  }

  // ============ 节点对齐 (P1-2 2026-06-19) ============

  function _alignSelectedNodesImpl(
    mode: AlignMode,
    selectedFlowNodes: Array<{ id: string; position: { x: number; y: number } }>,
    screenToFlowCoordinate: (pt: { x: number; y: number }) => { x: number; y: number }
  ): number {
    if (selectedFlowNodes.length < 2) return 0
    const ids = selectedFlowNodes.map((n) => n.id)

    interface Box { id: string; x: number; y: number; w: number; h: number }
    const boxes: Box[] = []
    for (const n of selectedFlowNodes) {
      const el = document.querySelector<HTMLElement>(`.vue-flow__node[data-id="${n.id}"]`)
      if (!el) continue
      const r = el.getBoundingClientRect()
      const tl = screenToFlowCoordinate({ x: r.left, y: r.top })
      const br = screenToFlowCoordinate({ x: r.right, y: r.bottom })
      boxes.push({
        id: n.id,
        x: tl.x,
        y: tl.y,
        w: br.x - tl.x,
        h: br.y - tl.y,
      })
    }
    if (boxes.length < 2) return 0

    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity
    for (const b of boxes) {
      if (b.x < minX) minX = b.x
      if (b.y < minY) minY = b.y
      if (b.x + b.w > maxX) maxX = b.x + b.w
      if (b.y + b.h > maxY) maxY = b.y + b.h
    }
    const midX = (minX + maxX) / 2
    const midY = (minY + maxY) / 2

    const updates: Array<{ id: string; position: { x: number; y: number } }> = []
    for (const b of boxes) {
      let nx = b.x
      let ny = b.y
      switch (mode) {
        case 'left':
          nx = minX
          break
        case 'right':
          nx = maxX - b.w
          break
        case 'top':
          ny = minY
          break
        case 'bottom':
          ny = maxY - b.h
          break
        case 'h-center':
          nx = midX - b.w / 2
          break
        case 'v-center':
          ny = midY - b.h / 2
          break
        case 'distribute-h': {
          if (boxes.length < 3) break
          const sorted = [...boxes].sort((a, b) => a.x - b.x)
          const first = sorted[0]
          const last = sorted[sorted.length - 1]
          const span = (last.x + last.w / 2) - (first.x + first.w / 2)
          const step = span / (sorted.length - 1)
          const idx = sorted.findIndex((s) => s.id === b.id)
          if (idx > 0 && idx < sorted.length - 1) {
            nx = (first.x + first.w / 2) + step * idx - b.w / 2
          }
          break
        }
        case 'distribute-v': {
          if (boxes.length < 3) break
          const sorted = [...boxes].sort((a, b) => a.y - b.y)
          const first = sorted[0]
          const last = sorted[sorted.length - 1]
          const span = (last.y + last.h / 2) - (first.y + first.h / 2)
          const step = span / (sorted.length - 1)
          const idx = sorted.findIndex((s) => s.id === b.id)
          if (idx > 0 && idx < sorted.length - 1) {
            ny = (first.y + first.h / 2) + step * idx - b.h / 2
          }
          break
        }
      }
      if (nx !== b.x || ny !== b.y) {
        updates.push({ id: b.id, position: { x: nx, y: ny } })
      }
    }
    void ids
    if (updates.length === 0) return 0

    setNodesPositions(updates, true, false, false)
    return updates.length
  }

  function alignSelectedNodes(
    mode: AlignMode,
    screenToFlowCoordinate: (pt: { x: number; y: number }) => { x: number; y: number }
  ): number {
    const selected = _getSelectedNodesFn ? _getSelectedNodesFn() : []
    return _alignSelectedNodesImpl(mode, selected, screenToFlowCoordinate)
  }

  /**
   * P1-2 (2026-06-19): store 不直接依赖 useVueFlow, 但 alignSelectedNodes 需要 selected 节点.
   * RuleCanvas 在 onMounted 时注入回调 (避免 store → composable 反向依赖)
   */
  let _getSelectedNodesFn: (() => Array<{ id: string; position: { x: number; y: number } }>) | null = null
  function setSelectedNodesGetter(fn: typeof _getSelectedNodesFn) {
    _getSelectedNodesFn = fn
  }

  // ============ Undo/Redo ============

  function _recordEdgeAddHistory(edge: GraphEdge) {
    if (isHistoryPaused.value) return
    historyStack.value = historyStack.value.slice(0, historyIndex.value + 1)
    historyStack.value.push({ type: 'addEdge', edge: { ...edge } })
    historyIndex.value = historyStack.value.length - 1
    if (historyStack.value.length > maxHistorySize) {
      historyStack.value.shift()
      historyIndex.value--
    }
  }
  function _recordEdgeRemoveHistory(edge: GraphEdge) {
    if (isHistoryPaused.value) return
    historyStack.value = historyStack.value.slice(0, historyIndex.value + 1)
    historyStack.value.push({ type: 'removeEdge', edge: { ...edge } })
    historyIndex.value = historyStack.value.length - 1
    if (historyStack.value.length > maxHistorySize) {
      historyStack.value.shift()
      historyIndex.value--
    }
  }
  function _recordEdgesRemoveHistory(removedEdges: GraphEdge[]) {
    if (isHistoryPaused.value) return
    if (removedEdges.length === 0) return
    historyStack.value = historyStack.value.slice(0, historyIndex.value + 1)
    historyStack.value.push({ type: 'removeEdges', edges: removedEdges.map(e => ({ ...e })) })
    historyIndex.value = historyStack.value.length - 1
    if (historyStack.value.length > maxHistorySize) {
      historyStack.value.shift()
      historyIndex.value--
    }
  }

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

  function recordMoveHistory(nodeId: string, from: { x: number; y: number }, to: { x: number; y: number }) {
    if (isHistoryPaused.value) return
    if (from.x === to.x && from.y === to.y) return
    historyStack.value = historyStack.value.slice(0, historyIndex.value + 1)
    historyStack.value.push({ type: 'move', nodeId, from: { ...from }, to: { ...to } })
    historyIndex.value = historyStack.value.length - 1
    if (historyStack.value.length > maxHistorySize) {
      historyStack.value.shift()
      historyIndex.value--
    }
  }

  function undo() {
    if (!canUndo.value) return
    historyIndex.value--
    applyHistoryEntry(historyStack.value[historyIndex.value], 'undo')
  }

  function redo() {
    if (!canRedo.value) return
    historyIndex.value++
    applyHistoryEntry(historyStack.value[historyIndex.value], 'redo')
  }

  function applyHistoryEntry(
    entry: typeof historyStack.value[number],
    direction: 'undo' | 'redo',
  ) {
    if (entry.type === 'snapshot') {
      nodes.value = JSON.parse(JSON.stringify(entry.nodes))
      _nodeByIdMarkDirty()
      edges.value = JSON.parse(JSON.stringify(entry.edges))
      _indexRebuild()
      triggerRef(_connectedHandleVersion)
    } else if (entry.type === 'move') {
      const targetPos = direction === 'undo' ? entry.from : entry.to
      const node = nodes.value.find(n => n.id === entry.nodeId)
      if (node) {
        node.position = { ...targetPos }
        triggerRef(nodes)
      }
    } else if (entry.type === 'addEdge') {
      if (direction === 'undo') {
        edges.value = edges.value.filter(e => e.id !== entry.edge.id)
        _indexRemoveEdge(entry.edge)
      } else {
        edges.value = [...edges.value, entry.edge]
        _indexAddEdge(entry.edge)
      }
      triggerRef(_connectedHandleVersion)
    } else if (entry.type === 'removeEdge') {
      if (direction === 'undo') {
        edges.value = [...edges.value, entry.edge]
        _indexAddEdge(entry.edge)
      } else {
        edges.value = edges.value.filter(e => e.id !== entry.edge.id)
        _indexRemoveEdge(entry.edge)
      }
      triggerRef(_connectedHandleVersion)
    } else if (entry.type === 'removeEdges') {
      if (direction === 'undo') {
        edges.value = [...edges.value, ...entry.edges]
        for (const e of entry.edges) _indexAddEdge(e)
      } else {
        const idSet = new Set(entry.edges.map(e => e.id))
        edges.value = edges.value.filter(e => !idSet.has(e.id))
        for (const e of entry.edges) _indexRemoveEdge(e)
      }
      triggerRef(_connectedHandleVersion)
    } else {
      const updates = entry.moves.map(m => ({
        id: m.nodeId,
        position: { ...(direction === 'undo' ? m.from : m.to) },
      }))
      setNodesPositions(updates, false)
    }
  }

  function pauseHistory() {
    isHistoryPaused.value = true
  }

  function unpauseHistory() {
    isHistoryPaused.value = false
    saveHistory()
  }

  function resumeHistory() {
    isHistoryPaused.value = false
  }

  // ============ 辅助函数 ============

  /** 获取节点类型对应的分类名称。 */
  function getNodeCategory(type: string): string {
    const def = nodeDefinitions.value.find(d => d.type === type)
    return def?.category ?? 'action'
  }

  // ============ LOD 状态 (Phase LOD-1) ============

  /** 自节流 setViewportZoom — 同一帧内多次合并为 1 次 ref.set */
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

  function setDragging(v: boolean) {
    isDragging.value = v
  }

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
    expandedNodeIds,
    availableModels,
    historyStack,
    historyIndex,
    isHistoryPaused,
    maxHistorySize,
    lastSavedHistoryIndex,
    viewportZoom,
    isDragging,
    isSelectionBoxActive,
    disabledNodeIds,
    currentGlobalLod,

    // 计算属性
    connectedHandleIndex,
    nodeById,
    canUndo,
    canRedo,
    isDirty,
    hasNodes,
    nodeDefinitionsByCategory,
    lodLevelMap,
    getLodLevel,
    configVersion: _configVersion,

    // 数据加载
    fetchNodeDefinitions,
    fetchModels,
    loadGraph,
    saveGraph,

    // 草稿 (P0-2)
    saveDraftToLocalStorage,
    loadDraftFromLocalStorage,
    clearLocalStorageDraft,

    // 导入导出 (P1-3)
    exportToJSON,
    importFromJSON,
    duplicateAsNewGraph,

    // 自动布局 (P2-C)
    autoLayoutGraph,
    applyAutoLayout,

    // 节点操作
    createNode,
    updateNodeConfig,
    setNodesPositions,
    removeNode,
    removeNodes,
    toggleNodeExpanded,
    collapseAllExpanded,
    syncExpandedNodeIds,
    expandAll,
    isHandleConnected,

    // 节点禁用 (P2-A)
    isNodeDisabled,
    toggleNodeDisabled,

    // 边操作
    addEdge,
    removeEdge,
    removeEdges,

    // Undo/Redo
    saveHistory,
    recordMoveHistory,
    undo,
    redo,
    pauseHistory,
    unpauseHistory,
    resumeHistory,

    // 节点对齐 (P1-2)
    alignSelectedNodes,
    setSelectedNodesGetter,

    // 辅助函数
    getNodeCategory,

    // LOD (Phase LOD-1)
    setViewportZoom,
    setDragging,
    setSelectionBoxActive,
  }
})
