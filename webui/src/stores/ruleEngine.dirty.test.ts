// -*- coding: utf-8 -*-
/**
 * 脏标记测试 - 任何修改都要能被用户感知。
 *
 * 背景: 2026-10-24 实测发现 `updateNodeConfig` 改节点参数时不写历史栈,
 * 而 `isDirty` 是按 historyIndex 算的 —— 于是改了配置既不可撤销也不标脏,
 * 用户以为保存了其实没保存。
 */
import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import type { NodeDefinition } from '@/types/api'

import { useRuleGraphStore } from './ruleEngine/graph'

/** 构造一个最小可用的节点定义 */
function makeDef(type: string): NodeDefinition {
  return {
    type,
    category: 'test',
    label: type,
    inputs: [],
    outputs: [],
    config_schema: {
      message: { type: 'string', title: '消息', default: '' },
    },
  }
}

describe('规则图脏标记', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('新建节点后标记为脏', () => {
    const store = useRuleGraphStore()
    store.clearDirty()
    expect(store.isDirty).toBe(false)

    store.createNode(makeDef('log_action'), { x: 0, y: 0 })

    expect(store.isDirty).toBe(true)
  })

  it('修改节点配置后标记为脏', () => {
    const store = useRuleGraphStore()
    store.createNode(makeDef('log_action'), { x: 0, y: 0 })
    const nodeId = store.nodes[0].id
    store.clearDirty()
    expect(store.isDirty).toBe(false)

    store.updateNodeConfig(nodeId, 'message', '你好')

    expect(store.isDirty).toBe(true)
  })

  it('修改节点配置不产生历史快照(避免每次按键都全图克隆)', () => {
    const store = useRuleGraphStore()
    store.createNode(makeDef('log_action'), { x: 0, y: 0 })
    const nodeId = store.nodes[0].id
    const historyBefore = store.historyStack.length

    store.updateNodeConfig(nodeId, 'message', '你好')
    store.updateNodeConfig(nodeId, 'message', '你好呀')

    expect(store.historyStack.length).toBe(historyBefore)
  })

  it('clearDirty 后恢复为干净状态', () => {
    const store = useRuleGraphStore()
    store.createNode(makeDef('log_action'), { x: 0, y: 0 })
    store.updateNodeConfig(store.nodes[0].id, 'message', '你好')
    expect(store.isDirty).toBe(true)

    store.clearDirty()

    expect(store.isDirty).toBe(false)
  })

  it('连线后标记为脏', () => {
    const store = useRuleGraphStore()
    store.createNode(makeDef('log_action'), { x: 0, y: 0 })
    store.createNode(makeDef('log_action'), { x: 200, y: 0 })
    const [a, b] = store.nodes
    store.clearDirty()

    store.addEdge({
      source: a.id,
      target: b.id,
      sourceHandle: 'result',
      targetHandle: 'trigger',
    })

    expect(store.isDirty).toBe(true)
  })
})
