<template>
  <div class="home">
    <!-- 统计卡片 -->
    <div class="stats-grid">
      <div
        v-for="(stat, index) in stats"
        :key="stat.label"
        class="stat-card"
        :style="{ animationDelay: `${index * 0.1}s` }"
      >
        <div class="stat-glow" :style="{ background: stat.gradient }"></div>
        <div class="stat-icon" :style="{ color: stat.color }">
          <component :is="stat.icon" />
        </div>
        <div class="stat-content">
          <div class="stat-value" :style="{ color: stat.color }">{{ stat.value }}</div>
          <div class="stat-label">{{ stat.label }}</div>
        </div>
        <div class="stat-decoration">
          <div class="decoration-line"></div>
        </div>
      </div>
    </div>

    <!-- 主功能区 -->
    <div class="main-grid">
      <!-- 快速操作 -->
      <div class="quick-actions ui-card">
        <div class="card-header">
          <span class="header-line"></span>
          <h3>快速操作</h3>
          <span class="header-badge">QUICK ACTIONS</span>
        </div>
        <div class="action-grid">
          <button
            class="action-tile"
            v-for="action in quickActions"
            :key="action.label"
            @click="$router.push(action.path)"
            :style="{ '--accent': action.color }"
          >
            <div class="action-icon">
              <component :is="action.icon" />
            </div>
            <span class="action-label">{{ action.label }}</span>
            <div class="action-hover-effect"></div>
          </button>
        </div>
      </div>

      <!-- 系统状态 -->
      <div class="system-status ui-card">
        <div class="card-header">
          <span class="header-line"></span>
          <h3>系统状态</h3>
          <span class="header-badge">SYSTEM STATUS</span>
        </div>
        <div class="status-content">
          <!-- CPU -->
          <div class="status-item">
            <div class="status-header">
              <span class="status-label">CPU 使用率</span>
              <span class="status-value">{{ systemStats.cpu.percent.toFixed(1) }}%</span>
            </div>
            <div class="status-bar">
              <div class="status-fill" :style="{ width: systemStats.cpu.percent + '%', background: systemStats.cpu.percent > 80 ? '#ff4466' : '#00f0ff' }"></div>
            </div>
          </div>
          <!-- 内存 -->
          <div class="status-item">
            <div class="status-header">
              <span class="status-label">内存</span>
              <span class="status-value">{{ formatBytes(systemStats.memory.used) }} / {{ formatBytes(systemStats.memory.total) }}</span>
            </div>
            <div class="status-bar">
              <div class="status-fill" :style="{ width: systemStats.memory.percent + '%', background: systemStats.memory.percent > 80 ? '#ff4466' : '#ff00aa' }"></div>
            </div>
          </div>
          <!-- 磁盘 -->
          <div class="status-item">
            <div class="status-header">
              <span class="status-label">存储空间</span>
              <span class="status-value">{{ formatBytes(systemStats.disk.used) }} / {{ formatBytes(systemStats.disk.total) }}</span>
            </div>
            <div class="status-bar">
              <div class="status-fill" :style="{ width: systemStats.disk.percent + '%', background: systemStats.disk.percent > 90 ? '#ff4466' : '#ffdd00' }"></div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 训练进度 -->
    <div class="training-section ui-card">
      <div class="card-header">
        <span class="header-line"></span>
        <h3>训练进度</h3>
        <span class="header-badge">TRAINING PROGRESS</span>
      </div>
      <div class="training-content">
        <div class="training-list" v-if="recentJobs.length > 0">
          <div class="training-item" v-for="job in recentJobs" :key="job.id">
            <div class="training-info">
              <span class="training-id">TASK #{{ job.id.toString().padStart(4, '0') }}</span>
              <span class="training-status" :class="job.status">
                {{ statusText[job.status] }}
              </span>
            </div>
            <div class="training-progress">
              <div class="progress-bar">
                <div class="progress-fill" :class="job.status"
                     :style="{ width: getProgress(job) + '%' }"></div>
              </div>
              <span class="progress-text">{{ job.current_step }} / {{ job.total_steps }}</span>
            </div>
            <div class="training-meta">
              <span class="meta-item">Model #{{ job.model_id }}</span>
              <span class="meta-item">Atlas #{{ job.atlas_id }}</span>
            </div>
          </div>
        </div>
        <div class="empty-state" v-else>
          <div class="empty-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <circle cx="12" cy="12" r="10"/>
              <path d="M12 6v6l4 2"/>
            </svg>
          </div>
          <p>暂无训练任务</p>
          <span>开始一个新训练来监控进度</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, h } from 'vue'
