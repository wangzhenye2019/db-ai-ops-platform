<template>
  <div class="page">
    <div class="title-row">
      <div class="title">主机添加</div>
      <el-button type="primary" @click="openCreate">新增主机</el-button>
    </div>
    <el-card class="card">
      <el-table :data="hosts" stripe>
        <el-table-column prop="name" label="名称" min-width="160" />
        <el-table-column prop="host" label="IP/域名" min-width="160" />
        <el-table-column prop="port" label="端口" width="90" />
        <el-table-column prop="os_type" label="类型" width="110" />
        <el-table-column label="标签" min-width="160">
          <template #default="{ row }">
            <el-tag v-for="t in (row.tags || [])" :key="t" class="tag" type="info">{{ t }}</el-tag>
            <span v-if="!(row.tags || []).length" class="muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="启用" width="90">
          <template #default="{ row }">
            <el-tag :type="row.enabled ? 'success' : 'info'">{{ row.enabled ? '是' : '否' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180">
          <template #default="{ row }">
            <el-button text @click="openEdit(row)">编辑</el-button>
            <el-button text type="danger" @click="onDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="520px">
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="IP/域名" prop="host">
          <el-input v-model="form.host" />
        </el-form-item>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="端口" prop="port">
              <el-input-number v-model="form.port" :min="1" :max="65535" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="类型" prop="os_type">
              <el-select v-model="form.os_type" style="width:100%">
                <el-option v-for="t in osTypes" :key="t.value" :label="t.label" :value="t.value" />
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
            <el-form-item label="密码">
              <el-input v-model="form.password" type="password" show-password />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="标签（逗号分隔）">
          <el-input v-model="form.tagsText" placeholder="例如：prod,db,linux" />
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
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { hostAPI } from '@/api/services'

const hosts = ref([])
const osTypes = ref([
  { value: 'linux', label: 'LINUX' },
  { value: 'windows', label: 'WINDOWS' }
])

const dialogVisible = ref(false)
const saving = ref(false)
const formRef = ref()
const editingId = ref(null)

const form = reactive({
  name: '',
  host: '',
  port: 22,
  os_type: 'linux',
  username: '',
  password: '',
  tagsText: '',
  enabled: true
})

const rules = {
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  host: [{ required: true, message: '请输入 IP/域名', trigger: 'blur' }],
  port: [{ required: true, message: '请输入端口', trigger: 'blur' }],
  os_type: [{ required: true, message: '请选择类型', trigger: 'change' }]
}

const dialogTitle = computed(() => (editingId.value ? '编辑主机' : '新增主机'))

const load = async () => {
  const [listRes, typesRes] = await Promise.allSettled([hostAPI.list(), hostAPI.getOsTypes()])
  if (listRes.status === 'fulfilled') hosts.value = listRes.value.hosts || []
  if (typesRes.status === 'fulfilled') osTypes.value = typesRes.value.types || osTypes.value
}

const resetForm = () => {
  editingId.value = null
  form.name = ''
  form.host = ''
  form.port = 22
  form.os_type = 'linux'
  form.username = ''
  form.password = ''
  form.tagsText = ''
  form.enabled = true
  formRef.value?.clearValidate?.()
}

const openCreate = () => {
  resetForm()
  dialogVisible.value = true
}

const openEdit = (row) => {
  editingId.value = row.id
  form.name = row.name || ''
  form.host = row.host || ''
  form.port = row.port || 22
  form.os_type = row.os_type || 'linux'
  form.username = row.username || ''
  form.password = ''
  form.tagsText = (row.tags || []).join(',')
  form.enabled = !!row.enabled
  dialogVisible.value = true
}

const onSave = async () => {
  await formRef.value?.validate(async (valid) => {
    if (!valid) return
    saving.value = true
    try {
      const payload = {
        name: form.name,
        host: form.host,
        port: form.port,
        os_type: form.os_type,
        username: form.username || null,
        password: form.password || null,
        enabled: form.enabled,
        tags: form.tagsText
          .split(',')
          .map(s => s.trim())
          .filter(Boolean)
      }
      if (editingId.value) {
        await hostAPI.update(editingId.value, payload)
      } else {
        await hostAPI.create(payload)
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
    await ElMessageBox.confirm(`确认删除主机「${row.name}」？`, '提示', { type: 'warning' })
    await hostAPI.delete(row.id)
    ElMessage.success('已删除')
    await load()
  } catch {
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
.tag {
  margin-right: 6px;
}
.muted {
  color: #94a3b8;
}
</style>
