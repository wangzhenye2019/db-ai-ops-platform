<template>
  <div class="page">
    <div class="title-row">
      <div class="title">巡检报告</div>
      <el-button @click="load">刷新</el-button>
    </div>
    <el-card class="card">
      <el-table :data="reports" stripe v-loading="loading">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="scope" label="范围" width="140" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">{{ getStatusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="target_summary" label="摘要" width="160" />
        <el-table-column prop="created_at" label="创建时间" width="180" />
        <el-table-column label="操作" width="240">
          <template #default="{ row }">
            <el-button text @click="view(row)">查看</el-button>
            <el-button text type="primary" :disabled="row.status !== 'ready'" @click="exportReport(row, 'json')">JSON</el-button>
            <el-button text type="primary" :disabled="row.status !== 'ready'" @click="exportReport(row, 'markdown')">MD</el-button>
            <el-button text type="primary" :disabled="row.status !== 'ready'" @click="exportReport(row, 'html')">HTML</el-button>
            <el-button text type="danger" @click="onDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination
        v-model:current-page="page"
        :page-size="20"
        :total="total"
        layout="total, prev, pager, next"
        @current-change="load"
        style="margin-top: 16px; justify-content: center;"
      />
    </el-card>

    <el-drawer v-model="detailVisible" title="报告详情" size="600px">
      <div v-if="detailData" class="detail-content">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="ID">{{ detailData.id }}</el-descriptions-item>
          <el-descriptions-item label="范围">{{ detailData.scope }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="getStatusType(detailData.status)">{{ getStatusText(detailData.status) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="创建人">{{ detailData.created_by || '-' }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ detailData.created_at }}</el-descriptions-item>
          <el-descriptions-item label="完成时间">{{ detailData.completed_at || '-' }}</el-descriptions-item>
        </el-descriptions>

        <div v-if="detailData.result && detailData.result.items" class="result-items">
          <h4>检查结果</h4>
          <el-table :data="detailData.result.items" size="small" stripe>
            <el-table-column label="状态" width="80">
              <template #default="{ row }">
                <span :class="'status-' + row.status">{{ getItemIcon(row.status) }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="name" label="检查项" />
            <el-table-column prop="check" label="项目" />
            <el-table-column prop="message" label="结果" />
          </el-table>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { inspectionAPI } from '@/api/services'

const reports = ref([])
const loading = ref(false)
const page = ref(1)
const total = ref(0)
const detailVisible = ref(false)
const detailData = ref(null)

const getStatusType = (status) => {
  const types = { pending: 'info', running: 'warning', ready: 'success', failed: 'danger' }
  return types[status] || 'info'
}

const getStatusText = (status) => {
  const texts = { pending: '待执行', running: '执行中', ready: '已完成', failed: '失败' }
  return texts[status] || status
}

const getItemIcon = (status) => {
  const icons = { ok: '✅', warning: '⚠️', error: '❌' }
  return icons[status] || '❓'
}

const load = async () => {
  loading.value = true
  try {
    const data = await inspectionAPI.listReports({ page: page.value, per_page: 20 })
    reports.value = data.reports || []
    total.value = data.total || 0
  } catch (e) {
    ElMessage.error(e.message || '加载失败')
  } finally {
    loading.value = false
  }
}

const view = async (row) => {
  try {
    const data = await inspectionAPI.getReport(row.id)
    detailData.value = data
    detailVisible.value = true
  } catch (e) {
    ElMessage.error(e.message || '加载失败')
  }
}

const exportReport = async (row, format) => {
  try {
    const blob = await inspectionAPI.exportReport(row.id, format)
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `report_${row.id}.${format === 'markdown' ? 'md' : format}`
    a.click()
    window.URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch (e) {
    ElMessage.error(e.message || '导出失败')
  }
}

const onDelete = async (row) => {
  try {
    await ElMessageBox.confirm(`确认删除报告 #${row.id}？`, '提示', { type: 'warning' })
    await inspectionAPI.deleteReport(row.id)
    ElMessage.success('已删除')
    await load()
  } catch {}
}

onMounted(load)
</script>

<style scoped>
.page { padding: 16px; }
.title-row { display: flex; align-items: center; justify-content: space-between; padding: 12px 16px; }
.title { font-size: 16px; font-weight: 700; color: #0f172a; }
.card { margin: 0 8px; }
.detail-content { padding: 16px; }
.result-items { margin-top: 20px; }
.result-items h4 { margin-bottom: 12px; }
.status-ok { color: #67c23a; }
.status-warning { color: #e6a23c; }
.status-error { color: #f56c6c; }
</style>