<template>
  <div
    class="flex flex-col gap-5 relative min-h-[400px]"
  >
    <LoadingSpinner
      v-if="loading"
      overlay
      text="加载统计信息..."
    />
    <template v-else>
      <!-- 统计卡片 -->
      <div class="grid grid-cols-4 gap-4">
        <div
          v-for="stat in stats"
          :key="stat.label"
          class="stat-card"
        >
          <div class="stat-icon">
            <SvgIcon :name="stat.icon" />
          </div>
          <div class="stat-content">
            <div class="stat-value">
              {{ stat.value }}
            </div>
            <div class="stat-label">
              {{ stat.label }}
            </div>
          </div>
        </div>
      </div>

      <!-- 主功能区 -->
      <div class="main-grid">
        <!-- 快速操作 -->
        <div class="ui-card">
          <div class="ui-card-header">
            <h3>快速操作</h3>
          </div>
          <div class="action-grid">
            <button
              v-for="action in quickActions"
              :key="action.label"
              class="action-tile"
              @click="$router.push(action.path)"
            >
              <div class="action-icon">
                <SvgIcon :name="action.icon" />
              </div>
              <span class="action-label">{{ action.label }}</span>
            </button>
          </div>
        </div>

        <!-- 系统状态 -->
        <div class="ui-card">
          <div class="ui-card-header">
            <h3>系统状态</h3>
          </div>
          <div class="status-content">
            <div
              v-for="item in statusItems"
              :key="item.label"
              class="status-item"
            >
              <div class="status-header">
                <span class="status-label">{{ item.label }}</span>
                <span class="status-value">{{ item.value }}</span>
              </div>
              <div class="status-bar">
                <div
                  class="status-fill"
                  :class="item.status"
                  :style="{ width: item.percent + '%' }"
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 训练进度 -->
      <div class="ui-card">
        <div class="ui-card-header">
          <h3>训练进度</h3>
        </div>
        <div class="ui-card-content">
          <div
            v-if="recentJobs.length > 0"
            class="training-list"
          >
            <div
              v-for="job in recentJobs"
              :key="job.id"
              class="training-item"
            >
              <div class="training-info">
                <span class="training-id">TASK #{{ job.id.toString().padStart(4, '0') }}</span>
                <span
                  class="training-status"
                  :class="job.status"
                >
                  {{ statusText[job.status] || job.status }}
                </span>
              </div>
              <div class="training-progress">
                <div class="progress-bar">
                  <div
                    class="progress-fill"
                    :class="job.status"
                    :style="{ width: getProgress(job) + '%' }"
                  />
                </div>
                <span class="progress-text">{{ job.current_step }} / {{ job.total_steps }}</span>
              </div>
              <div class="training-meta">
                <span class="meta-item">Model #{{ job.model_id }}</span>
                <span class="meta-item">Atlas #{{ job.atlas_id }}</span>
              </div>
            </div>
          </div>
          <div
            v-else
            class="empty-state"
          >
            <div class="empty-icon">
              <SvgIcon name="clock" />
            </div>
            <p>暂无训练任务</p>
            <span class="empty-hint">开始一个新训练来监控进度</span>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { atlasApi, imageApi, modelApi, trainingApi } from '@/api'
import type { TrainingJobResponse } from '@/types/api'
import { useWebSocket } from '@/composables/useWebSocket'

interface SystemStats {
  cpu: { percent: number }
  memory: { percent: number; used: number; total: number }
  disk: { percent: number; used: number; total: number }
  gpu: { percent: number; memory_used: number; memory_total: number; name: string | null }
}

const loading = ref(true)

interface StatItem {
  label: string
  value: number
  icon: string
}

const stats = ref<StatItem[]>([
  { label: '图集总数', value: 0, icon: 'folder' },
  { label: '图片总数', value: 0, icon: 'image' },
  { label: '模型数量', value: 0, icon: 'box' },
  { label: '训练任务', value: 0, icon: 'chart' },
])

const recentJobs = ref<TrainingJobResponse[]>([])
const statusText: Record<string, string> = {
  pending: '等待中',
  running: '进行中',
  completed: '已完成',
  failed: '失败',
}

const quickActions = [
  { label: '图集管理', path: '/atlas', icon: 'folder' },
  { label: '模型管理', path: '/models', icon: 'box' },
  { label: '模型训练', path: '/training', icon: 'play' },
  { label: '模型测试', path: '/launch', icon: 'brain' },
]

// 系统状态
const systemStats = ref<SystemStats>({
  cpu: { percent: 0 },
  memory: { total: 0, used: 0, percent: 0 },
  disk: { total: 0, used: 0, percent: 0 },
  gpu: { percent: 0, memory_used: 0, memory_total: 0, name: null },
})

