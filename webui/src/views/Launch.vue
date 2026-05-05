<template>
  <div class="launch">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-info">
        <h2>模型测试</h2>
        <span class="subtitle">图片/视频检测</span>
      </div>
      <!-- 模式切换 Tab -->
      <div class="mode-tabs">
        <button
          class="mode-tab"
          :class="{ active: mode === 'image' }"
          @click="mode = 'image'"
        >
          <SvgIcon name="image" />
          图片检测
        </button>
        <button
          class="mode-tab"
          :class="{ active: mode === 'stream' }"
          @click="mode = 'stream'"
        >
          <SvgIcon name="stream" />
          视频检测
        </button>
      </div>
    </div>

    <div class="launch-body">
      <!-- 左侧：配置面板 -->
      <div class="config-panel ui-card">
        <div class="panel-header">
          <div class="header-left">
            <SvgIcon name="brain" class="panel-icon" />
            <h3>检测配置</h3>
          </div>
        </div>

        <div class="config-content">
          <!-- 模型选择 -->
          <div class="config-section">
            <label class="section-label">选择模型</label>
            <div class="select-wrapper">
              <select v-model="selectedModelId" :disabled="detecting || streamConnected">
                <option :value="null" disabled>选择已训练的模型</option>
                <option v-for="m in trainedModels" :key="m.id" :value="m.id">
                  {{ m.name }}{{ m.version ? ` (${m.version})` : '' }}
                </option>
              </select>
            </div>
            <div class="model-info" v-if="selectedModel">
              <span class="info-tag">类别: {{ getModelClasses(selectedModel) }}</span>
              <span class="info-tag" v-if="selectedModel.metrics?.mAP50">mAP50: {{ (selectedModel.metrics.mAP50 * 100).toFixed(1) }}%</span>
            </div>
          </div>

          <!-- 置信度阈值 -->
          <div class="config-section">
            <label class="section-label">置信度阈值: {{ (confThreshold * 100).toFixed(0) }}%</label>
            <input
              type="range"
              v-model.number="confThreshold"
              min="0.05"
              max="0.95"
              step="0.05"
              class="range-slider"
            />
          </div>

          <!-- 图片模式 -->
          <template v-if="mode === 'image'">
            <div class="config-section">
              <label class="section-label">上传图片</label>
              <div
                class="upload-zone"
                :class="{ dragging: isDragging, disabled: detecting }"
                @dragover.prevent="isDragging = true"
                @dragleave="isDragging = false"
                @drop.prevent="handleDrop"
                @click="triggerFileInput"
              >
                <input
                  ref="fileInputRef"
                  type="file"
                  accept="image/*"
                  @change="handleFileSelect"
                  style="display: none"
                />
                <div class="upload-hint">
                  <SvgIcon name="upload" />
                  <span v-if="!selectedFile">拖拽或点击上传</span>
                  <span v-else class="file-name">{{ selectedFile.name }}</span>
                </div>
              </div>
            </div>
          </template>

          <!-- 视频检测模式 -->
          <template v-else-if="mode === 'stream'">
            <div class="config-section">
              <label class="section-label">上传视频</label>
              <div
                class="upload-zone"
                :class="{ dragging: isDragging, disabled: streamConnected }"
                @dragover.prevent="isDragging = true"
                @dragleave="isDragging = false"
                @drop.prevent="handleStreamDrop"
                @click="triggerStreamInput"
              >
                <input
                  ref="streamInputRef"
                  type="file"
                  accept="video/*"
                  @change="handleStreamSelect"
                  style="display: none"
                />
                <div class="upload-hint">
                  <SvgIcon name="upload" />
                  <span v-if="!selectedStreamFile">拖拽或点击上传视频</span>
                  <span v-else class="file-name">{{ selectedStreamFile.name }}</span>
                </div>
              </div>
            </div>

            <!-- 视频状态 -->
            <div class="stream-stats" v-if="streamConnected">
              <div class="stat-item">
                <span class="stat-label">帧率</span>
                <span class="stat-value">{{ streamStats.fps }} fps</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">已处理</span>
                <span class="stat-value">{{ streamStats.current_frame }} / {{ streamStats.total_frames }}</span>
              </div>
              <div class="stat-item" v-if="streamStats.buffered_frames">
                <span class="stat-label">缓冲</span>
                <span class="stat-value buffer-stat">{{ streamStats.buffered_frames }} 帧</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">检测数</span>
                <span class="stat-value">{{ streamStats.total_detections }}</span>
              </div>
            </div>
          </template>

          <!-- 最近记录 -->
          <div class="config-section">
            <div class="section-label-row" @click="recentRecordsExpanded = !recentRecordsExpanded">
              <span class="section-label">最近记录</span>
              <div class="flex items-center gap-2">
                <button
                  v-if="recentRecords.length > 0"
                  class="clear-btn"
                  @click.stop="handleClearRecords"
                  title="清除历史"
                >清空</button>
                <SvgIcon :name="recentRecordsExpanded ? 'chevron-up' : 'chevron-down'" class="chevron-icon" />
              </div>
            </div>
            <div class="recent-records" v-if="recentRecordsExpanded">
              <div v-if="filteredRecords.length === 0" class="records-empty">暂无{{ mode === 'stream' ? '视频' : '图片' }}检测记录</div>
              <div
                v-for="rec in filteredRecords"
                :key="rec.job_id"
                class="record-item"
              >
                <img v-if="rec.thumbnail" :src="rec.thumbnail" class="record-thumb" alt="缩略图" />
                <div class="record-info">
                  <span class="record-name">{{ rec.file_name }}</span>
                  <span class="record-meta">{{ rec.model_name }} · {{ rec.total_detections }} 个目标</span>
                  <span class="record-time">{{ formatRelativeTime(rec.created_at) }}</span>
                </div>
                <el-button
                  size="small"
                  class="rerun-btn"
                  :disabled="!rec.file_path"
                  @click="handleRerun(rec)"
                >
                  {{ rec.file_type === 'image' ? '图片重检' : '重新检测' }}
                </el-button>
              </div>
            </div>
          </div>

          <!-- 检测按钮 -->
          <el-button
            v-if="mode === 'image'"
            class="detect-btn"
            type="primary"
            :disabled="!canDetect || detecting"
            :loading="detecting"
            @click="startDetection"
          >
            {{ detecting ? '检测中...' : '开始检测' }}
          </el-button>

          <!-- 视频检测按钮 -->
          <template v-if="mode === 'stream'">
            <el-button
              v-if="!streamConnected"
              class="detect-btn"
              type="primary"
              :disabled="!canStreamDetect || streamUploading"
              :loading="streamUploading"
              @click="startVideoDetection"
            >
              {{ streamUploading ? '上传中...' : '开始视频检测' }}
            </el-button>
            <el-button
              v-else
              class="detect-btn"
              type="danger"
              @click="stopVideoDetection"
            >
              停止检测
            </el-button>
          </template>
        </div>
      </div>

      <!-- 右侧：结果显示 -->
      <div class="result-panel ui-card">
        <div class="panel-header">
          <div class="header-left">
            <SvgIcon name="eye" class="panel-icon" />
            <h3>检测结果</h3>
          </div>
        </div>

        <div class="result-body">
          <!-- 图片检测结果 -->
          <div v-if="resultImage" class="result-image-wrapper">
            <div class="image-area">
              <img :src="resultImage" alt="检测结果" class="result-image" />
              <svg class="bbox-overlay" :viewBox="`0 0 ${imageSize.width} ${imageSize.height}`">
                <g v-for="(det, idx) in detections" :key="idx">
                  <rect
                    :x="det.bbox[0]"
                    :y="det.bbox[1]"
                    :width="det.bbox[2] - det.bbox[0]"
                    :height="det.bbox[3] - det.bbox[1]"
                    :stroke="getClassColor(det.class_id)"
                    stroke-width="2"
                    fill="none"
                  />
                  <rect
                    :x="det.bbox[0]"
                    :y="det.bbox[1] - 20"
                    width="80"
                    height="20"
                    :fill="getClassColor(det.class_id)"
                  />
                  <text
                    :x="det.bbox[0] + 4"
                    :y="det.bbox[1] - 5"
                    fill="white"
                    font-size="12"
                    font-family="sans-serif"
                  >{{ det.class_name }} {{ (det.confidence * 100).toFixed(0) }}%</text>
                </g>
              </svg>
            </div>
            <div class="zoom-controls">
              <button class="zoom-btn" @click="zoomLevel = Math.min(2, zoomLevel + 0.25)">+</button>
              <span class="zoom-level">{{ (zoomLevel * 100).toFixed(0) }}%</span>
              <button class="zoom-btn" @click="zoomLevel = Math.max(0.5, zoomLevel - 0.25)">-</button>
            </div>
          </div>

        <!-- 视频检测结果 - Canvas 渲染 -->
        <div v-else-if="mode === 'stream' && (streamConnected || streamComplete)" class="result-stream-wrapper">
          <div class="stream-container">
            <canvas ref="streamCanvasRef" class="stream-canvas"></canvas>
          </div>
          <div class="stream-progress" v-if="!streamComplete">
            <div class="progress-bar-dual">
              <div class="progress-buffer" :style="{ width: `${bufferProgress}%` }"></div>
              <div class="progress-playback" :style="{ width: `${streamStats.progress}%` }"></div>
            </div>
            <div class="progress-controls">
              <button
                class="ctrl-btn"
                :title="streamPaused ? '继续' : '暂停'"
                @click="togglePause"
              >
                <SvgIcon :name="streamPaused ? 'play' : 'pause'" />
              </button>
              <span class="progress-text">帧 {{ streamStats.current_frame }} / {{ streamStats.total_frames }}</span>
              <span class="buffer-info" v-if="streamStats.buffer_frame">缓冲 {{ streamStats.buffer_frame }}</span>
              <div class="fps-control">
                <button class="ctrl-btn-sm" @click="adjustFps(-5)" :disabled="videoFps <= 1">-</button>
                <span class="fps-value">{{ videoFps }} fps</span>
                <button class="ctrl-btn-sm" @click="adjustFps(5)" :disabled="videoFps >= 60">+</button>
              </div>
            </div>
          </div>
          <div class="stream-complete" v-else>
            <span>检测完成，共 {{ streamStats.total_detections }} 个目标</span>
          </div>
        </div>

        <!-- 加载状态（图片检测用） -->
        <div v-else-if="detecting" class="result-loading">
          <div class="loading-spinner"></div>
          <span>图片检测中...</span>
        </div>

        <!-- 空状态 -->
        <div v-else class="empty-result">
          <div class="empty-icon">
            <SvgIcon name="image" v-if="mode === 'image'" />
            <SvgIcon name="stream" v-else />
          </div>
          <p>暂无检测结果</p>
          <span>{{ mode === 'image' ? '上传图片开始检测' : '上传视频开始检测' }}</span>
        </div>
        </div>

        <!-- 分割拖拽条 -->
        <div
          class="console-divider"
          v-show="consoleExpanded"
          @mousedown.prevent="startDrag"
        ></div>

        <!-- 监控台 -->
        <div class="console-panel" :class="{ expanded: consoleExpanded }" :style="consoleStyle">
          <div class="console-header" @click="consoleExpanded = !consoleExpanded">
            <div class="console-header-left">
              <SvgIcon name="terminal" class="console-icon" />
              <span>监控台</span>
              <span class="console-count" v-if="consoleEntries.length">{{ consoleEntries.length }} 条</span>
            </div>
            <div class="console-header-right">
              <button class="console-clear-btn" @click.stop="clearConsole" title="清空">清空</button>
              <SvgIcon :name="consoleExpanded ? 'chevron-down' : 'chevron-up'" class="console-toggle" />
            </div>
          </div>
          <div class="console-body" v-show="consoleExpanded" ref="consoleBodyRef">
            <div
              v-for="(entry, idx) in consoleEntries"
              :key="entry.id"
              class="console-entry"
              :class="{ expanded: entry.expanded }"
            >
              <div class="console-entry-header" @click="entry.expanded = !entry.expanded">
                <span class="entry-time">{{ entry.time }}</span>
                <span class="entry-source" :class="entry.source === '图片检测' ? 'src-image' : 'src-video'">{{ entry.source }}</span>
                <span class="entry-summary">{{ entry.summary }}</span>
                <button class="entry-copy-btn" @click.stop="copyEntry(entry)" title="复制 JSON">
                  <SvgIcon name="copy" />
                </button>
                <span class="entry-toggle">{{ entry.expanded ? '−' : '+' }}</span>
              </div>
              <div class="console-entry-body" v-show="entry.expanded">
                <pre class="console-json">{{ formatJSON(entry.data) }}</pre>
              </div>
            </div>
            <div class="console-empty" v-if="consoleEntries.length === 0">
              <span>暂无数据，执行检测后将自动显示</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { inferenceApi } from '@/api'
