<template>
  <div class="training">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-info">
        <h2>训练监控</h2>
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
              <label>总步数</label>
              <div class="number-input">
                <button @click="startForm.total_steps = Math.max(100, startForm.total_steps - 100)">-</button>
                <input type="number" v-model="startForm.total_steps" min="100" max="100000" />
                <button @click="startForm.total_steps += 100">+</button>
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
                <div class="progress-fill running"
                     :style="{ width: getProgress(currentJob) + '%' }"></div>
              </div>
              <span class="progress-percent">{{ getProgress(currentJob) }}%</span>
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
const currentJob = computed(() => jobs.value.find(j => j.status === 'running') || null)
const runningCount = computed(() => jobs.value.filter(j => j.status === 'running').length)
const completedCount = computed(() => jobs.value.filter(j => j.status === 'completed' || j.status === 'failed').length)

const startForm = ref({
  model_id: null as number | null,
  atlas_id: null as number | null,
  total_steps: 1000,
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
      config: { total_steps: startForm.value.total_steps },
    })
    ElMessage.success('训练已启动')
    loadJobs()
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
  ws = new WebSocket(`ws://localhost:8000/api/ws/training`)
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

onMounted(() => {
  Promise.all([loadJobs(), loadModels(), loadAtlases()])
  connectWebSocket()
})

onUnmounted(() => {
  if (ws) ws.close()
})
</script>

<style scoped>
.training {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 20px;
}

.header-stats {
  display: flex;
  gap: 12px;
}

.header-info h2 {
  font-size: 24px;
  font-weight: 600;
  background: linear-gradient(90deg, var(--text-primary), var(--accent-cyan));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.header-info .subtitle {
  font-size: 13px;
  color: var(--text-muted);
  margin-left: 12px;
}

.header-stats {
  display: flex;
  gap: 12px;
}

.stat-pill {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 20px;
  font-size: 13px;
  font-weight: 500;
}

.stat-pill .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.stat-pill.running .dot {
  background: var(--accent-cyan);
  box-shadow: 0 0 10px var(--accent-cyan);
  animation: pulse 2s infinite;
}

.stat-pill.completed .dot {
  background: var(--accent-green);
  box-shadow: 0 0 10px var(--accent-green);
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

/* 网格布局 */
.training-grid {
  display: grid;
  grid-template-columns: 1.5fr 1fr;
  gap: 24px;
}

/* 训练列表 */
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-color);
}

.section-header h3 {
  font-size: 16px;
  font-weight: 600;
}

.refresh-btn {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s ease;
}

.refresh-btn:hover {
  border-color: var(--accent-cyan);
  color: var(--accent-cyan);
}

.refresh-btn svg {
  width: 18px;
  height: 18px;
}

.jobs-list {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 400px;
}

.job-item {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 16px;
  transition: all 0.3s ease;
}

.job-item:hover {
  border-color: var(--accent-cyan);
}

.job-item.active {
  border-color: var(--accent-cyan);
  box-shadow: 0 0 20px rgba(0, 240, 255, 0.2);
}

.job-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.job-id {
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
  font-weight: 600;
  color: var(--accent-cyan);
}

.job-status {
  font-size: 11px;
  padding: 3px 8px;
  border-radius: 4px;
}

.job-status.pending {
  background: rgba(136, 136, 170, 0.2);
  color: var(--text-secondary);
}

.job-status.running {
  background: rgba(0, 240, 255, 0.2);
  color: var(--accent-cyan);
}

.job-status.completed {
  background: rgba(0, 255, 136, 0.2);
  color: var(--accent-green);
}

.job-status.failed {
  background: rgba(255, 68, 102, 0.2);
  color: #ff4466;
}

