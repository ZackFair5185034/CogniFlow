// -*- coding: utf-8 -*-
/**
 * useWebSocket 回归测试。
 *
 * 背景 (2026-10-24 人工走查发现):
 * connect() 会先 close 旧连接再建新连接, 而旧连接的 onclose 是**异步**触发的。
 * 旧实现里 onclose 无条件执行 `ws = null`, 此时模块级 ws 已指向**新连接**,
 * 于是新连接被误置空 → send() 因 `ws?.readyState !== OPEN` 返回 false →
 * subscribe 消息发不出去 → 表现是「点了执行但什么都没发生」(WS 状态却显示已连接)。
 *
 * 本文件锁定该缺陷的修复行为, 防止回归。
 */
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { defineComponent, h } from 'vue'
import { useWebSocket } from './useWebSocket'

/** 最小可用的 WebSocket 桩, 记录实例以便测试手动驱动事件时序 */
class MockWebSocket {
  static readonly CONNECTING = 0
  static readonly OPEN = 1
  static readonly CLOSING = 2
  static readonly CLOSED = 3
  /** 全部创建过的实例 (按创建顺序) */
  static instances: MockWebSocket[] = []

  readyState: number = MockWebSocket.CONNECTING
  /** 发送出去的消息 */
  sent: string[] = []
  onopen: ((ev: Event) => void) | null = null
  onmessage: ((ev: MessageEvent) => void) | null = null
  onerror: ((ev: Event) => void) | null = null
  onclose: ((ev: CloseEvent) => void) | null = null

  constructor(public url: string) {
    MockWebSocket.instances.push(this)
  }

  send(data: string): void {
    this.sent.push(data)
  }

  /** 只改状态, **不**派发 onclose —— 由测试显式控制事件时序 */
  close(): void {
    this.readyState = MockWebSocket.CLOSED
  }

  /** 模拟连接建立 */
  emitOpen(): void {
    this.readyState = MockWebSocket.OPEN
    this.onopen?.(new Event('open'))
  }

  /** 模拟服务端推送 */
  emitMessage(payload: unknown): void {
    this.onmessage?.({ data: JSON.stringify(payload) } as MessageEvent)
  }

  /** 模拟连接关闭 (异步派发) */
  emitClose(): void {
    this.readyState = MockWebSocket.CLOSED
    this.onclose?.({ code: 1000, reason: '', wasClean: true } as CloseEvent)
  }
}

/** 在组件 setup 上下文里执行 composable, 以便 onUnmounted 正常注册 */
function withSetup<T>(fn: () => T): { result: T; unmount: () => void } {
  let result!: T
  const wrapper = mount(
    defineComponent({
      setup() {
        result = fn()
        return () => h('div')
      },
    }),
  )
  return { result, unmount: () => wrapper.unmount() }
}

