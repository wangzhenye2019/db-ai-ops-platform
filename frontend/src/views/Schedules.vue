<template>
  <div class="schedules">
    <div class="header">
      <h2>定时任务</h2>
      <el-button type="primary" @click="showAddDialog = true">
        <el-icon><Plus /></el-icon>
        添加定时任务
      </el-button>
    </div>

    <el-table :data="schedules" stripe>
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column label="数据库" width="150">
        <template #default="{ row }">
          {{ getDatabaseName(row.database_id) }}
        </template>
      </el-table-column>
      <el-table-column prop="cron_expression" label="Cron表达式" width="150" />
      <el-table-column label="下次执行" width="170">
        <template #default="{ row }">
          {{ formatDate(row.next_run) }}
        </template>
      </el-table-column>
      <el-table-column label="上次执行" width="170">
        <template #default="{ row }">
          {{ formatDate(row.last_run) }}
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.enabled ? 'success' : 'info'">
            {{ row.enabled ? '启用' : '禁用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200">
        <template #default="{ row }">
          <el-button size="small" @click="toggleSchedule(row)">
            {{ row.enabled ? '禁用' : '启用' }}
          </el-button>
          <el-button size="small" type="primary" @click="editSchedule(row)">编辑</el-button>
          <el-button size="small" type="danger" @click="deleteSchedule(row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- Add/Edit Dialog -->
    <el-dialog
      v-model="showAddDialog"
      :title="editingSchedule ? '编辑定时任务' : '添加定时任务'"
      width="600px"
    >
      <el-form :model="form" :rules="rules" ref="formRef" label-width="120px">
        <el-form-item label="数据库" prop="database_id">
          <el-select v-model="form.database_id" placeholder="选择数据库">
            <el-option
              v-for="db in enabledDatabases"
              :key="db.id"
              :label="db.name"
              :value="db.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="Cron表达式" prop="cron_expression">
          <el-input v-model="form.cron_expression" placeholder="0 2 * * *" />
          <div class="cron-hint">格式: 分 时 日 月 周 (例如: 0 2 * * * 表示每天2点)</div>
        </el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="form.enabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button @click="showCronHelp">帮助</el-button>
        <el-button type="primary" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>

    <!-- Cron Help Dialog -->
    <el-dialog v-model="showCronDialog" title="Cron表达式帮助" width="700px">
      <div class="cron-help">
        <h3>格式说明</h3>
        <p>Cron表达式格式: <code>分 时 日 月 周</code></p>

        <h3>字段说明</h3>
        <el-table :data="cronFields" size="small">
          <el-table-column prop="name" label="字段" width="100" />
          <el-table-column prop="range" label="范围" width="150" />
          <el-table-column prop="description" label="说明" />
        </el-table>

        <h3>示例</h3>
        <el-table :data="cronExamples" size="small">
          <el-table-column prop="expression" label="表达式" width="200" />
          <el-table-column prop="description" label="说明" />
        </el-table>
      </div>
      <template #footer>
        <el-button type="primary" @click="showCronDialog = false">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { scheduleAPI, databaseAPI } from '@/api/services'

const schedules = ref([])
const databases = ref([])
const showAddDialog = ref(false)
const showCronDialog = ref(false)
const editingSchedule = ref(null)
const formRef = ref(null)

const form = ref({
  database_id: null,
  cron_expression: '0 2 * * *',
  enabled: true
})

const rules = {
  database_id: [{ required: true, message: '请选择数据库', trigger: 'change' }],
  cron_expression: [{ required: true, message: '请输入Cron表达式', trigger: 'blur' }]
}

const cronFields = [
  { name: '分钟', range: '0-59', description: '每小时的第几分钟' },
  { name: '小时', range: '0-23', description: '一天的第几小时' },
  { name: '日期', range: '1-31', description: '每月的第几天' },
  { name: '月份', range: '1-12', description: '一年中的第几个月' },
  { name: '星期', range: '0-6', description: '一周中的第几天 (0=周日)' }
]

const cronExamples = [
  { expression: '0 2 * * *', description: '每天凌晨2点执行' },
  { expression: '0 */6 * * *', description: '每6小时执行一次' },
  { expression: '0 0 * * 0', description: '每周日午夜执行' },
  { expression: '0 2 * * 1', description: '每周一凌晨2点执行' },
  { expression: '30 3 1 * *', description: '每月1日凌晨3:30执行' },
  { expression: '0 9 * * 1-5', description: '周一到周五每天早上9点执行' }
]

const enabledDatabases = computed(() => {
  return databases.value.filter(db => db.enabled)
})

const loadSchedules = async () => {
  try {
    const data = await scheduleAPI.list()
    schedules.value = data.schedules
  } catch (error) {
    ElMessage.error('加载定时任务失败')
  }
}

const loadDatabases = async () => {
  try {
    const data = await databaseAPI.list()
    databases.value = data.databases
  } catch (error) {
    console.error('Failed to load databases:', error)
  }
}

const getDatabaseName = (id) => {
  const db = databases.value.find(d => d.id === id)
  return db ? db.name : `ID: ${id}`
}

const editSchedule = (schedule) => {
  editingSchedule.value = schedule
  form.value = {
    database_id: schedule.database_id,
    cron_expression: schedule.cron_expression,
    enabled: schedule.enabled
  }
  showAddDialog.value = true
}

const handleSubmit = async () => {
  if (!formRef.value) return

  await formRef.value.validate(async (valid) => {
    if (valid) {
      try {
        if (editingSchedule.value) {
          await scheduleAPI.update(editingSchedule.value.id, form.value)
          ElMessage.success('更新成功')
        } else {
          await scheduleAPI.create(form.value)
          ElMessage.success('添加成功')
        }
        showAddDialog.value = false
        editingSchedule.value = null
        loadSchedules()
      } catch (error) {
        ElMessage.error('操作失败')
      }
    }
  })
}

const deleteSchedule = async (id) => {
  try {
    await ElMessageBox.confirm('确定要删除这个定时任务吗？', '警告', {
      type: 'warning'
    })
    await scheduleAPI.delete(id)
    ElMessage.success('删除成功')
    loadSchedules()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

const toggleSchedule = async (schedule) => {
  try {
    await scheduleAPI.toggle(schedule.id)
    ElMessage.success(schedule.enabled ? '已禁用' : '已启用')
    loadSchedules()
  } catch (error) {
    ElMessage.error('操作失败')
  }
}

const showCronHelp = () => {
  showCronDialog.value = true
}

const formatDate = (date) => {
  if (!date) return '-'
  return new Date(date).toLocaleString('zh-CN')
}

onMounted(() => {
  loadSchedules()
  loadDatabases()
})
</script>

<style scoped>
.schedules {
  padding: 20px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.cron-hint {
  font-size: 12px;
  color: #909399;
  margin-top: 5px;
}

.cron-help h3 {
  margin: 20px 0 10px;
}

.cron-help code {
  background: #f5f7fa;
  padding: 2px 6px;
  border-radius: 3px;
  font-family: monospace;
}
</style>
