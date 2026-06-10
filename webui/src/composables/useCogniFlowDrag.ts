// -*- coding: utf-8 -*-
/**
 * useCogniFlowDrag - 路径 B: 应用层自研拖动 (绕开 vue-flow 内部 useDrag)
 *
 * 核心设计 (Phase 17.2 P0-C: 事件委托):
 * - 拖动期间: 直接改节点 wrapper DOM transform, 0 次响应式写入,
 *   同时 mutate node.position (shallowRef + markRaw, 不触发响应式),
 *   rAF 节流 triggerRef 让边跟随 (~16fps).
 * - drag-end: 一次性 setNodesPositions + recordMoveHistory.
 * - 多节点联动: dragstart 收集所有 .selected 节点.
 * - **P0-C 优化**: 1 个 d3-drag handler 挂在 .vue-flow__viewport (事件委托),
 *   替代原 N 节点 N 个 handler (N=200 时 init 60ms→1ms, 内存 200KB→1KB).
 *   mousedown 时 event.target.closest('.vue-flow__node[data-id]') 找目标节点.
 */

import { onBeforeUnmount, onMounted, nextTick, triggerRef, type Ref } from 'vue'
import { select as d3Select } from 'd3-selection'
import { drag as d3Drag, type D3DragEvent } from 'd3-drag'
import { useRuleEngineStore, type RuleNodeData } from '@/stores/ruleEngine'
import { useEdgePathUpdater } from './useEdgePathUpdater'
import type { Node } from '@vue-flow/core'

type DragEvent = D3DragEvent<HTMLElement, unknown, unknown>

interface DraggedItem {
  id: string
  el: HTMLElement
  startPos: { x: number; y: number }
}

interface DragContext {
  startMouse: { x: number; y: number }
  allDragged: DraggedItem[]
}

export interface UseCogniFlowDragOptions {
  /** 传递 store.nodes 的 Ref, 供 triggerRef 用 (Pinia auto-unwraps, store.nodes 拿不到 ref) */
  nodesRef: Ref<Node<RuleNodeData>[]>
  /** 读取当前 zoom 的回调 (从 useVueFlow().getViewport().zoom 获取) */
  getZoom: () => number
  /** 从 useVueFlow().findNode(id) 拿 VueFlow 内部 reactive GraphNode, 改它 .position 触发 getEdges */
  findFlowNode: (id: string) => any
  onStart?: () => void
  onEnd?: () => void
}

