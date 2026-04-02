<template>
  <div class="page">
    <div class="title-row">
      <div class="title">IP资产管理</div>
      <div class="actions">
        <el-button @click="openImport">批量导入</el-button>
        <el-button type="primary" @click="openCreate">新增IP</el-button>
      </div>
    </div>

    <el-card class="card">
      <el-row :gutter="12" class="filters">
        <el-col :span="6">
          <el-select v-model="status" clearable style="width:100%" placeholder="状态">
            <el-option v-for="s in statuses" :key="s.value" :label="s.label" :value="s.value" />
          </el-select>
        </el-col>
        <el-col :span="6">
          <el-select v-model="systemId" clearable filterable style="width:100%" placeholder="业务系统">
            <el-option v-for="s in systems" :key="s.id" :label="s.name" :value="s.id" />
          </el-select>
        </el-col>
        <el-col :span="6">
          <el-select v-model="idcId" clearable filterable style="width:100%" placeholder="机房">
            <el-option v-for="i in idcs" :key="i.id" :label="i.name" :value="i.id" />
          </el-select>
        </el-col>
        <el-col :span="6">
          <el-input v-model="q" clearable placeholder="搜索（IP/负责人/备注）" @keyup.enter="load" />
        </el-col>
      </el-row>

      <el-table :data="ips" stripe>
        <el-table-column prop="ip" label="IP" width="160" />
        <el-table-column prop="cidr" label="掩码" width="100" />
        <el-table-column prop="version" label="版本" width="110" />
        <el-table-column prop="status" label="状态" width="120" />
        <el-table-column prop="business_system_name" label="业务系统" min-width="160" />
        <el-table-column prop="owner" label="负责人" width="120" />
        <el-table-column prop="env" label="环境" width="100" />
        <el-table-column prop="idc_name" label="机房" width="140" />
        <el-table-column prop="remark" label="备注" min-width="160" />
        <el-table-column label="操作" width="180">
          <template #default="{ row }">
            <el-button text @click="openEdit(row)">编辑</el-button>
            <el-button text type="danger" @click="onDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="640px">
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="IP" prop="ip">
              <el-input v-model="form.ip" :disabled="!!editingId" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="掩码（CIDR）">
              <el-input-number v-model="form.cidr" :min="0" :max="128" style="width:100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="版本">
              <el-select v-model="form.version" style="width:100%">
                <el-option v-for="v in versions" :key="v.value" :label="v.label" :value="v.value" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="状态">
              <el-select v-model="form.status" style="width:100%">
                <el-option v-for="s in statuses" :key="s.value" :label="s.label" :value="s.value" />
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
            <el-form-item label="机房">
              <el-select v-model="form.idc_id" clearable filterable style="width:100%">
                <el-option v-for="i in idcs" :key="i.id" :label="i.name" :value="i.id" />
              </el-select>
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
            <el-form-item label="环境">
              <el-input v-model="form.env" placeholder="例如：prod/test/dev" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="标签（逗号分隔）">
          <el-input v-model="form.tagsText" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible=false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="onSave">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="importVisible" title="批量导入IP" width="720px">
      <el-alert
        type="info"
        show-icon
        :closable="false"
        title="支持 CSV / XLSX / TXT（首行为表头）。支持预览校验与覆盖更新（upsert）。"
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
          <div class="el-upload__tip">字段：ip, cidr, version, status, business_system, owner, env, idc, remark, tags</div>
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
          <el-table-column prop="ip" label="IP" width="160" />
          <el-table-column prop="status" label="状态" width="120" />
          <el-table-column prop="business_system" label="业务系统" min-width="160" />
          <el-table-column prop="owner" label="负责人" width="120" />
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
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { dictAPI, importAPI, ipAPI, systemsAPI } from '@/api/services'
import { saveBlob } from '@/utils/download'

const ips = ref([])
const statuses = ref([])
const versions = ref([])
const systems = ref([])
const idcs = ref([])

const q = ref('')
const status = ref('')
const systemId = ref(null)
const idcId = ref(null)

const loadMeta = async () => {
  const [s, sys, idc] = await Promise.allSettled([ipAPI.statuses(), systemsAPI.list(), dictAPI.listIdcs()])
  if (s.status === 'fulfilled') {
    statuses.value = s.value.statuses || []
    versions.value = s.value.versions || []
  }
  if (sys.status === 'fulfilled') systems.value = sys.value.systems || []
  if (idc.status === 'fulfilled') idcs.value = idc.value.idcs || []
}

