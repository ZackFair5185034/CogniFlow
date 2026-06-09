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
  onStart?: () => void
  onEnd?: () => void
}

export function useCogniFlowDrag(options: UseCogniFlowDragOptions) {
  const store = useRuleEngineStore()

  /** 防止 reinstall 和 drag 冲突 */
  let isDragging = false
  let zoomRef = 1

  let ctx: DragContext | null = null
  const cleanups: Array<() => void> = []

  /** 当前帧是否视为"点击"（位移 < 3px 算点击，不拖动） */
  let isClick = false

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
    cleanups.push(() => { d3Select(el).on('.drag', null) })
  }

  function onDragStart(event: DragEvent, el: HTMLElement) {
    const id = el.dataset.id
    if (!id) return
    const node = store.nodeById.get(id)
    if (!node) return
    isDragging = true
    isClick = true

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

      // 1) DOM transform → 节点立即跟随
      item.el.style.transform = `translate(${flowX}px, ${flowY}px)`

      // 2) mutate store node.position (同上值, 供 rAF 触发 VueFlow 边更新时读最新位置)
      const en = store.nodeById.get(item.id)
      if (en) en.position = { x: flowX, y: flowY }
    }

    // 3) rAF 节流替换数组引用 → VueFlow :nodes prop watcher 检测到新数组 →
    //    setNodes → createGraphNodes → reactiveState.nodes 更新 → getEdges 重算 → 边跟随
    //    注意: 不在此处 re-apply transform (被闭包捕获的 event 可能已过期, 写旧值反而导致节点跳动).
    //    node.position 已在第 2 步 mutate 到最新值, VueFlow 同步后 computedPosition 自动正确.
    //
    // === 性能优化：拖动过程不触发 VueFlow 整图 createGraphNodes ===
    // 真凶: 之前每帧 rAF 调 `store.nodes = [...store.nodes]` 触发 VueFlow
    //      80 节点 createGraphNodes + getEdges 80 边 path 重算 + 80 节点 vdom diff/patch
    //      + paint —— 总每帧 200ms (5fps), 肉眼卡顿.
    //      实测 rAFMax 200ms vs 关闭后 rAFMax 16ms (60fps 流畅).
    // 现在: 拖动过程只 DOM transform (步骤 1) + mutate markRaw.position (步骤 2),
    //      不触发 VueFlow 内部响应式链.
    //      边不实时跟随, dragend 一次性 setNodesPositions(updates, true)
    //      + triggerRef 让 VueFlow 一次性同步 (1 次, ~30ms).
    // 视觉差异: 边在拖动过程中保持原位, 拖完那一刻才跳到新位置.
    // 优化: setNodesPositions 内部 batched groupMove entry (O(N+M) vs O(N×M))
    //      + 一次 triggerRef 替代 80 次 write, 80 节点 GROUP 拖动 up 974ms → <50ms.
  }

  function onDragEnd(event: DragEvent, _el: HTMLElement) {
    if (!ctx) return
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
    // 会因 isHistoryPaused=true 跳过 history 写入, 6 次拖动只 2 个 entry.
    const dxFlow = dxScreen / z
    const dyFlow = dyScreen / z
    const updates = ctx.allDragged.map((item) => ({
      id: item.id,
      position: {
        x: item.startPos.x + dxFlow,
        y: item.startPos.y + dyFlow,
      },
    }))
    store.resumeHistory()
    store.setNodesPositions(updates, true)
    options.onEnd?.()

    isDragging = false
    ctx = null
  }

  function uninstallAll() {
    for (const c of cleanups) c()
    cleanups.length = 0
  }

  function reinstallAll() {
    if (isDragging) return
    const els = document.querySelectorAll<HTMLElement>('.vue-flow__node')
    if (els.length === 0) return  // DOM 还没渲染好, 等下次触发
    uninstallAll()
    els.forEach(installOnNode)
  }

  onMounted(() => { nextTick(() => reinstallAll()) })

  // 替换方式 watch: 框选后 store.nodes = newNodes (length 不变但数组引用变了) 也能触发重挂
  watch(
    () => store.nodes,
    () => { nextTick(() => reinstallAll()) },
  )

  onBeforeUnmount(() => { uninstallAll() })
}