import { StreamClient, type StreamFrame, type StreamStats } from '@/utils/streamClient'
import SvgIcon from '@/components/SvgIcon.vue'

// 状态
const mode = ref<'image' | 'stream'>('image')
const trainedModels = ref<any[]>([])
const selectedModelId = ref<number | null>(null)
const confThreshold = ref(0.25)
const selectedFile = ref<File | null>(null)
const fileInputRef = ref<HTMLInputElement | null>(null)
const isDragging = ref(false)
const isLoading = ref(false)
const detecting = ref(false)

const resultImage = ref<string | null>(null)
const detections = ref<any[]>([])
const imageSize = ref({ width: 0, height: 0 })
const zoomLevel = ref(1)

// 视频检测状态
const videoClient = ref<StreamClient | null>(null)
const streamJobId = ref<string | null>(null)
const streamCanvasRef = ref<HTMLCanvasElement | null>(null)
const streamInputRef = ref<HTMLInputElement | null>(null)
const selectedStreamFile = ref<File | null>(null)
const streamUploading = ref(false)
const streamConnected = ref(false)
const streamComplete = ref(false)
const streamPaused = ref(false)
const videoFps = ref(24)

// 前端帧缓存：暂停时累积，恢复时快速重放
const frameCache = ref<StreamFrame[]>([])
const isReplaying = ref(false)
let replayTimer: number | null = null
/** 类别颜色映射，来自后端数据库配置 */
const categoryColors = ref<Record<number, string>>({})

