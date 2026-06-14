// -*- coding: utf-8 -*-
/**
 * LOD 等级决策单元测试 (Phase 19.2+)
 *
 * 覆盖 store.baseLodLevelMap 的阈值 / hysteresis 行为:
 * - LOD 0/1 两级 (LOD 2 概念删除, 配置只受 expanded CSS 修饰符控制)
 * - 升档阈值 0.80
 * - 降档阈值 0.65
 * - 死区 [0.65, 0.80) 维持上一态
 * - zoom > 1.50 仍 LOD 1 (节点壳只物理放大, 形态不变)
 * - expandedNodeIds 不影响 baseLod (CSS-only .expanded 修饰符负责显示配置)
 *
 * 设计取舍:
 * - 测 store 纯函数 (baseLodLevelMap computed), 不 mount RuleCanvas
 * - 不测 v-memo / CSS class (那是 Vue 渲染层职责, vue-tsc 静态检查已覆盖)
 */
import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useRuleEngineStore } from '@/stores/ruleEngine'

/** 构造 N 个 fake 节点, 类型与 store.nodes 兼容 */
function makeNodes(n: number) {
  return Array.from({ length: n }, (_, i) => ({
    id: `n${i}`,
    type: 'rule',
    data: {
      id: `n${i}`,
      type: 'set_variable',
      label: `Node ${i}`,
      category: 'data' as const,
      inputs: {},
      outputs: {},
    },
    position: { x: i * 100, y: 0 },
  }))
}

describe('LOD 等级决策 (Phase 19.2+: 两级 + hysteresis 死区)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('zoom 1.0 默认 → 全 LOD 1', () => {
    const s = useRuleEngineStore()
    s.nodes = makeNodes(25) as any
    s.viewportZoom = 1.0
    const levels = Array.from(s.lodLevelMap.values())
    expect(levels.every((l) => l === 1)).toBe(true)
  })

  it('zoom 0.50 (低于降档 0.65) → 全 LOD 0', () => {
    const s = useRuleEngineStore()
    s.nodes = makeNodes(5) as any
    s.viewportZoom = 0.50
    expect(s.lodLevelMap.get('n0')).toBe(0)
  })

  it('zoom 0.64 (低于 0.65 阈值) → 全 LOD 0', () => {
    const s = useRuleEngineStore()
    s.nodes = makeNodes(5) as any
    s.viewportZoom = 0.64
    expect(s.lodLevelMap.get('n0')).toBe(0)
  })

  it('zoom 0.80 (升档阈值) → 全 LOD 1', () => {
    const s = useRuleEngineStore()
    s.nodes = makeNodes(5) as any
    s.viewportZoom = 0.80
    expect(s.lodLevelMap.get('n0')).toBe(1)
  })

  it('死区 [0.65, 0.80): 从 LOD 0 出发, 反复扫不跳变', () => {
    const s = useRuleEngineStore()
    s.nodes = makeNodes(5) as any
    s.viewportZoom = 0.50
    expect(s.lodLevelMap.get('n0')).toBe(0)
    // 死区内反复扫
    for (const z of [0.72, 0.68, 0.75, 0.78, 0.65, 0.79]) {
      s.viewportZoom = z
      expect(s.lodLevelMap.get('n0')).toBe(0)
    }
  })

  it('死区内 [0.65, 0.80): 从 LOD 1 出发也不降', () => {
    const s = useRuleEngineStore()
    s.nodes = makeNodes(5) as any
    s.viewportZoom = 1.0
    expect(s.lodLevelMap.get('n0')).toBe(1)
    for (const z of [0.72, 0.68, 0.75, 0.78, 0.65, 0.79]) {
      s.viewportZoom = z
      expect(s.lodLevelMap.get('n0')).toBe(1)
    }
  })

  it('zoom 1.50 / 2.0 仍 LOD 1 (LOD 2 概念已删除)', () => {
    const s = useRuleEngineStore()
    s.nodes = makeNodes(5) as any
    s.viewportZoom = 1.5
    expect(s.lodLevelMap.get('n0')).toBe(1)
    s.viewportZoom = 2.0
    expect(s.lodLevelMap.get('n0')).toBe(1)
  })

  it('expanded 节点不影响 baseLod (CSS-only 修饰符负责)', () => {
    const s = useRuleEngineStore()
    s.nodes = makeNodes(5) as any
    s.viewportZoom = 1.0
    const before = s.lodLevelMap.get('n0')
    s.expandedNodeIds = new Set(['n0', 'n2'])
    const after = s.lodLevelMap.get('n0')
    expect(after).toBe(before)
  })

  it('阈值附近反复扫 7 次 LOD 不跳变 (hysteresis 核心)', () => {
    const s = useRuleEngineStore()
    s.nodes = makeNodes(5) as any
    s.viewportZoom = 1.0
    expect(s.lodLevelMap.get('n0')).toBe(1)
    // 死区内反复扫 7 次
    const flickers = [0.68, 0.79, 0.66, 0.75, 0.78, 0.65, 0.72]
    for (const z of flickers) {
      s.viewportZoom = z
      expect(s.lodLevelMap.get('n0')).toBe(1)
    }
  })

  it('拖动期 isDragging=true 锁定 LOD (v-memo 期间不跳变)', () => {
    const s = useRuleEngineStore()
    s.nodes = makeNodes(5) as any
    s.viewportZoom = 1.0
    expect(s.lodLevelMap.get('n0')).toBe(1)
    s.isDragging = true
    s.viewportZoom = 0.3
    expect(s.lodLevelMap.get('n0')).toBe(1)
    s.isDragging = false
    s.viewportZoom = 0.3
    expect(s.lodLevelMap.get('n0')).toBe(0)
  })

  it('LOD 决策无 LOD 2 概念 (类型保证)', () => {
    const s = useRuleEngineStore()
    s.nodes = makeNodes(5) as any
    for (const z of [0.1, 0.5, 0.7, 1.0, 1.5, 2.0, 3.0]) {
      s.viewportZoom = z
      const levels = Array.from(s.lodLevelMap.values())
      // 只能是 0 或 1
      for (const l of levels) {
        expect([0, 1]).toContain(l)
      }
    }
  })
})
