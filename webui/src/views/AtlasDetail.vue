<template>
  <div class="atlas-detail">
    <!-- 页面头部 -->
    <div class="page-header">
      <button class="back-btn" @click="$router.push('/atlas')">
        <BackIcon />
        返回列表
      </button>
      <div class="atlas-info">
        <h2>{{ atlas?.name }}</h2>
        <span class="atlas-desc" v-if="atlas?.description">{{ atlas?.description }}</span>
      </div>
      <div class="header-operations">
        <!-- 批量模式下显示操作按钮 -->
        <template v-if="batchMode || selectedImages.length > 0">
          <span class="selected-count">已选 {{ selectedImages.length }}</span>
          <button class="vg-btn vg-btn-sm" @click="selectAllImages">全选</button>
          <button class="vg-btn vg-btn-sm" @click="clearSelection">取消</button>
          <div class="batch-divider"></div>
          <select v-model="batchTargetDirectory" class="batch-dir-select">
            <option value="">根目录</option>
            <option v-for="dir in directories" :key="dir" :value="dir">{{ dir }}</option>
          </select>
          <button class="vg-btn vg-btn-sm" @click="handleBatchMoveDirectory" :disabled="selectedImages.length === 0">
            <FolderIcon />
            移动
          </button>
          <button class="vg-btn vg-btn-sm danger" @click="handleBatchDelete" :disabled="selectedImages.length === 0">
            <TrashIcon />
            删除
          </button>
        </template>
        <button class="vg-btn vg-btn-sm" v-if="batchMode" @click="exitBatchMode">
          退出批量
        </button>
        <button class="vg-btn vg-btn-sm" v-if="!batchMode" @click="enterBatchMode">
          <CheckSquareIcon />
          批量
        </button>
        <button class="vg-btn vg-btn-primary vg-btn-sm" @click="triggerUpload">
          <UploadIcon />
          上传
        </button>
      </div>
      <input ref="fileInputRef" type="file" accept="image/*" multiple style="display: none" @change="handleFileSelect" />
    </div>

    <div class="content-grid">
      <!-- 主内容区 -->
      <div class="main-panel vg-card">
        <div class="panel-header">
          <div class="tabs">
            <button class="tab-btn" :class="{ active: activeTab === 'images' }" @click="activeTab = 'images'">
              <ImageIcon />
              图片列表
              <span class="count">{{ pagination.total }}</span>
            </button>
            <button class="tab-btn" :class="{ active: activeTab === 'directories' }" @click="activeTab = 'directories'">
              <FolderIcon />
              目录管理
              <span class="count">{{ directories.length }}</span>
            </button>
          </div>
          <div class="header-actions" v-if="activeTab === 'images'">
            <div class="select-wrapper">
              <select v-model="selectedDirectory" @change="onDirectoryChange">
                <option value="">全部目录</option>
                <option v-for="dir in directories" :key="dir" :value="dir">{{ dir }}</option>
              </select>
            </div>
            <button class="action-btn" @click="loadImages">
              <RefreshIcon />
            </button>
          </div>
        </div>

        <!-- 图片列表 - 内部滚动 -->
        <div class="images-content" v-if="activeTab === 'images'">
          <div class="images-grid-wrapper" v-loading="loadingImages">
            <div class="images-grid">
              <div class="image-card" v-for="img in images" :key="img.id">
                <div class="image-wrapper" :class="{ selected: batchMode && isImageSelected(img.id) }">
                  <!-- 复选框 - 仅在批量模式下显示 -->
                  <label class="checkbox-wrapper" v-if="batchMode" @click.stop>
                    <input
                      type="checkbox"
                      :checked="isImageSelected(img.id)"
                      @change="toggleImageSelection(img.id)"
                    />
                  </label>
                  <img :src="getImageUrl(img.file_path)" :alt="getFileName(img.file_path)" @click="openImageDialog(img)" />
                  <div class="image-overlay">
                    <span class="overlay-icon">
                      <EyeIcon />
                    </span>
                  </div>
                  <span class="annotated-badge" v-if="img.annotated"></span>
                  <button class="annotate-btn" @click.stop="handleAnnotateImage(img)" title="标注图片">
                    <TagIcon />
                  </button>
                  <button class="delete-btn" @click.stop="handleDeleteImage(img)" title="删除图片">
                    <TrashIcon />
                  </button>
                </div>
                <div class="image-info">
                  <span class="image-name">{{ getFileName(img.file_path) }}</span>
                  <span class="image-dir" v-if="img.directory">{{ img.directory }}</span>
                </div>
              </div>
            </div>
            <div class="empty-state" v-if="!loadingImages && images.length === 0">
              <div class="empty-icon">
                <ImageIcon />
              </div>
              <p>暂无图片</p>
              <span>上传图片开始标注</span>
            </div>
          </div>
          <!-- 分页器 -->
          <div class="pagination-wrapper" v-if="pagination.total_pages > 1">
            <div class="pagination-info">共 {{ pagination.total }} 张图片</div>
            <div class="pagination-controls">
              <button class="page-btn" :disabled="pagination.page <= 1" @click="goToPage(1)">«</button>
              <button class="page-btn" :disabled="pagination.page <= 1" @click="goToPage(pagination.page - 1)">‹</button>
              <span class="page-current">{{ pagination.page }} / {{ pagination.total_pages }}</span>
              <button class="page-btn" :disabled="pagination.page >= pagination.total_pages" @click="goToPage(pagination.page + 1)">›</button>
              <button class="page-btn" :disabled="pagination.page >= pagination.total_pages" @click="goToPage(pagination.total_pages)">»</button>
            </div>
          </div>
        </div>

        <!-- 目录管理 -->
        <div class="directories-content" v-if="activeTab === 'directories'">
          <div class="create-dir-section">
            <div class="input-group">
              <FolderPlusIcon class="input-icon" />
              <input type="text" v-model="newDirectoryName" placeholder="输入新目录名称"
                     @keyup.enter="handleCreateDirectory" />
            </div>
            <button class="vg-btn vg-btn-primary" @click="handleCreateDirectory">
              <PlusIcon />
              创建目录
            </button>
          </div>

          <div class="directories-list" v-if="directories.length > 0">
            <div class="dir-item" v-for="dir in directories" :key="dir">
              <div class="dir-info">
                <FolderIcon class="dir-icon" />
                <span class="dir-name">{{ dir }}</span>
              </div>
              <div class="dir-actions">
                <button class="action-btn" @click="selectDirectory(dir)" title="选择此目录">
                  <CheckIcon />
                </button>
                <button class="action-btn danger" @click="handleDeleteDirectory(dir)" title="删除目录">
                  <TrashIcon />
                </button>
              </div>
            </div>
          </div>
          <div class="empty-state" v-else>
            <div class="empty-icon">
              <FolderIcon />
            </div>
            <p>暂无子目录</p>
            <span>创建目录来组织图片</span>
          </div>
        </div>
      </div>

      <!-- 侧边信息 -->
      <div class="side-panel">
        <div class="vg-card info-card">
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

        <div class="vg-card upload-tip">
          <div class="tip-header">
            <LightbulbIcon />
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
    <div class="dialog-overlay" v-if="showImageDialog" @click.self="showImageDialog = false">
      <div class="dialog-panel vg-card">
        <div class="dialog-header">
          <h3>图片详情</h3>
          <div class="dialog-actions">
            <el-button type="text" @click="handleAnnotateImage(selectedImage)">标注</el-button>
            <el-button type="text" @click="handleDeleteImage(selectedImage)">删除</el-button>
            <el-button class="close-btn" @click="showImageDialog = false">
              <CloseIcon />
            </el-button>
          </div>
        </div>
        <div class="dialog-content" v-if="selectedImage">
          <div class="image-preview">
            <img :src="getImageUrl(selectedImage.file_path)" :alt="getFileName(selectedImage.file_path)" />
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
              <div class="meta-value dir-edit" v-if="editingDirectory">
                <div class="dir-select-wrap">
                  <select v-model="editDirectoryValue" @change="onDirectorySelect">
                    <option value="">根目录</option>
                    <option v-for="dir in directories" :key="dir" :value="dir">{{ dir }}</option>
                  </select>
                  <input type="text" v-model="editDirectoryValue" placeholder="或输入新目录名"
                         class="dir-text-input" />
                </div>
                <div class="dir-edit-actions">
                  <button class="save-btn" @click="handleSaveDirectory" :disabled="savingDirectory">保存</button>
                  <button class="cancel-btn" @click="cancelEditDirectory">取消</button>
                </div>
              </div>
              <span class="meta-value" v-else>
                {{ selectedImage.directory || '根目录' }}
                <button class="edit-dir-btn" @click="startEditDirectory" title="修改目录">
                  <EditIcon />
                </button>
              </span>
            </div>
            <div class="meta-row">
              <span class="meta-label">标注状态</span>
              <span class="meta-value">
                <span class="status-tag" :class="selectedImage.annotated ? 'annotated' : 'pending'">
                  {{ selectedImage.annotated ? '已标注' : '未标注' }}
                </span>
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, h } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { atlasApi, imageApi } from '@/api'

