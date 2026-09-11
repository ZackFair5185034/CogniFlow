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
import type { Node } from '@vue-flow/core'
import type { RuleNodeData } from '@/types/api'
import { useRuleEngineStore } from '@/stores/ruleEngine'

/**
 * 构造 N 个 fake 节点, 类型与 store.nodes (Node<RuleNodeData>[]) 兼容。
 *
 * 2026-09-12: 显式声明返回类型并在此处做一次断言, 取代原先 11 个调用点各自的
 * `as any` (触发 @typescript-eslint/no-explicit-any 警告)。
 *
 * 用 `as unknown as` 双重断言而非直接 `as`: fixture 的运行时形状**刻意保持不变**
 * (data 多带一个 id, inputs/outputs 用 {} 占位), 以免改动依赖该形状的既有用例;
 * 而这些形状与 NodePort[] 互不可比, 直接断言会被 TS 拒绝。
 */
function makeNodes(n: number): Node<RuleNodeData>[] {
  return Array.from({ length: n }, (_, i) => ({
    id: `n${i}`,
    type: 'rule',
    data: {
      id: `n${i}`,
      type: 'set_variable',
      label: `Node ${i}`,
      category: 'data',
      inputs: {},
      outputs: {},
    },
    position: { x: i * 100, y: 0 },
  })) as unknown as Node<RuleNodeData>[]
}

describe('LOD 等级决策 (Phase 19.3+: 单阈值两级, 默认全展开)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('zoom 1.0 默认 → 全 LOD 1', () => {
    const s = useRuleEngineStore()
    s.nodes = makeNodes(25)
    s.viewportZoom = 1.0
    const levels = Array.from(s.lodLevelMap.values())
    expect(levels.every((l) => l === 1)).toBe(true)
  })

  it('zoom 0.64 (低于 0.65 阈值) → 全 LOD 0', () => {
    const s = useRuleEngineStore()
    s.nodes = makeNodes(5)
    s.viewportZoom = 0.64
    expect(s.lodLevelMap.get('n0')).toBe(0)
  })

  it('zoom 0.65 (升档阈值) → 全 LOD 1', () => {
    const s = useRuleEngineStore()
    s.nodes = makeNodes(5)
    s.viewportZoom = 0.65
    expect(s.lodLevelMap.get('n0')).toBe(1)
  })

  it('zoom 0.50 → 全 LOD 0 (低于 0.65 阈值)', () => {
    const s = useRuleEngineStore()
    s.nodes = makeNodes(5)
    s.viewportZoom = 0.50
    expect(s.lodLevelMap.get('n0')).toBe(0)
  })

  it('zoom 1.50 / 2.0 仍 LOD 1 (LOD 2 概念已删除)', () => {
    const s = useRuleEngineStore()
    s.nodes = makeNodes(5)
    s.viewportZoom = 1.5
    expect(s.lodLevelMap.get('n0')).toBe(1)
    s.viewportZoom = 2.0
    expect(s.lodLevelMap.get('n0')).toBe(1)
  })

  it('expandedNodeIds 集合反转: 不影响 baseLod, 仅作 CSS 折叠修饰符开关', () => {
    const s = useRuleEngineStore()
    s.nodes = makeNodes(5)
    s.viewportZoom = 1.0
    const before = s.lodLevelMap.get('n0')
    s.expandedNodeIds = new Set(['n0', 'n2'])
    const after = s.lodLevelMap.get('n0')
    expect(after).toBe(before)
  })

  it('toggleNodeExpanded: 默认全展开 -> 双击 -> 折叠集合', () => {
    const s = useRuleEngineStore()
    s.nodes = makeNodes(5)
    s.viewportZoom = 1.0
    expect(s.expandedNodeIds.has('n0')).toBe(false)
    s.toggleNodeExpanded('n0')
    expect(s.expandedNodeIds.has('n0')).toBe(true)
    s.toggleNodeExpanded('n0')
    expect(s.expandedNodeIds.has('n0')).toBe(false)
  })

  // 修复 (2026-09-12): 原测试名为「折叠集合清空 -> 所有节点回全展开」, 断言的是
  // collapseAllExpanded() 把集合清空 —— 恰好是「全部展开」, 与函数名相反。
  // 说明 collapseAllExpanded / expandAll 两个函数体此前互换了。
  it('collapseAllExpanded: 全部节点进入「已折叠」集合 (点击空白收起)', () => {
    const s = useRuleEngineStore()
    s.nodes = makeNodes(5)
    s.expandedNodeIds = new Set(['n0'])
    expect(s.expandedNodeIds.size).toBe(1)
    s.collapseAllExpanded()
    expect(s.expandedNodeIds.size).toBe(5)
    for (const n of s.nodes) {
      expect(s.expandedNodeIds.has(n.id), `${n.id} 应被收起`).toBe(true)
    }
  })

  it('expandAll: 清空「已折叠」集合 -> 全部展开', () => {
    const s = useRuleEngineStore()
    s.nodes = makeNodes(5)
    s.expandedNodeIds = new Set(['n0', 'n2', 'n4'])
    expect(s.expandedNodeIds.size).toBe(3)
    s.expandAll()
    expect(s.expandedNodeIds.size).toBe(0)
  })

  it('拖动期 isDragging=true 锁定 LOD (v-memo 期间不跳变)', () => {
    const s = useRuleEngineStore()
    s.nodes = makeNodes(5)
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
    s.nodes = makeNodes(5)
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
