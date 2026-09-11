// -*- coding: utf-8 -*-
/**
 * 规则引擎状态管理 - Pinia Store 入口 (P1-A 拆分)
 *
 * 拆分为 3 个子 store:
 *   - useRuleGraphStore      → 画布与图状态 (nodes/edges/LOD/history/...)
 *   - useRuleExecutionStore  → 执行状态 (status/progress/logs/nodeStates)
 *   - useRuleVariablesStore  → 变量列表
 *
 * 为保持向后兼容, useRuleEngineStore 作为聚合代理 (compat shim) 暴露:
 *   - 所有响应式 state (ref/computed) 通过 storeToRefs 从子 store 转发
 *   - 所有方法通过子 store 转发 (Pinia 已绑定 this, 直接 spread 安全)
 *   - 旧 view 代码 useRuleEngineStore() 调用零迁移成本
 *
 * 新代码建议直接 import 子 store, 减少 proxy 跳转.
 *
 * 文件布局:
 *   ruleEngine/
 *   ├── index.ts       ← 兼容入口 (本文件)
 *   ├── _helpers.ts    ← 共享工具
 *   ├── graph.ts       ← 画布/图 store
 *   ├── execution.ts   ← 执行 store
 *   └── variables.ts   ← 变量 store
 */

import { defineStore, storeToRefs } from 'pinia'
import { useRuleGraphStore } from './graph'
import { useRuleExecutionStore } from './execution'
import { useRuleVariablesStore } from './variables'

// ============ 类型导出 ============

export type {
  VariableDefaultValue,
  NodeDefinition,
  GraphNode,
  GraphEdge,
  ConfigSchemaProperty,
  RuleNodeData,
  VariableType,
} from '@/types/api'

export type { Variable } from './variables'
export type { GraphMeta, AlignMode } from './graph'
export type { ExecutionState } from './execution'

// 子 store re-export
export { useRuleGraphStore } from './graph'
export { useRuleExecutionStore } from './execution'
export { useRuleVariablesStore } from './variables'

// ============ 兼容层 useRuleEngineStore ============

/**
 * P1-A (2026-09-11): 兼容层 store, 旧代码 useRuleEngineStore() 调用仍工作.
 * 内部委托到 3 个子 store. view 应逐步迁移到直接 import 子 store.
 */
