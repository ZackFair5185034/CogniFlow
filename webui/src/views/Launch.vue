<template>
  <div class="launch">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-info">
        <h2>模型启动</h2>
        <span class="subtitle">推理模式控制</span>
      </div>
      <div class="system-status">
        <span class="status-indicator" :class="{ active: status.loaded }"></span>
        <span class="status-text">{{ status.loaded ? '模型已就绪' : '等待加载' }}</span>
      </div>
    </div>

    <div class="launch-grid">
      <!-- 主控制面板 -->
      <div class="control-panel vg-card">
        <div class="panel-header">
          <div class="header-left">
            <BrainIcon class="panel-icon" />
            <h3>推理控制</h3>
          </div>
          <span class="mode-badge">INFERENCE MODE</span>
        </div>

        <div class="control-content">
          <!-- 模型选择 -->
          <div class="control-section">
            <label class="section-label">选择模型</label>
            <div class="model-select">
              <div class="select-wrapper">
                <select v-model="selectedModelId" :disabled="status.inference_running">
                  <option :value="null" disabled>选择要加载的模型</option>
                  <option v-for="m in models" :key="m.id" :value="m.id">
                    {{ m.name }}{{ m.version ? ` (${m.version})` : '' }}
                  </option>
                </select>
              </div>
            </div>
          </div>

          <!-- 控制按钮 -->
          <div class="control-buttons">
            <el-button class="control-btn" @click="handleLoad" :disabled="!selectedModelId || loading">
              <DownloadIcon />
              加载模型
            </el-button>
            <el-button class="control-btn success" @click="handleStart" :disabled="!status.loaded || status.inference_running">
              <PlayIcon />
              开始执行
            </el-button>
            <el-button class="control-btn danger" @click="handleStop" :disabled="!status.inference_running">
              <StopIcon />
              停止执行
            </el-button>
          </div>

          <!-- 状态显示 -->
          <div class="status-grid">
            <div class="status-item">
              <span class="status-label">模型状态</span>
              <span class="status-value" :class="status.loaded ? 'success' : 'muted'">
                {{ status.loaded ? '已加载' : '未加载' }}
              </span>
            </div>
            <div class="status-item">
              <span class="status-label">执行状态</span>
              <span class="status-value" :class="status.inference_running ? 'running' : 'muted'">
                {{ status.inference_running ? '运行中' : '已停止' }}
              </span>
            </div>
            <div class="status-item full">
              <span class="status-label">模型信息</span>
              <span class="status-value mono">
                {{ status.info?.model_id ? `ID: ${status.info.model_id}` : '-' }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- 实时数据面板 -->
      <div class="realtime-panel vg-card">
        <div class="panel-header">
          <div class="header-left">
            <ActivityIcon class="panel-icon" />
            <h3>实时推理</h3>
          </div>
          <span class="live-indicator" v-if="realtimeStatus">
            <span class="live-dot"></span>
            LIVE
          </span>
        </div>

        <div class="realtime-content" v-if="realtimeStatus">
          <div class="metrics-grid">
            <div class="metric-card">
              <div class="metric-icon">
                <HashIcon />
              </div>
              <div class="metric-info">
                <span class="metric-value">{{ realtimeStatus.inference_step || 0 }}</span>
                <span class="metric-label">推理步数</span>
              </div>
            </div>

            <div class="metric-card">
              <div class="metric-icon fps">
                <SpeedIcon />
              </div>
              <div class="metric-info">
                <span class="metric-value">{{ realtimeStatus.fps || 0 }}</span>
                <span class="metric-label">FPS</span>
              </div>
            </div>

            <div class="metric-card">
              <div class="metric-icon">
                <CheckIcon />
              </div>
              <div class="metric-info">
                <span class="metric-value">{{ realtimeStatus.detections || 0 }}</span>
                <span class="metric-label">检测数</span>
              </div>
            </div>

            <div class="metric-card">
              <div class="metric-icon status-icon" :class="realtimeStatus.status">
                <ActivityIcon />
              </div>
              <div class="metric-info">
                <span class="metric-value">{{ realtimeStatus.status || 'idle' }}</span>
                <span class="metric-label">状态</span>
              </div>
            </div>
          </div>
        </div>

        <div class="empty-realtime" v-else>
          <div class="empty-graphic">
            <div class="pulse-ring"></div>
            <div class="pulse-ring delay"></div>
            <BrainIcon class="empty-icon" />
          </div>
          <p>暂无实时数据</p>
          <span>加载模型并启动推理后显示</span>
        </div>
      </div>

      <!-- 操作指南 -->
      <div class="guide-panel vg-card">
        <div class="panel-header">
          <div class="header-left">
            <HelpIcon class="panel-icon" />
            <h3>操作指南</h3>
          </div>
        </div>
        <div class="guide-content">
          <div class="guide-step" v-for="(step, index) in guideSteps" :key="index">
            <div class="step-number">{{ index + 1 }}</div>
            <div class="step-content">
              <span class="step-title">{{ step.title }}</span>
              <span class="step-desc">{{ step.desc }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, h } from 'vue'
import { ElMessage } from 'element-plus'
import { launchApi, modelApi } from '@/api'

const models = ref<any[]>([])
const selectedModelId = ref<number | null>(null)
const loading = ref(false)
const status = ref({
  loaded: false,
  inference_running: false,
  info: {} as any,
})
const realtimeStatus = ref<any>(null)

let ws: WebSocket | null = null

// 图标
const BrainIcon = () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
  h('path', { d: 'M9.5 2A2.5 2.5 0 0112 4.5v15a2.5 2.5 0 01-4.96.44 2.5 2.5 0 01-2.96-3.08 3 3 0 01-.34-5.58 2.5 2.5 0 011.32-4.24 2.5 2.5 0 011.98-3A2.5 2.5 0 019.5 2z' }),
  h('path', { d: 'M14.5 2A2.5 2.5 0 0112 4.5v15a2.5 2.5 0 004.96.44 2.5 2.5 0 002.96-3.08 3 3 0 00.34-5.58 2.5 2.5 0 00-1.32-4.24 2.5 2.5 0 00-1.98-3A2.5 2.5 0 0014.5 2z' })
])

