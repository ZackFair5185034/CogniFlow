// -*- coding: utf-8 -*-
/**
 * 规则引擎 compat store 回归测试 (P1-A.1, 2026-09-11)
 *
 * 背景: ruleEngine.ts 拆成 3 个子 store 后, useRuleEngineStore 变成聚合兼容层。
 * 它把子 store 的 storeToRefs 结果直接展开返回 —— 若某个字段在子 store 里不是
 * ref/computed (例如 graph.ts 的 `const maxHistorySize = 20` 这个普通常量),
 * storeToRefs 不会包含它, 展开后就成了 undefined。
 *
 * 后果: 任何 `storeToRefs(useRuleEngineStore())` 调用都会崩在 pinia 内部的
 * `value.effect` 上, 且堆栈完全指不到源头 —— 表现为 RuleCanvas 的 setup 抛
 * "Cannot read properties of undefined (reading 'effect')", 页面白屏。
 *
 * 这组测试锁定该回归。
 */
import { describe, it, expect, beforeEach } from 'vitest'
import { createPinia, setActivePinia, storeToRefs } from 'pinia'
import { toRaw } from 'vue'
import { useRuleEngineStore } from './ruleEngine'
import { useRuleGraphStore } from './ruleEngine/graph'

describe('useRuleEngineStore 兼容层', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('不暴露 undefined 字段', () => {
    const store = useRuleEngineStore()
    const raw = toRaw(store as unknown as Record<string, unknown>)
    const undefinedKeys = Object.keys(raw).filter((k) => raw[k] === undefined)
    expect(undefinedKeys).toEqual([])
  })

  it('storeToRefs(store) 可正常调用 (P1-A.1 回归)', () => {
    const store = useRuleEngineStore()
    // 修复前抛: TypeError: Cannot read properties of undefined (reading 'effect')
    const refs = storeToRefs(store)
    const keys = Object.keys(refs)
    for (const k of [
      'nodes',
      'edges',
      'canUndo',
      'canRedo',
      'hasNodes',
      'graphMeta',
      'nodeDefinitions',
      'executionState',
      'variables',
    ]) {
      expect(keys, `缺少 ${k}`).toContain(k)
    }
  })

  it('RuleCanvas 的解构写法可用', () => {
    const store = useRuleEngineStore()
    const {
      nodes,
      edges,
      canUndo,
      canRedo,
      hasNodes,
      variables,
      nodeDefinitions,
      graphMeta,
    } = storeToRefs(store)

    for (const [name, r] of Object.entries({
      nodes,
      edges,
      canUndo,
      canRedo,
      hasNodes,
      variables,
      nodeDefinitions,
      graphMeta,
    })) {
      expect(r, `${name} 应为 ref`).toBeDefined()
      expect('value' in (r as object), `${name} 应为 ref`).toBe(true)
    }
  })

  it('非 ref 常量 maxHistorySize 仍可读取', () => {
    const store = useRuleEngineStore()
    expect(store.maxHistorySize).toBe(20)
  })

  it('通过 compat store 写入会同步到子 store', () => {
    const store = useRuleEngineStore()
    const graph = useRuleGraphStore()
    const { graphMeta } = storeToRefs(store)

    graphMeta.value = { id: 7, name: 'cf-test', is_active: false }
    expect(graph.graphMeta?.id).toBe(7)
    expect(graph.graphMeta?.name).toBe('cf-test')
  })
})
