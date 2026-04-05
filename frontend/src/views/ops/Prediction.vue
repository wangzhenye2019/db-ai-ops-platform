<template>
  <div class="page">
    <div class="title-row">
      <div class="title">预测性维护</div>
      <div class="actions">
        <el-select v-model="metricType" style="width:160px" @change="loadPredictions">
          <el-option v-for="m in metrics" :key="m.value" :label="m.label" :value="m.value" />
        </el-select>
        <el-button type="primary" @click="runBatchPrediction" :loading="loading">批量预测</el-button>
        <el-button @click="loadPredictions">刷新</el-button>
      </div>
    </div>

    <!-- Stats -->
    <el-row :gutter="16" class="stats-row">
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-label">监控目标</div>
          <div class="stat-value">{{ predictions.length }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-label">即将阈值</div>
          <div class="stat-value warning">{{ warningCount }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-label">已超阈值</div>
          <div class="stat-value danger">{{ dangerCount }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-label">平均置信度</div>
          <div class="stat-value">{{ avgConfidence }}%</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Predictions Table -->
    <el-card class="card">
      <el-table :data="predictions" stripe v-loading="loading">
        <el-table-column prop="target_name" label="目标" min-width="140" />
        <el-table-column prop="metric_type" label="指标" width="100">
          <template #default="{ row }">
            {{ getMetricLabel(row.metric_type) }}
          </template>
        </el-table-column>
        <el-table-column label="当前值" width="100">
          <template #default="{ row }">
            <span :class="'value-' + getValueStatus(row)">{{ row.current_value }}{{ getMetricUnit(row.metric_type) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="预测值(7天后)" width="120">
          <template #default="{ row }">
            <span :class="'value-' + getValueStatus(row, row.predicted_value)">{{ row.predicted_value }}{{ getMetricUnit(row.metric_type) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="阈值" width="80">
          <template #default="{ row }">
            {{ row.threshold }}{{ getMetricUnit(row.metric_type) }}
          </template>
        </el-table-column>
        <el-table-column label="预警天数" width="100">
          <template #default="{ row }">
            <el-tag :type="getDaysType(row.days_to_threshold)">
              {{ row.days_to_threshold <= 0 ? '已超' : row.days_to_threshold + '天' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="趋势" width="80">
          <template #default="{ row }">
            <el-icon :class="row.trend === 'up' ? 'trend-up' : 'trend-down'">
              <ArrowUp v-if="row.trend === 'up'" />
              <ArrowDown v-else />
            </el-icon>
          </template>
        </el-table-column>
        <el-table-column label="置信度" width="100">
          <template #default="{ row }">
            <el-progress :percentage="Math.round(row.confidence * 100)" :status="getConfidenceStatus(row.confidence)" :stroke-width="10" style="width:80px" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button text @click="showDetail(row)">详情</el-button>
            <el-button text type="danger" @click="onDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- Detail Dialog -->
    <el-dialog v-model="detailVisible" title="预测详情" width="500px">
      <div v-if="detailData" class="detail-content">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="目标">{{ detailData.target_name }}</el-descriptions-item>
          <el-descriptions-item label="指标">{{ getMetricLabel(detailData.metric_type) }}</el-descriptions-item>
          <el-descriptions-item label="当前值">{{ detailData.current_value }}{{ getMetricUnit(detailData.metric_type) }}</el-descriptions-item>
          <el-descriptions-item label="预测值">{{ detailData.predicted_value }}{{ getMetricUnit(detailData.metric_type) }}</el-descriptions-item>
          <el-descriptions-item label="阈值">{{ detailData.threshold }}{{ getMetricUnit(detailData.metric_type) }}</el-descriptions-item>
          <el-descriptions-item label="预警天数">
            <el-tag :type="getDaysType(detailData.days_to_threshold)">{{ detailData.days_to_threshold }}天</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="预测日期">{{ detailData.prediction_date }}</el-descriptions-item>
          <el-descriptions-item label="置信度">{{ Math.round(detailData.confidence * 100) }}%</el-descriptions-item>
        </el-descriptions>

        <div class="advice">
          <h4>建议</h4>
          <ul v-if="detailData.days_to_threshold <= 7">
            <li v-if="detailData.metric_type === 'disk'">建议清理磁盘空间或扩展存储</li>
            <li v-if="detailData.metric_type === 'connections'">建议增加连接池配置</li>
            <li v-if="detailData.metric_type === 'capacity'">建议清理历史数据或扩容</li>
            <li>提前做好容量规划</li>
          </ul>
          <ul v-else>
            <li>指标正常，继续监控</li>
          </ul>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowUp, ArrowDown } from '@element-plus/icons-vue'
import { predictionAPI } from '@/api/services'

const predictions = ref([])
const loading = ref(false)
const metricType = ref('disk')
const metrics = ref([
  { value: 'disk', label: '磁盘使用率', unit: '%', threshold: 80 },
  { value: 'connections', label: '连接数', unit: '个', threshold: 80 },
  { value: 'capacity', label: '数据库容量', unit: 'GB', threshold: 85 }
])
const detailVisible = ref(false)
const detailData = ref(null)

const warningCount = computed(() => predictions.value.filter(p => p.days_to_threshold > 0 && p.days_to_threshold <= 7).length)
const dangerCount = computed(() => predictions.value.filter(p => p.days_to_threshold <= 0).length)
const avgConfidence = computed(() => {
  if (!predictions.value.length) return 0
  return Math.round(predictions.value.reduce((sum, p) => sum + p.confidence, 0) / predictions.value.length * 100)
})

const getMetricLabel = (type) => {
  const m = metrics.value.find(m => m.value === type)
  return m?.label || type
}

const getMetricUnit = (type) => {
  const m = metrics.value.find(m => m.value === type)
  return m?.unit || ''
}

const getValueStatus = (row, value) => {
  const v = value ?? row.current_value
  if (v >= row.threshold) return 'danger'
  if (v >= row.threshold * 0.8) return 'warning'
  return 'normal'
}

const getDaysType = (days) => {
  if (days <= 0) return 'danger'
  if (days <= 7) return 'warning'
  return 'success'
}

const getConfidenceStatus = (conf) => {
  if (conf >= 0.8) return 'success'
  if (conf >= 0.6) return 'warning'
  return 'exception'
}

const loadPredictions = async () => {
  loading.value = true
  try {
    const res = await predictionAPI.getPredictions({ metric_type: metricType.value })
    predictions.value = res.predictions || []
  } catch (e) {
    ElMessage.error(e.message || '加载失败')
  } finally {
    loading.value = false
  }
}

const runBatchPrediction = async () => {
  loading.value = true
  try {
    await predictionAPI.batchPrediction(metricType.value)
    ElMessage.success('预测完成')
    await loadPredictions()
  } catch (e) {
    ElMessage.error(e.message || '预测失败')
  } finally {
    loading.value = false
  }
}

const showDetail = (row) => {
  detailData.value = row
  detailVisible.value = true
}

const onDelete = async (row) => {
  try {
    await ElMessageBox.confirm('确认删除该预测记录？', '提示', { type: 'warning' })
    await predictionAPI.deletePrediction(row.id || row.target_id)
    ElMessage.success('已删除')
    await loadPredictions()
  } catch {}
}

onMounted(loadPredictions)
</script>

<style scoped>
.page { padding: 16px; }
.title-row { display: flex; align-items: center; justify-content: space-between; padding: 12px 16px; }
.title { font-size: 16px; font-weight: 700; color: #0f172a; }
.actions { display: flex; gap: 8px; }
.stats-row { margin-bottom: 16px; }
.stat-card { text-align: center; }
.stat-label { color: #909399; font-size: 14px; }
.stat-value { font-size: 28px; font-weight: 600; color: #303133; margin-top: 8px; }
.stat-value.warning { color: #e6a23c; }
.stat-value.danger { color: #f56c6c; }
.card { margin: 0 8px; }
.value-danger { color: #f56c6c; font-weight: 600; }
.value-warning { color: #e6a23c; font-weight: 600; }
.value-normal { color: #303133; }
.trend-up { color: #f56c6c; }
.trend-down { color: #67c23a; }
.detail-content { padding: 16px; }
.advice { margin-top: 20px; }
.advice h4 { margin-bottom: 8px; }
.advice ul { padding-left: 20px; color: #606266; }
.advice li { margin: 4px 0; }
</style>