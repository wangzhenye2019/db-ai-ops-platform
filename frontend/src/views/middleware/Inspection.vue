<template>
  <div class="page">
    <div class="title-row">
      <div class="title">中间件巡检</div>
      <el-button type="primary" :loading="running" @click="run">开始巡检</el-button>
    </div>
    <el-card class="card">
      <el-form label-position="top">
        <el-form-item label="目标中间件">
          <el-select v-model="selected" multiple filterable style="width:100%" placeholder="选择中间件实例">
            <el-option v-for="m in items" :key="m.id" :label="`${m.name} (${m.mw_type}@${m.host}:${m.port})`" :value="m.id" />
          </el-select>
        </el-form-item>
      </el-form>

      <el-divider />

      <el-table :data="reports" stripe>
        <el-table-column prop="id" label="报告ID" width="110" />
        <el-table-column prop="status" label="状态" width="120" />
        <el-table-column prop="target_summary" label="范围" width="160" />
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
import { inspectionAPI, middlewareAPI } from '@/api/services'

const items = ref([])
const selected = ref([])
const reports = ref([])
const running = ref(false)

const load = async () => {
  const [m, r] = await Promise.allSettled([middlewareAPI.list(), inspectionAPI.listReports()])
  if (m.status === 'fulfilled') items.value = m.value.middlewares || []
  if (r.status === 'fulfilled') reports.value = (r.value.reports || []).filter(x => x.scope === 'middleware')
}

const run = async () => {
  if (!selected.value.length) {
    ElMessage.warning('请选择目标中间件')
    return
  }
  running.value = true
  try {
    await inspectionAPI.run({ scope: 'middleware', target_ids: selected.value })
    ElMessage.success('已发起巡检（演示模式）')
    await load()
  } catch (e) {
    ElMessage.error(e.message || '发起失败')
  } finally {
    running.value = false
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