import { atlasApi, imageApi, modelApi, trainingApi } from '@/api'

// 图标定义必须在使用之前
const FolderIcon = () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
  h('path', { d: 'M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z' })
])

const ImageIcon = () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
  h('rect', { x: '3', y: '3', width: '18', height: '18', rx: '2', ry: '2' }),
  h('circle', { cx: '8.5', cy: '8.5', r: '1.5' }),
  h('polyline', { points: '21 15 16 10 5 21' })
])

const BoxIcon = () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
  h('path', { d: 'M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 003 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0021 16z' })
])

const ChartIcon = () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
  h('line', { x1: '18', y1: '20', x2: '18', y2: '10' }),
  h('line', { x1: '12', y1: '20', x2: '12', y2: '4' }),
  h('line', { x1: '6', y1: '20', x2: '6', y2: '14' })
])

const PlusIcon = () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
  h('line', { x1: '12', y1: '5', x2: '12', y2: '19' }),
  h('line', { x1: '5', y1: '12', x2: '19', y2: '12' })
])

const UploadIcon = () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
  h('path', { d: 'M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4' }),
  h('polyline', { points: '17 8 12 3 7 8' }),
  h('line', { x1: '12', y1: '3', x2: '12', y2: '15' })
])

const PlayIcon = () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
  h('polygon', { points: '5 3 19 12 5 21 5 3' })
])

const BrainIcon = () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
  h('path', { d: 'M9.5 2A2.5 2.5 0 0112 4.5v15a2.5 2.5 0 01-4.96.44 2.5 2.5 0 01-2.96-3.08 3 3 0 01-.34-5.58 2.5 2.5 0 011.32-4.24 2.5 2.5 0 011.98-3A2.5 2.5 0 019.5 2z' }),
  h('path', { d: 'M14.5 2A2.5 2.5 0 0112 4.5v15a2.5 2.5 0 004.96.44 2.5 2.5 0 002.96-3.08 3 3 0 00.34-5.58 2.5 2.5 0 00-1.32-4.24 2.5 2.5 0 00-1.98-3A2.5 2.5 0 0014.5 2z' })
])

const stats = ref<any[]>([
  { label: '图集总数', value: 0, color: '#00f0ff', gradient: 'radial-gradient(circle at 30% 30%, rgba(0, 240, 255, 0.2), transparent 70%)', icon: FolderIcon },
  { label: '图片总数', value: 0, color: '#ff00aa', gradient: 'radial-gradient(circle at 30% 30%, rgba(255, 0, 170, 0.2), transparent 70%)', icon: ImageIcon },
  { label: '模型数量', value: 0, color: '#00ff88', gradient: 'radial-gradient(circle at 30% 30%, rgba(0, 255, 136, 0.2), transparent 70%)', icon: BoxIcon },
  { label: '训练任务', value: 0, color: '#ffdd00', gradient: 'radial-gradient(circle at 30% 30%, rgba(255, 221, 0, 0.2), transparent 70%)', icon: ChartIcon },
])

const recentJobs = ref<any[]>([])
const statusText: Record<string, string> = {
  pending: '等待中',
  running: '进行中',
  completed: '已完成',
  failed: '失败',
}

const quickActions = [
  { label: '图集管理', path: '/atlas', icon: FolderIcon, color: '#00f0ff' },
  { label: '模型管理', path: '/models', icon: BoxIcon, color: '#ff00aa' },
  { label: '模型训练', path: '/training', icon: PlayIcon, color: '#ffdd00' },
  { label: '模型测试', path: '/launch', icon: BrainIcon, color: '#00ff88' },
]

// 系统状态
const systemStats = ref({
  cpu: { percent: 0, status: 'normal' },
  memory: { total: 0, used: 0, percent: 0, status: 'normal' },
  disk: { total: 0, used: 0, percent: 0, status: 'normal' },
})

// WebSocket
let wsSystem: WebSocket | null = null
let wsTraining: WebSocket | null = null

const formatBytes = (bytes: number) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
}

const connectSystemWs = () => {
  wsSystem = new WebSocket('/ws/system')
  wsSystem.onmessage = (event) => {
    const data = JSON.parse(event.data)
    if (data.type === 'system_stats') {
      systemStats.value = data.data
    }
  }
  wsSystem.onclose = () => {
    setTimeout(connectSystemWs, 3000)
  }
}