const ActivityIcon = () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
  h('polyline', { points: '22 12 18 12 15 21 9 3 6 12 2 12' })
])

const ChevronIcon = () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
  h('polyline', { points: '6 9 12 15 18 9' })
])

const DownloadIcon = () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
  h('path', { d: 'M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4' }),
  h('polyline', { points: '7 10 12 15 17 10' }),
  h('line', { x1: '12', y1: '15', x2: '12', y2: '3' })
])

const PlayIcon = () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
  h('polygon', { points: '5 3 19 12 5 21 5 3' })
])

const StopIcon = () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
  h('rect', { x: '3', y: '3', width: '18', height: '18', rx: '2', ry: '2' })
])

const HashIcon = () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
  h('line', { x1: '4', y1: '9', x2: '20', y2: '9' }),
  h('line', { x1: '4', y1: '15', x2: '20', y2: '15' }),
  h('line', { x1: '10', y1: '3', x2: '8', y2: '21' }),
  h('line', { x1: '16', y1: '3', x2: '14', y2: '21' })
])

const SpeedIcon = () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
  h('path', { d: 'M12 2L2 7l10 5 10-5-10-5z' }),
  h('path', { d: 'M2 17l10 5 10-5' }),
  h('path', { d: 'M2 12l10 5 10-5' })
])

const CheckIcon = () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
  h('polyline', { points: '20 6 9 17 4 12' })
])

const HelpIcon = () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
  h('circle', { cx: '12', cy: '12', r: '10' }),
  h('path', { d: 'M9.09 9a3 3 0 015.83 1c0 2-3 3-3 3' }),
  h('line', { x1: '12', y1: '17', x2: '12.01', y2: '17' })
])

const guideSteps = [
  { title: '选择模型', desc: '从下拉列表中选择要加载的模型' },
  { title: '加载模型', desc: '点击"加载模型"按钮等待加载完成' },
  { title: '启动推理', desc: '模型加载后点击"开始执行"启动推理' },
  { title: '监控状态', desc: '实时查看推理步数、FPS等指标' },
]

const loadModels = async () => {
  try {
    const res = await modelApi.list()
    models.value = res.data
  } catch (error) {
    console.error('加载模型失败', error)
  }
}

const loadStatus = async () => {
  try {
    const res = await launchApi.status()
    status.value = res.data
  } catch (error) {
    console.error('加载状态失败', error)
  }
}