// 监控台状态
interface ConsoleEntry {
  id: number
  time: string
  source: '图片检测' | '视频帧'
  frameId?: number
  summary: string
  data: any
  expanded: boolean
}
const consoleExpanded = ref(false)
const consoleEntries = ref<ConsoleEntry[]>([])
const consoleBodyRef = ref<HTMLDivElement | null>(null)
let nextEntryId = 0
let lastVideoLogTime = 0

const addConsoleEntry = (source: ConsoleEntry['source'], summary: string, data: any, frameId?: number) => {
  const now = Date.now()
  // 视频检测节流：每秒最多 5 条
  if (source === '视频帧' && now - lastVideoLogTime < 200) return
  lastVideoLogTime = now

  const time = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  consoleEntries.value.unshift({
    id: nextEntryId++,
    time,
    source,
    frameId,
    summary,
    data,
    expanded: false,
  })
  // 最多保留 200 条
  if (consoleEntries.value.length > 200) {
    consoleEntries.value = consoleEntries.value.slice(0, 200)
  }
}

const clearConsole = () => {
  consoleEntries.value = []
  nextEntryId = 0
}

const formatJSON = (data: any) => {
  try {
    return JSON.stringify(data, null, 2)
  } catch {
    return String(data)
  }
}

// 复制和拖拽
const consoleHeight = ref(260)
const isDraggingDivider = ref(false)

const consoleStyle = computed(() => {
  if (!consoleExpanded.value) return {}
  return { height: `${consoleHeight.value}px` }
})

const startDrag = (e: MouseEvent) => {
  isDragging.value = true
  const startY = e.clientY
  const startHeight = consoleHeight.value

  const onMove = (ev: MouseEvent) => {
    const delta = startY - ev.clientY
    const newHeight = Math.max(120, Math.min(600, startHeight + delta))
    consoleHeight.value = newHeight
  }

  const onUp = () => {
    isDragging.value = false
    document.removeEventListener('mousemove', onMove)
    document.removeEventListener('mouseup', onUp)
    document.body.style.cursor = ''
    document.body.style.userSelect = ''
  }

  document.addEventListener('mousemove', onMove)
  document.addEventListener('mouseup', onUp)
  document.body.style.cursor = 'row-resize'
  document.body.style.userSelect = 'none'
}

const copyEntry = async (entry: ConsoleEntry) => {
  try {
    await navigator.clipboard.writeText(formatJSON(entry.data))
    ElMessage.success('已复制到剪贴板')
  } catch {
    ElMessage.warning('复制失败')
  }
}

const streamStats = ref<StreamStats>({
  fps: 24,
  total_frames: 0,
  current_frame: 0,
  progress: 0,
  total_detections: 0,
  status: 'pending',
  buffer_frame: 0,
})

const bufferProgress = computed(() => {
  const total = streamStats.value.total_frames || 1
  const buf = streamStats.value.buffer_frame || 0
  return Math.min(100, Math.ceil((buf / total) * 100))
})

const canStreamDetect = computed(() => {
  return selectedModelId.value && selectedStreamFile.value && !streamConnected.value
})

const selectedModel = computed(() => {
  return trainedModels.value.find(m => m.id === selectedModelId.value)
})

const canDetect = computed(() => {
  return selectedModelId.value && selectedFile.value && !detecting.value
})

const getModelClasses = (model: any) => {
  if (model.metrics?.categories) {
    return model.metrics.categories.length
  }
  return model.metrics?.num_classes || '?'
}

const getClassColor = (classId: number) => {
  // 优先使用数据库配置的类别颜色
  const configured = categoryColors.value[classId]
  if (configured) return configured
  // 回退硬编码色板
  const fallbackColors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD', '#98D8C8', '#F7DC6F']
  return fallbackColors[classId % fallbackColors.length]
}

// 加载已训练模型
const loadTrainedModels = async () => {
  try {
    const res = await inferenceApi.listTrainedModels()
    trainedModels.value = res.data
    if (trainedModels.value.length > 0 && !selectedModelId.value) {
      selectedModelId.value = trainedModels.value[0].id
    }
  } catch (error) {
    console.error('加载模型失败', error)
  }
}

// 文件选择 - 图片
const handleFileSelect = (event: Event) => {
  const input = event.target as HTMLInputElement
  if (input.files && input.files[0]) {
    selectedFile.value = input.files[0]
    clearResults()
  }
}

