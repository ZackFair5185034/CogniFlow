<template>
  <div class="atlas-detail">
    <el-button @click="$router.push('/atlas')" style="margin-bottom: 20px">返回列表</el-button>

    <el-card>
      <template #header>
        <div class="header-actions">
          <span>图集详情: {{ atlas?.name }}</span>
          <el-button type="primary" @click="triggerUpload">上传图片</el-button>
          <input ref="fileInputRef" type="file" accept="image/*" multiple style="display: none" @change="handleFileSelect" />
        </div>
      </template>

      <el-tabs v-model="activeTab">
        <el-tab-pane label="图片列表" name="images">
          <el-select v-model="selectedDirectory" placeholder="按目录筛选" clearable style="margin-bottom: 20px; width: 200px">
            <el-option v-for="dir in directories" :key="dir" :label="dir || '根目录'" :value="dir" />
          </el-select>
          <el-button @click="loadImages" size="small" style="margin-left: 10px">刷新</el-button>

          <el-row :gutter="10" v-loading="loadingImages">
            <el-col :span="4" v-for="img in images" :key="img.id">
              <el-card shadow="hover" class="image-card">
                <img :src="getImageUrl(img.file_path)" class="image-thumb" @click="openImageDialog(img)" />
                <div class="image-info">
                  <span class="image-name">{{ getFileName(img.file_path) }}</span>
                  <el-tag v-if="img.annotated" size="small" type="success">已标注</el-tag>
                </div>
              </el-card>
            </el-col>
          </el-row>

          <el-empty v-if="!loadingImages && images.length === 0" description="暂无图片" />
        </el-tab-pane>

        <el-tab-pane label="目录管理" name="directories">
          <el-space wrap>
            <el-tag v-for="dir in directories" :key="dir" closable @close="handleDeleteDir(dir)">
              {{ dir || '根目录' }}
            </el-tag>
          </el-space>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <el-dialog v-model="showImageDialog" title="图片详情" width="800px">
      <div v-if="selectedImage" class="image-detail">
        <img :src="getImageUrl(selectedImage.file_path)" class="image-preview" />
        <el-descriptions :column="2" border style="margin-top: 20px">
          <el-descriptions-item label="ID">{{ selectedImage.id }}</el-descriptions-item>
          <el-descriptions-item label="尺寸">{{ selectedImage.width }} x {{ selectedImage.height }}</el-descriptions-item>
          <el-descriptions-item label="目录">{{ selectedImage.directory || '根目录' }}</el-descriptions-item>
          <el-descriptions-item label="已标注">
            <el-tag :type="selectedImage.annotated ? 'success' : 'info'">
              {{ selectedImage.annotated ? '是' : '否' }}
            </el-tag>
          </el-descriptions-item>
        </el-descriptions>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { atlasApi } from '@/api'

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
    const params = selectedDirectory.value ? { directory: selectedDirectory.value } : {}
    const res = await atlasApi.getImages(id, params)
    images.value = res.data
  } catch (error) {
    ElMessage.error('加载图片失败')
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

const handleFileSelect = async (event: Event) => {
  const input = event.target as HTMLInputElement
  if (!input.files || input.files.length === 0) return

  const formData = new FormData()
  for (let i = 0; i < input.files.length; i++) {
    formData.append('files', input.files[i])
  }

  try {
    await atlasApi.uploadImages(id, formData)
    ElMessage.success('上传成功')
    loadImages()
    loadDirectories()
  } catch (error) {
    ElMessage.error('上传失败')
  }

  // 清空 input 以便再次选择相同文件
  input.value = ''
}

const getImageUrl = (filePath: string) => {
  return `file://${filePath.replace(/\\/g, '/')}`
}

const getFileName = (filePath: string) => {
  return filePath.split(/[\\/]/).pop() || ''
}

const handleDeleteDir = (dir: string) => {
  ElMessage.info('目录删除功能待实现')
}

watch(selectedDirectory, loadImages)

onMounted(() => {
  loadAtlas()
  loadImages()
  loadDirectories()
})
</script>

<style scoped>
.header-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.image-card {
  margin-bottom: 10px;
  cursor: pointer;
}
.image-thumb {
  width: 100%;
  height: 120px;
  object-fit: cover;
}
.image-info {
  margin-top: 8px;
  text-align: center;
}
.image-name {
  display: block;
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.image-preview {
  max-width: 100%;
  max-height: 500px;
  display: block;
  margin: 0 auto;
}
</style>
