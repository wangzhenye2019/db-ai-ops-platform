<template>
  <div class="databases">
    <div class="header">
      <h2>数据库管理</h2>
      <div class="header-actions">
        <el-button @click="openImport">批量导入</el-button>
        <el-button type="primary" @click="showAddDialog = true">
          <el-icon><Plus /></el-icon>
          添加数据库
        </el-button>
      </div>
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
      <el-table-column prop="business_system_name" label="业务系统" width="160" />
      <el-table-column prop="owner" label="负责人" width="120" />
      <el-table-column prop="env" label="环境" width="100" />
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
        <el-form-item label="业务系统">
          <el-select v-model="form.business_system_id" clearable filterable placeholder="选择业务系统">
            <el-option v-for="s in systems" :key="s.id" :label="s.name" :value="s.id" />
          </el-select>
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
        <el-form-item label="负责人">
          <el-input v-model="form.owner" />
        </el-form-item>
        <el-form-item label="环境">
          <el-input v-model="form.env" placeholder="例如：prod/test/dev" />
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
        <el-form-item label="版本">
          <el-input v-model="form.version" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" :rows="2" />
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

    <el-dialog v-model="importVisible" title="批量导入数据库" width="720px">
      <el-alert
        type="info"
        show-icon
        :closable="false"
        title="支持 CSV / XLSX / TXT（首行为表头）。建议先下载模板填写后再上传。"
      />

      <div class="import-actions">
        <el-button @click="downloadTemplate('csv')">下载 CSV 模板</el-button>
        <el-button @click="downloadTemplate('xlsx')">下载 Excel 模板</el-button>
        <el-button @click="downloadTemplate('txt')">下载 TXT 模板</el-button>
        <div class="spacer" />
        <span class="muted">更新已存在</span>
        <el-switch v-model="importUpsert" />
      </div>

      <el-upload
        :auto-upload="false"
        :limit="1"
        :file-list="fileList"
        accept=".csv,.txt,.xlsx"
        drag
        @change="onFileChange"
        @remove="onFileRemove"
      >
        <el-icon><UploadFilled /></el-icon>
        <div class="el-upload__text">拖拽文件到此处，或点击上传</div>
        <template #tip>
          <div class="el-upload__tip">字段：name, db_type, host, port, database, username, password, business_system, owner, env, version, remark, enabled</div>
        </template>
      </el-upload>

      <template v-if="importResult">
        <el-divider />
        <el-descriptions :column="4" border>
          <el-descriptions-item label="总行数">{{ importResult.total }}</el-descriptions-item>
          <el-descriptions-item label="新增">{{ importResult.created ?? 0 }}</el-descriptions-item>
          <el-descriptions-item label="更新">{{ importResult.updated ?? 0 }}</el-descriptions-item>
          <el-descriptions-item label="资源">{{ importResult.resource }}</el-descriptions-item>
        </el-descriptions>

        <el-table v-if="(importResult.preview || []).length" :data="importResult.preview" stripe class="error-table">
          <el-table-column prop="row" label="行号" width="90" />
          <el-table-column prop="action" label="动作" width="110" />
          <el-table-column prop="name" label="名称" min-width="160" />
          <el-table-column prop="db_type" label="类型" width="140" />
          <el-table-column prop="host" label="主机" min-width="160" />
          <el-table-column prop="port" label="端口" width="90" />
          <el-table-column prop="database" label="数据库" min-width="160" />
        </el-table>

        <el-table v-if="(importResult.errors || []).length" :data="importResult.errors" stripe class="error-table">
          <el-table-column prop="row" label="行号" width="90" />
          <el-table-column prop="error" label="错误" />
        </el-table>
      </template>

      <template #footer>
        <el-button @click="importVisible=false">关闭</el-button>
        <el-button :loading="importing" :disabled="!selectedFile" @click="doPreview">预览校验</el-button>
        <el-button type="primary" :loading="importing" :disabled="!selectedFile" @click="doImport">开始导入</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { databaseAPI, importAPI, systemsAPI } from '@/api/services'
import { saveBlob } from '@/utils/download'

const databases = ref([])
const dbTypes = ref([])
const systems = ref([])
const showAddDialog = ref(false)
const editingDatabase = ref(null)
const formRef = ref(null)

const importVisible = ref(false)
const importing = ref(false)
const selectedFile = ref(null)
const fileList = ref([])
const importResult = ref(null)
const importUpsert = ref(false)

const form = ref({
  name: '',
  db_type: 'mysql',
  host: 'localhost',
  port: 3306,
  database: '',
  username: '',
  password: '',
  business_system_id: null,
  owner: '',
  env: '',
  version: '',
  remark: '',
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

const loadSystems = async () => {
  try {
    const data = await systemsAPI.list()
    systems.value = data.systems || []
  } catch {
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
        const payload = {
          ...form.value,
          business_system_id: form.value.business_system_id || null,
          owner: form.value.owner || null,
          env: form.value.env || null,
          version: form.value.version || null,
          remark: form.value.remark || null
        }
        if (editingDatabase.value) {
          await databaseAPI.update(editingDatabase.value.id, payload)
          ElMessage.success('更新成功')
        } else {
          await databaseAPI.create(payload)
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
    business_system_id: null,
    owner: '',
    env: '',
    version: '',
    remark: '',
    enabled: true
  }
  if (formRef.value) {
    formRef.value.resetFields()
  }
}

const openImport = () => {
  importVisible.value = true
  selectedFile.value = null
  fileList.value = []
  importResult.value = null
}

const onFileChange = (file, files) => {
  fileList.value = files.slice(-1)
  selectedFile.value = file.raw || null
}

const onFileRemove = () => {
  fileList.value = []
  selectedFile.value = null
}

const downloadTemplate = async (format) => {
  try {
    const blob = await importAPI.downloadTemplate('databases', format)
    saveBlob(blob, `databases_template.${format}`)
  } catch (e) {
    ElMessage.error(e.message || '下载失败')
  }
}

const doImport = async () => {
  if (!selectedFile.value) return
  importing.value = true
  try {
    const res = await importAPI.importFile('databases', selectedFile.value, { dryRun: false, mode: importUpsert.value ? 'upsert' : 'insert' })
    importResult.value = res
    ElMessage.success('导入完成')
    await loadDatabases()
  } catch (e) {
    ElMessage.error(e.message || '导入失败')
  } finally {
    importing.value = false
  }
}

const doPreview = async () => {
  if (!selectedFile.value) return
  importing.value = true
  try {
    const res = await importAPI.importFile('databases', selectedFile.value, { dryRun: true, mode: importUpsert.value ? 'upsert' : 'insert' })
    importResult.value = res
    ElMessage.success('校验完成')
  } catch (e) {
    ElMessage.error(e.message || '校验失败')
  } finally {
    importing.value = false
  }
}

onMounted(() => {
  loadDatabases()
  loadDbTypes()
  loadSystems()
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

.header-actions {
  display: flex;
  gap: 10px;
}

.import-actions {
  display: flex;
  gap: 10px;
  margin: 12px 0;
  align-items: center;
}

.spacer {
  flex: 1;
}

.muted {
  color: #64748b;
}

.error-table {
  margin-top: 12px;
}
</style>
