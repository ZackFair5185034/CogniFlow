<template>
  <div class="rule-list-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-info">
        <h2 class="cf-gradient-text text-2xl font-semibold">规则引擎</h2>
        <span class="subtitle">可视化规则流程编排与执行</span>
      </div>
      <!-- 数据为空时,这里也保留一个新建按钮,方便操作 -->
      <button
        v-if="!loading && graphs.length > 0"
        class="ui-btn ui-btn-primary"
        @click="showCreateDialog = true"
      >
        <SvgIcon name="plus" />
        新建规则
      </button>
    </div>

    <!-- 规则列表 -->
    <div class="rules-container">
      <LoadingSpinner
        v-if="loading"
        overlay
        text="加载中..."
      />

      <!-- 空状态:中间一个新建按钮 -->
      <div
        v-else-if="graphs.length === 0"
        class="empty-state"
      >
        <div class="empty-icon">
          <SvgIcon name="flow" />
        </div>
        <h3>暂无规则</h3>
        <p>创建您的第一条规则，开始自动化流程设计</p>
        <button
          class="ui-btn ui-btn-primary"
          @click="showCreateDialog = true"
        >
          <SvgIcon name="plus" />
          新建规则
        </button>
      </div>

      <!-- 简洁行式列表 -->
      <div
        v-else
        class="rules-table"
      >
        <!-- 表头 -->
        <div class="rules-table-header">
          <div class="col-name">名称</div>
          <div class="col-desc">描述</div>
          <div class="col-status">状态</div>
          <div class="col-updated">更新时间</div>
          <div class="col-actions">操作</div>
        </div>

        <!-- 行 -->
        <div
          v-for="graph in graphs"
          :key="graph.id"
          class="rules-table-row"
          @click="goToDesign(graph.id)"
        >
          <div class="col-name">
            <span class="rule-name">{{ graph.name }}</span>
            <span
              v-if="graph.version"
              class="rule-version"
            >v{{ graph.version }}</span>
          </div>
          <div class="col-desc">
            {{ graph.description || '—' }}
          </div>
          <div class="col-status">
            <span
              class="status-tag"
              :class="graph.is_active ? 'active' : 'inactive'"
            >
              {{ graph.is_active ? '已激活' : '未激活' }}
            </span>
            <span
              v-if="graph.cron_expression"
              class="cron-tag"
            >
              <SvgIcon name="clock" />
              {{ graph.cron_expression }}
            </span>
          </div>
          <div class="col-updated">
            {{ formatDate(graph.updated_at || '') }}
          </div>
          <div
            class="col-actions"
            @click.stop
          >
            <button
              class="action-btn"
              :class="{ active: graph.is_active }"
              :title="graph.is_active ? '停用规则' : '激活规则'"
              @click="toggleActive(graph)"
            >
              <SvgIcon :name="graph.is_active ? 'pause' : 'play'" />
            </button>
            <button
              class="action-btn"
              title="编辑规则"
              @click="goToDesign(graph.id)"
            >
              <SvgIcon name="edit" />
            </button>
            <button
              class="action-btn danger"
              title="删除规则"
              @click="handleDelete(graph)"
            >
              <SvgIcon name="trash" />
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 创建规则对话框 -->
    <div
      v-if="showCreateDialog"
      class="dialog-overlay"
      @click.self="showCreateDialog = false"
    >
      <div class="dialog">
        <div class="dialog-header">
          <h3>新建规则</h3>
          <button
            class="close-btn"
            @click="showCreateDialog = false"
          >
            <SvgIcon name="close" />
          </button>
        </div>
        <div class="dialog-body">
          <div class="form-group">
            <label>规则名称</label>
            <el-input
              v-model="createForm.name"
              placeholder="例如：目标检测自动响应"
              @keyup.enter="handleCreate"
            />
          </div>
          <div class="form-group">
            <label>描述（可选）</label>
            <el-input
              v-model="createForm.description"
              type="textarea"
              :rows="3"
              placeholder="描述规则的用途..."
            />
          </div>
          <div class="form-group">
            <label>版本（可选）</label>
            <el-input
              v-model="createForm.version"
              placeholder="例如：1.0.0"
            />
          </div>
        </div>
        <div class="dialog-footer">
          <button
            class="btn secondary"
            @click="showCreateDialog = false"
          >
            取消
          </button>
          <button
            class="btn primary"
            :disabled="!createForm.name.trim() || creating"
            @click="handleCreate"
          >
            {{ creating ? '创建中...' : '创建' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ruleEngineApi } from '@/api'

/** 规则图列表项 */
interface GraphItem {
  id: number
  name: string
  description?: string
  version?: string
  is_active: boolean
  thumbnail?: string
  cron_expression?: string
  last_executed_at?: string
  created_at?: string
  updated_at?: string
}

/** Axios 错误响应 */
interface ApiError {
  response?: {
    data?: {
      detail?: string
    }
  }
}

const router = useRouter()

const graphs = ref<GraphItem[]>([])
const loading = ref(false)
const showCreateDialog = ref(false)
const creating = ref(false)
const createForm = reactive({ name: '', description: '', version: '' })

onMounted(() => {
  loadGraphs()
})

async function loadGraphs() {
  loading.value = true
  try {
    const res = await ruleEngineApi.listGraphs()
    graphs.value = res.data
  } catch (err) {
    console.error('加载规则列表失败:', err)
    ElMessage.error('加载规则列表失败')
  } finally {
    loading.value = false
  }
}

async function handleCreate() {
  if (!createForm.name.trim()) return

  creating.value = true
  try {
    const res = await ruleEngineApi.createGraph({
      name: createForm.name,
      description: createForm.description,
      version: createForm.version
    })
    showCreateDialog.value = false
    ElMessage.success('规则创建成功')
    router.push(`/rule-engine/design/${res.data.id}`)
  } catch (err) {
    console.error('创建规则失败:', err)
    ElMessage.error('创建规则失败')
  } finally {
    creating.value = false
  }
}

function goToDesign(id: number) {
  router.push(`/rule-engine/design/${id}`)
}

async function toggleActive(graph: GraphItem) {
  try {
    if (graph.is_active) {
      await ruleEngineApi.deactivateGraph(graph.id)
      graph.is_active = false
      ElMessage.info('规则已停用')
    } else {
      await ruleEngineApi.activateGraph(graph.id)
      graph.is_active = true
      ElMessage.success('规则已激活')
    }
  } catch (err: unknown) {
    const error = err as ApiError
    ElMessage.error(error?.response?.data?.detail || '操作失败')
  }
}

async function handleDelete(graph: GraphItem) {
  try {
    await ElMessageBox.confirm(
      `确定要删除规则"${graph.name}"吗？此操作不可恢复。`,
      '删除确认',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' }
    )
    await ruleEngineApi.deleteGraph(graph.id)
    ElMessage.success('规则已删除')
    loadGraphs()
  } catch (err: unknown) {
    if (err !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

function formatDate(dateStr: string) {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

</script>

<style scoped lang="scss">
.rule-list-page {
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.page-header {
  @apply flex justify-between items-center gap-4;
}

.header-info {
  @apply flex items-baseline;
}

.header-info h2 {
  // cf-gradient-text + text-2xl font-semibold 已上移到 class
}

.header-info .subtitle {
  @apply text-sm text-[var(--text-muted)] ml-3;
}

.rules-container {
  flex: 1;
  overflow-y: auto;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 400px;
  color: var(--text-secondary);

  .empty-icon {
    width: 80px;
    height: 80px;
    margin-bottom: 20px;
    opacity: 0.25;

    svg {
      width: 100%;
      height: 100%;
      stroke: var(--accent-blue);
    }
  }

  h3 {
    font-size: 16px;
    margin-bottom: 6px;
  }

  p {
    font-size: 13px;
    margin-bottom: 20px;
  }
}

/* ===== 行式列表 ===== */
.rules-table {
  display: flex;
  flex-direction: column;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  overflow: hidden;
}

.rules-table-header,
.rules-table-row {
  display: grid;
  grid-template-columns: 2fr 3fr 1.5fr 1.2fr 140px;
  align-items: center;
  padding: 12px 16px;
  gap: 12px;
}

.rules-table-header {
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
  font-size: 12px;
  font-weight: 500;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.rules-table-row {
  border-bottom: 1px solid var(--border-color);
  cursor: pointer;
  transition: background 0.15s;
  font-size: 13px;

  &:last-child {
    border-bottom: none;
  }

  &:hover {
    background: var(--bg-hover);
  }
}

.col-name {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;

  .rule-name {
    font-weight: 500;
    color: var(--text-primary);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .rule-version {
    font-size: 10px;
    padding: 1px 6px;
    background: rgba(34, 211, 238, 0.15);
    color: var(--accent-blue);
    border-radius: 3px;
    font-family: 'JetBrains Mono', monospace;
    flex-shrink: 0;
  }
}

.col-desc {
  color: var(--text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.col-status {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.status-tag {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 500;
  white-space: nowrap;

  &.active {
    background: rgba(52, 217, 123, 0.15);
    color: var(--color-success);
    border: 1px solid rgba(52, 217, 123, 0.3);
  }

  &.inactive {
    background: rgba(255, 255, 255, 0.05);
    color: var(--text-muted);
    border: 1px solid var(--border-color);
  }
}

.cron-tag {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  background: rgba(255, 193, 7, 0.1);
  color: #ffc107;
  border: 1px solid rgba(255, 193, 7, 0.2);
  display: flex;
  align-items: center;
  gap: 4px;
  white-space: nowrap;

  svg { width: 11px; height: 11px; }
}

.col-updated {
  color: var(--text-muted);
  font-size: 12px;
  font-family: 'JetBrains Mono', monospace;
}

.col-actions {
  display: flex;
  gap: 4px;
  justify-content: flex-end;

  .action-btn {
    width: 28px;
    height: 28px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: transparent;
    border: 1px solid var(--border-color);
    border-radius: 5px;
    color: var(--text-secondary);
    cursor: pointer;
    transition: all 0.15s;

    svg {
      width: 14px;
      height: 14px;
    }

    &:hover {
      background: var(--bg-hover);
      color: var(--text-primary);
      border-color: var(--accent-blue);
    }

    &.active {
      color: var(--color-success);
      border-color: rgba(52, 217, 123, 0.4);
    }

    &.danger:hover {
      background: rgba(255, 68, 102, 0.1);
      border-color: rgba(255, 68, 102, 0.5);
      color: var(--color-danger);
    }
  }
}

/* ===== 对话框 ===== */
.dialog-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.dialog {
  width: 480px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  overflow: hidden;
}

.dialog-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-color);

  h3 {
    font-size: 16px;
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
    border-radius: 6px;
    color: var(--text-muted);
    cursor: pointer;
    transition: all 0.2s;

    svg { width: 16px; height: 16px; }

    &:hover {
      background: var(--bg-hover);
      color: var(--text-primary);
    }
  }
}

.dialog-body {
  padding: 24px;
}

.form-group {
  margin-bottom: 20px;

  &:last-child { margin-bottom: 0; }

  label {
    display: block;
    font-size: 13px;
    font-weight: 500;
    color: var(--text-secondary);
    margin-bottom: 8px;
  }

  input,
  textarea {
    width: 100%;
    background: var(--bg-secondary);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    padding: 12px;
    color: var(--text-primary);
    font-size: 14px;
    transition: all 0.2s;
    box-sizing: border-box;

    &:focus {
      outline: none;
      border-color: var(--accent-blue);
    }

    &::placeholder {
      color: var(--text-muted);
    }
  }

  textarea {
    resize: vertical;
    min-height: 80px;
  }
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 24px;
  border-top: 1px solid var(--border-color);
}

.btn {
  padding: 10px 20px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  &.secondary {
    background: var(--bg-secondary);
    border: 1px solid var(--border-color);
    color: var(--text-secondary);

    &:hover:not(:disabled) {
      background: var(--bg-hover);
    }
  }

  &.primary {
    background: linear-gradient(135deg, var(--accent-blue), var(--accent-blue));
    border: none;
    color: #000;

    &:hover:not(:disabled) {
      box-shadow: 0 4px 20px rgba(34, 211, 238, 0.3);
    }
  }
}

.toast {
  position: fixed;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  padding: 12px 24px;
  border-radius: 8px;
  font-size: 14px;
  z-index: 2000;

  &.success {
    background: linear-gradient(135deg, var(--color-success), var(--color-success));
    color: var(--on-vibrant);
  }

  &.error {
    background: linear-gradient(135deg, var(--color-danger), var(--color-danger));
    color: var(--on-vibrant);
  }

  &.info {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    color: var(--text-primary);
  }
}
</style>
