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
        <span class="atlas-desc">{{ atlas?.description || '无描述' }}</span>
      </div>
      <button class="vg-btn vg-btn-primary" @click="triggerUpload">
        <UploadIcon />
        上传图片
      </button>
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
              <span class="count">{{ images.length }}</span>
            </button>
            <button class="tab-btn" :class="{ active: activeTab === 'directories' }" @click="activeTab = 'directories'">
              <FolderIcon />
              目录管理
              <span class="count">{{ directories.length }}</span>
            </button>
          </div>
          <div class="header-actions" v-if="activeTab === 'images'">
            <div class="select-wrapper">
              <select v-model="selectedDirectory" @change="loadImages">
                <option value="">全部目录</option>
                <option v-for="dir in directories" :key="dir" :value="dir">{{ dir }}</option>
              </select>
            </div>
            <button class="action-btn" @click="loadImages">
              <RefreshIcon />
            </button>
          </div>
        </div>

        <!-- 图片列表 -->
        <div class="images-content" v-if="activeTab === 'images'">
          <div class="images-grid" v-loading="loadingImages">
            <div class="image-card" v-for="img in images" :key="img.id">
              <div class="image-wrapper" @click="openImageDialog(img)">
                <img :src="getImageUrl(img.file_path)" :alt="getFileName(img.file_path)" />
                <div class="image-overlay">
                  <span class="overlay-icon">
                    <EyeIcon />
                  </span>
                </div>
                <span class="annotated-badge" v-if="img.annotated">已标注</span>
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
              <span class="info-value">{{ images.length }}</span>
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
              <span class="meta-value">{{ selectedImage.directory || '根目录' }}</span>
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
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { atlasApi, imageApi } from '@/api'

const route = useRoute()
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

const annotatedCount = computed(() => images.value.filter(img => img.annotated).length)

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
    console.log('[DEBUG] loadImages called, directory:', directory)
    const res = await atlasApi.getImages(id, directory)
    console.log('[DEBUG] getImages response, count:', res.data.length)
    images.value = res.data
  } catch (error) {
    ElMessage.error('加载图片失败')
    console.error('[DEBUG] loadImages error:', error)
  } finally {
    loadingImages.value = false
  }
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

const handleDeleteDirectory = (dir: string) => {
  ElMessage.warning(`删除目录 "${dir}" 功能待实现`)
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
  loadAtlas()
  loadImages()
  loadDirectories()
})
</script>

<style scoped>
.atlas-detail {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.page-header {
  display: flex;
  align-items: center;
  gap: 20px;
}

.back-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  color: var(--text-secondary);
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.back-btn:hover {
  border-color: var(--accent-cyan);
  color: var(--accent-cyan);
}

.back-btn svg {
  width: 18px;
  height: 18px;
}

.atlas-info {
  flex: 1;
}

.atlas-info h2 {
  font-size: 24px;
  font-weight: 600;
  background: linear-gradient(90deg, var(--text-primary), var(--accent-cyan));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.atlas-desc {
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

/* 内容网格 */
.content-grid {
  display: grid;
  grid-template-columns: 1fr 300px;
  gap: 24px;
}

/* 面板头部 */
.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-color);
}

.tabs {
  display: flex;
  gap: 8px;
}

.tab-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 8px;
  color: var(--text-secondary);
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.tab-btn svg {
  width: 18px;
  height: 18px;
}

.tab-btn:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.tab-btn.active {
  background: rgba(0, 240, 255, 0.1);
  border-color: rgba(0, 240, 255, 0.3);
  color: var(--accent-cyan);
}

.tab-btn .count {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  padding: 2px 6px;
  background: var(--bg-secondary);
  border-radius: 4px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.select-wrapper {
  position: relative;
}

.select-wrapper select {
  padding: 8px 36px 8px 14px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: var(--text-primary);
  font-size: 13px;
  cursor: pointer;
  appearance: none;
}

.select-wrapper select:focus {
  outline: none;
  border-color: var(--accent-cyan);
}

.select-wrapper::after {
  content: '';
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  border-left: 4px solid transparent;
  border-right: 4px solid transparent;
  border-top: 4px solid var(--text-muted);
  pointer-events: none;
}

.action-btn {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s ease;
}

.action-btn:hover {
  border-color: var(--accent-cyan);
  color: var(--accent-cyan);
}

.action-btn svg {
  width: 16px;
  height: 16px;
}

.action-btn.danger:hover {
  border-color: #ff4466;
  color: #ff4466;
}

/* 图片网格 */
.images-content {
  padding: 20px;
}

.images-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 16px;
}

.image-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.3s ease;
}

.image-card:hover {
  border-color: var(--accent-cyan);
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 240, 255, 0.15);
}

.image-wrapper {
  position: relative;
  aspect-ratio: 1;
  overflow: hidden;
}

.image-wrapper img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.image-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.2s ease;
}

