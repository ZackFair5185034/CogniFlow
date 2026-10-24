// -*- coding: utf-8 -*-
/**
 * 草稿提示框状态跟踪测试。
 *
 * 背景 (2026-10-24 走查发现): 草稿恢复用的 ElMessageBox 挂在 body 上,
 * 不随组件卸载消失 —— 离开页面时弹框残留, 再次进入同一张图会再弹一个,
 * 最终多层叠加。本模块用「打开序号」精确配对, 保证旧组件的异步回调
 * 不会误关新组件的弹框。
 */
import { describe, expect, it, beforeEach } from 'vitest'
import {
  closeDraftPrompt,
  hasActiveDraftPrompt,
  openDraftPrompt,
  resetDraftPromptState,
} from './draftPrompt'

describe('draftPrompt', () => {
  beforeEach(() => {
    resetDraftPromptState()
  })

  it('初始状态没有打开的提示框', () => {
    expect(hasActiveDraftPrompt()).toBe(false)
  })

  it('打开后状态为 true, 关闭后回到 false', () => {
    const seq = openDraftPrompt()
    expect(hasActiveDraftPrompt()).toBe(true)
    closeDraftPrompt(seq)
    expect(hasActiveDraftPrompt()).toBe(false)
  })

  it('每次打开返回递增序号', () => {
    const first = openDraftPrompt()
    const second = openDraftPrompt()
    expect(second).toBeGreaterThan(first)
  })

  it('过期序号不能关闭当前提示框', () => {
    const stale = openDraftPrompt()
    const current = openDraftPrompt()
    // 旧组件的异步回调此时才落地 —— 不能把新弹框关掉
    closeDraftPrompt(stale)
    expect(hasActiveDraftPrompt()).toBe(true)
    closeDraftPrompt(current)
    expect(hasActiveDraftPrompt()).toBe(false)
  })

  it('未知序号不影响当前状态', () => {
    openDraftPrompt()
    closeDraftPrompt(9999)
    expect(hasActiveDraftPrompt()).toBe(true)
  })
})
