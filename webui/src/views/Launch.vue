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
          <ImageIcon />
          图片检测
        </button>
        <button
          class="mode-tab"
          :class="{ active: mode === 'video' }"
          @click="mode = 'video'"
        >
          <VideoIcon />
          视频检测
        </button>
      </div>
    </div>

    <div class="launch-body">
      <!-- 左侧：配置面板 -->
      <div class="config-panel vg-card">
        <div class="panel-header">
          <div class="header-left">
            <BrainIcon class="panel-icon" />
            <h3>检测配置</h3>
          </div>
        </div>

        <div class="config-content">
          <!-- 模型选择 -->
          <div class="config-section">
            <label class="section-label">选择模型</label>
            <div class="select-wrapper">
              <select v-model="selectedModelId" :disabled="detecting">
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
                  <UploadIcon />
                  <span v-if="!selectedFile">拖拽或点击上传</span>
                  <span v-else class="file-name">{{ selectedFile.name }}</span>
                </div>
              </div>
            </div>
          </template>

          <!-- 视频模式 -->
          <template v-else>
            <div class="config-section">
              <label class="section-label">上传视频</label>
              <div
                class="upload-zone"
                :class="{ dragging: isDragging, disabled: detecting }"
                @dragover.prevent="isDragging = true"
                @dragleave="isDragging = false"
                @drop.prevent="handleVideoDrop"
                @click="triggerVideoInput"
              >
                <input
                  ref="videoInputRef"
                  type="file"
                  accept="video/*"
                  @change="handleVideoSelect"
                  style="display: none"
                />
                <div class="upload-hint">
                  <VideoUploadIcon />
                  <span v-if="!selectedVideoFile">拖拽或点击上传视频</span>
                  <span v-else class="file-name">{{ selectedVideoFile.name }}</span>
                </div>
              </div>
            </div>
          </template>

          <!-- 检测按钮 -->
          <el-button
            class="detect-btn"
            type="primary"
            :disabled="!canDetect || detecting"
            :loading="detecting"
            @click="startDetection"
          >
            {{ detecting ? (mode === 'video' ? '上传中...' : '检测中...') : (videoJobProcessing ? '处理中...' : '开始检测') }}
          </el-button>
        </div>
      </div>

      <!-- 右侧：结果显示 -->
      <div class="result-panel vg-card">
        <div class="panel-header">
          <div class="header-left">
            <EyeIcon class="panel-icon" />
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

        <!-- 视频检测结果 -->
        <div v-else-if="videoResultPath" class="result-video-wrapper">
          <div class="video-container">
            <video :src="videoResultPath" controls class="result-video"></video>
          </div>
        </div>

        <!-- 视频处理进度 -->
        <div v-else-if="videoJobProcessing" class="video-progress-wrapper">
          <div class="progress-indicator">
            <div class="progress-ring">
              <svg viewBox="0 0 100 100">
                <circle cx="50" cy="50" r="42" class="progress-track" />
                <circle
                  cx="50" cy="50" r="42"
                  class="progress-fill"
                  :style="{ strokeDashoffset: 264 - (264 * videoProgress.progress / 100) }"
                />
              </svg>
              <span class="progress-value">{{ videoProgress.progress }}%</span>
            </div>
            <div class="progress-detail">
              <span class="progress-label">视频检测中</span>
              <span class="progress-frames">
                帧 {{ videoProgress.current_frame }} / {{ videoProgress.total_frames }}
              </span>
              <span class="progress-detections" v-if="videoProgress.detections_count > 0">
                已检测 {{ videoProgress.detections_count }} 个目标
              </span>
            </div>
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
            <ImageIcon v-if="mode === 'image'" />
            <VideoIcon v-else />
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
import { ref, computed, onMounted, onUnmounted, watch, h } from 'vue'
import { ElMessage } from 'element-plus'
import { inferenceApi } from '@/api'

// 图标组件
const BrainIcon = () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
  h('path', { d: 'M9.5 2A2.5 2.5 0 0112 4.5v15a2.5 2.5 0 01-4.96.44 2.5 2.5 0 01-2.96-3.08 3 3 0 01-.34-5.58 2.5 2.5 0 011.32-4.24 2.5 2.5 0 011.98-3A2.5 2.5 0 019.5 2z' }),
  h('path', { d: 'M14.5 2A2.5 2.5 0 0112 4.5v15a2.5 2.5 0 004.96.44 2.5 2.5 0 002.96-3.08 3 3 0 00.34-5.58 2.5 2.5 0 00-1.32-4.24 2.5 2.5 0 00-1.98-3A2.5 2.5 0 0014.5 2z' })
])

const ImageIcon = () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
  h('rect', { x: '3', y: '3', width: '18', height: '18', rx: '2', ry: '2' }),
  h('circle', { cx: '8.5', cy: '8.5', r: '1.5' }),
  h('polyline', { points: '21 15 16 10 5 21' })
])

const VideoIcon = () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
  h('polygon', { points: '23 7 16 12 23 17 23 7' }),
  h('rect', { x: '1', y: '5', width: '15', height: '14', rx: '2', ry: '2' })
])

const UploadIcon = () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
  h('path', { d: 'M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4' }),
  h('polyline', { points: '17 8 12 3 7 8' }),
  h('line', { x1: '12', y1: '3', x2: '12', y2: '15' })
])

const VideoUploadIcon = () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
  h('path', { d: 'M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4' }),
  h('polyline', { points: '17 8 12 3 7 8' }),
  h('line', { x1: '12', y1: '3', x2: '12', y2: '15' }),
  h('polyline', { points: '10 13 12 15 14 13' })
])

const EyeIcon = () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
  h('path', { d: 'M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z' }),
  h('circle', { cx: '12', cy: '12', r: '3' })
])