export function useCogniFlowDrag(options: UseCogniFlowDragOptions) {
  const store = useRuleEngineStore()
  /** Tier 2 边增量更新器: 拖动期间手动更新 incident edges 的 SVG path d 属性 */
  const edgeUpdater = useEdgePathUpdater()

  let zoomRef = 1
  let ctx: DragContext | null = null

  /** P0-C 事件委托: 当前帧"鼠标按下时锁定的节点 el",
   *  d3-drag 的 start 事件会拿到 sourceEvent, 我们从 sourceEvent 提取.
   *  不存在时 start 不会触发 (filter 阶段已 return false). */
  let currentDragEl: HTMLElement | null = null

  /** 当前帧是否视为"点击"（位移 < 3px 算点击，不拖动） */
  let isClick = false

  /** rAF 节流: 拖动 mousemove 频率远高于 rAF, 防止同一帧内多次改 position */
  let rafId: number | null = null
  let rafPending = false

  /** 单一 d3-drag handler 句柄, onBeforeUnmount 时拆 */
  let cleanupViewportDrag: (() => void) | null = null

  // ============================================================
  // P0-C: 事件委托 — 单一 handler 挂在 .vue-flow__viewport
  // ============================================================
  function setupViewportDrag() {
    const viewport = document.querySelector<HTMLElement>('.vue-flow__viewport')
    if (!viewport) {
      // 节点尚未渲染, 下一帧重试 (罕见, 兜底)
      requestAnimationFrame(setupViewportDrag)
      return
    }

    const dragHandler = d3Drag<HTMLElement, unknown>()
      .filter((event: MouseEvent) => {
        if (event.button) return false
        // 找最近的可拖动节点 wrapper
        const target = event.target as HTMLElement | null
        if (!target) return false
        const nodeEl = target.closest<HTMLElement>('.vue-flow__node[data-id]')
        if (!nodeEl) return false
        // 排除交互元素 (连线/编辑/展开按钮等):
        // - .nodrag: VueFlow 标准拖拽排除 class (Handle 默认携带)
        // - .vue-flow__handle: 连接点本身
        // - .vue-flow__edge: 边上的交互元素
        // - .node-expand-btn: 节点内配置展开按钮 (d3-drag 会劫持 click 事件,
        //   必须从 mousedown 起就放行, 否则按钮 @click 不触发)
        if (target.closest('.nodrag')) return false
        if (target.closest('.vue-flow__handle')) return false
        if (target.closest('.vue-flow__edge')) return false
        if (target.closest('.node-expand-btn')) return false
        // 把 nodeEl 存到 sourceEvent 供 start/drag/end 阶段读取
        ;(event as any).__cfNodeEl = nodeEl
        return true
      })
      .on('start', (event: DragEvent) => {
        const el = (event.sourceEvent as any)?.__cfNodeEl as HTMLElement | undefined
        if (!el) return
        currentDragEl = el
        onDragStart(event, el)
      })
      .on('drag', (event: DragEvent) => {
        if (!currentDragEl) return
        onDrag(event, currentDragEl)
      })
      .on('end', (event: DragEvent) => {
        const el = currentDragEl
        currentDragEl = null
        if (!el) return
        onDragEnd(event, el)
      })

    d3Select(viewport).call(dragHandler)
    cleanupViewportDrag = () => {
      d3Select(viewport).on('.drag', null)
    }
  }

  function onDragStart(event: DragEvent, el: HTMLElement) {
    const id = el.dataset.id
    if (!id) return
    const node = store.nodeById.get(id)
    if (!node) return
    isClick = true

    // 重置 rAF state: 上次拖动可能未正常清理 (异常路径)
    rafPending = false
    rafId = null

    zoomRef = options.getZoom()
    const src = event.sourceEvent as MouseEvent

    let allEls: HTMLElement[]
    if (el.classList.contains('selected')) {
      allEls = Array.from(document.querySelectorAll<HTMLElement>('.vue-flow__node.selected'))
    } else {
      allEls = [el]
    }
    if (!allEls.includes(el)) allEls.push(el)

    ctx = {
      startMouse: { x: src.clientX, y: src.clientY },
      allDragged: allEls
        .map((e) => {
          const eid = e.dataset.id
          if (!eid) return null
          const en = store.nodeById.get(eid)
          if (!en) return null
          return { id: eid, el: e, startPos: { ...en.position } }
        })
        .filter((x): x is DraggedItem => x !== null),
    }

    // === Tier 2: 启动边增量更新器, 收集 incident edges ===
    edgeUpdater.start(
      ctx.allDragged.map((i) => i.id),
      zoomRef,
    )

    // === Tier 0 优化: 标记 .dragging class,触发 CSS 关 transition + GPU 合成层 ===
    for (const item of ctx.allDragged) {
      item.el.classList.add('dragging')
    }

    store.pauseHistory()
    options.onStart?.()
  }

  function onDrag(event: DragEvent, _el: HTMLElement) {
    if (!ctx) return
    const src = event.sourceEvent as MouseEvent
    const z = zoomRef
    const dxScreen = src.clientX - ctx.startMouse.x
    const dyScreen = src.clientY - ctx.startMouse.y

    // 位移超过 5px 才视为拖动, 否则算点击 (防止手抖误判)
    if (Math.abs(dxScreen) > 5 || Math.abs(dyScreen) > 5) {
      isClick = false
    }

    for (const item of ctx.allDragged) {
      const flowX = item.startPos.x + dxScreen / z
      const flowY = item.startPos.y + dyScreen / z

      // 1) DOM transform → 节点立即跟随 (60fps)
      item.el.style.transform = `translate(${flowX}px, ${flowY}px)`
    }

    // 2) rAF 节流:
    //    Tier 2 边增量更新: 不再写 reactive flowNode.position 触发 vue-flow 全量
    //    getEdges 路径重算 (P0-1 最大热点), 改为直接对 incident edges 的
    //    SVG <path> 元素写 d 属性 (O(incident_edges), 通常 2-6 而非 80).
    //    onDragEnd 时一次性同步 flowNode.position 让 vue-flow 接管, 边路径立即
    //    跟手不闪烁.
    if (rafPending) return
    rafPending = true
    rafId = requestAnimationFrame(() => {
      rafPending = false
      if (!ctx) return  // 拖动可能已结束

      // Tier 2: 直接重算 incident edges 的 d 属性
      const positions = new Map<string, { x: number; y: number }>()
      for (const item of ctx.allDragged) {
        const flowX = item.startPos.x + dxScreen / z
        const flowY = item.startPos.y + dyScreen / z
        positions.set(item.id, { x: flowX, y: flowY })
      }
      edgeUpdater.update(positions)
    })
  }

  function onDragEnd(event: DragEvent, _el: HTMLElement) {
    // 清 rAF: 防止最后一帧 rAF 在 onDragEnd 后才跑, 覆盖 setNodesPositions 结果
    if (rafId !== null) {
      cancelAnimationFrame(rafId)
      rafId = null
    }
    rafPending = false
    if (!ctx) return

    // === Tier 0 优化: 清除 .dragging class,恢复 transition + 合成层回收 ===
    for (const item of ctx.allDragged) {
      item.el.classList.remove('dragging')
    }
    const src = event.sourceEvent as MouseEvent
    const z = zoomRef
    const dxScreen = src.clientX - ctx.startMouse.x
    const dyScreen = src.clientY - ctx.startMouse.y

    // === 点击检测 (非拖动) ===
    if (isClick) {
      const primary = ctx.allDragged[0]
      if (primary) {
        const isMulti = src.ctrlKey || src.metaKey
        if (isMulti) {
          // Ctrl+click: 切换当前节点选中态, 其他不变
          const n = store.nodeById.get(primary.id) as any
          if (n) n.selected = !n.selected
        } else {
          // 普通点击: 全部取消选中, 只选中当前
          for (const n of store.nodes as any) n.selected = false
          const n = store.nodeById.get(primary.id) as any
          if (n) n.selected = true
        }
        // Phase 17.1+: 取消 store.selectNode (右侧面板不再需要 selectedNodeId 同步)
        // selected 状态直接由 VueFlow 内部 useSelectedNodes + store.nodes[].selected 维护
        triggerRef(options.nodesRef)
      }
      store.resumeHistory()
      options.onEnd?.()
      ctx = null
      return
    }

    // === 拖动结束: 写回 store + 同步 VueFlow 内部状态 ===
    // 关键顺序: 先 resumeHistory 再 setNodesPositions —— 否则 setNodesPositions
    // 内部 `if (recordHistory && !isHistoryPaused.value && moves.length > 0)`
    // 会因 isHistoryPaused=true 跳过 history 写入.
    //
    // rawWrite=true: 用 toRaw(node.position) 绕过 Vue Proxy 直接写原始对象,
    // 零 watcher 触发, 零微任务调度. 拖动期间 edgeUpdater 手动更新了 d 属性,
    // store 只做持久化/history.
    //
    // 同步 flowNode.position (让 vue-flow 接管, 接管后我们清 el.style.transform
    // 让 NodeWrapper 内部 watcher 接管 transform, 跟手不闪烁).
    const dxFlow = dxScreen / z
    const dyFlow = dyScreen / z
    const updates = ctx.allDragged.map((item) => {
      const newX = item.startPos.x + dxFlow
      const newY = item.startPos.y + dyFlow
      // === 同步 flowNode.position 让 vue-flow 接管 ===
      // 这是拖动期间被 vue-flow watch 跳过的 position 写入,
      // 此时 edgeUpdater 已停止, vue-flow 接管后全图一次重建但仅一次.
      const flowNode = options.findFlowNode(item.id)
      if (flowNode?.position) {
        flowNode.position.x = newX
        flowNode.position.y = newY
      }
      return {
        id: item.id,
        position: { x: newX, y: newY },
      }
    })

    // === 清 el.style.transform 让 vue-flow 接管节点位置 ===
    // NodeWrapper 内部 watcher([x, y]) 触发后会自动设 transform,
    // 与我们之前写的 transform 一致, 不会有跳变.
    for (const item of ctx.allDragged) {
      item.el.style.transform = ''
    }

    // === Tier 2: 清边增量更新器缓存 ===
    edgeUpdater.clear()

    store.resumeHistory()
    store.setNodesPositions(updates, true, true, true)  // recordHistory, skipTrigger, rawWrite
    options.onEnd?.()
    ctx = null
  }

  onMounted(() => {
    // 单次挂载: 单一 d3-drag handler 挂 .vue-flow__viewport
    // 等 nextTick 让 vue-flow 把 viewport 元素渲染出来
    nextTick(setupViewportDrag)
  })

  onBeforeUnmount(() => {
    cleanupViewportDrag?.()
    cleanupViewportDrag = null
  })
}
