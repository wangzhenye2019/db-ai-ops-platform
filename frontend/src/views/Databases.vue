<template>
  <div class="databases">
    <div class="header">
      <h2>数据库管理</h2>
      <el-button type="primary" @click="showAddDialog = true">
        <el-icon><Plus /></el-icon>
        添加数据库
      </el-button>
    </div>

    <el-table :data="databases" stripe>
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="name" label="名称" width="150" />
      <el-table-column label="类型" width="120">
        <template #default="{ row }">
          <el-tag>{{ getDbTypeLabel(row.db_type) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="host" label="主机" width="150" />
      <el-table-column prop="port" label="端口" width="80" />
      <el-table-column prop="database" label="数据库" width="150" />
      <el-table-column prop="username" label="用户名" width="120" />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.enabled ? 'success' : 'info'">
            {{ row.enabled ? '启用' : '禁用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="250">
        <template #default="{ row }">
          <el-button size="small" @click="testConnection(row.id)">测试</el-button>
          <el-button size="small" type="primary" @click="editDatabase(row)">编辑</el-button>
          <el-button size="small" type="danger" @click="deleteDatabase(row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- Add/Edit Dialog -->
    <el-dialog
      v-model="showAddDialog"
      :title="editingDatabase ? '编辑数据库' : '添加数据库'"
      width="600px"
    >
      <el-form :model="form" :rules="rules" ref="formRef" label-width="100px">
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入数据库名称" />
        </el-form-item>
        <el-form-item label="类型" prop="db_type">
          <el-select v-model="form.db_type" placeholder="选择数据库类型" @change="onDbTypeChange">
            <el-option
              v-for="type in dbTypes"
              :key="type.value"
              :label="type.label"
              :value="type.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="主机" prop="host">
          <el-input v-model="form.host" placeholder="localhost" />
        </el-form-item>
        <el-form-item label="端口" prop="port">
          <el-input-number v-model="form.port" :min="1" :max="65535" />
        </el-form-item>
        <el-form-item label="数据库" prop="database">
          <el-input v-model="form.database" placeholder="数据库名/SID" />
        </el-form-item>
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" type="password" show-password />
        </el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="form.enabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { databaseAPI } from '@/api/services'

const databases = ref([])
const dbTypes = ref([])
const showAddDialog = ref(false)
const editingDatabase = ref(null)
const formRef = ref(null)

const form = ref({
  name: '',
  db_type: 'mysql',
  host: 'localhost',
  port: 3306,
  database: '',
  username: '',
  password: '',
  enabled: true
})

const rules = {
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  db_type: [{ required: true, message: '请选择数据库类型', trigger: 'change' }],
  host: [{ required: true, message: '请输入主机地址', trigger: 'blur' }],
  port: [{ required: true, message: '请输入端口号', trigger: 'blur' }],
  database: [{ required: true, message: '请输入数据库名', trigger: 'blur' }],
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

const loadDatabases = async () => {
  try {
    const data = await databaseAPI.list()
    databases.value = data.databases
  } catch (error) {
    ElMessage.error('加载数据库失败')
  }
}

const loadDbTypes = async () => {
  try {
    const data = await databaseAPI.getTypes()
    dbTypes.value = data.types
  } catch (error) {
    console.error('Failed to load database types:', error)
  }
}

const onDbTypeChange = () => {
  const type = dbTypes.value.find(t => t.value === form.value.db_type)
  if (type) {
    form.value.port = type.default_port
  }
}

const getDbTypeLabel = (type) => {
  const t = dbTypes.value.find(d => d.value === type)
  return t ? t.label : type
}

const editDatabase = (db) => {
  editingDatabase.value = db
  form.value = { ...db }
  showAddDialog.value = true
}

const handleSubmit = async () => {
  if (!formRef.value) return

  await formRef.value.validate(async (valid) => {
    if (valid) {
      try {
        if (editingDatabase.value) {
          await databaseAPI.update(editingDatabase.value.id, form.value)
          ElMessage.success('更新成功')
        } else {
          await databaseAPI.create(form.value)
          ElMessage.success('添加成功')
        }
        showAddDialog.value = false
        editingDatabase.value = null
        loadDatabases()
      } catch (error) {
        ElMessage.error('操作失败')
      }
    }
  })
}

const deleteDatabase = async (id) => {
  try {
    await ElMessageBox.confirm('确定要删除这个数据库吗？', '警告', {
      type: 'warning'
    })
    await databaseAPI.delete(id)
    ElMessage.success('删除成功')
    loadDatabases()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

const testConnection = async (id) => {
  try {
    ElMessage.info('测试连接中...')
    const result = await databaseAPI.test(id)
    if (result.status === 'success') {
      ElMessage.success('连接成功')
    } else {
      ElMessage.error(`连接失败: ${result.message}`)
    }
  } catch (error) {
    ElMessage.error(`连接失败: ${error.message}`)
  }
}

const resetForm = () => {
  editingDatabase.value = null
  form.value = {
    name: '',
    db_type: 'mysql',
    host: 'localhost',
    port: 3306,
    database: '',
    username: '',
    password: '',
    enabled: true
  }
  if (formRef.value) {
    formRef.value.resetFields()
  }
}

onMounted(() => {
  loadDatabases()
  loadDbTypes()
})
</script>

<style scoped>
.databases {
  padding: 20px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
</style>
