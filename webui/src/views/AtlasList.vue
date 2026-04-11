<template>
  <div class="atlas-list">
    <el-card>
      <template #header>
        <div class="header-actions">
          <span>图集列表</span>
          <el-button type="primary" @click="showCreateDialog = true">创建图集</el-button>
        </div>
      </template>
      <el-table :data="atlases" v-loading="loading" style="width: 100%">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="name" label="名称" />
        <el-table-column prop="description" label="描述" />
        <el-table-column prop="created_at" label="创建时间">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200">
          <template #default="{ row }">
            <el-button size="small" @click="$router.push(`/atlas/${row.id}`)">查看</el-button>
            <el-button size="small" type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="showCreateDialog" title="创建图集" width="400px">
      <el-form :model="createForm" label-width="80px">
        <el-form-item label="名称">
          <el-input v-model="createForm.name" placeholder="请输入图集名称" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="createForm.description" type="textarea" rows="3" placeholder="请输入描述" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="handleCreate" :loading="creating">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { atlasApi } from '@/api'

const atlases = ref<any[]>([])
const loading = ref(false)
const showCreateDialog = ref(false)
const creating = ref(false)
const createForm = ref({ name: '', description: '' })

const formatDate = (dateStr: string) => {
  return new Date(dateStr).toLocaleString()
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
    await ElMessageBox.confirm(`确定删除图集 "${row.name}" 吗？`, '提示', {
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
.header-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
