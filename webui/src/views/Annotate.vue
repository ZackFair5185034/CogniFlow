<template>
  <div class="annotate-page">
    <!-- 顶部工具栏 -->
    <div class="toolbar">
      <div class="toolbar-left">
        <button class="vg-btn" @click="goBack">
          <ArrowLeftIcon />
          返回
        </button>
        <div class="image-nav" v-if="currentImage">
          <button class="vg-btn" @click="prevImage" :disabled="!hasPrev">
            <ChevronLeftIcon />
          </button>
          <span class="nav-info">#{{ currentImage.id }}</span>
          <button class="vg-btn" @click="nextImage" :disabled="!hasNext">
            <ChevronRightIcon />
          </button>
        </div>
      </div>
      <div class="toolbar-center">
        <div class="hotkey-hints">
          <span class="hint"><kbd>1-9</kbd> 选择类别</span>
          <span class="hint"><kbd>S</kbd> 保存</span>
          <span class="hint"><kbd>Z</kbd> 撤销</span>
          <span class="hint"><kbd>←→</kbd> 翻页</span>
        </div>
      </div>
      <div class="toolbar-right">
        <button class="vg-btn vg-btn-primary" @click="saveAnnotations" :disabled="!hasChanges || saving">
          <SaveIcon />
          {{ saving ? '保存中...' : '保存 (S)' }}
        </button>
      </div>
    </div>

    <!-- 主内容区 -->
    <div class="content-area">
      <!-- 左侧类别面板 -->
      <div class="category-panel">
        <div class="panel-header">
          <h3>类别库</h3>
          <button class="vg-btn vg-btn-small" @click="showCategoryDialog = true">
            <PlusIcon />
          </button>
        </div>
        <div class="category-list">
          <div
            v-for="(cat, index) in categories"
            :key="cat.id"
            class="category-item"
            :class="{ active: selectedCategoryId === cat.id }"
            :style="{ '--cat-color': cat.color }"
            @click="selectCategory(cat.id)"
          >
            <span class="cat-color" :style="{ background: cat.color }"></span>
            <span class="cat-name">{{ cat.name }}</span>
            <span class="cat-hotkey">{{ index + 1 }}</span>
          </div>
        </div>
        <div v-if="categories.length === 0" class="empty-tip">
          暂无类别，请先创建
        </div>
      </div>

      <!-- 画布区域 -->
      <div class="canvas-container" ref="canvasContainer">
        <canvas
          ref="canvasRef"
          @mousedown="handleMouseDown"
          @mousemove="handleMouseMove"
          @mouseup="handleMouseUp"
          @mouseleave="handleMouseUp"
        ></canvas>
        <div class="canvas-loading" v-if="imageLoading">
          <div class="loading-spinner"></div>
          <span>加载图片中...</span>
        </div>
        <div class="canvas-overlay" v-if="!currentImage && !imageLoading">
          <div class="no-image">请先选择图片</div>
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
            <span class="ann-color" :style="{ background: getCategoryColor(ann.category_id) }"></span>
            <span class="ann-name">{{ getCategoryName(ann.category_id) }}</span>
            <span class="ann-bbox">[{{ formatBbox(ann.bbox) }}]</span>
            <div class="ann-actions">
              <button class="icon-btn" @click.stop="removeAnnotation(index)" title="删除">
                <TrashIcon />
              </button>
            </div>
          </div>
        </div>
        <div v-if="localAnnotations.length === 0" class="empty-tip">
          暂无标注<br/>在画布上拖拽绘制框
        </div>
      </div>
    </div>

    <!-- 创建类别对话框 -->
    <div class="dialog-overlay" v-if="showCategoryDialog" @click.self="showCategoryDialog = false">
      <div class="dialog-panel vg-card">
        <div class="dialog-header">
          <h3>创建类别</h3>
          <button class="close-btn" @click="showCategoryDialog = false">
            <CloseIcon />
          </button>
        </div>
        <div class="dialog-body">
          <div class="form-group">
            <label>类别名称</label>
            <input type="text" v-model="categoryForm.name" placeholder="输入类别名称" />
          </div>
          <div class="form-group">
            <label>颜色</label>
            <div class="color-picker">
              <input type="color" v-model="categoryForm.color" />
              <span class="color-preview" :style="{ background: categoryForm.color }"></span>
            </div>
          </div>
        </div>
        <div class="dialog-footer">
          <button class="vg-btn" @click="showCategoryDialog = false">取消</button>
          <button class="vg-btn vg-btn-primary" @click="handleCreateCategory" :disabled="creatingCategory">
            {{ creatingCategory ? '创建中...' : '创建' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, computed, nextTick, h } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { categoryApi, annotationApi, atlasApi } from '@/api'

interface Category {
  id: number
  name: string
  color: string
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
}

const route = useRoute()
const router = useRouter()

const canvasRef = ref<HTMLCanvasElement | null>(null)
const canvasContainer = ref<HTMLDivElement | null>(null)

const categories = ref<Category[]>([])
const currentImage = ref<ImageData | null>(null)
const localAnnotations = ref<Annotation[]>([])
const selectedCategoryId = ref<number | null>(null)
const selectedAnnotationIndex = ref<number | null>(null)

const imageLoading = ref(false)
const saving = ref(false)
const showCategoryDialog = ref(false)
const creatingCategory = ref(false)
const categoryForm = ref({ name: '', color: '#ff4444' })

const imageList = ref<ImageData[]>([])
const currentImageIndex = ref(0)

const hasPrev = computed(() => currentImageIndex.value > 0)
const hasNext = computed(() => currentImageIndex.value < imageList.value.length - 1)
const hasChanges = computed(() => {
  return localAnnotations.value.some(ann => !ann.id)
})

let ctx: CanvasRenderingContext2D | null = null
let isDrawing = false
let startX = 0
let startY = 0
let imgElement: HTMLImageElement | null = null
let originalWidth = 0
let originalHeight = 0
let displayScale = 1

const image_id = computed(() => Number(route.params.image_id))

// 图标组件
const ArrowLeftIcon = () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
  h('line', { x1: '19', y1: '12', x2: '5', y2: '12' }),
  h('polyline', { points: '12 19 5 12 12 5' })
])