const formatBytes = (bytes: number) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`
}

const statusItems = computed(() => {
  const s = systemStats.value
  return [
    {
      label: 'CPU 使用率',
      value: `${s.cpu.percent.toFixed(1)}%`,
      percent: s.cpu.percent,
      status: s.cpu.percent > 80 ? 'danger' : 'normal',
    },
    {
      label: '内存',
      value: `${formatBytes(s.memory.used)} / ${formatBytes(s.memory.total)}`,
      percent: s.memory.percent,
      status: s.memory.percent > 80 ? 'danger' : 'normal',
    },
    {
      label: '存储空间',
      value: `${formatBytes(s.disk.used)} / ${formatBytes(s.disk.total)}`,
      percent: s.disk.percent,
      status: s.disk.percent > 90 ? 'danger' : 'normal',
    },
    {
      label: s.gpu.name || 'GPU 使用率',
      value: s.gpu.memory_total > 0
        ? `${formatBytes(s.gpu.memory_used)} / ${formatBytes(s.gpu.memory_total)}`
        : `${s.gpu.percent.toFixed(1)}%`,
      percent: s.gpu.percent,
      status: s.gpu.percent > 80 ? 'danger' : 'normal',
    },
  ]
})

// WebSocket (P1-B, 2026-09-11): 改用统一 composable, 自动重连 + 卸载清理
useWebSocket<{ type: string; data: SystemStats }>({
  url: '/ws/system',
  onMessage: (msg) => {
    if (msg.type === 'system_stats') {
      systemStats.value = msg.data
    }
  },
})

useWebSocket<{ type: string }>({
  url: '/ws/training',
  onMessage: (msg) => {
    if (msg.type === 'training_update') {
      loadTrainingJobs()
    }
  },
})

const loadTrainingJobs = async () => {
  try {
    const res = await trainingApi.listJobs()
    recentJobs.value = res.data.slice(0, 5)
    stats.value[3].value = res.data.length
  } catch (error) {
    console.error('加载训练任务失败:', error)
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

const getProgress = (job: TrainingJobResponse) => {
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
    console.error('加载统计数据失败:', error)
  } finally {
    loading.value = false
  }
  // WebSocket 由 composable 自动建立 + 自动卸载清理 (P1-B, 2026-09-11)
  startTrainingProgressPolling()
})

onUnmounted(() => {
  // useWebSocket composable 已在 onUnmounted 内部自动 close (P1-B)
  stopTrainingProgressPolling()
})
</script>

<style lang="scss" scoped>
.stat-card {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  padding: 20px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
}

.stat-icon {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--accent-blue);
  flex-shrink: 0;

  svg {
    width: 24px;
    height: 24px;
  }
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  font-family: var(--font-family-mono);
  line-height: 1.1;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.stat-label {
  font-size: 13px;
  color: var(--text-secondary);
}

.main-grid {
  display: grid;
  grid-template-columns: 1.5fr 1fr;
  gap: 20px;
}

.action-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  padding: 20px;
}

.action-tile {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 24px 16px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.15s ease;
  color: var(--text-primary);
  font-family: inherit;

  &:hover {
    background: var(--bg-hover);
    border-color: var(--accent-blue);
  }
}

.action-icon {
  width: 32px;
  height: 32px;
  color: var(--accent-blue);

  svg {
    width: 100%;
    height: 100%;
  }
}

.action-label {
  font-size: 13px;
  font-weight: 500;
}

.status-content {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.status-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.status-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.status-label {
  font-size: 13px;
  color: var(--text-secondary);
}

.status-value {
  font-family: var(--font-family-mono);
  font-size: 12px;
  color: var(--text-primary);
}

.status-bar {
  height: 4px;
  border-radius: 2px;
  background: var(--bg-secondary);
  overflow: hidden;
}

.status-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 0.5s ease;

  &.normal {
    background: var(--accent-blue);
  }

  &.danger {
    background: var(--color-danger);
  }
}

.training-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.training-item {
  display: grid;
  grid-template-columns: 1fr 2fr 1fr;
  gap: 16px;
  align-items: center;
  padding: 14px 16px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
}

.training-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.training-id {
  font-family: var(--font-family-mono);
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.training-status {
  font-size: 11px;
  padding: 1px 8px;
  border-radius: 4px;
  width: fit-content;

  &.pending { background: var(--color-info-bg); color: var(--accent-blue); }
  &.running { background: var(--color-info-bg); color: var(--accent-blue); }
  &.completed { background: var(--color-success-bg); color: var(--color-success); }
  &.failed { background: var(--color-danger-bg); color: var(--color-danger); }
}

.training-progress {
  display: flex;
  align-items: center;
  gap: 12px;
}

.progress-bar {
  flex: 1;
  height: 6px;
  border-radius: 3px;
  background: var(--bg-primary);
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.5s ease;

  &.pending { background: var(--text-muted); }
  &.running { background: var(--accent-blue); }
  &.completed { background: var(--color-success); }
  &.failed { background: var(--color-danger); }
}

.progress-text {
  font-family: var(--font-family-mono);
  font-size: 11px;
  color: var(--text-muted);
  min-width: 90px;
  text-align: right;
  flex-shrink: 0;
}

.training-meta {
  display: flex;
  gap: 8px;
}

.meta-item {
  font-size: 11px;
  color: var(--text-muted);
  padding: 2px 8px;
  background: var(--bg-primary);
  border-radius: 4px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 20px;
  text-align: center;
}

.empty-icon {
  width: 48px;
  height: 48px;
  color: var(--text-muted);
  opacity: 0.4;
  margin-bottom: 16px;

  svg {
    width: 100%;
    height: 100%;
  }
}

.empty-state p {
  font-size: 14px;
  color: var(--text-secondary);
  margin-bottom: 4px;
}

.empty-hint {
  font-size: 12px;
  color: var(--text-muted);
}
</style>
