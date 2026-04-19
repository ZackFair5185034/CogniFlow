<template>
  <div class="model-list">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-info">
        <h2>模型管理</h2>
        <span class="subtitle">管理训练模型</span>
      </div>
      <button class="vg-btn vg-btn-primary" @click="showCreateDialog = true">
        <PlusIcon />
        注册模型
      </button>
    </div>

    <!-- 模型列表 -->
    <div class="vg-card">
      <div class="table-container">
        <el-table :data="models" v-loading="loading" style="width: 100%" :row-class-name="tableRowClassName">
          <el-table-column prop="id" label="ID" width="100">
            <template #default="{ row }">
              <span class="id-badge">#{{ row.id }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="name" label="名称">
            <template #default="{ row }">
              <div class="name-cell">
                <BoxIcon class="model-icon" />
                <span>{{ row.name }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="version" label="版本" width="120">
            <template #default="{ row }">
              <span class="version-badge" v-if="row.version">{{ row.version }}</span>
              <span v-else class="text-muted">-</span>
            </template>
          </el-table-column>
          <el-table-column label="最佳" width="80">
            <template #default="{ row }">
              <span class="best-badge" v-if="row.is_best">
                <StarIcon />
                最佳
              </span>
            </template>
          </el-table-column>
          <el-table-column label="指标" width="150">
            <template #default="{ row }">
              <span v-if="row.metrics" class="metric-value">
                {{ row.metrics.loss || row.metrics.accuracy || '-' }}
              </span>
              <span v-else class="text-muted">-</span>
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="创建时间" width="160">
            <template #default="{ row }">
              <span class="time-badge">{{ formatDate(row.created_at) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="200" fixed="right">
            <template #default="{ row }">
              <div class="action-buttons">
                <el-button type="text" @click="handleUpload(row)">上传</el-button>
                <el-button type="text" @click="handleSetBest(row)" :disabled="row.is_best">最佳</el-button>
                <el-button type="text" @click="handleDelete(row)">删除</el-button>
              </div>
            </template>
          </el-table-column>
        </el-table>

        <div class="empty-state" v-if="!loading && models.length === 0">
          <div class="empty-icon">
            <BoxIcon />
          </div>
          <p>暂无模型</p>
          <span>注册第一个模型开始训练</span>
        </div>
      </div>
    </div>

    <!-- 创建对话框 -->
    <div class="dialog-overlay" v-if="showCreateDialog" @click.self="showCreateDialog = false">
      <div class="dialog-panel vg-card">
        <div class="dialog-header">
          <h3>注册模型</h3>
          <button class="close-btn" @click="showCreateDialog = false">
            <CloseIcon />
          </button>
        </div>
        <div class="dialog-body">
          <div class="form-group">
            <label>模型名称</label>
            <input type="text" v-model="createForm.name" placeholder="输入模型名称" />
          </div>
          <div class="form-group">
            <label>版本</label>
            <input type="text" v-model="createForm.version" placeholder="如 v1, v2" />
          </div>
          <div class="form-group">
            <label>训练图集（可选）</label>
            <div class="select-wrapper">
              <select v-model="createForm.atlas_id">
                <option :value="null">不关联图集</option>
                <option v-for="atlas in atlases" :key="atlas.id" :value="atlas.id">
                  {{ atlas.name }}
                </option>
              </select>
            </div>
          </div>
        </div>
        <div class="dialog-footer">
          <button class="vg-btn" @click="showCreateDialog = false">取消</button>
          <button class="vg-btn vg-btn-primary" @click="handleCreate" :disabled="creating">
            {{ creating ? '注册中...' : '注册' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 上传对话框 -->
    <div class="dialog-overlay" v-if="showUploadDialog" @click.self="showUploadDialog = false">
      <div class="dialog-panel vg-card">
        <div class="dialog-header">
          <h3>上传模型文件</h3>
          <button class="close-btn" @click="showUploadDialog = false">
            <CloseIcon />
          </button>
        </div>
        <div class="dialog-body">
          <div class="upload-area">
            <input ref="fileInputRef" type="file" accept=".pt,.pth,.onnx" style="display: none" @change="handleFileChange" />
            <button class="upload-btn" @click="fileInputRef?.click()">
              <UploadIcon />
              <span>{{ uploadFile ? uploadFile.name : '选择模型文件' }}</span>
            </button>
            <p class="upload-hint">支持 .pt, .pth, .onnx 格式</p>
          </div>
        </div>
        <div class="dialog-footer">
          <button class="vg-btn" @click="showUploadDialog = false">取消</button>
          <button class="vg-btn vg-btn-primary" @click="handleUploadSubmit" :disabled="!uploadFile || uploading">
            {{ uploading ? '上传中...' : '上传' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, h } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { modelApi, atlasApi } from '@/api'

const models = ref<any[]>([])
const atlases = ref<any[]>([])
const loading = ref(false)
const showCreateDialog = ref(false)
const creating = ref(false)
const showUploadDialog = ref(false)
const uploading = ref(false)
const fileInputRef = ref<HTMLInputElement | null>(null)
const selectedModel = ref<any>(null)
const uploadFile = ref<File | null>(null)

const createForm = ref({ name: '', version: '', atlas_id: null as number | null })

// 图标组件
const PlusIcon = () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
  h('line', { x1: '12', y1: '5', x2: '12', y2: '19' }),
  h('line', { x1: '5', y1: '12', x2: '19', y2: '12' })
])

const BoxIcon = () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
  h('path', { d: 'M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 003 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0021 16z' }),
  h('polyline', { points: '3.27 6.96 12 12.01 20.73 6.96' }),
  h('line', { x1: '12', y1: '22.08', x2: '12', y2: '12' })
])

const StarIcon = () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
  h('polygon', { points: '12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2' })
])

