<template>
  <div class="dashboard">
    <h2>概览</h2>

    <el-row :gutter="20" class="stats-row">
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-icon" style="background: #409eff">
            <el-icon size="24"><DataBoard /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ stats.total_databases }}</div>
            <div class="stat-label">数据库</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-icon" style="background: #67c23a">
            <el-icon size="24"><DocumentCopy /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ stats.total_backups }}</div>
            <div class="stat-label">总备份</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-icon" style="background: #e6a23c">
            <el-icon size="24"><SuccessFilled /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ stats.successful_backups }}</div>
            <div class="stat-label">成功</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-icon" style="background: #f56c6c">
            <el-icon size="24"><CircleCloseFilled /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ stats.failed_backups }}</div>
            <div class="stat-label">失败</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" class="info-row">
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>存储使用</span>
          </template>
          <div class="storage-info">
            <div class="storage-value">{{ stats.total_size_mb }} MB</div>
            <el-progress :percentage="storagePercentage" />
          </div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>快捷操作</span>
          </template>
          <div class="quick-actions">
            <el-button type="primary" @click="$router.push('/databases')">
              <el-icon><Plus /></el-icon>
              添加数据库
            </el-button>
            <el-button type="success" @click="$router.push('/schedules')">
              <el-icon><Timer /></el-icon>
              设置定时任务
            </el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-card class="recent-backups">
      <template #header>
        <div class="card-header">
          <span>最近备份</span>
          <el-button text @click="$router.push('/backups')">查看全部</el-button>
        </div>
      </template>
      <el-table :data="recentBackups" stripe>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="database_id" label="数据库ID" width="120" />
        <el-table-column label="状态">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">{{ getStatusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="文件大小">
          <template #default="{ row }">
            {{ formatFileSize(row.file_size) }}
          </template>
        </el-table-column>
        <el-table-column label="创建时间">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { backupAPI } from '@/api/services'

const stats = ref({
  total_databases: 0,
  total_backups: 0,
  successful_backups: 0,
  failed_backups: 0,
  total_size_mb: 0
})

const recentBackups = ref([])

const storagePercentage = computed(() => {
  const max = 10240 // 10GB
  return Math.min((stats.value.total_size_mb / max) * 100, 100)
})

const loadStats = async () => {
  try {
    const data = await backupAPI.stats()
    stats.value = data
  } catch (error) {
    console.error('Failed to load stats:', error)
  }
}

const loadRecentBackups = async () => {
  try {
    const data = await backupAPI.list({ per_page: 5 })
    recentBackups.value = data.backups
  } catch (error) {
    console.error('Failed to load recent backups:', error)
  }
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
  return new Date(date).toLocaleString('zh-CN')
}

onMounted(() => {
  loadStats()
  loadRecentBackups()
})
</script>

<style scoped>
.dashboard {
  padding: 20px;
}

h2 {
  margin-bottom: 20px;
}

.stats-row {
  margin-bottom: 20px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 15px;
}

.stat-icon {
  width: 60px;
  height: 60px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}

.stat-content {
  flex: 1;
}

.stat-value {
  font-size: 24px;
  font-weight: bold;
  margin-bottom: 5px;
}

.stat-label {
  color: #909399;
  font-size: 14px;
}

.info-row {
  margin-bottom: 20px;
}

.storage-info {
  text-align: center;
}

.storage-value {
  font-size: 36px;
  font-weight: bold;
  margin-bottom: 20px;
  color: #409eff;
}

.quick-actions {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.recent-backups {
  margin-top: 20px;
}
</style>
