<template>
  <div class="training">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-info">
        <h2>模型训练</h2>
        <span class="subtitle">实时监控训练进度</span>
      </div>
      <div class="header-actions">
        <div class="header-stats">
          <div class="stat-pill running">
            <span class="dot" />
            {{ runningCount }} 运行
          </div>
          <div class="stat-pill completed">
            <span class="dot" />
            {{ completedCount }} 完成
          </div>
        </div>
        <button
          class="ui-btn ui-btn-sm"
          :disabled="completedCount === 0"
          @click="handleClearCompleted"
        >
          清理
        </button>
      </div>
    </div>

    <div class="training-layout">
      <!-- 左侧：参数配置 -->
      <div class="config-panel ui-card">
        <div class="section-header">
          <div class="header-left">
            <SvgIcon
              name="box"
              class="panel-icon"
            />
            <h3>参数配置</h3>
          </div>
        </div>
        <div class="config-form">
          <div class="form-group">
            <label>选择模型</label>
            <div class="select-wrapper">
              <select v-model="startForm.model_id">
                <option
                  :value="null"
                  disabled
                >
                  选择模型
                </option>
                <option
                  v-for="m in models"
                  :key="m.id"
                  :value="m.id"
                >
                  {{ m.name }}{{ m.version ? ` (${m.version})` : '' }}
                </option>
              </select>
            </div>
          </div>

          <div class="form-group">
            <label>选择图集</label>
            <div class="select-wrapper">
              <select v-model="startForm.atlas_id">
                <option
                  :value="null"
                  disabled
                >
                  选择图集
                </option>
                <option
                  v-for="a in atlases"
                  :key="a.id"
                  :value="a.id"
                >
                  {{ a.name }}
                </option>
              </select>
            </div>
          </div>

          <div class="form-group">
            <label>训练轮数</label>
            <div class="number-input">
              <button @click="startForm.total_steps = Math.max(10, startForm.total_steps - 10)">
                -
              </button>
              <input
                v-model="startForm.total_steps"
                type="number"
                min="10"
                max="1000"
              >
              <button @click="startForm.total_steps = Math.min(1000, startForm.total_steps + 10)">
                +
              </button>
            </div>
          </div>

          <div class="form-group">
            <label>训练设备</label>
            <div class="select-wrapper">
              <select v-model="startForm.device">
                <option value="cpu">
                  CPU
                </option>
                <option
                  v-if="deviceInfo.available"
                  value="cuda"
                >
                  GPU ({{ deviceInfo.device_name }})
                </option>
              </select>
            </div>
            <span
              v-if="deviceInfo.available"
              class="device-hint"
            >
              推荐使用 GPU
            </span>
            <span
              v-else
              class="device-hint"
            >
              将使用 CPU 训练
            </span>
          </div>

          <div class="form-group">
            <label>预训练模型</label>
            <div class="select-wrapper">
              <select v-model="startForm.pretrained_model">
                <option value="yolov8n.pt">
                  YOLOv8n (最小)
                </option>
                <option value="yolov8s.pt">
                  YOLOv8s (推荐)
                </option>
                <option value="yolov8m.pt">
                  YOLOv8m (中)
                </option>
                <option value="yolov8l.pt">
                  YOLOv8l (大)
                </option>
                <option value="yolov8x.pt">
                  YOLOv8x (最大)
                </option>
              </select>
            </div>
          </div>

          <button
            class="ui-btn ui-btn-primary start-btn"
            :disabled="starting"
            @click="handleStart"
          >
            <SvgIcon name="play" />
            {{ starting ? '启动中...' : '启动训练' }}
          </button>
        </div>
      </div>

      <!-- 右侧：训练列表和实时状态 -->
      <div class="main-panel">
        <!-- 训练任务列表 -->
        <div class="training-list-section ui-card">
          <div class="section-header">
            <div class="header-left">
              <SvgIcon
                name="chart"
                class="panel-icon"
              />
              <h3>训练任务</h3>
            </div>
            <button
              class="refresh-btn"
              @click="loadJobs"
            >
              <SvgIcon name="refresh" />
            </button>
          </div>

          <div
            v-loading="loading"
            class="jobs-list"
          >
            <div
              v-for="job in jobs"
              :key="job.id"
              class="job-item"
              :class="{ active: job.status === 'running' }"
            >
              <div class="job-header">
                <span class="job-id">#{{ job.id.toString().padStart(4, '0') }}</span>
                <span
                  class="job-status"
                  :class="job.status"
                >{{ statusText[job.status] }}</span>
              </div>
              <div class="job-progress">
                <div class="progress-bar">
                  <div
                    class="progress-fill"
                    :class="job.status"
                    :style="{ width: getProgress(job) + '%' }"
                  />
                </div>
                <span class="progress-text">{{ job.current_step }} / {{ job.total_steps || '?' }}</span>
              </div>
              <div class="job-meta">
                <span class="meta-tag">M#{{ job.model_id }}</span>
                <span class="meta-tag">A#{{ job.atlas_id }}</span>
              </div>
              <div
                v-if="job.status === 'running'"
                class="job-actions"
              >
                <el-button
                  type="text"
                  size="small"
                  @click="handleStop(job)"
                >
                  停止
                </el-button>
              </div>
            </div>

            <div
              v-if="!loading && jobs.length === 0"
              class="empty-jobs"
            >
              <div class="empty-icon">
                <SvgIcon name="chart" />
              </div>
              <p>暂无训练任务</p>
            </div>
          </div>
        </div>

        <!-- 实时状态 -->
        <div
          v-if="currentJob"
          class="realtime-card ui-card"
        >
          <div class="section-header">
            <h3>实时状态</h3>
            <span class="live-badge">
              <span class="live-dot" />
              LIVE
            </span>
          </div>
          <div class="realtime-content">
            <div class="realtime-stat">
              <span class="stat-label">任务</span>
              <span class="stat-value">#{{ currentJob.id }}</span>
            </div>
            <div class="realtime-stat">
              <span class="stat-label whitespace-nowrap">状态</span>
              <span
                class="stat-value"
                :class="'status-' + currentJob._displayStatus"
              >
                {{ currentJob._displayStatus === 'downloading' ? '下载中' : currentJob._displayStatus === 'running' ? '进行中' : statusText[currentJob.status] }}
              </span>
            </div>
            <div class="realtime-progress">
              <div class="progress-bar large">
                <div
                  class="progress-fill"
                  :class="currentJob.status"
                  :style="{ width: getProgress(currentJob) + '%' }"
                />
              </div>
              <span class="progress-percent">
                <span v-if="currentJob._displayStatus === 'downloading'">{{ getProgress(currentJob) }}%</span>
                <span v-else>{{ getProgress(currentJob) }}%</span>
              </span>
            </div>
            <div
              v-if="currentJob.message"
              class="realtime-message"
            >
              <span class="message-text">{{ currentJob.message }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { trainingApi, modelApi, atlasApi } from '@/api'
import SvgIcon from '@/components/SvgIcon.vue'
import type { TrainingJobResponse, ModelResponse, AtlasResponse } from '@/types/api'

const jobs = ref<TrainingJobResponse[]>([])
const models = ref<ModelResponse[]>([])
const atlases = ref<AtlasResponse[]>([])
const loading = ref(false)
const starting = ref(false)
const deviceInfo = ref<{ available: boolean; device: string; device_name: string }>({
  available: false,
  device: 'cpu',
  device_name: 'CPU',
})
const currentJob = computed(() => jobs.value.find(j => j.status === 'running') || null)
const runningCount = computed(() => jobs.value.filter(j => j.status === 'running').length)
const completedCount = computed(() => jobs.value.filter(j => j.status === 'completed' || j.status === 'failed').length)

const startForm = ref({
  model_id: null as number | null,
  atlas_id: null as number | null,
  total_steps: 100,
  device: 'cpu',
  pretrained_model: 'yolov8s.pt',
})

let ws: WebSocket | null = null

const statusText: Record<string, string> = {
  pending: '等待中',
  downloading: '下载中',
  running: '进行中',
  completed: '已完成',
  failed: '失败',
}

const handleClearCompleted = async () => {
  try {
    await trainingApi.clearCompleted()
    ElMessage.success('已清理完成和失败的记录')
    loadJobs()
  } catch (error: unknown) {
    const msg = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '清理失败'
    ElMessage.error(msg)
  }
}

// 图标
const getProgress = (job: TrainingJobResponse) => {
  if (!job || !job.total_steps) return 0
  return Math.round((job.current_step / job.total_steps) * 100)
}

const loadJobs = async () => {
  try {
    const res = await trainingApi.listJobs()
    jobs.value = res.data
  } catch (error) {
    console.error('加载训练任务失败', error)
  }
}

const loadModels = async () => {
  try {
    const res = await modelApi.list()
    models.value = res.data
  } catch (error) {
    console.error('加载模型失败', error)
  }
}

const loadAtlases = async () => {
  try {
    const res = await atlasApi.list()
    atlases.value = res.data
  } catch (error) {
    console.error('加载图集失败', error)
  }
}

const loadDeviceInfo = async () => {
  try {
    const res = await trainingApi.getDeviceInfo()
    deviceInfo.value = res.data
    startForm.value.device = res.data.available ? 'cuda' : 'cpu'
  } catch (error) {
    console.error('获取设备信息失败', error)
  }
}

const handleStart = async () => {
  if (!startForm.value.model_id || !startForm.value.atlas_id) {
    ElMessage.warning('请选择模型和图集')
    return
  }
  starting.value = true
  try {
    await trainingApi.start({
      model_id: startForm.value.model_id,
      atlas_id: startForm.value.atlas_id,
      config: {
        epochs: startForm.value.total_steps,
        device: startForm.value.device,
        pretrained_model: startForm.value.pretrained_model,
      },
    })
    ElMessage.success('训练已启动')
    loadJobs()
    startProgressPolling()
  } catch (error: unknown) {
    const msg = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '启动失败'
    ElMessage.error(msg)
  } finally {
    starting.value = false
  }
}

const handleStop = async (job: TrainingJobResponse) => {
  try {
    await trainingApi.stop(job.id)
    ElMessage.success('训练已停止')
    loadJobs()
  } catch (error: unknown) {
    const msg = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '停止失败'
    ElMessage.error(msg)
  }
}

const connectWebSocket = () => {
  ws = new WebSocket(`/ws/training`)
  ws.onmessage = (event) => {
    const data = JSON.parse(event.data)
    if (data.type === 'training_update') {
      loadJobs()
    }
  }
  ws.onclose = () => {
    setTimeout(connectWebSocket, 3000)
  }
}

// 轮询进度
let progressPollingTimer: number | null = null

const startProgressPolling = () => {
  if (progressPollingTimer) return
  const poll = async () => {
    try {
      const res = await trainingApi.getProgress()
      const progress = res.data
      if (progress.status === 'running' || progress.status === 'downloading') {
        // 更新 running 任务的进度
        const runningJob = jobs.value.find(j => j.status === 'running')
        if (runningJob) {
          runningJob.current_step = progress.epoch
          runningJob.total_steps = progress.total_epochs
          runningJob.message = progress.message
          runningJob._displayStatus = progress.status  // 用于实时卡片显示下载中/训练中
        }
        progressPollingTimer = window.setTimeout(poll, 2000)
      } else if (progress.status === 'completed' || progress.status === 'failed') {
        loadJobs() // 重新加载以获取最终状态
        stopProgressPolling()
        if (progress.status === 'failed' && progress.message) {
          ElMessage.error(progress.message)
        }
      }
    } catch (e) {
      console.error('轮询进度失败', e)
    }
  }
  poll()
}

const stopProgressPolling = () => {
  if (progressPollingTimer) {
    clearTimeout(progressPollingTimer)
    progressPollingTimer = null
  }
}

onMounted(() => {
  Promise.all([loadJobs(), loadModels(), loadAtlases(), loadDeviceInfo()])
  connectWebSocket()
  // 启动轮询
  startProgressPolling()
})

onUnmounted(() => {
  if (ws) ws.close()
  stopProgressPolling()
})
</script>

<style lang="scss" scoped>
.training {
  @apply flex flex-col gap-4;
  height: 100%;
  box-sizing: border-box;
  min-height: 0;
  overflow: hidden;
}

.page-header {
  @apply flex justify-between items-center gap-4 flex-shrink-0;
}

.header-info {
  @apply flex items-baseline;
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

.header-actions {
  @apply flex items-center gap-3 h-9;
}

.header-stats {
  @apply flex gap-2;
}

.stat-pill {
  @apply flex items-center gap-1.5 px-2.5 py-1 bg-[var(--bg-card)] border border-[var(--border-color)] rounded-full text-xs font-medium;

  .dot {
    @apply w-1.5 h-1.5 rounded-full;
  }

  &.running .dot {
    @apply bg-[var(--accent-cyan)];
    box-shadow: 0 0 8px var(--accent-cyan);
    animation: pulse 2s infinite;
  }

  &.completed .dot {
    @apply bg-[var(--accent-green)];
    box-shadow: 0 0 8px var(--accent-green);
  }
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

/* 布局 - 左侧参数配置，右侧上下布局 */
.training-layout {
  @apply flex gap-4 flex-1 min-h-0 overflow-hidden;
}

/* 左侧配置面板 */
.config-panel {
  @apply flex flex-col flex-shrink-0 overflow-hidden;
  width: 360px;
}

.config-form {
  @apply p-4 flex flex-col gap-4 overflow-y-auto flex-1;
}

.start-btn {
  @apply w-full justify-center py-2.5 mt-2;
  svg {
    @apply w-3.5 h-3.5;
  }
}

/* 右侧主面板 - 上下布局 */
.main-panel {
  @apply flex flex-col gap-4 flex-1 min-w-0 overflow-hidden;
}

/* 训练列表 */
.training-list-section {
  @apply flex flex-col flex-1 min-h-0 overflow-hidden;
}

.section-header {
  @apply flex justify-between items-center px-4 py-3 border-b border-[var(--border-color)] flex-shrink-0;

  .header-left {
    @apply flex items-center gap-2;
  }

  h3 {
    @apply text-sm font-semibold;
  }
}

.refresh-btn {
  @apply w-7 h-7 flex items-center justify-center bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded text-[var(--text-secondary)] cursor-pointer transition-all;

  &:hover {
    @apply border-[var(--accent-cyan)] text-[var(--accent-cyan)];
  }

  svg {
    @apply w-3.5 h-3.5;
  }
}

.jobs-list {
  @apply p-3 flex flex-col gap-2 overflow-y-auto flex-1;
}

.job-item {
  @apply bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-lg p-3 transition-all;

  &:hover {
    @apply border-[var(--accent-cyan)];
  }

  &.active {
    @apply border-[var(--accent-cyan)];
    box-shadow: 0 0 15px rgba(0, 240, 255, 0.15);
  }
}

.job-header {
  @apply flex justify-between items-center mb-2;
}

.job-id {
  @apply font-mono text-xs font-semibold text-[var(--accent-cyan)];
}

.job-status {
  @apply text-[10px] px-1.5 py-0.5 rounded;

  &.pending {
    @apply bg-[rgba(136,136,170,0.2)] text-[var(--text-secondary)];
  }

  &.running {
    @apply bg-[rgba(0,240,255,0.2)] text-[var(--accent-cyan)];
  }

  &.completed {
    @apply bg-[rgba(0,255,136,0.2)] text-[var(--accent-green)];
  }

  &.failed {
    @apply bg-[rgba(255,68,102,0.2)] text-[#ff4466];
  }
}

.job-progress {
  @apply flex items-center gap-2 mb-2;
}

.progress-bar {
  @apply flex-1 h-1 bg-[var(--bg-primary)] rounded overflow-hidden;

  &.large {
    @apply h-2 rounded-lg;
  }
}

.progress-fill {
  @apply h-full rounded transition-all duration-500;

  &.pending { @apply bg-[var(--text-muted)]; }
  &.downloading {
    background: linear-gradient(90deg, var(--accent-cyan), var(--accent-magenta));
    box-shadow: 0 0 8px var(--accent-cyan);
    animation: downloadPulse 1.5s ease-in-out infinite;
  }
  &.running {
    background: linear-gradient(90deg, var(--accent-cyan), var(--accent-magenta));
    box-shadow: 0 0 8px var(--accent-cyan);
  }
  &.completed { @apply bg-[var(--accent-green)]; }
  &.failed { @apply bg-[#ff4466]; }
}

@keyframes downloadPulse {
  0%, 100% { opacity: 0.6; }
  50% { opacity: 1; }
}

.progress-text {
  @apply font-mono text-[10px] text-[var(--text-muted)] min-w-16 text-right;
}

.job-meta {
  @apply flex gap-1.5;
}

.meta-tag {
  @apply text-[10px] px-1.5 py-0.5 bg-[var(--bg-primary)] rounded text-[var(--text-muted)];
}

.job-actions {
  @apply mt-2 pt-2 border-t border-[var(--border-color)];
}

.empty-jobs {
  @apply flex-1 flex flex-col items-center justify-center text-center text-[var(--text-muted)];
}

.empty-icon {
  @apply w-12 h-12 mb-3 opacity-30;

  svg {
    @apply w-full h-full;
  }
}

.empty-jobs p {
  @apply text-sm text-[var(--text-secondary)] mb-1;
}

.empty-jobs span {
  @apply text-xs;
}

/* 实时状态卡片 */
.realtime-card {
  @apply flex flex-col flex-shrink-0 max-h-[40%] overflow-hidden;
}

.live-badge {
  @apply flex items-center gap-1 font-mono text-[10px] text-[#ff4466] tracking-wider;
}

.live-dot {
  @apply w-1 h-1 rounded-full bg-[#ff4466];
  animation: livePulse 1s infinite;
}

@keyframes livePulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(0.8); }
}

.realtime-content {
  @apply p-4 flex flex-col gap-3 overflow-y-auto;
}

.realtime-stat {
  @apply flex justify-between items-center;

  .stat-label {
    @apply text-xs text-[var(--text-secondary)];
  }

  .stat-value {
    @apply font-mono text-xs font-semibold;
  }

  .stat-value.status-running {
    @apply text-[var(--accent-cyan)];
    text-shadow: 0 0 8px var(--accent-cyan);
  }

  .stat-value.status-downloading {
    @apply text-[var(--accent-orange)];
    text-shadow: 0 0 8px var(--accent-orange);
  }
}

.realtime-progress {
  @apply flex items-center gap-3;
}

.progress-percent {
  @apply font-mono text-lg font-bold text-[var(--accent-cyan)] min-w-12 text-right;
}

.realtime-message {
  @apply mt-2 pt-2 border-t border-[var(--border-color)];
}

.message-text {
  @apply text-xs text-[var(--text-secondary)];
}

/* 表单元素 */
.form-group {
  @apply flex flex-col gap-1.5;

  label {
    @apply text-[11px] text-[var(--text-secondary)] uppercase tracking-wide;
  }
}

.select-wrapper {
  @apply relative;

  select {
    @apply w-full px-3 py-2 bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded text-xs text-[var(--text-primary)] cursor-pointer appearance-none transition-all;

    &:focus {
      @apply outline-none border-[var(--accent-cyan)];
    }

    option {
      @apply bg-[var(--bg-card)];
    }
  }

  &::after {
    content: '';
    @apply absolute right-3 top-1/2 -translate-y-1/2 border-l-1 border-r-1 border-t-1 border-l-transparent border-r-transparent border-t-[var(--text-muted)];
    pointer-events: none;
  }
}

.number-input {
  @apply flex items-center bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded overflow-hidden;

  button {
    @apply w-8 h-8 bg-transparent border-none text-[var(--text-secondary)] text-base cursor-pointer transition-all;
    &:hover {
      @apply bg-[var(--bg-hover)] text-[var(--accent-cyan)];
    }
  }

  input {
    @apply flex-1 px-2 py-2 bg-transparent border-none text-[var(--text-primary)] text-xs font-mono text-center;
    &:focus {
      @apply outline-none;
    }
  }
}

.panel-icon {
  @apply w-4 h-4 text-[var(--accent-cyan)];
}
</style>
