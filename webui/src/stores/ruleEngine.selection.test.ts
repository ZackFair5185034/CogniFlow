// -*- coding: utf-8 -*-
/**
 * 选中态增量维护 + 配置版本按节点粒度 —— store 层测试。
 *
 * 背景 (Task 14):
 * - 选中态: 旧实现每次 select change 都整体替换 nodes 数组 (500 节点图 = 全图 vdom diff),
 *   现改为增量 setNodeSelected + selectedIds 集合。
 * - 配置版本: 旧实现是全局计数器, 改一个节点会让全图节点配置区重算,
 *   现改为按节点粒度的版本号 Map。
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
      threshold: { type: 'number', title: '阈值', default: 0.5 },
    },
  }
}

describe('规则图 store - 增量选中态 (Task 14)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('setNodeSelected 只增删目标 id, 不替换 nodes 数组引用', () => {
    const store = useRuleGraphStore()
    store.createNode(makeDef('a'), { x: 0, y: 0 })
    store.createNode(makeDef('b'), { x: 200, y: 0 })
    const [a, b] = store.nodes
    const nodesRefBefore = store.nodes

    store.setNodeSelected(a.id, true)
    expect(store.selectedIds.has(a.id)).toBe(true)
    expect(store.selectedIds.has(b.id)).toBe(false)

    store.setNodeSelected(b.id, true)
    expect(store.selectedIds.size).toBe(2)

    // 数组引用不变 —— 这是「不触发整图 vdom diff」的前提
    expect(store.nodes).toBe(nodesRefBefore)
  })

  it('取消选中会同时清掉节点自身的 selected 标记', () => {
    const store = useRuleGraphStore()
    store.createNode(makeDef('a'), { x: 0, y: 0 })
    const [a] = store.nodes

    store.setNodeSelected(a.id, true)
    expect(store.nodeById.get(a.id)?.data?.selected).toBe(true)

    store.setNodeSelected(a.id, false)
    expect(store.selectedIds.has(a.id)).toBe(false)
    expect(store.nodeById.get(a.id)?.data?.selected).toBe(false)
  })

  it('删除节点时自动从选中集合中移除', () => {
    const store = useRuleGraphStore()
    store.createNode(makeDef('a'), { x: 0, y: 0 })
    const [a] = store.nodes
    store.setNodeSelected(a.id, true)

    store.removeNode(a.id)
    expect(store.selectedIds.size).toBe(0)
  })

  it('clearSelection 清空整个集合', () => {
    const store = useRuleGraphStore()
    store.createNode(makeDef('a'), { x: 0, y: 0 })
    store.createNode(makeDef('b'), { x: 200, y: 0 })
    store.setNodeSelected(store.nodes[0]!.id, true)
    store.setNodeSelected(store.nodes[1]!.id, true)

    store.clearSelection()
    expect(store.selectedIds.size).toBe(0)
  })
})

describe('规则图 store - 按节点粒度的配置版本 (Task 14)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('改一个节点只影响该节点的版本号', () => {
    const store = useRuleGraphStore()
    store.createNode(makeDef('a'), { x: 0, y: 0 })
    store.createNode(makeDef('b'), { x: 200, y: 0 })
    const [a, b] = store.nodes

    expect(store.configVersionOf(a.id)).toBe(0)
    expect(store.configVersionOf(b.id)).toBe(0)

    store.updateNodeConfig(a.id, 'threshold', 0.8)

    expect(store.configVersionOf(a.id)).toBe(1)
    expect(store.configVersionOf(b.id)).toBe(0)
  })

  it('配置变更后 isDirty 为真 (改了参数没保存 = 脏)', () => {
    const store = useRuleGraphStore()
    store.createNode(makeDef('a'), { x: 0, y: 0 })
    const [a] = store.nodes
    store.clearDirty()
    expect(store.isDirty).toBe(false)

    store.updateNodeConfig(a.id, 'threshold', 0.9)
    expect(store.isDirty).toBe(true)
  })
})
