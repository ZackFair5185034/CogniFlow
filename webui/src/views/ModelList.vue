<template>
  <div class="model-list">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-info">
        <h2>模型管理</h2>
        <span class="subtitle">管理训练模型</span>
      </div>
      <button class="ui-btn ui-btn-primary" @click="showCreateDialog = true">
        <PlusIcon />
        注册模型
      </button>
    </div>

    <!-- 模型列表 -->
    <div class="ui-card" style="width: 100%; min-width: 0;">
      <div class="table-wrapper">
        <el-table :data="models" v-loading="loading" :row-class-name="tableRowClassName" table-layout="auto">
          <el-table-column prop="id" label="ID" width="80">
            <template #default="{ row }">
              <span class="id-badge">#{{ row.id }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="name" label="名称" min-width="150">
            <template #default="{ row }">
              <div class="name-cell">
                <BoxIcon class="model-icon" />
                <span>{{ row.name }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="version" label="版本" width="100">
            <template #default="{ row }">
              <span class="version-badge" v-if="row.version">{{ row.version }}</span>
              <span v-else class="text-muted">-</span>
            </template>
          </el-table-column>
          <el-table-column prop="pretrained_model" label="预训练" width="120">
            <template #default="{ row }">
              <span class="text-muted" v-if="!row.pretrained_model">-</span>
              <span v-else>{{ row.pretrained_model.replace('.pt', '') }}</span>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <span class="status-badge" :class="row.file_path ? 'trained' : 'untrained'">
                {{ row.file_path ? '已训练' : '未训练' }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="性能指标" width="180">
            <template #default="{ row }">
              <div v-if="row.metrics?.mAP50" class="metrics-cell">
                <span class="metric-item">
                  <span class="metric-label">mAP50:</span>
                  <span class="metric-value">{{ (row.metrics.mAP50 * 100).toFixed(1) }}%</span>
                </span>
                <span class="metric-item" v-if="row.metrics?.mAP50_95">
                  <span class="metric-label">mAP:</span>
                  <span class="metric-value">{{ (row.metrics.mAP50_95 * 100).toFixed(1) }}%</span>
                </span>
              </div>
              <span v-else class="text-muted">-</span>
            </template>
          </el-table-column>
          <el-table-column label="模型文件" min-width="200">
            <template #default="{ row }">
              <span v-if="row.file_path" class="file-path" :title="row.file_path">
                {{ shortenPath(row.file_path) }}
              </span>
              <span v-else class="text-muted">-</span>
            </template>
          </el-table-column>
          <el-table-column label="训练时间" width="140">
            <template #default="{ row }">
              <span v-if="row.metrics?.trained_at" class="time-badge">
                {{ formatTrainedAt(row.metrics.trained_at) }}
              </span>
              <span v-else class="text-muted">-</span>
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="创建时间" width="140">
            <template #default="{ row }">
              <span class="time-badge">{{ formatDate(row.created_at) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="160" fixed="right">
            <template #default="{ row }">
              <div class="action-buttons">
                <el-button type="text" @click="handleUpload(row)" v-if="!row.file_path">上传</el-button>
                <el-button type="text" @click="handleSetBest(row)" :disabled="row.is_best || !row.file_path">最佳</el-button>
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
      <div class="dialog-panel ui-card">
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
          <div class="form-group">
            <label>预训练模型</label>
            <div class="select-wrapper">
              <select v-model="createForm.pretrained_model">
                <option value="yolov8n.pt">YOLOv8n (最小最快)</option>
                <option value="yolov8s.pt">YOLOv8s (小，推荐)</option>
                <option value="yolov8m.pt">YOLOv8m (中)</option>
                <option value="yolov8l.pt">YOLOv8l (大)</option>
                <option value="yolov8x.pt">YOLOv8x (最大最准)</option>
              </select>
            </div>
          </div>
        </div>
        <div class="dialog-footer">
          <button class="ui-btn" @click="showCreateDialog = false">取消</button>
          <button class="ui-btn ui-btn-primary" @click="handleCreate" :disabled="creating">
            {{ creating ? '注册中...' : '注册' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 上传对话框 -->
    <div class="dialog-overlay" v-if="showUploadDialog" @click.self="showUploadDialog = false">
      <div class="dialog-panel ui-card">
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
          <button class="ui-btn" @click="showUploadDialog = false">取消</button>
          <button class="ui-btn ui-btn-primary" @click="handleUploadSubmit" :disabled="!uploadFile || uploading">
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

const createForm = ref({ name: '', version: '', pretrained_model: 'yolov8s.pt', atlas_id: null as number | null })

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

const formatTrainedAt = (dateStr: string) => {
  if (!dateStr) return '-'
  const date = new Date(dateStr.replace('_', ' ').replace(/(\d{4})(\d{2})(\d{2})/, '$1-$2-$3'))
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const shortenPath = (path: string) => {
  if (!path) return ''
  if (path.length <= 40) return path
  const parts = path.split(/[/\\]/)
  if (parts.length > 3) {
    return `.../${parts.slice(-3).join('/')}`
  }
  return path
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
    createForm.value = { name: '', version: '', pretrained_model: 'yolov8s.pt', atlas_id: null }
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

<style lang="scss" scoped>
.model-list {
  @apply flex flex-col gap-6;
}

.page-header {
  @apply flex justify-between items-center;
  flex-wrap: wrap;
  gap: 16px;
}

.header-info {
  @apply flex items-baseline;
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

/* 表格包装器 - 响应式滚动 */
.table-wrapper {
  width: 100%;
  overflow-x: auto;
  min-width: 0;

  :deep(.el-table) {
    table-layout: auto;
  }
}

/* 表格样式覆盖 */
:deep(.el-table) {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: var(--bg-secondary);
  --el-table-row-hover-bg-color: var(--bg-hover);
  --el-table-border-color: var(--border-color);
  --el-table-text-color: var(--text-primary);
  --el-table-header-text-color: var(--text-secondary);

  th.el-table__cell {
    @apply bg-[var(--bg-secondary)] font-medium uppercase text-xs tracking-wider;
  }

  td.el-table__cell {
    @apply border-b border-[var(--border-color)] py-4 px-3;
  }
}

:deep(.even-row) {
  @apply bg-[var(--bg-card)];
}

:deep(.odd-row) {
  background: rgba(26, 26, 36, 0.5);
}

.id-badge {
  @apply font-mono text-xs text-[var(--accent-cyan)] px-2 py-1 bg-[rgba(0,240,255,0.1)] rounded;
}

.name-cell {
  @apply flex items-center gap-2.5;
}

.model-icon {
  @apply w-5 h-5 text-[var(--accent-magenta)];
}

.version-badge {
  @apply font-mono text-xs px-2 py-1 bg-[rgba(255,221,0,0.1)] text-[var(--accent-yellow)] border border-[rgba(255,221,0,0.3)] rounded;
}

.best-badge {
  @apply inline-flex items-center gap-1 text-xs px-2 py-1 bg-[rgba(0,255,136,0.1)] text-[var(--accent-green)] border border-[rgba(0,255,136,0.3)] rounded;

  svg {
    @apply w-3 h-3;
  }
}

.status-badge {
  @apply inline-flex items-center gap-1 text-xs px-2 py-1 rounded;

  &.trained {
    @apply bg-[rgba(0,255,136,0.1)] text-[var(--accent-green)] border border-[rgba(0,255,136,0.3)];
  }

  &.untrained {
    @apply bg-[rgba(255,136,102,0.1)] text-[#ff4466] border border-[rgba(255,136,102,0.3)];
  }
}

.metrics-cell {
  @apply flex flex-col gap-1;
}

.metric-item {
  @apply flex items-center gap-1;
}

.metric-label {
  @apply text-[10px] text-[var(--text-muted)];
}

.metric-value {
  @apply font-mono text-xs text-[var(--accent-cyan)];
}

.metric-value {
  @apply font-mono text-sm text-[var(--accent-cyan)];
}

.time-badge {
  @apply font-mono text-xs text-[var(--text-muted)];
}

.file-path {
  @apply font-mono text-xs text-[var(--text-secondary)] truncate max-w-full block;
}

.text-muted {
  @apply text-[var(--text-muted)];
}

.action-buttons {
  @apply flex gap-4 items-center;
}

:deep(.el-button--text) {
  @apply p-1 border-none bg-transparent text-[var(--accent-cyan)] text-sm;

  &:hover {
    @apply bg-transparent border-none text-[var(--accent-cyan)];
  }

  &:last-child:hover {
    @apply text-[#ff4466];
  }

  &:disabled {
    @apply text-[var(--text-muted)] opacity-50;
  }
}

/* 空状态 */
.empty-state {
  @apply py-20 px-5 flex flex-col items-center text-center;
}

.empty-icon {
  @apply w-20 h-20 flex items-center justify-center bg-[var(--bg-secondary)] rounded-xl mb-5 text-[var(--text-muted)] opacity-50;

  svg {
    @apply w-10 h-10;
  }
}

.empty-state p {
  @apply text-lg text-[var(--text-secondary)] mb-2;
}

.empty-state span {
  @apply text-sm text-[var(--text-muted)];
}

/* 对话框 */
.dialog-overlay {
  @apply fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-1000;
}

.dialog-panel {
  width: clamp(320px, 90vw, 450px);
  max-width: 95vw;
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
  @apply flex justify-between items-center px-6 py-5 border-b border-[var(--border-color)];

  h3 {
    @apply text-lg font-semibold;
  }
}

.close-btn {
  @apply w-8 h-8 flex items-center justify-center border-none bg-transparent text-[var(--text-muted)] cursor-pointer rounded transition-all;

  &:hover {
    @apply bg-[var(--bg-hover)] text-[var(--text-primary)];
  }

  svg {
    @apply w-4.5 h-4.5;
  }
}

.dialog-body {
  @apply p-6;
}

.form-group {
  @apply mb-5;

  label {
    @apply block text-sm text-[var(--text-secondary)] mb-2 uppercase tracking-wide;
  }

  input,
  select {
    @apply w-full px-4 py-3 bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-lg text-[var(--text-primary)] text-sm font-sans transition-all;
  }

  input:focus,
  select:focus {
    @apply outline-none border-[var(--accent-cyan)];
    box-shadow: 0 0 0 3px rgba(0, 240, 255, 0.1);
  }

  input::placeholder {
    @apply text-[var(--text-muted)];
  }
}

.select-wrapper {
  @apply relative;

  select {
    @apply appearance-none cursor-pointer;
  }

  &::after {
    content: '';
    @apply absolute right-3.5 top-1/2 -translate-y-1/2 border-l-1.5 border-r-1.5 border-t-1.5 border-l-transparent border-r-transparent border-t-[var(--text-muted)];
    pointer-events: none;
  }
}

.dialog-footer {
  @apply flex justify-end gap-3 px-6 py-5 border-t border-[var(--border-color)];
}

/* 上传区域 */
.upload-area {
  @apply text-center p-5;
}

.upload-btn {
  @apply inline-flex items-center gap-2.5 px-6 py-4 bg-[var(--bg-secondary)] border-2 border-dashed border-[var(--border-color)] rounded-xl text-[var(--text-secondary)] text-sm cursor-pointer transition-all;

  &:hover {
    @apply border-[var(--accent-cyan)] text-[var(--accent-cyan)];
  }

  svg {
    @apply w-6 h-6;
  }
}

.upload-hint {
  @apply mt-3 text-xs text-[var(--text-muted)];
}
</style>
