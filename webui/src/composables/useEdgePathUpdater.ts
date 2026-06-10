// -*- coding: utf-8 -*-
/**
 * useEdgePathUpdater - Tier 2 边增量更新器
 *
 * 核心问题: vue-flow 内部 getEdges 对所有 visible edges 全量重算 SVG path,
 * 80 节点 / 79 条边每帧 30-50ms, 是当前最大拖动卡顿源 (P0-1).
 *
 * 解决方案: 拖动期间绕开 vue-flow 响应式系统, 直接对受影响的 incident edges
 * 的 SVG <path> 元素写 d 属性, 复杂度 O(incident_edges) 而非 O(E_visible).
 * 通常 incident_edges 仅为 2-6 (5 节点框选).
 *
 * 工作流程:
 * 1. start: dragStart 时遍历 store.edges, 找 source/target 在拖动节点集中的边,
 *    缓存其 <path> 引用 + 边端点的逻辑坐标 (vue-flow 已经在 path 属性上
 *    算好了 sourceX/Y/targetX/Y, 这就是 d 属性的坐标系)
 * 2. update: 拖动每帧 (rAF 内) 重新计算 d 属性
 *    - source/target 端点新坐标 = (移动节点 newPosition) + (handle 在节点内偏移)
 *    - static 端点不变 (从 path 缓存读)
 * 3. clear: dragEnd 清空缓存, 恢复 vue-flow 接管
 *
 * 坐标系关键发现 (2026-06-08 debug):
 * - path.d 属性的坐标系 = vue-flow 的"逻辑坐标" (未应用 zoom, 未应用 viewport translate)
 * - sourceX = node.computedPosition.x + handle.x + handle.width (Position.Right)
 *   或        node.computedPosition.x + handle.x (Position.Left)
 * - handle 在节点内的偏移是固定的, 节点移动 (dx, dy) 时, sourceX/Y 整体 +dx, +dy
 * - 缓存边端点坐标 + 节点在拖动开始时的 position, 拖动时用:
 *   newSourceX = oldSourceX + (node.newPos.x - node.startPos.x)
 *
 * Bezier path 公式: M sx,sy C scx,scy tcx,tcy tx,ty
 * curvature=0.25 (vue-flow 默认)
 *
 * 读改写分离: 批量读 store/positions (N 次连续读) → 批量 setAttribute (N 次连续写),
 * 避免 layout thrash.
 */

import type { Edge } from '@vue-flow/core'
import { useRuleEngineStore } from '@/stores/ruleEngine'

interface CachedEdge {
  id: string
  /** DOM <path> 元素 (直接写 d 属性) */
  pathEl: SVGPathElement
  /** source 节点 ID */
  sourceNodeId: string
  /** target 节点 ID */
  targetNodeId: string
  /** dragStart 时, 边 source 端点的逻辑坐标 (= path.sourceX/Y) */
  sourceX: number
  sourceY: number
  /** dragStart 时, 边 target 端点的逻辑坐标 (= path.targetX/Y) */
  targetX: number
  targetY: number
  /** source 端点是否在拖动节点中 (true=需要随节点移动, false=静态) */
  sourceMoving: boolean
  /** target 端点是否在拖动节点中 */
  targetMoving: boolean
  /** source 端点在节点内的逻辑偏移 (handle 相对节点 position 的固定偏移) */
  sourceHandleOffsetX: number
  sourceHandleOffsetY: number
  /** target 端点在节点内的逻辑偏移 */
  targetHandleOffsetX: number
  targetHandleOffsetY: number
}

/**
 * 边增量更新器 (Tier 2)
 * @returns start/clear/update 函数
 */
