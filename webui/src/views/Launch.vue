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
                <ChevronIcon />
              </div>
            </div>
          </div>

          <!-- 控制按钮 -->
          <div class="control-buttons">
            <button class="vg-btn control-btn load" @click="handleLoad" :disabled="!selectedModelId || loading">
              <DownloadIcon />
              加载模型
            </button>
            <button class="vg-btn vg-btn-success control-btn start" @click="handleStart"
                    :disabled="!status.loaded || status.inference_running">
              <PlayIcon />
              开始执行
            </button>
            <button class="vg-btn vg-btn-danger control-btn stop" @click="handleStop"
                    :disabled="!status.inference_running">
              <StopIcon />
              停止执行
            </button>
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
  } catch (error) {
    ElMessage.error('模型加载失败')
  } finally {
    loading.value = false
  }
}

const handleStart = async () => {
  try {
    await launchApi.start()
    ElMessage.success('推理已开始')
    loadStatus()
  } catch (error) {
    ElMessage.error('启动失败')
  }
}

const handleStop = async () => {
  try {
    await launchApi.stop()
    ElMessage.success('推理已停止')
    loadStatus()
  } catch (error) {
    ElMessage.error('停止失败')
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

<style scoped>
.launch {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
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

.system-status {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 20px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 30px;
}

.status-indicator {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--text-muted);
}

.status-indicator.active {
  background: var(--accent-green);
  box-shadow: 0 0 15px var(--accent-green);
  animation: statusGlow 2s infinite;
}

@keyframes statusGlow {
  0%, 100% { box-shadow: 0 0 15px var(--accent-green); }
  50% { box-shadow: 0 0 25px var(--accent-green); }
}

.status-text {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
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

.realtime-panel {
  animation: fadeInUp 0.6s ease forwards;
  animation-delay: 0.1s;
  opacity: 0;
}

.guide-panel {
  animation: fadeInUp 0.6s ease forwards;
  animation-delay: 0.2s;
  opacity: 0;
}

/* 面板头部 */
.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-color);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.panel-icon {
  width: 24px;
  height: 24px;
  color: var(--accent-cyan);
}

.panel-header h3 {
  font-size: 16px;
  font-weight: 600;
}

.mode-badge,
.live-indicator {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  letter-spacing: 1px;
  padding: 6px 12px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  color: var(--text-muted);
}

.live-indicator {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #ff4466;
}

.live-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #ff4466;
  animation: livePulse 1s infinite;
}

@keyframes livePulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

/* 控制内容 */
.control-content {
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.section-label {
  display: block;
  font-size: 12px;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 10px;
}

.model-select .select-wrapper {
  position: relative;
}

.model-select select {
  width: 100%;
  padding: 14px 50px 14px 16px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  color: var(--text-primary);
  font-size: 15px;
  cursor: pointer;
  appearance: none;
  transition: all 0.2s ease;
}

.model-select select:focus {
  outline: none;
  border-color: var(--accent-cyan);
  box-shadow: 0 0 0 3px rgba(0, 240, 255, 0.1);
}

.model-select select:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.model-select select option {
  background: var(--bg-card);
  padding: 12px;
}

.select-wrapper::after {
  content: '';
  position: absolute;
  right: 16px;
  top: 50%;
  transform: translateY(-50%);
  border-left: 6px solid transparent;
  border-right: 6px solid transparent;
  border-top: 6px solid var(--text-muted);
  pointer-events: none;
}

/* 控制按钮 */
.control-buttons {
  display: flex;
  gap: 12px;
}

.control-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 14px 16px;
  font-size: 14px;
  font-weight: 500;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.control-btn svg {
  width: 18px;
  height: 18px;
}

.control-btn.load {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  color: var(--text-primary);
}

.control-btn.load:hover:not(:disabled) {
  border-color: var(--accent-cyan);
  color: var(--accent-cyan);
}

.control-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
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
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.status-item.full {
  grid-column: span 2;
}

.status-label {
  font-size: 11px;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.status-value {
  font-size: 16px;
  font-weight: 600;
}

.status-value.success {
  color: var(--accent-green);
}

.status-value.running {
  color: var(--accent-cyan);
  text-shadow: 0 0 10px var(--accent-cyan);
}

.status-value.muted {
  color: var(--text-muted);
}

.status-value.mono {
  font-family: 'JetBrains Mono', monospace;
}

/* 实时内容 */
.realtime-content {
  padding: 24px;
}

.metrics-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.metric-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 12px;
}

.metric-icon {
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 240, 255, 0.1);
  border-radius: 10px;
  color: var(--accent-cyan);
}

.metric-icon.fps {
  background: rgba(255, 0, 170, 0.1);
  color: var(--accent-magenta);
}

.metric-icon.status-icon {
  background: rgba(0, 255, 136, 0.1);
  color: var(--accent-green);
}

.metric-icon.status-icon.running {
  animation: iconPulse 1s infinite;
}

@keyframes iconPulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.1); }
}

.metric-icon svg {
  width: 22px;
  height: 22px;
}

.metric-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.metric-value {
  font-family: 'JetBrains Mono', monospace;
  font-size: 22px;
  font-weight: 700;
  color: var(--text-primary);
}

.metric-label {
  font-size: 11px;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* 空状态 */
.empty-realtime {
  padding: 60px 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.empty-graphic {
  position: relative;
  width: 80px;
  height: 80px;
  margin-bottom: 20px;
}

.pulse-ring {
  position: absolute;
  inset: 0;
  border: 2px solid var(--accent-cyan);
  border-radius: 50%;
  opacity: 0;
  animation: pulseRing 2s infinite;
}

.pulse-ring.delay {
  animation-delay: 1s;
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
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 36px;
  height: 36px;
  color: var(--text-muted);
}

.empty-realtime p {
  font-size: 15px;
  color: var(--text-secondary);
  margin-bottom: 6px;
}

.empty-realtime span {
  font-size: 13px;
  color: var(--text-muted);
}

/* 操作指南 */
.guide-content {
  padding: 20px 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.guide-step {
  display: flex;
  align-items: flex-start;
  gap: 14px;
}

.step-number {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, var(--accent-cyan), var(--accent-magenta));
  border-radius: 8px;
  font-size: 12px;
  font-weight: 700;
  color: var(--bg-primary);
  flex-shrink: 0;
}

.step-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.step-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
}

.step-desc {
  font-size: 12px;
  color: var(--text-muted);
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
