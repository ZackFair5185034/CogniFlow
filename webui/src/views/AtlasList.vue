<template>
  <div class="atlas-list">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-info">
        <h2>图集管理</h2>
        <span class="subtitle">管理训练数据集</span>
      </div>
      <button class="vg-btn vg-btn-primary" @click="showCreateDialog = true">
        <PlusIcon />
        创建图集
      </button>
    </div>

    <!-- 图集表格 -->
    <div class="vg-card">
      <div class="table-container">
        <el-table :data="atlases" v-loading="loading" style="width: 100%" :row-class-name="tableRowClassName">
          <el-table-column prop="id" label="ID" width="100">
            <template #default="{ row }">
              <span class="id-badge">#{{ row.id }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="name" label="名称">
            <template #default="{ row }">
              <div class="name-cell">
                <FolderIcon class="folder-icon" />
                <span>{{ row.name }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="description" label="描述" />
          <el-table-column prop="created_at" label="创建时间" width="180">
            <template #default="{ row }">
              <span class="time-badge">{{ formatDate(row.created_at) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="200" fixed="right">
            <template #default="{ row }">
              <div class="action-buttons">
                <button class="action-btn view" @click="$router.push(`/atlas/${row.id}`)">
                  <EyeIcon />
                  查看
                </button>
                <button class="action-btn delete" @click="handleDelete(row)">
                  <TrashIcon />
                </button>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <!-- 创建对话框 -->
    <div class="dialog-overlay" v-if="showCreateDialog" @click.self="showCreateDialog = false">
      <div class="dialog-panel vg-card">
        <div class="dialog-header">
          <h3>创建新图集</h3>
          <button class="close-btn" @click="showCreateDialog = false">
            <CloseIcon />
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
          <button class="vg-btn" @click="showCreateDialog = false">取消</button>
          <button class="vg-btn vg-btn-primary" @click="handleCreate" :disabled="creating">
            {{ creating ? '创建中...' : '创建' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, h } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { atlasApi } from '@/api'

const atlases = ref<any[]>([])
const loading = ref(false)
const showCreateDialog = ref(false)
const creating = ref(false)
const createForm = ref({ name: '', description: '' })

// 图标组件
const PlusIcon = () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
  h('line', { x1: '12', y1: '5', x2: '12', y2: '19' }),
  h('line', { x1: '5', y1: '12', x2: '19', y2: '12' })
])

const FolderIcon = () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
  h('path', { d: 'M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z' })
])

const EyeIcon = () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
  h('path', { d: 'M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z' }),
  h('circle', { cx: '12', cy: '12', r: '3' })
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
  } catch (error) {
    ElMessage.error('创建失败')
  } finally {
    creating.value = false
  }
}

const handleDelete = async (row: any) => {
  try {
    await ElMessageBox.confirm(`确定删除图集 "${row.name}" 吗？此操作不可撤销。`, '删除确认', {
      type: 'warning',
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

<style scoped>
.atlas-list {
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

/* 表格容器 */
.table-container {
  padding: 0;
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

.folder-icon {
  width: 20px;
  height: 20px;
  color: var(--accent-yellow);
}

.time-badge {
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  color: var(--text-muted);
}

.action-buttons {
  display: flex;
  gap: 8px;
}

.action-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background: transparent;
  color: var(--text-secondary);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.action-btn svg {
  width: 14px;
  height: 14px;
}

.action-btn.view:hover {
  border-color: var(--accent-cyan);
  color: var(--accent-cyan);
  background: rgba(0, 240, 255, 0.1);
}

.action-btn.delete:hover {
  border-color: #ff4466;
  color: #ff4466;
  background: rgba(255, 68, 102, 0.1);
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
  border: none;
  background: transparent;
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
.form-group textarea {
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
.form-group textarea:focus {
  outline: none;
  border-color: var(--accent-cyan);
  box-shadow: 0 0 0 3px rgba(0, 240, 255, 0.1);
}

.form-group input::placeholder,
.form-group textarea::placeholder {
  color: var(--text-muted);
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 20px 24px;
  border-top: 1px solid var(--border-color);
}
</style>
