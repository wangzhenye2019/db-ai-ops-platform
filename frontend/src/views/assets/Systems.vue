<template>
  <div class="page">
    <div class="title-row">
      <div class="title">业务系统管理</div>
      <div class="actions">
        <el-button @click="load">刷新</el-button>
        <el-button type="primary" @click="openCreate">新建业务系统</el-button>
      </div>
    </div>

    <el-card class="card">
      <el-table :data="systems" stripe>
        <el-table-column prop="name" label="名称" min-width="200" />
        <el-table-column prop="code" label="编码" width="160" />
        <el-table-column prop="owner" label="负责人" width="140" />
        <el-table-column prop="owner_contact" label="联系方式" width="160" />
        <el-table-column label="资产" width="260">
          <template #default="{ row }">
            <el-tag class="tag" type="info">主机 {{ row.counts?.hosts || 0 }}</el-tag>
            <el-tag class="tag" type="info">数据库 {{ row.counts?.databases || 0 }}</el-tag>
            <el-tag class="tag" type="info">中间件 {{ row.counts?.middlewares || 0 }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="启用" width="100">
          <template #default="{ row }">
            <el-tag :type="row.enabled ? 'success' : 'info'">{{ row.enabled ? '是' : '否' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220">
          <template #default="{ row }">
            <el-button text @click="openEdit(row)">编辑</el-button>
            <el-button text type="danger" @click="onDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="620px">
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="名称" prop="name">
              <el-input v-model="form.name" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="编码">
              <el-input v-model="form.code" placeholder="可选，建议唯一" />
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
            <el-form-item label="联系方式">
              <el-input v-model="form.owner_contact" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="标签（逗号分隔）">
          <el-input v-model="form.tagsText" />
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
import { systemsAPI } from '@/api/services'

const systems = ref([])
const dialogVisible = ref(false)
const saving = ref(false)
const formRef = ref()
const editingId = ref(null)

const form = reactive({
  name: '',
  code: '',
  owner: '',
  owner_contact: '',
  description: '',
  tagsText: '',
  enabled: true
})

const rules = {
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }]
}

const dialogTitle = computed(() => (editingId.value ? '编辑业务系统' : '新建业务系统'))

const load = async () => {
  const data = await systemsAPI.list()
  systems.value = data.systems || []
}

const resetForm = () => {
  editingId.value = null
  form.name = ''
  form.code = ''
  form.owner = ''
  form.owner_contact = ''
  form.description = ''
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
  form.code = row.code || ''
  form.owner = row.owner || ''
  form.owner_contact = row.owner_contact || ''
  form.description = row.description || ''
  form.tagsText = (row.tags || []).join(',')
  form.enabled = !!row.enabled
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
        code: form.code || null,
        owner: form.owner || null,
        owner_contact: form.owner_contact || null,
        description: form.description || null,
        tags: form.tagsText.split(',').map(s => s.trim()).filter(Boolean),
        enabled: form.enabled
      }
      if (editingId.value) {
        await systemsAPI.update(editingId.value, payload)
      } else {
        await systemsAPI.create(payload)
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
    await ElMessageBox.confirm(`确认删除业务系统「${row.name}」？`, '提示', { type: 'warning' })
    await systemsAPI.delete(row.id)
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
</style>
