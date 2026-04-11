<template>
  <div class="home">
    <el-row :gutter="20">
      <el-col :span="6">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <el-icon><Folder /></el-icon>
              <span>图集</span>
            </div>
          </template>
          <div class="stat-value">{{ stats.atlasCount }}</div>
          <div class="stat-label">总数量</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <el-icon><Picture /></el-icon>
              <span>图片</span>
            </div>
          </template>
          <div class="stat-value">{{ stats.imageCount }}</div>
          <div class="stat-label">总数量</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <el-icon><Box /></el-icon>
              <span>模型</span>
            </div>
          </template>
          <div class="stat-value">{{ stats.modelCount }}</div>
          <div class="stat-label">总数量</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <el-icon><TrendCharts /></el-icon>
              <span>训练</span>
            </div>
          </template>
          <div class="stat-value">{{ stats.trainingCount }}</div>
          <div class="stat-label">总任务数</div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>快速操作</span>
          </template>
          <el-space wrap>
            <el-button type="primary" @click="$router.push('/atlas')">创建图集</el-button>
            <el-button type="success" @click="$router.push('/models')">注册模型</el-button>
            <el-button type="warning" @click="$router.push('/training')">开始训练</el-button>
            <el-button type="info" @click="$router.push('/launch')">启动模型</el-button>
          </el-space>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>最近训练</span>
          </template>
          <el-table :data="recentJobs" style="width: 100%">
            <el-table-column prop="id" label="ID" width="60" />
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="getStatusType(row.status)">{{ row.status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="current_step" label="进度">
              <template #default="{ row }">
                {{ row.current_step }} / {{ row.total_steps }}
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { atlasApi, modelApi, trainingApi } from '@/api'

const stats = ref({
  atlasCount: 0,
  imageCount: 0,
  modelCount: 0,
  trainingCount: 0,
})

const recentJobs = ref<any[]>([])

const getStatusType = (status: string) => {
  const map: Record<string, string> = {
    pending: 'info',
    running: 'primary',
    completed: 'success',
    failed: 'danger',
  }
  return map[status] || 'info'
}

onMounted(async () => {
  try {
    const [atlasRes, modelRes, trainingRes] = await Promise.all([
      atlasApi.list(),
      modelApi.list(),
      trainingApi.listJobs(),
    ])
    stats.value.atlasCount = atlasRes.data.length
    stats.value.modelCount = modelRes.data.length
    stats.value.trainingCount = trainingRes.data.length
    recentJobs.value = trainingRes.data.slice(0, 5)
  } catch (error) {
    console.error('Failed to load stats:', error)
  }
})
</script>

<style scoped>
.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
}
.stat-value {
  font-size: 32px;
  font-weight: bold;
  color: #409eff;
}
.stat-label {
  color: #909399;
  font-size: 14px;
}
</style>
