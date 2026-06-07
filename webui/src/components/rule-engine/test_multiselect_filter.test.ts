// -*- coding: utf-8 -*-
/**
 * Multi-port filter Set 行为单元测试。
 *
 * Phase 15.x 节点面板端口类型过滤支持多选 Set。验证：
 * 1. toggle 行为正确（添加/移除）
 * 2. matchesPortType OR 逻辑（任一选中匹配即通过）
 * 3. 空集合 = 全通过
 */
import { describe, it, expect, beforeEach } from 'vitest'
import { ref } from 'vue'

// 复制 matchesPortType 的核心逻辑（无法在测试环境直接 mount RuleCanvas）
function createFilter() {
  const filter = ref<Set<string>>(new Set())

  function toggle(t: string) {
    const next = new Set(filter.value)
    if (next.has(t)) {
      next.delete(t)
    } else {
      next.add(t)
    }
    filter.value = next
  }

  function matchesPortType(node: { inputs?: { type: string }[]; outputs?: { type: string }[] }): boolean {
    const f = filter.value
    if (f.size === 0) return true
    const inputMatch = node.inputs?.some((p) => f.has(p.type)) ?? false
    const outputMatch = node.outputs?.some((p) => f.has(p.type)) ?? false
    return inputMatch || outputMatch
  }

  return { filter, toggle, matchesPortType }
}

describe('multi-port filter Set behavior', () => {
  let filter: ReturnType<typeof createFilter>

  beforeEach(() => {
    filter = createFilter()
  })

  it('初始状态为空 Set，全节点通过', () => {
    expect(filter.filter.value.size).toBe(0)
    expect(filter.matchesPortType({ inputs: [{ type: 'IMAGE' }] })).toBe(true)
    expect(filter.matchesPortType({ outputs: [{ type: 'BBOX' }] })).toBe(true)
  })

  it('toggle 添加端口类型到 Set', () => {
    filter.toggle('IMAGE')
    expect(filter.filter.value.has('IMAGE')).toBe(true)
    expect(filter.filter.value.size).toBe(1)
  })

  it('toggle 已存在的端口类型会移除（toggle 行为）', () => {
    filter.toggle('IMAGE')
    filter.toggle('IMAGE')
    expect(filter.filter.value.has('IMAGE')).toBe(false)
    expect(filter.filter.value.size).toBe(0)
  })

  it('matchesPortType: 任一选中类型匹配即通过（OR 逻辑）', () => {
    filter.toggle('IMAGE')
    expect(filter.matchesPortType({ inputs: [{ type: 'IMAGE' }] })).toBe(true)
    expect(filter.matchesPortType({ inputs: [{ type: 'BBOX' }] })).toBe(false)
  })

  it('matchesPortType: 多选时任一类型匹配即通过', () => {
    filter.toggle('IMAGE')
    filter.toggle('BBOX')
    // 任一匹配通过
    expect(filter.matchesPortType({ inputs: [{ type: 'IMAGE' }] })).toBe(true)
    expect(filter.matchesPortType({ outputs: [{ type: 'BBOX' }] })).toBe(true)
    // 都不匹配
    expect(filter.matchesPortType({ inputs: [{ type: 'STRING' }] })).toBe(false)
  })

  it('matchesPortType: outputs 端口也参与匹配', () => {
    filter.toggle('BBOX')
    expect(filter.matchesPortType({ inputs: [], outputs: [{ type: 'BBOX' }] })).toBe(true)
  })

  it('多选 toggle 后 Set 保持类型不变（new Set 拷贝）', () => {
    filter.toggle('IMAGE')
    filter.toggle('BBOX')
    const before = filter.filter.value
    filter.toggle('STRING')
    expect(before.has('IMAGE')).toBe(true)
    expect(before.has('BBOX')).toBe(true)
    expect(filter.filter.value.has('STRING')).toBe(true)
    // 原 Set 引用未变（用 new Set 拷贝）
    expect(filter.filter.value).not.toBe(before)
  })
})
