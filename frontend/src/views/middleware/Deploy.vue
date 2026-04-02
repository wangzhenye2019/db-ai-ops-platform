<template>
  <div class="page">
    <div class="title-row">
      <div class="title">中间件部署</div>
      <div class="actions">
        <el-button @click="openImport">批量导入</el-button>
        <el-button type="primary" @click="openCreate">新增中间件</el-button>
      </div>
    </div>
    <el-card class="card">
      <el-table :data="items" stripe>
        <el-table-column prop="name" label="名称" min-width="160" />
        <el-table-column prop="mw_type" label="类型" width="150" />
        <el-table-column prop="host" label="主机" min-width="160" />
        <el-table-column prop="port" label="端口" width="90" />
        <el-table-column prop="version" label="版本" width="120" />
        <el-table-column prop="business_system_name" label="业务系统" min-width="160" />
        <el-table-column prop="owner" label="负责人" width="120" />
        <el-table-column prop="env" label="环境" width="100" />
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
            <el-form-item label="业务系统">
              <el-select v-model="form.business_system_id" clearable filterable style="width:100%">
                <el-option v-for="s in systems" :key="s.id" :label="s.name" :value="s.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="负责人">
              <el-input v-model="form.owner" />
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
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="环境">
              <el-input v-model="form.env" placeholder="例如：prod/test/dev" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="备注">
              <el-input v-model="form.remark" />
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

    <el-dialog v-model="importVisible" title="批量导入中间件" width="720px">
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
          <div class="el-upload__tip">字段：name, mw_type, host, port, version, business_system, owner, env, remark, enabled, meta</div>
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
          <el-table-column prop="mw_type" label="类型" width="140" />
          <el-table-column prop="host" label="主机" min-width="160" />
          <el-table-column prop="port" label="端口" width="90" />
          <el-table-column prop="version" label="版本" width="120" />
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
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { importAPI, middlewareAPI, systemsAPI } from '@/api/services'
import { saveBlob } from '@/utils/download'

const items = ref([])
const types = ref([{ value: 'other', label: 'OTHER' }])
const systems = ref([])

const dialogVisible = ref(false)
const saving = ref(false)
const formRef = ref()
const editingId = ref(null)

const importVisible = ref(false)
const importing = ref(false)
const selectedFile = ref(null)
const fileList = ref([])
const importResult = ref(null)
const importUpsert = ref(false)

const form = reactive({
  name: '',
  mw_type: 'other',
  host: '',
  port: 6379,
  version: '',
  business_system_id: null,
  owner: '',
  env: '',
  remark: '',
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
  const [listRes, typeRes, sysRes] = await Promise.allSettled([middlewareAPI.list(), middlewareAPI.getTypes(), systemsAPI.list()])
  if (listRes.status === 'fulfilled') items.value = listRes.value.middlewares || []
  if (typeRes.status === 'fulfilled') types.value = typeRes.value.types || types.value
  if (sysRes.status === 'fulfilled') systems.value = sysRes.value.systems || []
}

const resetForm = () => {
  editingId.value = null
  form.name = ''
  form.mw_type = 'other'
  form.host = ''
  form.port = 6379
  form.version = ''
  form.business_system_id = null
  form.owner = ''
  form.env = ''
  form.remark = ''
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
  form.business_system_id = row.business_system_id || null
  form.owner = row.owner || ''
  form.env = row.env || ''
  form.remark = row.remark || ''
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
        business_system_id: form.business_system_id || null,
        owner: form.owner || null,
        env: form.env || null,
        remark: form.remark || null,
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
    const blob = await importAPI.downloadTemplate('middlewares', format)
    saveBlob(blob, `middlewares_template.${format}`)
  } catch (e) {
    ElMessage.error(e.message || '下载失败')
  }
}

const doImport = async () => {
  if (!selectedFile.value) return
  importing.value = true
  try {
    const res = await importAPI.importFile('middlewares', selectedFile.value, { dryRun: false, mode: importUpsert.value ? 'upsert' : 'insert' })
    importResult.value = res
    ElMessage.success('导入完成')
    await load()
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
    const res = await importAPI.importFile('middlewares', selectedFile.value, { dryRun: true, mode: importUpsert.value ? 'upsert' : 'insert' })
    importResult.value = res
    ElMessage.success('校验完成')
  } catch (e) {
    ElMessage.error(e.message || '校验失败')
  } finally {
    importing.value = false
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
.actions {
  display: flex;
  gap: 10px;
}
.title {
  font-size: 16px;
  font-weight: 700;
  color: #0f172a;
}
.card {
  margin: 0 8px;
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
