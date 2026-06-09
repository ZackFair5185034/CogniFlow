// -*- coding: utf-8 -*-
/**
 * useCogniFlowDrag - 路径 B: 应用层自研拖动 (绕开 vue-flow 内部 useDrag)
 *
 * 核心设计:
 * - 拖动期间: 直接改节点 wrapper DOM transform, 0 次响应式写入,
 *   同时 mutate node.position (shallowRef + markRaw, 不触发响应式),
 *   rAF 节流 triggerRef 让边跟随 (~16fps).
 * - drag-end: 一次性 setNodesPositions + recordMoveHistory.
 * - 多节点联动: dragstart 收集所有 .selected 节点.
 */

import { onBeforeUnmount, onMounted, watch, nextTick, triggerRef, type Ref } from 'vue'
import { select as d3Select } from 'd3-selection'
import { drag as d3Drag, type D3DragEvent } from 'd3-drag'
import { useRuleEngineStore, type RuleNodeData } from '@/stores/ruleEngine'
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

  /** 防止 reinstall 和 drag 冲突 */
  let isDragging = false
  let zoomRef = 1

  let ctx: DragContext | null = null
  /** 已挂载节点 -> 卸载函数,实现增量挂载/卸载 (Tier 1 优化)
   *  替代原 cleanups[]: store.nodes 变化时只 diff 新增/移除的节点,
   *  避免 N 节点重新挂载 d3-drag handler 的 O(N) 开销 */
  const installedMap = new Map<HTMLElement, () => void>()

  /** 当前帧是否视为"点击"（位移 < 3px 算点击，不拖动） */
  let isClick = false

  /** rAF 节流: 拖动 mousemove 频率远高于 rAF, 防止同一帧内多次改 position */
  let rafId: number | null = null
  let rafPending = false

  function installOnNode(el: HTMLElement) {
    const dragHandler = d3Drag<HTMLElement, unknown>()
      .filter((event: MouseEvent) => {
        if (event.button) return false
        // 不拦截 Handle/连线/标签/展开按钮等交互元素, 保障连线/编辑操作:
        // - .nodrag: VueFlow 标准拖拽排除 class (Handle 默认携带)
        // - .vue-flow__handle: 连接点本身
        // - .vue-flow__edge: 边上的交互元素
        // - .node-expand-btn: 节点内配置展开按钮 (d3-drag 会劫持 click 事件,
        //                       必须从 mousedown 起就放行, 否则按钮 @click 不触发)
        const target = event.target as HTMLElement | null
        if (!target) return false
        if (target.closest('.nodrag')) return false
        if (target.closest('.vue-flow__handle')) return false
        if (target.closest('.vue-flow__edge')) return false
        if (target.closest('.node-expand-btn')) return false
        return true
      })
      .on('start', (event: DragEvent) => onDragStart(event, el))
      .on('drag', (event: DragEvent) => onDrag(event, el))
      .on('end', (event: DragEvent) => onDragEnd(event, el))
    d3Select(el).call(dragHandler)
    installedMap.set(el, () => { d3Select(el).on('.drag', null) })
  }

  /** 增量同步 d3-drag handler: 仅挂载新增节点, 卸载已移除节点 (Tier 1 优化)
   *  替代原 reinstallAll: 100 节点 add/remove 1 个时从 O(N) 降到 O(1) */
  function syncDragHandlers() {
    if (isDragging) return
    const els = document.querySelectorAll<HTMLElement>('.vue-flow__node')
    if (els.length === 0) return
    const live = new Set<HTMLElement>(Array.from(els))
    // 卸载已不在 DOM 的旧节点
    for (const [el, cleanup] of installedMap) {
      if (!live.has(el)) {
        cleanup()
        installedMap.delete(el)
      }
    }
    // 挂载新节点 (installOnNode 内部幂等)
    live.forEach(installOnNode)
  }

  function onDragStart(event: DragEvent, el: HTMLElement) {
    const id = el.dataset.id
    if (!id) return
    const node = store.nodeById.get(id)
    if (!node) return
    isDragging = true
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

    // 2) rAF 节流改 VueFlow 内部 reactive GraphNode.position → 触发 getEdges 80 边 path 重算 → 边跟随
    //    不调 setNodes / createGraphNodes, 绕过 80 节点 vdom diff/patch.
    //    VueFlow NodeWrapper 内部 watch([node.position.x, node.position.y]) 触发 computedPosition
    //    更新, 同步设 el.style.transform (跟步骤 1 一致, 不会跳).
    if (rafPending) return
    rafPending = true
    rafId = requestAnimationFrame(() => {
      rafPending = false
      if (!ctx) return  // 拖动可能已结束
      for (const item of ctx.allDragged) {
        const flowX = item.startPos.x + dxScreen / z
        const flowY = item.startPos.y + dyScreen / z
        const flowNode = options.findFlowNode(item.id)
        if (flowNode && flowNode.position) {
          // 改 reactive 包装的 position object, 触发 NodeWrapper watch + getEdges
          flowNode.position.x = flowX
          flowNode.position.y = flowY
        }
      }
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
        store.selectNode(primary.id)
        triggerRef(options.nodesRef)
      }
      store.resumeHistory()
      options.onEnd?.()
      isDragging = false
      ctx = null
      return
    }

    // === 拖动结束: 写回 store ===
    // 关键顺序: 先 resumeHistory 再 setNodesPositions —— 否则 setNodesPositions
    // 内部 `if (recordHistory && !isHistoryPaused.value && moves.length > 0)`
    // 会因 isHistoryPaused=true 跳过 history 写入.
    //
    // rawWrite=true: 用 toRaw(node.position) 绕过 Vue Proxy 直接写原始对象,
    // 零 watcher 触发, 零微任务调度. 拖动期间 flowNode.position 已实时同步
    // 到 VueFlow 内部, store 只做持久化/history. undo/redo 走 reactive 路径
    // (rawWrite=false) 正常触发 triggerRef 重建.
    const dxFlow = dxScreen / z
    const dyFlow = dyScreen / z
    const updates = ctx.allDragged.map((item) => ({
      id: item.id,
      position: {
        x: item.startPos.x + dxFlow,
        y: item.startPos.y + dyFlow,
      },
    }))
    isDragging = false
    ctx = null
    store.resumeHistory()
    store.setNodesPositions(updates, true, true, true)  // recordHistory, skipTrigger, rawWrite
    options.onEnd?.()
  }

  function uninstallAll() {
    for (const cleanup of installedMap.values()) cleanup()
    installedMap.clear()
  }

  onMounted(() => { nextTick(() => syncDragHandlers()) })

  // 替换方式 watch: 框选后 store.nodes = newNodes (length 不变但数组引用变了) 也能触发增量同步
  watch(
    () => store.nodes,
    () => { nextTick(() => syncDragHandlers()) },
  )

  onBeforeUnmount(() => { uninstallAll() })
}