const connectTrainingWs = () => {
  wsTraining = new WebSocket('/ws/training')
  wsTraining.onmessage = (event) => {
    const data = JSON.parse(event.data)
    if (data.type === 'training_update') {
      loadTrainingJobs()
    }
  }
  wsTraining.onclose = () => {
    setTimeout(connectTrainingWs, 3000)
  }
}

const loadTrainingJobs = async () => {
  try {
    const res = await trainingApi.listJobs()
    recentJobs.value = res.data.slice(0, 5)
    stats.value[3].value = res.data.length
  } catch (error) {
    console.error('Failed to load training jobs:', error)
  }
}

// 训练进度轮询
let trainingProgressTimer: number | null = null

const startTrainingProgressPolling = () => {
  if (trainingProgressTimer) return
  const poll = async () => {
    try {
      const res = await trainingApi.getProgress()
      const progress = res.data
      if (progress.status === 'running' || progress.status === 'downloading') {
        // 更新 running 任务的进度
        const runningJob = recentJobs.value.find(j => j.status === 'running')
        if (runningJob) {
          runningJob.current_step = progress.epoch
          runningJob.total_steps = progress.total_epochs
        }
        trainingProgressTimer = window.setTimeout(poll, 2000)
      } else if (progress.status === 'completed' || progress.status === 'failed') {
        loadTrainingJobs()
        stopTrainingProgressPolling()
      }
    } catch (e) {
      console.error('轮询训练进度失败', e)
      trainingProgressTimer = window.setTimeout(poll, 5000)
    }
  }
  poll()
}

const stopTrainingProgressPolling = () => {
  if (trainingProgressTimer) {
    clearTimeout(trainingProgressTimer)
    trainingProgressTimer = null
  }
}

const getProgress = (job: any) => {
  if (!job || !job.total_steps) return 0
  return Math.round((job.current_step / job.total_steps) * 100)
}

onMounted(async () => {
  try {
    const [atlasRes, imageRes, modelRes, trainingRes] = await Promise.all([
      atlasApi.list(),
      imageApi.list(),
      modelApi.list(),
      trainingApi.listJobs(),
    ])
    stats.value[0].value = atlasRes.data.length
    stats.value[1].value = imageRes.data.length
    stats.value[2].value = modelRes.data.length
    stats.value[3].value = trainingRes.data.length
    recentJobs.value = trainingRes.data.slice(0, 5)
  } catch (error) {
    console.error('Failed to load stats:', error)
  }
  // 连接系统状态 WebSocket
  connectSystemWs()
  // 连接训练状态 WebSocket
  connectTrainingWs()
  // 启动训练进度轮询
  startTrainingProgressPolling()
})

onUnmounted(() => {
  if (wsSystem) {
    wsSystem.close()
  }
  if (wsTraining) {
    wsTraining.close()
  }
  stopTrainingProgressPolling()
})
</script>

<style lang="scss" scoped>
.home {
  @apply flex flex-col gap-6;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
}

.stat-card {
  @apply relative overflow-hidden rounded-2xl p-6;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  animation: fadeInUp 0.6s ease forwards;
  @apply opacity-0;
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

.stat-glow {
  @apply absolute inset-0 pointer-events-none;
}

.stat-icon {
  @apply relative z-10 w-12 h-12 mb-4;
}

.stat-icon svg {
  @apply w-full h-full;
}

.stat-content {
  @apply relative z-10;
}

.stat-value {
  font-size: 36px;
  font-weight: 700;
  font-family: 'JetBrains Mono', monospace;
  @apply leading-none;
}

.stat-label {
  @apply text-sm text-[var(--text-secondary)] mt-2 uppercase tracking-wider;
}

.stat-decoration {
  @apply absolute bottom-0 right-0 overflow-hidden;
  width: 80px;
  height: 80px;
}

.decoration-line {
  @apply absolute rounded-full;
  bottom: -40px;
  right: -40px;
  width: 100px;
  height: 100px;
  border: 2px solid var(--border-color);
  @apply opacity-30;
}

.main-grid {
  display: grid;
  grid-template-columns: 1.5fr 1fr;
  gap: 24px;
}

.card-header {
  @apply flex items-center gap-3 p-5;
  border-bottom: 1px solid var(--border-color);
}

.header-line {
  @apply w-1 h-5 rounded-sm;
  background: linear-gradient(180deg, var(--accent-cyan), var(--accent-magenta));
}

.card-header h3 {
  @apply text-base font-semibold flex-1;
}

.header-badge {
  font-family: 'JetBrains Mono', monospace;
  @apply text-[10px] text-[var(--text-muted)] tracking-wider px-2 py-1 bg-[var(--bg-secondary)] rounded border border-[var(--border-color)];
}

.action-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  @apply p-6;
}

