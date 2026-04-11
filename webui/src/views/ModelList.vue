<template>
  <div class="model-list">
    <el-card>
      <template #header>
        <div class="header-actions">
          <span>模型列表</span>
          <el-button type="primary" @click="showCreateDialog = true">注册模型</el-button>
        </div>
      </template>
      <el-table :data="models" v-loading="loading" style="width: 100%">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="name" label="名称" />
        <el-table-column prop="version" label="版本" width="100" />
        <el-table-column label="最佳" width="80">
          <template #default="{ row }">
            <el-tag v-if="row.is_best" type="success" size="small">最佳</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="metrics" label="指标" width="150">
          <template #default="{ row }">
            <span v-if="row.metrics">{{ row.metrics.loss || row.metrics.accuracy || '-' }}</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="280">
          <template #default="{ row }">
            <el-button size="small" @click="handleUpload(row)">上传模型</el-button>
            <el-button size="small" type="primary" @click="handleSetBest(row)" :disabled="row.is_best">设为最佳</el-button>
            <el-button size="small" type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="showCreateDialog" title="注册模型" width="400px">
      <el-form :model="createForm" label-width="80px">
        <el-form-item label="名称">
          <el-input v-model="createForm.name" placeholder="请输入模型名称" />
        </el-form-item>
        <el-form-item label="版本">
          <el-input v-model="createForm.version" placeholder="如 v1, v2" />
        </el-form-item>
        <el-form-item label="训练图集">
          <el-select v-model="createForm.atlas_id" placeholder="选择图集（可选）" clearable>
            <el-option v-for="atlas in atlases" :key="atlas.id" :label="atlas.name" :value="atlas.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="handleCreate" :loading="creating">注册</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showUploadDialog" title="上传模型文件" width="400px">
      <el-upload
        ref="uploadRef"
        :auto-upload="false"
        :limit="1"
        :on-change="handleFileChange"
        accept=".pt,.pth,.onnx"
      >
        <el-button>选择模型文件</el-button>
      </el-upload>
      <template #footer>
        <el-button @click="showUploadDialog = false">取消</el-button>
        <el-button type="primary" @click="handleUploadSubmit" :loading="uploading">上传</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { modelApi, atlasApi } from '@/api'

const models = ref<any[]>([])
const atlases = ref<any[]>([])
const loading = ref(false)
const showCreateDialog = ref(false)
const creating = ref(false)
const showUploadDialog = ref(false)
const uploading = ref(false)
const uploadRef = ref()
const selectedModel = ref<any>(null)
const uploadFile = ref<File | null>(null)

const createForm = ref({ name: '', version: '', atlas_id: null as number | null })

const formatDate = (dateStr: string) => {
  return new Date(dateStr).toLocaleString()
}

const loadModels = async () => {
  loading.value = true
  try {
    const res = await modelApi.list()
    models.value = res.data
  } catch (error) {
    ElMessage.error('加载模型列表失败')
  } finally {
    loading.value = false
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

const handleCreate = async () => {
  if (!createForm.value.name) {
    ElMessage.warning('请输入模型名称')
    return
  }
  creating.value = true
  try {
    await modelApi.create(createForm.value)
    ElMessage.success('注册成功')
    showCreateDialog.value = false
    createForm.value = { name: '', version: '', atlas_id: null }
    loadModels()
  } catch (error) {
    ElMessage.error('注册失败')
  } finally {
    creating.value = false
  }
}

const handleUpload = (row: any) => {
  selectedModel.value = row
  uploadFile.value = null
  showUploadDialog.value = true
}

const handleFileChange = (file: any) => {
  uploadFile.value = file.raw
}

const handleUploadSubmit = async () => {
  if (!uploadFile.value) {
    ElMessage.warning('请选择模型文件')
    return
  }
  uploading.value = true
  try {
    await modelApi.upload(selectedModel.value.id, uploadFile.value)
    ElMessage.success('上传成功')
    showUploadDialog.value = false
    loadModels()
  } catch (error) {
    ElMessage.error('上传失败')
  } finally {
    uploading.value = false
  }
}

const handleSetBest = async (row: any) => {
  try {
    await modelApi.setBest(row.id)
    ElMessage.success('已设为最佳模型')
    loadModels()
  } catch (error) {
    ElMessage.error('操作失败')
  }
}

const handleDelete = async (row: any) => {
  try {
    await ElMessageBox.confirm(`确定删除模型 "${row.name}" 吗？`, '提示', { type: 'warning' })
    await modelApi.delete(row.id)
    ElMessage.success('删除成功')
    loadModels()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

onMounted(() => {
  loadModels()
  loadAtlases()
})
</script>

<style scoped>
.header-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