// 最近记录
interface RecentRecord {
  job_id: string
  model_id: number
  model_name: string
  file_name: string
  file_path: string
  file_type: 'image' | 'video'
  conf_threshold: number
  status: string
  total_frames: number | null
  total_detections: number
  thumbnail: string | null
  created_at: string
  finished_at: string | null
}

const recentRecords = ref<RecentRecord[]>([])
const recentRecordsExpanded = ref(true)
const filteredRecords = computed(() => {
  return recentRecords.value.filter(r => r.file_type === (mode.value === 'stream' ? 'video' : 'image'))
})

// 加载最近记录
const loadRecentRecords = async () => {
  try {
    const res = await inferenceApi.listInferenceJobs()
    recentRecords.value = res.data
  } catch (error) {
    console.error('加载最近记录失败', error)
  }
}

// 相对时间格式化
const formatRelativeTime = (isoString: string): string => {
  if (!isoString) return '未知'
  const serverTime = new Date(isoString.endsWith('Z') ? isoString : isoString + 'Z').getTime()
  if (isNaN(serverTime)) return '未知'
  const diff = Date.now() - serverTime
  const seconds = Math.floor(diff / 1000)
  if (seconds < 60) return '刚刚'
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}分钟前`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}小时前`
  const days = Math.floor(hours / 24)
  return `${days}天前`
}

// 清除历史记录
const handleClearRecords = async () => {
  try {
    await inferenceApi.clearInferenceJobs()
    recentRecords.value = []
    ElMessage.success('已清除历史记录')
  } catch (error: any) {
    ElMessage.error('清除失败')
  }
}

// 重新检测
const handleRerun = async (rec: RecentRecord) => {
  selectedModelId.value = rec.model_id
  confThreshold.value = rec.conf_threshold

  try {
    const res = await inferenceApi.rerunInferenceJob(rec.job_id, rec.model_id, rec.conf_threshold)
    if (res.data.success) {
      // 图片重检：内联结果
      if (res.data.file_type === 'image') {
        mode.value = 'image'
        resultImage.value = res.data.result_image_base64
        detections.value = res.data.detections || []
        loadImageSize(res.data.result_image_base64)

        // 构建类别颜色映射
        if (res.data.categories) {
          const colors: Record<number, string> = {}
          res.data.categories.forEach((cat: any, idx: number) => {
            colors[idx] = cat.color || '#FF0000'
          })
          categoryColors.value = colors
        }

        addConsoleEntry('图片检测', `${res.data.num_detections || 0} 个目标`, {
          num_detections: res.data.num_detections,
          detections: res.data.detections,
          model_id: rec.model_id,
          conf_threshold: rec.conf_threshold,
          rerun: true,
        })
        loadRecentRecords()
        return
      }

      // 视频重检：WebSocket 流式
      mode.value = 'stream'
      streamJobId.value = res.data.job_id
      const videoInfo = res.data.video_info
      videoFps.value = videoInfo.fps || 24
      streamStats.value = {
        fps: videoInfo.fps || 24,
        total_frames: videoInfo.total_frames || 0,
        current_frame: 0,
        progress: 0,
        total_detections: 0,
        status: 'processing',
        buffer_frame: 0,
      }
      frameCache.value = []
      isReplaying.value = false

      const client = new StreamClient()
      client.onFrame((frame) => {
        if (streamPaused.value || isReplaying.value) {
          frameCache.value.push(frame)
          streamStats.value = {
            ...streamStats.value,
            buffer_frame: frame.progress?.buffer_frame || streamStats.value.buffer_frame || frame.frame_id,
            buffered_frames: frameCache.value.length,
          }
          return
        }

        streamStats.value = {
          ...streamStats.value,
          current_frame: frame.frame_id,
          total_detections: frame.stats.total_detections,
          progress: Math.min(99, Math.ceil((frame.frame_id / (videoInfo.total_frames || 1)) * 100)),
          buffer_frame: frame.progress?.buffer_frame || streamStats.value.buffer_frame,
          buffered_frames: frameCache.value.length,
        }
        renderFrame(frame)
        addConsoleEntry('视频帧',
          `帧 #${frame.frame_id} | ${frame.detections.length} 个目标 | ${frame.stats.inference_ms}ms`,
          {
            frame_id: frame.frame_id,
            timestamp: frame.timestamp,
            detections: frame.detections,
            stats: frame.stats,
          },
          frame.frame_id,
        )
      })
      client.onComplete((totalFrames, totalDetections) => {
        streamComplete.value = true
        streamConnected.value = false
        streamPaused.value = false
        streamStats.value = {
          ...streamStats.value,
          progress: 100,
          current_frame: totalFrames,
          total_detections: totalDetections,
          status: 'completed',
        }
        loadRecentRecords()
        addConsoleEntry('视频帧', `检测完成，共 ${totalFrames} 帧，${totalDetections} 个目标`, {
          total_frames: totalFrames,
          total_detections: totalDetections,
          status: 'completed',
        })
      })
      client.onError((error) => {
        ElMessage.error(`视频检测错误: ${error}`)
        streamConnected.value = false
      })
      client.onPaused(() => { streamPaused.value = true })
      client.onResumed(() => { streamPaused.value = false })
      client.onFpsUpdated((fps) => { videoFps.value = fps })
      client.onProgress((progress) => {
        streamStats.value = {
          ...streamStats.value,
          buffer_frame: progress.buffer_frame,
        }
      })

      client.connect(res.data.job_id, res.data.stream_url)
      videoClient.value = client
      streamConnected.value = true
      streamPaused.value = false
      streamComplete.value = false
    }
  } catch (error: any) {
    const msg = error.response?.data?.detail || '重新检测失败'
    ElMessage.error(msg)
  }
}

const handleDrop = (event: DragEvent) => {
  isDragging.value = false
  if (event.dataTransfer?.files && event.dataTransfer.files[0]) {
    const file = event.dataTransfer.files[0]
    if (file.type.startsWith('image/')) {
      selectedFile.value = file
      clearResults()
    }
  }
}

const triggerFileInput = () => {
  fileInputRef.value?.click()
}

