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

  function setExecutionStatus(status: ExecutionState['status']) {
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
    executionState.value.progress = progress
    triggerRef(executionState)
  }

  function setNodeExecutionState(nodeId: string, state: string) {
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
    executionState.value.executionId = id
    triggerRef(executionState)
  }

  return {
    executionState,
    setExecutionStatus,
    addExecutionLog,
    setExecutionProgress,
    setNodeExecutionState,
    clearExecution,
    setExecutionId,
  }
})
