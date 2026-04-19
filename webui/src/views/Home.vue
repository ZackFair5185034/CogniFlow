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
      <div class="quick-actions vg-card">
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
      <div class="system-status vg-card">
        <div class="card-header">
          <span class="header-line"></span>
          <h3>系统状态</h3>
          <span class="header-badge">SYSTEM STATUS</span>
        </div>
        <div class="status-content">
          <div class="status-item" v-for="item in systemStatus" :key="item.label">
            <div class="status-header">
              <span class="status-label">{{ item.label }}</span>
              <span class="status-indicator" :class="item.status"></span>
            </div>
            <div class="status-bar">
              <div class="status-fill" :style="{ width: item.value + '%', background: item.color }"></div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 训练进度 -->
    <div class="training-section vg-card">
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
import { ref, onMounted, h } from 'vue'
import { atlasApi, modelApi, trainingApi } from '@/api'

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

const quickActions = [
  { label: '创建图集', path: '/atlas', icon: PlusIcon, color: '#00f0ff' },
  { label: '上传数据', path: '/atlas', icon: UploadIcon, color: '#ff00aa' },
  { label: '开始训练', path: '/training', icon: PlayIcon, color: '#ffdd00' },
  { label: '模型推理', path: '/launch', icon: BrainIcon, color: '#00ff88' },
]

const systemStatus = [
  { label: 'GPU 利用率', value: 45, status: 'normal', color: '#00f0ff' },
  { label: '内存使用', value: 62, status: 'normal', color: '#ff00aa' },
  { label: '存储空间', value: 78, status: 'warning', color: '#ffdd00' },
]

const getProgress = (job: any) => {
  if (!job || !job.total_steps) return 0
  return Math.round((job.current_step / job.total_steps) * 100)
}

onMounted(async () => {
  try {
    const [atlasRes, modelRes, trainingRes] = await Promise.all([
      atlasApi.list(),
      modelApi.list(),
      trainingApi.listJobs(),
    ])
    stats.value[0].value = atlasRes.data.length
    stats.value[2].value = modelRes.data.length
    stats.value[3].value = trainingRes.data.length
    recentJobs.value = trainingRes.data.slice(0, 5)
  } catch (error) {
    console.error('Failed to load stats:', error)
  }
})
</script>

<style scoped>
.home {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
}

.stat-card {
  --un-rotate: 0;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 16px;
  padding: 24px;
  position: relative;
  overflow: hidden;
  animation: fadeInUp 0.6s ease forwards;
  opacity: 0;
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
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.stat-icon {
  width: 48px;
  height: 48px;
  margin-bottom: 16px;
  position: relative;
  z-index: 1;
}

.stat-icon svg {
  width: 100%;
  height: 100%;
}

.stat-content {
  position: relative;
  z-index: 1;
}

.stat-value {
  font-size: 36px;
  font-weight: 700;
  font-family: 'JetBrains Mono', monospace;
  line-height: 1;
}

.stat-label {
  font-size: 13px;
  color: var(--text-secondary);
  margin-top: 8px;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.stat-decoration {
  position: absolute;
  bottom: 0;
  right: 0;
  width: 80px;
  height: 80px;
  overflow: hidden;
}

.decoration-line {
  position: absolute;
  bottom: -40px;
  right: -40px;
  width: 100px;
  height: 100px;
  border: 2px solid var(--border-color);
  border-radius: 50%;
  opacity: 0.3;
}

.main-grid {
  display: grid;
  grid-template-columns: 1.5fr 1fr;
  gap: 24px;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-color);
}

.header-line {
  width: 4px;
  height: 20px;
  background: linear-gradient(180deg, var(--accent-cyan), var(--accent-magenta));
  border-radius: 2px;
}

.card-header h3 {
  font-size: 16px;
  font-weight: 600;
  flex: 1;
}

.header-badge {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  color: var(--text-muted);
  letter-spacing: 1px;
  padding: 4px 8px;
  background: var(--bg-secondary);
  border-radius: 4px;
  border: 1px solid var(--border-color);
}

.action-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  padding: 24px;
}

.action-tile {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 24px 16px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

.action-tile:hover {
  border-color: var(--accent);
  background: var(--bg-hover);
  transform: translateY(-4px);
}

.action-tile:hover .action-hover-effect {
  opacity: 1;
}

.action-hover-effect {
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at center, var(--accent), transparent 70%);
  opacity: 0;
  transition: opacity 0.3s ease;
}

.action-icon {
  width: 36px;
  height: 36px;
  color: var(--accent);
  position: relative;
  z-index: 1;
}

.action-icon svg {
  width: 100%;
  height: 100%;
}

.action-label {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
  position: relative;
  z-index: 1;
}

.status-content {
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.status-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
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

.status-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
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
  height: 6px;
  background: var(--bg-secondary);
  border-radius: 3px;
  overflow: hidden;
}

.status-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 1s ease;
  box-shadow: 0 0 10px currentColor;
}

.training-section {
  animation: fadeInUp 0.6s ease forwards;
  animation-delay: 0.4s;
  opacity: 0;
}

.training-content {
  padding: 24px;
}

.training-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.training-item {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 20px;
  display: grid;
  grid-template-columns: 1fr 2fr 1fr;
  gap: 20px;
  align-items: center;
}

.training-info {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.training-id {
  font-family: 'JetBrains Mono', monospace;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.training-status {
  font-size: 12px;
  padding: 3px 8px;
  border-radius: 4px;
  width: fit-content;
}

.training-status.pending {
  background: rgba(136, 136, 170, 0.2);
  color: var(--text-secondary);
}

.training-status.running {
  background: rgba(0, 240, 255, 0.2);
  color: var(--accent-cyan);
}

.training-status.completed {
  background: rgba(0, 255, 136, 0.2);
  color: var(--accent-green);
}

.training-status.failed {
  background: rgba(255, 68, 102, 0.2);
  color: #ff4466;
}

.training-progress {
  display: flex;
  align-items: center;
  gap: 12px;
}

.progress-bar {
  flex: 1;
  height: 8px;
  background: var(--bg-primary);
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.5s ease;
}

.progress-fill.pending { background: var(--text-muted); }
.progress-fill.running {
  background: linear-gradient(90deg, var(--accent-cyan), var(--accent-magenta));
  box-shadow: 0 0 10px var(--accent-cyan);
}
.progress-fill.completed { background: var(--accent-green); }
.progress-fill.failed { background: #ff4466; }

.progress-text {
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  color: var(--text-muted);
  min-width: 100px;
  text-align: right;
}

.training-meta {
  display: flex;
  gap: 12px;
}

.meta-item {
  font-size: 12px;
  color: var(--text-muted);
  padding: 4px 8px;
  background: var(--bg-primary);
  border-radius: 4px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  text-align: center;
}

.empty-icon {
  width: 64px;
  height: 64px;
  color: var(--text-muted);
  margin-bottom: 20px;
  opacity: 0.5;
}

.empty-icon svg {
  width: 100%;
  height: 100%;
}

.empty-state p {
  font-size: 16px;
  color: var(--text-secondary);
  margin-bottom: 8px;
}

.empty-state span {
  font-size: 13px;
  color: var(--text-muted);
}
</style>
