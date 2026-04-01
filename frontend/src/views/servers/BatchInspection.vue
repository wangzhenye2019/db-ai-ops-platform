<template>
  <div class="page">
    <div class="title-row">
      <div class="title">批量巡检</div>
      <el-button type="primary" @click="openCreate">新建任务</el-button>
    </div>
    <el-card class="card">
      <el-table :data="tasks" stripe>
        <el-table-column prop="id" label="ID" width="90" />
        <el-table-column prop="status" label="状态" width="120" />
        <el-table-column prop="created_at" label="创建时间" min-width="180" />
        <el-table-column label="范围" min-width="220">
          <template #default="{ row }">
            <span class="muted">{{ (row.payload?.target_ids || []).length }} 台主机</span>
          </template>
        </el-table-column>
        <el-table-column label="结果" min-width="260">
          <template #default="{ row }">
            <span class="muted">{{ row.result?.message || '-' }}</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" title="新建批量巡检任务" width="560px">
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
        <el-form-item label="目标主机" prop="target_ids">
          <el-select v-model="form.target_ids" multiple filterable style="width:100%" placeholder="选择主机">
            <el-option v-for="h in hosts" :key="h.id" :label="`${h.name} (${h.host})`" :value="h.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="巡检项（演示）">
          <el-checkbox-group v-model="form.items">
            <el-checkbox label="connectivity">连通性</el-checkbox>
            <el-checkbox label="disk">磁盘</el-checkbox>
            <el-checkbox label="cpu">CPU</el-checkbox>
            <el-checkbox label="memory">内存</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible=false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="onSave">提交</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { hostAPI, opsAPI } from '@/api/services'

const tasks = ref([])
const hosts = ref([])

const dialogVisible = ref(false)
const saving = ref(false)
const formRef = ref()

const form = reactive({
  target_ids: [],
  items: ['connectivity', 'disk', 'cpu', 'memory']
})

const rules = {
  target_ids: [{ required: true, message: '请选择目标主机', trigger: 'change' }]
}

const load = async () => {
  const [t, h] = await Promise.allSettled([opsAPI.listTasks(), hostAPI.list()])
  if (t.status === 'fulfilled') tasks.value = (t.value.tasks || []).filter(x => x.category === 'server' && x.action === 'batch-inspection')
  if (h.status === 'fulfilled') hosts.value = h.value.hosts || []
}

const openCreate = () => {
  form.target_ids = []
  form.items = ['connectivity', 'disk', 'cpu', 'memory']
  dialogVisible.value = true
  formRef.value?.clearValidate?.()
}

const onSave = async () => {
  await formRef.value?.validate(async (valid) => {
    if (!valid) return
    saving.value = true
    try {
      await opsAPI.createTask({
        category: 'server',
        action: 'batch-inspection',
        payload: { target_ids: form.target_ids, items: form.items }
      })
      ElMessage.success('已提交任务')
      dialogVisible.value = false
      await load()
    } catch (e) {
      ElMessage.error(e.message || '提交失败')
    } finally {
      saving.value = false
    }
  })
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
