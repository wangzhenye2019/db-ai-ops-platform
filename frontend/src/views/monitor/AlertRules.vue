<template>
  <div class="page">
    <div class="title-row">
      <div class="title">告警规则管理</div>
      <div class="actions">
        <el-button @click="load" :icon="Refresh"">刷新</el-button>
        <el-button type="primary" @click="openCreate" :icon="Plus">新建规则</el-button>
      </div>
    </div>

    <el-card class="card">
      <el-row :gutter="12" class="filters">
        <el-col :span="6">
          <el-select v-model="filterType" placeholder="目标类型" clearable style="width:100%" @change="load">
            <el-option label="数据库" value="database" />
            <el-option label="主机" value="host" />
            <el-option label="中间件" value="middleware" />
          </el-select>
        </el-col>
        <el-col :span="6">
          <el-select v-model="filterEnabled" placeholder="状态" clearable style="width:100%" @change="load">
            <el-option label="启用" :value="true" />
            <el-option label="禁用" :value="false" />
          </el-select>
        </el-col>
      </el-row>

      <el-table :data="rules" stripe v-loading="loading" :empty-text="loading ? '加载中...' : '暂无告警规则'">
        <el-table-column prop="name" label="规则名称" min-width="180" show-overflow-tooltip />
        <el-table-column label="监控目标" width="180">
          <template #default="{ row }">
            <el-tag size="small">{{ targetTypeLabel(row.target_type) }}</el-tag>
            <span class="target-name">{{ row.target_name }}</span>
          </template>
        </el-table-column>
        <el-table-column label="告警条件" min-width="200">
          <template #default="{ row }">
            <div class="condition">
              <span class="metric">{{ getMetricLabel(row.target_type, row.metric) }}</span>
              <span class="operator">{{ row.operator }}</span>
              <span class="threshold">{{ row.threshold }}</span>
              <span class="period">/ {{ row.period_seconds / 60 }}分钟</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="级别" width="90">
          <template #default="{ row }">
            <el-tag :type="levelType(row.level)" size="small">{{ row.level.toUpperCase() }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-switch v-model="row.enabled" @change="toggleRule(row)" />
          </template>
        </el-table-column>
        <el-table-column label="通知渠道" width="120">
          <template #default="{ row }">
            <el-tag type="info" size="small">{{ row.channel_ids?.length || 0 }} 个</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button link type="primary" @click="viewHistory(row)">历史</el-button>
            <el-button link type="danger" @click="onDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 创建/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑告警规则' : '新建告警规则'" width="720px">
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
        <el-row :gutter="12">
          <el-col :span="16">
            <el-form-item label="规则名称" prop="name">
              <el-input v-model="form.name" placeholder="例如：MySQL连接数告警" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="告警级别" prop="level">
              <el-select v-model="form.level" style="width:100%">
                <el-option label="P0 - 紧急" value="p0" />
                <el-option label="P1 - 重要" value="p1" />
                <el-option label="P2 - 一般" value="p2" />
                <el-option label="P3 - 提示" value="p3" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-divider>监控目标</el-divider>

        <el-row :gutter="12">
          <el-col :span="8">
            <el-form-item label="目标类型" prop="target_type">
              <el-select v-model="form.target_type" style="width:100%" @change="onTargetTypeChange">
                <el-option label="数据库" value="database" />
                <el-option label="主机" value="host" />
                <el-option label="中间件" value="middleware" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="16">
            <el-form-item label="具体目标">
              <el-select v-model="form.target_id" clearable placeholder="不选=监控全部" style="width:100%">
                <el-option
                  v-for="t in targetOptions"
                  :key="t.id"
                  :label="t.name"
                  :value="t.id"
                />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-divider>告警条件</el-divider>

        <el-row :gutter="12">
          <el-col :span="8">
            <el-form-item label="监控指标" prop="metric">
              <el-select v-model="form.metric" style="width:100%">
                <el-option
                  v-for="m in availableMetrics"
                  :key="m.value"
                  :label="m.label"
                  :value="m.value"
                >
                  <span>{{ m.label }}</span>
                  <span style="float:right;color:#909399">{{ m.unit }}</span>
                </el-option>
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="4">
            <el-form-item label="运算符" prop="operator">
              <el-select v-model="form.operator" style="width:100%">
                <el-option label=">" value=">" />
                <el-option label="<" value="<" />
                <el-option label=">=" value=">=" />
                <el-option label="<=" value="<=" />
                <el-option label="=" value="==" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="阈值" prop="threshold">
              <el-input-number v-model="form.threshold" style="width:100%" :precision="2" />
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="统计周期">
              <el-select v-model="form.period_seconds" style="width:100%">
                <el-option label="1分钟" :value="60" />
                <el-option label="5分钟" :value="300" />
                <el-option label="10分钟" :value="600" />
                <el-option label="30分钟" :value="1800" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="聚合方式">
              <el-select v-model="form.aggregator" style="width:100%">
                <el-option label="平均值" value="avg" />
                <el-option label="最大值" value="max" />
                <el-option label="最小值" value="min" />
                <el-option label="求和" value="sum" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="连续触发次数">
              <el-input-number v-model="form.consecutive_count" :min="1" :max="10" style="width:100%" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-divider>通知配置</el-divider>

        <el-form-item label="通知渠道">
          <el-select v-model="form.channel_ids" multiple placeholder="选择通知渠道" style="width:100%">
            <el-option
              v-for="c in channels"
              :key="c.id"
              :label="c.name"
              :value="c.id"
            >
              <span>{{ c.name }}</span>
              <el-tag size="small" style="float:right">{{ c.channel_type }}</el-tag>
            </el-option>
          </el-select>
        </el-form-item>

        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="恢复通知">
              <el-switch v-model="form.notify_on_resolve" active-text="告警恢复时发送通知" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="抑制时长(秒)">
              <el-input-number v-model="form.suppression_duration" :min="0" :step="60" style="width:100%" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="onSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh } from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'
import { databaseAPI, hostAPI, middlewareAPI } from '@/api/services'

const router = useRouter()

const rules = ref([])
const channels = ref([])
const databases = ref([])
const hosts = ref([])
const middlewares = ref([])
const metrics = ref({})
const loading = ref(false)

const filterType = ref('')
const filterEnabled = ref(null)

const dialogVisible = ref(false)
const saving = ref(false)
const formRef = ref()
const editingId = ref(null)

const form = reactive({
  name: '',
  enabled: true,
  target_type: 'database',
  target_id: null,
  metric: '',
  aggregator: 'avg',
  period_seconds: 300,
  operator: '>',
  threshold: 80,
  consecutive_count: 1,
  level: 'p2',
  channel_ids: [],
  notify_on_resolve: true,
  suppression_duration: 300
})

const rulesValidation = {
  name: [{ required: true, message: '请输入规则名称', trigger: 'blur' }],
  target_type: [{ required: true, message: '请选择目标类型', trigger: 'change' }],
  metric: [{ required: true, message: '请选择监控指标', trigger: 'change' }],
  operator: [{ required: true, message: '请选择运算符', trigger: 'change' }],
  threshold: [{ required: true, message: '请输入阈值', trigger: 'blur' }],
  level: [{ required: true, message: '请选择告警级别', trigger: 'change' }]
}

const targetOptions = computed(() => {
  if (form.target_type === 'database') return databases.value
  if (form.target_type === 'host') return hosts.value
  if (form.target_type === 'middleware') return middlewares.value
  return []
})

const availableMetrics = computed(() => {
  return metrics.value[form.target_type] || []
})

const targetTypeLabel = (type) => {
  const map = { database: '数据库', host: '主机', middleware: '中间件' }
  return map[type] || type
}

const getMetricLabel = (targetType, metricValue) => {
  const list = metrics.value[targetType] || []
  const found = list.find(m => m.value === metricValue)
  return found ? found.label : metricValue
}

const levelType = (level) => {
  const map = { p0: 'danger', p1: 'warning', p2: 'info', p3: '' }
  return map[level] || 'info'
}

const load = async () => {
  loading.value = true
  try {
    // 加载规则和渠道
    const [r, c, m] = await Promise.all([
      fetch('/api/alerts/rules').then(res => res.json()),
      fetch('/api/alerts/channels').then(res => res.json()),
      fetch('/api/alerts/metrics').then(res => res.json())
    ])
    rules.value = r.data?.rules || []
    channels.value = c.data?.channels || []
    metrics.value = m.data?.metrics || {}

    // 加载目标列表
    const [dbRes, hostRes, mwRes] = await Promise.allSettled([
      databaseAPI.list(),
      hostAPI.list(),
      middlewareAPI.list()
    ])
    if (dbRes.status === 'fulfilled') databases.value = dbRes.value.databases || []
    if (hostRes.status === 'fulfilled') hosts.value = hostRes.value.hosts || []
    if (mwRes.status === 'fulfilled') middlewares.value = mwRes.value.middlewares || []
  } catch (e) {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

const resetForm = () => {
  editingId.value = null
  Object.assign(form, {
    name: '',
    enabled: true,
    target_type: 'database',
    target_id: null,
    metric: '',
    aggregator: 'avg',
    period_seconds: 300,
    operator: '>',
    threshold: 80,
    consecutive_count: 1,
    level: 'p2',
    channel_ids: [],
    notify_on_resolve: true,
    suppression_duration: 300
  })
  formRef.value?.clearValidate?.()
}

const openCreate = () => {
  resetForm()
  dialogVisible.value = true
}

const openEdit = (row) => {
  editingId.value = row.id
  Object.assign(form, row)
  dialogVisible.value = true
}

const onTargetTypeChange = () => {
  form.target_id = null
  form.metric = ''
}

const onSave = async () => {
  await formRef.value?.validate(async (valid) => {
    if (!valid) return
    saving.value = true
    try {
      const url = editingId.value ? `/api/alerts/rules/${editingId.value}` : '/api/alerts/rules'
      const method = editingId.value ? 'PUT' : 'POST'
      const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form)
      })
      const data = await res.json()
      if (data.success) {
        ElMessage.success('保存成功')
        dialogVisible.value = false
        load()
      } else {
        ElMessage.error(data.message)
      }
    } catch (e) {
      ElMessage.error('保存失败')
    } finally {
      saving.value = false
    }
  })
}