const UploadIcon = () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
  h('path', { d: 'M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4' }),
  h('polyline', { points: '17 8 12 3 7 8' }),
  h('line', { x1: '12', y1: '3', x2: '12', y2: '15' })
])

const CheckIcon = () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
  h('polyline', { points: '20 6 9 17 4 12' })
])

const TrashIcon = () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
  h('polyline', { points: '3 6 5 6 21 6' }),
  h('path', { d: 'M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2' })
])

const CloseIcon = () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
  h('line', { x1: '18', y1: '6', x2: '6', y2: '18' }),
  h('line', { x1: '6', y1: '6', x2: '18', y2: '18' })
])

const formatDate = (dateStr: string) => {
  return new Date(dateStr).toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const tableRowClassName = ({ rowIndex }: { rowIndex: number }) => {
  return rowIndex % 2 === 0 ? 'even-row' : 'odd-row'
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
  } catch (error: any) {
    const msg = error.response?.data?.detail || '注册失败'
    ElMessage.error(msg)
  } finally {
    creating.value = false
  }
}

const handleUpload = (row: any) => {
  selectedModel.value = row
  uploadFile.value = null
  showUploadDialog.value = true
}

const handleFileChange = (event: Event) => {
  const input = event.target as HTMLInputElement
  if (input.files && input.files.length > 0) {
    uploadFile.value = input.files[0]
  }
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
    await ElMessageBox.confirm(`确定删除模型 "${row.name}" 吗？此操作不可撤销。`, '删除确认', {
      type: 'warning',
      confirmButtonText: '确认',
      cancelButtonText: '取消',
    })
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
.model-list {
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

.vg-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.vg-btn svg {
  width: 18px;
  height: 18px;
}

/* 表格样式覆盖 */
.table-container {
  padding: 0;
}

:deep(.el-table) {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: var(--bg-secondary);
  --el-table-row-hover-bg-color: var(--bg-hover);
  --el-table-border-color: var(--border-color);
  --el-table-text-color: var(--text-primary);
  --el-table-header-text-color: var(--text-secondary);
}

:deep(.el-table th.el-table__cell) {
  background: var(--bg-secondary);
  font-weight: 500;
  text-transform: uppercase;
  font-size: 11px;
  letter-spacing: 1px;
}

:deep(.el-table td.el-table__cell) {
  border-bottom: 1px solid var(--border-color);
  padding: 16px 12px;
}

:deep(.even-row) {
  background: var(--bg-card);
}

:deep(.odd-row) {
  background: rgba(26, 26, 36, 0.5);
}

.id-badge {
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  color: var(--accent-cyan);
  padding: 4px 8px;
  background: rgba(0, 240, 255, 0.1);
  border-radius: 4px;
}

.name-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}

.model-icon {
  width: 20px;
  height: 20px;
  color: var(--accent-magenta);
}

.version-badge {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  padding: 3px 8px;
  background: rgba(255, 221, 0, 0.1);
  color: var(--accent-yellow);
  border: 1px solid rgba(255, 221, 0, 0.3);
  border-radius: 4px;
}

.best-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  padding: 4px 8px;
  background: rgba(0, 255, 136, 0.1);
  color: var(--accent-green);
  border: 1px solid rgba(0, 255, 136, 0.3);
  border-radius: 4px;
}

