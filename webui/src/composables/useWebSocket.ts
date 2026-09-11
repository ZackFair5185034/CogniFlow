// -*- coding: utf-8 -*-
/**
 * useWebSocket - 统一 WebSocket 入口 composable。
 *
 * 设计目标 (P1-B, 2026-09-11):
 * - 收口 5 处 view 中的 `new WebSocket(...)` 直调
 * - 自动断线重连 (可配置指数退避或固定延迟)
 * - 组件卸载自动 close (避免内存泄漏)
 * - 消息回调统一 JSON.parse, 类型安全
 *
 * 不替代的内容:
 * - streamClient.ts (二进制流式推理协议, 帧元数据 + JPEG 字节合并)
 *   该客户端保留其独立协议和重连逻辑, useWebSocket 仅覆盖文本 JSON 类连接。
 */

import { ref, onUnmounted, type Ref } from 'vue'

/** WebSocket 当前状态。reconnecting 表示已断开但正在等待下次重连。 */
export type WebSocketStatus = 'connecting' | 'open' | 'closed' | 'reconnecting'

export interface UseWebSocketOptions<TMessage = unknown> {
  /**
   * WebSocket URL。允许传函数以便动态解析 (例如包含执行 ID)。
   * 相对路径会自动按当前页面协议/host 补全为 ws:// 或 wss://。
   */
  url: string | (() => string)
  /** 同原生 WebSocket constructor 第二参 */
  protocols?: string | string[]
  /** 是否在 composable 初始化时立即连接。默认 true。需要手动 connect 时传 false。 */
  autoConnect?: boolean
  /**
   * 是否断线重连。默认 true。
   * - false: 断开后不再重连
   * - true: 一直重连 (受 maxReconnectAttempts 限制)
   * - () => boolean: 每次 onclose 触发时动态判断, 返回 true 才重连
   *   (例如规则引擎: 仅当 executionStatus === 'running' 时重连)
   */
  reconnect?: boolean | (() => boolean)
  /**
   * 重连延迟 (毫秒)。
   * - number: 固定延迟 (默认 3000)
   * - (attempt: number) => number: 动态计算, 支持指数退避
   *   例如: (n) => Math.min(30000, 1000 * 2 ** n) → 1s, 2s, 4s, 8s ... 上限 30s
   */
  reconnectDelay?: number | ((attempt: number) => number)
  /** 最大重连尝试次数。默认 10。设为 Infinity 表示无限重连 (直到主动 close 或组件卸载)。 */
  maxReconnectAttempts?: number
  /** 收到消息 (已 JSON.parse)。raw 参数可访问 MessageEvent 原始事件。 */
  onMessage?: (msg: TMessage, raw: MessageEvent) => void
  /** WebSocket.onopen。连接建立后触发 (可用于发送 subscribe 等初始化消息)。 */
  onOpen?: (ev: Event) => void
  /** WebSocket.onclose。intentional close 或组件卸载触发的关闭也会回调。 */
  onClose?: (ev: CloseEvent) => void
  /** WebSocket.onerror。 */
  onError?: (ev: Event) => void
}

export interface UseWebSocketReturn<TMessage = unknown> {
  /** 当前连接状态 */
  status: Ref<WebSocketStatus>
  /** 最近一条已解析的消息 */
  data: Ref<TMessage | null>
  /**
   * 发送消息。
   * - 若连接尚未 open, 返回 false
   * - 对象会被 JSON.stringify; 字符串原样发送
   */
  send: (data: string | object) => boolean
  /**
   * 主动关闭 (标记为 intentional, 不再重连)。
   * 适用于: 任务完成 / 弹窗关闭 / 用户主动取消。
   */
  close: () => void
  /**
   * 主动连接 (会重置重连计数, 关闭已有连接后重新建立)。
   * 适用于: autoConnect:false 场景下首次连接, 或重置 URL 后重连。
   */
  connect: () => void
}

/**
 * P1-B (2026-09-11): 统一 WebSocket 入口 composable。
 *
 * 典型用法:
 * ```ts
 * const { status, send } = useWebSocket<MyMsg>({
 *   url: '/ws/training',
 *   onMessage: (msg) => { /* ... *\/ },
 * })
 * ```
 *
 * 动态 URL + 条件重连 (规则引擎实时执行):
 * ```ts
 * const { connect, close, send } = useWebSocket<ExecMsg>({
 *   url: () => `/ws/rule-execution`,
 *   reconnect: () => executionStatus.value === 'running' && !!executionId.value,
 *   onOpen: () => send({ action: 'subscribe', execution_id: executionId.value }),
 * })
 * ```
 */
