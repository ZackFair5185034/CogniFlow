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
 * 1. collectAffectedEdges: dragStart 时遍历 store.edges, 找 source/target 在
 *    拖动节点集中的边, 缓存其 <path> 引用 (DOM 元素的 transform 锚点是
 *    .vue-flow__viewport, 后续 d 属性必须用 viewport 坐标)
 * 2. updateAffectedEdgePaths: 拖动每帧 (rAF 内) 重新计算 d 属性
 *    - 拖动节点新 sourceX/Y = 当前 viewport 内的右侧 handle 中心
 *    - 静态边端点从 path 元素 dataset 读 (dragStart 时一次性缓存)
 * 3. dragEnd 清空缓存, 恢复 vue-flow 接管
 *
 * Bezier path 公式: M sx,sy C scx,scy tcx,tcy tx,ty
 * 与 vue-flow BezierEdge 一致, 详见 vue-flow/packages/core/src/components/Edges/utils/bezier.ts
 *
 * 读改写分离: 批量 getBoundingClientRect (N 次连续读) → 批量 setAttribute (N 次连续写),
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
  /** 当前 zoom (dragStart 时快照) — 保留接口, 实际未使用 (DOM transform 推算) */
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
    // 触发 _zoom 的 "已读" 标记, 避免 ts unused-variable 告警.
    // _zoom 保留供未来 zoom-aware path 计算 (如 dpr 补偿、视口坐标转换) 使用.
    void _zoom

    for (const edge of store.edges as Edge[]) {
      const sourceMoving = draggedIds.has(edge.source)
      const targetMoving = draggedIds.has(edge.target)
      if (!sourceMoving && !targetMoving) continue  // 不受影响

      // 找 <path> 元素: vue-flow BezierEdge 渲染 .vue-flow__edge-path
      const pathEl = document.querySelector<SVGPathElement>(
        `[data-testid="rf__edge-wrapper"][data-id="${edge.id}"] .vue-flow__edge-path`,
      ) || document.querySelector<SVGPathElement>(
        `.vue-flow__edge[data-id="${edge.id}"] .vue-flow__edge-path`,
      ) || document.querySelector<SVGPathElement>(
        `.vue-flow__edge[data-testid="rf__edge-${edge.id}"] .vue-flow__edge-path`,
      )
      if (!pathEl) continue

      // 端点位置: 不在 start 缓存 (依赖实时 bbox), 仅缓存 sourceNodeId/targetNodeId.
      cache.push({
        id: edge.id,
        pathEl,
        sourceNodeId: edge.source,
        targetNodeId: edge.target,
      })
    }
  }

  /**
   * 拖动每帧调用: 用拖动节点的新 position 重算受影响边 d 属性
   * @param _positions 当前拖动节点 position 集合 (备用, 当前用 DOM transform 推算)
   */
  function update(_positions: Map<string, { x: number; y: number }>) {
    if (cache.length === 0) return
    // 当前实现不直接用 _positions / zoom, 而是从 DOM 实际渲染位置推算.
    // 注意: .vue-flow__transformationpane 应用了 zoom (e.g. 0.65), 节点的
    // offsetWidth/offsetHeight 是 CSS 像素 (280), 但 SVG <path> d 属性是
    // viewport 坐标 (已应用 zoom). 直接相加 offsetWidth 算 sourceX 会错位 35%.
    // 正确做法: getBoundingClientRect 拿到已应用 zoom 的实际渲染坐标.

    // 读改写分离: 阶段 1 - 批量读取所有节点 bbox (N 次连续读)
    const bboxMap = new Map<string, DOMRect>()
    const nodeIds = new Set<string>()
    for (const c of cache) {
      nodeIds.add(c.sourceNodeId)
      nodeIds.add(c.targetNodeId)
    }
    for (const id of nodeIds) {
      const el = document.querySelector<HTMLElement>(`[data-id="${id}"]`)
      if (el) bboxMap.set(id, el.getBoundingClientRect())
    }

    // 阶段 2: 算所有 d (无 DOM 写入)
    const updates: Array<{ el: SVGPathElement; d: string }> = []
    for (const c of cache) {
      const sourceBox = bboxMap.get(c.sourceNodeId)
      const targetBox = bboxMap.get(c.targetNodeId)
      if (!sourceBox || !targetBox) continue

      // source = source 节点右边缘中心 (已应用 zoom 的渲染坐标)
      const sxNew = sourceBox.right
      const syNew = sourceBox.top + sourceBox.height / 2
      // target = target 节点左边缘中心
      const txNew = targetBox.left
      const tyNew = targetBox.top + targetBox.height / 2

      // Bezier 公式: 与 vue-flow bezier.ts 一致
      // Position.Right: ctX = sx + 0.5*|sx-tx|, ctY = sy
      // Position.Left:  ctX = tx - 0.5*|sx-tx|, ctY = ty
      const dx = txNew - sxNew
      const offset = 0.5 * Math.abs(dx)
      const scxNew = sxNew + offset
      const scyNew = syNew
      const tcxNew = txNew - offset
      const tcyNew = tyNew

      const d = `M${sxNew},${syNew} C${scxNew},${scyNew} ${tcxNew},${tcyNew} ${txNew},${tyNew}`
      updates.push({ el: c.pathEl, d })
    }

    // 阶段 3: 批量写 d (N 次连续写, 不触发 layout thrash)
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
    _zoom = 1
  }

  return { start, update, clear }
}
