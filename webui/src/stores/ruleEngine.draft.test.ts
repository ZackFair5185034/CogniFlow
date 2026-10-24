// -*- coding: utf-8 -*-
/**
 * 草稿自动保存测试 (Task 15) —— 载荷瘦身 + 变更计数。
 *
 * 背景: 旧实现每 5s 定时器无条件全图序列化, 且序列化的是含 VueFlow 内部字段
 * (dimensions / handleBounds / computedPosition / internals) 的原始节点对象,
 * 500 节点图轻易上百 KB, localStorage 超配额后写入被静默吞掉 —— 草稿形同虚设。
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

describe('草稿自动保存 (Task 15)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
  })

  it('草稿载荷只含业务字段, 不含 VueFlow 内部字段', () => {
    const store = useRuleGraphStore()
    store.createNode(makeDef('a'), { x: 0, y: 0 })

    // 模拟 VueFlow 在节点对象上挂的内部字段
    const node = store.nodes[0] as unknown as Record<string, unknown>
    node.dimensions = { width: 280, height: 222 }
    node.handleBounds = { source: [], target: [] }
    node.computedPosition = { x: 12, y: 34 }
    node.internals = { positionAbsolute: { x: 12, y: 34 } }
    node.selected = true

    expect(store.saveDraftToLocalStorage(1)).toBe(true)

    const raw = localStorage.getItem('cogniflow:rule-graph:1:draft')
    expect(raw).toBeTruthy()
    const parsed = JSON.parse(raw!)

    const saved = parsed.nodes[0]
    expect(saved.dimensions).toBeUndefined()
    expect(saved.handleBounds).toBeUndefined()
    expect(saved.computedPosition).toBeUndefined()
    expect(saved.internals).toBeUndefined()

    // 业务字段保留
    expect(saved.id).toBe(node.id)
    expect(saved.type).toBe('ruleNode')
    expect(saved.position).toEqual({ x: 0, y: 0 })
    expect(saved.data.type).toBe('a')

    // 体积显著小于原始对象
    expect(raw!.length).toBeLessThan(JSON.stringify(store.nodes).length)
  })

  it('dirtyTick 在结构改动与配置改动时都自增', () => {
    const store = useRuleGraphStore()
    const before = store.dirtyTick

    store.createNode(makeDef('a'), { x: 0, y: 0 })
    expect(store.dirtyTick).toBeGreaterThan(before)

    const afterCreate = store.dirtyTick
    const node = store.nodes[0]!
    store.updateNodeConfig(node.id, 'threshold', 0.9)
    expect(store.dirtyTick).toBeGreaterThan(afterCreate)
  })
})
