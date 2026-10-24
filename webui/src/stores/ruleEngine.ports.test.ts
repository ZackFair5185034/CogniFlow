// -*- coding: utf-8 -*-
/**
 * 端口兼容矩阵 store 测试 - 前端不再硬编码兼容规则。
 *
 * 背景: 后端 `backend/services/rule_engine/port_types.py` 是矩阵的唯一事实源,
 * 前端旧实现只认 4 条规则, 与后端 14 类矩阵漂移, 导致 BOOLEAN->TRIGGER 的边
 * 被 VueFlow 在 isValidConnection 阶段静默丢弃, 动作层事实上不可达。
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

const mockGet = vi.fn()

vi.mock('@/api/index', () => ({
  ruleEngineApi: {
    getPortCompatibility: () => mockGet(),
  },
}))

import { useRulePortsStore } from './ruleEngine/ports'

describe('useRulePortsStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    mockGet.mockReset()
  })

  it('矩阵未加载时拒绝未知类型组合(fail-loud, 不静默放行)', () => {
    const store = useRulePortsStore()
    expect(store.loaded).toBe(false)
    expect(store.isCompatible('BOOLEAN', 'TRIGGER')).toBe(false)
    expect(store.isCompatible('IMAGE', 'IMAGE')).toBe(false)
  })

  it('加载后按后端矩阵判定 BOOLEAN -> TRIGGER 兼容', async () => {
    mockGet.mockResolvedValue({
      data: {
        matrix: { BOOLEAN: ['ANY', 'BOOLEAN', 'TRIGGER', 'CONTROL'] },
        types: ['ANY', 'BOOLEAN', 'TRIGGER'],
      },
    })
    const store = useRulePortsStore()
    await store.loadPorts()
    expect(store.loaded).toBe(true)
    expect(store.isCompatible('BOOLEAN', 'TRIGGER')).toBe(true)
    expect(store.isCompatible('IMAGE', 'BOOLEAN')).toBe(false)
  })

  it('ANY 与任意类型双向兼容', async () => {
    mockGet.mockResolvedValue({
      data: {
        matrix: { ANY: ['ANY', 'IMAGE', 'BOOLEAN'] },
        types: ['ANY', 'IMAGE', 'BOOLEAN'],
      },
    })
    const store = useRulePortsStore()
    await store.loadPorts()
    expect(store.isCompatible('ANY', 'BOOLEAN')).toBe(true)
    expect(store.isCompatible('IMAGE', 'ANY')).toBe(true)
  })

  it('接口失败时保持未加载状态并抛出错误', async () => {
    mockGet.mockRejectedValue(new Error('网络错误'))
    const store = useRulePortsStore()
    await expect(store.loadPorts()).rejects.toThrow('网络错误')
    expect(store.loaded).toBe(false)
  })

  it('未知源类型不兼容', async () => {
    mockGet.mockResolvedValue({
      data: {
        matrix: { IMAGE: ['ANY', 'IMAGE'] },
        types: ['ANY', 'IMAGE'],
      },
    })
    const store = useRulePortsStore()
    await store.loadPorts()
    expect(store.isCompatible('NOT_A_TYPE', 'IMAGE')).toBe(false)
  })
})