.action-tile {
  @apply flex flex-col items-center gap-3 p-6 bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-xl cursor-pointer transition-all relative overflow-hidden;
}

.action-tile:hover {
  border-color: var(--accent);
  @apply bg-[var(--bg-hover)] -translate-y-1;
}

.action-tile:hover .action-hover-effect {
  @apply opacity-100;
}

.action-hover-effect {
  @apply absolute inset-0 opacity-0 transition-opacity duration-300;
  background: radial-gradient(circle at center, var(--accent), transparent 70%);
}

.action-icon {
  @apply relative z-10 w-9 h-9;
  color: var(--accent);
}

.action-icon svg {
  @apply w-full h-full;
}

.action-label {
  @apply relative z-10 text-sm font-medium text-[var(--text-primary)];
}

.status-content {
  @apply p-6 flex flex-col gap-5;
}

.status-item {
  @apply flex flex-col gap-2;
}

.status-header {
  @apply flex justify-between items-center;
}

.status-label {
  @apply text-sm text-[var(--text-secondary)];
}

.status-value {
  font-family: 'JetBrains Mono', monospace;
  @apply text-xs text-[var(--text-primary)];
}

.status-indicator {
  @apply w-2 h-2 rounded-full;
  background: var(--accent-green);
  box-shadow: 0 0 10px var(--accent-green);
}

.status-indicator.warning {
  background: var(--accent-yellow);
  box-shadow: 0 0 10px var(--accent-yellow);
}

.status-indicator.danger {
  background: #ff4466;
  box-shadow: 0 0 10px #ff4466;
}

.status-bar {
  @apply h-1.5 rounded overflow-hidden;
  background: var(--bg-secondary);
}

.status-fill {
  @apply h-full rounded transition-all duration-1000;
  box-shadow: 0 0 10px currentColor;
}

.training-section {
  animation: fadeInUp 0.6s ease forwards;
  animation-delay: 0.4s;
  @apply opacity-0;
}

.training-content {
  @apply p-6;
}

.training-list {
  @apply flex flex-col gap-4;
}

.training-item {
  @apply bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-xl p-5 grid gap-5 items-center;
  grid-template-columns: 1fr 2fr 1fr;
}

.training-info {
  @apply flex flex-col gap-1.5;
}

.training-id {
  font-family: 'JetBrains Mono', monospace;
  @apply text-sm font-semibold text-[var(--text-primary)];
}

.training-status {
  @apply text-xs px-2 py-1 rounded w-fit;
}

.training-status.pending {
  background: rgba(136, 136, 170, 0.2);
  @apply text-[var(--text-secondary)];
}

.training-status.running {
  background: rgba(0, 240, 255, 0.2);
  @apply text-[var(--accent-cyan)];
}

.training-status.completed {
  background: rgba(0, 255, 136, 0.2);
  @apply text-[var(--accent-green)];
}

.training-status.failed {
  background: rgba(255, 68, 102, 0.2);
  @apply text-[#ff4466];
}

.training-progress {
  @apply flex items-center gap-3;
}

.progress-bar {
  @apply flex-1 h-2 rounded overflow-hidden;
  background: var(--bg-primary);
}

.progress-fill {
  @apply h-full rounded transition-all duration-500;
}

.progress-fill.pending { @apply bg-[var(--text-muted)]; }
.progress-fill.running {
  background: linear-gradient(90deg, var(--accent-cyan), var(--accent-magenta));
  box-shadow: 0 0 10px var(--accent-cyan);
}
.progress-fill.completed { @apply bg-[var(--accent-green)]; }
.progress-fill.failed { @apply bg-[#ff4466]; }

.progress-text {
  font-family: 'JetBrains Mono', monospace;
  @apply text-xs text-[var(--text-muted)] min-w-[100px] text-right;
}

.training-meta {
  @apply flex gap-3;
}

.meta-item {
  @apply text-xs text-[var(--text-muted)] px-2 py-1 bg-[var(--bg-primary)] rounded;
}

.empty-state {
  @apply flex flex-col items-center justify-center py-15 px-5 text-center;
}

.empty-icon {
  @apply w-16 h-16 text-[var(--text-muted)] mb-5 opacity-50;

  svg {
    @apply w-full h-full;
  }
}

.empty-state p {
  @apply text-base text-[var(--text-secondary)] mb-2;
}

.empty-state span {
  @apply text-sm text-[var(--text-muted)];
}
</style>