// 清除结果
const clearResults = () => {
  resultImage.value = null
  detections.value = []
  imageSize.value = { width: 0, height: 0 }
}

// 加载图片获取尺寸（用于 SVG viewBox）
const loadImageSize = (src: string) => {
  const img = new Image()
  img.onload = () => {
    imageSize.value = { width: img.naturalWidth, height: img.naturalHeight }
  }
  img.src = src
}

// 开始检测
const startDetection = async () => {
  if (!canDetect.value) return

  detecting.value = true
  clearResults()

  try {
    if (mode.value === 'image' && selectedFile.value) {
      const res = await inferenceApi.detectImage(selectedFile.value, selectedModelId.value!, confThreshold.value)
      if (res.data.success) {
        resultImage.value = res.data.result_image_base64
        detections.value = res.data.detections || []
        loadImageSize(res.data.result_image_base64)

        // 构建类别颜色映射（来自模型配置，使用数组索引作为 key）
        if (res.data.categories) {
          const colors: Record<number, string> = {}
          res.data.categories.forEach((cat: any, idx: number) => {
            colors[idx] = cat.color || '#FF0000'
          })
          categoryColors.value = colors
        }

        // 写入监控台
        addConsoleEntry('图片检测', `${res.data.num_detections || 0} 个目标`, {
          num_detections: res.data.num_detections,
          detections: res.data.detections,
          model_id: selectedModelId.value,
          conf_threshold: confThreshold.value,
        })
        loadRecentRecords()
      }
    }
  } catch (error: any) {
    const msg = error.response?.data?.detail || '检测失败'
    addConsoleEntry('图片检测', '检测失败', { error: msg })
    ElMessage.error(msg)
  } finally {
    detecting.value = false
  }
}

// 切换模式时清除状态
const handleModeChange = () => {
  clearResults()
  if (mode.value !== 'stream') {
    stopVideoDetection()
  }
}

// ===== 视频检测 =====

// 文件选择 - 视频
const handleStreamSelect = (event: Event) => {
  const input = event.target as HTMLInputElement
  if (input.files && input.files[0]) {
    selectedStreamFile.value = input.files[0]
    streamComplete.value = false
  }
}

const handleStreamDrop = (event: DragEvent) => {
  isDragging.value = false
  if (event.dataTransfer?.files && event.dataTransfer.files[0]) {
    const file = event.dataTransfer.files[0]
    if (file.type.startsWith('video/')) {
      selectedStreamFile.value = file
      streamComplete.value = false
    }
  }
}

const triggerStreamInput = () => {
  streamInputRef.value?.click()
}

// 渲染帧到 Canvas
const renderFrame = async (frame: StreamFrame) => {
  const canvas = streamCanvasRef.value
  if (!canvas) return

  const ctx = canvas.getContext('2d')
  if (!ctx) return

  try {
    let bitmap: ImageBitmap | null = null

    if (frame.bitmap) {
      // 直接使用预解码的位图
      bitmap = frame.bitmap
    } else if (frame.imageData) {
      // 二进制 JPEG 数据 → Blob → createImageBitmap（零拷贝解码）
      const blob = new Blob([frame.imageData], { type: 'image/jpeg' })
      bitmap = await createImageBitmap(blob)
    } else if (frame.image) {
      // 旧协议 base64 回退
      const blob = await (await fetch(`data:image/jpeg;base64,${frame.image}`)).blob()
      bitmap = await createImageBitmap(blob)
    } else {
      return
    }

    // 设置 Canvas 尺寸与图片一致
    canvas.width = bitmap.width
    canvas.height = bitmap.height
    // 绘制原帧
    ctx.drawImage(bitmap, 0, 0)
    // 释放 GPU 内存
    bitmap.close()

    // 绘制检测框
    for (const det of frame.detections) {
      const [x1, y1, x2, y2] = det.bbox
      const color = getClassColor(det.class_id)
      ctx.strokeStyle = color
      ctx.lineWidth = 3
      ctx.strokeRect(x1, y1, x2 - x1, y2 - y1)
      const label = `${det.class_name} ${(det.confidence * 100).toFixed(0)}%`
      ctx.font = 'bold 16px sans-serif'
      const textWidth = ctx.measureText(label).width
      ctx.fillStyle = color
      ctx.fillRect(x1, y1 - 24, textWidth + 8, 22)
      ctx.fillStyle = 'white'
      ctx.fillText(label, x1 + 4, y1 - 7)
    }
  } catch (e) {
    console.error('[Launch] 渲染帧失败', e)
  }
}