const route = useRoute()
const router = useRouter()
const id = Number(route.params.id)
const fileInputRef = ref<HTMLInputElement | null>(null)

const atlas = ref<any>(null)
const images = ref<any[]>([])
const directories = ref<string[]>([])
const loadingImages = ref(false)
const activeTab = ref('images')
const selectedDirectory = ref('')
const showImageDialog = ref(false)
const selectedImage = ref<any>(null)
const newDirectoryName = ref('')

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
  } catch (error: any) {
    const msg = error.response?.data?.detail || '修改目录失败'
    ElMessage.error(msg)
  } finally {
    savingDirectory.value = false
  }
}

// 图标组件
const BackIcon = () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
  h('line', { x1: '19', y1: '12', x2: '5', y2: '12' }),
  h('polyline', { points: '12 19 5 12 12 5' })
])

const UploadIcon = () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
  h('path', { d: 'M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4' }),
  h('polyline', { points: '17 8 12 3 7 8' }),
  h('line', { x1: '12', y1: '3', x2: '12', y2: '15' })
])

const CheckSquareIcon = () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
  h('polyline', { points: '9 11 12 14 22 4' }),
  h('path', { d: 'M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11' })
])

const ImageIcon = () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
  h('rect', { x: '3', y: '3', width: '18', height: '18', rx: '2', ry: '2' }),
  h('circle', { cx: '8.5', cy: '8.5', r: '1.5' }),
  h('polyline', { points: '21 15 16 10 5 21' })
])

