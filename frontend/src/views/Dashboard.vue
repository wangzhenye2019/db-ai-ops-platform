<template>
  <div class="dashboard">
    <div class="page-title">首页</div>

    <el-row :gutter="16" class="top-row">
      <el-col :span="12">
        <el-card class="chart-card">
          <template #header>
            <div class="card-title">数据库</div>
          </template>
          <div class="chart-body">
            <div class="chart">
              <el-progress type="dashboard" :percentage="100" :width="180">
                <template #default>
                  <div class="center-number">{{ totalDatabases }}</div>
                  <div class="center-label">总量</div>
                </template>
              </el-progress>
            </div>
            <div class="legend">
              <div v-for="item in dbTypeLegend" :key="item.label" class="legend-item">
                <span class="dot" :style="{ background: item.color }" />
                <span class="legend-label">{{ item.label }}</span>
                <span class="legend-value">{{ item.value }}</span>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="12">
        <el-card class="chart-card">
          <template #header>
            <div class="card-title">主机</div>
          </template>
          <div class="chart-body">
            <div class="chart">
              <el-progress type="dashboard" :percentage="100" :width="180" color="#8b5cf6">
                <template #default>
                  <div class="center-number">{{ totalHosts }}</div>
                  <div class="center-label">总量</div>
                </template>
              </el-progress>
            </div>
            <div class="legend">
              <div v-for="item in hostLegend" :key="item.label" class="legend-item">
                <span class="dot" :style="{ background: item.color }" />
                <span class="legend-label">{{ item.label }}</span>
                <span class="legend-value">{{ item.value }}</span>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" class="kpi-row">
      <el-col :span="6">
        <el-card class="kpi-card">
          <div class="kpi-top">
            <div class="kpi-icon" style="background:#e0f2fe;color:#0284c7">
              <el-icon><DataBoard /></el-icon>
            </div>
            <div class="kpi-title">数据库总数</div>
          </div>
          <div class="kpi-value">{{ totalDatabases }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="kpi-card">
          <div class="kpi-top">
            <div class="kpi-icon" style="background:#dcfce7;color:#16a34a">
              <el-icon><Monitor /></el-icon>
            </div>
            <div class="kpi-title">主机总数</div>
          </div>
          <div class="kpi-value">{{ totalHosts }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="kpi-card">
          <div class="kpi-top">
            <div class="kpi-icon" style="background:#fff7ed;color:#ea580c">
              <el-icon><DocumentCopy /></el-icon>
            </div>
            <div class="kpi-title">备份总数</div>
          </div>
          <div class="kpi-value">{{ stats.total_backups }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="kpi-card">
          <div class="kpi-top">
            <div class="kpi-icon" style="background:#fee2e2;color:#dc2626">
              <el-icon><CircleCloseFilled /></el-icon>
            </div>
            <div class="kpi-title">失败次数</div>
          </div>
          <div class="kpi-value">{{ stats.failed_backups }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" class="bottom-row">
      <el-col :span="24">
        <el-card class="table-card">
          <template #header>
            <div class="table-header">
              <div class="card-title">任务管理</div>
              <el-button text @click="$router.push('/backups')">更多</el-button>
            </div>
          </template>
          <el-table :data="recentBackups" stripe>
            <el-table-column prop="id" label="ID" width="80" />
            <el-table-column prop="database_id" label="数据库ID" width="120" />
            <el-table-column label="状态" width="120">
              <template #default="{ row }">
                <el-tag :type="getStatusType(row.status)">{{ getStatusText(row.status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="文件大小" width="140">
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
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { backupAPI, databaseAPI } from '@/api/services'

const stats = ref({
  total_databases: 0,
  total_backups: 0,
  successful_backups: 0,
  failed_backups: 0,
  total_size_mb: 0
})

const recentBackups = ref([])
const databases = ref([])

const totalDatabases = computed(() => databases.value.length)
const totalHosts = computed(() => new Set(databases.value.map(d => d.host)).size)

const palette = ['#409eff', '#67c23a', '#e6a23c', '#8b5cf6', '#10b981', '#ef4444', '#06b6d4', '#f59e0b']

const dbTypeLegend = computed(() => {
  const map = new Map()
  for (const d of databases.value) {
    const key = d.db_type || 'unknown'
    map.set(key, (map.get(key) || 0) + 1)
  }
  const entries = Array.from(map.entries()).sort((a, b) => b[1] - a[1])
  return entries.slice(0, 8).map(([k, v], idx) => ({
    label: k.toUpperCase(),
    value: v,
    color: palette[idx % palette.length]
  }))
})

const hostLegend = computed(() => {
  const map = new Map()
  for (const d of databases.value) {
    const key = d.host || '-'
    map.set(key, (map.get(key) || 0) + 1)
  }
  const entries = Array.from(map.entries()).sort((a, b) => b[1] - a[1])
  return entries.slice(0, 8).map(([k, v], idx) => ({
    label: k,
    value: v,
    color: palette[(idx + 3) % palette.length]
  }))
})

const loadStats = async () => {
  try {
    const data = await backupAPI.stats()
    stats.value = data
  } catch (error) {
    console.error('Failed to load stats:', error)
  }
}

const loadDatabases = async () => {
  try {
    const data = await databaseAPI.list()
    databases.value = data.databases || []
  } catch (error) {
    console.error('Failed to load databases:', error)
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
  loadDatabases()
  loadStats()
  loadRecentBackups()
})
</script>

<style scoped>
.dashboard {
  padding: 16px;
}

.page-title {
  font-size: 16px;
  font-weight: 700;
  color: #0f172a;
  padding: 12px 16px;
}

.top-row,
.kpi-row,
.bottom-row {
  padding: 0 8px 16px 8px;
}

.card-title {
  font-weight: 600;
  color: #0f172a;
}

.chart-body {
  display: flex;
  align-items: center;
  gap: 22px;
}

.chart {
  width: 220px;
  display: flex;
  justify-content: center;
}

.center-number {
  font-size: 28px;
  font-weight: 800;
  color: #0f172a;
  line-height: 1;
}

.center-label {
  margin-top: 4px;
  font-size: 12px;
  color: #64748b;
}

.legend {
  flex: 1;
}

.legend-item {
  display: grid;
  grid-template-columns: 12px 1fr auto;
  align-items: center;
  gap: 10px;
  padding: 6px 0;
}

.dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.legend-label {
  color: #334155;
  font-size: 13px;
}

.legend-value {
  color: #0f172a;
  font-weight: 600;
}

.kpi-card {
  border-radius: 10px;
}

.kpi-top {
  display: flex;
  align-items: center;
  gap: 10px;
}

.kpi-icon {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.kpi-title {
  color: #475569;
  font-size: 13px;
}

.kpi-value {
  margin-top: 10px;
  font-size: 26px;
  font-weight: 800;
  color: #0f172a;
}

.table-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
