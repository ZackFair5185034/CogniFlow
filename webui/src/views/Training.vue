<template>
  <div class="training">
    <el-row :gutter="20">
      <el-col :span="16">
        <el-card>
          <template #header>
            <span>训练任务</span>
          </template>
          <el-table :data="jobs" v-loading="loading" style="width: 100%">
            <el-table-column prop="id" label="ID" width="80" />
            <el-table-column prop="model_id" label="模型ID" width="100" />
            <el-table-column prop="atlas_id" label="图集ID" width="100" />
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="getStatusType(row.status)">{{ row.status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="进度" width="200">
              <template #default="{ row }">
                <el-progress :percentage="getProgress(row)" :status="getProgressStatus(row.status)" />
              </template>
            </el-table-column>
            <el-table-column label="操作" width="150">
              <template #default="{ row }">
                <el-button v-if="row.status === 'running'" size="small" type="danger" @click="handleStop(row)">
                  停止
                </el-button>
                <el-button v-else-if="row.status === 'pending'" size="small" type="info" disabled>
                  等待中
                </el-button>
                <el-button v-else size="small" @click="handleViewHistory(row)">
                  查看
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>

      <el-col :span="8">
        <el-card>
          <template #header>
            <span>启动训练</span>
          </template>
          <el-form :model="startForm" label-width="100px">
            <el-form-item label="选择模型">
              <el-select v-model="startForm.model_id" placeholder="选择模型">
                <el-option v-for="m in models" :key="m.id" :label="m.name" :value="m.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="选择图集">
              <el-select v-model="startForm.atlas_id" placeholder="选择图集">
                <el-option v-for="a in atlases" :key="a.id" :label="a.name" :value="a.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="总步数">
              <el-input-number v-model="startForm.total_steps" :min="100" :max="100000" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="handleStart" :loading="starting">启动训练</el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <el-card style="margin-top: 20px">
          <template #header>
            <span>实时状态</span>
          </template>
          <div v-if="currentJob">
            <p>任务 #{{ currentJob.id }} - {{ currentJob.status }}</p>
            <el-progress :percentage="getProgress(currentJob)" :status="getProgressStatus(currentJob.status)" />
            <p class="metrics" v-if="currentJob.metrics">
              Loss: {{ currentJob.metrics.loss || '-' }}
            </p>
          </div>
          <el-empty v-else description="暂无运行中的任务" />
        </el-card>
      </el-col>
    </el-row>

    <el-dialog v-model="showHistoryDialog" title="训练历史" width="600px">
      <div v-if="metricsHistory.length > 0">
        <el-progress :percentage="getProgress(selectedJob)" style="margin-bottom: 20px" />
        <p>损失曲线（模拟数据）</p>
      </div>
      <el-empty v-else description="暂无历史数据" />
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { trainingApi, modelApi, atlasApi } from '@/api'

const jobs = ref<any[]>([])
const models = ref<any[]>([])
const atlases = ref<any[]>([])
const loading = ref(false)
const starting = ref(false)
const currentJob = ref<any>(null)
const showHistoryDialog = ref(false)
const metricsHistory = ref<any[]>([])
const selectedJob = ref<any>(null)

const startForm = ref({
  model_id: null as number | null,
  atlas_id: null as number | null,
  total_steps: 1000,
})

let ws: WebSocket | null = null

const getStatusType = (status: string) => {
  const map: Record<string, string> = {
    pending: 'info',
    running: 'primary',
    completed: 'success',
    failed: 'danger',
  }
  return map[status] || 'info'
}

const getProgress = (job: any) => {
  if (!job || !job.total_steps) return 0
  return Math.round((job.current_step / job.total_steps) * 100)
}

const getProgressStatus = (status: string) => {
  if (status === 'completed') return 'success'
  if (status === 'failed') return 'exception'
  return undefined
}

const loadJobs = async () => {
  try {
    const res = await trainingApi.listJobs()
    jobs.value = res.data
    currentJob.value = jobs.value.find(j => j.status === 'running') || null
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
  } catch (error) {
    ElMessage.error('启动失败')
  } finally {
    starting.value = false
  }
}

const handleStop = async (job: any) => {
  try {
    await trainingApi.stop(job.id)
    ElMessage.success('训练已停止')
    loadJobs()
  } catch (error) {
    ElMessage.error('停止失败')
  }
}

const handleViewHistory = async (job: any) => {
  selectedJob.value = job
  try {
    const res = await trainingApi.getMetricsHistory(job.id)
    metricsHistory.value = res.data.history || []
  } catch (error) {
    metricsHistory.value = []
  }
  showHistoryDialog.value = true
}

const connectWebSocket = (jobId: number) => {
  ws = new WebSocket(`ws://localhost:8000/api/ws/training/${jobId}`)
  ws.onmessage = (event) => {
    const data = JSON.parse(event.data)
    if (data.type === 'training_update') {
      loadJobs()
    }
  }
  ws.onclose = () => {
    setTimeout(() => connectWebSocket(jobId), 3000)
  }
}

onMounted(() => {
  loadJobs()
  loadModels()
  loadAtlases()
  const runningJob = jobs.value.find(j => j.status === 'running')
  if (runningJob) {
    connectWebSocket(runningJob.id)
  }
})

onUnmounted(() => {
  if (ws) {
    ws.close()
  }
})
</script>

<style scoped>
.metrics {
  margin-top: 10px;
  font-size: 14px;
  color: #606266;
}
</style>
