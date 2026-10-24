// -*- coding: utf-8 -*-
/**
 * 执行状态回填测试 - nodeStates 必须映射回节点数据。
 *
 * 背景: WS 消息写的是 `executionState.nodeStates`, 但没有任何代码把它映射回
 * 节点, 而 `RuleNode.vue` 的状态视觉读的是节点状态 —— 结果执行状态永不点亮。
 */
import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { computed, watchEffect } from 'vue'
import type { NodeDefinition } from '@/types/api'

import { useRuleExecutionStore } from './ruleEngine/execution'
import { useRuleGraphStore } from './ruleEngine/graph'

/** 构造一个最小可用的节点定义 */
function makeDef(type: string, ports: string[] = []): NodeDefinition {
  return {
    type,
    category: 'test',
    label: type,
    inputs: ports.map((p) => ({ name: p, type: 'ANY' })),
    outputs: ports.map((p) => ({ name: p, type: 'ANY' })),
    config_schema: {},
  }
}

describe('执行状态回填', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('setNodeExecutionState 会把状态写回节点', () => {
    const graphStore = useRuleGraphStore()
    const executionStore = useRuleExecutionStore()
    graphStore.createNode(makeDef('log_action'), { x: 0, y: 0 })
    const nodeId = graphStore.nodes[0].id

    executionStore.setNodeStateSink((id, state) => graphStore.setNodeStatus(id, state))
    executionStore.setNodeExecutionState(nodeId, 'running')

    expect(graphStore.getNodeStatus(nodeId)).toBe('running')
  })

  it('timeout 归一化为 failed 视觉状态', () => {
    const graphStore = useRuleGraphStore()
    const executionStore = useRuleExecutionStore()
    graphStore.createNode(makeDef('log_action'), { x: 0, y: 0 })
    const nodeId = graphStore.nodes[0].id

    executionStore.setNodeStateSink((id, state) => graphStore.setNodeStatus(id, state))
    executionStore.setNodeExecutionState(nodeId, 'timeout')

    expect(graphStore.getNodeStatus(nodeId)).toBe('failed')
  })

  it('clearExecution 不清除节点状态(历史状态保留)', () => {
    const graphStore = useRuleGraphStore()
    const executionStore = useRuleExecutionStore()
    graphStore.createNode(makeDef('log_action'), { x: 0, y: 0 })
    const nodeId = graphStore.nodes[0].id
    executionStore.setNodeStateSink((id, state) => graphStore.setNodeStatus(id, state))
    executionStore.setNodeExecutionState(nodeId, 'success')

    executionStore.clearExecution()

    expect(graphStore.getNodeStatus(nodeId)).toBe('success')
  })

  it('状态变更只影响目标节点', () => {
    const graphStore = useRuleGraphStore()
    const executionStore = useRuleExecutionStore()
    graphStore.createNode(makeDef('log_action'), { x: 0, y: 0 })
    graphStore.createNode(makeDef('log_action'), { x: 200, y: 0 })
    const [first, second] = graphStore.nodes

    executionStore.setNodeStateSink((id, state) => graphStore.setNodeStatus(id, state))
    executionStore.setNodeExecutionState(first.id, 'running')

    expect(graphStore.getNodeStatus(first.id)).toBe('running')
    expect(graphStore.getNodeStatus(second.id)).toBe('idle')
  })

  it('clearNodeStatuses 把所有节点状态复位为 idle', () => {
    const graphStore = useRuleGraphStore()
    graphStore.createNode(makeDef('log_action'), { x: 0, y: 0 })
    const nodeId = graphStore.nodes[0].id
    graphStore.setNodeStatus(nodeId, 'success')

    graphStore.clearNodeStatuses()

    expect(graphStore.getNodeStatus(nodeId)).toBe('idle')
  })
})

/**
 * 日志列表的响应式回归 (2026-10-24 走查发现)。
 *
 * 视图层用的是 `computed(() => store.executionState.logs)` ——
 * computed 返回的是数组**本身**。Vue 的 refreshComputed 只在
 * `hasChanged(value, oldValue)` 为真时才通知依赖, 而 hasChanged 对数组比引用。
 * 若批合并时就地 push, 引用不变 → computed 判定「值没变」→ 不通知依赖
 * → 模板永远停在「暂无执行日志」(节点状态能回显是因为它是字符串, 值确实变了)。
 */
describe('执行日志的响应式刷新', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('批合并落盘后, 依赖 logs 的 computed 必须把变化通知出去', async () => {
    const executionStore = useRuleExecutionStore()
    // 复刻视图层的取法: computed 直接返回数组
    const logs = computed(() => executionStore.executionState.logs)
    const observed: number[] = []
    watchEffect(() => {
      observed.push(logs.value.length)
    })
    expect(observed).toEqual([0])

    executionStore.addExecutionLog({
      level: 'info',
      timestamp: '12:00:00',
      message: '开始执行: manual_trigger',
    })
    // 等过 100ms 的批合并窗口
    await new Promise((resolve) => setTimeout(resolve, 150))

    expect(executionStore.executionState.logs.length).toBe(1)
    // 关键断言: 视图层依赖被通知 → 重新渲染
    expect(observed).toEqual([0, 1])
  })

  it('clearExecution 后日志列表归零且通知出去', async () => {
    const executionStore = useRuleExecutionStore()
    executionStore.addExecutionLog({ level: 'info', timestamp: '12:00:00', message: 'x' })
    await new Promise((resolve) => setTimeout(resolve, 150))

    const logs = computed(() => executionStore.executionState.logs)
    const observed: number[] = []
    watchEffect(() => {
      observed.push(logs.value.length)
    })
    expect(observed).toEqual([1])

    executionStore.clearExecution()
    await new Promise((resolve) => setTimeout(resolve, 0))

    expect(observed).toEqual([1, 0])
  })

  it('每条日志都带唯一 id (虚拟列表按 id 取键, 缺了就一条都渲染不出来)', async () => {
    const executionStore = useRuleExecutionStore()
    executionStore.addExecutionLog({ level: 'info', timestamp: '12:00:00', message: 'a' })
    executionStore.addExecutionLog({ level: 'info', timestamp: '12:00:00', message: 'b' })
    await new Promise((resolve) => setTimeout(resolve, 150))

    const logs = executionStore.executionState.logs
    expect(logs.length).toBe(2)
    expect(logs.every((l) => typeof l.id === 'number')).toBe(true)
    expect(logs[0].id).not.toBe(logs[1].id)
  })
})
