<template>
  <div class="page">
    <div class="title-row">
      <div class="title">机房/区域字典</div>
      <div class="actions">
        <el-button @click="load">刷新</el-button>
        <el-button type="primary" @click="openCreate">新建机房</el-button>
      </div>
    </div>

    <el-card class="card">
      <el-table :data="idcs" stripe>
        <el-table-column prop="region" label="区域" width="160" />
        <el-table-column prop="name" label="机房" min-width="200" />
        <el-table-column prop="remark" label="备注" min-width="220" />
        <el-table-column label="操作" width="220">
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
            <el-form-item label="区域">
              <el-input v-model="form.region" placeholder="例如：北京/上海/华南" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="机房" prop="name">
              <el-input v-model="form.name" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="备注">
          <el-input v-model="form.remark" />
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
import { dictAPI } from '@/api/services'

const idcs = ref([])
const dialogVisible = ref(false)
const saving = ref(false)
const formRef = ref()
const editingId = ref(null)

const form = reactive({
  region: '',
  name: '',
  remark: ''
})

const rules = {
  name: [{ required: true, message: '请输入机房名称', trigger: 'blur' }]
}

const dialogTitle = computed(() => (editingId.value ? '编辑机房' : '新建机房'))

const load = async () => {
  try {
    const data = await dictAPI.listIdcs()
    idcs.value = data.idcs || []
  } catch (e) {
    ElMessage.error(e.message || '加载失败')
  }
}

const openCreate = () => {
  editingId.value = null
  form.region = ''
  form.name = ''
  form.remark = ''
  dialogVisible.value = true
  formRef.value?.clearValidate?.()
}

const openEdit = (row) => {
  editingId.value = row.id
  form.region = row.region || ''
  form.name = row.name || ''
  form.remark = row.remark || ''
  dialogVisible.value = true
  formRef.value?.clearValidate?.()
}

const onSave = async () => {
  await formRef.value?.validate(async (valid) => {
    if (!valid) return
    saving.value = true
    try {
      const payload = { region: form.region || null, name: form.name, remark: form.remark || null }
      if (editingId.value) {
        await dictAPI.updateIdc(editingId.value, payload)
      } else {
        await dictAPI.createIdc(payload)
      }
      ElMessage.success('保存成功')
      dialogVisible.value = false
      await load()
    } catch (e) {
      ElMessage.error(e.message || '保存失败（需要管理员权限）')
    } finally {
      saving.value = false
    }
  })
}

const onDelete = async (row) => {
  try {
    await ElMessageBox.confirm(`确认删除机房「${row.name}」？`, '提示', { type: 'warning' })
    await dictAPI.deleteIdc(row.id)
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
</style>
