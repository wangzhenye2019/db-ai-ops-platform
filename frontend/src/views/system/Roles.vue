<template>
  <div class="page">
    <div class="title-row">
      <div class="title">角色管理</div>
      <el-button type="primary" @click="openCreate">新建角色</el-button>
    </div>

    <el-card class="card">
      <el-table :data="roles" stripe>
        <el-table-column prop="name" label="角色名" width="180" />
        <el-table-column prop="description" label="描述" min-width="240" />
        <el-table-column label="权限" min-width="400">
          <template #default="{ row }">
            <el-tag v-for="p in (row.permissions || []).slice(0, 6)" :key="p" class="tag" type="info" size="small">{{ p }}</el-tag>
            <span v-if="(row.permissions || []).length > 6" class="muted"> +{{ (row.permissions || []).length - 6 }} 更多</span>
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
        <el-form-item label="角色名" prop="name">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" />
        </el-form-item>
        <el-form-item label="权限">
          <el-checkbox-group v-model="selectedPerms">
            <el-row :gutter="8">
              <el-col :span="8" v-for="cat in categories" :key="cat">
                <div class="perm-category">{{ cat }}</div>
                <el-checkbox v-for="p in getPermsByCategory(cat)" :key="p.id" :label="p.id" class="perm-check">
                  {{ p.name }}
                </el-checkbox>
              </el-col>
            </el-row>
          </el-checkbox-group>
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

const roles = ref([])
const permissions = ref([])
const dialogVisible = ref(false)
const saving = ref(false)
const formRef = ref()
const editingId = ref(null)

const form = reactive({
  name: '',
  description: ''
})
const selectedPerms = ref([])

const rules = {
  name: [{ required: true, message: '请输入角色名', trigger: 'blur' }]
}

const dialogTitle = computed(() => editingId.value ? '编辑角色' : '新建角色')

const categories = computed(() => {
  const cats = new Set(permissions.value.map(p => p.category).filter(Boolean))
  return Array.from(cats)
})

const getPermsByCategory = (cat) => permissions.value.filter(p => p.category === cat)

const load = async () => {
  try {
    const [r, p] = await Promise.all([rbacAPI.listRoles(), rbacAPI.listPermissions()])
    roles.value = r.roles || []
    permissions.value = p.permissions || []
  } catch (e) {
    ElMessage.error(e.message || '加载失败')
  }
}

const resetForm = () => {
  editingId.value = null
  form.name = ''
  form.description = ''
  selectedPerms.value = []
  formRef.value?.clearValidate?.()
}

const openCreate = () => {
  resetForm()
  dialogVisible.value = true
}

const openEdit = (row) => {
  editingId.value = row.id
  form.name = row.name || ''
  form.description = row.description || ''
  selectedPerms.value = permissions.value.filter(p => (row.permissions || []).includes(p.code)).map(p => p.id)
  dialogVisible.value = true
}

const onSave = async () => {
  await formRef.value?.validate(async (valid) => {
    if (!valid) return
    saving.value = true
    try {
      const payload = {
        name: form.name,
        description: form.description,
        permission_ids: selectedPerms.value
      }
      if (editingId.value) {
        await rbacAPI.updateRole(editingId.value, payload)
      } else {
        await rbacAPI.createRole(payload)
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
    await ElMessageBox.confirm(`确认删除角色「${row.name}」？`, '提示', { type: 'warning' })
    await rbacAPI.deleteRole(row.id)
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
.perm-category { font-weight: 600; margin: 8px 0 4px; color: #475569; }
.perm-check { display: block; margin: 4px 0; }
</style>
