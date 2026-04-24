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
            <span class="dot"></span>
            {{ runningCount }} 运行中
          </div>
          <div class="stat-pill completed">
            <span class="dot"></span>
            {{ completedCount }} 已完成
          </div>
        </div>
        <el-button type="text" @click="handleClearCompleted" :disabled="completedCount === 0">
          清理记录
        </el-button>
      </div>
    </div>

    <div class="training-grid">
      <!-- 左侧：训练列表 -->
      <div class="training-list-section vg-card">
        <div class="section-header">
          <h3>训练任务</h3>
          <button class="refresh-btn" @click="loadJobs">
            <RefreshIcon />
          </button>
        </div>

        <div class="jobs-list" v-loading="loading">
          <div class="job-item" v-for="job in jobs" :key="job.id"
               :class="{ active: job.status === 'running' }">
            <div class="job-header">
              <span class="job-id">TASK #{{ job.id.toString().padStart(4, '0') }}</span>
              <span class="job-status" :class="job.status">{{ statusText[job.status] }}</span>
            </div>
            <div class="job-progress">
              <div class="progress-bar">
                <div class="progress-fill" :class="job.status"
                     :style="{ width: getProgress(job) + '%' }"></div>
              </div>
              <span class="progress-text">{{ job.current_step }} / {{ job.total_steps || '?' }}</span>
            </div>
            <div class="job-meta">
              <span class="meta-tag">Model #{{ job.model_id }}</span>
              <span class="meta-tag">Atlas #{{ job.atlas_id }}</span>
            </div>
            <div class="job-actions" v-if="job.status === 'running'">
              <el-button type="text" @click="handleStop(job)">停止</el-button>
            </div>
          </div>

          <div class="empty-jobs" v-if="!loading && jobs.length === 0">
            <div class="empty-icon">
              <ChartIcon />
            </div>
            <p>暂无训练任务</p>
            <span>开始一个新训练来监控进度</span>
          </div>
        </div>
      </div>

      <!-- 右侧：启动训练 -->
      <div class="control-section">
        <div class="vg-card start-training-card">
          <div class="section-header">
            <h3>启动训练</h3>
          </div>
          <div class="start-form">
            <div class="form-group">
              <label>选择模型</label>
              <div class="select-wrapper">
                <select v-model="startForm.model_id">
                  <option :value="null" disabled>选择模型</option>
                  <option v-for="m in models" :key="m.id" :value="m.id">
                    {{ m.name }}{{ m.version ? ` (${m.version})` : '' }}
                  </option>
                </select>
              </div>
            </div>

            <div class="form-group">
              <label>选择图集</label>
              <div class="select-wrapper">
                <select v-model="startForm.atlas_id">
                  <option :value="null" disabled>选择图集</option>
                  <option v-for="a in atlases" :key="a.id" :value="a.id">
                    {{ a.name }}
                  </option>
                </select>
              </div>
            </div>

            <div class="form-group">
              <label>训练轮数</label>
              <div class="number-input">
                <button @click="startForm.total_steps = Math.max(10, startForm.total_steps - 10)">-</button>
                <input type="number" v-model="startForm.total_steps" min="10" max="1000" />
                <button @click="startForm.total_steps = Math.min(1000, startForm.total_steps + 10)">+</button>
              </div>
            </div>

            <div class="form-group">
              <label>训练设备</label>
              <div class="select-wrapper">
                <select v-model="startForm.device">
                  <option value="cpu">CPU</option>
                  <option value="cuda" v-if="deviceInfo.available">GPU ({{ deviceInfo.device_name }})</option>
                </select>
              </div>
              <span class="device-hint" v-if="deviceInfo.available">
                检测到 {{ deviceInfo.device_name }}，推荐使用 GPU 加速训练
              </span>
              <span class="device-hint" v-else>
                未检测到 GPU，将使用 CPU 训练
              </span>
            </div>

            <div class="form-group">
              <label>预训练模型</label>
              <div class="select-wrapper">
                <select v-model="startForm.pretrained_model">
                  <option value="yolov8n.pt">YOLOv8n (最小最快)</option>
                  <option value="yolov8s.pt">YOLOv8s (小，推荐)</option>
                  <option value="yolov8m.pt">YOLOv8m (中)</option>
                  <option value="yolov8l.pt">YOLOv8l (大)</option>
                  <option value="yolov8x.pt">YOLOv8x (最大最准)</option>
                </select>
              </div>
            </div>

            <button class="vg-btn vg-btn-primary start-btn" @click="handleStart" :disabled="starting">
              <PlayIcon />
              {{ starting ? '启动中...' : '启动训练' }}
            </button>
          </div>
        </div>

        <!-- 实时状态 -->
        <div class="vg-card realtime-card" v-if="currentJob">
          <div class="section-header">
            <h3>实时状态</h3>
            <span class="live-badge">
              <span class="live-dot"></span>
              LIVE
            </span>
          </div>
          <div class="realtime-content">
            <div class="realtime-stat">
              <span class="stat-label">当前任务</span>
              <span class="stat-value">#{{ currentJob.id }}</span>
            </div>
            <div class="realtime-stat">
              <span class="stat-label">状态</span>
              <span class="stat-value status-running" v-if="currentJob.status === 'running'">进行中</span>
              <span class="stat-value" v-else>{{ statusText[currentJob.status] }}</span>
            </div>
            <div class="realtime-progress">
              <div class="progress-bar large">
                <div class="progress-fill" :class="currentJob.status"
                     :style="{ width: getProgress(currentJob) + '%' }"></div>
              </div>
              <span class="progress-percent">
                <span v-if="currentJob.status === 'downloading'">下载中</span>
                <span v-else>{{ getProgress(currentJob) }}%</span>
              </span>
            </div>
            <div class="realtime-message" v-if="currentJob.message">
              <span class="message-text">{{ currentJob.message }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, h } from 'vue'
