<template>
  <div class="performance-page">
    <div class="toolbar">
      <div class="left">
        <el-select v-model="targetType" placeholder="目标类型" style="width:140px" @change="loadTargets">
          <el-option label="全部" value="" />
          <el-option label="主机" value="host" />
          <el-option label="数据库" value="database" />
          <el-option label="中间件" value="middleware" />
        </el-select>
        <el-select v-model="targetId" placeholder="选择目标" style="width:180px" :disabled="!targetType">
          <el-option v-for="t in targets" :key="t.id + '-' + t.type" :label="t.name" :value="t.id" />
        </el-select>
        <el-select v-model="metricType" placeholder="指标类型" style="width:140px">
          <el-option label="全部" value="" />
          <el-option v-for="t in metricTypes" :key="t.value" :label="t.label" :value="t.value" />
        </el-select>
        <el-select v-model="timeRange" style="width:120px">
          <el-option label="1小时" value="1h" />
          <el-option label="6小时" value="6h" />
          <el-option label="24小时" value="24h" />
          <el-option label="7天" value="7d" />
          <el-option label="30天" value="30d" />
        </el-select>
        <el-button type="primary" @click="loadMetrics">查询</el-button>
      </div>
      <div class="right">
        <el-button @click="refresh" :icon="Refresh">刷新</el-button>
      </div>
    </div>

    <div class="content">
      <el-row :gutter="16">
        <el-col :span="6" v-for="m in latestMetrics" :key="m.metric_type">
          <el-card class="metric-card">
            <div class="metric-label">{{ getLabel(m.metric_type) }}</div>
            <div class="metric-value">
              <span class="value">{{ m.value?.toFixed(1) }}</span>
              <span class="unit">{{ m.unit }}</span>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <el-card class="chart-card">
        <div class="chart-title">趋势图</div>
        <div class="chart-container" ref="chartRef">
          <svg :viewBox="`0 0 ${chartWidth} ${chartHeight}`" class="chart-svg">
            <!-- Y-axis labels -->
            <g class="y-axis">
              <text v-for="(label, i) in yLabels" :key="i" :x="35" :y="40 + i * 60" font-size="10" fill="#909399" text-anchor="end">{{ label }}</text>
            </g>
            <!-- Grid lines -->
            <g class="grid">
              <line v-for="(label, i) in yLabels" :key="i" x1="40" :y1="40 + i * 60" :x2="chartWidth - 20" :y2="40 + i * 60" stroke="#eee" />
            </g>
            <!-- X-axis labels -->
            <g class="x-axis">
              <text v-for="(label, i) in xLabels" :key="i" :x="40 + i * xStep" :y="chartHeight - 10" font-size="10" fill="#909399" text-anchor="middle">{{ label }}</text>
            </g>
            <!-- Line chart -->
            <path :d="chartPath" fill="none" stroke="#409eff" stroke-width="2" />
            <!-- Area under line -->
            <path :d="areaPath" fill="url(#gradient)" opacity="0.3" />
            <defs>
              <linearGradient id="gradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stop-color="#409eff" />
                <stop offset="100%" stop-color="#fff" />
              </linearGradient>
            </defs>
            <!-- Data points -->
            <circle v-for="(p, i) in dataPoints" :key="i" :cx="p.x" :cy="p.y" r="3" fill="#409eff" />
          </svg>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { metricsAPI } from '@/api/services'
import { Refresh } from '@element-plus/icons-vue'

const targetType = ref('')
const targetId = ref(null)
const metricType = ref('')
const timeRange = ref('24h')
const targets = ref([])
const metricTypes = ref([])
const latestMetrics = ref([])
const chartData = ref([])

const chartWidth = 800
const chartHeight = 300
const chartRef = ref(null)

const xStep = computed(() => (chartWidth - 60) / Math.max(chartData.value.length - 1, 1))

