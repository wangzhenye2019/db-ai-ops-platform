<template>
  <div class="page">
    <div class="title-row">
      <div class="title">资产分组</div>
      <div class="actions">
        <el-button @click="load">刷新</el-button>
        <el-button type="primary" @click="openCreate">新建分组</el-button>
      </div>
    </div>

    <el-card class="card">
      <el-table :data="groups" stripe>
        <el-table-column prop="name" label="名称" min-width="220" />
        <el-table-column prop="description" label="描述" min-width="260" />
        <el-table-column label="成员" width="220">
          <template #default="{ row }">
            <el-tag class="tag" type="info">主机 {{ row.counts?.host || 0 }}</el-tag>
            <el-tag class="tag" type="info">数据库 {{ row.counts?.database || 0 }}</el-tag>
            <el-tag class="tag" type="info">中间件 {{ row.counts?.middleware || 0 }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="240">
          <template #default="{ row }">
            <el-button text @click="openMembers(row)">成员</el-button>
            <el-button text @click="openEdit(row)">编辑</el-button>
            <el-button text type="danger" @click="onDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="560px">
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible=false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="onSave">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="membersVisible" :title="membersTitle" width="860px">
      <el-tabs v-model="memberTab">
        <el-tab-pane label="主机" name="host">
          <el-select v-model="selectHostIds" multiple filterable style="width:100%" placeholder="选择主机加入分组">
            <el-option v-for="h in hosts" :key="h.id" :label="`${h.name} (${h.host}:${h.port})`" :value="h.id" />
          </el-select>
        </el-tab-pane>
        <el-tab-pane label="数据库" name="database">
          <el-select v-model="selectDbIds" multiple filterable style="width:100%" placeholder="选择数据库加入分组">
            <el-option v-for="d in databases" :key="d.id" :label="`${d.name} (${d.db_type}@${d.host}:${d.port}/${d.database})`" :value="d.id" />
          </el-select>
        </el-tab-pane>
        <el-tab-pane label="中间件" name="middleware">
          <el-select v-model="selectMwIds" multiple filterable style="width:100%" placeholder="选择中间件加入分组">
            <el-option v-for="m in middlewares" :key="m.id" :label="`${m.name} (${m.mw_type}@${m.host}:${m.port})`" :value="m.id" />
          </el-select>
        </el-tab-pane>
      </el-tabs>

      <div class="member-actions">
        <el-button @click="loadMembers">刷新成员</el-button>
        <el-button type="primary" :loading="savingMembers" @click="addSelected">加入分组</el-button>
      </div>

      <el-table :data="members" stripe class="members-table">
        <el-table-column prop="asset_type" label="类型" width="120" />
        <el-table-column prop="label" label="资产" min-width="420" />
        <el-table-column label="操作" width="140">
          <template #default="{ row }">
            <el-button text type="danger" @click="removeMember(row)">移除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <template #footer>
        <el-button @click="membersVisible=false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { assetsAPI, databaseAPI, hostAPI, middlewareAPI } from '@/api/services'

const groups = ref([])
const saving = ref(false)
const dialogVisible = ref(false)
const formRef = ref()
const editingId = ref(null)

const form = reactive({
  name: '',
  description: ''
})

const rules = {
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }]
}

const dialogTitle = computed(() => (editingId.value ? '编辑分组' : '新建分组'))

const load = async () => {
  const data = await assetsAPI.listGroups()
  groups.value = data.groups || []
}

const openCreate = () => {
  editingId.value = null
  form.name = ''
  form.description = ''
  dialogVisible.value = true
  formRef.value?.clearValidate?.()
}

const openEdit = (row) => {
  editingId.value = row.id
  form.name = row.name || ''
  form.description = row.description || ''
  dialogVisible.value = true
  formRef.value?.clearValidate?.()
}

const onSave = async () => {
  await formRef.value?.validate(async (valid) => {
    if (!valid) return
    saving.value = true
    try {
      if (editingId.value) {
        await assetsAPI.updateGroup(editingId.value, { name: form.name, description: form.description })
      } else {
        await assetsAPI.createGroup({ name: form.name, description: form.description })
      }
      ElMessage.success('保存成功')
      dialogVisible.value = false
      await load()
    } catch (e) {
      ElMessage.error(e.message || '保存失败')
    } finally {
      saving.value = false
    }
  })
}

const onDelete = async (row) => {
  try {
    await ElMessageBox.confirm(`确认删除分组「${row.name}」？`, '提示', { type: 'warning' })
    await assetsAPI.deleteGroup(row.id)
    ElMessage.success('已删除')
    await load()
  } catch {
  }
}

const membersVisible = ref(false)
const membersGroupId = ref(null)
const membersTitle = computed(() => {
  const g = groups.value.find(x => x.id === membersGroupId.value)
  return g ? `分组成员 - ${g.name}` : '分组成员'
})

const members = ref([])
const savingMembers = ref(false)
const memberTab = ref('host')

const hosts = ref([])
const databases = ref([])
const middlewares = ref([])

const selectHostIds = ref([])
const selectDbIds = ref([])
const selectMwIds = ref([])

const openMembers = async (row) => {
  membersGroupId.value = row.id
  membersVisible.value = true
  selectHostIds.value = []
  selectDbIds.value = []
  selectMwIds.value = []
  await Promise.all([loadAssets(), loadMembers()])
}

const loadAssets = async () => {
  const [h, d, m] = await Promise.allSettled([hostAPI.list(), databaseAPI.list(), middlewareAPI.list()])
  if (h.status === 'fulfilled') hosts.value = h.value.hosts || []
  if (d.status === 'fulfilled') databases.value = d.value.databases || []
  if (m.status === 'fulfilled') middlewares.value = m.value.middlewares || []
}

const loadMembers = async () => {
  if (!membersGroupId.value) return
  const data = await assetsAPI.listGroupMembers(membersGroupId.value)
  members.value = data.members || []
}

const addSelected = async () => {
  if (!membersGroupId.value) return
  const add = []
  for (const id of selectHostIds.value) add.push({ type: 'host', id })
  for (const id of selectDbIds.value) add.push({ type: 'database', id })
  for (const id of selectMwIds.value) add.push({ type: 'middleware', id })
  if (!add.length) {
    ElMessage.warning('请选择要加入的资产')
    return
  }
  savingMembers.value = true
  try {
    await assetsAPI.updateGroupMembers(membersGroupId.value, { add })
    ElMessage.success('已加入')
    selectHostIds.value = []
    selectDbIds.value = []
    selectMwIds.value = []
    await Promise.all([loadMembers(), load()])
  } catch (e) {
    ElMessage.error(e.message || '操作失败')
  } finally {
    savingMembers.value = false
  }
}

const removeMember = async (row) => {
  if (!membersGroupId.value) return
  savingMembers.value = true
  try {
    await assetsAPI.updateGroupMembers(membersGroupId.value, { remove: [{ type: row.asset_type, id: row.asset_id }] })
    ElMessage.success('已移除')
    await Promise.all([loadMembers(), load()])
  } catch (e) {
    ElMessage.error(e.message || '操作失败')
  } finally {
    savingMembers.value = false
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
.actions {
  display: flex;
  gap: 10px;
}
.card {
  margin: 0 8px;
}
.tag {
  margin-right: 6px;
}
.member-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin: 12px 0;
}
.members-table {
  margin-top: 10px;
}
</style>
