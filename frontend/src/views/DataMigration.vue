<template>
  <div class="page">
    <div class="title-row">
      <div class="title">数据迁移</div>
      <el-button type="primary" :loading="saving" @click="createTask">创建迁移任务</el-button>
    </div>
    <el-card class="card">
      <el-form label-position="top">
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="源库">
              <el-select v-model="sourceId" filterable style="width:100%" placeholder="选择源库">
                <el-option v-for="d in dbs" :key="d.id" :label="`${d.name} (${d.db_type})`" :value="d.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="目标库">
              <el-select v-model="targetId" filterable style="width:100%" placeholder="选择目标库">
                <el-option v-for="d in dbs" :key="d.id" :label="`${d.name} (${d.db_type})`" :value="d.id" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="模式（演示）">
          <el-radio-group v-model="mode">
            <el-radio label="full">全量</el-radio>
            <el-radio label="incremental">增量</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>

      <el-divider />

      <el-table :data="tasks" stripe>
        <el-table-column prop="id" label="ID" width="90" />
        <el-table-column prop="status" label="状态" width="120" />
        <el-table-column prop="created_at" label="创建时间" min-width="180" />
        <el-table-column label="结果" min-width="260">
          <template #default="{ row }">
            <span class="muted">{{ row.result?.message || row.error_message || '-' }}</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { databaseAPI, opsAPI } from '@/api/services'

const dbs = ref([])
const tasks = ref([])

const sourceId = ref(null)
const targetId = ref(null)
const mode = ref('full')
const saving = ref(false)

const load = async () => {
  const [d, t] = await Promise.allSettled([databaseAPI.list(), opsAPI.listTasks()])
  if (d.status === 'fulfilled') dbs.value = d.value.databases || []
  if (t.status === 'fulfilled') tasks.value = (t.value.tasks || []).filter(x => x.category === 'database' && x.action === 'data-migration')
}

const createTask = async () => {
  if (!sourceId.value || !targetId.value) {
    ElMessage.warning('请选择源库和目标库')
    return
  }
  saving.value = true
  try {
    await opsAPI.createTask({
      category: 'database',
      action: 'data-migration',
      payload: { source_id: sourceId.value, target_id: targetId.value, mode: mode.value }
    })
    ElMessage.success('已创建迁移任务（演示模式）')
    await load()
  } catch (e) {
    ElMessage.error(e.message || '创建失败')
  } finally {
    saving.value = false
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
.muted {
  color: #64748b;
}
</style>
