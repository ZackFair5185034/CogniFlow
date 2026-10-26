// -*- coding: utf-8 -*-
/**
 * 框选命中测试 - 必须是数据层判定, 与 DOM 无关。
 *
 * 背景 (Task 16): 旧实现走 DOM 查询 (`.vue-flow__node[data-id]`),
 * 视口外的节点在 DOM 里不存在 → 框不到 (纯缺陷, 与节点数量无关);
 * 且每次框选结束都要对所有可见节点做 getBoundingClientRect, 强制布局。
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
    config_schema: {},
  }
}

describe('框选命中', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('返回锚点落在矩形内的节点', () => {
    const store = useRuleGraphStore()
    store.createNode(makeDef('log_action'), { x: 0, y: 0 })
    store.createNode(makeDef('log_action'), { x: 1000, y: 1000 })
    const [inside, outside] = store.nodes

    const ids = store.nodesInRect({ x: -50, y: -50, width: 200, height: 200 })

    expect(ids).toContain(inside.id)
    expect(ids).not.toContain(outside.id)
  })

  it('不依赖 DOM, 视口外的节点也能被框到', () => {
    const store = useRuleGraphStore()
    // 模拟"视口外"的节点: 坐标很大, 但仍在矩形内
    store.createNode(makeDef('log_action'), { x: 5000, y: 5000 })
    const node = store.nodes[0]!

    const ids = store.nodesInRect({ x: 4900, y: 4900, width: 200, height: 200 })

    expect(ids).toContain(node.id)
  })

  it('空矩形返回空数组', () => {
    const store = useRuleGraphStore()
    store.createNode(makeDef('log_action'), { x: 0, y: 0 })

    expect(store.nodesInRect({ x: 100, y: 100, width: 0, height: 0 })).toEqual([])
  })

  it('负宽高 (反向拖拽) 也能正确命中', () => {
    const store = useRuleGraphStore()
    store.createNode(makeDef('log_action'), { x: 150, y: 150 })
    const node = store.nodes[0]!

    // 从右下往左上拖 → width/height 为负, 归一化后是 (100,100)-(200,200)
    const ids = store.nodesInRect({ x: 200, y: 200, width: -100, height: -100 })

    expect(ids).toContain(node.id)
  })
})
