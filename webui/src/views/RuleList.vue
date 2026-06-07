<template>
  <div class="rule-list-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-info">
        <h2>规则引擎</h2>
        <span class="subtitle">可视化规则流程编排与执行</span>
      </div>
      <button
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

      <div
        v-else
        class="rules-grid"
      >
        <div
          v-for="graph in graphs"
          :key="graph.id"
          class="rule-card"
          :style="graph.thumbnail ? { backgroundImage: `url(${graph.thumbnail})` } : {}"
          @click="goToDesign(graph.id)"
        >
          <!-- 无快照时的渐变背景 -->
          <div
            v-if="!graph.thumbnail"
            class="card-placeholder-bg"
          />

          <!-- 快照遮罩 -->
          <div class="card-snapshot-overlay" />

          <!-- 卡片内容 -->
          <div class="card-content">
            <div class="card-header">
              <div class="card-title">
                <h3>{{ graph.name }}</h3>
                <span
                  v-if="graph.version"
                  class="card-version"
                >v{{ graph.version }}</span>
              </div>
              <div
                class="card-actions"
                @click.stop
              >
                <!-- 激活/停用开关 -->
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

            <!-- 规则状态标签 -->
            <div class="rule-status-tags">
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

            <p class="card-desc">
              {{ graph.description || '暂无描述' }}
            </p>

            <div class="card-footer">
              <div class="card-meta">
                <span
                  v-if="graph.last_executed_at"
                  class="meta-item"
                >
                  <SvgIcon name="clock" />
                  {{ formatDate(graph.last_executed_at) }}
                </span>
                <span class="meta-item">
                  <SvgIcon name="clock" />
                  {{ formatDate(graph.updated_at || '') }}
                </span>
              </div>
              <span
                v-if="graph.thumbnail"
                class="has-snapshot"
              >
                <SvgIcon name="image" />
                快照
              </span>
            </div>
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
    month: 'short',
    day: 'numeric',
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
  @apply text-2xl font-semibold;
  background: linear-gradient(90deg, var(--text-primary), var(--accent-blue));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
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
    width: 100px;
    height: 100px;
    margin-bottom: 24px;
    opacity: 0.2;

    svg {
      width: 100%;
      height: 100%;
      stroke: var(--accent-blue);
    }
  }

  h3 {
    font-size: 18px;
    margin-bottom: 8px;
  }

  p {
    font-size: 14px;
    margin-bottom: 24px;
  }
}

.rules-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
  padding: 4px 2px 4px 2px;
}

.rule-card {
  position: relative;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.25s ease;
  min-height: 160px;

  &:hover {
    border-color: rgba(0, 240, 255, 0.35);
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(0, 240, 255, 0.12);
  }
}

.card-placeholder-bg {
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, rgba(0, 240, 255, 0.04), rgba(0, 170, 136, 0.02));
  z-index: 0;
}

.card-snapshot-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    to bottom,
    rgba(0, 0, 0, 0.05) 0%,
    rgba(0, 0, 0, 0.35) 50%,
    rgba(0, 0, 0, 0.75) 100%
  );
  z-index: 1;
}

.card-content {
  position: relative;
  z-index: 2;
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 10px;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  flex: 1;

  h3 {
    font-size: 15px;
    font-weight: 600;
    color: #fff;
    line-height: 1.3;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .card-version {
    font-size: 10px;
    padding: 2px 8px;
    background: rgba(0, 240, 255, 0.2);
    color: var(--accent-blue);
    border-radius: 4px;
    font-family: 'JetBrains Mono', monospace;
    flex-shrink: 0;
  }
}

.card-actions {
  display: flex;
  gap: 4px;

  .action-btn {
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(255, 255, 255, 0.1);
    backdrop-filter: blur(8px);
    border: 1px solid rgba(255, 255, 255, 0.15);
    border-radius: 6px;
    color: #fff;
    cursor: pointer;
    transition: all 0.2s;

    svg {
      width: 16px;
      height: 16px;
    }

    &:hover {
      background: rgba(255, 255, 255, 0.2);
    }

    &.danger:hover {
      background: rgba(255, 68, 102, 0.3);
      border-color: rgba(255, 68, 102, 0.5);
    }
  }
}

.card-desc {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.7);
  line-height: 1.5;
  margin-bottom: 14px;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.rule-status-tags {
  display: flex;
  gap: 8px;
  margin-bottom: 10px;
  flex-wrap: wrap;

  .status-tag {
    font-size: 11px;
    padding: 3px 8px;
    border-radius: 4px;
    font-weight: 500;

    &.active {
      background: rgba(0, 255, 136, 0.15);
      color: var(--color-success);
      border: 1px solid rgba(0, 255, 136, 0.3);
    }

    &.inactive {
      background: rgba(255, 255, 255, 0.05);
      color: rgba(255, 255, 255, 0.4);
      border: 1px solid rgba(255, 255, 255, 0.1);
    }
  }

  .cron-tag {
    font-size: 11px;
    padding: 3px 8px;
    border-radius: 4px;
    background: rgba(255, 193, 7, 0.1);
    color: #ffc107;
    border: 1px solid rgba(255, 193, 7, 0.2);
    display: flex;
    align-items: center;
    gap: 4px;

    svg { width: 12px; height: 12px; }
  }
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 10px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.card-meta {
  display: flex;
  gap: 12px;

  .meta-item {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
    color: rgba(255, 255, 255, 0.5);

    svg {
      width: 14px;
      height: 14px;
    }
  }
}

.has-snapshot {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: rgba(0, 240, 255, 0.7);

  svg {
    width: 12px;
    height: 12px;
  }
}

// 对话框
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
      box-shadow: 0 4px 20px rgba(0, 240, 255, 0.3);
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
    color: #000;
  }

  &.error {
    background: linear-gradient(135deg, var(--color-danger), var(--color-danger));
    color: #fff;
  }

  &.info {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    color: var(--text-primary);
  }
}

</style>
