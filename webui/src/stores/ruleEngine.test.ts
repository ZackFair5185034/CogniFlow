// -*- coding: utf-8 -*-
/**
 * LOD 等级决策单元测试 (Phase 19.3+: 单阈值两级, 默认全展开)
 *
 * 覆盖 store.lodLevelMap (Phase 19.3 反转):
 * - LOD 0/1 两级 (LOD 2 概念删除, 配置只受 expandedNodeIds 集合的反转语义控制)
 * - 单阈值 0.65, 无 hysteresis 死区
 * - 升档 LOD 0 → 1: zoom ≥ 0.65
 * - 降档 LOD 1 → 0: zoom < 0.65
 * - expandedNodeIds 含义反转 = "已折叠节点"
 *   - 默认空集 = 全节点全展开 (280px, 配置可见)
 *   - 双击加入 = 折叠 (200px, 配置 hidden)
 *
 * 设计取舍:
 * - 测 store 纯函数 (lodLevelMap computed), 不 mount RuleCanvas
 * - 不测 v-memo / CSS class (Vue 渲染层职责, vue-tsc 静态检查已覆盖)
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

describe('LOD 等级决策 (Phase 19.3+: 单阈值两级, 默认全展开)', () => {
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

  it('zoom 0.64 (低于 0.65 阈值) → 全 LOD 0', () => {
    const s = useRuleEngineStore()
    s.nodes = makeNodes(5) as any
    s.viewportZoom = 0.64
    expect(s.lodLevelMap.get('n0')).toBe(0)
  })

  it('zoom 0.65 (升档阈值) → 全 LOD 1', () => {
    const s = useRuleEngineStore()
    s.nodes = makeNodes(5) as any
    s.viewportZoom = 0.65
    expect(s.lodLevelMap.get('n0')).toBe(1)
  })

  it('zoom 0.50 → 全 LOD 0 (低于 0.65 阈值)', () => {
    const s = useRuleEngineStore()
    s.nodes = makeNodes(5) as any
    s.viewportZoom = 0.50
    expect(s.lodLevelMap.get('n0')).toBe(0)
  })

  it('zoom 1.50 / 2.0 仍 LOD 1 (LOD 2 概念已删除)', () => {
    const s = useRuleEngineStore()
    s.nodes = makeNodes(5) as any
    s.viewportZoom = 1.5
    expect(s.lodLevelMap.get('n0')).toBe(1)
    s.viewportZoom = 2.0
    expect(s.lodLevelMap.get('n0')).toBe(1)
  })

  it('expandedNodeIds 集合反转: 不影响 baseLod, 仅作 CSS 折叠修饰符开关', () => {
    const s = useRuleEngineStore()
    s.nodes = makeNodes(5) as any
    s.viewportZoom = 1.0
    const before = s.lodLevelMap.get('n0')
    s.expandedNodeIds = new Set(['n0', 'n2'])
    const after = s.lodLevelMap.get('n0')
    expect(after).toBe(before)
  })

  it('toggleNodeExpanded: 默认全展开 -> 双击 -> 折叠集合', () => {
    const s = useRuleEngineStore()
    s.nodes = makeNodes(5) as any
    s.viewportZoom = 1.0
    expect(s.expandedNodeIds.has('n0')).toBe(false)
    s.toggleNodeExpanded('n0')
    expect(s.expandedNodeIds.has('n0')).toBe(true)
    s.toggleNodeExpanded('n0')
    expect(s.expandedNodeIds.has('n0')).toBe(false)
  })

  it('collapseAllExpanded: 折叠集合清空 -> 所有节点回全展开', () => {
    const s = useRuleEngineStore()
    s.nodes = makeNodes(5) as any
    s.expandedNodeIds = new Set(['n0', 'n2', 'n4'])
    expect(s.expandedNodeIds.size).toBe(3)
    s.collapseAllExpanded()
    expect(s.expandedNodeIds.size).toBe(0)
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
    for (const z of [0.1, 0.5, 0.65, 0.8, 1.0, 1.5, 2.0, 3.0]) {
      s.viewportZoom = z
      const levels = Array.from(s.lodLevelMap.values())
      // 只能是 0 或 1
      for (const l of levels) {
        expect([0, 1]).toContain(l)
      }
    }
  })
})
