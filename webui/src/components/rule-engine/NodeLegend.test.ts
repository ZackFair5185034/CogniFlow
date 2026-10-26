// -*- coding: utf-8 -*-
/**
 * 图例组件测试 - 必须覆盖 6 类节点分类与常用端口类型。
 *
 * 背景: 画布此前没有图例, 用户看不出颜色含义。
 */
import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import NodeLegend from './NodeLegend.vue'
import { LEGEND_CATEGORIES, LEGEND_PORT_TYPES } from './legendMeta'

describe('NodeLegend', () => {
  it('覆盖 6 个节点分类', () => {
    expect(LEGEND_CATEGORIES).toHaveLength(6)
    expect(LEGEND_CATEGORIES.map((c) => c.key)).toEqual([
      'input',
      'detection',
      'processing',
      'action',
      'logic',
      'output',
    ])
  })

  it('包含常用端口类型说明', () => {
    const types = LEGEND_PORT_TYPES.map((p) => p.type)
    for (const t of ['ANY', 'IMAGE', 'BOOLEAN', 'TRIGGER', 'CONTROL', 'STRING']) {
      expect(types).toContain(t)
    }
  })

  it('渲染分类名与端口类型', () => {
    const wrapper = mount(NodeLegend)
    const text = wrapper.text()
    for (const cat of LEGEND_CATEGORIES) {
      expect(text).toContain(cat.label)
    }
    expect(text).toContain('ANY')
    expect(text).toContain('TRIGGER')
  })
})
