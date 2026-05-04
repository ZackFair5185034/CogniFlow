/**
 * 流式推理 WebSocket 客户端
 * 负责连接后端 /ws/inference/stream/{job_id} 并接收实时帧数据
 */

export interface StreamFrame {
  frame_id: number
  timestamp: number
  image: string          // base64 jpeg
  detections: StreamDetection[]
  stats: {
    inference_ms: number
    total_detections: number
  }
}

export interface StreamDetection {
  bbox: [number, number, number, number]   // [x1, y1, x2, y2]
  class_id: number
  class_name: string
  confidence: number
}

export interface StreamStats {
  fps: number
  total_frames: number
  current_frame: number
  progress: number
  total_detections: number
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'stopped'
}

type FrameCallback = (frame: StreamFrame) => void
type StatsCallback = (stats: StreamStats) => void
type CompleteCallback = (total_frames: number, total_detections: number) => void
type ErrorCallback = (error: string) => void

export class StreamClient {
  private ws: WebSocket | null = null
  private jobId: string | null = null
  private url: string = ''
  private reconnectAttempts = 0
  private maxReconnectAttempts = 3
  private reconnectDelay = 2000

  private onFrameCb: FrameCallback | null = null
  private onStatsCb: StatsCallback | null = null
  private onCompleteCb: CompleteCallback | null = null
  private onErrorCb: ErrorCallback | null = null

  private paused = false
  private lastFrame: StreamFrame | null = null

  /**
   * 连接到流式推理任务
   * @param jobId 任务 ID
   * @param streamUrl WebSocket URL（相对路径，如 /ws/inference/stream/abc123）
   */
  connect(jobId: string, streamUrl: string): void {
    this.jobId = jobId
    this.url = this._buildWsUrl(streamUrl)
    this.reconnectAttempts = 0
    this._doConnect()
  }

  /**
   * 断开连接
   */
  disconnect(): void {
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
    this.jobId = null
  }

  /**
   * 暂停接收帧（但保持连接）
   */
  pause(): void {
    this.paused = true
  }

  /**
   * 恢复接收帧
   */
  resume(): void {
    this.paused = false
    // 立即渲染最新帧
    if (this.lastFrame) {
      this._emitFrame(this.lastFrame)
    }
  }

  /**
   * 获取暂停状态
   */
  isPaused(): boolean {
    return this.paused
  }

  // 回调设置
  onFrame(cb: FrameCallback): void {
    this.onFrameCb = cb
  }

  onStats(cb: StatsCallback): void {
    this.onStatsCb = cb
  }

  onComplete(cb: CompleteCallback): void {
    this.onCompleteCb = cb
  }

  onError(cb: ErrorCallback): void {
    this.onErrorCb = cb
  }

  private _buildWsUrl(streamUrl: string): string {
    // 相对路径转 WebSocket URL
    if (streamUrl.startsWith('ws') || streamUrl.startsWith('http')) {
      return streamUrl.replace('http', 'ws')
    }
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    return `${protocol}//${host}${streamUrl}`
  }

  private _doConnect(): void {
    if (!this.url) return

    try {
      this.ws = new WebSocket(this.url)

      this.ws.onopen = () => {
        this.reconnectAttempts = 0
      }

      this.ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data)
          this._handleMessage(msg)
        } catch (e) {
          console.error('[StreamClient] 解析消息失败', e)
        }
      }

      this.ws.onerror = (error) => {
        console.error('[StreamClient] WebSocket 错误', error)
        this.onErrorCb?.('WebSocket 连接错误')
      }

      this.ws.onclose = () => {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
          this.reconnectAttempts++
          setTimeout(() => this._doConnect(), this.reconnectDelay)
        }
      }
    } catch (e) {
      this.onErrorCb?.(`连接失败: ${e}`)
    }
  }

  private _handleMessage(msg: any): void {
    switch (msg.type) {
      case 'frame':
        if (!this.paused) {
          this._emitFrame(msg as StreamFrame)
        } else {
          this.lastFrame = msg as StreamFrame
        }
        break

      case 'complete':
        this.onCompleteCb?.(msg.total_frames || 0, msg.total_detections || 0)
        this.disconnect()
        break

      case 'stopped':
        this.onCompleteCb?.(msg.total_frames || 0, msg.total_detections || 0)
        break

      case 'error':
        this.onErrorCb?.(msg.error || '未知错误')
        break

      case 'heartbeat':
        // 心跳包，无需处理
        break

      case 'pong':
        // pong 响应，无需处理
        break

      default:
        // 忽略其他消息
        break
    }
  }

  private _emitFrame(frame: StreamFrame): void {
    this.onFrameCb?.(frame)
  }
}