const FolderIcon = () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
  h('path', { d: 'M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z' })
])

const FolderPlusIcon = () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
  h('path', { d: 'M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z' }),
  h('line', { x1: '12', y1: '11', x2: '12', y2: '17' }),
  h('line', { x1: '9', y1: '14', x2: '15', y2: '14' })
])

const PlusIcon = () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
  h('line', { x1: '12', y1: '5', x2: '12', y2: '19' }),
  h('line', { x1: '5', y1: '12', x2: '19', y2: '12' })
])

const ChevronIcon = () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
  h('polyline', { points: '6 9 12 15 18 9' })
])

const RefreshIcon = () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
  h('polyline', { points: '23 4 23 10 17 10' }),
  h('polyline', { points: '1 20 1 14 7 14' }),
  h('path', { d: 'M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15' })
])

const EyeIcon = () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
  h('path', { d: 'M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z' }),
  h('circle', { cx: '12', cy: '12', r: '3' })
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

const TagIcon = () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
  h('path', { d: 'M20.59 13.41l-7.17 7.17a2 2 0 01-2.83 0L2 12V2h10l8.59 8.59a2 2 0 010 2.82z' }),
  h('line', { x1: '7', y1: '7', x2: '7.01', y2: '7' })
])

const EditIcon = () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
  h('path', { d: 'M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7' }),
  h('path', { d: 'M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z' })
])

const LightbulbIcon = () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
  h('path', { d: 'M9 18h6' }),
  h('path', { d: 'M10 22h4' }),
  h('path', { d: 'M15.09 14c.18-.98.65-1.74 1.41-2.5A4.65 4.65 0 0018 8 6 6 0 006 8c0 1 .23 2.23 1.5 3.5A4.61 4.61 0 018.91 14' })
])

const loadAtlas = async () => {
  try {
    const res = await atlasApi.get(id)
    atlas.value = res.data
  } catch (error) {
    ElMessage.error('加载图集详情失败')
  }
}

