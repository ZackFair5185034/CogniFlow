<template>
  <div class="model-list">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-info">
        <h2>模型管理</h2>
        <span class="subtitle">管理训练模型</span>
      </div>
      <button
        class="ui-btn ui-btn-primary"
        @click="showCreateDialog = true"
      >
        <SvgIcon name="plus" />
        注册模型
      </button>
    </div>

    <!-- 模型列表 -->
    <div
      class="ui-card"
      style="width: 100%; min-width: 0;"
    >
      <div class="table-wrapper">
        <el-table
          v-loading="loading"
          :data="models"
          :row-class-name="tableRowClassName"
          style="width: 100%"
        >
          <el-table-column
            prop="id"
            label="ID"
            width="100"
          >
            <template #default="{ row }">
              <span class="id-badge">#{{ row.id }}</span>
            </template>
          </el-table-column>
          <el-table-column
            prop="name"
            label="名称"
            min-width="200"
          >
            <template #default="{ row }">
              <div class="name-cell">
                <SvgIcon
                  name="box"
                  class="model-icon"
                />
                <span>{{ row.name }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column
            prop="version"
            label="版本"
            width="100"
          >
            <template #default="{ row }">
              <span
                v-if="row.version"
                class="version-badge"
              >{{ row.version }}</span>
              <span
                v-else
                class="text-muted"
              >-</span>
            </template>
          </el-table-column>
          <el-table-column
            prop="pretrained_model"
            label="预训练"
            width="120"
          >
            <template #default="{ row }">
              <span
                v-if="!row.pretrained_model"
                class="text-muted"
              >-</span>
              <span v-else>{{ row.pretrained_model.replace('.pt', '') }}</span>
            </template>
          </el-table-column>
          <el-table-column
            label="状态"
            width="100"
          >
            <template #default="{ row }">
              <span
                class="status-badge"
                :class="row.file_path ? 'trained' : 'untrained'"
              >
                {{ row.file_path ? '已训练' : '未训练' }}
              </span>
            </template>
          </el-table-column>
          <el-table-column
            label="格式"
            width="150"
          >
            <template #default="{ row }">
              <div
                v-if="row.files?.length"
                class="format-badges"
              >
                <span
                  v-for="file in row.files.slice(0, 3)"
                  :key="file.id"
                  class="format-badge"
                  :class="{ 'is-default': file.is_default }"
                  :title="`${file.format.toUpperCase()}${file.is_default ? ' (默认)' : ''}`"
                >
                  {{ file.format.toUpperCase() }}
                </span>
                <span
                  v-if="row.files.length > 3"
                  class="format-badge more"
                >
                  +{{ row.files.length - 3 }}
                </span>
              </div>
              <span
                v-else
                class="text-muted"
              >-</span>
            </template>
          </el-table-column>
          <el-table-column
            label="性能指标"
            width="200"
          >
            <template #default="{ row }">
              <div
                v-if="row.metrics?.mAP50"
                class="metrics-cell"
              >
                <span class="metric-item">
                  <span class="metric-label">mAP50:</span>
                  <span class="metric-value">{{ (row.metrics.mAP50 * 100).toFixed(1) }}%</span>
                </span>
                <span
                  v-if="row.metrics?.mAP50_95"
                  class="metric-item"
                >
                  <span class="metric-label">mAP:</span>
                  <span class="metric-value">{{ (row.metrics.mAP50_95 * 100).toFixed(1) }}%</span>
                </span>
              </div>
              <span
                v-else
                class="text-muted"
              >-</span>
            </template>
          </el-table-column>
          <el-table-column
            label="模型文件"
            min-width="240"
          >
            <template #default="{ row }">
              <span
                v-if="row.file_path"
                class="file-path"
                :title="row.file_path"
              >
                {{ shortenPath(row.file_path) }}
              </span>
              <span
                v-else
                class="text-muted"
              >-</span>
            </template>
          </el-table-column>
          <el-table-column
            label="训练时间"
            width="140"
          >
            <template #default="{ row }">
              <span
                v-if="row.metrics?.trained_at"
                class="time-badge"
              >
                {{ formatTrainedAt(row.metrics.trained_at) }}
              </span>
              <span
                v-else
                class="text-muted"
              >-</span>
            </template>
          </el-table-column>
          <el-table-column
            prop="created_at"
            label="创建时间"
            width="140"
          >
            <template #default="{ row }">
              <span class="time-badge">{{ formatDate(row.created_at) }}</span>
            </template>
          </el-table-column>
          <el-table-column
            label="操作"
            width="200"
            fixed="right"
            align="center"
            header-align="center"
          >
            <template #default="{ row }">
              <div class="action-cell">
                <!-- 直接显示第1个操作 -->
                <el-button
                  class="action-text"
                  @click.stop="handleAction('rename', row)"
                >
                  编辑
                </el-button>
                <!-- 收纳剩余操作 -->
                <el-dropdown
                  v-if="getVisibleActions(row).length > 0"
                  trigger="click"
                  @command="(cmd: string) => handleAction(cmd, row)"
                >
                  <el-button class="action-text">
                    更多
                  </el-button>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item
                        v-for="action in getVisibleActions(row)"
                        :key="action.command"
                        :command="action.command"
                        :divided="action.command === 'delete'"
                        :disabled="action.disabled"
                        :class="{ 'delete-item': action.command === 'delete' }"
                      >
                        {{ action.label }}
                      </el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
              </div>
            </template>
          </el-table-column>
        </el-table>

        <div
          v-if="!loading && models.length === 0"
          class="empty-state"
        >
          <div class="empty-icon">
            <SvgIcon name="box" />
          </div>
          <p>暂无模型</p>
          <span>注册第一个模型开始训练</span>
        </div>
      </div>
    </div>

    <!-- 创建对话框 -->
    <div
      v-if="showCreateDialog"
      class="dialog-overlay"
      @click.self="showCreateDialog = false"
    >
      <div class="dialog-panel ui-card">
        <div class="dialog-header">
          <h3>注册模型</h3>
          <button
            class="close-btn"
            @click="showCreateDialog = false"
          >
            <SvgIcon name="close" />
          </button>
        </div>
        <div class="dialog-body">
          <div class="form-group">
            <label>模型名称</label>
            <el-input
              v-model="createForm.name"
              type="text"
              placeholder="输入模型名称"
            />
          </div>
          <div class="form-group">
            <label>版本</label>
            <el-input
              v-model="createForm.version"
              type="text"
              placeholder="如 v1, v2"
            />
          </div>
          <div class="form-group">
            <label>训练图集（可选）</label>
            <el-select
              v-model="createForm.atlas_id"
              placeholder="不关联图集"
              clearable
              class="full-width"
            >
              <el-option
                :value="null"
                label="不关联图集"
              />
              <el-option
                v-for="atlas in atlases"
                :key="atlas.id"
                :value="atlas.id"
                :label="atlas.name"
              />
            </el-select>
          </div>
          <div class="form-group">
            <label>预训练模型</label>
            <el-select
              v-model="createForm.pretrained_model"
              class="full-width"
            >
              <el-option value="yolov8n.pt">
                YOLOv8n (最小最快)
              </el-option>
              <el-option value="yolov8s.pt">
                YOLOv8s (小，推荐)
              </el-option>
              <el-option value="yolov8m.pt">
                YOLOv8m (中)
              </el-option>
              <el-option value="yolov8l.pt">
                YOLOv8l (大)
              </el-option>
              <el-option value="yolov8x.pt">
                YOLOv8x (最大最准)
              </el-option>
            </el-select>
          </div>
        </div>
        <div class="dialog-footer">
          <button
            class="ui-btn"
            @click="showCreateDialog = false"
          >
            取消
          </button>
          <button
            class="ui-btn ui-btn-primary"
            :disabled="creating"
            @click="handleCreate"
          >
            {{ creating ? '注册中...' : '注册' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 上传对话框 -->
    <div
      v-if="showUploadDialog"
      class="dialog-overlay"
      @click.self="showUploadDialog = false"
    >
      <div class="dialog-panel ui-card">
        <div class="dialog-header">
          <h3>上传模型文件</h3>
          <button
            class="close-btn"
            @click="showUploadDialog = false"
          >
            <SvgIcon name="close" />
          </button>
        </div>
        <div class="dialog-body">
          <div class="upload-area">
            <input
              ref="fileInputRef"
              type="file"
              accept=".pt,.pth,.onnx"
              style="display: none"
              @change="handleFileChange"
            >
            <button
              class="upload-btn"
              @click="fileInputRef?.click()"
            >
              <SvgIcon name="upload" />
              <span>{{ uploadFile ? uploadFile.name : '选择模型文件' }}</span>
            </button>
            <p class="upload-hint">
              支持 .pt, .pth, .onnx 格式
            </p>
          </div>
        </div>
        <div class="dialog-footer">
          <button
            class="ui-btn"
            @click="showUploadDialog = false"
          >
            取消
          </button>
          <button
            class="ui-btn ui-btn-primary"
            :disabled="!uploadFile || uploading"
            @click="handleUploadSubmit"
          >
            {{ uploading ? '上传中...' : '上传' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 编辑对话框 -->
    <div
      v-if="showRenameDialog"
      class="dialog-overlay"
      @click.self="showRenameDialog = false"
    >
      <div class="dialog-panel ui-card">
        <div class="dialog-header">
          <h3>编辑模型</h3>
          <button
            class="close-btn"
            @click="showRenameDialog = false"
          >
            <SvgIcon name="close" />
          </button>
        </div>
        <div class="dialog-body">
          <div class="form-group">
            <label>模型名称</label>
            <el-input
              v-model="renameForm.name"
              type="text"
              placeholder="输入模型名称"
            />
          </div>
          <div class="form-group">
            <label>版本</label>
            <el-input
              v-model="renameForm.version"
              type="text"
              placeholder="如 v1, v2"
            />
          </div>
        </div>
        <div class="dialog-footer">
          <button
            class="ui-btn"
            @click="showRenameDialog = false"
          >
            取消
          </button>
          <button
            class="ui-btn ui-btn-primary"
            :disabled="renaming"
            @click="handleRenameSubmit"
          >
            {{ renaming ? '保存中...' : '保存' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 导出对话框 -->
    <div
      v-if="showExportDialog"
      class="dialog-overlay"
      @click.self="handleExportClose"
    >
      <div class="dialog-panel ui-card">
        <div class="dialog-header">
          <h3>导出模型</h3>
          <button
            class="close-btn"
            @click="handleExportClose"
          >
            <SvgIcon name="close" />
          </button>
        </div>
        <div
          v-if="exportTargetModel"
          class="dialog-body"
        >
          <p class="export-model-name">
            导出模型: {{ exportTargetModel.name }}
          </p>

          <!-- 导出进度（导出中显示） -->
          <div
            v-if="exportStatus !== 'idle'"
            class="export-progress"
          >
            <div class="progress-info">
              <span
                class="progress-status"
                :class="exportStatus"
              >
                {{ exportStatusText }}
              </span>
              <span class="progress-percent">{{ exportProgress }}%</span>
            </div>
            <div class="progress-bar">
              <div
                class="progress-fill"
                :class="exportStatus"
                :style="{ width: exportProgress + '%' }"
              />
            </div>
            <p class="progress-message">
              {{ exportMessage }}
            </p>
          </div>

          <!-- 导出配置（未开始或完成后显示） -->
          <template v-else>
            <!-- 显示已有格式 -->
            <div
              v-if="exportTargetModel.files?.length"
              class="form-group"
            >
              <label>已有格式</label>
              <div class="existing-formats">
                <span
                  v-for="f in exportTargetModel.files"
                  :key="f.id"
                  class="format-tag"
                  :class="{ 'is-default': f.is_default }"
                >
                  {{ f.format.toUpperCase() }}
                  <span
                    v-if="f.is_default"
                    class="default-tag"
                  >默认</span>
                </span>
              </div>
            </div>

            <div class="form-group">
              <label>目标格式</label>
              <el-select
                v-model="exportForm.target_format"
                class="full-width"
              >
                <el-option value="onnx">
                  ONNX (跨平台，CPU/GPU)
                </el-option>
                <el-option value="openvino">
                  OpenVINO (Intel 硬件加速)
                </el-option>
                <el-option value="tensorrt">
                  TensorRT (NVIDIA GPU 高性能)
                </el-option>
              </el-select>
            </div>
            <div class="form-group">
              <label>导出名称</label>
              <el-input
                v-model="exportForm.name"
                type="text"
                placeholder="输入导出文件名称（可选）"
              />
            </div>
            <div class="form-group">
              <el-checkbox
                v-model="exportForm.half"
              >
                导出为 FP16 半精度（减小模型体积，加速推理）
              </el-checkbox>
            </div>
          </template>
        </div>
        <div class="dialog-footer">
          <button
            class="ui-btn"
            @click="handleExportClose"
          >
            {{ exportStatus !== 'idle' && exportStatus !== 'completed' ? '取消' : '关闭' }}
          </button>
          <button
            v-if="exportStatus === 'idle'"
            class="ui-btn ui-btn-primary"
            :disabled="exporting"
            @click="handleExportSubmit"
          >
            {{ exporting ? '准备中...' : '开始导出' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import {computed, onMounted, ref} from 'vue'
import {ElMessage, ElMessageBox} from 'element-plus'
import {atlasApi, modelApi} from '@/api'
import SvgIcon from '@/components/SvgIcon.vue'
import type {ModelResponse, AtlasResponse} from '@/types/api'

const models = ref<ModelResponse[]>([])
const atlases = ref<AtlasResponse[]>([])
const loading = ref(false)
const showCreateDialog = ref(false)
const creating = ref(false)
const showUploadDialog = ref(false)
const uploading = ref(false)
const fileInputRef = ref<HTMLInputElement | null>(null)
const selectedModel = ref<ModelResponse | null>(null)
const uploadFile = ref<File | null>(null)

// 导出相关
const showExportDialog = ref(false)
const exporting = ref(false)
const exportTargetModel = ref<ModelResponse | null>(null)
const exportForm = ref({target_format: 'onnx', half: false, name: ''})
const exportStatus = ref<'idle' | 'starting' | 'loading' | 'saving' | 'completed' | 'error'>('idle')
const exportProgress = ref(0)
const exportMessage = ref('')
const exportId = ref<string | null>(null)
let exportWs: WebSocket | null = null

const exportStatusText = computed(() => {
  const map: Record<string, string> = {
    idle: '',
    starting: '准备中',
    loading: '加载模型',
    saving: '保存文件',
    completed: '导出完成',
    error: '导出失败',
  }
  return map[exportStatus.value] || ''
})

const createForm = ref({name: '', version: '', pretrained_model: 'yolov8s.pt', atlas_id: null as number | null})

// 编辑状态
const showRenameDialog = ref(false)
const renaming = ref(false)
const renameTarget = ref<ModelResponse | null>(null)
const renameForm = ref({name: '', version: ''})

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
  // 后端格式: %Y%m%d_%H%M%S → 20250315_143022
  const formatted = dateStr.replace(
      /^(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})$/,
      '$1-$2-$3 $4:$5:$6'
  )
  const date = new Date(formatted)
  if (isNaN(date.getTime())) return '-'
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

const tableRowClassName = ({rowIndex}: { rowIndex: number }) => {
  return rowIndex % 2 === 0 ? 'even-row' : 'odd-row'
}

// 计算可见操作按钮（编辑始终显示，其余放入折叠菜单）
const getVisibleActions = (row: ModelResponse) => {
  const actions = []
  if (row.file_path && row.format === 'yolo_pt') {
    actions.push({command: 'export', label: '导出', disabled: false})
  }
  if (row.file_path) {
    actions.push({command: 'download', label: '下载', disabled: false})
  }
  if (!row.file_path) {
    actions.push({command: 'upload', label: '上传', disabled: false})
  }
  if (row.is_best || !row.file_path) {
    actions.push({command: 'best', label: '设为最佳', disabled: true})
  } else {
    actions.push({command: 'best', label: '设为最佳', disabled: false})
  }
  actions.push({command: 'delete', label: '删除', disabled: false})
  return actions
}

const loadModels = async () => {
  loading.value = true
  try {
    const res = await modelApi.list()
    models.value = res.data
  } catch {
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
    createForm.value = {name: '', version: '', pretrained_model: 'yolov8s.pt', atlas_id: null}
    loadModels()
  } catch (error: unknown) {
    const msg = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '注册失败'
    ElMessage.error(msg)
  } finally {
    creating.value = false
  }
}

const handleUpload = (row: ModelResponse) => {
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
  } catch {
    ElMessage.error('上传失败')
  } finally {
    uploading.value = false
  }
}

const handleSetBest = async (row: ModelResponse) => {
  try {
    await modelApi.setBest(row.id)
    ElMessage.success('已设为最佳模型')
    loadModels()
  } catch {
    ElMessage.error('操作失败')
  }
}

const handleDelete = async (row: ModelResponse) => {
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

// 操作处理函数
const handleAction = (cmd: string, row: ModelResponse) => {
  switch (cmd) {
    case 'rename':
      handleRename(row)
      break
    case 'export':
      handleExport(row)
      break
    case 'download':
      handleDownload(row)
      break
    case 'upload':
      handleUpload(row)
      break
    case 'best':
      handleSetBest(row)
      break
    case 'delete':
      handleDelete(row)
      break
  }
}

const handleRename = (row: ModelResponse) => {
  renameTarget.value = row
  renameForm.value = {name: row.name, version: row.version || ''}
  showRenameDialog.value = true
}

const handleRenameSubmit = async () => {
  if (!renameForm.value.name) {
    ElMessage.warning('请输入模型名称')
    return
  }
  renaming.value = true
  try {
    await modelApi.update(renameTarget.value.id, {
      name: renameForm.value.name,
      version: renameForm.value.version || undefined,
    })
    ElMessage.success('编辑成功')
    showRenameDialog.value = false
    loadModels()
  } catch (error: unknown) {
    const msg = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '编辑失败'
    ElMessage.error(msg)
  } finally {
    renaming.value = false
  }
}

const handleDownload = (row: ModelResponse) => {
  if (!row.file_path) {
    ElMessage.warning('模型文件不存在')
    return
  }
  const url = modelApi.getDownloadUrl(row.id)
  const link = document.createElement('a')
  link.href = url
  link.download = `${row.name + (row.version ? `_${row.version}` : '')  }.pt`
  link.click()
}

// 导出模型
const handleExport = (row: ModelResponse) => {
  exportTargetModel.value = row
  exportForm.value = {target_format: 'onnx', half: false, name: ''}
  exportStatus.value = 'idle'
  exportProgress.value = 0
  exportMessage.value = ''
  showExportDialog.value = true
}

// 关闭导出弹窗
const handleExportClose = () => {
  if (exportWs) {
    exportWs.close()
    exportWs = null
  }
  showExportDialog.value = false
  exportStatus.value = 'idle'
  exportProgress.value = 0
  exportMessage.value = ''
}

// 连接导出进度 WebSocket
const connectExportWs = (exportId: string) => {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = window.location.host
  const wsUrl = `${protocol}//${host}/ws/export/${exportId}`

  exportWs = new WebSocket(wsUrl)

  exportWs.onopen = () => {
    // 连接已建立
  }

  exportWs.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data)
      if (msg.type === 'export_update') {
        const data = msg.data
        exportStatus.value = data.status
        exportProgress.value = data.progress
        exportMessage.value = data.message

        if (data.status === 'completed') {
          ElMessage.success('导出完成')
          exporting.value = false
          loadModels()
        } else if (data.status === 'error') {
          ElMessage.error(data.message)
          exporting.value = false
        }
      }
    } catch (e) {
      console.error('解析导出消息失败', e)
    }
  }

  exportWs.onerror = (error) => {
    console.error('导出 WebSocket 错误', error)
  }

  exportWs.onclose = () => {
    exportWs = null
  }
}

const handleExportSubmit = async () => {
  if (!exportTargetModel.value) return
  exporting.value = true
  try {
    // 调用异步导出接口
    const res = await modelApi.exportAsync(exportTargetModel.value.id, {
      target_format: exportForm.value.target_format,
      half: exportForm.value.half,
    })

    if (res.data.status === 'started') {
      // 导出已开始，连接 WebSocket 监听进度
      exportId.value = res.data.export_id
      exportStatus.value = 'starting'
      exportProgress.value = 0
      exportMessage.value = '正在连接...'
      connectExportWs(res.data.export_id)
    }
  } catch (error: unknown) {
    const msg = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '导出失败'
    ElMessage.error(msg)
    exporting.value = false
  }
}

onMounted(() => {
  loadModels()
  loadAtlases()
})
</script>

<style lang="scss" scoped>
.model-list {
  @apply flex flex-col gap-4;
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
  white-space: nowrap;

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

.action-cell {
  @apply flex items-center justify-around;
  width: 100%;
}

.action-text {
  @apply flex items-center gap-1 text-[var(--accent-cyan)] text-xs font-medium bg-transparent border-none cursor-pointer p-0 transition-all;

  &:hover {
    opacity: 0.75;
  }

  .el-icon {
    @apply text-xs;
  }
}

.delete-item {
  @apply text-red-400;

  &:hover {
    @apply text-red-300 bg-red-50;
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

/* 格式列样式 */
.format-badges {
  @apply flex gap-1.5 flex-wrap;
}

.format-badge {
  @apply text-[10px] px-1.5 py-0.5 rounded bg-[var(--bg-secondary)] text-[var(--text-secondary)] font-mono;

  &.more {
    @apply text-[var(--text-muted)];
  }

  &.is-default {
    @apply text-[var(--accent-cyan)] bg-[rgba(0,240,255,0.1)] border border-[rgba(0,240,255,0.3)];
  }
}

/* 导出对话框 */
.export-model-name {
  @apply mb-4 text-sm text-[var(--text-secondary)];
}

/* 导出进度 */
.export-progress {
  @apply py-4;
}

.progress-info {
  @apply flex justify-between items-center mb-2;
}

.progress-status {
  @apply text-sm font-medium;

  &.idle { @apply text-[var(--text-muted)]; }
  &.starting, &.loading { @apply text-[var(--accent-cyan)]; }
  &.saving { @apply text-[var(--accent-yellow)]; }
  &.completed { @apply text-[var(--accent-green)]; }
  &.error { @apply text-red-400; }
}

.progress-percent {
  @apply text-sm font-mono text-[var(--text-secondary)];
}

.progress-bar {
  @apply w-full h-2 bg-[var(--bg-secondary)] rounded-full overflow-hidden;
}

.progress-fill {
  @apply h-full rounded-full transition-all duration-300;

  &.idle { @apply bg-[var(--bg-secondary)]; }
  &.starting, &.loading { @apply bg-[var(--accent-cyan)]; }
  &.saving { @apply bg-[var(--accent-yellow)]; }
  &.completed { @apply bg-[var(--accent-green)]; }
  &.error { @apply bg-red-400; }
}

.progress-message {
  @apply mt-2 text-xs text-[var(--text-muted)];
}

/* 已有格式标签 */
.existing-formats {
  @apply flex flex-wrap gap-2;
}

.format-tag {
  @apply inline-flex items-center gap-1 px-2 py-1 rounded text-xs bg-[var(--bg-secondary)] text-[var(--text-secondary)];

  &.is-default {
    @apply text-[var(--accent-cyan)] bg-[rgba(0,240,255,0.1)] border border-[rgba(0,240,255,0.25)];
  }

  .default-tag {
    @apply text-[10px] px-1 py-0 rounded bg-[var(--accent-cyan)] text-black;
  }
}

.full-width {
  width: 100%;
}
</style>
