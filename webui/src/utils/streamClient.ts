/**
 * 流式推理 WebSocket 客户端
 * 负责连接后端 /ws/inference/stream/{job_id} 并接收实时帧数据
 *
 * 协议：混合模式
 * - 文本消息（JSON）: 帧元数据 + 检测结果 + 进度信息
 * - 二进制消息: JPEG 原始字节
 *
 * 服务端不做节流，来帧即推；前端自行控制渲染帧率。
 */

export interface StreamFrameProgress {
  buffer_frame: number
  total_frames: number
  buffer_pct: number
}

export interface StreamFrame {
  frame_id: number
  timestamp: number
  /** 仅当需要 base64 回退时使用 */
  image?: string
  /** 通过 createImageBitmap 解码后的位图 */
  bitmap?: ImageBitmap
  /** JPEG 二进制数据 */
  imageData?: ArrayBuffer
  detections: StreamDetection[]
  stats: {
    inference_ms: number
    total_detections: number
  }
  /** 双进度信息 */
  progress?: StreamFrameProgress
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
  /** 缓冲帧数（暂停期间累积） */
  buffer_frame?: number
  buffered_frames?: number
}

type FrameCallback = (frame: StreamFrame) => void
type CompleteCallback = (total_frames: number, total_detections: number) => void
type ErrorCallback = (error: string) => void

interface WsMessage {
  type: string
  // frame_meta / frame 字段
  frame_id?: number
  timestamp?: number
  detections?: StreamDetection[]
  stats?: { inference_ms: number; total_detections: number }
  progress?: StreamFrameProgress
  // complete / stopped 字段
  total_frames?: number
  total_detections?: number
  // error 字段
  error?: string
  // 允许其他未知字段（后端可能扩展）
  [key: string]: unknown
}

export class StreamClient {
  private ws: WebSocket | null = null
  private url: string = ''
  private reconnectAttempts = 0
  private maxReconnectAttempts = 3
  private reconnectDelay = 2000
  /** 标记是否为主动断开（调用 disconnect()），避免误触 onError */
  private _intentionalDisconnect = false
  /** 标记是否已收到 complete/stopped 消息 */
  private _completedNormally = false

  private onFrameCb: FrameCallback | null = null
  private onCompleteCb: CompleteCallback | null = null
  private onErrorCb: ErrorCallback | null = null

  /** 缓存的帧元数据，等待二进制图片数据到达后合并 */
  private pendingMeta: StreamFrame | null = null

  /**
   * 连接到流式推理任务
   * @param jobId 任务 ID
   * @param streamUrl WebSocket URL（相对路径，如 /ws/inference/stream/abc123）
   */
  connect(_jobId: string, streamUrl: string): void {
    this.url = this._buildWsUrl(streamUrl)
    this.reconnectAttempts = 0
    this._intentionalDisconnect = false
    this._completedNormally = false
    this.pendingMeta = null
    this._doConnect()
  }

  /**
   * 主动断开连接
   */
  disconnect(): void {
    this._intentionalDisconnect = true
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
    this.pendingMeta = null
  }

  // 回调设置
  onFrame(cb: FrameCallback): void {
    this.onFrameCb = cb
  }

  onComplete(cb: CompleteCallback): void {
    this.onCompleteCb = cb
  }

  onError(cb: ErrorCallback): void {
    this.onErrorCb = cb
  }

  private _buildWsUrl(streamUrl: string): string {
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
      // 设置为二进制类型为 ArrayBuffer
      this.ws.binaryType = 'arraybuffer'

      this.ws.onopen = () => {
        this.reconnectAttempts = 0
      }

      this.ws.onmessage = (event) => {
        try {
          if (event.data instanceof ArrayBuffer) {
            this._handleBinary(event.data)
          } else {
            const msg = JSON.parse(event.data)
            this._handleMessage(msg)
          }
        } catch (e) {
          console.error('[StreamClient] 解析消息失败', e)
        }
      }

      this.ws.onerror = () => {
        this.onErrorCb?.('WebSocket 连接错误')
      }

      this.ws.onclose = () => {
        if (this._intentionalDisconnect || this._completedNormally) {
          return  // 主动断开或正常结束，不触发错误
        }
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
          this.reconnectAttempts++
          setTimeout(() => this._doConnect(), this.reconnectDelay)
        } else {
          this.onErrorCb?.('连接已断开，请重新检测')
        }
      }
    } catch (e) {
      this.onErrorCb?.(`连接失败: ${e}`)
    }
  }

  private _handleMessage(msg: WsMessage): void {
    switch (msg.type) {
      case 'frame_meta':
        // 缓存元数据，等待后续的二进制帧数据
        this.pendingMeta = {
          frame_id: msg.frame_id ?? 0,
          timestamp: msg.timestamp ?? 0,
          detections: msg.detections ?? [],
          stats: msg.stats ?? { inference_ms: 0, total_detections: 0 },
          progress: msg.progress,
        }
        break

      case 'frame':
        // 兼容旧协议（base64），不走二进制路径
        this._emitFrame(msg as StreamFrame)
        break

      case 'complete':
        this._completedNormally = true
        this.onCompleteCb?.(msg.total_frames ?? 0, msg.total_detections ?? 0)
        this.disconnect()
        break

      case 'stopped':
        this._completedNormally = true
        this.onCompleteCb?.(msg.total_frames ?? 0, msg.total_detections ?? 0)
        break

      case 'error':
        this.onErrorCb?.(msg.error ?? '未知错误')
        break

      case 'heartbeat':
      case 'pong':
        break

      default:
        break
    }
  }

  private _handleBinary(data: ArrayBuffer): void {
    const meta = this.pendingMeta
    if (!meta) return

    // 合并元数据和二进制图片数据
    const frame: StreamFrame = {
      ...meta,
      imageData: data,
    }
    this.pendingMeta = null

    this._emitFrame(frame)
  }

  private _emitFrame(frame: StreamFrame): void {
    this.onFrameCb?.(frame)
  }
}
