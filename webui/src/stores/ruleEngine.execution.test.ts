// -*- coding: utf-8 -*-
/**
 * 执行状态回填测试 - nodeStates 必须映射回节点数据。
 *
 * 背景: WS 消息写的是 `executionState.nodeStates`, 但没有任何代码把它映射回
 * 节点, 而 `RuleNode.vue` 的状态视觉读的是节点状态 —— 结果执行状态永不点亮。
 */
import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
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
