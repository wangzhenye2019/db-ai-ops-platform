<template>
  <div class="page">
    <div class="title-row">
      <div class="title">标签体系</div>
      <div class="actions">
        <el-button @click="load">刷新</el-button>
        <el-button type="primary" @click="openCreate">新建标签</el-button>
      </div>
    </div>

    <el-card class="card">
      <el-table :data="tags" stripe>
        <el-table-column prop="name" label="标签" min-width="220" />
        <el-table-column prop="category" label="分类" width="140" />
        <el-table-column prop="created_at" label="创建时间" min-width="200" />
        <el-table-column label="操作" width="160">
          <template #default="{ row }">
            <el-button text type="danger" @click="onDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" title="新建标签" width="520px">
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
        <el-form-item label="标签" prop="name">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="分类">
          <el-select v-model="form.category" style="width:100%">
            <el-option label="资产" value="asset" />
            <el-option label="业务系统" value="system" />
          </el-select>
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
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { dictAPI } from '@/api/services'

const tags = ref([])
const dialogVisible = ref(false)
const saving = ref(false)
const formRef = ref()

const form = reactive({
  name: '',
  category: 'asset'
})

const rules = {
  name: [{ required: true, message: '请输入标签', trigger: 'blur' }]
}

const load = async () => {
  try {
    const data = await dictAPI.listTags()
    tags.value = data.tags || []
  } catch (e) {
    ElMessage.error(e.message || '加载失败')
  }
}

const openCreate = () => {
  form.name = ''
  form.category = 'asset'
  dialogVisible.value = true
  formRef.value?.clearValidate?.()
}

const onSave = async () => {
  await formRef.value?.validate(async (valid) => {
    if (!valid) return
    saving.value = true
    try {
      await dictAPI.createTag({ name: form.name, category: form.category })
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
    await ElMessageBox.confirm(`确认删除标签「${row.name}」？`, '提示', { type: 'warning' })
    await dictAPI.deleteTag(row.id)
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
