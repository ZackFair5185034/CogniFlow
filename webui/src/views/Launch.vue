<template>
  <div class="launch">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-info">
        <h2>模型测试</h2>
        <span class="subtitle">图片目标检测</span>
      </div>
    </div>

    <div class="launch-grid">
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

          <!-- 文件上传 -->
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

          <!-- 检测按钮 -->
          <el-button
            class="detect-btn"
            type="primary"
            :disabled="!canDetect || detecting"
            :loading="detecting"
            @click="startDetection"
          >
            {{ detecting ? '检测中...' : '开始检测' }}
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

        <!-- 图片检测结果（带bbox叠加层） -->
        <div class="result-image-wrapper" v-if="resultImage">
          <div class="image-container">
            <img :src="resultImage" alt="检测结果" class="result-image" />
            <!-- BBox 叠加层 -->
            <svg class="bbox-overlay" :viewBox="`0 0 ${imageSize.width} ${imageSize.height}`">
              <g v-for="(det, idx) in detections" :key="idx">
                <!-- 边框矩形 -->
                <rect
                  :x="det.bbox[0]"
                  :y="det.bbox[1]"
                  :width="det.bbox[2] - det.bbox[0]"
                  :height="det.bbox[3] - det.bbox[1]"
                  :stroke="getClassColor(det.class_id)"
                  stroke-width="2"
                  fill="none"
                />
                <!-- 类别标签背景 -->
                <rect
                  :x="det.bbox[0]"
                  :y="det.bbox[1] - 20"
                  width="80"
                  height="20"
                  :fill="getClassColor(det.class_id)"
                />
                <!-- 类别标签文字 -->
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

          <!-- 缩放控制 -->
          <div class="zoom-controls">
            <button class="zoom-btn" @click="zoomLevel = Math.min(2, zoomLevel + 0.25)">+</button>
            <span class="zoom-level">{{ (zoomLevel * 100).toFixed(0) }}%</span>
            <button class="zoom-btn" @click="zoomLevel = Math.max(0.5, zoomLevel - 0.25)">-</button>
          </div>
        </div>

        <!-- 加载状态 -->
        <div class="result-loading" v-else-if="detecting">
          <div class="loading-spinner"></div>
          <span>图片检测中...</span>
        </div>

        <!-- 空状态 -->
        <div class="empty-result" v-else>
          <div class="empty-icon">
            <ImageIcon />
          </div>
          <p>暂无检测结果</p>
          <span>上传图片开始检测</span>
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
import { ref, computed, onMounted, h } from 'vue'
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

const UploadIcon = () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
  h('path', { d: 'M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4' }),
  h('polyline', { points: '17 8 12 3 7 8' }),
  h('line', { x1: '12', y1: '3', x2: '12', y2: '15' })
])

const EyeIcon = () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
  h('path', { d: 'M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z' }),
  h('circle', { cx: '12', cy: '12', r: '3' })
])

// 状态
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

// 文件选择
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
    selectedFile.value = event.dataTransfer.files[0]
    clearResults()
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
  if (!canDetect.value || !selectedFile.value) return

  isLoading.value = true
  detecting.value = true
  clearResults()

  try {
    const res = await inferenceApi.detectImage(selectedFile.value, selectedModelId.value!, confThreshold.value)
    if (res.data.success) {
      resultImage.value = res.data.result_image_base64
      detections.value = res.data.detections || []
      loadImageSize(res.data.result_image_base64)
    }
  } catch (error: any) {
    const msg = error.response?.data?.detail || '检测失败'
    ElMessage.error(msg)
  } finally {
    isLoading.value = false
    detecting.value = false
  }
}

onMounted(() => {
  loadTrainedModels()
})
</script>