import { ElMessage } from 'element-plus'
import { trainingApi, modelApi, atlasApi } from '@/api'

const jobs = ref<any[]>([])
const models = ref<any[]>([])
const atlases = ref<any[]>([])
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
  running: '进行中',
  completed: '已完成',
  failed: '失败',
}

const handleClearCompleted = async () => {
  try {
    await trainingApi.clearCompleted()
    ElMessage.success('已清理完成和失败的记录')
    loadJobs()
  } catch (error: any) {
    const msg = error.response?.data?.detail || '清理失败'
    ElMessage.error(msg)
  }
}

// 图标
const RefreshIcon = () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
  h('polyline', { points: '23 4 23 10 17 10' }),
  h('polyline', { points: '1 20 1 14 7 14' }),
  h('path', { d: 'M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15' })
])

const ChartIcon = () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '1.5' }, [
  h('line', { x1: '18', y1: '20', x2: '18', y2: '10' }),
  h('line', { x1: '12', y1: '20', x2: '12', y2: '4' }),
  h('line', { x1: '6', y1: '20', x2: '6', y2: '14' })
])

const StopIcon = () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
  h('rect', { x: '3', y: '3', width: '18', height: '18', rx: '2', ry: '2' })
])

const PlayIcon = () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
  h('polygon', { points: '5 3 19 12 5 21 5 3' })
])

const ChevronIcon = () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
  h('polyline', { points: '6 9 12 15 18 9' })
])

const getProgress = (job: any) => {
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
  } catch (error: any) {
    const msg = error.response?.data?.detail || '启动失败'
    ElMessage.error(msg)
  } finally {
    starting.value = false
  }
}

