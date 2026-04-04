<template>
  <div class="page">
    <div class="title-row">
      <div class="title">
        告警历史
        <el-tag v-if="stats.active" type="danger" effect="dark" class="stats-tag">
          活跃 {{ stats.active }}
        </el-tag>
      </div>
      <div class="actions">
        <el-button @click="load" :icon="Refresh">刷新</el-button>
        <el-button @click="showStats = true" :icon="TrendCharts">统计</el-button>
      </div>
    </div>

    <el-card class="card">
      <el-row :gutter="12" class="filters">
        <el-col :span="5">
          <el-select v-model="filters.status" placeholder="状态" clearable @change="load">
            <el-option label="触发中" value="active">
              <el-tag type="danger" size="small">触发中</el-tag>
            </el-option>
            <el-option label="已确认" value="acked">
              <el-tag type="warning" size="small">已确认</el-tag>
            </el-option>
            <el-option label="已恢复" value="resolved">
              <el-tag type="success" size="small">已恢复</el-tag>
            </el-option>
          </el-select>
        </el-col>
        <el-col :span="5">
          <el-select v-model="filters.level" placeholder="级别" clearable @change="load">
            <el-option label="P0 - 紧急" value="p0" />
            <el-option label="P1 - 重要" value="p1" />
            <el-option label="P2 - 一般" value="p2" />
            <el-option label="P3 - 提示" value="p3" />
          </el-select>
        </el-col>
        <el-col :span="5">
          <el-select v-model="filters.target_type" placeholder="目标类型" clearable @change="load">
            <el-option label="数据库" value="database" />
            <el-option label="主机" value="host" />
            <el-option label="中间件" value="middleware" />
          </el-select>
        </el-col>
        <el-col :span="5">
          <el-select v-model="filters.hours" placeholder="时间范围" @change="load">
            <el-option label="最近1小时" :value="1" />
            <el-option label="最近6小时" :value="6" />
            <el-option label="最近24小时" :value="24" />
            <el-option label="最近7天" :value="168" />
          </el-select>
        </el-col>
        <el-col :span="4">
          <el-button type="primary" @click="batchAck" :disabled="!selectedAlerts.length">
            批量确认 ({{ selectedAlerts.length }})
          </el-button>
        </el-col>
      </el-row>

      <el-table
        :data="alerts"
        stripe
        v-loading="loading"
        @selection-change="handleSelectionChange"
        :empty-text="loading ? '加载中...' : '暂无告警记录'"
      >
        <el-table-column type="selection" width="55" />

        <el-table-column label="级别" width="80">
          <template #default="{ row }">
            <el-tag :type="levelType(row.level)" effect="dark" size="small">
              {{ row.level.toUpperCase() }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small">
              {{ statusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="alert_name" label="告警名称" min-width="180" show-overflow-tooltip />

        <el-table-column label="目标" min-width="160">
          <template #default="{ row }">
            <div class="target-info">
              <el-tag size="small">{{ targetTypeLabel(row.target_type) }}</el-tag>
              <span class="target-name">{{ row.target_name }}</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="指标" width="140">
          <template #default="{ row }">
            <div class="metric-info">
              <div>{{ row.metric }}: <span class="value">{{ formatValue(row.metric_value) }}</span></div>
              <div class="threshold">阈值: {{ formatValue(row.threshold) }}</div>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="持续时间" width="120">
          <template #default="{ row }">
            <span :class="{ 'duration-long': row.duration_seconds > 3600 }">
              {{ formatDuration(row.duration_seconds) }}
            </span>
          </template>
        </el-table-column>

        <el-table-column label="触发时间" width="160">
          <template #default="{ row }">
            <el-tooltip :content="row.triggered_at">
              <span>{{ formatTime(row.triggered_at) }}</span>
            </el-tooltip>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="row.status === 'active'"
              link
              type="warning"
              @click="ackAlert(row)"
            >
              确认
            </el-button>
            <el-button
              v-if="row.status !== 'resolved'"
              link
              type="success"
              @click="resolveAlert(row)"
            >
              解决
            </el-button>
            <el-button link type="primary" @click="viewDetail(row)">
              详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 统计对话框 -->
    <el-dialog v-model="showStats" title="告警统计" width="600px">
      <el-row :gutter="20">
        <el-col :span="12">
          <h4>按级别分布</h4>
          <div class="stat-list">
            <div v-for="(count, level) in stats.by_level" :key="level" class="stat-item">
              <el-tag :type="levelType(level)" size="small">{{ level.toUpperCase() }}</el-tag>
              <el-progress :percentage="calcPercentage(count, stats.total)" :color="levelColor(level)" />
              <span class="count">{{ count }}</span>
            </div>
          </div>
        </el-col>
        <el-col :span="12">
          <h4>按状态分布</h4>
          <div class="stat-list">
            <div v-for="(count, status) in stats.by_status" :key="status" class="stat-item">
              <el-tag :type="statusType(status)" size="small">{{ statusLabel(status) }}</el-tag>
              <el-progress :percentage="calcPercentage(count, stats.total)" />
              <span class="count">{{ count }}</span>
            </div>
          </div>
        </el-col>
      </el-row>

      <el-divider />

      <h4>Top 5 告警规则</h4>
      <el-table :data="stats.top_rules" size="small">
        <el-table-column prop="name" label="规则" />
        <el-table-column prop="count" label="次数" width="80" />
      </el-table>
    </el-dialog>

    <!-- 确认对话框 -->
    <el-dialog v-model="ackDialogVisible" title="确认告警" width="400px">
      <el-form>
        <el-form-item label="备注">
          <el-input v-model="ackForm.comment" type="textarea" :rows="3" placeholder="输入确认备注（可选）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="ackDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitAck">确认</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, TrendCharts } from '@element-plus/icons-vue'

const alerts = ref([])
const selectedAlerts = ref([])
const loading = ref(false)
const showStats = ref(false)
const stats = ref({ active: 0, total: 0, by_level: {}, by_status: {}, top_rules: [] })

const filters = reactive({
  status: '',
  level: '',
  target_type: '',
  hours: 24
})

const ackDialogVisible = ref(false)
const ackForm = reactive({ comment: '', ids: [] })

const levelType = (level) => ({ p0: 'danger', p1: 'warning', p2: 'info', p3: '' }[level] || 'info')
const levelColor = (level) => ({ p0: '#f56c6c', p1: '#e6a23c', p2: '#409eff', p3: '#909399' }[level])
const statusType = (status) => ({ active: 'danger', acked: 'warning', resolved: 'success' }[status] || 'info')
const statusLabel = (status) => ({ active: '触发中', acked: '已确认', resolved: '已恢复' }[status] || status)
const targetTypeLabel = (type) => ({ database: '数据库', host: '主机', middleware: '中间件' }[type] || type)

const formatValue = (v) => {
  if (v === null || v === undefined) return '-'
  return typeof v === 'number' ? v.toFixed(2) : v
}

const formatDuration = (seconds) => {
  if (!seconds) return '-'
  if (seconds < 60) return `${seconds}秒`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}分${seconds % 60}秒`
  const hours = Math.floor(seconds / 3600)
  const mins = Math.floor((seconds % 3600) / 60)
  return `${hours}时${mins}分`
}

const formatTime = (time) => {
  if (!time) return '-'
  const d = new Date(time)
  const now = new Date()
  const isToday = d.toDateString() === now.toDateString()
  if (isToday) return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours()}:${d.getMinutes().toString().padStart(2, '0')}`
}

const calcPercentage = (count, total) => {
  if (!total) return 0
  return Math.round((count / total) * 100)
}

const buildQuery = () => {
  const params = new URLSearchParams()
  if (filters.status) params.append('status', filters.status)
  if (filters.level) params.append('level', filters.level)
  if (filters.target_type) params.append('target_type', filters.target_type)
  params.append('hours', filters.hours)
  return params.toString()
}

const load = async () => {
  loading.value = true
  try {
    const [alertsRes, statsRes] = await Promise.all([
      fetch(`/api/alerts/history?${buildQuery()}`),
      fetch(`/api/alerts/history/stats?hours=${filters.hours}`)
    ])
    const alertsData = await alertsRes.json()
    const statsData = await statsRes.json()
    alerts.value = alertsData.data?.alerts || []
    const s = statsData.data || {}
    stats.value = {
      active: s.by_status?.active || 0,
      total: Object.values(s.by_status || {}).reduce((a, b) => a + b, 0),
      by_level: s.by_level || {},
      by_status: s.by_status || {},
      top_rules: s.top_rules || []
    }
  } catch (e) {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

const handleSelectionChange = (selection) => {
  selectedAlerts.value = selection
}

const ackAlert = (row) => {
  ackForm.ids = [row.id]
  ackForm.comment = ''
  ackDialogVisible.value = true
}

const batchAck = () => {
  ackForm.ids = selectedAlerts.value.map(a => a.id)
  ackForm.comment = ''
  ackDialogVisible.value = true
}

const submitAck = async () => {
  try {
    for (const id of ackForm.ids) {
      await fetch(`/api/alerts/history/${id}/ack`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ comment: ackForm.comment })
      })
    }
    ElMessage.success('确认成功')
    ackDialogVisible.value = false
    load()
  } catch (e) {
    ElMessage.error('确认失败')
  }
}

const resolveAlert = async (row) => {
  try {
    await fetch(`/api/alerts/history/${row.id}/resolve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reason: '手动解决' })
    })
    ElMessage.success('已标记为已恢复')
    load()
  } catch (e) {
    ElMessage.error('操作失败')
  }
}

const viewDetail = (row) => {
  // 可扩展为详情抽屉
  ElMessage.info(`告警详情: ${row.message}`)
}

onMounted(load)
</script>

<style scoped>
.page { padding: 16px; }
.title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
}
.title {
  font-size: 18px;
  font-weight: 600;
  color: #0f172a;
  display: flex;
  align-items: center;
  gap: 12px;
}
.stats-tag { font-size: 12px; }
.actions { display: flex; gap: 10px; }
.card { margin: 0 8px; }
.filters { margin-bottom: 16px; }
.target-info {
  display: flex;
  align-items: center;
  gap: 8px;
}
.target-name {
  color: #606266;
  font-size: 13px;
}
.metric-info {
  font-size: 13px;
}
.metric-info .value {
  color: #f56c6c;
  font-weight: 600;
}
.metric-info .threshold {
  color: #909399;
  font-size: 12px;
}
.duration-long {
  color: #f56c6c;
  font-weight: 500;
}
.stat-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.stat-item {
  display: flex;
  align-items: center;
  gap: 12px;
}
.stat-item .el-progress {
  flex: 1;
}
.stat-item .count {
  width: 40px;
  text-align: right;
  font-weight: 600;
}
h4 {
  margin: 0 0 12px 0;
  font-size: 14px;
  color: #606266;
}
</style>
