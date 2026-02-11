<template>
  <div class="backups">
    <div class="header">
      <h2>备份记录</h2>
      <div class="header-actions">
        <el-select v-model="filters.database_id" placeholder="选择数据库" clearable @change="loadBackups">
          <el-option label="全部" :value="null" />
          <el-option
            v-for="db in databases"
            :key="db.id"
            :label="db.name"
            :value="db.id"
          />
        </el-select>
        <el-button type="primary" @click="showCreateDialog = true">
          <el-icon><Plus /></el-icon>
          创建备份
        </el-button>
        <el-button @click="cleanupBackups">
          <el-icon><Delete /></el-icon>
          清理旧备份
        </el-button>
      </div>
    </div>

    <el-table :data="backups" stripe v-loading="loading">
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column label="数据库" width="150">
        <template #default="{ row }">
          {{ getDatabaseName(row.database_id) }}
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="getStatusType(row.status)">{{ getStatusText(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="文件大小" width="120">
        <template #default="{ row }">
          {{ formatFileSize(row.file_size) }}
        </template>
      </el-table-column>
      <el-table-column label="开始时间" width="170">
        <template #default="{ row }">
          {{ formatDate(row.started_at) }}
        </template>
      </el-table-column>
      <el-table-column label="完成时间" width="170">
        <template #default="{ row }">
          {{ formatDate(row.completed_at) }}
        </template>
      </el-table-column>
      <el-table-column label="创建时间" width="170">
        <template #default="{ row }">
          {{ formatDate(row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="150">
        <template #default="{ row }">
          <el-button
            v-if="row.status === 'success'"
            size="small"
            @click="downloadBackup(row)"
          >
            下载
          </el-button>
          <el-button
            size="small"
            type="danger"
            @click="deleteBackup(row.id)"
          >
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      v-model:current-page="pagination.current_page"
      :page-size="pagination.per_page"
      :total="pagination.total"
      layout="total, prev, pager, next"
      @current-change="loadBackups"
    />

    <!-- Create Backup Dialog -->
    <el-dialog v-model="showCreateDialog" title="创建备份" width="500px">
      <el-form :model="createForm" label-width="100px">
        <el-form-item label="数据库">
          <el-select v-model="createForm.database_id" placeholder="选择数据库">
            <el-option
              v-for="db in enabledDatabases"
              :key="db.id"
              :label="db.name"
              :value="db.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="createBackup" :loading="creating">
          开始备份
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { backupAPI, databaseAPI } from '@/api/services'

const backups = ref([])
const databases = ref([])
const loading = ref(false)
const creating = ref(false)
const showCreateDialog = ref(false)

const filters = ref({
  database_id: null
})

const pagination = ref({
  current_page: 1,
  per_page: 20,
  total: 0
})

const createForm = ref({
  database_id: null
})

const enabledDatabases = computed(() => {
  return databases.value.filter(db => db.enabled)
})

const loadDatabases = async () => {
  try {
    const data = await databaseAPI.list()
    databases.value = data.databases
  } catch (error) {
    console.error('Failed to load databases:', error)
  }
}

const loadBackups = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.value.current_page,
      per_page: pagination.value.per_page,
      ...filters.value
    }
    const data = await backupAPI.list(params)
    backups.value = data.backups
    pagination.value.total = data.total
  } catch (error) {
    ElMessage.error('加载备份记录失败')
  } finally {
    loading.value = false
  }
}

const createBackup = async () => {
  if (!createForm.value.database_id) {
    ElMessage.warning('请选择数据库')
    return
  }

  creating.value = true
  try {
    const result = await backupAPI.create(createForm.value)
    ElMessage.success('备份任务已创建')
    showCreateDialog.value = false
    loadBackups()
  } catch (error) {
    ElMessage.error('创建备份失败')
  } finally {
    creating.value = false
  }
}

const deleteBackup = async (id) => {
  try {
    await ElMessageBox.confirm('确定要删除这个备份吗？', '警告', {
      type: 'warning'
    })
    await backupAPI.delete(id)
    ElMessage.success('删除成功')
    loadBackups()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

const downloadBackup = (backup) => {
  ElMessage.info(`下载备份文件: ${backup.file_path}`)
  // In production, implement actual download logic
}

const cleanupBackups = async () => {
  try {
    await ElMessageBox.confirm('确定要清理旧备份吗？', '警告', {
      type: 'warning'
    })
    await backupAPI.cleanup()
    ElMessage.success('清理任务已创建')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('创建清理任务失败')
    }
  }
}

const getDatabaseName = (id) => {
  const db = databases.value.find(d => d.id === id)
  return db ? db.name : `ID: ${id}`
}

const getStatusType = (status) => {
  const types = {
    success: 'success',
    failed: 'danger',
    running: 'warning',
    pending: 'info'
  }
  return types[status] || 'info'
}

const getStatusText = (status) => {
  const texts = {
    success: '成功',
    failed: '失败',
    running: '进行中',
    pending: '等待中'
  }
  return texts[status] || status
}

const formatFileSize = (bytes) => {
  if (!bytes) return '-'
  return (bytes / (1024 * 1024)).toFixed(2) + ' MB'
}

const formatDate = (date) => {
  if (!date) return '-'
  return new Date(date).toLocaleString('zh-CN')
}

onMounted(() => {
  loadDatabases()
  loadBackups()
})
</script>

<style scoped>
.backups {
  padding: 20px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.el-pagination {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}
</style>