describe('useWebSocket', () => {
  beforeEach(() => {
    MockWebSocket.instances = []
    vi.stubGlobal('WebSocket', MockWebSocket)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.useRealTimers()
  })

  it('连接建立后 send 能把消息发到当前连接', () => {
    const { result, unmount } = withSetup(() =>
      useWebSocket({ url: '/ws/rule-execution', autoConnect: true, reconnect: false }),
    )
    const sock = MockWebSocket.instances[0]
    sock.emitOpen()

    expect(result.status.value).toBe('open')
    expect(result.send({ action: 'subscribe', execution_id: 7 })).toBe(true)
    expect(sock.sent).toEqual(['{"action":"subscribe","execution_id":7}'])
    unmount()
  })

  it('连接未建立时 send 返回 false', () => {
    const { result, unmount } = withSetup(() =>
      useWebSocket({ url: '/ws/rule-execution', autoConnect: true, reconnect: false }),
    )
    expect(result.send({ action: 'subscribe' })).toBe(false)
    unmount()
  })

  it('重连后旧连接的 close 事件不会置空新连接, subscribe 仍可发出', () => {
    // 这是 2026-10-24 走查定位到的核心回归点
    const { result, unmount } = withSetup(() =>
      useWebSocket({ url: '/ws/rule-execution', autoConnect: true, reconnect: false }),
    )
    const first = MockWebSocket.instances[0]
    first.emitOpen()

    // 重连: connect() 先 close 旧连接,再建新连接
    result.connect()
    expect(MockWebSocket.instances.length).toBe(2)
    const second = MockWebSocket.instances[1]

    // 旧连接的 close 事件此刻才异步到达 —— 不能影响新连接
    first.emitClose()
    second.emitOpen()

    expect(result.status.value).toBe('open')
    expect(result.send({ action: 'subscribe', execution_id: 3 })).toBe(true)
    expect(second.sent).toEqual(['{"action":"subscribe","execution_id":3}'])
    // 消息不应发到已废弃的旧连接
    expect(first.sent).toHaveLength(0)
    unmount()
  })

  it('旧连接的 close 事件不会触发重连', () => {
    vi.useFakeTimers()
    const { result, unmount } = withSetup(() =>
      useWebSocket({
        url: '/ws/rule-execution',
        autoConnect: true,
        reconnect: true,
        reconnectDelay: 10,
      }),
    )
    const first = MockWebSocket.instances[0]
    first.emitOpen()

    result.connect()
    const second = MockWebSocket.instances[1]
    second.emitOpen()

    // 旧连接的关闭事件不应排定新的重连
    first.emitClose()
    vi.advanceTimersByTime(1000)

    expect(MockWebSocket.instances.length).toBe(2)
    expect(result.status.value).toBe('open')
    unmount()
  })

  it('当前连接断开后按延迟重连', () => {
    vi.useFakeTimers()
    const { result, unmount } = withSetup(() =>
      useWebSocket({
        url: '/ws/rule-execution',
        autoConnect: true,
        reconnect: true,
        reconnectDelay: 10,
      }),
    )
    const first = MockWebSocket.instances[0]
    first.emitOpen()

    first.emitClose()
    expect(result.status.value).toBe('reconnecting')

    vi.advanceTimersByTime(10)
    expect(MockWebSocket.instances.length).toBe(2)
    unmount()
  })

  it('主动 close 后不再重连且状态为 closed', () => {
    vi.useFakeTimers()
    const { result, unmount } = withSetup(() =>
      useWebSocket({
        url: '/ws/rule-execution',
        autoConnect: true,
        reconnect: true,
        reconnectDelay: 10,
      }),
    )
    MockWebSocket.instances[0].emitOpen()

    result.close()
    expect(result.status.value).toBe('closed')

    vi.advanceTimersByTime(1000)
    expect(MockWebSocket.instances.length).toBe(1)
    unmount()
  })

  it('收到消息时解析 JSON 并回调 onMessage', () => {
    const received: unknown[] = []
    const { result, unmount } = withSetup(() =>
      useWebSocket({
        url: '/ws/rule-execution',
        autoConnect: true,
        reconnect: false,
        onMessage: (msg) => received.push(msg),
      }),
    )
    const sock = MockWebSocket.instances[0]
    sock.emitOpen()
    sock.emitMessage({ type: 'node_status', node_id: 'n1', status: 'success' })

    expect(received).toEqual([{ type: 'node_status', node_id: 'n1', status: 'success' }])
    expect(result.data.value).toEqual({
      type: 'node_status',
      node_id: 'n1',
      status: 'success',
    })
    unmount()
  })

  it('组件卸载后关闭连接', () => {
    const { unmount } = withSetup(() =>
      useWebSocket({ url: '/ws/rule-execution', autoConnect: true, reconnect: true }),
    )
    const sock = MockWebSocket.instances[0]
    sock.emitOpen()

    unmount()
    expect(sock.readyState).toBe(MockWebSocket.CLOSED)
  })
})