const ChevronLeftIcon = () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
  h('polyline', { points: '15 18 9 12 15 6' })
])

const ChevronRightIcon = () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
  h('polyline', { points: '9 18 15 12 9 6' })
])

const PlusIcon = () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
  h('line', { x1: '12', y1: '5', x2: '12', y2: '19' }),
  h('line', { x1: '5', y1: '12', x2: '19', y2: '12' })
])

const SaveIcon = () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
  h('path', { d: 'M19 21H5a2 2 0 01-2-2V5a2 2 0 012-2h11l5 5v11a2 2 0 01-2 2z' }),
  h('polyline', { points: '17 21 17 13 7 13 7 21' }),
  h('polyline', { points: '7 3 7 8 15 8' })
])

const TrashIcon = () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
  h('polyline', { points: '3 6 5 6 21 6' }),
  h('path', { d: 'M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2' })
])

const CloseIcon = () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
  h('line', { x1: '18', y1: '6', x2: '6', y2: '18' }),
  h('line', { x1: '6', y1: '6', x2: '18', y2: '18' })
])

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
    if (categories.value.length > 0 && !selectedCategoryId.value) {
      selectedCategoryId.value = categories.value[0].id
    }
  } catch (error) {
    ElMessage.error('加载类别失败')
  }
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
    localAnnotations.value = res.data.map((ann: any) => ({
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
    const res = await atlasApi.getImages(currentImage.value.atlas_id)
    imageList.value = res.data || []
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
    originalWidth = img.width
    originalHeight = img.height

    const containerWidth = container.clientWidth - 40
    const containerHeight = container.clientHeight - 40

    displayScale = Math.min(
      containerWidth / img.width,
      containerHeight / img.height,
      1
    )

    canvas.width = img.width * displayScale
    canvas.height = img.height * displayScale

    ctx.drawImage(img, 0, 0, canvas.width, canvas.height)
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
  if (!selectedCategoryId.value) {
    ElMessage.warning('请先选择类别')
    return
  }
  if (!canvasRef.value) return

  const rect = canvasRef.value.getBoundingClientRect()
  isDrawing = true
  startX = e.clientX - rect.left
  startY = e.clientY - rect.top
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
  ctx.fillStyle = color + '40'  // 40 = 25% opacity
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

const selectCategory = (id: number) => {
  selectedCategoryId.value = id
}

const selectAnnotation = (index: number) => {
  selectedAnnotationIndex.value = index
  drawAllBboxes()
}

const getCategoryColor = (id: number) => {
  return categories.value.find(c => c.id === id)?.color || '#ff4444'
}

const getCategoryName = (id: number) => {
  return categories.value.find(c => c.id === id)?.name || '未知'
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
    drawAllBboxes()
  } catch (error: any) {
    const msg = error.response?.data?.detail || '保存失败'
    ElMessage.error(msg)
  } finally {
    saving.value = false
  }
}

const handleCreateCategory = async () => {
  if (!categoryForm.value.name) {
    ElMessage.warning('请输入类别名称')
    return
  }

  creatingCategory.value = true
  try {
    await categoryApi.create(categoryForm.value)
    ElMessage.success('创建成功')
    showCategoryDialog.value = false
    categoryForm.value = { name: '', color: '#ff4444' }
    await loadCategories()
  } catch (error: any) {
    const msg = error.response?.data?.detail || '创建失败'
    ElMessage.error(msg)
  } finally {
    creatingCategory.value = false
  }
}

const goBack = () => {
  router.back()
}

const prevImage = () => {
  if (hasPrev.value) {
    const newId = imageList.value[currentImageIndex.value - 1].id
    router.push(`/annotate/${newId}`)
  }
}

const nextImage = () => {
  if (hasNext.value) {
    const newId = imageList.value[currentImageIndex.value + 1].id
    router.push(`/annotate/${newId}`)
  }
}

const handleKeyDown = (e: KeyboardEvent) => {
  if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return

  if (e.key >= '1' && e.key <= '9') {
    const index = parseInt(e.key) - 1
    if (categories.value[index]) {
      selectedCategoryId.value = categories.value[index].id
    }
  }

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

  if (e.key === 'ArrowLeft') {
    prevImage()
  }

  if (e.key === 'ArrowRight') {
    nextImage()
  }
}

watch(image_id, (newId) => {
  if (newId) {
    loadImage(newId)
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
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyDown)
})
</script>

<style scoped>
.annotate-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 60px);
  background: var(--bg-primary);
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 20px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
}

