// -*- coding: utf-8 -*-
/**
 * 快速添加选点测试 —— 保证空画布能露出各分类代表节点。
 */
import { describe, expect, it } from 'vitest'
import { pickQuickAddNodes } from './ruleQuickAdd'
import type { NodeDefinition } from '@/types/api'

function def(type: string, category: string): NodeDefinition {
  return {
    type,
    category,
    label: type,
    inputs: [],
    outputs: [],
    config_schema: {},
  }
}

describe('pickQuickAddNodes', () => {
  it('每个分类只取一个, 不再是注册顺序前 4 个', () => {
    const defs = [
      def('screen_capture', 'input'),
      def('manual_trigger', 'input'),
      def('yolo_model', 'detection'),
      def('image_preprocessor', 'processing'),
      def('log_action', 'action'),
      def('branch', 'logic'),
      def('alert_output', 'output'),
    ]
    const picked = pickQuickAddNodes(defs)
    expect(picked.map((d) => d.type)).toEqual([
      'screen_capture',
      'yolo_model',
      'image_preprocessor',
      'log_action',
      'branch',
      'alert_output',
    ])
  })

  it('分类缺失时归入 other 分组', () => {
    const picked = pickQuickAddNodes([def('a', ''), def('b', '')])
    expect(picked).toHaveLength(1)
    expect(picked[0]?.type).toBe('a')
  })

  it('空列表返回空数组', () => {
    expect(pickQuickAddNodes([])).toEqual([])
  })
})