export function useWebSocket<TMessage = unknown>(
  options: UseWebSocketOptions<TMessage>,
): UseWebSocketReturn<TMessage> {
  const {
    url,
    protocols,
    autoConnect = true,
    reconnect = true,
    reconnectDelay = 3000,
    maxReconnectAttempts = 10,
    onMessage,
    onOpen,
    onClose,
    onError,
  } = options

  const status = ref<WebSocketStatus>('closed')
  // cast 以避免 Vue 的 UnwrapRef 干扰 TMessage 内部 ref 的展开
  const data = ref<TMessage | null>(null) as Ref<TMessage | null>

  let ws: WebSocket | null = null
  let reconnectAttempts = 0
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null
  /** 主动调用 close() 后置 true, 阻止重连 */
  let intentionalClose = false
  /** onUnmounted 后置 true, 阻止重连 + 标记状态 closed */
  let unmounted = false

  function resolveUrl(): string {
    return typeof url === 'function' ? url() : url
  }

  function computeDelay(): number {
    return typeof reconnectDelay === 'function'
      ? reconnectDelay(reconnectAttempts)
      : reconnectDelay
  }

  function shouldReconnect(): boolean {
    if (intentionalClose || unmounted) return false
    return typeof reconnect === 'function' ? reconnect() : reconnect
  }

  function clearReconnectTimer(): void {
    if (reconnectTimer !== null) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
  }

  function connect(): void {
    clearReconnectTimer()
    intentionalClose = false
    if (ws) {
      try {
        ws.close()
      } catch {
        // 忽略已关闭的 ws
      }
      ws = null
    }

    const target = resolveUrl()
    if (!target) {
      // URL 为空 (例如 exportId 尚未设置), 跳过本次连接
      status.value = 'closed'
      return
    }

    status.value = reconnectAttempts > 0 ? 'reconnecting' : 'connecting'
    try {
      ws = new WebSocket(buildAbsoluteWsUrl(target), protocols)
    } catch (e) {
      console.error('[useWebSocket] 创建连接失败', e)
      status.value = 'closed'
      return
    }

    ws.onopen = (ev) => {
      reconnectAttempts = 0
      status.value = 'open'
      onOpen?.(ev)
    }

    ws.onmessage = (ev) => {
      let parsed: TMessage
      try {
        parsed = typeof ev.data === 'string'
          ? (JSON.parse(ev.data) as TMessage)
          : (ev.data as unknown as TMessage)
      } catch {
        // 非 JSON 文本, 原样传递
        parsed = ev.data as unknown as TMessage
      }
      data.value = parsed
      onMessage?.(parsed, ev)
    }

    ws.onerror = (ev) => {
      onError?.(ev)
    }

    ws.onclose = (ev) => {
      ws = null
      if (intentionalClose || unmounted) {
        status.value = 'closed'
        onClose?.(ev)
        return
      }
      if (shouldReconnect() && reconnectAttempts < maxReconnectAttempts) {
        reconnectAttempts += 1
        status.value = 'reconnecting'
        reconnectTimer = setTimeout(connect, computeDelay())
      } else {
        status.value = 'closed'
        onClose?.(ev)
      }
    }
  }

  function close(): void {
    clearReconnectTimer()
    intentionalClose = true
    if (ws) {
      try {
        ws.close()
      } catch {
        // 忽略
      }
      ws = null
    }
    status.value = 'closed'
  }

  function send(payload: string | object): boolean {
    if (ws?.readyState !== WebSocket.OPEN) return false
    ws.send(typeof payload === 'string' ? payload : JSON.stringify(payload))
    return true
  }

  onUnmounted(() => {
    unmounted = true
    clearReconnectTimer()
    if (ws) {
      try {
        ws.close()
      } catch {
        // 忽略
      }
      ws = null
    }
    status.value = 'closed'
  })

  if (autoConnect) connect()

  return { status, data, send, close, connect }
}

/**
 * 把相对 URL (如 /ws/training) 转成完整 ws://host/path。
 * 已包含 ws:// 或 wss:// 的原样返回; http(s) 自动替换协议。
 */
function buildAbsoluteWsUrl(input: string): string {
  if (input.startsWith('ws://') || input.startsWith('wss://')) return input
  if (input.startsWith('http://') || input.startsWith('https://')) {
    return input.replace(/^http/, 'ws')
  }
  if (typeof window === 'undefined') return input
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}${input}`
}