const toggleRule = async (row) => {
  try {
    const res = await fetch(`/api/alerts/rules/${row.id}/toggle`, { method: 'POST' })
    const data = await res.json()
    if (data.success) {
      ElMessage.success('操作成功')
      row.enabled = data.data.enabled
    } else {
      ElMessage.error(data.message)
      row.enabled = !row.enabled
    }
  } catch (e) {
    ElMessage.error('操作失败')
    row.enabled = !row.enabled
  }
}

const viewHistory = (row) => {
  router.push(`/alerts/history?rule_id=${row.id}`)
}

const onDelete = async (row) => {
  try {
    await ElMessageBox.confirm(`确认删除规则「${row.name}」？`, '提示', { type: 'warning' })
    const res = await fetch(`/api/alerts/rules/${row.id}`, { method: 'DELETE' })
    const data = await res.json()
    if (data.success) {
      ElMessage.success('删除成功')
      load()
    } else {
      ElMessage.error(data.message)
    }
  } catch {}
}

onMounted(load)
</script>

<style scoped>
.page {
  padding: 16px;
}
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
}
.actions {
  display: flex;
  gap: 10px;
}
.card {
  margin: 0 8px;
}
.filters {
  margin-bottom: 16px;
}
.condition {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
}
.metric {
  color: #409eff;
  font-weight: 500;
}
.operator {
  color: #f56c6c;
  font-weight: bold;
}
.threshold {
  color: #e6a23c;
  font-weight: 600;
}
.period {
  color: #909399;
  font-size: 12px;
}
.target-name {
  margin-left: 8px;
  color: #606266;
}
</style>