export const useRuleEngineStore = defineStore('ruleEngine', () => {
  const graph = useRuleGraphStore()
  const execution = useRuleExecutionStore()
  const variables = useRuleVariablesStore()

  // 状态: 通过 storeToRefs 拿真实 refs (Pinia 同实例, 修改会传到子 store)
  // 注: storeToRefs 自动 unwrap, 这里拿到的是真正的 Ref<T> 对象, 可读写
  const graphRefs = storeToRefs(graph)
  const executionRefs = storeToRefs(execution)
  const variablesRefs = storeToRefs(variables)

  const exposed = {
    // ===== graph store state (re-exposed) =====
    nodeDefinitions: graphRefs.nodeDefinitions,
    graphMeta: graphRefs.graphMeta,
    nodes: graphRefs.nodes,
    edges: graphRefs.edges,
    expandedNodeIds: graphRefs.expandedNodeIds,
    availableModels: graphRefs.availableModels,
    historyStack: graphRefs.historyStack,
    historyIndex: graphRefs.historyIndex,
    isHistoryPaused: graphRefs.isHistoryPaused,
    // P1-A.1 修复 (2026-09-11): maxHistorySize 在 graph.ts 是普通常量 (非 ref),
    // storeToRefs(graph) 不会包含它 —— 走 graphRefs 会得到 undefined,
    // 导致外部 storeToRefs(本 store) 读 `value.effect` 时抛
    // TypeError: Cannot read properties of undefined (reading 'effect')。
    maxHistorySize: graph.maxHistorySize,
    lastSavedHistoryIndex: graphRefs.lastSavedHistoryIndex,
    viewportZoom: graphRefs.viewportZoom,
    isDragging: graphRefs.isDragging,
    isSelectionBoxActive: graphRefs.isSelectionBoxActive,
    disabledNodeIds: graphRefs.disabledNodeIds,
    currentGlobalLod: graphRefs.currentGlobalLod,

    // ===== graph store computed =====
    connectedHandleIndex: graphRefs.connectedHandleIndex,
    nodeById: graphRefs.nodeById,
    canUndo: graphRefs.canUndo,
    canRedo: graphRefs.canRedo,
    isDirty: graphRefs.isDirty,
    hasNodes: graphRefs.hasNodes,
    nodeDefinitionsByCategory: graphRefs.nodeDefinitionsByCategory,
    lodLevelMap: graphRefs.lodLevelMap,
    configVersion: graphRefs.configVersion,

    // ===== execution store state =====
    executionState: executionRefs.executionState,

    // ===== variables store state =====
    variables: variablesRefs.variables,

    // ===== graph store methods =====
    fetchNodeDefinitions: graph.fetchNodeDefinitions,
    fetchModels: graph.fetchModels,
    loadGraph: graph.loadGraph,
    saveGraph: graph.saveGraph,
    saveDraftToLocalStorage: graph.saveDraftToLocalStorage,
    loadDraftFromLocalStorage: graph.loadDraftFromLocalStorage,
    clearLocalStorageDraft: graph.clearLocalStorageDraft,
    exportToJSON: graph.exportToJSON,
    importFromJSON: graph.importFromJSON,
    duplicateAsNewGraph: graph.duplicateAsNewGraph,
    autoLayoutGraph: graph.autoLayoutGraph,
    applyAutoLayout: graph.applyAutoLayout,
    createNode: graph.createNode,
    updateNodeConfig: graph.updateNodeConfig,
    setNodesPositions: graph.setNodesPositions,
    removeNode: graph.removeNode,
    removeNodes: graph.removeNodes,
    toggleNodeExpanded: graph.toggleNodeExpanded,
    collapseAllExpanded: graph.collapseAllExpanded,
    syncExpandedNodeIds: graph.syncExpandedNodeIds,
    expandAll: graph.expandAll,
    isHandleConnected: graph.isHandleConnected,
    isNodeDisabled: graph.isNodeDisabled,
    toggleNodeDisabled: graph.toggleNodeDisabled,
    addEdge: graph.addEdge,
    removeEdge: graph.removeEdge,
    removeEdges: graph.removeEdges,
    saveHistory: graph.saveHistory,
    recordMoveHistory: graph.recordMoveHistory,
    undo: graph.undo,
    redo: graph.redo,
    pauseHistory: graph.pauseHistory,
    unpauseHistory: graph.unpauseHistory,
    resumeHistory: graph.resumeHistory,
    alignSelectedNodes: graph.alignSelectedNodes,
    setSelectedNodesGetter: graph.setSelectedNodesGetter,
    getNodeCategory: graph.getNodeCategory,
    setViewportZoom: graph.setViewportZoom,
    setDragging: graph.setDragging,
    setSelectionBoxActive: graph.setSelectionBoxActive,
    getLodLevel: graph.getLodLevel,

    // ===== execution store methods =====
    setExecutionStatus: execution.setExecutionStatus,
    addExecutionLog: execution.addExecutionLog,
    setExecutionProgress: execution.setExecutionProgress,
    setNodeExecutionState: execution.setNodeExecutionState,
    clearExecution: execution.clearExecution,
    setExecutionId: execution.setExecutionId,

    // ===== variables store methods =====
    addVariable: variables.addVariable,
    removeVariable: variables.removeVariable,
    updateVariable: variables.updateVariable,
    getVariable: variables.getVariable,
  }

  // 兜底断言 (P1-A.1 2026-09-11):
  //   compat store 里任何 undefined 字段都会让外部 `storeToRefs(compatStore)` 崩在
  //   pinia 内部的 `value.effect` 上, 而报错信息完全指不到源头 (只在 RuleCanvas 的
  //   setup 行号上打转)。这里在 store 创建期就抛出可定位的错误。
  //   根因通常是: 字段来自子 store 但本身不是 ref/computed (普通常量/函数),
  //   被错误地经由 storeToRefs 结果取值。
  for (const [key, value] of Object.entries(exposed)) {
    if (value === undefined) {
      throw new Error(
        `[useRuleEngineStore] 字段 "${key}" 为 undefined。` +
        `若它来自子 store, 请确认是 ref/computed 再走 storeToRefs; ` +
        `普通常量请直接取 store.${key}。`
      )
    }
  }

  return exposed
})
