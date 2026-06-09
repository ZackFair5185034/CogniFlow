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
  const cleanups: Array<() => void> = []

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
    cleanups.push(() => { d3Select(el).on('.drag', null) })
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
    //
    // === 性能修复 (二次拖动卡顿真凶) ===
    // 实测 setNodesPositions(5 nodes) 内部 triggerRef 同步 flush 跑 200ms,
    // (VueFlow 80 节点 vdom diff/patch + 80 边 path 重算 + 响应式链).
    // 慢在 mouseup 之后, 用户立刻开始第二次拖动时 200ms 同步阻塞事件循环,
    // 导致 mousedown 响应延迟, 视觉上是"二次拖动卡顿".
    //
    // 修法: 异步 setNodesPositions (nextTick), mouseup 同步链立刻返回,
    // 200ms store 同步在后台跑, 不阻塞第二次拖动.
    // 安全: history 写入延后一次微任务, 不影响 undo/redo 正确性.
    const dxFlow = dxScreen / z
    const dyFlow = dyScreen / z
    const updates = ctx.allDragged.map((item) => ({
      id: item.id,
      position: {
        x: item.startPos.x + dxFlow,
        y: item.startPos.y + dyFlow,
      },
    }))
    // 同步 reset state (isDragging/ctx), 让 d3-drag 立刻可以接下一次 mousedown
    isDragging = false
    ctx = null
    store.resumeHistory()
    // 异步执行 setNodesPositions (含 triggerRef), 不阻塞 mouseup 链
    nextTick(() => {
      store.setNodesPositions(updates, true)
    })
    options.onEnd?.()
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