// 开始视频检测
const startVideoDetection = async () => {
  if (!canStreamDetect.value || !selectedStreamFile.value) return

  streamUploading.value = true

  try {
    const res = await inferenceApi.detectVideoStream(
      selectedStreamFile.value,
      selectedModelId.value!,
      confThreshold.value
    )

    if (res.data.success) {
      const jobId = res.data.job_id
      const streamUrl = res.data.stream_url
      const videoInfo = res.data.video_info

      // 构建类别颜色映射（来自数据库配置）
      const colors: Record<number, string> = {}
      for (const cat of (res.data.categories || [])) {
        colors[cat.id] = cat.color || '#FF0000'
      }
      categoryColors.value = colors

      streamJobId.value = jobId
      videoFps.value = videoInfo.fps || 24
      streamStats.value = {
        fps: videoInfo.fps || 24,
        total_frames: videoInfo.total_frames || 0,
        current_frame: 0,
        progress: 0,
        total_detections: 0,
        status: 'processing',
        buffer_frame: 0,
      }
      frameCache.value = []
      isReplaying.value = false

      // 创建 StreamClient 并连接
      const client = new StreamClient()
      client.onFrame((frame) => {
        // 暂停或重放中 → 前端缓存，不渲染
        if (streamPaused.value || isReplaying.value) {
          frameCache.value.push(frame)
          streamStats.value = {
            ...streamStats.value,
            buffer_frame: frame.progress?.buffer_frame || streamStats.value.buffer_frame || frame.frame_id,
            buffered_frames: frameCache.value.length,
          }
          return
        }

        streamStats.value = {
          ...streamStats.value,
          current_frame: frame.frame_id,
          total_detections: frame.stats.total_detections,
          progress: Math.min(99, Math.ceil((frame.frame_id / (videoInfo.total_frames || 1)) * 100)),
          buffer_frame: frame.progress?.buffer_frame || streamStats.value.buffer_frame,
          buffered_frames: frameCache.value.length,
        }
        renderFrame(frame)
        // 写入监控台（节流到每秒 5 条）
        addConsoleEntry('视频帧',
          `帧 #${frame.frame_id} | ${frame.detections.length} 个目标 | ${frame.stats.inference_ms}ms`,
          {
            frame_id: frame.frame_id,
            timestamp: frame.timestamp,
            detections: frame.detections,
            stats: frame.stats,
          },
          frame.frame_id,
        )
      })
      client.onComplete((totalFrames, totalDetections) => {
        streamComplete.value = true
        streamConnected.value = false
        streamPaused.value = false
        streamStats.value = {
          ...streamStats.value,
          progress: 100,
          current_frame: totalFrames,
          total_detections: totalDetections,
          status: 'completed',
        }
        addConsoleEntry('视频帧', `检测完成，共 ${totalFrames} 帧，${totalDetections} 个目标`, {
          total_frames: totalFrames,
          total_detections: totalDetections,
          status: 'completed',
        })
      })
      client.onError((error) => {
        ElMessage.error(`视频检测错误: ${error}`)
        streamConnected.value = false
      })
      client.onPaused(() => {
        streamPaused.value = true
      })
      client.onResumed(() => {
        streamPaused.value = false
      })
      client.onFpsUpdated((fps) => {
        videoFps.value = fps
      })
      client.onProgress((progress) => {
        streamStats.value = {
          ...streamStats.value,
          buffer_frame: progress.buffer_frame,
        }
      })

      client.connect(jobId, streamUrl)
      videoClient.value = client
      streamConnected.value = true
      streamPaused.value = false
      streamComplete.value = false
    }
  } catch (error: any) {
    const msg = error.response?.data?.detail || '启动视频检测失败'
    ElMessage.error(msg)
  } finally {
    streamUploading.value = false
  }
}

// 停止视频检测
const stopVideoDetection = () => {
  if (videoClient.value) {
    videoClient.value.disconnect()
    videoClient.value = null
  }
  if (streamJobId.value) {
    inferenceApi.stopVideoStream(streamJobId.value).catch(() => {})
    streamJobId.value = null
  }
  streamConnected.value = false
  streamComplete.value = false
  streamPaused.value = false
  categoryColors.value = {}
  streamStats.value = {
    fps: 24,
    total_frames: 0,
    current_frame: 0,
    progress: 0,
    total_detections: 0,
    status: 'pending',
    buffer_frame: 0,
  }
  frameCache.value = []
  isReplaying.value = false
}

// 暂停/继续切换
const togglePause = () => {
  const client = videoClient.value
  if (!client) return
  if (streamPaused.value) {
    // 恢复：先快速重放缓存帧，再切回实时
    if (frameCache.value.length > 0) {
      isReplaying.value = true
      burstReplay()
    }
    client.sendResume()
  } else {
    // 暂停：清旧缓存，开始累积
    frameCache.value = []
    isReplaying.value = false
    if (replayTimer !== null) {
      clearInterval(replayTimer)
      replayTimer = null
    }
    client.sendPause()
  }
}

/** 快速重放暂停期间缓存的帧 */
const burstReplay = () => {
  const tick = () => {
    const batch = Math.min(5, frameCache.value.length)
    for (let i = 0; i < batch; i++) {
      const frame = frameCache.value.shift()
      if (!frame) break
      renderFrame(frame)
      streamStats.value = {
        ...streamStats.value,
        current_frame: frame.frame_id,
        progress: Math.min(99, Math.ceil((frame.frame_id / (streamStats.value.total_frames || 1)) * 100)),
        buffered_frames: frameCache.value.length,
      }
    }

    if (frameCache.value.length > 0) {
      requestAnimationFrame(tick)
    } else {
      // 缓存耗尽，切回实时模式
      isReplaying.value = false
      streamStats.value.buffered_frames = 0
    }
  }
  requestAnimationFrame(tick)
}

// 调整帧率
const adjustFps = (delta: number) => {
  const newFps = Math.max(1, Math.min(60, videoFps.value + delta))
  videoFps.value = newFps
  videoClient.value?.setFps(newFps)
}

watch(mode, handleModeChange)

onMounted(() => {
  loadTrainedModels()
  loadRecentRecords()
})

onUnmounted(() => {
  stopVideoDetection()
})
</script>

<style lang="scss" scoped>
.launch {
  display: flex;
  flex-direction: column;
  height: 100%;
  gap: 16px;
}

.page-header {
  @apply flex justify-between items-center gap-4;
  flex-shrink: 0;
}

.header-info {
  @apply flex items-baseline;
}

.header-info .subtitle {
  @apply text-sm text-[var(--text-muted)] ml-3;
}

