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
  /** source 节点 ID — 拖动中端点 (新 position); 或非拖动端 (null = 用 path 起点) */
  sourceNodeId: string
  /** target 节点 ID — 拖动中端点 (新 position); 或非拖动端 (null = 用 path 终点) */
  targetNodeId: string
  /** source 端点 (node 坐标系) — dragStart 时一次性快照 */
  sourceX: number
  sourceY: number
  sourcePosition: 'left' | 'right' | 'top' | 'bottom'
  /** target 端点 (node 坐标系) — dragStart 时一次性快照 */
  targetX: number
  targetY: number
  targetPosition: 'left' | 'right' | 'top' | 'bottom'
  /** 当前 zoom (dragStart 时取, 拖动期间 zoom 不变则可用) */
  zoom: number
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

      // 端点快照: 用 .vue-flow__handle DOM getBoundingClientRect 算 viewport 坐标
      // (但坐标系是 viewport, d 属性也要写 viewport 坐标, OK)
      const sourceHandle = document.querySelector<HTMLElement>(
        `[data-id="${edge.source}"] .vue-flow__handle-right`,
      )
      const targetHandle = document.querySelector<HTMLElement>(
        `[data-id="${edge.target}"] .vue-flow__handle-left`,
      )
      if (!sourceHandle || !targetHandle) continue

      const viewportEl = document.querySelector('.vue-flow__viewport') as HTMLElement
      if (!viewportEl) continue

      // viewport 坐标 = (handle 的 client 坐标 - viewport 的 client 坐标) / zoom
      // 但更简单: 直接用 path 元素当前 d 属性, 解析 M/C 命令拿端点
      // Bezier: M sx,sy C scx,scy tcx,tcy tx,ty
      const d = pathEl.getAttribute('d') || ''
      const m = d.match(/M\s*([\d.-]+)[\s,]+([\d.-]+)\s*C\s*([\d.-]+)[\s,]+([\d.-]+)\s+([\d.-]+)[\s,]+([\d.-]+)\s+([\d.-]+)[\s,]+([\d.-]+)/)
      if (!m) continue
      const [_, sx, sy, _scx, _scy, _tcx, _tcy, tx, ty] = m

      cache.push({
        id: edge.id,
        pathEl,
        sourceNodeId: edge.source,
        targetNodeId: edge.target,
        sourceX: parseFloat(sx),
        sourceY: parseFloat(sy),
        sourcePosition: 'right',
        targetX: parseFloat(tx),
        targetY: parseFloat(ty),
        targetPosition: 'left',
        zoom: currentZoom,
      })
    }
  }

  /**
   * 拖动每帧调用: 用拖动节点的新 position 重算受影响边 d 属性
   * @param _positions 当前拖动节点 position 集合 (备用, 当前用 DOM transform 推算)
   */
  function update(_positions: Map<string, { x: number; y: number }>) {
    if (cache.length === 0) return
    // 当前实现不直接用 _positions / zoom, 而是从 DOM el.style.transform 推算
    // (translate(flowX, flowY) 是 onDrag 写的, 与 sourceX/Y 计算自洽)

    // 读改写分离: 阶段 1 - 算所有 d (无 DOM 写入)
    const updates: Array<{ el: SVGPathElement; d: string }> = []
    for (const c of cache) {
      // 移动端点: 拖动节点的 sourceX = node.x + nodeWidth, sourceY = node.y + nodeHeight/2
      // 静态端点: 用 cache 里的 sourceX/sourceY (源端在动的边, 即 source 是被拖动节点, 则 source 端要更新; 反之亦然)
      // 简化: source 端 = source 节点右侧 handle; target 端 = target 节点左侧 handle
      // 拖动节点的 handle 位置 = 它的新 position + 节点宽/2

      // 关键: 不知道节点宽/高, 但可以通过 transform 算出 (el.style.transform 写的是 translate(x,y))
      // 节点 element: data-id="nodeId", 拖动期间 el.style.transform = "translate(flowX, flowY)"

      // 用 cache 里的起始 sourceX/Y + 增量 dx/dy 计算新 sourceX/Y
      // dx/dy 来自拖动节点 position 差值 (新 - 起始)
      // 但 cache 里的 sourceX/Y 是当前 d 属性的端点, 不一定是 dragStart 时的值
      // 实际上, 边 path 在 dragStart 之后被 vue-flow 同步重算过 (dragend 之间)
      // 简单方案: 直接读每个 source/target 节点的当前 viewport 内位置

      // 取 source 节点和 target 节点
      const sourceEl = document.querySelector<HTMLElement>(`[data-id="${c.sourceNodeId}"]`)
      const targetEl = document.querySelector<HTMLElement>(`[data-id="${c.targetNodeId}"]`)
      if (!sourceEl || !targetEl) continue

      // 节点的 transform 样式: 我们 onDrag 已经写了 translate(flowX, flowY)
      const sourceTransform = sourceEl.style.transform
      const targetTransform = targetEl.style.transform

      // 解析: translate(x, y)
      const sm = sourceTransform.match(/translate\(([\d.-]+)px,\s*([\d.-]+)px\)/)
      const tm = targetTransform.match(/translate\(([\d.-]+)px,\s*([\d.-]+)px\)/)
      if (!sm || !tm) continue

      const sxNew = parseFloat(sm[1]) + sourceEl.offsetWidth  // source = 节点右边缘
      const syNew = parseFloat(sm[2]) + sourceEl.offsetHeight / 2
      const txNew = parseFloat(tm[1])                       // target = 节点左边缘
      const tyNew = parseFloat(tm[2]) + targetEl.offsetHeight / 2

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
    _zoom = 1
  }

  return { start, update, clear }
}