const load = async () => {
  try {
    const data = await ipAPI.list({
      q: q.value || undefined,
      status: status.value || undefined,
      system_id: systemId.value || undefined,
      idc_id: idcId.value || undefined
    })
    ips.value = data.ips || []
  } catch (e) {
    ElMessage.error(e.message || '加载失败')
  }
}

watch([status, systemId, idcId], () => load())

const dialogVisible = ref(false)
const saving = ref(false)
const formRef = ref()
const editingId = ref(null)

const form = reactive({
  ip: '',
  cidr: null,
  version: 'ipv4',
  status: 'free',
  business_system_id: null,
  idc_id: null,
  owner: '',
  env: '',
  tagsText: '',
  remark: ''
})

const rules = {
  ip: [{ required: true, message: '请输入IP', trigger: 'blur' }]
}

const dialogTitle = computed(() => (editingId.value ? '编辑IP' : '新增IP'))

const resetForm = () => {
  editingId.value = null
  form.ip = ''
  form.cidr = null
  form.version = 'ipv4'
  form.status = 'free'
  form.business_system_id = null
  form.idc_id = null
  form.owner = ''
  form.env = ''
  form.tagsText = ''
  form.remark = ''
  formRef.value?.clearValidate?.()
}

const openCreate = () => {
  resetForm()
  dialogVisible.value = true
}

const openEdit = (row) => {
  editingId.value = row.id
  form.ip = row.ip
  form.cidr = row.cidr
  form.version = row.version || 'ipv4'
  form.status = row.status || 'free'
  form.business_system_id = row.business_system_id || null
  form.idc_id = row.idc_id || null
  form.owner = row.owner || ''
  form.env = row.env || ''
  form.tagsText = (row.tags || []).join(',')
  form.remark = row.remark || ''
  dialogVisible.value = true
}

const onSave = async () => {
  await formRef.value?.validate(async (valid) => {
    if (!valid) return
    saving.value = true
    try {
      const payload = {
        ip: form.ip,
        cidr: form.cidr || null,
        version: form.version,
        status: form.status,
        business_system_id: form.business_system_id || null,
        idc_id: form.idc_id || null,
        owner: form.owner || null,
        env: form.env || null,
        remark: form.remark || null,
        tags: form.tagsText.split(',').map(s => s.trim()).filter(Boolean)
      }
      if (editingId.value) {
        await ipAPI.update(editingId.value, payload)
      } else {
        await ipAPI.create(payload)
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
    await ElMessageBox.confirm(`确认删除IP「${row.ip}」？`, '提示', { type: 'warning' })
    await ipAPI.delete(row.id)
    ElMessage.success('已删除')
    await load()
  } catch {
  }
}

const importVisible = ref(false)
const importing = ref(false)
const selectedFile = ref(null)
const fileList = ref([])
const importResult = ref(null)
const importUpsert = ref(false)

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
    const blob = await importAPI.downloadTemplate('ips', format)
    saveBlob(blob, `ips_template.${format}`)
  } catch (e) {
    ElMessage.error(e.message || '下载失败')
  }
}

const doPreview = async () => {
  if (!selectedFile.value) return
  importing.value = true
  try {
    const res = await importAPI.importFile('ips', selectedFile.value, { dryRun: true, mode: importUpsert.value ? 'upsert' : 'insert' })
    importResult.value = res
    ElMessage.success('校验完成')
  } catch (e) {
    ElMessage.error(e.message || '校验失败')
  } finally {
    importing.value = false
  }
}

const doImport = async () => {
  if (!selectedFile.value) return
  importing.value = true
  try {
    const res = await importAPI.importFile('ips', selectedFile.value, { dryRun: false, mode: importUpsert.value ? 'upsert' : 'insert' })
    importResult.value = res
    ElMessage.success('导入完成')
    await load()
  } catch (e) {
    ElMessage.error(e.message || '导入失败')
  } finally {
    importing.value = false
  }
}

onMounted(async () => {
  await loadMeta()
  await load()
})
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
.filters {
  margin-bottom: 12px;
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
