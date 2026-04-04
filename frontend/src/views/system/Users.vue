<template>
  <div class="page">
    <div class="title-row">
      <div class="title">用户管理</div>
      <el-button type="primary" @click="openCreate">新建用户</el-button>
    </div>

    <el-card class="card">
      <el-table :data="users" stripe>
        <el-table-column prop="username" label="用户名" width="180" />
        <el-table-column label="角色" min-width="240">
          <template #default="{ row }">
            <el-tag v-for="r in (row.roles || [])" :key="r.id" class="tag">{{ r.name }}</el-tag>
            <span v-if="!(row.roles || []).length" class="muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="启用" width="100">
          <template #default="{ row }">
            <el-tag :type="row.enabled ? 'success' : 'info'">{{ row.enabled ? '是' : '否' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180" />
        <el-table-column label="操作" width="200">
          <template #default="{ row }">
            <el-button text @click="openEdit(row)">编辑</el-button>
            <el-button text type="danger" @click="onDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="520px">
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" :disabled="!!editingId" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" type="password" show-password :placeholder="editingId ? '留空表示不修改' : '必填'" />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="form.roleIds" multiple filterable style="width:100%">
            <el-option v-for="r in roles" :key="r.id" :label="r.name" :value="r.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="form.enabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible=false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="onSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { rbacAPI } from '@/api/services'

const users = ref([])
const roles = ref([])
const dialogVisible = ref(false)
const saving = ref(false)
const formRef = ref()
const editingId = ref(null)

const form = reactive({
  username: '',
  password: '',
  roleIds: [],
  enabled: true
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

const dialogTitle = computed(() => editingId.value ? '编辑用户' : '新建用户')

const load = async () => {
  try {
    const [u, r] = await Promise.all([rbacAPI.listUsers(), rbacAPI.listRoles()])
    users.value = u.users || []
    roles.value = r.roles || []
  } catch (e) {
    ElMessage.error(e.message || '加载失败')
  }
}

const resetForm = () => {
  editingId.value = null
  form.username = ''
  form.password = ''
  form.roleIds = []
  form.enabled = true
  formRef.value?.clearValidate?.()
}

const openCreate = () => {
  resetForm()
  dialogVisible.value = true
}

const openEdit = (row) => {
  editingId.value = row.id
  form.username = row.username || ''
  form.password = ''
  form.roleIds = (row.roles || []).map(r => r.id)
  form.enabled = row.enabled
  dialogVisible.value = true
}

const onSave = async () => {
  await formRef.value?.validate(async (valid) => {
    if (!valid) return
    saving.value = true
    try {
      const payload = {
        username: form.username,
        role_ids: form.roleIds,
        enabled: form.enabled
      }
      if (form.password) payload.password = form.password

      if (editingId.value) {
        await rbacAPI.updateUser(editingId.value, payload)
      } else {
        await rbacAPI.createUser(payload)
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
    await ElMessageBox.confirm(`确认删除用户「${row.username}」？`, '提示', { type: 'warning' })
    await rbacAPI.deleteUser(row.id)
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
.tag { margin-right: 4px; }
.muted { color: #94a3b8; }
</style>
