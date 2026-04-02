<template>
  <div class="page">
    <div class="title-row">
      <div class="title">账号/凭据库</div>
      <div class="actions">
        <el-button @click="load">刷新</el-button>
        <el-button type="primary" @click="openCreate">新建凭据</el-button>
      </div>
    </div>

    <el-card class="card">
      <el-alert type="info" show-icon :closable="false" title="明文仅管理员可查看/编辑；列表不返回密文。"/>
      <el-table :data="items" stripe class="table">
        <el-table-column prop="name" label="名称" min-width="220" />
        <el-table-column prop="cred_type" label="类型" width="140" />
        <el-table-column prop="username" label="用户名" width="160" />
        <el-table-column prop="business_system_name" label="业务系统" min-width="160" />
        <el-table-column prop="owner" label="负责人" width="120" />
        <el-table-column label="启用" width="100">
          <template #default="{ row }">
            <el-tag :type="row.enabled ? 'success' : 'info'">{{ row.enabled ? '是' : '否' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="240">
          <template #default="{ row }">
            <el-button text @click="viewSecret(row)">查看</el-button>
            <el-button text @click="openEdit(row)">编辑</el-button>
            <el-button text type="danger" @click="onDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="640px">
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="名称" prop="name">
              <el-input v-model="form.name" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="类型" prop="cred_type">
              <el-select v-model="form.cred_type" style="width:100%">
                <el-option v-for="t in types" :key="t.value" :label="t.label" :value="t.value" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="用户名">
              <el-input v-model="form.username" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="业务系统">
              <el-select v-model="form.business_system_id" clearable filterable style="width:100%">
                <el-option v-for="s in systems" :key="s.id" :label="s.name" :value="s.id" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="负责人">
              <el-input v-model="form.owner" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="启用">
              <el-switch v-model="form.enabled" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="标签（逗号分隔）">
          <el-input v-model="form.tagsText" />
        </el-form-item>
        <el-form-item label="密钥/密码" prop="secret">
          <el-input v-model="form.secret" type="password" show-password :placeholder="editingId ? '留空表示不修改' : '必填'" />
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
import { credsAPI, systemsAPI } from '@/api/services'

const items = ref([])
const types = ref([])
const systems = ref([])

const dialogVisible = ref(false)
const saving = ref(false)
const formRef = ref()
const editingId = ref(null)

const form = reactive({
  name: '',
  cred_type: 'generic',
  username: '',
  business_system_id: null,
  owner: '',
  enabled: true,
  tagsText: '',
  secret: ''
})

const rules = {
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  cred_type: [{ required: true, message: '请选择类型', trigger: 'change' }],
  secret: [{ required: true, message: '请输入密钥/密码', trigger: 'blur' }]
}

const dialogTitle = computed(() => (editingId.value ? '编辑凭据' : '新建凭据'))

const load = async () => {
  try {
    const [c, t, s] = await Promise.all([credsAPI.list(), credsAPI.types(), systemsAPI.list()])
    items.value = c.credentials || []
    types.value = t.types || []
    systems.value = s.systems || []
  } catch (e) {
    ElMessage.error(e.message || '加载失败')
  }
}

const resetForm = () => {
  editingId.value = null
  form.name = ''
  form.cred_type = 'generic'
  form.username = ''
  form.business_system_id = null
  form.owner = ''
  form.enabled = true
  form.tagsText = ''
  form.secret = ''
  formRef.value?.clearValidate?.()
}

const openCreate = () => {
  resetForm()
  dialogVisible.value = true
}

const openEdit = (row) => {
  editingId.value = row.id
  form.name = row.name || ''
  form.cred_type = row.cred_type || 'generic'
  form.username = row.username || ''
  form.business_system_id = row.business_system_id || null
  form.owner = row.owner || ''
  form.enabled = !!row.enabled
  form.tagsText = (row.tags || []).join(',')
  form.secret = ''
  dialogVisible.value = true
  formRef.value?.clearValidate?.()
}

const onSave = async () => {
  await formRef.value?.validate(async (valid) => {
    if (!valid) return
    saving.value = true
    try {
      const payload = {
        name: form.name,
        cred_type: form.cred_type,
        username: form.username || null,
        business_system_id: form.business_system_id || null,
        owner: form.owner || null,
        enabled: form.enabled,
        tags: form.tagsText.split(',').map(s => s.trim()).filter(Boolean)
      }
      if (!editingId.value) payload.secret = form.secret
      if (editingId.value && form.secret) payload.secret = form.secret

      if (editingId.value) {
        await credsAPI.update(editingId.value, payload)
      } else {
        await credsAPI.create(payload)
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
    await ElMessageBox.confirm(`确认删除凭据「${row.name}」？`, '提示', { type: 'warning' })
    await credsAPI.delete(row.id)
    ElMessage.success('已删除')
    await load()
  } catch {
  }
}

const viewSecret = async (row) => {
  try {
    const data = await credsAPI.get(row.id, { include_secret: 1 })
    if (!data.secret) {
      ElMessage.warning('无权限或密钥为空')
      return
    }
    await ElMessageBox.alert(data.secret, `凭据 - ${row.name}`, { confirmButtonText: '关闭' })
  } catch (e) {
    ElMessage.error(e.message || '查看失败')
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
.table {
  margin-top: 10px;
}
</style>
