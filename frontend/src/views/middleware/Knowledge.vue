<template>
  <div class="page">
    <div class="title-row">
      <div class="title">中间件知识库</div>
      <el-button type="primary" @click="openCreate">新建文章</el-button>
    </div>
    <el-card class="card">
      <el-table :data="articles" stripe>
        <el-table-column prop="title" label="标题" min-width="240" />
        <el-table-column prop="category" label="分类" width="160" />
        <el-table-column label="标签" min-width="200">
          <template #default="{ row }">
            <el-tag v-for="t in (row.tags || [])" :key="t" class="tag" type="info">{{ t }}</el-tag>
            <span v-if="!(row.tags || []).length" class="muted">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" min-width="180" />
        <el-table-column label="操作" width="200">
          <template #default="{ row }">
            <el-button text @click="openEdit(row)">编辑</el-button>
            <el-button text type="danger" @click="onDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="720px">
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
        <el-form-item label="标题" prop="title">
          <el-input v-model="form.title" />
        </el-form-item>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="分类">
              <el-input v-model="form.category" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="标签（逗号分隔）">
              <el-input v-model="form.tagsText" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="内容">
          <el-input v-model="form.content" type="textarea" :rows="10" />
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
import { kbAPI } from '@/api/services'

const articles = ref([])
const dialogVisible = ref(false)
const saving = ref(false)
const formRef = ref()
const editingId = ref(null)

const form = reactive({
  title: '',
  category: '',
  tagsText: '',
  content: ''
})

const rules = {
  title: [{ required: true, message: '请输入标题', trigger: 'blur' }]
}

const dialogTitle = computed(() => (editingId.value ? '编辑文章' : '新建文章'))

const load = async () => {
  const data = await kbAPI.listArticles({ scope: 'middleware' })
  articles.value = data.articles || []
}

const resetForm = () => {
  editingId.value = null
  form.title = ''
  form.category = ''
  form.tagsText = ''
  form.content = ''
  formRef.value?.clearValidate?.()
}

const openCreate = () => {
  resetForm()
  dialogVisible.value = true
}

const openEdit = (row) => {
  editingId.value = row.id
  form.title = row.title || ''
  form.category = row.category || ''
  form.tagsText = (row.tags || []).join(',')
  form.content = row.content || ''
  dialogVisible.value = true
}

const onSave = async () => {
  await formRef.value?.validate(async (valid) => {
    if (!valid) return
    saving.value = true
    try {
      const payload = {
        scope: 'middleware',
        title: form.title,
        category: form.category || null,
        tags: form.tagsText.split(',').map(s => s.trim()).filter(Boolean),
        content: form.content
      }
      if (editingId.value) {
        await kbAPI.updateArticle(editingId.value, payload)
      } else {
        await kbAPI.createArticle(payload)
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
    await ElMessageBox.confirm(`确认删除文章「${row.title}」？`, '提示', { type: 'warning' })
    await kbAPI.deleteArticle(row.id)
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
