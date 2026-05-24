<template>
  <div class="flex flex-col h-full bg-[var(--bg-primary)]">
    <!-- 顶部工具栏 -->
    <div class="toolbar">
      <div class="toolbar-left">
        <button
          class="ui-btn"
          @click="goBack"
        >
          <SvgIcon name="back" />
          返回
        </button>
        <div
          v-if="currentImage"
          class="image-nav"
        >
          <button
            class="ui-btn"
            :disabled="!hasPrev"
            @click="prevImage"
          >
            <SvgIcon name="chevron-left" />
          </button>
          <span class="nav-info">#{{ currentImage.id }}</span>
          <button
            class="ui-btn"
            :disabled="!hasNext"
            @click="nextImage"
          >
            <SvgIcon name="chevron-right" />
          </button>
        </div>
        <div
          v-if="totalImages > 0"
          class="progress-stats"
        >
          <div class="stat-item">
            <span class="stat-label">标注</span>
            <span class="stat-value done">{{ annotatedImages }}</span>
          </div>
          <span class="stat-sep">/</span>
          <div class="stat-item">
            <span class="stat-label">共</span>
            <span class="stat-value">{{ totalImages }}</span>
          </div>
          <div class="stat-bar">
            <div
              class="stat-fill"
              :style="{ width: progressPercent + '%' }"
            />
          </div>
          <span
            class="stat-pct"
            :class="{ done: progressPercent === 100 }"
          >{{ progressPercent }}%</span>
        </div>
      </div>
      <div class="toolbar-center">
        <div class="hotkey-hints">
          <span class="hint"><kbd>S</kbd> 保存</span>
          <span class="hint"><kbd>Z</kbd> 撤销</span>
          <span class="hint"><kbd>DEL</kbd> 删除选中</span>
          <span class="hint"><kbd>← A</kbd> 上一页 <kbd>D →</kbd> 下一页</span>
        </div>
      </div>
      <div class="toolbar-right">
        <button
          class="ui-btn ui-btn-primary"
          :disabled="!hasChanges || saving"
          @click="saveAnnotations"
        >
          <SvgIcon name="save" />
          {{ saving ? '保存中...' : '保存 (S)' }}
        </button>
      </div>
    </div>

    <!-- 主内容区 -->
    <div class="content-area p-0">
      <!-- 左侧类别面板 -->
      <div class="category-panel">
        <div class="panel-header">
          <h3>类别库</h3>
          <div class="header-actions">
            <div
              class="header-dropdown"
              @click.stop
            >
              <button
                class="ui-btn ui-btn-small"
                @click="showHeaderMenu = !showHeaderMenu"
              >
                <SvgIcon name="menu" />
              </button>
              <div
                v-if="showHeaderMenu"
                class="dropdown-menu"
                @click="showHeaderMenu = false"
              >
                <div
                  class="dropdown-item"
                  @click="handleExport"
                >
                  <SvgIcon name="download" />
                  <span>导出类别</span>
                </div>
                <div
                  class="dropdown-item"
                  @click="triggerImport"
                >
                  <SvgIcon name="upload" />
                  <span>导入类别</span>
                </div>
                <div class="dropdown-divider" />
                <div
                  class="dropdown-item"
                  @click="openCreateDialog"
                >
                  <SvgIcon name="plus" />
                  <span>新建类别</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 路径导航 + 当前选中标签 -->
        <div
          v-if="currentPath.length > 0 || selectedCategoryId"
          class="breadcrumb"
        >
          <span
            class="breadcrumb-item"
            @click="navigateToRoot"
          >根目录</span>
          <template
            v-for="(item, idx) in currentPath"
            :key="item.id"
          >
            <SvgIcon
              name="chevron-right"
              class="breadcrumb-sep"
            />
            <span
              class="breadcrumb-item"
              @click="navigateTo(idx)"
            >{{ item.name }}</span>
          </template>
          <template v-if="selectedCategoryId">
            <SvgIcon
              name="chevron-right"
              class="breadcrumb-sep"
            />
            <span
              class="current-tag"
              :style="{ background: getSelectedCategoryColor }"
            >
              {{ getSelectedCategoryName }}
            </span>
          </template>
        </div>

        <!-- 当前目录下的目录列表 -->
        <div class="dir-list">
          <div
            v-for="dir in currentDirectories"
            :key="dir.id"
            class="dir-item"
            @click="enterDirectory(dir)"
          >
            <SvgIcon
              name="folder"
              class="dir-icon"
            />
            <span class="dir-name">{{ dir.name }}</span>
            <div class="item-actions">
              <button
                class="icon-btn"
                title="删除"
                @click.stop="deleteCategory(dir.id)"
              >
                <SvgIcon name="trash" />
              </button>
              <SvgIcon
                name="chevron-right"
                class="enter-icon"
              />
            </div>
          </div>
        </div>

        <!-- 当前目录下的标签列表 -->
        <div
          v-if="currentCategories.length > 0"
          class="tag-list"
        >
          <div class="tag-header">
            标签
          </div>
          <div
            v-for="(cat, idx) in currentCategories"
            :key="cat.id"
            class="tag-item"
            :class="{ active: selectedCategoryId === cat.id }"
            @click="selectCategory(cat.id)"
          >
            <span
              class="tag-color"
              :style="{ background: cat.color }"
            />
            <span class="tag-name">{{ cat.name }}</span>
            <div class="item-actions">
              <button
                class="icon-btn"
                title="删除"
                @click.stop="deleteCategory(cat.id)"
              >
                <SvgIcon name="trash" />
              </button>
              <span class="tag-hotkey">{{ idx + 1 }}</span>
            </div>
          </div>
        </div>

        <div
          v-if="currentItems.length === 0"
          class="empty-tip"
        >
          空目录
        </div>
      </div>

      <!-- 画布区域 -->
      <div
        ref="canvasContainer"
        class="canvas-container"
      >
        <canvas
          ref="canvasRef"
          @mousedown="handleMouseDown"
          @mousemove="handleMouseMove"
          @mouseup="handleMouseUp"
          @mouseleave="handleMouseUp"
        />
        <div
          v-if="imageLoading"
          class="canvas-loading"
        >
          <div class="loading-spinner" />
          <span>加载图片中...</span>
        </div>
        <div
          v-if="!currentImage && !imageLoading"
          class="canvas-overlay"
        >
          <div class="no-image">
            请先选择图片
          </div>
        </div>
      </div>

      <!-- 右侧标注列表 -->
      <div class="annotation-panel">
        <div class="panel-header">
          <h3>当前标注 ({{ localAnnotations.length }})</h3>
        </div>
        <div class="annotation-list">
          <div
            v-for="(ann, index) in localAnnotations"
            :key="ann.id || index"
            class="annotation-item"
            :class="{ selected: selectedAnnotationIndex === index, pending: !ann.id }"
            @click="selectAnnotation(index)"
          >
            <span
              class="ann-color"
              :style="{ background: getCategoryColor(ann.category_id) }"
            />
            <span class="ann-name">{{ getCategoryName(ann.category_id) }}</span>
            <span class="ann-bbox">[{{ formatBbox(ann.bbox) }}]</span>
            <div class="ann-actions">
              <button
                class="icon-btn"
                title="删除"
                @click.stop="removeAnnotation(index)"
              >
                <SvgIcon name="trash" />
              </button>
            </div>
          </div>
        </div>
        <div
          v-if="localAnnotations.length === 0"
          class="empty-tip"
        >
          暂无标注<br>在画布上拖拽绘制框
        </div>
      </div>
    </div>

    <!-- 创建类别对话框 -->
    <div
      v-if="showCategoryDialog"
      class="dialog-overlay"
      @click.self="closeCreateDialog"
    >
      <div class="dialog-panel ui-card">
        <div class="dialog-header">
          <h3>{{ categoryForm.is_directory ? '创建目录' : '创建标签' }}</h3>
          <button
            class="close-btn"
            @click="closeCreateDialog"
          >
            <SvgIcon name="close" />
          </button>
        </div>
        <div class="dialog-body">
          <!-- 类型选择 -->
          <div class="form-group">
            <label>类型</label>
            <div class="type-toggle">
              <button
                type="button"
                class="toggle-btn"
                :class="{ active: !categoryForm.is_directory }"
                @click="categoryForm.is_directory = false"
              >
                <SvgIcon name="tag" /> 标签
              </button>
              <button
                type="button"
                class="toggle-btn"
                :class="{ active: categoryForm.is_directory }"
                @click="categoryForm.is_directory = true"
              >
                <SvgIcon name="folder" /> 目录
              </button>
            </div>
          </div>
          <!-- 名称 -->
          <div class="form-group">
            <label>名称</label>
            <el-input
              v-model="categoryForm.name"
              type="text"
              :placeholder="categoryForm.is_directory ? '输入目录名称' : '输入标签名称'"
            />
          </div>
          <!-- 颜色（仅标签） -->
          <div
            v-if="!categoryForm.is_directory"
            class="form-group"
          >
            <label>颜色</label>
            <div class="color-picker">
              <el-input
                v-model="categoryForm.color"
                type="text"
              />
              <span
                class="color-preview"
                :style="{ background: categoryForm.color }"
              />
            </div>
          </div>
          <!-- 父目录 -->
          <div class="form-group">
            <label>父目录</label>
            <div class="parent-path">
              {{ currentPath.length === 0 ? '根目录' : currentPath.map(p => p.name).join(' > ') }}
            </div>
          </div>
        </div>
        <div class="dialog-footer">
          <button
            class="ui-btn"
            @click="closeCreateDialog"
          >
            取消
          </button>
          <button
            class="ui-btn ui-btn-primary"
            :disabled="creatingCategory"
            @click="handleCreateCategory"
          >
            {{ creatingCategory ? '创建中...' : '创建' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 导入类别对话框 -->
    <div
      v-if="showImportDialog"
      class="dialog-overlay"
      @click.self="closeImportDialog"
    >
      <div class="dialog-panel ui-card">
        <div class="dialog-header">
          <h3>导入类别</h3>
          <button
            class="close-btn"
            @click="closeImportDialog"
          >
            <SvgIcon name="close" />
          </button>
        </div>
        <div class="dialog-body">
          <!-- 步骤 1：文件选择 -->
          <div
            v-if="!importPreviewData"
            class="form-group"
          >
            <label>选择 JSON 文件</label>
            <div
              class="import-dropzone"
              @click="importFileInput?.click()"
            >
              <SvgIcon name="upload" />
              <span>点击选择文件</span>
              <span class="import-hint">支持 .json 格式的类别导出文件</span>
            </div>
            <input
              ref="importFileInput"
              type="file"
              accept=".json,application/json"
              style="display: none"
              @change="onImportFileSelected"
            >
          </div>

          <!-- 步骤 2：预览 -->
          <div
            v-if="importPreviewData"
            class="import-preview"
          >
            <div class="preview-stats">
              <div class="preview-stat">
                <span class="stat-count">{{ importPreviewStats.directories }}</span>
                <span class="stat-label">目录</span>
              </div>
              <div class="preview-stat">
                <span class="stat-count">{{ importPreviewStats.tags }}</span>
                <span class="stat-label">标签</span>
              </div>
              <div class="preview-stat">
                <span class="stat-count">{{ importPreviewStats.total }}</span>
                <span class="stat-label">总计</span>
              </div>
            </div>
            <div class="preview-tree">
              <div
                v-for="node in importPreviewData.categories"
                :key="node.name"
                class="preview-node"
              >
                <SvgIcon :name="node.is_directory ? 'folder' : 'tag'" />
                <span>{{ node.name }}</span>
                <span
                  v-if="node.children?.length"
                  class="node-count"
                >({{ countChildren(node) }} 子项)</span>
              </div>
            </div>
            <div
              v-if="importParseError"
              class="import-error"
            >
              {{ importParseError }}
            </div>
          </div>
        </div>
        <div class="dialog-footer">
          <button
            class="ui-btn"
            @click="closeImportDialog"
          >
            取消
          </button>
          <button
            v-if="importPreviewData"
            class="ui-btn ui-btn-primary"
            :disabled="importing"
            @click="handleImport"
          >
            {{ importing ? '导入中...' : '确认导入' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, computed, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { categoryApi, annotationApi, atlasApi } from '@/api'
import SvgIcon from '@/components/SvgIcon.vue'
import type { AnnotationResponse } from '@/types/api'
import type { CategoryNode } from '@/api'

interface Category {
  id: number
  name: string
  color: string
  is_directory: boolean
  parent_id: number | null
  children?: Category[]
}

interface Annotation {
  id?: number
  image_id: number
  category_id: number
  bbox: number[]  // [x, y, w, h] 在原始图片坐标中
}

interface ImageData {
  id: number
  file_path: string
  atlas_id: number
  width?: number
  height?: number
  annotated?: boolean
}

const route = useRoute()
const router = useRouter()

const canvasRef = ref<HTMLCanvasElement | null>(null)
const canvasContainer = ref<HTMLDivElement | null>(null)

const categories = ref<Category[]>([])
const treeData = ref<Category[]>([])
const currentPath = ref<Category[]>([])
const currentImage = ref<ImageData | null>(null)
const localAnnotations = ref<Annotation[]>([])
const selectedCategoryId = ref<number | null>(null)
const selectedAnnotationIndex = ref<number | null>(null)

const imageLoading = ref(false)
const saving = ref(false)
const showCategoryDialog = ref(false)
const creatingCategory = ref(false)
const categoryForm = ref({ name: '', color: '#FF0000', is_directory: false, parent_id: null as number | null })

// 导入导出状态
const showHeaderMenu = ref(false)
const closeHeaderMenu = () => { showHeaderMenu.value = false }
const showImportDialog = ref(false)
const importPreviewData = ref<{ version: number; categories: CategoryNode[] } | null>(null)
const importParseError = ref('')
const importing = ref(false)
const importFileInput = ref<HTMLInputElement | null>(null)

const imageList = ref<ImageData[]>([])
const currentImageIndex = ref(0)

const hasPrev = computed(() => currentImageIndex.value > 0)
const hasNext = computed(() => currentImageIndex.value >= 0 && currentImageIndex.value < imageList.value.length - 1)
const hasChanges = computed(() => {
  return localAnnotations.value.some(ann => !ann.id)
})

// 标注进度统计
const totalImages = computed(() => imageList.value.length)
const annotatedImages = computed(() => imageList.value.filter(img => img.annotated).length)
const progressPercent = computed(() => totalImages.value > 0 ? Math.round(annotatedImages.value / totalImages.value * 100) : 0)

// ============ 类别树 Computed ============
const flatCategories = computed(() => {
  const result: Category[] = []
  const flatten = (items: Category[]) => {
    items.forEach(item => {
      result.push(item)
      if (item.children?.length) {
        flatten(item.children)
      }
    })
  }
  flatten(treeData.value)
  return result
})

const currentItems = computed(() => {
  const parentId = currentPath.value.length === 0 ? null : currentPath.value[currentPath.value.length - 1].id
  return flatCategories.value.filter(c => c.parent_id === parentId)
})

const currentDirectories = computed(() => {
  return currentItems.value.filter(c => c.is_directory)
})

const currentCategories = computed(() => {
  return currentItems.value.filter(c => !c.is_directory)
})

const getSelectedCategoryColor = computed(() => {
  const cat = flatCategories.value.find(c => c.id === selectedCategoryId.value)
  return cat?.color || '#ff4444'
})

const getSelectedCategoryName = computed(() => {
  const cat = flatCategories.value.find(c => c.id === selectedCategoryId.value)
  return cat?.name || '未选中'
})

// ============ 类别树 Methods ============
const loadTree = async () => {
  try {
    const res = await categoryApi.getTree()
    treeData.value = res.data || []
    if (!selectedCategoryId.value && flatCategories.value.length > 0) {
      const firstTag = flatCategories.value.find(c => !c.is_directory)
      if (firstTag) selectedCategoryId.value = firstTag.id
    }
  } catch (error) {
    console.error('加载类别失败:', error)
  }
}

const enterDirectory = (dir: Category) => {
  if (!dir.is_directory) return
  currentPath.value.push(dir)
}

const navigateTo = (index: number) => {
  if (index === currentPath.value.length - 1) return
  currentPath.value = currentPath.value.slice(0, index + 1)
}

const navigateToRoot = () => {
  currentPath.value = []
}

const selectCategory = (id: number) => {
  selectedCategoryId.value = id
}

const deleteCategory = async (id: number) => {
  if (!confirm('确定要删除吗？')) return
  try {
    await categoryApi.delete(id)
    ElMessage.success('删除成功')
    // 如果删除的是当前选中的类别，清除选中
    if (selectedCategoryId.value === id) {
      selectedCategoryId.value = null
    }
    // 重新加载树
    await loadTree()
  } catch (error: unknown) {
    const msg = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '删除失败'
    ElMessage.error(msg)
  }
}

// ============ 导入导出 ============
const countChildren = (node: { children?: unknown[] }): number => {
  let count = 0
  const walk = (nodes: unknown[]) => {
    for (const n of nodes as { children?: unknown[] }[]) {
      count++
      if (n.children?.length) walk(n.children)
    }
  }
  if (node.children?.length) walk(node.children)
  return count
}

const importPreviewStats = computed(() => {
  const data = importPreviewData.value
  if (!data) return { directories: 0, tags: 0, total: 0 }
  let dirs = 0, tags = 0
  const walk = (nodes: CategoryNode[]) => {
    for (const n of nodes) {
      if (n.is_directory) dirs++
      else tags++
      if (n.children?.length) walk(n.children)
    }
  }
  walk(data.categories || [])
  return { directories: dirs, tags, total: dirs + tags }
})

const handleExport = async () => {
  try {
    const res = await categoryApi.export()
    const data = JSON.stringify(res.data, null, 2)
    const blob = new Blob([data], { type: 'application/json' })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `categories_${Date.now()}.json`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch {
    ElMessage.error('导出失败')
  }
}

const triggerImport = () => {
  importPreviewData.value = null
  importParseError.value = ''
  showImportDialog.value = true
  nextTick(() => {
    if (importFileInput.value) importFileInput.value.value = ''
  })
}

const closeImportDialog = () => {
  showImportDialog.value = false
  importPreviewData.value = null
  importParseError.value = ''
}

const onImportFileSelected = (e: Event) => {
  const input = e.target as HTMLInputElement
  if (!input.files?.length) return
  const file = input.files[0]
  const reader = new FileReader()
  reader.onload = (evt) => {
    try {
      const data = JSON.parse(evt.target?.result as string)
      if (typeof data.version !== 'number' || !Array.isArray(data.categories)) {
        importParseError.value = '无效的类别文件格式：缺少 version 或 categories 字段'
        return
      }
      importPreviewData.value = data
      importParseError.value = ''
    } catch {
      importParseError.value = '无效的 JSON 文件'
    }
  }
  reader.readAsText(file)
}

const handleImport = async () => {
  if (!importPreviewData.value) return
  importing.value = true
  try {
    const res = await categoryApi.import(importPreviewData.value)
    const result = res.data
    const msgs: string[] = []
    if (result.created > 0) msgs.push(`新增 ${result.created} 个类别`)
    if (result.skipped > 0) msgs.push(`跳过 ${result.skipped} 个重复类别`)
    ElMessage.success(msgs.join('，') || '导入完成')
    closeImportDialog()
    await loadTree()
    if (selectedCategoryId.value) {
      const stillExists = flatCategories.value.find(c => c.id === selectedCategoryId.value)
      if (!stillExists) selectedCategoryId.value = null
    }
  } catch (error: unknown) {
    const msg = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '导入失败'
    ElMessage.error(msg)
  } finally {
    importing.value = false
  }
}

// ============ 类别树 Methods ============
const openCreateDialog = () => {
  categoryForm.value = {
    name: '',
    color: '#FF0000',
    is_directory: false,
    parent_id: currentPath.value.length > 0 ? currentPath.value[currentPath.value.length - 1].id : null
  }
  showCategoryDialog.value = true
}

const closeCreateDialog = () => {
  showCategoryDialog.value = false
  categoryForm.value = { name: '', color: '#FF0000', is_directory: false, parent_id: null }
}

let ctx: CanvasRenderingContext2D | null = null
let isDrawing = false
let startX = 0
let startY = 0
let imgElement: HTMLImageElement | null = null
let displayScale = 1

const image_id = computed(() => Number(route.params.image_id))

const getImageUrl = (filePath: string) => {
  const uploadsIndex = filePath.indexOf('uploads')
  if (uploadsIndex !== -1) {
    const relativePath = filePath.substring(uploadsIndex)
    return `/${relativePath.replace(/\\/g, '/')}`
  }
  return `file://${filePath.replace(/\\/g, '/')}`
}

const formatBbox = (bbox: number[]) => {
  return bbox.map(v => Math.round(v)).join(', ')
}

const loadCategories = async () => {
  try {
    const res = await categoryApi.list()
    categories.value = res.data
    // 查找第一个标签（非目录）作为默认选中
    if (categories.value.length > 0 && !selectedCategoryId.value) {
      const firstTag = categories.value.find(c => !c.is_directory)
      if (firstTag) {
        selectedCategoryId.value = firstTag.id
      }
    }
  } catch {
    ElMessage.error('加载类别失败')
  }
  // 同时加载树形结构
  await loadTree()
}

const loadImage = async (id: number) => {
  imageLoading.value = true
  try {
    const res = await fetch(`/api/images/${id}`)
    if (!res.ok) throw new Error('图片不存在')
    const imgData = await res.json()
    currentImage.value = imgData

    await loadAnnotations(id)
    await nextTick()
    initCanvas()
  } catch (error) {
    ElMessage.error('加载图片失败')
    console.error(error)
  } finally {
    imageLoading.value = false
  }
}

const loadAnnotations = async (imageId: number) => {
  try {
    const res = await annotationApi.getByImage(imageId)
    localAnnotations.value = res.data.map((ann: AnnotationResponse) => ({
      id: ann.id,
      image_id: ann.image_id,
      category_id: ann.category_id,
      bbox: ann.bbox
    }))
  } catch (error) {
    console.error('加载标注失败', error)
  }
}

const loadImageList = async () => {
  if (!currentImage.value) return
  try {
    const directory = route.query.directory as string | undefined
    const sortBy = route.query.sort_by as string | undefined
    const sortOrder = route.query.sort_order as string | undefined
    const res = await atlasApi.getImages(currentImage.value.atlas_id, directory, 1, 999, sortBy, sortOrder)
    imageList.value = res.data.items || []
    currentImageIndex.value = imageList.value.findIndex((img: ImageData) => img.id === currentImage.value?.id)
  } catch (error) {
    console.error('加载图片列表失败', error)
  }
}

const initCanvas = () => {
  if (!canvasRef.value || !canvasContainer.value || !currentImage.value) return

  const canvas = canvasRef.value
  const container = canvasContainer.value
  ctx = canvas.getContext('2d')
  if (!ctx) return

  const img = new Image()
  imgElement = img
  img.onload = () => {
    const containerWidth = container.clientWidth - 40
    const containerHeight = container.clientHeight - 40

    displayScale = Math.min(
      containerWidth / img.width,
      containerHeight / img.height,
      1
    )

    canvas.width = img.width * displayScale
    canvas.height = img.height * displayScale

    ctx!.drawImage(img, 0, 0, canvas.width, canvas.height)
    drawAllBboxes()
  }
  img.onerror = () => {
    ElMessage.error('图片加载失败')
    imageLoading.value = false
  }
  img.src = getImageUrl(currentImage.value.file_path)
}

const drawAllBboxes = () => {
  if (!ctx || !canvasRef.value) return

  const canvas = canvasRef.value
  ctx.clearRect(0, 0, canvas.width, canvas.height)

  if (imgElement) {
    ctx.drawImage(imgElement, 0, 0, canvas.width, canvas.height)
  }

  localAnnotations.value.forEach((ann, index) => {
    draw_bbox(ann, index === selectedAnnotationIndex.value)
  })
}

const draw_bbox = (ann: Annotation, selected = false) => {
  if (!ctx) return

  // 将原始坐标转换为显示坐标
  const [origX, origY, origW, origH] = ann.bbox
  const x = origX * displayScale
  const y = origY * displayScale
  const w = origW * displayScale
  const h = origH * displayScale

  const cat = categories.value.find(c => c.id === ann.category_id)
  const color = cat?.color || '#ff4444'

  ctx.strokeStyle = color
  ctx.lineWidth = selected ? 3 : 2
  ctx.strokeRect(x, y, w, h)

  // 绘制选择框的角点
  if (selected) {
    const cornerSize = 6
    ctx.fillStyle = color
    ctx.fillRect(x - 2, y - 2, cornerSize, cornerSize)
    ctx.fillRect(x + w - 4, y - 2, cornerSize, cornerSize)
    ctx.fillRect(x - 2, y + h - 4, cornerSize, cornerSize)
    ctx.fillRect(x + w - 4, y + h - 4, cornerSize, cornerSize)
  }

  // 绘制标签
  const labelHeight = 20
  const labelText = cat?.name || '未知'
  ctx.font = 'bold 12px sans-serif'
  const textWidth = ctx.measureText(labelText).width + 10
  ctx.fillStyle = color
  ctx.fillRect(x, y - labelHeight, textWidth, labelHeight)
  ctx.fillStyle = '#ffffff'
  ctx.fillText(labelText, x + 5, y - 5)
}

const handleMouseDown = (e: MouseEvent) => {
  if (!canvasRef.value) return

  const rect = canvasRef.value.getBoundingClientRect()
  const clickX = e.clientX - rect.left
  const clickY = e.clientY - rect.top

  // 检查是否点击在已有标注框上
  for (let i = 0; i < localAnnotations.value.length; i++) {
    const ann = localAnnotations.value[i]
    const [origX, origY, origW, origH] = ann.bbox
    const x = origX * displayScale
    const y = origY * displayScale
    const w = origW * displayScale
    const h = origH * displayScale

    if (clickX >= x && clickX <= x + w && clickY >= y && clickY <= y + h) {
      // 点击在已有标注上，选中它
      selectedAnnotationIndex.value = i
      drawAllBboxes()
      return
    }
  }

  // 点击空白区域，开始绘制新标注
  if (!selectedCategoryId.value) {
    ElMessage.warning('请先选择类别')
    return
  }

  isDrawing = true
  startX = clickX
  startY = clickY
}

const handleMouseMove = (e: MouseEvent) => {
  if (!isDrawing || !ctx || !canvasRef.value) return

  const rect = canvasRef.value.getBoundingClientRect()
  const currentX = e.clientX - rect.left
  const currentY = e.clientY - rect.top

  drawAllBboxes()

  const cat = categories.value.find(c => c.id === selectedCategoryId.value)
  const color = cat?.color || '#ff4444'

  // 绘制预览框（实线 + 半透明填充）
  const x = Math.min(startX, currentX)
  const y = Math.min(startY, currentY)
  const w = Math.abs(currentX - startX)
  const h = Math.abs(currentY - startY)

  // 半透明填充
  ctx.fillStyle = `${color  }40`  // 40 = 25% opacity
  ctx.fillRect(x, y, w, h)

  // 实线边框
  ctx.strokeStyle = color
  ctx.lineWidth = 3
  ctx.strokeRect(x, y, w, h)

  // 绘制尺寸标签
  const labelText = `${Math.round(w / displayScale)} × ${Math.round(h / displayScale)}`
  ctx.font = 'bold 14px JetBrains Mono, monospace'
  const textMetrics = ctx.measureText(labelText)
  const labelPadding = 6
  const labelHeight = 22

  ctx.fillStyle = color
  ctx.fillRect(x, y - labelHeight - 4, textMetrics.width + labelPadding * 2, labelHeight)
  ctx.fillStyle = '#ffffff'
  ctx.fillText(labelText, x + labelPadding, y - 10)
}

const handleMouseUp = (e: MouseEvent) => {
  if (!isDrawing || !canvasRef.value) return

  const rect = canvasRef.value.getBoundingClientRect()
  const endX = e.clientX - rect.left
  const endY = e.clientY - rect.top

  const canvasX = Math.min(startX, endX)
  const canvasY = Math.min(startY, endY)
  const canvasW = Math.abs(endX - startX)
  const canvasH = Math.abs(endY - startY)

  if (canvasW > 10 && canvasH > 10) {
    // 转换为原始图片坐标
    const origX = canvasX / displayScale
    const origY = canvasY / displayScale
    const origW = canvasW / displayScale
    const origH = canvasH / displayScale

    localAnnotations.value.push({
      image_id: currentImage.value!.id,
      category_id: selectedCategoryId.value!,
      bbox: [origX, origY, origW, origH]
    })

    selectedAnnotationIndex.value = localAnnotations.value.length - 1
    drawAllBboxes()
  }

  isDrawing = false
}

const selectAnnotation = (index: number) => {
  selectedAnnotationIndex.value = index
  drawAllBboxes()
}

const getCategoryColor = (id: number) => {
  const cat = flatCategories.value.find(c => c.id === id)
  return cat?.color || '#ff4444'
}

const getCategoryName = (id: number) => {
  const cat = flatCategories.value.find(c => c.id === id)
  return cat?.name || '未知'
}

const removeAnnotation = (index: number) => {
  localAnnotations.value.splice(index, 1)
  if (selectedAnnotationIndex.value === index) {
    selectedAnnotationIndex.value = null
  } else if (selectedAnnotationIndex.value !== null && selectedAnnotationIndex.value > index) {
    selectedAnnotationIndex.value--
  }
  drawAllBboxes()
}

const saveAnnotations = async () => {
  if (!currentImage.value) return

  saving.value = true
  try {
    for (const ann of localAnnotations.value) {
      if (!ann.id) {
        await annotationApi.create({
          image_id: ann.image_id,
          category_id: ann.category_id,
          bbox: ann.bbox
        })
      }
    }
    ElMessage.success('保存成功')
    await loadAnnotations(currentImage.value.id)
    await loadImageList()  // 刷新标注进度
    drawAllBboxes()
  } catch (error: unknown) {
    const msg = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '保存失败'
    ElMessage.error(msg)
  } finally {
    saving.value = false
  }
}

const handleCreateCategory = async () => {
  if (!categoryForm.value.name) {
    ElMessage.warning('请输入名称')
    return
  }

  creatingCategory.value = true
  try {
    await categoryApi.create({
      name: categoryForm.value.name,
      color: categoryForm.value.color,
      is_directory: categoryForm.value.is_directory,
      parent_id: categoryForm.value.parent_id
    })
    ElMessage.success(categoryForm.value.is_directory ? '目录创建成功' : '标签创建成功')
    closeCreateDialog()
    // 同时更新 categories 和 treeData
    await loadCategories()
  } catch (error: unknown) {
    const msg = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '创建失败'
    ElMessage.error(msg)
  } finally {
    creatingCategory.value = false
  }
}

const goBack = () => {
  if (currentImage.value?.atlas_id) {
    const query = route.query.directory ? { directory: route.query.directory as string } : {}
    router.push({ path: `/atlas/${currentImage.value.atlas_id}`, query })
  } else {
    router.push('/atlas')
  }
}

const prevImage = async () => {
  if (!hasPrev.value) return
  // 有未保存的标注则自动保存
  if (hasChanges.value) {
    await saveAnnotations()
  }
  const newId = imageList.value[currentImageIndex.value - 1].id
  const query: Record<string, string> = route.query.directory ? { directory: route.query.directory as string } : {}
  query.sort_by = route.query.sort_by as string || 'created_at'
  query.sort_order = route.query.sort_order as string || 'desc'
  router.push({ path: `/annotate/${newId}`, query })
}

const nextImage = async () => {
  if (!hasNext.value) return
  // 有未保存的标注则自动保存
  if (hasChanges.value) {
    await saveAnnotations()
  }
  const newId = imageList.value[currentImageIndex.value + 1].id
  const query: Record<string, string> = route.query.directory ? { directory: route.query.directory as string } : {}
  query.sort_by = route.query.sort_by as string || 'created_at'
  query.sort_order = route.query.sort_order as string || 'desc'
  router.push({ path: `/annotate/${newId}`, query })
}

const handleKeyDown = (e: KeyboardEvent) => {
  if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return

  if (e.key.toLowerCase() === 's') {
    e.preventDefault()
    saveAnnotations()
  }

  if (e.key.toLowerCase() === 'z') {
    e.preventDefault()
    if (localAnnotations.value.length > 0) {
      const lastIndex = localAnnotations.value.length - 1
      if (!localAnnotations.value[lastIndex].id) {
        localAnnotations.value.splice(lastIndex, 1)
        drawAllBboxes()
      }
    }
  }

  if (e.key === 'ArrowLeft' || e.key.toLowerCase() === 'a') {
    prevImage()
  }

  if (e.key === 'ArrowRight' || e.key.toLowerCase() === 'd') {
    nextImage()
  }

  if (e.key === 'Delete' && selectedAnnotationIndex.value !== null) {
    e.preventDefault()
    removeAnnotation(selectedAnnotationIndex.value)
  }
}

watch(image_id, (newId) => {
  if (newId) {
    loadImage(newId).then(() => {
      loadImageList()
    })
  }
})

onMounted(() => {
  loadCategories()
  if (route.params.image_id) {
    loadImage(Number(route.params.image_id)).then(() => {
      loadImageList()
    })
  }
  window.addEventListener('keydown', handleKeyDown)
  window.addEventListener('click', closeHeaderMenu)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyDown)
  window.removeEventListener('click', closeHeaderMenu)
})
</script>

<style lang="scss" scoped>
.toolbar {
  @apply flex justify-between items-center;
  padding: 8px 16px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
}

.toolbar-left,
.toolbar-right {
  @apply flex items-center gap-3;
}

.toolbar-center {
  @apply flex items-center;
}

.image-nav {
  @apply flex items-center gap-1;
}

.nav-info {
  font-family: 'JetBrains Mono', monospace;
  @apply text-sm text-[var(--accent-blue)] px-3 py-1 rounded;
  background: rgba(0, 240, 255, 0.1);
}

.hotkey-hints {
  @apply flex gap-4;
}

/* 标注进度 */
.progress-stats {
  @apply flex items-center gap-2 ml-4 pl-4;
  border-left: 1px solid var(--border-color);
}

.stat-item {
  @apply flex items-center gap-1;
}

.stat-label {
  @apply text-xs text-[var(--text-muted)];
}

.stat-value {
  font-family: 'JetBrains Mono', monospace;
  @apply text-sm font-bold text-[var(--text-primary)];
}

.stat-value.done {
  @apply text-[var(--color-success)];
}

.stat-sep {
  @apply text-xs text-[var(--text-muted)];
}

.stat-bar {
  @apply w-16 h-1.5 rounded-full overflow-hidden;
  background: var(--bg-primary);
}

.stat-fill {
  @apply h-full rounded-full transition-all duration-500;
  background: linear-gradient(90deg, var(--accent-blue), var(--accent-blue));
}

.stat-pct {
  @apply text-xs font-mono font-semibold min-w-[2.5em] text-right;
  @apply text-[var(--accent-blue)];
  transition: color 0.3s;
}

.stat-pct.done {
  @apply text-[var(--color-success)];
}

.hint {
  @apply text-xs text-[var(--text-muted)];
}

.hint kbd {
  @apply inline-block px-1.5 py-0.5 rounded;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  font-family: 'JetBrains Mono', monospace;
  @apply text-[11px] text-[var(--text-secondary)] mr-1;
}

.content-area {
  @apply flex flex-1 overflow-hidden;
}

.category-panel {
  @apply flex flex-col;
  width: clamp(160px, 15vw, 240px);
  min-width: 160px;
  background: var(--bg-secondary);
  border-right: 1px solid var(--border-color);
  flex-shrink: 0;
}

.panel-header {
  @apply flex justify-between items-center p-3;
  border-bottom: 1px solid var(--border-color);

  h3 {
    @apply text-sm font-medium text-[var(--text-primary)];
  }
}

.category-list {
  @apply flex-1 overflow-y-auto p-2;
}

.category-item {
  @apply flex items-center gap-2.5 p-2.5 rounded-md cursor-pointer transition-all border border-transparent;
}

.category-item:hover {
  @apply bg-[var(--bg-hover)];
}

.category-item.active {
  background: rgba(0, 240, 255, 0.1);
  @apply border-[var(--accent-blue)];
}

.cat-color {
  @apply w-3 h-3 rounded flex-shrink-0;
}

.cat-name {
  @apply flex-1 text-sm text-[var(--text-primary)];
}

.cat-hotkey {
  font-family: 'JetBrains Mono', monospace;
  @apply text-[11px] text-[var(--text-muted)] px-1.5 py-0.5 rounded;
  background: var(--bg-primary);
}

// 面包屑导航
.breadcrumb {
  @apply flex items-center gap-1 px-3 py-1.5 text-xs;
  @apply bg-[var(--bg-primary)] border-b border-[var(--border-color)];
  flex-wrap: wrap;
}

.breadcrumb-item {
  @apply text-[var(--text-secondary)] cursor-pointer;
  @apply hover:text-[var(--accent-blue)];
}

.breadcrumb-item.active {
  @apply text-[var(--text-primary)] cursor-default;
  @apply hover:text-[var(--text-primary)];
}

.breadcrumb-sep {
  @apply w-3 h-3 text-[var(--text-muted)];
}

.current-tag {
  @apply px-2 py-0.5 rounded text-white text-[11px] font-medium;
}

// 目录列表
.dir-list {
  @apply p-1.5;
}

.dir-item {
  @apply flex items-center gap-2 p-1.5 rounded-md cursor-pointer;
  @apply text-sm text-[var(--color-warning)];
}

.dir-item:hover {
  @apply bg-[var(--bg-hover)];
}

.dir-icon {
  @apply w-4 h-4 flex-shrink-0;
}

.dir-name {
  @apply flex-1 truncate;
}

.enter-icon {
  @apply w-4 h-4 text-[var(--text-muted)];
}

.item-actions {
  @apply flex items-center gap-1;
  opacity: 0;
  transition: opacity 0.2s;
}

.dir-item:hover .item-actions,
.tag-item:hover .item-actions {
  opacity: 1;
}

.item-actions .icon-btn {
  @apply w-5 h-5 p-0.5;
}

.item-actions .icon-btn svg {
  @apply w-full h-full;
}

// 标签列表
.tag-list {
  @apply p-1.5;
  border-top: 1px solid var(--border-color);
}

.tag-header {
  @apply px-2 py-1 text-xs text-[var(--text-muted)] uppercase tracking-wide;
}

.tag-item {
  @apply flex items-center gap-2 p-1.5 rounded-md cursor-pointer;
  @apply text-sm text-[var(--text-primary)];
  @apply border border-transparent;
}

.tag-item:hover {
  @apply bg-[var(--bg-hover)];
}

.tag-item.active {
  background: rgba(0, 240, 255, 0.1);
  @apply border-[var(--accent-blue)];
}

.tag-color {
  @apply w-3 h-3 rounded flex-shrink-0;
}

.tag-name {
  @apply flex-1 truncate;
}

.tag-hotkey {
  font-family: 'JetBrains Mono', monospace;
  @apply text-[10px] text-[var(--text-muted)] px-1.5 py-0.5 rounded;
  background: var(--bg-primary);
}

.canvas-container {
  @apply flex items-center justify-center relative overflow-hidden;
  flex: 1;
  background: var(--bg-primary);
}

.canvas-container canvas {
  cursor: crosshair;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.4);
  background: #1a1a24;
}

.canvas-loading {
  @apply absolute inset-0 flex flex-col items-center justify-center;
  background: rgba(0, 0, 0, 0.7);
  @apply gap-4;
}

.loading-spinner {
  @apply w-10 h-10 rounded-full;
  border: 3px solid var(--border-color);
  border-top-color: var(--accent-blue);
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.canvas-overlay {
  @apply absolute inset-0 flex items-center justify-center;
  background: rgba(0, 0, 0, 0.5);
}

.no-image {
  @apply text-base text-[var(--text-muted)];
}

.annotation-panel {
  @apply flex flex-col;
  width: clamp(200px, 18vw, 280px);
  min-width: 200px;
  background: var(--bg-secondary);
  border-left: 1px solid var(--border-color);
  flex-shrink: 0;
}

.annotation-list {
  @apply flex-1 overflow-y-auto;
  padding: var(--spacing-xs);
}

.annotation-item {
  @apply flex items-center gap-2 p-2 rounded-lg cursor-pointer transition-all border border-transparent;
  margin-bottom: 4px;

  // Figma Design: 轻微背景区分，未选中项也有层次感
  &:hover {
    background: var(--bg-hover);
  }

  &.selected {
    background: rgba(0, 240, 255, 0.08);
    border-color: rgba(0, 240, 255, 0.4);
  }

  &.pending {
    opacity: 0.65;
  }
}

.ann-color {
  @apply w-3 h-3 rounded-sm flex-shrink-0;
  box-shadow: 0 0 4px currentColor;  // 颜色点带微发光
}

.ann-name {
  @apply flex-1 text-sm text-[var(--text-primary)] font-medium;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ann-bbox {
  font-family: var(--font-family-mono);
  font-size: 12px;        // Figma: caption = 12px，不再是 10px
  font-weight: 400;
  color: var(--text-secondary);  // 从 muted → secondary，对比度提升
  letter-spacing: 0.30px;  // Figma caption letter-spacing
  flex-shrink: 0;
  text-transform: uppercase;  // Figma caption 规范
}

.ann-actions {
  @apply flex gap-1;
  flex-shrink: 0;
}

.icon-btn {
  @apply w-7 h-7 flex items-center justify-center bg-transparent border-none cursor-pointer rounded-lg transition-all;
  color: var(--text-muted);

  &:hover {
    background: rgba(255, 68, 102, 0.15);
    color: var(--color-danger);
  }

  svg {
    @apply w-3.5 h-3.5;
  }
}

.empty-tip {
  @apply p-5 text-center leading-relaxed;
  font-size: 14px;
  color: var(--text-muted);
}

/* 对话框 */
.dialog-overlay {
  @apply fixed inset-0 flex items-center justify-center;
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(4px);
  z-index: 1000;
}

.dialog-panel {
  width: clamp(320px, 90vw, 450px);
  max-width: 95vw;
  animation: dialogIn 0.2s ease;
}

@keyframes dialogIn {
  from {
    opacity: 0;
    transform: scale(0.95) translateY(-10px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

.dialog-header {
  @apply flex justify-between items-center p-4;
  border-bottom: 1px solid var(--border-color);

  h3 {
    @apply text-base font-semibold;
  }
}

.close-btn {
  @apply w-8 h-8 flex items-center justify-center bg-transparent border-none text-[var(--text-muted)] cursor-pointer rounded transition-all;
}

.close-btn:hover {
  @apply bg-[var(--bg-hover)] text-[var(--text-primary)];
}

.close-btn svg {
  @apply w-4 h-4;
}

.dialog-body {
  @apply p-4;
}

.form-group {
  @apply mb-4;

  label {
    @apply block text-xs text-[var(--text-secondary)] mb-1.5 uppercase tracking-wide;
  }

  input {
    @apply w-full px-3 py-2.5 bg-[var(--bg-primary)] border border-[var(--border-color)] rounded text-sm text-[var(--text-primary)];
  }

  input:focus {
    @apply outline-none border-[var(--accent-blue)];
  }
}

.color-picker {
  @apply flex items-center gap-3;
}

.color-picker input[type="color"] {
  @apply w-10 h-8 p-0 border border-[var(--border-color)] rounded cursor-pointer;
}

.color-preview {
  @apply w-8 h-8 rounded border border-[var(--border-color)];
}

.type-toggle {
  @apply flex gap-2;
}

.toggle-btn {
  @apply flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded border border-[var(--border-color)] text-sm cursor-pointer transition-all;
  @apply text-[var(--text-secondary)] bg-[var(--bg-primary)];

  svg {
    @apply w-4 h-4;
  }
}

.toggle-btn:hover {
  @apply border-[var(--accent-blue)] text-[var(--text-primary)];
}

.toggle-btn.active {
  @apply border-[var(--accent-blue)] bg-[rgba(88,152,255,0.1)] text-[var(--accent-blue)];
}

.parent-path {
  @apply text-sm text-[var(--text-muted)] py-2;
}

.dialog-footer {
  @apply flex justify-end gap-2 p-3;
  border-top: 1px solid var(--border-color);
}

/* 下拉菜单样式 */
.header-dropdown {
  position: relative;
}

.dropdown-menu {
  position: absolute;
  top: 100%;
  right: 0;
  z-index: 100;
  min-width: 140px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 4px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
  animation: dialogIn 0.15s ease;
}

.dropdown-item {
  @apply flex items-center gap-2 px-3 py-2 rounded text-sm cursor-pointer;
  color: var(--text-secondary);
  transition: all 0.15s;
}

.dropdown-item:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.dropdown-item svg {
  @apply w-4 h-4;
}

.dropdown-divider {
  height: 1px;
  background: var(--border-color);
  margin: 4px 8px;
}

/* 导入导出样式 */
.import-dropzone {
  @apply flex flex-col items-center gap-2 p-8 rounded-lg cursor-pointer border-2 border-dashed;
  border-color: var(--border-color);
  background: var(--bg-primary);
  transition: all 0.2s;
}

.import-dropzone:hover {
  border-color: var(--accent-blue);
  background: rgba(0, 240, 255, 0.05);
}

.import-dropzone svg {
  @apply w-8 h-8 text-[var(--text-muted)];
}

.import-hint {
  @apply text-xs text-[var(--text-muted)];
}

.import-preview {
  @apply space-y-3;
}

.preview-stats {
  @apply flex gap-4;
}

.preview-stat {
  @apply flex flex-col items-center p-3 rounded-lg;
  background: var(--bg-primary);
  flex: 1;
}

.preview-stat .stat-count {
  @apply text-xl font-bold font-mono;
  color: var(--accent-blue);
}

.preview-stat .stat-label {
  @apply text-xs text-[var(--text-muted)] uppercase tracking-wide;
}

.preview-tree {
  @apply space-y-1 max-h-48 overflow-y-auto p-2 rounded;
  background: var(--bg-primary);
}

.preview-node {
  @apply flex items-center gap-2 text-sm p-1.5;
}

.preview-node svg {
  @apply w-4 h-4;
}

.node-count {
  @apply text-xs text-[var(--text-muted)];
}

.import-error {
  @apply text-sm p-2 rounded;
  color: var(--color-danger);
  background: rgba(255, 68, 102, 0.1);
}

</style>