const loadImages = async () => {
  loadingImages.value = true
  try {
    const directory = selectedDirectory.value || undefined
    console.log('[DEBUG] loadImages called, directory:', directory, 'page:', pagination.value.page)
    const res = await atlasApi.getImages(id, directory, pagination.value.page, pagination.value.page_size)
    console.log('[DEBUG] getImages response, total:', res.data.total)
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

const openImageDialog = (img: any) => {
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
  } catch (error) {
    ElMessage.error('上传失败')
  }

  input.value = ''
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
  } catch (error: any) {
    const msg = error.response?.data?.detail || '创建目录失败'
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

const handleAnnotateImage = (img: any) => {
  const query = selectedDirectory.value ? { directory: selectedDirectory.value } : {}
  router.push({ path: `/annotate/${img.id}`, query })
}

const handleDeleteImage = async (img: any) => {
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
  } catch (error: any) {
    if (error !== 'cancel') {
      const msg = error.response?.data?.detail || '批量移动失败'
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
  } catch (error: any) {
    if (error !== 'cancel') {
      const msg = error.response?.data?.detail || '批量删除失败'
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
  @apply flex flex-col gap-3;
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
  @apply flex-1 min-w-0;
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
  @apply px-2 py-1 bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded text-xs text-[var(--text-primary)];
}

.vg-btn {
  @apply inline-flex items-center gap-1.5 px-4 py-2 bg-[var(--bg-card)] border border-[var(--border-color)] rounded-md text-sm text-[var(--text-primary)] cursor-pointer transition-all;
}

.vg-btn:hover {
  @apply border-[var(--accent-cyan)] text-[var(--accent-cyan)];
}

.vg-btn svg {
  @apply w-4 h-4;
}

.vg-btn-sm {
  @apply px-3 py-1.5 text-xs;
}

.vg-btn-sm svg {
  @apply w-3.5 h-3.5;
}

.vg-btn-primary {
  @apply bg-[var(--accent-cyan)] border-[var(--accent-cyan)] text-black font-medium;
}

.vg-btn-primary:hover {
  @apply opacity-80;
}

.vg-btn.danger {
  @apply text-[#ff4466];
}

.vg-btn.danger:hover {
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

  select {
    @apply px-4 py-2 pr-9 bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-md text-[var(--text-primary)] text-sm cursor-pointer appearance-none;
  }

  select:focus {
    @apply outline-none border-[var(--accent-cyan)];
  }

  &::after {
    content: '';
    @apply absolute right-3 top-1/2 -translate-y-1/2 border-l-1.5 border-r-1.5 border-t-1.5 border-l-transparent border-r-transparent border-t-[var(--text-muted)];
    pointer-events: none;
  }
}

.action-btn {
  @apply w-9 h-9 flex items-center justify-center bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-md text-[var(--text-secondary)] cursor-pointer transition-all;
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
  @apply w-10 h-10 flex items-center justify-center bg-[var(--accent-cyan)] rounded-full text-[var(--bg-primary)];
}

.overlay-icon svg {
  @apply w-5 h-5;
}

.annotated-badge {
  @apply absolute bottom-2 left-2 w-2 h-2 rounded-full bg-[var(--accent-green)] shadow-[0_0_6px_var(--accent-green)];
}

.delete-btn {
  @apply absolute top-2 right-2 w-7 h-7 flex items-center justify-center bg-[rgba(255,68,102,0.9)] border-none rounded-md text-white cursor-pointer opacity-0 transition-all;
}

.delete-btn svg {
  @apply w-3.5 h-3.5;
}

.annotate-btn {
  @apply absolute top-2 right-10 w-7 h-7 flex items-center justify-center bg-[rgba(0,240,255,0.9)] border-none rounded-md text-black cursor-pointer opacity-0 transition-all;
}

.annotate-btn svg {
  @apply w-3.5 h-3.5;
}

.image-card:hover .annotate-btn {
  @apply opacity-100;
}

.annotate-btn:hover {
  @apply bg-[var(--accent-cyan)] scale-110;
}

.image-card:hover .delete-btn {
  @apply opacity-100;
}

.delete-btn:hover {
  @apply bg-[#ff4466] scale-110;
}

.image-info {
  @apply p-3;
}

.image-name {
  @apply block text-xs text-[var(--text-primary)] truncate;
}

.image-dir {
  @apply block text-[11px] text-[var(--text-muted)] mt-1;
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

.input-group input {
  @apply flex-1 py-3 bg-transparent border-none text-sm text-[var(--text-primary)];
}

.input-group input:focus {
  @apply outline-none;
}

.input-group input::placeholder {
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

:deep(.el-button--text) {
  @apply p-1 border-none bg-transparent text-[#ff4466] text-sm;
  &:hover {
    @apply bg-transparent border-none text-[#ff4466];
  }
}

.close-btn {
  @apply w-9 h-9 flex items-center justify-center bg-transparent border-none text-[var(--text-muted)] cursor-pointer rounded-lg transition-all;
}

.close-btn:hover {
  @apply bg-[var(--bg-hover)] text-[var(--text-primary)];
}

.close-btn svg {
  @apply w-5 h-5;
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

.dir-select-wrap select {
  @apply w-full px-3 py-2 bg-[var(--bg-primary)] border border-[var(--border-color)] rounded-lg text-[var(--text-primary)] text-sm appearance-none cursor-pointer;
}

.dir-select-wrap select:focus {
  @apply outline-none border-[var(--accent-cyan)];
}

.dir-text-input {
  @apply w-full px-3 py-2 bg-[var(--bg-primary)] border border-[var(--border-color)] rounded-lg text-[var(--text-primary)] text-sm;
}

.dir-text-input:focus {
  @apply outline-none border-[var(--accent-cyan)];
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
</style>
