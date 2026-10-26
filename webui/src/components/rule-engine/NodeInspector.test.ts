// -*- coding: utf-8 -*-
/**
 * 属性面板测试 —— 覆盖「未选中占位」与「选中后展示参数/端口」两条路径。
 *
 * 背景 (Task 13): 画布此前没有右侧属性面板, 改节点参数只能在 LOD2 展开的节点壳内操作。
 */
import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import NodeInspector from './NodeInspector.vue'
import type { RuleNodeData } from '@/types/api'

/** 桩掉配置编辑器 —— 它依赖 pinia store 与 element-plus, 与本用例无关 */
const global = {
  stubs: {
    NodeConfigEditor: { template: '<div class="stub-config-editor" />' },
    SvgIcon: { template: '<i class="stub-icon" />' },
  },
}

const node: RuleNodeData = {
  type: 'yolo_model',
  label: 'YOLO 检测',
  category: 'detection',
  description: '加载 YOLO 模型做目标检测',
  inputs: [{ name: 'image', type: 'IMAGE', label: '图像' }],
  outputs: [{ name: 'bboxes', type: 'BBOX' }, { name: 'count', type: 'NUMBER' }],
  configSchema: {
    confidence: { type: 'number', title: '置信度', default: 0.25 },
  },
}

describe('NodeInspector', () => {
  it('未选中节点时显示占位提示', () => {
    const wrapper = mount(NodeInspector, {
      props: { node: null, nodeId: null },
      global,
    })
    expect(wrapper.text()).toContain('选择一个节点')
    expect(wrapper.find('.stub-config-editor').exists()).toBe(false)
  })

  it('选中节点时展示名称、类型与端口摘要', () => {
    const wrapper = mount(NodeInspector, {
      props: { node, nodeId: 'node_1' },
      global,
    })
    const text = wrapper.text()
    expect(text).toContain('YOLO 检测')
    expect(text).toContain('yolo_model')
    expect(text).toContain('IMAGE')
    expect(text).toContain('BBOX')
    expect(wrapper.find('.stub-config-editor').exists()).toBe(true)
  })

  it('点击关闭时抛出 close 事件', async () => {
    const wrapper = mount(NodeInspector, {
      props: { node, nodeId: 'node_1' },
      global,
    })
    await wrapper.find('.ui-btn-small').trigger('click')
    expect(wrapper.emitted('close')).toBeTruthy()
  })
})
