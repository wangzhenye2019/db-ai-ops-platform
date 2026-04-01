<template>
  <div class="page">
    <div class="title-row">
      <div class="title">中间件故障排查</div>
      <el-button @click="load">刷新</el-button>
    </div>
    <el-card class="card">
      <el-tabs>
        <el-tab-pane label="运维任务">
          <el-table :data="tasks" stripe>
            <el-table-column prop="id" label="ID" width="90" />
            <el-table-column prop="action" label="动作" width="160" />
            <el-table-column prop="status" label="状态" width="120" />
            <el-table-column prop="created_at" label="创建时间" min-width="180" />
            <el-table-column label="结果" min-width="260">
              <template #default="{ row }">
                <span class="muted">{{ row.result?.message || row.error_message || '-' }}</span>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
        <el-tab-pane label="审计日志">
          <el-table :data="logs" stripe>
            <el-table-column prop="id" label="ID" width="90" />
            <el-table-column prop="username" label="用户" width="120" />
            <el-table-column prop="method" label="方法" width="90" />
            <el-table-column prop="path" label="路径" min-width="240" />
            <el-table-column prop="status_code" label="状态码" width="110" />
            <el-table-column prop="created_at" label="时间" min-width="180" />
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { auditAPI, opsAPI } from '@/api/services'

const tasks = ref([])
const logs = ref([])

const load = async () => {
  const [t, l] = await Promise.allSettled([opsAPI.listTasks(), auditAPI.list({ limit: 200 })])
  if (t.status === 'fulfilled') tasks.value = (t.value.tasks || []).filter(x => x.category === 'middleware')
  if (l.status === 'fulfilled') logs.value = l.value.logs || []
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
.muted {
  color: #64748b;
}
</style>
