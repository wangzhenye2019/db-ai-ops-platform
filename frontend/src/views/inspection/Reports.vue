<template>
  <div class="page">
    <div class="title-row">
      <div class="title">巡检报告</div>
      <el-button @click="load">刷新</el-button>
    </div>
    <el-card class="card">
      <el-table :data="reports" stripe>
        <el-table-column prop="id" label="ID" width="100" />
        <el-table-column prop="scope" label="范围" width="120" />
        <el-table-column prop="status" label="状态" width="120" />
        <el-table-column prop="target_summary" label="摘要" width="160" />
        <el-table-column prop="created_at" label="创建时间" min-width="180" />
        <el-table-column label="操作" width="160">
          <template #default="{ row }">
            <el-button text @click="view(row)">查看</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { inspectionAPI } from '@/api/services'

const reports = ref([])

const load = async () => {
  try {
    const data = await inspectionAPI.listReports()
    reports.value = data.reports || []
  } catch (e) {
    ElMessage.error(e.message || '加载失败')
  }
}

const view = async (row) => {
  try {
    const data = await inspectionAPI.getReport(row.id)
    await ElMessageBox.alert(JSON.stringify(data.result || {}, null, 2), `报告 ${row.id}`, {
      confirmButtonText: '关闭',
      customClass: 'json-alert'
    })
  } catch (e) {
    ElMessage.error(e.message || '加载失败')
  }
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
  font-size: 16px;
  font-weight: 700;
  color: #0f172a;
}
.card {
  margin: 0 8px;
}
</style>