// 状态
const mode = ref<'image' | 'video'>('image')
const trainedModels = ref<any[]>([])
const selectedModelId = ref<number | null>(null)
const confThreshold = ref(0.25)
const selectedFile = ref<File | null>(null)
const selectedVideoFile = ref<File | null>(null)
const fileInputRef = ref<HTMLInputElement | null>(null)
const videoInputRef = ref<HTMLInputElement | null>(null)
const isDragging = ref(false)
const isLoading = ref(false)
const detecting = ref(false)

const resultImage = ref<string | null>(null)
const videoResultPath = ref<string | null>(null)
const detections = ref<any[]>([])
const imageSize = ref({ width: 0, height: 0 })
const zoomLevel = ref(1)

// 视频检测任务状态
const videoJobId = ref<string | null>(null)
const videoProgress = ref({ progress: 0, current_frame: 0, total_frames: 0, detections_count: 0, status: 'pending' })
let videoPollingTimer: number | null = null

const videoJobProcessing = computed(() => {
  return mode.value === 'video' && videoJobId.value !== null && videoProgress.value.status !== 'completed' && videoProgress.value.status !== 'failed'
})

const selectedModel = computed(() => {
  return trainedModels.value.find(m => m.id === selectedModelId.value)
})

const canDetect = computed(() => {
  if (mode.value === 'image') {
    return selectedModelId.value && selectedFile.value && !detecting.value
  }
  return selectedModelId.value && selectedVideoFile.value && !detecting.value && !videoJobProcessing.value
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

// 文件选择 - 视频
const handleVideoSelect = (event: Event) => {
  const input = event.target as HTMLInputElement
  if (input.files && input.files[0]) {
    selectedVideoFile.value = input.files[0]
    clearResults()
  }
}

const handleVideoDrop = (event: DragEvent) => {
  isDragging.value = false
  if (event.dataTransfer?.files && event.dataTransfer.files[0]) {
    const file = event.dataTransfer.files[0]
    if (file.type.startsWith('video/')) {
      selectedVideoFile.value = file
      clearResults()
    }
  }
}

const triggerVideoInput = () => {
  videoInputRef.value?.click()
}

// 清除结果
const clearResults = () => {
  resultImage.value = null
  videoResultPath.value = null
  detections.value = []
  imageSize.value = { width: 0, height: 0 }
  stopVideoPolling()
  videoJobId.value = null
  videoProgress.value = { progress: 0, current_frame: 0, total_frames: 0, detections_count: 0, status: 'pending' }
}

// 加载图片获取尺寸
const loadImageSize = (src: string) => {
  const img = new Image()
  img.onload = () => {
    imageSize.value = { width: img.naturalWidth, height: img.naturalHeight }
  }
  img.src = src
}

// 轮询视频检测进度
const startVideoPolling = () => {
  stopVideoPolling()
  const poll = async () => {
    if (!videoJobId.value) return
    try {
      const res = await inferenceApi.getVideoJobStatus(videoJobId.value)
      const status = res.data
      videoProgress.value = status

      if (status.status === 'completed') {
        videoPollingTimer = null
        videoResultPath.value = inferenceApi.getVideoResultUrl(videoJobId.value)
        detections.value = []  // 视频检测暂不返回详细列表
        videoJobId.value = null
      } else if (status.status === 'failed') {
        videoPollingTimer = null
        ElMessage.error(status.error || '视频检测失败')
        videoJobId.value = null
      } else {
        videoPollingTimer = window.setTimeout(poll, 1500)
      }
    } catch (e) {
      console.error('轮询视频进度失败', e)
      videoPollingTimer = window.setTimeout(poll, 3000)
    }
  }
  poll()
}

const stopVideoPolling = () => {
  if (videoPollingTimer !== null) {
    clearTimeout(videoPollingTimer)
    videoPollingTimer = null
  }
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
    } else if (mode.value === 'video' && selectedVideoFile.value) {
      const res = await inferenceApi.detectVideo(selectedVideoFile.value, selectedModelId.value!, confThreshold.value)
      if (res.data.success) {
        videoJobId.value = res.data.job_id
        // 开始轮询进度
        startVideoPolling()
      }
    }
  } catch (error: any) {
    const msg = error.response?.data?.detail || '检测失败'
    ElMessage.error(msg)
    videoJobId.value = null
  } finally {
    detecting.value = false
  }
}

// 切换模式时清除状态
const handleModeChange = () => {
  clearResults()
}

watch(mode, handleModeChange)

onMounted(() => {
  loadTrainedModels()
})

onUnmounted(() => {
  stopVideoPolling()
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
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.result-video-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.image-container {
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

/* 视频处理进度 */
.video-progress-wrapper {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.progress-indicator {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
}

.progress-ring {
  position: relative;
  width: 120px;
  height: 120px;

  svg {
    width: 100%;
    height: 100%;
    transform: rotate(-90deg);
  }

  .progress-track {
    fill: none;
    stroke: var(--border-color);
    stroke-width: 6;
  }

  .progress-fill {
    fill: none;
    stroke: var(--accent-cyan);
    stroke-width: 6;
    stroke-linecap: round;
    stroke-dasharray: 264;
    stroke-dashoffset: 264;
    transition: stroke-dashoffset 0.5s ease;
  }

  .progress-value {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 22px;
    font-weight: 700;
    font-family: 'JetBrains Mono', monospace;
    color: var(--accent-cyan);
  }
}

.progress-detail {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.progress-label {
  font-size: 14px;
  color: var(--text-secondary);
  font-weight: 500;
}

.progress-frames {
  font-size: 12px;
  font-family: 'JetBrains Mono', monospace;
  color: var(--text-muted);
}

.progress-detections {
  font-size: 12px;
  color: var(--accent-green);
}

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
</style>