.job-progress {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.progress-bar {
  flex: 1;
  height: 6px;
  background: var(--bg-primary);
  border-radius: 3px;
  overflow: hidden;
}

.progress-bar.large {
  height: 10px;
  border-radius: 5px;
}

.progress-fill {
  height: 100%;
  border-radius: 3px;
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
  font-size: 11px;
  color: var(--text-muted);
  min-width: 80px;
  text-align: right;
}

.job-meta {
  display: flex;
  gap: 8px;
}

.meta-tag {
  font-size: 11px;
  padding: 3px 8px;
  background: var(--bg-primary);
  border-radius: 4px;
  color: var(--text-muted);
}

.job-actions {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--border-color);
}

:deep(.el-button--text) {
  padding: 4px 0;
  border: none;
  background: transparent;
  color: #ff4466;
  font-size: 13px;
}

:deep(.el-button--text:hover) {
  color: #ff4466;
  background: transparent;
  border: none;
}

.empty-jobs {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  color: var(--text-muted);
}

.empty-icon {
  width: 64px;
  height: 64px;
  margin-bottom: 16px;
  opacity: 0.3;
}

.empty-icon svg {
  width: 100%;
  height: 100%;
}

.empty-jobs p {
  font-size: 16px;
  color: var(--text-secondary);
  margin-bottom: 8px;
}

.empty-jobs span {
  font-size: 13px;
}

/* 控制区 */
.control-section {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.start-training-card,
.realtime-card {
  animation: fadeInUp 0.6s ease forwards;
}

.start-form {
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-group label {
  font-size: 12px;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.select-wrapper {
  position: relative;
}

.select-wrapper select {
  width: 100%;
  padding: 12px 40px 12px 16px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  color: var(--text-primary);
  font-size: 14px;
  cursor: pointer;
  appearance: none;
  transition: all 0.2s ease;
}

.select-wrapper select:focus {
  outline: none;
  border-color: var(--accent-cyan);
}

.select-wrapper select option {
  background: var(--bg-card);
}

.select-wrapper::after {
  content: '';
  position: absolute;
  right: 16px;
  top: 50%;
  transform: translateY(-50%);
  width: 0;
  height: 0;
  border-left: 5px solid transparent;
  border-right: 5px solid transparent;
  border-top: 5px solid var(--text-muted);
  pointer-events: none;
}

.select-wrapper svg {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  width: 18px;
  height: 18px;
  color: var(--text-muted);
  pointer-events: none;
}

.number-input {
  display: flex;
  align-items: center;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  overflow: hidden;
}

.number-input button {
  width: 44px;
  height: 44px;
  background: transparent;
  border: none;
  color: var(--text-secondary);
  font-size: 18px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.number-input button:hover {
  background: var(--bg-hover);
  color: var(--accent-cyan);
}

.number-input input {
  flex: 1;
  padding: 12px;
  background: transparent;
  border: none;
  color: var(--text-primary);
  font-size: 14px;
  font-family: 'JetBrains Mono', monospace;
  text-align: center;
}

.number-input input:focus {
  outline: none;
}

.start-btn {
  width: 100%;
  justify-content: center;
  padding: 14px;
  font-size: 15px;
  margin-top: 8px;
}

.start-btn svg {
  width: 18px;
  height: 18px;
}

/* 实时状态 */
.live-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  color: #ff4466;
  letter-spacing: 1px;
}

.live-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #ff4466;
  animation: livePulse 1s infinite;
}

@keyframes livePulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(0.8); }
}

.realtime-content {
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.realtime-stat {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.realtime-stat .stat-label {
  font-size: 13px;
  color: var(--text-secondary);
}

.realtime-stat .stat-value {
  font-family: 'JetBrains Mono', monospace;
  font-size: 14px;
  font-weight: 600;
}

.realtime-stat .stat-value.status-running {
  color: var(--accent-cyan);
  text-shadow: 0 0 10px var(--accent-cyan);
}

.realtime-progress {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-top: 8px;
}

.progress-percent {
  font-family: 'JetBrains Mono', monospace;
  font-size: 24px;
  font-weight: 700;
  color: var(--accent-cyan);
  min-width: 60px;
  text-align: right;
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