<style lang="scss" scoped>
.launch {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.page-header {
  @apply flex justify-between items-center;
}

.header-info h2 {
  @apply text-2xl font-semibold;
  background: linear-gradient(90deg, var(--text-primary), var(--accent-cyan));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.header-info .subtitle {
  @apply text-sm text-[var(--text-muted)] ml-3;
}

/* 网格布局 */
.launch-grid {
  display: grid;
  grid-template-columns: 400px 1fr;
  gap: 24px;
  min-height: 600px;
}

/* 配置面板 */
.config-panel {
  height: fit-content;
}

.panel-header {
  @apply flex justify-between items-center px-6 py-4 border-b border-[var(--border-color)];
}

.header-left {
  @apply flex items-center gap-3;
}

.panel-icon {
  @apply w-5 h-5 text-[var(--accent-cyan)];
}

.panel-header h3 {
  @apply text-base font-semibold;
}

.config-content {
  @apply p-6 flex flex-col gap-5;
}

.config-section {
  @apply flex flex-col gap-2;
}

.section-label {
  @apply text-xs text-[var(--text-secondary)] uppercase tracking-wide;
}

.select-wrapper {
  select {
    @apply w-full px-4 py-3 bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-lg text-[var(--text-primary)] cursor-pointer appearance-none;

    &:focus {
      @apply outline-none border-[var(--accent-cyan)];
    }

    option {
      @apply bg-[var(--bg-card)] p-3;
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
  @apply w-full h-2 bg-[var(--bg-secondary)] rounded-lg appearance-none cursor-pointer;

  &::-webkit-slider-thumb {
    @apply w-4 h-4 bg-[var(--accent-cyan)] rounded-full appearance-none cursor-pointer;
  }
}

.upload-zone {
  @apply border-2 border-dashed border-[var(--border-color)] rounded-lg p-8 text-center cursor-pointer transition-all;

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
    @apply w-8 h-8;
  }
}

.file-name {
  @apply text-sm text-[var(--accent-cyan)] truncate max-w-full;
}

:deep(.detect-btn) {
  @apply w-full py-3 text-base font-medium rounded-lg;
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
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.result-count {
  @apply text-sm text-[var(--accent-cyan)] px-3 py-1 bg-[rgba(0,240,255,0.1)] rounded-full;
}

.result-image-wrapper {
  @apply flex-1 flex flex-col overflow-hidden;
}

.image-container {
  @apply relative flex-1 overflow-auto flex items-center justify-center p-4 bg-[var(--bg-primary)];
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
  @apply flex items-center justify-center gap-4 p-3 border-t border-[var(--border-color)];
  background: var(--bg-secondary);
}

.zoom-btn {
  @apply w-8 h-8 flex items-center justify-center bg-[var(--bg-primary)] border border-[var(--border-color)] rounded text-lg font-bold cursor-pointer;
  &:hover {
    @apply border-[var(--accent-cyan)] text-[var(--accent-cyan)];
  }
}

.zoom-level {
  @apply font-mono text-sm text-[var(--text-secondary)] min-w-16 text-center;
}

.result-loading {
  @apply flex-1 flex flex-col items-center justify-center gap-4 p-8;

  .loading-spinner {
    @apply w-12 h-12 border-4 border-[var(--border-color)] border-t-[var(--accent-cyan)] rounded-full animate-spin;
  }
}

.empty-result {
  @apply flex-1 flex flex-col items-center justify-center text-center text-[var(--text-muted)];

  .empty-icon {
    @apply w-20 h-20 mb-4 flex items-center justify-center;

    svg {
      @apply w-full h-full opacity-30;
    }
  }

  p {
    @apply text-base text-[var(--text-secondary)] mb-1;
  }

  span {
    @apply text-sm;
  }
}

/* 检测列表 */
.detections-list {
  @apply max-h-60 overflow-y-auto border-t border-[var(--border-color)];
}

.detection-item {
  @apply flex items-center gap-3 px-4 py-2 text-sm border-b border-[var(--border-color)] last:border-b-0;
}

.det-class {
  @apply px-2 py-0.5 rounded text-white text-xs;
}

.det-conf {
  @apply text-[var(--accent-cyan)] font-mono text-xs;
}

.det-bbox {
  @apply text-[var(--text-muted)] font-mono text-[10px];
}
</style>