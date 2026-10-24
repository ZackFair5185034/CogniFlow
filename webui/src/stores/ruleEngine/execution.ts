// -*- coding: utf-8 -*-
/**
 * 规则引擎执行状态 (P1-A 拆分)
 *
 * 独立子 store — 仅管理 executionState (status / progress / logs / nodeStates).
 * 日志批量合并 (P1-H): 100ms 内多条 log 合成一次 triggerRef, YOLO 30FPS 推流时
 * 避免峰值帧耗.
 */

import { defineStore } from 'pinia'
import { shallowRef, triggerRef } from 'vue'

/** 执行状态 */
export interface ExecutionState {
  status: 'idle' | 'running' | 'success' | 'failed'
  progress: number
  executionId: number | null
  logs: ExecutionLog[]
  nodeStates: Record<string, string>
}

/**
 * 单条执行日志。
 *
 * `id` 是必填的 —— 视图层用 vue-virtual-scroller 渲染日志列表,
 * 该库默认按 `keyField='id'` 取键, 取不到就直接抛
 * "Key is undefined on item" → 整个列表一条都渲染不出来 (2026-10-24 走查发现)。
 */
export interface ExecutionLog {
  /** 全局递增序号 —— 作为虚拟列表的唯一键 */
  id: number
  level: string
  timestamp: string
  node_type?: string
  message: string
  duration_ms?: number
  /** 节点输出指标（如 detections 数量、数据量等） */
  metrics?: Record<string, number>
}

/** 写入日志时的入参 —— id 由 store 统一分配, 调用方不用关心 */
export type ExecutionLogInput = Omit<ExecutionLog, 'id'>

export const useRuleExecutionStore = defineStore('ruleExecution', () => {
  /**
   * 执行状态 (Phase 17.2 P1-H: shallowRef 避免 logs/nodeStates 深代理)
   *  - logs 高速推送 (YOLO 30FPS) 时, 深 ref 触发整对象深 watcher 链
   *  - 改 shallowRef 后, mutate 字段需手动 triggerRef 通知
   *  - addExecutionLog 走 100ms 批合并, 推送峰值帧耗不抖
   */
  const executionState = shallowRef<ExecutionState>({
    status: 'idle',
    progress: 0,
    executionId: null,
    logs: [],
    nodeStates: {}
  })

  /** P1-H: 日志批合并 — 100ms 内多条 log 合成一次 triggerRef */
  let pendingLogs: ExecutionLog[] = []
  let logsFlushTimer: ReturnType<typeof setTimeout> | null = null
  const LOGS_BATCH_INTERVAL_MS = 100

  /** 日志序号 —— 作为虚拟列表的唯一键, 全局递增不重复 */
  let logIdSeq = 0

  function flushPendingLogs() {
    if (pendingLogs.length === 0) return
    // ⚠️ 必须**换引用**而不是就地 push (2026-10-24 走查发现)。
    //
    // 视图层用的是 `computed(() => store.executionState.logs)` —— 返回的是数组本身。
    // Vue 的 refreshComputed 只在 `hasChanged(value, oldValue)` 为真时才通知依赖,
    // 而 hasChanged 对数组比的是引用。就地 push 后引用不变 → computed 重算后
    // 判定「值没变」→ **不通知依赖** → 模板永远停在「暂无执行日志」。
    // (节点状态能正常回显是因为它是字符串, 值变了就满足 hasChanged。)
    //
    // 换新数组引用后 hasChanged 为真 → 依赖被通知 → 列表按 100ms 批节奏刷新。
    executionState.value.logs = [...executionState.value.logs, ...pendingLogs]
    pendingLogs = []
    logsFlushTimer = null
    triggerRef(executionState)
  }

  function setExecutionStatus(status: ExecutionState['status']) {
    executionState.value.status = status
    triggerRef(executionState)
  }

  function addExecutionLog(log: ExecutionLogInput) {
    // P1-H: 100ms 批合并 — YOLO 30FPS 推流时, 一次推送可能 N 条 log
    // id 在此统一分配: 虚拟列表按 id 取键, 缺了就渲染不出来
    logIdSeq += 1
    pendingLogs.push({ ...log, id: logIdSeq })
    if (logsFlushTimer === null) {
      logsFlushTimer = setTimeout(flushPendingLogs, LOGS_BATCH_INTERVAL_MS)
    }
  }

  function setExecutionProgress(progress: number) {
    executionState.value.progress = progress
    triggerRef(executionState)
  }

  /**
   * 节点状态回填回调 - 由 graph store 注册。
   * 用回调而不是直接 import graph store, 避免两个子 store 互相依赖成环。
   */
  let nodeStateSink: ((nodeId: string, state: string) => void) | null = null

  /** 注册节点状态回填回调 */
  function setNodeStateSink(sink: (nodeId: string, state: string) => void): void {
    nodeStateSink = sink
  }

  function setNodeExecutionState(nodeId: string, state: string) {
    executionState.value.nodeStates[nodeId] = state
    triggerRef(executionState)
    // 回填到节点状态, 让 RuleNode 的状态视觉真正点亮。
    // timeout 归一化为 failed(节点状态只有 idle/running/success/failed 四态)。
    const visual = state === 'timeout' ? 'failed' : state
    nodeStateSink?.(nodeId, visual)
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
    executionState.value.executionId = id
    triggerRef(executionState)
  }

  return {
    executionState,
    setExecutionStatus,
    addExecutionLog,
    setExecutionProgress,
    setNodeExecutionState,
    setNodeStateSink,
    clearExecution,
    setExecutionId,
  }
})