export function useEdgePathUpdater() {
  const store = useRuleEngineStore()
  /** dragStart → dragEnd 期间缓存的受影响边 */
  const cache: CachedEdge[] = []
  /** 拖动节点 ID 集合 (用于更新时判断该边是 source/target 在动) */
  let draggedIds: Set<string> = new Set()
  /** 拖动节点 dragStart 时的 position, 用于计算 dx/dy */
  const startPositions = new Map<string, { x: number; y: number }>()
  /** dragStart 时的 zoom (保留接口) */
  let _zoom: number = 1

  /**
   * dragStart 时调用: 收集受影响边 + 缓存其 <path> 引用和端点快照
   * @param draggedNodeIds 当前拖动节点 ID 集合
   * @param currentZoom 拖动时的 zoom
   */
  function start(draggedNodeIds: string[], currentZoom: number) {
    clear()
    draggedIds = new Set(draggedNodeIds)
    _zoom = currentZoom
    void _zoom

    // 记录每个拖动节点 dragStart 时的 position
    for (const id of draggedNodeIds) {
      const node = store.nodes.find(n => n.id === id)
      if (node) startPositions.set(id, { x: node.position.x, y: node.position.y })
    }

    for (const edge of store.edges as Edge[]) {
      const sourceMoving = draggedIds.has(edge.source)
      const targetMoving = draggedIds.has(edge.target)
      if (!sourceMoving && !targetMoving) continue  // 不受影响

      // 找 <path> 元素: vue-flow BezierEdge 渲染 .vue-flow__edge-path
      const pathEl = document.querySelector<SVGPathElement>(
        `.vue-flow__edge[data-id="${edge.id}"] .vue-flow__edge-path`,
      )
      if (!pathEl) continue

      // vue-flow 已经在 path 属性上算好了真实逻辑坐标 sourceX/Y/targetX/Y
      const sourceX = parseFloat(pathEl.getAttribute('sourceX') || '0')
      const sourceY = parseFloat(pathEl.getAttribute('sourceY') || '0')
      const targetX = parseFloat(pathEl.getAttribute('targetX') || '0')
      const targetY = parseFloat(pathEl.getAttribute('targetY') || '0')

      // 算 handle 在节点内的逻辑偏移 (= 端点逻辑坐标 - 节点 position)
      // 节点移动时这个偏移不变
      const sourceNode = sourceMoving ? store.nodes.find(n => n.id === edge.source) : null
      const targetNode = targetMoving ? store.nodes.find(n => n.id === edge.target) : null

      const sourceHandleOffsetX = sourceNode ? sourceX - sourceNode.position.x : 0
      const sourceHandleOffsetY = sourceNode ? sourceY - sourceNode.position.y : 0
      const targetHandleOffsetX = targetNode ? targetX - targetNode.position.x : 0
      const targetHandleOffsetY = targetNode ? targetY - targetNode.position.y : 0

      cache.push({
        id: edge.id,
        pathEl,
        sourceNodeId: edge.source,
        targetNodeId: edge.target,
        sourceX, sourceY, targetX, targetY,
        sourceMoving, targetMoving,
        sourceHandleOffsetX, sourceHandleOffsetY,
        targetHandleOffsetX, targetHandleOffsetY,
      })
    }
  }

  /**
   * 拖动每帧调用: 用拖动节点的新 position 重算受影响边 d 属性
   * @param positions 当前拖动节点 position 集合 (id → {x, y})
   */
  function update(positions: Map<string, { x: number; y: number }>) {
    if (cache.length === 0) return

    // 阶段 1: 算所有 d (无 DOM 写入)
    const updates: Array<{ el: SVGPathElement; d: string }> = []
    for (const c of cache) {
      // 算新端点坐标
      let newSourceX = c.sourceX
      let newSourceY = c.sourceY
      let newTargetX = c.targetX
      let newTargetY = c.targetY

      if (c.sourceMoving) {
        const newPos = positions.get(c.sourceNodeId) || startPositions.get(c.sourceNodeId)
        if (newPos) {
          newSourceX = newPos.x + c.sourceHandleOffsetX
          newSourceY = newPos.y + c.sourceHandleOffsetY
        }
      }
      if (c.targetMoving) {
        const newPos = positions.get(c.targetNodeId) || startPositions.get(c.targetNodeId)
        if (newPos) {
          newTargetX = newPos.x + c.targetHandleOffsetX
          newTargetY = newPos.y + c.targetHandleOffsetY
        }
      }

      // Bezier 公式: 与 vue-flow bezier.ts 一致 (curvature=0.25)
      // calculateControlOffset: distance >= 0 → 0.5*distance; 否则 0.25*25*sqrt(-distance)
      // Position.Right (source): distance = tx - sx, offset = 0.5*max(0,dx) 或 c*25*sqrt(-dx)
      // Position.Left  (target): distance = sx - tx, offset = 0.5*max(0,-dx) 或 c*25*sqrt(dx)
      // (互斥, 不能相加!)
      const sourceDx = newTargetX - newSourceX
      const targetDx = newSourceX - newTargetX
      const sourceOffset = sourceDx >= 0
        ? 0.5 * sourceDx
        : 0.25 * 25 * Math.sqrt(-sourceDx)
      const targetOffset = targetDx >= 0
        ? 0.5 * targetDx
        : 0.25 * 25 * Math.sqrt(-targetDx)
      const scxNew = newSourceX + sourceOffset
      const scyNew = newSourceY
      const tcxNew = newTargetX - targetOffset
      const tcyNew = newTargetY

      const d = `M${newSourceX},${newSourceY} C${scxNew},${scyNew} ${tcxNew},${tcyNew} ${newTargetX},${newTargetY}`
      updates.push({ el: c.pathEl, d })
    }

    // 阶段 2: 批量写 d (N 次连续写, 不触发 layout thrash)
    for (const u of updates) {
      u.el.setAttribute('d', u.d)
    }
  }

  /**
   * dragEnd 调用: 清空缓存, 恢复 vue-flow 接管
   */
  function clear() {
    cache.length = 0
    draggedIds.clear()
    startPositions.clear()
    _zoom = 1
  }

  return { start, update, clear }
}