.image-card:hover .image-overlay {
  opacity: 1;
}

.overlay-icon {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--accent-cyan);
  border-radius: 50%;
  color: var(--bg-primary);
}

.overlay-icon svg {
  width: 20px;
  height: 20px;
}

.annotated-badge {
  position: absolute;
  top: 8px;
  left: 8px;
  padding: 4px 8px;
  background: var(--accent-green);
  border-radius: 4px;
  font-size: 10px;
  font-weight: 600;
  color: var(--bg-primary);
}

.delete-btn {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 68, 102, 0.9);
  border: none;
  border-radius: 6px;
  color: white;
  cursor: pointer;
  opacity: 0;
  transition: all 0.2s ease;
}

.delete-btn svg {
  width: 14px;
  height: 14px;
}

.image-card:hover .delete-btn {
  opacity: 1;
}

.delete-btn:hover {
  background: #ff4466;
  transform: scale(1.1);
}

.image-info {
  padding: 12px;
}

.image-name {
  display: block;
  font-size: 12px;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.image-dir {
  display: block;
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 4px;
}

/* 目录管理 */
.directories-content {
  padding: 20px;
}

.create-dir-section {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
}

.input-group {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 14px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
}

.input-icon {
  width: 18px;
  height: 18px;
  color: var(--text-muted);
}

.input-group input {
  flex: 1;
  padding: 12px 0;
  background: transparent;
  border: none;
  color: var(--text-primary);
  font-size: 14px;
}

.input-group input:focus {
  outline: none;
}

.input-group input::placeholder {
  color: var(--text-muted);
}

.directories-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.dir-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  transition: all 0.2s ease;
}

.dir-item:hover {
  border-color: var(--accent-cyan);
}

.dir-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.dir-icon {
  width: 22px;
  height: 22px;
  color: var(--accent-yellow);
}

.dir-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
}

.dir-actions {
  display: flex;
  gap: 8px;
}

/* 侧边栏 */
.side-panel {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.info-card .card-header {
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-color);
}

.info-card .card-header h4 {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.info-list {
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.info-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.info-label {
  font-size: 13px;
  color: var(--text-muted);
}

.info-value {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
}

.info-value.id {
  font-family: 'JetBrains Mono', monospace;
  color: var(--accent-cyan);
}

.info-value.success {
  color: var(--accent-green);
}

/* 上传提示 */
.upload-tip {
  background: linear-gradient(135deg, rgba(0, 240, 255, 0.05), rgba(255, 0, 170, 0.05));
}

.tip-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-color);
  font-size: 14px;
  font-weight: 600;
  color: var(--accent-yellow);
}

.tip-header svg {
  width: 18px;
  height: 18px;
}

.tip-list {
  padding: 16px 20px;
  margin: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.tip-list li {
  font-size: 13px;
  color: var(--text-secondary);
  padding-left: 16px;
  position: relative;
}

.tip-list li::before {
  content: '›';
  position: absolute;
  left: 0;
  color: var(--accent-cyan);
}

/* 空状态 */
.empty-state {
  padding: 60px 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.empty-icon {
  width: 64px;
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-secondary);
  border-radius: 16px;
  margin-bottom: 16px;
  color: var(--text-muted);
  opacity: 0.5;
}

.empty-icon svg {
  width: 32px;
  height: 32px;
}

.empty-state p {
  font-size: 16px;
  color: var(--text-secondary);
  margin-bottom: 6px;
}

.empty-state span {
  font-size: 13px;
  color: var(--text-muted);
}

/* 对话框 */
.dialog-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.8);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.dialog-panel {
  width: 600px;
  max-width: 90vw;
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

.dialog-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

:deep(.el-button--text) {
  padding: 4px 0;
  border: none;
  background: transparent;
  color: #ff4466;
  font-size: 13px;
}

:deep(.el-button--text:hover) {
  color: #ff4466;
  background: transparent;
  border: none;
}

.close-btn {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  border-radius: 8px;
  transition: all 0.2s ease;
}

.close-btn:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.close-btn svg {
  width: 20px;
  height: 20px;
}

.dialog-content {
  padding: 24px;
}

.image-preview {
  background: var(--bg-secondary);
  border-radius: 12px;
  overflow: hidden;
  margin-bottom: 20px;
}

.image-preview img {
  width: 100%;
  max-height: 400px;
  object-fit: contain;
}

.image-meta {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.meta-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 14px;
  background: var(--bg-secondary);
  border-radius: 8px;
}

.meta-label {
  font-size: 13px;
  color: var(--text-muted);
}

.meta-value {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
}

.status-tag {
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

.status-tag.annotated {
  background: rgba(0, 255, 136, 0.15);
  color: var(--accent-green);
}

.status-tag.pending {
  background: rgba(136, 136, 170, 0.15);
  color: var(--text-muted);
}
</style>