.toolbar-left,
.toolbar-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.toolbar-center {
  display: flex;
  align-items: center;
}

.image-nav {
  display: flex;
  align-items: center;
  gap: 8px;
}

.nav-info {
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
  color: var(--accent-cyan);
  padding: 4px 12px;
  background: rgba(0, 240, 255, 0.1);
  border-radius: 4px;
}

.hotkey-hints {
  display: flex;
  gap: 20px;
}

.hint {
  font-size: 12px;
  color: var(--text-muted);
}

.hint kbd {
  display: inline-block;
  padding: 2px 6px;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  color: var(--text-secondary);
  margin-right: 4px;
}

.vg-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: var(--text-primary);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.vg-btn:hover:not(:disabled) {
  background: var(--bg-hover);
  border-color: var(--accent-cyan);
}

.vg-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.vg-btn svg {
  width: 16px;
  height: 16px;
}

.vg-btn-primary {
  background: var(--accent-cyan);
  border-color: var(--accent-cyan);
  color: #000;
}

.vg-btn-primary:hover:not(:disabled) {
  background: #00d4e0;
  border-color: #00d4e0;
}

.vg-btn-small {
  padding: 4px 8px;
}

.vg-btn-small svg {
  width: 14px;
  height: 14px;
}

.content-area {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.category-panel {
  width: 220px;
  background: var(--bg-secondary);
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border-bottom: 1px solid var(--border-color);
}

.panel-header h3 {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
}

.category-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.category-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
  border: 1px solid transparent;
}

.category-item:hover {
  background: var(--bg-hover);
}

.category-item.active {
  background: rgba(0, 240, 255, 0.1);
  border-color: var(--accent-cyan);
}

.cat-color {
  width: 12px;
  height: 12px;
  border-radius: 3px;
  flex-shrink: 0;
}

.cat-name {
  flex: 1;
  font-size: 13px;
  color: var(--text-primary);
}

.cat-hotkey {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  color: var(--text-muted);
  background: var(--bg-primary);
  padding: 2px 6px;
  border-radius: 4px;
}

.canvas-container {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-primary);
  position: relative;
  overflow: hidden;
  padding: 20px;
}

.canvas-container canvas {
  cursor: crosshair;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.4);
  background: #1a1a24;
}

.canvas-loading {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.7);
  gap: 16px;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--border-color);
  border-top-color: var(--accent-cyan);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.canvas-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.5);
}

.no-image {
  font-size: 16px;
  color: var(--text-muted);
}

.annotation-panel {
  width: 280px;
  background: var(--bg-secondary);
  border-left: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
}

.annotation-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.annotation-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
  border: 1px solid transparent;
}

.annotation-item:hover {
  background: var(--bg-hover);
}

.annotation-item.selected {
  background: rgba(0, 240, 255, 0.1);
  border-color: var(--accent-cyan);
}

.annotation-item.pending {
  opacity: 0.7;
}

.ann-color {
  width: 10px;
  height: 10px;
  border-radius: 2px;
  flex-shrink: 0;
}

.ann-name {
  flex: 1;
  font-size: 12px;
  color: var(--text-primary);
}

.ann-bbox {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  color: var(--text-muted);
}

.ann-actions {
  display: flex;
  gap: 4px;
}

.icon-btn {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  border-radius: 4px;
  transition: all 0.2s ease;
}

.icon-btn:hover {
  background: rgba(255, 68, 102, 0.2);
  color: #ff4466;
}

.icon-btn svg {
  width: 14px;
  height: 14px;
}

.empty-tip {
  padding: 20px;
  text-align: center;
  font-size: 13px;
  color: var(--text-muted);
  line-height: 1.6;
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
  width: 380px;
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
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-color);
}

.dialog-header h3 {
  font-size: 16px;
  font-weight: 600;
}

.close-btn {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  border-radius: 4px;
  transition: all 0.2s ease;
}

.close-btn:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.close-btn svg {
  width: 16px;
  height: 16px;
}

.dialog-body {
  padding: 20px;
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 6px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.form-group input {
  width: 100%;
  padding: 10px 12px;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: var(--text-primary);
  font-size: 14px;
}

.form-group input:focus {
  outline: none;
  border-color: var(--accent-cyan);
}

.color-picker {
  display: flex;
  align-items: center;
  gap: 12px;
}

.color-picker input[type="color"] {
  width: 40px;
  height: 32px;
  padding: 0;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  cursor: pointer;
}

.color-preview {
  width: 32px;
  height: 32px;
  border-radius: 4px;
  border: 1px solid var(--border-color);
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 16px 20px;
  border-top: 1px solid var(--border-color);
}
</style>