const yLabels = computed(() => {
  if (!chartData.value.length) return ['100', '75', '50', '25', '0']
  const max = Math.max(...chartData.value.map(d => d.value))
  const step = max / 4
  return [max.toFixed(0), (max * 0.75).toFixed(0), (max * 0.5).toFixed(0), (max * 0.25).toFixed(0), '0']
})

const xLabels = computed(() => {
  if (!chartData.value.length) return []
  const labels = []
  const step = Math.ceil(chartData.value.length / 6)
  for (let i = 0; i < chartData.value.length; i += step) {
    const ts = chartData.value[i]?.timestamp?.slice(11, 16) || ''
    labels.push(ts)
  }
  return labels
})

const dataPoints = computed(() => {
  if (!chartData.value.length) return []
  const max = Math.max(...chartData.value.map(d => d.value)) || 1
  return chartData.value.map((d, i) => ({
    x: 40 + i * xStep.value,
    y: 40 + (1 - d.value / max) * 240,
    value: d.value
  }))
})

const chartPath = computed(() => {
  if (!dataPoints.value.length) return ''
  return 'M' + dataPoints.value.map(p => `${p.x},${p.y}`).join(' L')
})

const areaPath = computed(() => {
  if (!dataPoints.value.length) return ''
  const bottom = chartHeight - 20
  return 'M40,' + bottom + ' L' + dataPoints.value.map(p => `${p.x},${p.y}`).join(' L') + ' L' + (40 + (dataPoints.value.length - 1) * xStep.value) + ',' + bottom + ' Z'
})

const getLabel = (type) => {
  const labels = { cpu: 'CPU', memory: '内存', disk: '磁盘', connections: '连接数', qps: 'QPS', tps: 'TPS', slow_queries: '慢查询', threads: '线程' }
  return labels[type] || type
}

const loadTypes = async () => {
  try {
    const res = await metricsAPI.getTypes()
    metricTypes.value = res.types || []
  } catch (e) {
    console.error(e)
  }
}

const loadTargets = async () => {
  try {
    const res = await metricsAPI.getTargets(targetType.value || undefined)
    targets.value = res.targets || []
  } catch (e) {
    console.error(e)
  }
}

const loadLatest = async () => {
  try {
    const res = await metricsAPI.getLatest({
      target_type: targetType.value || undefined,
      target_id: targetId.value
    })
    latestMetrics.value = res.metrics || []
  } catch (e) {
    console.error(e)
  }
}

const loadMetrics = async () => {
  try {
    const res = await metricsAPI.getMetrics({
      target_type: targetType.value || undefined,
      target_id: targetId.value,
      metric_type: metricType.value || undefined,
      time_range: timeRange.value
    })
    chartData.value = res.metrics || []
    if (!chartData.value.length) {
      ElMessage.info('暂无数据，显示示例数据')
    }
  } catch (e) {
    ElMessage.error(e.message || '加载失败')
  }
}

const refresh = () => {
  loadLatest()
  loadMetrics()
}

onMounted(() => {
  loadTypes()
  loadTargets()
  loadLatest()
  loadMetrics()
})

watch([targetType, targetId], () => {
  loadLatest()
})
</script>

<style scoped>
.performance-page { display: flex; flex-direction: column; height: 100vh; background: #f5f7fb; }
.toolbar { display: flex; justify-content: space-between; padding: 12px 16px; background: #fff; border-bottom: 1px solid #e4e7ed; }
.toolbar .left, .toolbar .right { display: flex; gap: 8px; align-items: center; }
.content { padding: 16px; flex: 1; overflow: auto; }
.metric-card { margin-bottom: 16px; text-align: center; }
.metric-label { color: #909399; font-size: 14px; margin-bottom: 8px; }
.metric-value .value { font-size: 28px; font-weight: 600; color: #303133; }
.metric-value .unit { font-size: 14px; color: #909399; margin-left: 4px; }
.chart-card { margin-top: 16px; }
.chart-title { font-size: 16px; font-weight: 600; margin-bottom: 16px; }
.chart-container { width: 100%; height: 320px; }
.chart-svg { width: 100%; height: 100%; }
</style>