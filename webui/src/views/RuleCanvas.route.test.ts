// -*- coding: utf-8 -*-
/**
 * 路由可达性测试 - 画布内的跳转目标必须真实存在。
 *
 * 背景: 2026-10-24 实测发现「复制为新」跳转 `/rule-engine/${newId}`,
 * 而实际路由是 `/rule-engine/design/:id` —— 点「复制为新」后跳到不存在的
 * 路由, 表现为白屏无反应。
 */
import { describe, expect, it } from 'vitest'
import router from '@/router/index'
import { ruleCanvasPath, ruleListPath } from '@/utils/ruleNavigation'

describe('规则引擎路由', () => {
  it('存在「复制为新」跳转目标的路由(规则图设计器)', () => {
    const paths = router.getRoutes().map((r) => r.path)
    expect(paths).toContain('/rule-engine/design/:id')
  })

  it('规则图设计器路由名可解析', () => {
    const resolved = router.resolve({
      name: 'rule-canvas',
      params: { id: '42' },
    })
    expect(resolved.path).toBe('/rule-engine/design/42')
  })

  it('ruleCanvasPath 产出的是真实存在的路由', () => {
    const paths = router.getRoutes().map((r) => r.path)
    const path = ruleCanvasPath(42)
    // 把 :id 段替换成实际值后必须命中某条路由
    const matched = paths.some((p) => p.replace(':id', '42') === path)
    expect(matched).toBe(true)
  })

  it('ruleCanvasPath 不产出旧版的 /rule-engine/:id(那是坏跳转的目标)', () => {
    expect(ruleCanvasPath(42)).not.toBe('/rule-engine/42')
    expect(ruleCanvasPath(42)).toBe('/rule-engine/design/42')
  })

  it('不存在旧版的 /rule-engine/:id 路由', () => {
    const paths = router.getRoutes().map((r) => r.path)
    expect(paths).not.toContain('/rule-engine/:id')
  })

  it('规则图列表路由存在', () => {
    const paths = router.getRoutes().map((r) => r.path)
    expect(paths).toContain('/rule-engine')
    expect(ruleListPath()).toBe('/rule-engine')
  })
})
