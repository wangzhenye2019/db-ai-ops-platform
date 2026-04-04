<template>
  <div class="page">
    <div class="title-row">
      <div class="title">SQL 工单</div>
      <div class="actions">
        <el-button @click="load" :icon="Refresh">刷新</el-button>
        <el-button type="primary" @click="openCreate" :icon="Plus">新建工单</el-button>
      </div>
    </div>

    <el-card class="card">
      <el-row :gutter="12" class="filters">
        <el-col :span="5">
          <el-select v-model="filters.status" placeholder="状态" clearable @change="load">
            <el-option label="待审核" value="pending" />
            <el-option label="已通过" value="approved" />
            <el-option label="已拒绝" value="rejected" />
            <el-option label="执行中" value="executing" />
            <el-option label="已执行" value="executed" />
            <el-option label="执行失败" value="failed" />
          </el-select>
        </el-col>
        <el-col :span="5">
          <el-select v-model="filters.database_id" placeholder="数据库" clearable @change="load">
            <el-option v-for="db in databases" :key="db.id" :label="db.name" :value="db.id" />
          </el-select>
        </el-col>
      </el-row>

      <el-table :data="orders" stripe v-loading="loading" :empty-text="loading ? '加载中...' : '暂无工单'">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="title" label="标题" min-width="200" show-overflow-tooltip />
        <el-table-column label="数据库" width="120">
          <template #default="{ row }">
            <el-tag size="small" type="info">{{ row.database_name }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="sql_type" label="SQL类型" width="90">
          <template #default="{ row }">
            <el-tag :type="sqlTypeTag(row.sql_type)" size="small">{{ row.sql_type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusTag(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="耗时" width="80">
          <template #default="{ row }">
            {{ row.execution_time ? row.execution_time.toFixed(2) + 's' : '-' }}
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="160">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="240" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="viewDetail(row)">详情</el-button>
            <template v-if="row.status === 'pending'">
              <el-button link type="success" @click="audit(row, 'approve')">通过</el-button>
              <el-button link type="danger" @click="audit(row, 'reject')">拒绝</el-button>
            </template>
            <template v-if="row.status === 'approved'">
              <el-button link type="warning" @click="execute(row)">执行</el-button>
            </template>
            <template v-if="row.status === 'executed'">
              <el-button link type="info" @click="rollback(row)">回滚</el-button>
            </template>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="pagination.page"
        :page-size="pagination.per_page"
        :total="pagination.total"
        layout="total, prev, pager, next"
        @current-change="load"
        style="margin-top: 16px; justify-content: center"
      />
    </el-card>

    <!-- 创建工单对话框 -->
    <el-dialog v-model="createVisible" title="新建SQL工单" width="800px" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
        <el-form-item label="工单标题" prop="title">
          <el-input v-model="form.title" placeholder="例如：更新用户状态" />
        </el-form-item>
        <el-form-item label="工单描述">
          <el-input v-model="form.description" type="textarea" :rows="2" placeholder="可选，描述工单背景和目的" />
        </el-form-item>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="目标数据库" prop="database_id">
              <el-select v-model="form.database_id" placeholder="选择数据库" style="width:100%">
                <el-option v-for="db in databases" :key="db.id" :label="db.name" :value="db.id" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="SQL内容" prop="sql_content">
          <el-input
            v-model="form.sql_content"
            type="textarea"
            :rows="8"
            placeholder="请输入SQL语句"
            font-family="monospace"
          />
        </el-form-item>

        <!-- 风险提示 -->
        <el-alert v-if="riskResult" :type="riskLevelType" :title="riskTitle" show-icon>
          <ul v-if="riskResult.items && riskResult.items.length" style="margin: 8px 0 0 20px; padding: 0">
            <li v-for="(item, idx) in riskResult.items" :key="idx">{{ item.message }}</li>
          </ul>
        </el-alert>

        <el-button type="primary" link @click="auditSQL" style="margin-top: 8px">检查SQL风险</el-button>
      </el-form>

      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitCreate">提交工单</el-button>
      </template>
    </el-dialog>

    <!-- 工单详情对话框 -->
    <el-dialog v-model="detailVisible" title="工单详情" width="800px">
      <el-descriptions :column="2" border v-if="currentOrder">
        <el-descriptions-item label="工单ID">{{ currentOrder.id }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="statusTag(currentOrder.status)">{{ statusLabel(currentOrder.status) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="标题" :span="2">{{ currentOrder.title }}</el-descriptions-item>
        <el-descriptions-item label="数据库">{{ currentOrder.database_name }}</el-descriptions-item>
        <el-descriptions-item label="SQL类型">
          <el-tag :type="sqlTypeTag(currentOrder.sql_type)">{{ currentOrder.sql_type }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="执行耗时">{{ currentOrder.execution_time }}s</el-descriptions-item>
        <el-descriptions-item label="影响行数">{{ currentOrder.affected_rows }}</el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ currentOrder.created_at }}</el-descriptions-item>
        <el-descriptions-item label="审核时间">{{ currentOrder.reviewed_at || '-' }}</el-descriptions-item>
        <el-descriptions-item label="审核意见" :span="2">{{ currentOrder.review_comment || '-' }}</el-descriptions-item>
      </el-descriptions>

      <el-divider>SQL内容</el-divider>
      <pre class="sql-content">{{ currentOrder?.sql_content }}</pre>

      <template v-if="currentOrder?.rollback_sql">
        <el-divider>回滚SQL</el-divider>
        <pre class="sql-content rollback">{{ currentOrder.rollback_sql }}</pre>
      </template>

      <template #footer>
        <el-button @click="detailVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh } from '@element-plus/icons-vue'
import { databaseAPI } from '@/api/services'

const orders = ref([])
const databases = ref([])
const loading = ref(false)
const createVisible = ref(false)
const detailVisible = ref(false)
const saving = ref(false)
const currentOrder = ref(null)
const riskResult = ref(null)

const filters = reactive({ status: '', database_id: null })
const pagination = reactive({ page: 1, per_page: 20, total: 0 })

const formRef = ref()
const form = reactive({
  title: '',
  description: '',
  database_id: null,
  sql_content: ''
})

const rules = {
  title: [{ required: true, message: '请输入工单标题', trigger: 'blur' }],
  database_id: [{ required: true, message: '请选择数据库', trigger: 'change' }],
  sql_content: [{ required: true, message: '请输入SQL内容', trigger: 'blur' }]
}

const statusTag = (status) => ({
  pending: 'info', approved: 'success', rejected: 'danger',
  executing: 'warning', executed: 'success', failed: 'danger', rolled_back: 'info'
}[status] || 'info')

const statusLabel = (status) => ({
  pending: '待审核', approved: '已通过', rejected: '已拒绝',
  executing: '执行中', executed: '已执行', failed: '失败', rolled_back: '已回滚'
}[status] || status)

const sqlTypeTag = (type) => ({
  SELECT: 'success', INSERT: 'primary', UPDATE: 'warning',
  DELETE: 'danger', CREATE: 'info', ALTER: 'info', DROP: 'danger'
}[type] || 'info')

const formatTime = (time) => {
  if (!time) return '-'
  return new Date(time).toLocaleString('zh-CN')
}

const load = async () => {
  loading.value = true
  try {
    const params = new URLSearchParams()
    if (filters.status) params.append('status', filters.status)
    if (filters.database_id) params.append('database_id', filters.database_id)
    params.append('page', pagination.page)
    params.append('per_page', pagination.per_page)

    const res = await fetch(`/api/sql/orders?${params}`)
    const data = await res.json()
    orders.value = data.data?.orders || []
    pagination.total = data.data?.total || 0
  } catch (e) {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

const loadDatabases = async () => {
  try {
    const res = await databaseAPI.list()
    databases.value = res.databases || []
  } catch (e) {
    console.error('Failed to load databases', e)
  }
}

const openCreate = () => {
  form.title = ''
  form.description = ''
  form.database_id = null
  form.sql_content = ''
  riskResult.value = null
  createVisible.value = true
}

const auditSQL = async () => {
  if (!form.sql_content) return
  try {
    const res = await fetch('/api/sql/audit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sql: form.sql_content, database_id: form.database_id })
    })
    const data = await res.json()
    riskResult.value = data.data?.risk
  } catch (e) {
    ElMessage.error('检查失败')
  }
}

const submitCreate = async () => {
  await formRef.value?.validate(async (valid) => {
    if (!valid) return
    saving.value = true
    try {
      const res = await fetch('/api/sql/orders', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form)
      })
      const data = await res.json()
      if (data.success) {
        ElMessage.success('工单创建成功')
        createVisible.value = false
        load()
      } else {
        ElMessage.error(data.message)
      }
    } catch (e) {
      ElMessage.error('创建失败')
    } finally {
      saving.value = false
    }
  })
}

const viewDetail = (row) => {
  currentOrder.value = row
  detailVisible.value = true
}

const audit = async (row, action) => {
  try {
    await ElMessageBox.confirm(`确认${action === 'approve' ? '通过' : '拒绝'}该工单？`, '提示', { type: 'warning' })
    const res = await fetch(`/api/sql/orders/${row.id}/audit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action })
    })
    const data = await res.json()
    if (data.success) {
      ElMessage.success('审核完成')
      load()
    } else {
      ElMessage.error(data.message)
    }
  } catch {}
}

const execute = async (row) => {
  try {
    await ElMessageBox.confirm('确认执行该SQL？', '提示', { type: 'warning' })
    const res = await fetch(`/api/sql/orders/${row.id}/execute`, { method: 'POST' })
    const data = await res.json()
    if (data.success) {
      ElMessage.success('执行任务已启动')
      load()
    } else {
      ElMessage.error(data.message)
    }
  } catch {}
}

const rollback = async (row) => {
  try {
    await ElMessageBox.confirm('确认回滚该工单？', '提示', { type: 'warning' })
    const res = await fetch(`/api/sql/orders/${row.id}/rollback`, { method: 'POST' })
    const data = await res.json()
    if (data.success) {
      ElMessage.success('回滚工单已创建')
      load()
    } else {
      ElMessage.error(data.message)
    }
  } catch {}
}

const riskLevelType = computed(() => {
  if (!riskResult.value) return 'info'
  if (riskResult.value.level === 'high') return 'error'
  if (riskResult.value.level === 'medium') return 'warning'
  return 'success'
})

const riskTitle = computed(() => {
  if (!riskResult.value) return ''
  const level = riskResult.value.level
  return level === 'high' ? '高风险操作' : level === 'medium' ? '中等风险' : '低风险操作'
})

import { computed } from 'vue'

onMounted(() => {
  load()
  loadDatabases()
})
</script>

<style scoped>
.page { padding: 16px; }
.title-row { display: flex; justify-content: space-between; align-items: center; padding: 12px 16px; }
.title { font-size: 18px; font-weight: 600; color: #0f172a; }
.actions { display: flex; gap: 10px; }
.card { margin: 0 8px; }
.filters { margin-bottom: 16px; }
.sql-content {
  background: #f5f7fa;
  padding: 12px;
  border-radius: 4px;
  font-family: monospace;
  white-space: pre-wrap;
  word-break: break-all;
}
.sql-content.rollback { background: #fff7ed; }
</style>