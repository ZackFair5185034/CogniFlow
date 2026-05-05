<template>
  <div class="atlas-list">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-info">
        <h2>图集管理</h2>
        <span class="subtitle">管理训练数据集</span>
      </div>
      <button class="ui-btn ui-btn-primary" @click="showCreateDialog = true">
        <SvgIcon name="plus" />
        创建图集
      </button>
    </div>

    <!-- 图集表格 -->
    <div class="ui-card" style="width: 100%; min-width: 0;">
      <div class="table-wrapper">
        <el-table :data="atlases" v-loading="loading" :row-class-name="tableRowClassName" style="width: 100%">
          <el-table-column prop="id" label="ID" width="100">
            <template #default="{ row }">
              <span class="id-badge">#{{ row.id }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="name" label="名称" min-width="280">
            <template #default="{ row }">
              <div class="name-cell">
                <SvgIcon name="folder" class="folder-icon" />
                <div class="name-desc">
                  <span class="atlas-name">{{ row.name }}</span>
                  <span class="atlas-desc" v-if="row.description">{{ row.description }}</span>
                </div>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="创建时间" width="160">
            <template #default="{ row }">
              <span class="time-badge">{{ formatDate(row.created_at) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="240" fixed="right">
            <template #default="{ row }">
              <div class="action-buttons">
                <el-button type="text" @click="handleRename(row)">编辑</el-button>
                <el-button type="text" @click="$router.push(`/atlas/${row.id}`)">查看</el-button>
                <el-button type="text" @click="handleDelete(row)">删除</el-button>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <!-- 创建对话框 -->
    <div class="dialog-overlay" v-if="showCreateDialog" @click.self="showCreateDialog = false">
      <div class="dialog-panel ui-card">
        <div class="dialog-header">
          <h3>创建新图集</h3>
          <button class="close-btn" @click="showCreateDialog = false">
            <SvgIcon name="close" />
          </button>
        </div>
        <div class="dialog-body">
          <div class="form-group">
            <label>图集名称</label>
            <input type="text" v-model="createForm.name" placeholder="输入图集名称" />
          </div>
          <div class="form-group">
            <label>描述</label>
            <textarea v-model="createForm.description" rows="3" placeholder="输入描述（可选）"></textarea>
          </div>
        </div>
        <div class="dialog-footer">
          <button class="ui-btn" @click="showCreateDialog = false">取消</button>
          <button class="ui-btn ui-btn-primary" @click="handleCreate" :disabled="creating">
            {{ creating ? '创建中...' : '创建' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 编辑对话框 -->
    <div class="dialog-overlay" v-if="showRenameDialog" @click.self="showRenameDialog = false">
      <div class="dialog-panel ui-card">
        <div class="dialog-header">
          <h3>编辑图集</h3>
          <button class="close-btn" @click="showRenameDialog = false">
            <SvgIcon name="close" />
          </button>
        </div>
        <div class="dialog-body">
          <div class="form-group">
            <label>图集名称</label>
            <input type="text" v-model="renameForm.name" placeholder="输入图集名称" />
          </div>
          <div class="form-group">
            <label>描述</label>
            <textarea v-model="renameForm.description" rows="3" placeholder="输入描述（可选）"></textarea>
          </div>
        </div>
        <div class="dialog-footer">
          <button class="ui-btn" @click="showRenameDialog = false">取消</button>
          <button class="ui-btn ui-btn-primary" @click="handleRenameSubmit" :disabled="renaming">
            {{ renaming ? '保存中...' : '保存' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { atlasApi } from '@/api'

const atlases = ref<any[]>([])
const loading = ref(false)
const showCreateDialog = ref(false)
const creating = ref(false)
const createForm = ref({ name: '', description: '' })

// 编辑状态
const showRenameDialog = ref(false)
const renaming = ref(false)
const renameTarget = ref<any>(null)
const renameForm = ref({ name: '', description: '' })

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

const loadAtlases = async () => {
  loading.value = true
  try {
    const res = await atlasApi.list()
    atlases.value = res.data
  } catch (error) {
    ElMessage.error('加载图集失败')
  } finally {
    loading.value = false
  }
}

const handleCreate = async () => {
  if (!createForm.value.name) {
    ElMessage.warning('请输入图集名称')
    return
  }
  creating.value = true
  try {
    await atlasApi.create(createForm.value)
    ElMessage.success('创建成功')
    showCreateDialog.value = false
    createForm.value = { name: '', description: '' }
    loadAtlases()
  } catch (error: any) {
    const msg = error.response?.data?.detail || '创建失败'
    ElMessage.error(msg)
  } finally {
    creating.value = false
  }
}

const handleRename = (row: any) => {
  renameTarget.value = row
  renameForm.value = { name: row.name, description: row.description || '' }
  showRenameDialog.value = true
}

const handleRenameSubmit = async () => {
  if (!renameForm.value.name) {
    ElMessage.warning('请输入图集名称')
    return
  }
  renaming.value = true
  try {
    await atlasApi.update(renameTarget.value.id, renameForm.value)
    ElMessage.success('编辑成功')
    showRenameDialog.value = false
    loadAtlases()
  } catch (error: any) {
    const msg = error.response?.data?.detail || '编辑失败'
    ElMessage.error(msg)
  } finally {
    renaming.value = false
  }
}

const handleDelete = async (row: any) => {
  try {
    await ElMessageBox.confirm(`确定删除图集 "${row.name}" 吗？此操作不可撤销。`, '删除确认', {
      type: 'warning',
      confirmButtonText: '确认',
      cancelButtonText: '取消',
    })
    await atlasApi.delete(row.id)
    ElMessage.success('删除成功')
    loadAtlases()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

onMounted(loadAtlases)
</script>

<style lang="scss" scoped>
.atlas-list {
  @apply flex flex-col gap-6;
  width: 100%;
  min-width: 0;
}

.page-header {
  @apply flex justify-between items-center;
  flex-wrap: wrap;
  gap: 16px;
  width: 100%;
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

  td.el-table__cell {
    @apply border-b border-[var(--border-color)];
  }
}

:deep(.el-table__cell) {
  padding: 12px 16px !important;
  white-space: nowrap;
}

:deep(.el-table th.el-table__cell) {
  @apply bg-[var(--bg-secondary)] font-medium uppercase text-xs tracking-wider;
}

:deep(.el-table__fixed-right .el-table__cell) {
  white-space: nowrap;
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
  display: flex !important;
  align-items: center;
  gap: 10px;
}

.name-desc {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
  overflow: hidden;
}

.atlas-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
  flex-shrink: 0;
}

.atlas-desc {
  font-size: 12px;
  color: var(--text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.folder-icon {
  @apply w-5 h-5 text-[var(--accent-yellow)] flex-shrink-0;
}

.time-badge {
  @apply font-mono text-xs text-[var(--text-muted)];
}

.action-buttons {
  @apply flex gap-4 items-center;
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
  textarea {
    @apply w-full px-4 py-3 bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-lg text-[var(--text-primary)] text-sm font-sans transition-all;
  }

  input:focus,
  textarea:focus {
    @apply outline-none border-[var(--accent-cyan)];
    box-shadow: 0 0 0 3px rgba(0, 240, 255, 0.1);
  }

  input::placeholder,
  textarea::placeholder {
    @apply text-[var(--text-muted)];
  }
}

.dialog-footer {
  @apply flex justify-end gap-3 px-6 py-5 border-t border-[var(--border-color)];
}
</style>