const handleLoad = async () => {
  if (!selectedModelId.value) return
  loading.value = true
  try {
    await launchApi.load(selectedModelId.value)
    ElMessage.success('模型加载成功')
    loadStatus()
  } catch (error: any) {
    const msg = error.response?.data?.detail || '模型加载失败'
    ElMessage.error(msg)
  } finally {
    loading.value = false
  }
}

const handleStart = async () => {
  try {
    await launchApi.start()
    ElMessage.success('推理已开始')
    loadStatus()
  } catch (error: any) {
    const msg = error.response?.data?.detail || '启动失败'
    ElMessage.error(msg)
  }
}

const handleStop = async () => {
  try {
    await launchApi.stop()
    ElMessage.success('推理已停止')
    loadStatus()
  } catch (error: any) {
    const msg = error.response?.data?.detail || '停止失败'
    ElMessage.error(msg)
  }
}

const connectWebSocket = () => {
  ws = new WebSocket('ws://localhost:8000/api/ws/launch')
  ws.onmessage = (event) => {
    const data = JSON.parse(event.data)
    if (data.type === 'launch_update') {
      realtimeStatus.value = data.data
    }
  }
  ws.onclose = () => {
    setTimeout(connectWebSocket, 3000)
  }
}

onMounted(() => {
  loadModels()
  loadStatus()
  connectWebSocket()
})

onUnmounted(() => {
  if (ws) ws.close()
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

.system-status {
  @apply flex items-center gap-2.5 px-5 py-2.5 bg-[var(--bg-card)] border border-[var(--border-color)] rounded-full;
}

.status-indicator {
  @apply w-2.5 h-2.5 rounded-full bg-[var(--text-muted)];
}

.status-indicator.active {
  @apply bg-[var(--accent-green)];
  box-shadow: 0 0 15px var(--accent-green);
  animation: statusGlow 2s infinite;
}

@keyframes statusGlow {
  0%, 100% { box-shadow: 0 0 15px var(--accent-green); }
  50% { box-shadow: 0 0 25px var(--accent-green); }
}

.status-text {
  @apply text-sm font-medium text-[var(--text-secondary)];
}

/* 网格布局 */
.launch-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  grid-template-rows: auto auto;
  gap: 24px;
}

.control-panel {
  grid-row: span 2;
  animation: fadeInUp 0.6s ease forwards;
}

.realtime-panel,
.guide-panel {
  animation: fadeInUp 0.6s ease forwards;
}

.realtime-panel {
  animation-delay: 0.1s;
}

.guide-panel {
  animation-delay: 0.2s;
}

/* 面板头部 */
.panel-header {
  @apply flex justify-between items-center px-6 py-5 border-b border-[var(--border-color)];
}

.header-left {
  @apply flex items-center gap-3;
}

.panel-icon {
  @apply w-6 h-6 text-[var(--accent-cyan)];
}

.panel-header h3 {
  @apply text-base font-semibold;
}

.mode-badge,
.live-indicator {
  @apply font-mono text-xs tracking-wider px-3 py-1.5 bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded text-[var(--text-muted)];
}

.live-indicator {
  @apply flex items-center gap-1.5 text-[#ff4466];
}

.live-dot {
  @apply w-1.5 h-1.5 rounded-full bg-[#ff4466];
  animation: livePulse 1s infinite;
}

@keyframes livePulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

/* 控制内容 */
.control-content {
  @apply p-6 flex flex-col gap-6;
}

.section-label {
  @apply block text-xs text-[var(--text-secondary)] uppercase tracking-wide mb-2.5;
}

.model-select {
  .select-wrapper {
    @apply relative;
  }

  select {
    @apply w-full px-4 py-3.5 bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-lg text-[var(--text-primary)] text-base cursor-pointer appearance-none transition-all;

    &:focus {
      @apply outline-none border-[var(--accent-cyan)];
      box-shadow: 0 0 0 3px rgba(0, 240, 255, 0.1);
    }

    &:disabled {
      @apply opacity-50 cursor-not-allowed;
    }

    option {
      @apply bg-[var(--bg-card)] p-3;
    }
  }
}

.select-wrapper::after {
  content: '';
  @apply absolute right-4 top-1/2 -translate-y-1/2 border-l-1.5 border-r-1.5 border-t-1.5 border-l-transparent border-r-transparent border-t-[var(--text-muted)];
  pointer-events: none;
}

/* 控制按钮 */
.control-buttons {
  @apply flex gap-3.5;
}

:deep(.control-btn) {
  @apply flex-1 inline-flex items-center justify-center gap-2.5 px-5 py-3.5 text-sm font-medium font-sans whitespace-nowrap border border-[var(--border-color)] rounded-lg bg-[var(--bg-card)] text-[var(--text-primary)] cursor-pointer transition-all;

  &:hover:not(:disabled) {
    @apply border-[var(--accent-cyan)] text-[var(--accent-cyan)];
    background: rgba(0, 240, 255, 0.05);
  }

  &:disabled {
    @apply opacity-40 cursor-not-allowed;
  }

  &.success {
    @apply border-[var(--accent-green)] text-[var(--accent-green)];
    &:hover:not(:disabled) {
      background: rgba(0, 255, 136, 0.08);
    }
  }

  &.danger {
    @apply border-[#ff4466] text-[#ff4466];
    &:hover:not(:disabled) {
      background: rgba(255, 68, 102, 0.08);
    }
  }

  svg {
    @apply w-4 h-4 shrink-0;
  }
}

/* 状态网格 */
.status-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  padding-top: 20px;
  border-top: 1px solid var(--border-color);
}

.status-item {
  @apply flex flex-col gap-1.5;

  &.full {
    grid-column: span 2;
  }
}

.status-label {
  @apply text-xs text-[var(--text-muted)] uppercase tracking-wide;
}

.status-value {
  @apply text-base font-semibold;

  &.success {
    @apply text-[var(--accent-green)];
  }

  &.running {
    @apply text-[var(--accent-cyan)];
    text-shadow: 0 0 10px var(--accent-cyan);
  }

  &.muted {
    @apply text-[var(--text-muted)];
  }

  &.mono {
    @apply font-mono;
  }
}

/* 实时内容 */
.realtime-content {
  @apply p-6;
}

.metrics-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.metric-card {
  @apply flex items-center gap-3.5 p-4 bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-xl;
}

.metric-icon {
  @apply w-11 h-11 flex items-center justify-center bg-[rgba(0,240,255,0.1)] rounded-lg text-[var(--accent-cyan)];

  &.fps {
    @apply bg-[rgba(255,0,170,0.1)] text-[var(--accent-magenta)];
  }

  &.status-icon {
    @apply bg-[rgba(0,255,136,0.1)] text-[var(--accent-green)];

    &.running {
      animation: iconPulse 1s infinite;
    }
  }

  svg {
    @apply w-5.5 h-5.5;
  }
}

@keyframes iconPulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.1); }
}

