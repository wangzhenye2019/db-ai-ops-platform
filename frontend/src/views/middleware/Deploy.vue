<template>
  <div class="page">
    <div class="title-row">
      <div class="title">中间件部署</div>
      <el-button type="primary" @click="openCreate">新增中间件</el-button>
    </div>
    <el-card class="card">
      <el-table :data="items" stripe>
        <el-table-column prop="name" label="名称" min-width="160" />
        <el-table-column prop="mw_type" label="类型" width="150" />
        <el-table-column prop="host" label="主机" min-width="160" />
        <el-table-column prop="port" label="端口" width="90" />
        <el-table-column prop="version" label="版本" width="120" />
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

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="560px">
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="名称" prop="name">
              <el-input v-model="form.name" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="类型" prop="mw_type">
              <el-select v-model="form.mw_type" style="width:100%">
                <el-option v-for="t in types" :key="t.value" :label="t.label" :value="t.value" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="主机" prop="host">
              <el-input v-model="form.host" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="端口" prop="port">
              <el-input-number v-model="form.port" :min="1" :max="65535" style="width:100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="版本">
              <el-input v-model="form.version" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="启用">
              <el-switch v-model="form.enabled" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="元数据（JSON）">
          <el-input v-model="form.meta" type="textarea" :rows="4" placeholder='例如：{"cluster":"c1"}' />
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
import { middlewareAPI } from '@/api/services'

const items = ref([])
const types = ref([{ value: 'other', label: 'OTHER' }])

const dialogVisible = ref(false)
const saving = ref(false)
const formRef = ref()
const editingId = ref(null)

const form = reactive({
  name: '',
  mw_type: 'other',
  host: '',
  port: 6379,
  version: '',
  enabled: true,
  meta: ''
})

const rules = {
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  mw_type: [{ required: true, message: '请选择类型', trigger: 'change' }],
  host: [{ required: true, message: '请输入主机', trigger: 'blur' }],
  port: [{ required: true, message: '请输入端口', trigger: 'blur' }]
}

const dialogTitle = computed(() => (editingId.value ? '编辑中间件' : '新增中间件'))

const load = async () => {
  const [listRes, typeRes] = await Promise.allSettled([middlewareAPI.list(), middlewareAPI.getTypes()])
  if (listRes.status === 'fulfilled') items.value = listRes.value.middlewares || []
  if (typeRes.status === 'fulfilled') types.value = typeRes.value.types || types.value
}

const resetForm = () => {
  editingId.value = null
  form.name = ''
  form.mw_type = 'other'
  form.host = ''
  form.port = 6379
  form.version = ''
  form.enabled = true
  form.meta = ''
  formRef.value?.clearValidate?.()
}

const openCreate = () => {
  resetForm()
  dialogVisible.value = true
}

const openEdit = (row) => {
  editingId.value = row.id
  form.name = row.name || ''
  form.mw_type = row.mw_type || 'other'
  form.host = row.host || ''
  form.port = row.port || 0
  form.version = row.version || ''
  form.enabled = !!row.enabled
  form.meta = row.meta ? JSON.stringify(row.meta) : ''
  dialogVisible.value = true
}

const onSave = async () => {
  await formRef.value?.validate(async (valid) => {
    if (!valid) return
    saving.value = true
    try {
      let metaObj = {}
      if (form.meta.trim()) metaObj = JSON.parse(form.meta)
      const payload = {
        name: form.name,
        mw_type: form.mw_type,
        host: form.host,
        port: form.port,
        version: form.version || null,
        enabled: form.enabled,
        meta: metaObj
      }
      if (editingId.value) {
        await middlewareAPI.update(editingId.value, payload)
      } else {
        await middlewareAPI.create(payload)
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
    await ElMessageBox.confirm(`确认删除中间件「${row.name}」？`, '提示', { type: 'warning' })
    await middlewareAPI.delete(row.id)
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
</style>
