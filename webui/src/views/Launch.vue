<template>
  <div class="launch">
    <el-card>
      <template #header>
        <span>模型启动控制</span>
      </template>

      <el-row :gutter="20">
        <el-col :span="12">
          <el-form label-width="100px">
            <el-form-item label="选择模型">
              <el-select v-model="selectedModelId" placeholder="选择要加载的模型" style="width: 100%">
                <el-option v-for="m in models" :key="m.id" :label="m.name + (m.version ? ` (${m.version})` : '')" :value="m.id" />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="handleLoad" :loading="loading" :disabled="!selectedModelId">
                加载模型
              </el-button>
              <el-button type="success" @click="handleStart" :disabled="!status.loaded || status.inference_running">
                开始执行
              </el-button>
              <el-button type="danger" @click="handleStop" :disabled="!status.inference_running">
                停止执行
              </el-button>
            </el-form-item>
          </el-form>
        </el-col>

        <el-col :span="12">
          <el-descriptions border title="状态信息">
            <el-descriptions-item label="模型状态">
              <el-tag :type="status.loaded ? 'success' : 'info'">
                {{ status.loaded ? '已加载' : '未加载' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="执行状态">
              <el-tag :type="status.inference_running ? 'primary' : 'info'">
                {{ status.inference_running ? '运行中' : '已停止' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="模型信息">
              {{ status.info?.model_id ? `ID: ${status.info.model_id}` : '-' }}
            </el-descriptions-item>
          </el-descriptions>
        </el-col>
      </el-row>
    </el-card>

    <el-card style="margin-top: 20px">
      <template #header>
        <span>实时推理状态</span>
      </template>
      <div v-if="realtimeStatus" class="realtime-info">
        <el-row :gutter="20">
          <el-col :span="8">
            <div class="stat-box">
              <div class="stat-label">推理步数</div>
              <div class="stat-value">{{ realtimeStatus.inference_step }}</div>
            </div>
          </el-col>
          <el-col :span="8">
            <div class="stat-box">
              <div class="stat-label">FPS</div>
              <div class="stat-value">{{ realtimeStatus.fps }}</div>
            </div>
          </el-col>
          <el-col :span="8">
            <div class="stat-box">
              <div class="stat-label">状态</div>
              <div class="stat-value">{{ realtimeStatus.status }}</div>
            </div>
          </el-col>
        </el-row>
      </div>
      <el-empty v-else description="暂无实时数据，请先加载并启动模型" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
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
  if (ws) {
    ws.close()
  }
})
</script>

<style scoped>
.realtime-info {
  padding: 20px 0;
}
.stat-box {
  text-align: center;
  padding: 20px;
  background: #f5f7fa;
  border-radius: 4px;
}
.stat-label {
  font-size: 14px;
  color: #909399;
}
.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #409eff;
  margin-top: 8px;
}
</style>
