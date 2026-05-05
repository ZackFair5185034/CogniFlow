<template>
  <div class="launch">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-info">
        <h2>模型测试</h2>
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
              <div class="stat-item">
                <span class="stat-label">检测数</span>
                <span class="stat-value">{{ streamStats.total_detections }}</span>
              </div>
            </div>
          </template>

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
          <span class="result-count" v-if="detections.length > 0">
            {{ detections.length }} 个目标
          </span>
        </div>

        <!-- 图片检测结果 -->
        <div v-if="resultImage" class="result-image-wrapper">
          <div class="image-container">
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
            <div class="progress-bar">
              <div class="progress-fill" :style="{ width: `${streamStats.progress}%` }"></div>
            </div>
            <span class="progress-text">帧 {{ streamStats.current_frame }} / {{ streamStats.total_frames }}</span>
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

        <!-- 检测详情列表 -->
        <div class="detections-list" v-if="detections.length > 0">
          <div class="detection-item" v-for="(det, idx) in detections" :key="idx">
            <span class="det-class" :style="{ background: getClassColor(det.class_id) }">
              {{ det.class_name }}
            </span>
            <span class="det-conf">{{ (det.confidence * 100).toFixed(1) }}%</span>
            <span class="det-bbox">x: {{ Math.round(det.bbox[0]) }}, y: {{ Math.round(det.bbox[1]) }}, w: {{ Math.round(det.bbox[2] - det.bbox[0]) }}, h: {{ Math.round(det.bbox[3] - det.bbox[1]) }}</span>
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
const streamStats = ref<StreamStats>({
  fps: 24,
  total_frames: 0,
  current_frame: 0,
  progress: 0,
  total_detections: 0,
  status: 'pending',
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
  const colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD', '#98D8C8', '#F7DC6F']
  return colors[classId % colors.length]
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

// 加载图片获取尺寸
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
      }
    }
  } catch (error: any) {
    const msg = error.response?.data?.detail || '检测失败'
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
const renderFrame = (frame: StreamFrame) => {
  const canvas = streamCanvasRef.value
  if (!canvas) return

  const ctx = canvas.getContext('2d')
  if (!ctx) return

  const img = new Image()
  img.onload = () => {
    // 设置 Canvas 尺寸与图片一致
    canvas.width = img.width
    canvas.height = img.height
    // 绘制原帧
    ctx.drawImage(img, 0, 0)
    // 绘制检测框
    for (const det of frame.detections) {
      const [x1, y1, x2, y2] = det.bbox
      const color = getClassColor(det.class_id)
      // 绘制矩形框
      ctx.strokeStyle = color
      ctx.lineWidth = 3
      ctx.strokeRect(x1, y1, x2 - x1, y2 - y1)
      // 绘制标签背景
      const label = `${det.class_name} ${(det.confidence * 100).toFixed(0)}%`
      ctx.font = 'bold 16px sans-serif'
      const textWidth = ctx.measureText(label).width
      ctx.fillStyle = color
      ctx.fillRect(x1, y1 - 24, textWidth + 8, 22)
      // 绘制标签文字
      ctx.fillStyle = 'white'
      ctx.fillText(label, x1 + 4, y1 - 7)
    }
  }
  img.src = `data:image/jpeg;base64,${frame.image}`
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

      streamJobId.value = jobId
      streamStats.value = {
        fps: videoInfo.fps || 24,
        total_frames: videoInfo.total_frames || 0,
        current_frame: 0,
        progress: 0,
        total_detections: 0,
        status: 'processing',
      }

      // 创建 StreamClient 并连接
      const client = new StreamClient()
      client.onFrame((frame) => {
        streamStats.value = {
          ...streamStats.value,
          current_frame: frame.frame_id,
          total_detections: frame.stats.total_detections,
          progress: Math.min(99, Math.ceil((frame.frame_id / (videoInfo.total_frames || 1)) * 100)),
        }
        renderFrame(frame)
      })
      client.onComplete((totalFrames, totalDetections) => {
        streamComplete.value = true
        streamConnected.value = false
        streamStats.value = {
          ...streamStats.value,
          progress: 100,
          current_frame: totalFrames,
          total_detections: totalDetections,
          status: 'completed',
        }
      })
      client.onError((error) => {
        ElMessage.error(`视频检测错误: ${error}`)
        streamConnected.value = false
      })

      client.connect(jobId, streamUrl)
      videoClient.value = client
      streamConnected.value = true
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
  streamStats.value = {
    fps: 24,
    total_frames: 0,
    current_frame: 0,
    progress: 0,
    total_detections: 0,
    status: 'pending',
  }
}

watch(mode, handleModeChange)

onMounted(() => {
  loadTrainedModels()
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
  @apply flex justify-between items-center;
  flex-shrink: 0;
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
  @apply flex items-center gap-2 px-5 py-2 rounded-md text-sm font-medium cursor-pointer transition-all;
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
}

.result-count {
  @apply text-xs text-[var(--accent-cyan)] px-2.5 py-1 bg-[rgba(0,240,255,0.1)] rounded-full;
}

.result-image-wrapper {
  flex: 1;
  overflow: auto;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 12px;
  background: var(--bg-primary);
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
  @apply flex items-center justify-center gap-4 p-2 border-t border-[var(--border-color)];
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
  @apply max-h-48 overflow-y-auto border-t border-[var(--border-color)];
  flex-shrink: 0;
}

.detection-item {
  @apply flex items-center gap-3 px-4 py-2 text-xs border-b border-[var(--border-color)] last:border-b-0;
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

.progress-bar {
  flex: 1;
  height: 6px;
  background: var(--border-color);
  border-radius: 3px;
  overflow: hidden;
  position: relative;
}

.progress-fill {
  position: absolute;
  left: 0;
  top: 0;
  height: 100%;
  background: var(--accent-cyan);
  border-radius: 3px;
  transition: width 0.3s ease;
}

.progress-text {
  @apply text-xs font-mono text-[var(--text-secondary)];
  white-space: nowrap;
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
</style>