const handleStop = async (job: any) => {
  try {
    await trainingApi.stop(job.id)
    ElMessage.success('训练已停止')
    loadJobs()
  } catch (error: any) {
    const msg = error.response?.data?.detail || '停止失败'
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
  @apply flex flex-col gap-6;
}

.page-header {
  @apply flex justify-between items-center;
  gap: 20px;
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
  @apply flex items-center gap-4;
}

.header-stats {
  @apply flex gap-3;
}

.stat-pill {
  @apply flex items-center gap-2 px-4 py-2 bg-[var(--bg-card)] border border-[var(--border-color)] rounded-full text-sm font-medium;

  .dot {
    @apply w-2 h-2 rounded-full;
  }

  &.running .dot {
    @apply bg-[var(--accent-cyan)];
    box-shadow: 0 0 10px var(--accent-cyan);
    animation: pulse 2s infinite;
  }

  &.completed .dot {
    @apply bg-[var(--accent-green)];
    box-shadow: 0 0 10px var(--accent-green);
  }
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

/* 网格布局 */
.training-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: clamp(16px, 2vw, 32px);
}

.training-list-section {
  min-width: 0;  // 允许收缩
}

/* 训练列表 */
.section-header {
  @apply flex justify-between items-center px-6 py-5 border-b border-[var(--border-color)];

  h3 {
    @apply text-base font-semibold;
  }
}

.refresh-btn {
  @apply w-9 h-9 flex items-center justify-center bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-lg text-[var(--text-secondary)] cursor-pointer transition-all;

  &:hover {
    @apply border-[var(--accent-cyan)] text-[var(--accent-cyan)];
  }

  svg {
    @apply w-4.5 h-4.5;
  }
}

.jobs-list {
  @apply p-4 flex flex-col gap-3 min-h-[400px];
}

.job-item {
  @apply bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-xl p-4 transition-all;

  &:hover {
    @apply border-[var(--accent-cyan)];
  }

  &.active {
    @apply border-[var(--accent-cyan)];
    box-shadow: 0 0 20px rgba(0, 240, 255, 0.2);
  }
}

.job-header {
  @apply flex justify-between items-center mb-3;
}

.job-id {
  @apply font-mono text-sm font-semibold text-[var(--accent-cyan)];
}

.job-status {
  @apply text-xs px-2 py-1 rounded;

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
  @apply flex items-center gap-3 mb-3;
}

.progress-bar {
  @apply flex-1 h-1.5 bg-[var(--bg-primary)] rounded overflow-hidden;

  &.large {
    @apply h-2.5 rounded-lg;
  }
}

.progress-fill {
  @apply h-full rounded transition-all duration-500;

  &.pending { @apply bg-[var(--text-muted)]; }
  &.downloading {
    background: linear-gradient(90deg, var(--accent-cyan), var(--accent-magenta));
    box-shadow: 0 0 10px var(--accent-cyan);
    animation: downloadPulse 1.5s ease-in-out infinite;
  }
  &.running {
    background: linear-gradient(90deg, var(--accent-cyan), var(--accent-magenta));
    box-shadow: 0 0 10px var(--accent-cyan);
  }
  &.completed { @apply bg-[var(--accent-green)]; }
  &.failed { @apply bg-[#ff4466]; }
}

@keyframes downloadPulse {
  0%, 100% { opacity: 0.6; }
  50% { opacity: 1; }
}

.progress-text {
  @apply font-mono text-xs text-[var(--text-muted)] min-w-20 text-right;
}

.job-meta {
  @apply flex gap-2;
}

.meta-tag {
  @apply text-xs px-2 py-1 bg-[var(--bg-primary)] rounded text-[var(--text-muted)];
}

.job-actions {
  @apply mt-3 pt-3 border-t border-[var(--border-color)];
}

:deep(.el-button--text) {
  @apply p-1 border-none bg-transparent text-[#ff4466] text-sm;
  &:hover {
    @apply bg-transparent border-none text-[#ff4466];
  }
}

.empty-jobs {
  @apply flex-1 flex flex-col items-center justify-center text-center text-[var(--text-muted)];
}

.empty-icon {
  @apply w-16 h-16 mb-4 opacity-30;

  svg {
    @apply w-full h-full;
  }
}

.empty-jobs p {
  @apply text-base text-[var(--text-secondary)] mb-2;
}

.empty-jobs span {
  @apply text-sm;
}

/* 控制区 */
.control-section {
  @apply flex flex-col gap-6;
}

.start-training-card,
.realtime-card {
  animation: fadeInUp 0.6s ease forwards;
}

.start-form {
  @apply p-6 flex flex-col gap-5;
}

.form-group {
  @apply flex flex-col gap-2;

  label {
    @apply text-xs text-[var(--text-secondary)] uppercase tracking-wide;
  }
}

.select-wrapper {
  @apply relative;

  select {
    @apply w-full px-4 py-3 bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-lg text-[var(--text-primary)] text-sm cursor-pointer appearance-none transition-all;

    &:focus {
      @apply outline-none border-[var(--accent-cyan)];
    }

    option {
      @apply bg-[var(--bg-card)];
    }
  }

  &::after {
    content: '';
    @apply absolute right-4 top-1/2 -translate-y-1/2 border-l-1.5 border-r-1.5 border-t-1.5 border-l-transparent border-r-transparent border-t-[var(--text-muted)];
    pointer-events: none;
  }
}

.number-input {
  @apply flex items-center bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-lg overflow-hidden;

  button {
    @apply w-11 h-11 bg-transparent border-none text-[var(--text-secondary)] text-lg cursor-pointer transition-all;
    &:hover {
      @apply bg-[var(--bg-hover)] text-[var(--accent-cyan)];
    }
  }

  input {
    @apply flex-1 px-3 py-3 bg-transparent border-none text-[var(--text-primary)] text-sm font-mono text-center;
    &:focus {
      @apply outline-none;
    }
  }
}

.start-btn {
  @apply w-full justify-center py-3.5 text-base mt-2;
  svg {
    @apply w-4.5 h-4.5;
  }
}

.device-hint {
  @apply text-xs text-[var(--text-muted)] mt-1;
}

/* 实时状态 */
.live-badge {
  @apply flex items-center gap-1.5 font-mono text-xs text-[#ff4466] tracking-wider;
}

.live-dot {
  @apply w-1.5 h-1.5 rounded-full bg-[#ff4466];
  animation: livePulse 1s infinite;
}

@keyframes livePulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(0.8); }
}

.realtime-content {
  @apply p-6 flex flex-col gap-4;
}

.realtime-stat {
  @apply flex justify-between items-center;

  .stat-label {
    @apply text-sm text-[var(--text-secondary)];
  }

  .stat-value {
    @apply font-mono text-sm font-semibold;
  }

  .stat-value.status-running {
    @apply text-[var(--accent-cyan)];
    text-shadow: 0 0 10px var(--accent-cyan);
  }
}

.realtime-progress {
  @apply flex items-center gap-4 mt-2;
}

.progress-percent {
  @apply font-mono text-2xl font-bold text-[var(--accent-cyan)] min-w-15 text-right;
}

.realtime-message {
  @apply mt-3 pt-3 border-t border-[var(--border-color)];
}

.message-text {
  @apply text-sm text-[var(--text-secondary)];
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