.metric-info {
  @apply flex flex-col gap-1;
}

.metric-value {
  @apply font-mono text-xl font-bold text-[var(--text-primary)];
}

.metric-label {
  @apply text-xs text-[var(--text-muted)] uppercase tracking-wide;
}

/* 空状态 */
.empty-realtime {
  @apply p-15 flex flex-col items-center text-center;
}

.empty-graphic {
  @apply relative w-20 h-20 mb-5;
}

.pulse-ring {
  @apply absolute inset-0 border-2 border-[var(--accent-cyan)] rounded-full opacity-0;
  animation: pulseRing 2s infinite;

  &.delay {
    animation-delay: 1s;
  }
}

@keyframes pulseRing {
  0% {
    transform: scale(0.5);
    opacity: 0.8;
  }
  100% {
    transform: scale(1.5);
    opacity: 0;
  }
}

.empty-icon {
  @apply absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-9 h-9 text-[var(--text-muted)];
}

.empty-realtime p {
  @apply text-base text-[var(--text-secondary)] mb-1.5;
}

.empty-realtime span {
  @apply text-sm text-[var(--text-muted)];
}

/* 操作指南 */
.guide-content {
  @apply p-5 flex flex-col gap-4;
}

.guide-step {
  @apply flex items-start gap-3.5;
}

.step-number {
  @apply w-7 h-7 flex items-center justify-center bg-gradient-to-br from-[var(--accent-cyan)] to-[var(--accent-magenta)] rounded-lg text-xs font-bold text-[var(--bg-primary)] shrink-0;
}

.step-content {
  @apply flex flex-col gap-1;
}

.step-title {
  @apply text-sm font-medium text-[var(--text-primary)];
}

.step-desc {
  @apply text-xs text-[var(--text-muted)];
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
