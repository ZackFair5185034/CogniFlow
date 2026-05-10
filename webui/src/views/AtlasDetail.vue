<template>
  <div class="atlas-detail">
    <!-- 页面头部 -->
    <div class="page-header">
      <button
        class="back-btn"
        @click="$router.push('/atlas')"
      >
        <SvgIcon name="back" />
        返回列表
      </button>
      <div class="atlas-info">
        <h2>{{ atlas?.name }}</h2>
        <span
          v-if="atlas?.description"
          class="atlas-desc"
        >{{ atlas?.description }}</span>
      </div>
      <div class="header-operations">
        <!-- 批量模式下显示操作按钮 -->
        <template v-if="batchMode || selectedImages.length > 0">
          <span class="selected-count">已选 {{ selectedImages.length }}</span>
          <button
            class="ui-btn ui-btn-sm"
            @click="selectAllImages"
          >
            全选
          </button>
          <button
            class="ui-btn ui-btn-sm"
            @click="clearSelection"
          >
            取消
          </button>
          <div class="batch-divider" />
          <el-select
            v-model="batchTargetDirectory"
            placeholder="选择目录"
            clearable
            class="batch-dir-select"
          >
            <el-option
              label="根目录"
              value=""
            />
            <el-option
              v-for="dir in directories"
              :key="dir"
              :label="dir"
              :value="dir"
            />
          </el-select>
          <button
            class="ui-btn ui-btn-sm"
            :disabled="selectedImages.length === 0"
            @click="handleBatchMoveDirectory"
          >
            <SvgIcon name="folder" />
            移动
          </button>
          <button
            class="ui-btn ui-btn-sm"
            :disabled="selectedImages.length === 0"
            @click="handleBatchDownload"
          >
            <SvgIcon name="download" />
            下载
          </button>
          <button
            class="ui-btn ui-btn-sm danger"
            :disabled="selectedImages.length === 0"
            @click="handleBatchDelete"
          >
            <SvgIcon name="trash" />
            删除
          </button>
        </template>
        <button
          v-if="batchMode"
          class="ui-btn ui-btn-sm"
          @click="exitBatchMode"
        >
          退出批量
        </button>
        <button
          v-if="!batchMode"
          class="ui-btn ui-btn-sm"
          @click="enterBatchMode"
        >
          <SvgIcon name="check-square" />
          批量
        </button>
        <button
          class="ui-btn ui-btn-secondary ui-btn-sm"
          @click="triggerVideoUpload"
        >
          <SvgIcon name="video" />
          解析视频
        </button>
        <button
          class="ui-btn ui-btn-primary ui-btn-sm"
          @click="triggerUpload"
        >
          <SvgIcon name="upload" />
          上传图片
        </button>
      </div>
      <input
        ref="fileInputRef"
        type="file"
        accept="image/*"
        multiple
        style="display: none"
        @change="handleFileSelect"
      >
      <input
        ref="videoInputRef"
        type="file"
        accept="video/*"
        style="display: none"
        @change="handleVideoSelect"
      >
    </div>

    <div class="content-grid">
      <!-- 主内容区 -->
      <div class="main-panel ui-card">
        <div class="panel-header">
          <div class="tabs">
            <button
              class="tab-btn"
              :class="{ active: activeTab === 'images' }"
              @click="activeTab = 'images'"
            >
              <SvgIcon name="image" />
              图片列表
              <span class="count">{{ pagination.total }}</span>
            </button>
            <button
              class="tab-btn"
              :class="{ active: activeTab === 'directories' }"
              @click="activeTab = 'directories'"
            >
              <SvgIcon name="folder" />
              目录管理
              <span class="count">{{ directories.length }}</span>
            </button>
          </div>
          <div
            v-if="activeTab === 'images'"
            class="header-actions"
          >
            <div class="select-wrapper">
              <el-select
                v-model="selectedDirectory"
                placeholder="全部目录"
                clearable
                @change="onDirectoryChange"
              >
                <el-option
                  label="全部目录"
                  value=""
                />
                <el-option
                  v-for="dir in directories"
                  :key="dir"
                  :label="dir"
                  :value="dir"
                />
              </el-select>
            </div>
            <div
              class="sort-wrapper"
              @click="showSortMenu = !showSortMenu"
            >
              <span class="sort-label">
                {{ sortConfig.by === 'created_at' ? '创建时间' : '名称' }}
                <span class="sort-arrow">{{ sortConfig.order === 'asc' ? '↑' : '↓' }}</span>
              </span>
              <div
                v-if="showSortMenu"
                class="sort-dropdown"
                @click.stop
              >
                <div class="sort-group-title">
                  排序字段
                </div>
                <div
                  class="sort-option"
                  :class="{ active: sortConfig.by === 'created_at' }"
                  @click="sortConfig.by = 'created_at'; loadImages()"
                >
                  创建时间
                </div>
                <div
                  class="sort-option"
                  :class="{ active: sortConfig.by === 'name' }"
                  @click="sortConfig.by = 'name'; loadImages()"
                >
                  名称
                </div>
                <div class="sort-divider" />
                <div class="sort-group-title">
                  排序方向
                </div>
                <div
                  class="sort-option"
                  :class="{ active: sortConfig.order === 'desc' }"
                  @click="sortConfig.order = 'desc'; loadImages()"
                >
                  降序
                </div>
                <div
                  class="sort-option"
                  :class="{ active: sortConfig.order === 'asc' }"
                  @click="sortConfig.order = 'asc'; loadImages()"
                >
                  升序
                </div>
              </div>
            </div>
            <button
              class="action-btn"
              @click="loadImages"
            >
              <SvgIcon name="refresh" />
            </button>
          </div>
        </div>

        <!-- 图片列表 - 内部滚动 -->
        <div
          v-if="activeTab === 'images'"
          class="images-content"
        >
          <div
            v-loading="loadingImages"
            class="images-grid-wrapper"
          >
            <div class="images-grid">
              <div
                v-for="img in images"
                :key="img.id"
                class="image-card"
              >
                <div
                  class="image-wrapper"
                  :class="{ selected: batchMode && isImageSelected(img.id) }"
                >
                  <!-- 复选框 - 仅在批量模式下显示 -->
                  <el-checkbox
                    v-if="batchMode"
                    :model-value="isImageSelected(img.id)"
                    @update:model-value="toggleImageSelection(img.id)"
                    @click.stop
                  />
                  <img
                    :src="getImageUrl(img.file_path)"
                    :alt="getFileName(img.file_path)"
                    @click="openImageDialog(img)"
                  >
                  <div class="image-overlay">
                    <span class="overlay-icon">
                      <SvgIcon name="eye" />
                    </span>
                  </div>
                  <span
                    v-if="img.annotated"
                    class="annotated-badge"
                  />
                </div>
                <div class="image-info">
                  <span
                    class="image-name"
                    :title="getFileName(img.file_path)"
                  >{{ getFileName(img.file_path) }}</span>
                  <div
                    v-if="img.directory"
                    class="image-dir-row"
                  >
                    <span class="image-dir">{{ img.directory }}</span>
                    <div
                      class="image-actions"
                      @click.stop
                    >
                      <button
                        class="img-action-btn"
                        title="下载"
                        @click="handleDownloadImage(img)"
                      >
                        <SvgIcon name="download" />
                      </button>
                      <button
                        class="img-action-btn"
                        title="标注图片"
                        @click="handleAnnotateImage(img)"
                      >
                        <SvgIcon name="tag" />
                      </button>
                      <button
                        class="img-action-btn danger"
                        title="删除图片"
                        @click="handleDeleteImage(img)"
                      >
                        <SvgIcon name="trash" />
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div
              v-if="!loadingImages && images.length === 0"
              class="empty-state"
            >
              <div class="empty-icon">
                <SvgIcon name="image" />
              </div>
              <p>暂无图片</p>
              <span>上传图片开始标注</span>
            </div>
          </div>
          <!-- 分页器 -->
          <div
            v-if="pagination.total_pages > 1"
            class="pagination-wrapper"
          >
            <div class="pagination-info">
              共 {{ pagination.total }} 张图片
            </div>
            <div class="pagination-controls">
              <button
                class="page-btn"
                :disabled="pagination.page <= 1"
                @click="goToPage(1)"
              >
                «
              </button>
              <button
                class="page-btn"
                :disabled="pagination.page <= 1"
                @click="goToPage(pagination.page - 1)"
              >
                ‹
              </button>
              <span class="page-current">{{ pagination.page }} / {{ pagination.total_pages }}</span>
              <button
                class="page-btn"
                :disabled="pagination.page >= pagination.total_pages"
                @click="goToPage(pagination.page + 1)"
              >
                ›
              </button>
              <button
                class="page-btn"
                :disabled="pagination.page >= pagination.total_pages"
                @click="goToPage(pagination.total_pages)"
              >
                »
              </button>
            </div>
          </div>
        </div>

        <!-- 目录管理 -->
        <div
          v-if="activeTab === 'directories'"
          class="directories-content"
        >
          <div class="create-dir-section">
            <div class="input-group">
              <SvgIcon
                name="folder-plus"
                class="input-icon"
              />
              <el-input
                v-model="newDirectoryName"
                placeholder="输入新目录名称"
                @keyup.enter="handleCreateDirectory"
              />
            </div>
            <button
              class="ui-btn ui-btn-primary"
              @click="handleCreateDirectory"
            >
              <SvgIcon name="plus" />
              创建目录
            </button>
          </div>

          <div
            v-if="directories.length > 0"
            class="directories-list"
          >
            <div
              v-for="dir in directories"
              :key="dir"
              class="dir-item"
            >
              <div class="dir-info">
                <FolderIcon class="dir-icon" />
                <span class="dir-name">{{ dir }}</span>
              </div>
              <div class="dir-actions">
                <button
                  class="action-btn"
                  title="选择此目录"
                  @click="selectDirectory(dir)"
                >
                  <SvgIcon name="check" />
                </button>
                <button
                  class="action-btn danger"
                  title="删除目录"
                  @click="handleDeleteDirectory(dir)"
                >
                  <SvgIcon name="trash" />
                </button>
              </div>
            </div>
          </div>
          <div
            v-else
            class="empty-state"
          >
            <div class="empty-icon">
              <SvgIcon name="folder" />
            </div>
            <p>暂无子目录</p>
            <span>创建目录来组织图片</span>
          </div>
        </div>
      </div>

      <!-- 侧边信息 -->
      <div class="side-panel">
        <div class="ui-card info-card">
          <div class="card-header">
            <h4>图集信息</h4>
          </div>
          <div class="info-list">
            <div class="info-item">
              <span class="info-label">ID</span>
              <span class="info-value id">#{{ atlas?.id }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">图片数</span>
              <span class="info-value">{{ pagination.total }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">目录数</span>
              <span class="info-value">{{ directories.length }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">已标注</span>
              <span class="info-value success">{{ annotatedCount }} 张</span>
            </div>
          </div>
        </div>

        <div class="ui-card upload-tip">
          <div class="tip-header">
            <SvgIcon name="lightbulb" />
            <span>上传提示</span>
          </div>
          <ul class="tip-list">
            <li>支持 JPG、PNG 等常见格式</li>
            <li>可多选文件同时上传</li>
            <li>上传时可选择目标目录</li>
            <li>或在上传后拖拽图片调整目录</li>
          </ul>
        </div>
      </div>
    </div>

    <!-- 图片详情对话框 -->
    <div
      v-if="showImageDialog"
      class="dialog-overlay"
      @click.self="showImageDialog = false"
    >
      <div class="dialog-panel ui-card">
        <div class="dialog-header">
          <h3>图片详情</h3>
          <div class="dialog-actions">
            <el-button
              link
              @click="handleAnnotateImage(selectedImage)"
            >
              标注
            </el-button>
            <el-button
              link
              @click="handleDeleteImage(selectedImage)"
            >
              删除
            </el-button>
            <el-button
              class="close-btn"
              @click="showImageDialog = false"
            >
              <SvgIcon name="close" />
            </el-button>
          </div>
        </div>
        <div
          v-if="selectedImage"
          class="dialog-content"
        >
          <div class="image-preview">
            <img
              :src="getImageUrl(selectedImage.file_path)"
              :alt="getFileName(selectedImage.file_path)"
            >
          </div>
          <div class="image-meta">
            <div class="meta-row">
              <span class="meta-label">文件名</span>
              <span class="meta-value">{{ getFileName(selectedImage.file_path) }}</span>
            </div>
            <div class="meta-row">
              <span class="meta-label">尺寸</span>
              <span class="meta-value">{{ selectedImage.width }} x {{ selectedImage.height }}</span>
            </div>
            <div class="meta-row">
              <span class="meta-label">目录</span>
              <div
                v-if="editingDirectory"
                class="meta-value dir-edit"
              >
                <div class="dir-select-wrap">
                  <el-select
                    v-model="editDirectoryValue"
                    placeholder="选择目录"
                    clearable
                    @change="onDirectorySelect"
                  >
                    <el-option
                      label="根目录"
                      value=""
                    />
                    <el-option
                      v-for="dir in directories"
                      :key="dir"
                      :label="dir"
                      :value="dir"
                    />
                  </el-select>
                  <el-input
                    v-model="editDirectoryValue"
                    placeholder="或输入新目录名"
                    class="dir-text-input"
                  />
                </div>
                <div class="dir-edit-actions">
                  <button
                    class="save-btn"
                    :disabled="savingDirectory"
                    @click="handleSaveDirectory"
                  >
                    保存
                  </button>
                  <button
                    class="cancel-btn"
                    @click="cancelEditDirectory"
                  >
                    取消
                  </button>
                </div>
              </div>
              <span
                v-else
                class="meta-value"
              >
                {{ selectedImage.directory || '根目录' }}
                <button
                  class="edit-dir-btn"
                  title="修改目录"
                  @click="startEditDirectory"
                >
                  <SvgIcon name="edit" />
                </button>
              </span>
            </div>
            <div class="meta-row">
              <span class="meta-label">标注状态</span>
              <span class="meta-value">
                <span
                  class="status-tag"
                  :class="selectedImage.annotated ? 'annotated' : 'pending'"
                >
                  {{ selectedImage.annotated ? '已标注' : '未标注' }}
                </span>
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
    <!-- 视频提取对话框 -->
    <div
      v-if="showVideoDialog"
      class="dialog-overlay"
      @click.self="showVideoDialog = false"
    >
      <div class="dialog-panel ui-card">
        <div class="dialog-header">
          <h3>从视频提取帧</h3>
          <button
            class="close-btn"
            @click="showVideoDialog = false"
          >
            <SvgIcon name="close" />
          </button>
        </div>
        <div class="dialog-content">
          <div
            v-if="videoMeta"
            class="video-meta"
          >
            <div class="meta-row">
              <span class="meta-label">时长</span>
              <span class="meta-value">{{ videoMeta.duration }}s</span>
            </div>
            <div class="meta-row">
              <span class="meta-label">帧率</span>
              <span class="meta-value">{{ videoMeta.fps }} fps</span>
            </div>
            <div class="meta-row">
              <span class="meta-label">总帧数</span>
              <span class="meta-value">{{ videoMeta.total_frames }}</span>
            </div>
          </div>
          <div class="extract-config">
            <label class="section-label">提取张数</label>
            <el-input-number
              v-model="extractCount"
              :min="1"
              :max="videoMeta?.total_frames || 999999"
              class="extract-input"
            />
            <span
              v-if="videoMeta && extractCount"
              class="extract-hint"
            >
              均匀采样，间隔约 {{ Math.max(1, Math.round(videoMeta.total_frames / extractCount)) }} 帧
            </span>
          </div>
          <div class="dialog-footer">
            <button
              class="ui-btn"
              @click="showVideoDialog = false"
            >
              取消
            </button>
            <button
              class="ui-btn ui-btn-primary"
              :disabled="!extractCount"
              @click="confirmExtract"
            >
              开始提取
            </button>
          </div>
        </div>
      </div>
    </div>
    <!-- 提取进度对话框 -->
    <div
      v-if="showExtractProgress"
      class="dialog-overlay"
      @click.self="() => {}"
    >
      <div class="dialog-panel ui-card extract-progress-dialog">
        <div class="dialog-header">
          <h3>正在提取帧...</h3>
        </div>
        <div class="dialog-content">
          <div class="progress-info">
            <span
              class="progress-status"
              :class="extractProgress.status"
            >
              {{ extractProgress.status === 'pending' ? '等待开始...' : extractProgress.status === 'processing' ? '提取中...' : extractProgress.status === 'completed' ? '完成' : '失败' }}
            </span>
            <span class="progress-count">{{ extractProgress.extracted_count }} / {{ extractProgress.total_frames }}</span>
          </div>
          <div class="progress-bar-wrapper">
            <div class="progress-bar">
              <div
                class="progress-fill"
                :style="{ width: extractProgress.progress + '%' }"
              />
            </div>
          </div>
          <p
            v-if="extractProgress.status === 'processing'"
            class="progress-hint"
          >
            正在从视频提取帧，请稍候...
          </p>
          <p
            v-if="extractProgress.error"
            class="progress-error"
          >
            {{ extractProgress.error }}
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { atlasApi, imageApi } from '@/api'
import type { AtlasResponse, ImageResponse } from '@/types/api'

const route = useRoute()
const router = useRouter()
const id = Number(route.params.id)
const fileInputRef = ref<HTMLInputElement | null>(null)
const videoInputRef = ref<HTMLInputElement | null>(null)

const atlas = ref<AtlasResponse | null>(null)
const images = ref<ImageResponse[]>([])
const directories = ref<string[]>([])
const loadingImages = ref(false)
const activeTab = ref('images')
const selectedDirectory = ref('')
const sortConfig = ref<{ by: string; order: 'asc' | 'desc' }>({ by: 'created_at', order: 'desc' })
const showSortMenu = ref(false)
const showImageDialog = ref(false)
const selectedImage = ref<ImageResponse | null>(null)
const newDirectoryName = ref('')

// 视频提取相关
const showVideoDialog = ref(false)
const videoMeta = ref<{ fps: number; total_frames: number; duration: number } | null>(null)
const extractCount = ref(0)
const pendingVideoPath = ref('')

// 异步提取进度相关
const showExtractProgress = ref(false)
const extractJobId = ref('')
const extractProgress = ref({
  status: '',
  progress: 0,
  extracted_count: 0,
  total_frames: 0,
  error: null as string | null,
})
const extractPollingTimer = ref<number | null>(null)

// 分页状态
const pagination = ref({
  page: 1,
  page_size: 50,
  total: 0,
  total_pages: 1,
})

// 批量操作模式
const batchMode = ref(false)

const enterBatchMode = () => {
  batchMode.value = true
}

const exitBatchMode = () => {
  batchMode.value = false
  clearSelection()
}

const annotatedCount = computed(() => images.value.filter(img => img.annotated).length)

// 目录编辑状态
const editingDirectory = ref(false)
const editDirectoryValue = ref('')
const savingDirectory = ref(false)

const startEditDirectory = () => {
  editDirectoryValue.value = selectedImage.value?.directory || ''
  editingDirectory.value = true
}

const onDirectorySelect = () => {
  // select 改变时同步到 input（用户可继续手动编辑）
}

const cancelEditDirectory = () => {
  editingDirectory.value = false
  editDirectoryValue.value = ''
}

const handleSaveDirectory = async () => {
  if (!selectedImage.value) return
  savingDirectory.value = true
  try {
    await imageApi.updateDirectory(selectedImage.value.id, editDirectoryValue.value)
    ElMessage.success('目录已更新')
    selectedImage.value.directory = editDirectoryValue.value || null
    editingDirectory.value = false
    loadImages()
    loadDirectories()
  } catch (error: unknown) {
    const msg = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '修改目录失败'
    ElMessage.error(msg)
  } finally {
    savingDirectory.value = false
  }
}

const loadAtlas = async () => {
  try {
    const res = await atlasApi.get(id)
    atlas.value = res.data
  } catch {
    ElMessage.error('加载图集详情失败')
  }
}

const loadImages = async () => {
  loadingImages.value = true
  try {
    const directory = selectedDirectory.value || undefined
    const res = await atlasApi.getImages(id, directory, pagination.value.page, pagination.value.page_size, sortConfig.value.by, sortConfig.value.order)
    images.value = res.data.items
    pagination.value.total = res.data.total
    pagination.value.total_pages = res.data.total_pages
  } catch (error) {
    ElMessage.error('加载图片失败')
    console.error('[DEBUG] loadImages error:', error)
  } finally {
    loadingImages.value = false
  }
}

const onDirectoryChange = () => {
  pagination.value.page = 1
  loadImages()
}

const goToPage = (page: number) => {
  pagination.value.page = page
  loadImages()
}

const loadDirectories = async () => {
  try {
    const res = await atlasApi.getDirectories(id)
    directories.value = res.data
  } catch (error) {
    console.error('加载目录失败', error)
  }
}

const triggerUpload = () => {
  fileInputRef.value?.click()
}

const openImageDialog = (img: ImageResponse) => {
  selectedImage.value = img
  showImageDialog.value = true
}

const selectDirectory = (dir: string) => {
  selectedDirectory.value = dir
  activeTab.value = 'images'
  loadImages()
}

const handleFileSelect = async (event: Event) => {
  const input = event.target as HTMLInputElement
  if (!input.files || input.files.length === 0) return

  const formData = new FormData()
  for (let i = 0; i < input.files.length; i++) {
    formData.append('files', input.files[i])
  }

  try {
    await atlasApi.uploadImages(id, formData, selectedDirectory.value || undefined)
    ElMessage.success('上传成功')
    loadImages()
    loadDirectories()
  } catch {
    ElMessage.error('上传失败')
  }

  input.value = ''
}

const triggerVideoUpload = () => {
  videoInputRef.value?.click()
}

const handleVideoSelect = async (event: Event) => {
  const input = event.target as HTMLInputElement
  if (!input.files || input.files.length === 0) return
  const file = input.files[0]

  try {
    const res = await atlasApi.uploadVideo(id, file)
    videoMeta.value = res.data.metadata
    extractCount.value = res.data.metadata.total_frames
    pendingVideoPath.value = res.data.video_path
    showVideoDialog.value = true
  } catch {
    ElMessage.error('视频上传失败')
  }

  input.value = ''
}

const confirmExtract = async () => {
  if (!extractCount.value || extractCount.value <= 0) {
    ElMessage.warning('请输入有效的提取张数')
    return
  }

  showVideoDialog.value = false
  showExtractProgress.value = true
  extractProgress.value = { status: 'pending', progress: 0, extracted_count: 0, total_frames: videoMeta.value?.total_frames || 0, error: null }

  try {
    const res = await atlasApi.extractVideoFramesAsync(id, pendingVideoPath.value, extractCount.value)
    extractJobId.value = res.data.job_id
    extractProgress.value.status = 'processing'
    startExtractPolling()
  } catch (error: unknown) {
    const msg = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '提交提取任务失败'
    extractProgress.value.status = 'failed'
    extractProgress.value.error = msg
  }
}

const startExtractPolling = () => {
  stopExtractPolling()
  extractPollingTimer.value = window.setInterval(async () => {
    if (!extractJobId.value) return
    try {
      const res = await atlasApi.getExtractJobStatus(id, extractJobId.value)
      const data = res.data
      extractProgress.value = {
        status: data.status,
        progress: data.progress * 100,
        extracted_count: data.extracted_count,
        total_frames: data.total_frames,
        error: data.error,
      }
      if (data.status === 'completed' || data.status === 'failed') {
        stopExtractPolling()
        if (data.status === 'completed') {
          ElMessage.success(`成功提取 ${data.extracted_count} 张图片`)
          showExtractProgress.value = false
          // 自动切换到新提取的目录
          selectedDirectory.value = data.directory
          loadImages()
          loadDirectories()
        }
      }
    } catch {
      stopExtractPolling()
    }
  }, 1000)
}

const stopExtractPolling = () => {
  if (extractPollingTimer.value !== null) {
    clearInterval(extractPollingTimer.value)
    extractPollingTimer.value = null
  }
}

const handleCreateDirectory = async () => {
  if (!newDirectoryName.value.trim()) {
    ElMessage.warning('请输入目录名')
    return
  }
  const dirName = newDirectoryName.value.trim()
  try {
    await atlasApi.createDirectory(id, dirName)
    // 重新加载目录列表
    await loadDirectories()
    // 自动选中新创建的目录
    selectedDirectory.value = dirName
    ElMessage.success(`已创建目录 "${dirName}"，上传图片将自动归类到此目录`)
    newDirectoryName.value = ''
  } catch (error: unknown) {
    const msg = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '创建目录失败'
    ElMessage.error(msg)
  }
}

const handleDeleteDirectory = async (dir: string) => {
  try {
    await ElMessageBox.confirm(
      `确定删除目录 "${dir}" 吗？该目录下的所有图片将被永久删除，此操作不可撤销。`,
      '删除目录',
      { type: 'warning', confirmButtonText: '确认删除', cancelButtonText: '取消' }
    )
    await atlasApi.deleteDirectory(id, dir)
    ElMessage.success(`目录 "${dir}" 已删除`)
    loadDirectories()
    loadImages()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除目录失败')
    }
  }
}

const handleAnnotateImage = (img: { id: number }) => {
  const query: Record<string, string> = selectedDirectory.value ? { directory: selectedDirectory.value } : {}
  query.sort_by = sortConfig.value.by
  query.sort_order = sortConfig.value.order
  router.push({ path: `/annotate/${img.id}`, query })
}

const handleDeleteImage = async (img: { file_path: string; id: number }) => {
  try {
    await ElMessageBox.confirm(
      `确定删除图片 "${getFileName(img.file_path)}" 吗？此操作不可撤销。`,
      '删除确认',
      { type: 'warning', confirmButtonText: '确认', cancelButtonText: '取消' }
    )
    await imageApi.delete(img.id)
    ElMessage.success('删除成功')
    showImageDialog.value = false
    loadImages()
    loadDirectories()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

const handleDownloadImage = (img: ImageResponse) => {
  const url = getImageUrl(img.file_path)
  const filename = getFileName(img.file_path)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
}

const handleBatchDownload = async () => {
  if (selectedImages.value.length === 0) {
    ElMessage.warning('请先选择图片')
    return
  }
  ElMessage.info(`正在打包下载 ${selectedImages.value.length} 张图片...`)
  try {
    const response = await atlasApi.batchDownloadImages(Number(route.params.id), selectedImages.value)
    const blob = response instanceof Blob ? response : response.data
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `images_${Date.now()}.zip`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    ElMessage.success('打包下载完成')
  } catch {
    ElMessage.error('打包下载失败')
  }
}

// ============ 批量操作逻辑 ============

// 选中的图片ID列表
const selectedImages = ref<number[]>([])
const batchTargetDirectory = ref('')

// 判断图片是否被选中
const isImageSelected = (imageId: number) => {
  return selectedImages.value.includes(imageId)
}

// 切换图片选中状态
const toggleImageSelection = (imageId: number) => {
  const index = selectedImages.value.indexOf(imageId)
  if (index === -1) {
    selectedImages.value.push(imageId)
  } else {
    selectedImages.value.splice(index, 1)
  }
}

// 全选当前显示的图片
const selectAllImages = () => {
  selectedImages.value = images.value.map(img => img.id)
}

// 清除选中状态
const clearSelection = () => {
  selectedImages.value = []
}

// 批量移动到指定目录
const handleBatchMoveDirectory = async () => {
  if (selectedImages.value.length === 0) {
    ElMessage.warning('请先选择图片')
    return
  }
  try {
    await ElMessageBox.confirm(
      `确定将选中的 ${selectedImages.value.length} 张图片移动到 ${batchTargetDirectory.value || '根目录'} 吗？`,
      '批量移动',
      { type: 'warning', confirmButtonText: '确认', cancelButtonText: '取消' }
    )
    await imageApi.batchUpdateDirectory(selectedImages.value, batchTargetDirectory.value)
    ElMessage.success(`成功移动 ${selectedImages.value.length} 张图片`)
    clearSelection()
    batchTargetDirectory.value = ''
    loadImages()
    loadDirectories()
  } catch (error: unknown) {
    if (error !== 'cancel') {
      const msg = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '批量移动失败'
      ElMessage.error(msg)
    }
  }
}

// 批量删除图片
const handleBatchDelete = async () => {
  if (selectedImages.value.length === 0) {
    ElMessage.warning('请先选择图片')
    return
  }
  try {
    await ElMessageBox.confirm(
      `确定删除选中的 ${selectedImages.value.length} 张图片吗？此操作不可撤销。`,
      '批量删除',
      { type: 'warning', confirmButtonText: '确认', cancelButtonText: '取消' }
    )
    await imageApi.batchDelete(selectedImages.value)
    ElMessage.success(`成功删除 ${selectedImages.value.length} 张图片`)
    clearSelection()
    loadImages()
    loadDirectories()
  } catch (error: unknown) {
    if (error !== 'cancel') {
      const msg = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '批量删除失败'
      ElMessage.error(msg)
    }
  }
}

const getImageUrl = (filePath: string) => {
  const uploadsIndex = filePath.indexOf('uploads')
  if (uploadsIndex !== -1) {
    const relativePath = filePath.substring(uploadsIndex)
    return `/${relativePath.replace(/\\/g, '/')}`
  }
  return `file://${filePath.replace(/\\/g, '/')}`
}

const getFileName = (filePath: string) => {
  return filePath.split(/[\\/]/).pop() || ''
}

onMounted(() => {
  // 从 URL 查询参数恢复目录筛选状态
  const dirFromQuery = route.query.directory as string | undefined
  if (dirFromQuery) {
    selectedDirectory.value = dirFromQuery
  }
  loadAtlas()
  loadImages()
  loadDirectories()
})
</script>

<style lang="scss" scoped>
.atlas-detail {
  @apply flex flex-col gap-4;
  height: 100%;
  min-height: 0;
  overflow: hidden;
}

.page-header {
  @apply flex items-center gap-3 flex-shrink-0 flex-wrap;
}

.back-btn {
  @apply inline-flex items-center gap-1.5 px-3 py-1.5 bg-[var(--bg-card)] border border-[var(--border-color)] rounded text-[var(--text-secondary)] text-xs cursor-pointer transition-all;
}

.back-btn:hover {
  @apply border-[var(--accent-cyan)] text-[var(--accent-cyan)];
}

.back-btn svg {
  @apply w-3.5 h-3.5;
}

.atlas-info {
  @apply flex-1 min-w-0 flex items-center;
}

.atlas-info h2 {
  @apply text-xl font-semibold truncate;
  background: linear-gradient(90deg, var(--text-primary), var(--accent-cyan));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.atlas-desc {
  @apply text-xs text-[var(--text-muted)] ml-2;
}

.header-operations {
  @apply flex items-center gap-2 flex-wrap;
}

.selected-count {
  @apply text-xs font-medium text-[var(--accent-cyan)] mr-1;
}

.batch-divider {
  @apply w-px h-5 bg-[var(--border-color)] mx-1;
}

.batch-dir-select {
  @apply text-xs;
  width: 140px;
}

.ui-btn.danger {
  @apply text-[#ff4466];
}

.ui-btn.danger:hover {
  @apply border-[#ff4466];
}

/* 内容网格 */
.content-grid {
  @apply flex gap-6;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

/* 主面板 */
.main-panel {
  @apply flex flex-col;
  flex: 1;
  min-width: 0;
  overflow: hidden;
}

/* 面板头部 */
.panel-header {
  @apply flex justify-between items-center p-4;
  border-bottom: 1px solid var(--border-color);
}

.tabs {
  @apply flex gap-2;
}

.tab-btn {
  @apply inline-flex items-center gap-2 px-4 py-2.5 bg-transparent border border-transparent rounded-lg text-[var(--text-secondary)] text-sm cursor-pointer transition-all;
}

.tab-btn svg {
  @apply w-4.5 h-4.5;
}

.tab-btn:hover {
  @apply bg-[var(--bg-hover)] text-[var(--text-primary)];
}

.tab-btn.active {
  background: rgba(0, 240, 255, 0.1);
  border-color: rgba(0, 240, 255, 0.3);
  @apply text-[var(--accent-cyan)];
}

.tab-btn .count {
  font-family: 'JetBrains Mono', monospace;
  @apply text-[11px] px-1.5 py-0.5 rounded;
  background: var(--bg-secondary);
}

.header-actions {
  @apply flex items-center gap-2.5;
}

.select-wrapper {
  @apply relative;
}

.action-btn {
  @apply w-9 h-9 flex items-center justify-center bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-md text-[var(--text-secondary)] cursor-pointer transition-all;
}

.sort-wrapper {
  @apply relative flex items-center gap-2 px-4 h-9 bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-md text-[var(--text-primary)] text-sm cursor-pointer transition-all;
  min-width: 140px;
}

.sort-wrapper:hover {
  @apply border-[var(--accent-cyan)];
}

.sort-label {
  @apply flex items-center gap-2;
}

.sort-arrow {
  @apply inline-flex items-center justify-center min-w-[1.2em] text-[var(--accent-cyan)] font-medium;
}

.sort-dropdown {
  @apply absolute top-full left-0 mt-1 w-full bg-[var(--bg-card)] border border-[var(--border-color)] rounded-md shadow-lg z-50;
}

.sort-option {
  @apply px-3 py-2 text-sm cursor-pointer transition-all;
}

.sort-option:hover {
  @apply bg-[var(--bg-hover)] text-[var(--accent-cyan)];
}

.sort-option.active {
  @apply text-[var(--accent-cyan)] bg-[rgba(0,240,255,0.1)];
}

.sort-divider {
  @apply h-px bg-[var(--border-color)] my-1;
}

.sort-group-title {
  @apply px-3 py-1 text-xs text-[var(--text-muted)] uppercase tracking-wider;
}

.action-btn:hover {
  @apply border-[var(--accent-cyan)] text-[var(--accent-cyan)];
}

.action-btn svg {
  @apply w-4 h-4;
}

.action-btn.danger:hover {
  @apply border-[#ff4466] text-[#ff4466];
}

/* 图片网格 */
.images-content {
  @apply flex flex-col;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.images-grid-wrapper {
  @apply flex-1 overflow-y-auto;
  min-height: 0;
}

.images-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 16px;
  padding: 16px;
}

/* 分页器 */
.pagination-wrapper {
  @apply flex items-center justify-between p-4 border-t border-[var(--border-color)];
  flex-shrink: 0;
}

.pagination-info {
  @apply text-sm text-[var(--text-muted)];
}

.pagination-controls {
  @apply flex items-center gap-2;
}

.page-btn {
  @apply px-3 py-1.5 bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-md text-sm text-[var(--text-secondary)] cursor-pointer transition-all;
}

.page-btn:hover:not(:disabled) {
  @apply border-[var(--accent-cyan)] text-[var(--accent-cyan)];
}

.page-btn:disabled {
  @apply opacity-40 cursor-not-allowed;
}

.page-current {
  @apply px-3 py-1.5 font-mono text-sm text-[var(--accent-cyan)];
}

.image-card {
  @apply bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-xl overflow-hidden cursor-pointer transition-all;
}

.image-card:hover {
  @apply border-[var(--accent-cyan)];
  box-shadow: 0 4px 16px rgba(0, 240, 255, 0.12);
}

.image-wrapper {
  @apply relative overflow-hidden;
  aspect-ratio: 1;
  background: var(--bg-secondary);  /* 占位暗色，避免图片加载前闪白 */
}

/* 选中状态 */
.image-wrapper.selected {
  @apply ring-2 ring-[var(--accent-cyan)] ring-offset-2 ring-offset-[var(--bg-card)];
}

/* 复选框样式 */
.checkbox-wrapper {
  @apply absolute top-2 left-2 z-10 cursor-pointer;
}

.checkbox-wrapper input[type="checkbox"] {
  @apply w-5 h-5 cursor-pointer accent-[var(--accent-cyan)];
}

.image-wrapper img {
  @apply w-full h-full object-cover;
  background: var(--bg-secondary);  /* 图片加载完成前不闪白 */
}

.image-overlay {
  @apply absolute inset-0 bg-black/50 flex items-center justify-center opacity-0 transition-opacity duration-200 pointer-events-none;
}

.image-card:hover .image-overlay {
  @apply opacity-100;
}

.overlay-icon {
  @apply w-8 h-8 flex items-center justify-center bg-black/60 rounded-full text-white;
}

.overlay-icon svg {
  @apply w-4 h-4;
}

.annotated-badge {
  @apply absolute bottom-2 left-2 w-2 h-2 rounded-full bg-[var(--accent-green)] shadow-[0_0_6px_var(--accent-green)];
}

.image-info {
  @apply p-3;
  @apply flex flex-col gap-1;
}

.image-name {
  @apply text-xs text-[var(--text-primary)] truncate block w-full min-w-0;
}

.image-dir-row {
  @apply flex items-center justify-between gap-2;
}

.image-dir {
  @apply text-[11px] text-[var(--text-muted)] truncate;
}

.image-actions {
  @apply flex items-center gap-1;
}

.img-action-btn {
  @apply w-5 h-5 flex items-center justify-center rounded text-[var(--text-muted)] cursor-pointer transition-all bg-transparent border-none;
}

.img-action-btn svg {
  @apply w-3.5 h-3.5;
}

.img-action-btn:hover {
  @apply text-[var(--accent-cyan)] bg-[var(--bg-hover)];
}

.img-action-btn.danger:hover {
  @apply text-[#ff4466] bg-[var(--bg-hover)];
}

/* 目录管理 */
.directories-content {
  @apply p-5;
}

.create-dir-section {
  @apply flex gap-3 mb-6;
}

.input-group {
  @apply flex-1 flex items-center gap-2.5 px-3.5 bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-lg;
}

.input-icon {
  @apply w-4.5 h-4.5 text-[var(--text-muted)];
}

.input-group :deep(.el-input__wrapper) {
  @apply flex-1 py-0 px-0 bg-transparent;
  box-shadow: none !important;
  border: none !important;
}

.input-group :deep(.el-input__inner) {
  @apply py-3 text-sm text-[var(--text-primary)];
}

.input-group :deep(.el-input__inner::placeholder) {
  @apply text-[var(--text-muted)];
}

.directories-list {
  @apply flex flex-col gap-2;
}

.dir-item {
  @apply flex items-center justify-between p-3.5 bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-lg transition-all;
}

.dir-item:hover {
  @apply border-[var(--accent-cyan)];
}

.dir-info {
  @apply flex items-center gap-3;
}

.dir-icon {
  @apply w-5.5 h-5.5 text-[var(--accent-yellow)];
}

.dir-name {
  @apply text-sm font-medium text-[var(--text-primary)];
}

.dir-actions {
  @apply flex gap-2;
}

/* 主面板 */
.main-panel {
  @apply flex flex-col;
  flex: 1;
  min-width: 0;
  overflow: hidden;
}

/* 侧边栏 */
.side-panel {
  @apply flex flex-col gap-4;
  width: 280px;
  flex-shrink: 0;
  overflow-y: auto;
}

.info-card .card-header {
  @apply p-4;
  border-bottom: 1px solid var(--border-color);

  h4 {
    @apply text-sm font-semibold text-[var(--text-secondary)] uppercase tracking-wide;
  }
}

.info-list {
  @apply p-4 flex flex-col gap-3.5;
}

.info-item {
  @apply flex justify-between items-center;
}

.info-label {
  @apply text-sm text-[var(--text-muted)];
}

.info-value {
  @apply text-sm font-medium text-[var(--text-primary)];
}

.info-value.id {
  font-family: 'JetBrains Mono', monospace;
  @apply text-[var(--accent-cyan)];
}

.info-value.success {
  @apply text-[var(--accent-green)];
}

/* 上传提示 */
.upload-tip {
  background: linear-gradient(135deg, rgba(0, 240, 255, 0.05), rgba(255, 0, 170, 0.05));
}

.tip-header {
  @apply flex items-center gap-2.5 p-4 text-sm font-semibold text-[var(--accent-yellow)];
  border-bottom: 1px solid var(--border-color);

  svg {
    @apply w-4.5 h-4.5;
  }
}

.tip-list {
  @apply p-4 m-0 list-none flex flex-col gap-2.5;
}

.tip-list li {
  @apply text-sm text-[var(--text-secondary)] pl-4 relative;
}

.tip-list li::before {
  content: '›';
  @apply absolute left-0 text-[var(--accent-cyan)];
}

/* 空状态 */
.empty-state {
  @apply py-15 px-5 flex flex-col items-center text-center;
}

.empty-icon {
  @apply w-16 h-16 flex items-center justify-center bg-[var(--bg-secondary)] rounded-xl mb-4 text-[var(--text-muted)] opacity-50;

  svg {
    @apply w-8 h-8;
  }
}

.empty-state p {
  @apply text-base text-[var(--text-secondary)] mb-1.5;
}

.empty-state span {
  @apply text-sm text-[var(--text-muted)];
}

/* 对话框 */
.dialog-overlay {
  @apply fixed inset-0 flex items-center justify-center;
  background: rgba(0, 0, 0, 0.8);
  backdrop-filter: blur(4px);
  z-index: 1000;
}

.dialog-panel {
  width: 600px;
  @apply max-w-[90vw];
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  animation: dialogIn 0.3s ease;
}

@keyframes dialogIn {
  from {
    opacity: 0;
    transform: scale(0.95);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

.dialog-header {
  @apply flex justify-between items-center p-5;
  border-bottom: 1px solid var(--border-color);

  h3 {
    @apply text-lg font-semibold;
  }
}

.dialog-actions {
  @apply flex items-center gap-2.5;
}

.close-btn {
  @apply w-8 h-8 flex items-center justify-center bg-transparent border-none text-[var(--text-muted)] cursor-pointer rounded-lg transition-all;
}

.close-btn:hover {
  @apply bg-[var(--bg-hover)] text-[var(--text-primary)];
}

.close-btn svg {
  @apply w-4.5 h-4.5;
}

.dialog-content {
  @apply p-6;
  overflow-y: auto;
  min-height: 0;
}

.image-preview {
  @apply bg-[var(--bg-secondary)] rounded-xl overflow-hidden mb-5;
}

.image-preview img {
  @apply w-full object-contain;
  max-height: min(400px, 60vh);
}

.image-meta {
  @apply flex flex-col gap-3.5;
}

.meta-row {
  @apply flex justify-between items-center p-2.5 bg-[var(--bg-secondary)] rounded-lg;
}

.meta-label {
  @apply text-sm text-[var(--text-muted)];
}

.meta-value {
  @apply text-sm font-medium text-[var(--text-primary)];
}

.status-tag {
  @apply px-2 py-1 rounded text-xs font-medium;
}

.status-tag.annotated {
  background: rgba(0, 255, 136, 0.15);
  @apply text-[var(--accent-green)];
}

.status-tag.pending {
  background: rgba(136, 136, 170, 0.15);
  @apply text-[var(--text-muted)];
}

/* 目录编辑 */
.dir-edit {
  @apply flex flex-col gap-2 w-full max-w-[280px];
}

.dir-select-wrap {
  @apply flex flex-col gap-2;
}

.dir-edit-actions {
  @apply flex gap-2 justify-end;
}

.save-btn {
  @apply px-4 py-1.5 bg-[var(--accent-cyan)] border-none rounded-md text-black text-xs font-semibold cursor-pointer transition-all;
}

.save-btn:hover {
  @apply opacity-80;
}

.save-btn:disabled {
  @apply opacity-40 cursor-not-allowed;
}

.cancel-btn {
  @apply px-4 py-1.5 bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-md text-[var(--text-secondary)] text-xs cursor-pointer transition-all;
}

.cancel-btn:hover {
  @apply border-[var(--accent-cyan)] text-[var(--accent-cyan)];
}

.edit-dir-btn {
  @apply inline-flex items-center justify-center w-6 h-6 ml-2 bg-transparent border-none text-[var(--text-muted)] cursor-pointer rounded align-middle transition-all;
}

.edit-dir-btn:hover {
  @apply text-[var(--accent-cyan)] bg-[var(--bg-hover)];
}

.edit-dir-btn svg {
  @apply w-3.5 h-3.5;
}

/* 视频提取对话框 */
.video-meta {
  @apply flex flex-col gap-2 mb-5;
}

.video-meta .meta-row {
  @apply flex justify-between items-center p-3 bg-[var(--bg-secondary)] rounded-lg;
}

.video-meta .meta-label {
  @apply text-sm text-[var(--text-muted)];
}

.video-meta .meta-value {
  @apply text-sm font-medium font-mono text-[var(--accent-cyan)];
}

.extract-config {
  @apply flex flex-col gap-3 mb-5;
}

.section-label {
  @apply text-xs text-[var(--text-secondary)] uppercase tracking-wide;
}

.extract-input {
  @apply font-mono;
}

.extract-hint {
  @apply text-xs text-[var(--text-muted)];
}

.ui-btn-secondary {
  @apply bg-[var(--bg-secondary)] border-[var(--border-color)] text-[var(--text-primary)];
}

.ui-btn-secondary:hover {
  @apply border-[var(--accent-cyan)] text-[var(--accent-cyan)];
}

/* 提取进度对话框 */
.extract-progress-dialog .dialog-content {
  @apply flex flex-col gap-5;
}

.progress-info {
  @apply flex justify-between items-center;
}

.progress-status {
  @apply text-sm font-medium;
}

.progress-status.pending { @apply text-[var(--text-muted)]; }
.progress-status.processing { @apply text-[var(--accent-cyan)]; }
.progress-status.completed { @apply text-[var(--accent-green)]; }
.progress-status.failed { @apply text-[#ff4466]; }

.progress-count {
  @apply text-sm font-mono text-[var(--text-secondary)];
}

.progress-bar-wrapper {
  @apply w-full;
}

.progress-bar {
  @apply w-full h-2.5 bg-[var(--bg-secondary)] rounded-full overflow-hidden relative;
}

.progress-fill {
  @apply h-full bg-gradient-to-r from-[var(--accent-cyan)] to-[var(--accent-magenta)] rounded-full transition-all duration-300 ease-out;
}

.progress-hint {
  @apply text-xs text-[var(--text-muted)] text-center;
}

.progress-error {
  @apply text-xs text-[#ff4466] text-center;
}

/* 深色主题 Element Plus 覆盖 */
:deep(.el-input__wrapper) {
  background: var(--bg-primary) !important;
  box-shadow: none !important;
  border: 1px solid var(--border-color);
}
:deep(.el-input__wrapper:hover) {
  border-color: var(--accent-cyan);
}
:deep(.el-input__wrapper.is-focus) {
  border-color: var(--accent-cyan);
  box-shadow: 0 0 0 1px var(--accent-cyan) inset !important;
}
:deep(.el-input__inner) {
  color: var(--text-primary);
}
:deep(.el-select__wrapper) {
  background: var(--bg-primary) !important;
  box-shadow: none !important;
  border: 1px solid var(--border-color);
}
:deep(.el-select-dropdown) {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
}
:deep(.el-select-dropdown__item) {
  color: var(--text-primary);
}
:deep(.el-select-dropdown__item.hover),
:deep(.el-select-dropdown__item:hover) {
  background: var(--bg-hover);
}
:deep(.el-select-dropdown__item.is-selected) {
  color: var(--accent-cyan);
}
:deep(.el-input-number__decrease),
:deep(.el-input-number__increase) {
  background: var(--bg-secondary) !important;
  border-color: var(--border-color) !important;
  color: var(--text-secondary) !important;
}
:deep(.el-input-number__decrease:hover),
:deep(.el-input-number__increase:hover) {
  color: var(--accent-cyan) !important;
}
:deep(.el-checkbox__input.is-checked .el-checkbox__inner) {
  background: var(--accent-cyan);
  border-color: var(--accent-cyan);
}
</style>