.header-info h2 {
  @apply text-2xl font-semibold;
  background: linear-gradient(90deg, var(--text-primary), var(--accent-cyan));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

/* Tab 切换 */
.mode-tabs {
  @apply flex gap-1 bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-lg p-1;
}

.mode-tab {
  @apply flex items-center gap-2 px-4 py-1.5 rounded-md text-sm font-medium cursor-pointer transition-all;
  @apply text-[var(--text-secondary)] bg-transparent border-none;

  svg {
    @apply w-4 h-4;
  }

  &:hover {
    @apply text-[var(--text-primary)];
  }

  &.active {
    @apply bg-[var(--accent-cyan)] text-black;
  }
}

/* 主内容区 */
.launch-body {
  display: grid;
  grid-template-columns: 360px 1fr;
  gap: 16px;
  flex: 1;
  min-height: 0;
}

/* 配置面板 */
.config-panel {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.panel-header {
  @apply flex justify-between items-center px-5 py-3 border-b border-[var(--border-color)];
}

.header-left {
  @apply flex items-center gap-2;
}

.panel-icon {
  @apply w-4 h-4 text-[var(--accent-cyan)];
}

.panel-header h3 {
  @apply text-sm font-semibold;
}

.config-content {
  @apply p-5 flex flex-col gap-4;
  overflow-y: auto;
  flex: 1;
}

.config-section {
  @apply flex flex-col gap-2;
}

.section-label {
  @apply text-xs text-[var(--text-secondary)] uppercase tracking-wide;
}

.select-wrapper {
  select {
    @apply w-full px-3 py-2.5 bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-lg text-sm text-[var(--text-primary)] cursor-pointer appearance-none;

    &:focus {
      @apply outline-none border-[var(--accent-cyan)];
    }

    option {
      @apply bg-[var(--bg-card)];
    }
  }
}

.model-info {
  @apply flex gap-2 mt-1;
}

.info-tag {
  @apply text-xs px-2 py-1 bg-[var(--bg-secondary)] rounded text-[var(--text-muted)];
}

.range-slider {
  @apply w-full h-1.5 bg-[var(--bg-secondary)] rounded-lg appearance-none cursor-pointer;

  &::-webkit-slider-thumb {
    @apply w-3.5 h-3.5 bg-[var(--accent-cyan)] rounded-full appearance-none cursor-pointer;
  }
}

.upload-zone {
  @apply border-2 border-dashed border-[var(--border-color)] rounded-lg p-6 text-center cursor-pointer transition-all;

  &.dragging {
    @apply border-[var(--accent-cyan)] bg-[rgba(0,240,255,0.05)];
  }

  &.disabled {
    @apply opacity-50 cursor-not-allowed;
  }
}

.upload-hint {
  @apply flex flex-col items-center gap-2 text-[var(--text-muted)];

  svg {
    @apply w-7 h-7;
  }
}

.file-name {
  @apply text-sm text-[var(--accent-cyan)] truncate max-w-full;
}

:deep(.detect-btn) {
  @apply w-full py-2.5 text-sm font-medium rounded-lg mt-2;
  background: var(--accent-cyan) !important;
  border-color: var(--accent-cyan) !important;
  color: black !important;

  &:hover:not(:disabled) {
    background: #00d4e0 !important;
  }

  &:disabled {
    @apply opacity-50 cursor-not-allowed;
  }
}

/* 结果面板 */
.result-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
  position: relative;
}

.result-count {
  @apply text-xs text-[var(--accent-cyan)] px-2.5 py-1 bg-[rgba(0,240,255,0.1)] rounded-full;
}

.result-image-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  background: var(--bg-primary);
  position: relative;
}

.image-area {
  flex: 1;
  overflow: auto;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  min-height: 0;
}

.video-container {
  @apply relative flex-1 overflow-hidden flex items-center justify-center p-3 bg-[var(--bg-primary)];

  video {
    @apply max-w-full max-h-full rounded;
  }
}

.result-image {
  @apply max-w-full max-h-full rounded;
  transform: scale(v-bind(zoomLevel));
  transform-origin: center;
}

.bbox-overlay {
  @apply absolute inset-0 w-full h-full pointer-events-none;
  overflow: visible;
}

.zoom-controls {
  @apply flex items-center justify-center gap-4 p-2 border-t border-[var(--border-color)] flex-shrink-0;
  background: var(--bg-secondary);
}

.zoom-btn {
  @apply w-7 h-7 flex items-center justify-center bg-[var(--bg-primary)] border border-[var(--border-color)] rounded text-sm font-bold cursor-pointer;
  &:hover {
    @apply border-[var(--accent-cyan)] text-[var(--accent-cyan)];
  }
}

.zoom-level {
  @apply font-mono text-xs text-[var(--text-secondary)] min-w-[3.5rem] text-center;
}

.result-loading {
  @apply flex-1 flex flex-col items-center justify-center gap-4;

  .loading-spinner {
    @apply w-10 h-10 border-3 border-[var(--border-color)] border-t-[var(--accent-cyan)] rounded-full animate-spin;
  }

  span {
    @apply text-sm text-[var(--text-muted)];
  }
}

/* 视频检测样式 */
.empty-result {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  color: var(--text-muted);

  .empty-icon {
    @apply w-16 h-16 mb-3 flex items-center justify-center;

    svg {
      @apply w-full h-full opacity-25;
    }
  }

  p {
    @apply text-sm text-[var(--text-secondary)] mb-1;
  }

  span {
    @apply text-xs;
  }
}

/* 检测列表 */
.detections-list {
  @apply max-h-[72px] overflow-y-auto border-t border-[var(--border-color)] flex flex-wrap content-start gap-1 p-2;
  flex-shrink: 0;
}

.detection-item {
  @apply inline-flex items-center gap-1 text-xs px-1.5 py-0.5 rounded bg-[var(--bg-secondary)] border border-[var(--border-color)];
}

.det-class {
  @apply px-2 py-0.5 rounded text-white text-[10px];
}

.det-conf {
  @apply text-[var(--accent-cyan)] font-mono;
}

.det-bbox {
  @apply text-[var(--text-muted)] font-mono text-[10px];
}

/* 视频检测样式 */
.result-stream-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.stream-container {
  flex: 1;
  overflow: auto;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 12px;
  background: var(--bg-primary);
}

.stream-canvas {
  max-width: 100%;
  max-height: 100%;
  border-radius: 8px;
}

.stream-progress {
  @apply flex items-center gap-4 p-3 border-t border-[var(--border-color)];
  background: var(--bg-secondary);
}

.progress-bar-dual {
  flex: 1;
  height: 6px;
  background: var(--border-color);
  border-radius: 3px;
  overflow: hidden;
  position: relative;
}

.progress-buffer {
  position: absolute;
  left: 0;
  top: 0;
  height: 100%;
  background: rgba(0, 240, 255, 0.2);
  border-radius: 3px;
  transition: width 0.5s ease;
}

.progress-playback {
  position: absolute;
  left: 0;
  top: 0;
  height: 100%;
  background: var(--accent-cyan);
  border-radius: 3px;
  transition: width 0.3s ease;
  box-shadow: 0 0 8px rgba(0, 240, 255, 0.5);
  z-index: 1;
}

.buffer-info {
  @apply text-xs font-mono text-[var(--text-muted)];
  white-space: nowrap;
}

.progress-text {
  @apply text-xs font-mono text-[var(--text-secondary)];
  white-space: nowrap;
}

.progress-controls {
  @apply flex items-center gap-3 ml-auto flex-shrink-0;
}