.best-badge svg {
  width: 12px;
  height: 12px;
}

.metric-value {
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
  color: var(--accent-cyan);
}

.time-badge {
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  color: var(--text-muted);
}

.text-muted {
  color: var(--text-muted);
}

.action-buttons {
  display: flex;
  gap: 16px;
  align-items: center;
}

:deep(.el-button--text) {
  padding: 4px 0;
  border: none;
  background: transparent;
  color: var(--accent-cyan);
  font-size: 13px;
}

:deep(.el-button--text:hover) {
  color: var(--accent-cyan);
  background: transparent;
  border: none;
}

:deep(.el-button--text:last-child:hover) {
  color: #ff4466;
}

:deep(.el-button--text:disabled) {
  color: var(--text-muted);
  opacity: 0.5;
}

/* 空状态 */
.empty-state {
  padding: 80px 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.empty-icon {
  width: 80px;
  height: 80px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-secondary);
  border-radius: 20px;
  margin-bottom: 20px;
  color: var(--text-muted);
  opacity: 0.5;
}

.empty-icon svg {
  width: 40px;
  height: 40px;
}

.empty-state p {
  font-size: 18px;
  color: var(--text-secondary);
  margin-bottom: 8px;
}

.empty-state span {
  font-size: 14px;
  color: var(--text-muted);
}

/* 对话框 */
.dialog-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.dialog-panel {
  width: 450px;
  max-width: 90vw;
  animation: dialogIn 0.3s ease;
}

@keyframes dialogIn {
  from {
    opacity: 0;
    transform: scale(0.95) translateY(20px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

.dialog-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-color);
}

.dialog-header h3 {
  font-size: 18px;
  font-weight: 600;
}

.close-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  border-radius: 6px;
  transition: all 0.2s ease;
}

.close-btn:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.close-btn svg {
  width: 18px;
  height: 18px;
}

.dialog-body {
  padding: 24px;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 8px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.form-group input,
.form-group select {
  width: 100%;
  padding: 12px 16px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  color: var(--text-primary);
  font-size: 14px;
  font-family: inherit;
  transition: all 0.2s ease;
}

.form-group input:focus,
.form-group select:focus {
  outline: none;
  border-color: var(--accent-cyan);
  box-shadow: 0 0 0 3px rgba(0, 240, 255, 0.1);
}

.form-group input::placeholder {
  color: var(--text-muted);
}

.select-wrapper {
  position: relative;
}

.select-wrapper select {
  appearance: none;
  cursor: pointer;
}

.select-wrapper::after {
  content: '';
  position: absolute;
  right: 14px;
  top: 50%;
  transform: translateY(-50%);
  border-left: 5px solid transparent;
  border-right: 5px solid transparent;
  border-top: 5px solid var(--text-muted);
  pointer-events: none;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 20px 24px;
  border-top: 1px solid var(--border-color);
}

/* 上传区域 */
.upload-area {
  text-align: center;
  padding: 20px;
}

.upload-btn {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 16px 24px;
  background: var(--bg-secondary);
  border: 2px dashed var(--border-color);
  border-radius: 12px;
  color: var(--text-secondary);
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.upload-btn:hover {
  border-color: var(--accent-cyan);
  color: var(--accent-cyan);
}

.upload-btn svg {
  width: 24px;
  height: 24px;
}

.upload-hint {
  margin-top: 12px;
  font-size: 12px;
  color: var(--text-muted);
}
</style>
