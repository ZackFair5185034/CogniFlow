// -*- coding: utf-8 -*-
/**
 * data.connections 契约测试 - 前端连线必须落到节点数据里。
 *
 * 背景: 后端 `_resolve_inputs` 需要知道「目标端口 <- 哪个节点的哪个输出」。
 * 旧实现把端口元数据数组放在 data.inputs 里, 后端拿到后调 .items() 直接崩,
 * 54 个节点全崩、0 输出。现在端口元数据(data.inputs)与连线关系(data.connections)分离。
 */
import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import type { NodeDefinition } from '@/types/api'

import { useRuleGraphStore } from './ruleEngine/graph'

/** 构造一个最小可用的节点定义 */
function makeDef(type: string, ports: string[] = []): NodeDefinition {
  return {
    type,
    category: 'test',
    label: type,
    inputs: ports.map((p) => ({ name: p, type: 'ANY' })),
    outputs: ports.map((p) => ({ name: p, type: 'ANY' })),
    config_schema: {},
  }
}

describe('规则图 store - data.connections', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('addEdge 后目标节点的 connections 记录上游节点与输出端口', () => {
    const store = useRuleGraphStore()
    store.createNode(makeDef('yolo_model', ['detections']), { x: 0, y: 0 })
    store.createNode(makeDef('log_action', ['trigger']), { x: 200, y: 0 })
    const [source, target] = store.nodes

    const added = store.addEdge({
      source: source.id,
      target: target.id,
      sourceHandle: 'detections',
      targetHandle: 'trigger',
    })

    expect(added).toBe(true)
    const connections = store.nodeById.get(target.id)?.data?.connections
    expect(connections?.trigger).toEqual({
      node_id: source.id,
      output: 'detections',
    })
  })

  it('removeEdge 后清掉对应的 connections 记录', () => {
    const store = useRuleGraphStore()
    store.createNode(makeDef('yolo_model', ['detections']), { x: 0, y: 0 })
    store.createNode(makeDef('log_action', ['trigger']), { x: 200, y: 0 })
    const [source, target] = store.nodes
    store.addEdge({
      source: source.id,
      target: target.id,
      sourceHandle: 'detections',
      targetHandle: 'trigger',
    })
    const edgeId = store.edges[0].id

    store.removeEdge(edgeId)

    const connections = store.nodeById.get(target.id)?.data?.connections
    expect(connections?.trigger).toBeUndefined()
  })

  it('同一目标端口被新边占用时, connections 指向最新上游', () => {
    const store = useRuleGraphStore()
    store.createNode(makeDef('yolo_model', ['detections']), { x: 0, y: 0 })
    store.createNode(makeDef('timer_trigger', ['result']), { x: 0, y: 200 })
    store.createNode(makeDef('log_action', ['trigger']), { x: 200, y: 0 })
    const [source1, source2, target] = store.nodes

    store.addEdge({
      source: source1.id,
      target: target.id,
      sourceHandle: 'detections',
      targetHandle: 'trigger',
    })
    store.addEdge({
      source: source2.id,
      target: target.id,
      sourceHandle: 'result',
      targetHandle: 'trigger',
    })

    const connections = store.nodeById.get(target.id)?.data?.connections
    expect(connections?.trigger?.node_id).toBe(source2.id)
  })

  it('removeEdges 批量删除时同样清空 connections', () => {
    const store = useRuleGraphStore()
    store.createNode(makeDef('yolo_model', ['detections']), { x: 0, y: 0 })
    store.createNode(makeDef('log_action', ['trigger']), { x: 200, y: 0 })
    const [source, target] = store.nodes
    store.addEdge({
      source: source.id,
      target: target.id,
      sourceHandle: 'detections',
      targetHandle: 'trigger',
    })
    const edgeId = store.edges[0].id

    store.removeEdges([edgeId])

    const connections = store.nodeById.get(target.id)?.data?.connections
    expect(connections?.trigger).toBeUndefined()
  })

  it('端口元数据不被连线关系污染(职责分离)', () => {
    const store = useRuleGraphStore()
    store.createNode(makeDef('yolo_model', ['detections']), { x: 0, y: 0 })
    store.createNode(makeDef('log_action', ['trigger']), { x: 200, y: 0 })
    const [source, target] = store.nodes
    store.addEdge({
      source: source.id,
      target: target.id,
      sourceHandle: 'detections',
      targetHandle: 'trigger',
    })

    // data.inputs 仍然是端口元数据数组(供 RuleNode 渲染手柄)
    expect(Array.isArray(target.data?.inputs)).toBe(true)
  })
})