.ctrl-btn {
  @apply w-7 h-7 flex items-center justify-center bg-transparent border border-[var(--border-color)] rounded text-[var(--text-secondary)] cursor-pointer transition-all;
  &:hover {
    @apply border-[var(--accent-cyan)] text-[var(--accent-cyan)];
  }
  svg {
    @apply w-3.5 h-3.5;
  }
}

.fps-control {
  @apply flex items-center gap-1.5;
}

.ctrl-btn-sm {
  @apply w-5 h-5 flex items-center justify-center bg-transparent border border-[var(--border-color)] rounded text-[var(--text-muted)] text-xs cursor-pointer transition-all;
  &:hover:not(:disabled) {
    @apply border-[var(--accent-cyan)] text-[var(--accent-cyan)];
  }
  &:disabled {
    @apply opacity-30 cursor-not-allowed;
  }
}

.fps-value {
  @apply text-xs font-mono text-[var(--accent-cyan)] min-w-[3rem] text-center;
}

.stream-complete {
  @apply flex items-center justify-center p-3 border-t border-[var(--border-color)];
  background: var(--bg-secondary);
  color: var(--accent-green);
  font-size: 13px;
}

.stream-stats {
  @apply grid grid-cols-3 gap-2 p-3 mb-3 rounded-lg;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
}

.stat-item {
  @apply flex flex-col items-center gap-1;
}

.stat-label {
  @apply text-xs text-[var(--text-muted)];
}

.stat-value {
  @apply text-sm font-mono font-semibold text-[var(--accent-cyan)];
}

/* ===== 监控台样式 ===== */
.result-body {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.console-panel {
  flex-shrink: 0;
  border-top: 1px solid var(--border-color);
  background: var(--bg-primary);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.console-divider {
  flex-shrink: 0;
  height: 4px;
  cursor: row-resize;
  background: transparent;
  position: relative;
  z-index: 2;

  &:hover {
    background: rgba(0, 240, 255, 0.15);
  }
}

.console-header {
  @apply flex items-center justify-between px-4 py-2 cursor-pointer select-none;
  flex-shrink: 0;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);

  &:hover {
    background: var(--bg-hover);
  }
}

.console-header-left {
  @apply flex items-center gap-2 text-sm text-[var(--text-secondary)];
}

.console-icon {
  @apply w-4 h-4;
}

.console-count {
  @apply text-xs px-1.5 py-0.5 rounded bg-[rgba(0,240,255,0.1)] text-[var(--accent-cyan)];
}

.console-header-right {
  @apply flex items-center gap-2;
}

.console-clear-btn {
  @apply text-xs px-2 py-0.5 rounded border border-[var(--border-color)] bg-transparent text-[var(--text-muted)] cursor-pointer;

  &:hover {
    @apply border-[#ff4466] text-[#ff4466];
  }
}

.console-toggle {
  @apply w-4 h-4 text-[var(--text-muted)];
}

.console-body {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
  padding: 4px 0;
}

.console-entry {
  @apply mx-1 my-px rounded text-xs;
  background: rgba(0, 0, 0, 0.15);

  &.expanded {
    background: rgba(0, 0, 0, 0.3);
  }
}

.console-entry-header {
  @apply flex items-center gap-2 px-3 py-1.5 cursor-pointer select-none;

  &:hover {
    background: rgba(255, 255, 255, 0.03);
  }
}

.entry-time {
  @apply font-mono text-[10px] text-[var(--text-muted)] flex-shrink-0;
  min-width: 60px;
}

.entry-source {
  @apply text-[10px] px-1.5 py-0.5 rounded flex-shrink-0 font-medium;

  &.src-image {
    background: rgba(0, 240, 255, 0.15);
    color: var(--accent-cyan);
  }

  &.src-video {
    background: rgba(255, 221, 0, 0.15);
    color: var(--accent-yellow);
  }
}

.entry-summary {
  @apply text-[var(--text-secondary)] truncate flex-1;
}

.entry-copy-btn {
  @apply flex items-center justify-center w-5 h-5 border-none bg-transparent text-[var(--text-muted)] cursor-pointer rounded opacity-0 flex-shrink-0;
  transition: opacity 0.15s;

  .console-entry-header:hover & {
    opacity: 1;
  }

  &:hover {
    @apply text-[var(--accent-cyan)] bg-[rgba(0,240,255,0.1)];
  }

  svg {
    @apply w-3 h-3;
  }
}

.entry-toggle {
  @apply text-[var(--text-muted)] font-mono text-xs flex-shrink-0 w-4 text-center;
}

.console-entry-body {
  @apply px-3 pb-2;
}

.console-json {
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 10px;
  line-height: 1.6;
  color: #e0e0e0;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 4px;
  padding: 8px;
  margin: 0;
  max-height: 400px;
  overflow-y: auto;
  overflow-x: auto;
  white-space: pre;
  word-wrap: normal;
}

.console-empty {
  @apply flex items-center justify-center py-8 text-xs text-[var(--text-muted)];
}

.section-label-row {
  @apply flex items-center justify-between cursor-pointer;
}

.clear-btn {
  @apply text-xs px-2 py-0.5 rounded border border-[var(--border-color)] bg-transparent text-[var(--text-muted)] cursor-pointer;
  &:hover {
    @apply border-[#ff4466] text-[#ff4466];
  }
}

.chevron-icon {
  @apply w-4 h-4 text-[var(--text-muted)];
}

.recent-records {
  @apply mt-2 flex flex-col gap-2 max-h-64 overflow-y-auto;
}

.records-empty {
  @apply text-sm text-[var(--text-muted)] text-center py-4;
}

.record-item {
  @apply flex items-center gap-2 p-2 rounded-lg bg-[var(--bg-primary)] border border-[var(--border-color)];

  &.expired {
    @apply opacity-50;
  }
}

.record-thumb {
  @apply w-10 h-10 rounded object-cover flex-shrink-0 border border-[var(--border-color)];
}

.record-info {
  @apply flex-1 min-w-0 flex flex-col gap-0.5;
}

.record-name {
  @apply text-sm text-[var(--text-primary)] truncate font-medium;
}

.record-meta {
  @apply text-xs text-[var(--text-secondary)];
}

.record-time {
  @apply text-xs text-[var(--text-muted)];
}

.rerun-btn {
  @apply flex-shrink-0 text-xs py-1 px-2;
}

</style>