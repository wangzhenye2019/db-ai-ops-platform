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
            <el-tag class="tag" type="info">IP {{ row.counts?.ips || 0 }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="启用" width="100">
          <template #default="{ row }">
            <el-tag :type="row.enabled ? 'success' : 'info'">{{ row.enabled ? '是' : '否' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220">
          <template #default="{ row }">
            <el-button text @click="openContacts(row)">联系人</el-button>
            <el-button text @click="openLinks(row)">关联资产</el-button>
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

    <el-dialog v-model="contactsVisible" :title="contactsTitle" width="780px">
      <el-form :model="contactForm" label-position="top">
        <el-row :gutter="12">
          <el-col :span="6">
            <el-form-item label="姓名">
              <el-input v-model="contactForm.name" />
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="角色">
              <el-input v-model="contactForm.role" placeholder="例如：运维/开发/值班" />
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="电话">
              <el-input v-model="contactForm.phone" />
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="邮箱">
              <el-input v-model="contactForm.email" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="备注">
          <el-input v-model="contactForm.remark" />
        </el-form-item>
        <div class="contact-actions">
          <el-button @click="loadContacts">刷新</el-button>
          <el-button type="primary" :loading="savingContacts" @click="addContact">添加联系人</el-button>
        </div>
      </el-form>

      <el-table :data="contacts" stripe class="contacts-table">
        <el-table-column prop="name" label="姓名" width="140" />
        <el-table-column prop="role" label="角色" width="160" />
        <el-table-column prop="phone" label="电话" width="160" />
        <el-table-column prop="email" label="邮箱" min-width="200" />
        <el-table-column prop="remark" label="备注" min-width="180" />
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button text type="danger" @click="deleteContact(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <template #footer>
        <el-button @click="contactsVisible=false">关闭</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="linksVisible" :title="linksTitle" width="980px">
      <el-tabs v-model="linkTab">
        <el-tab-pane label="主机" name="host">
          <el-select v-model="selectHostIds" multiple filterable style="width:100%" placeholder="选择主机额外关联到该业务系统">
            <el-option v-for="h in allHosts" :key="h.id" :label="`${h.name} (${h.host}:${h.port})`" :value="h.id" />
          </el-select>
          <div class="link-actions">
            <el-button @click="refreshLinks">刷新</el-button>
            <el-button type="primary" :loading="savingLinks" @click="addSelectedLinks('host')">添加关联</el-button>
          </div>
          <el-table :data="systemAssets.hosts" stripe class="link-table">
            <el-table-column prop="name" label="名称" min-width="180" />
            <el-table-column prop="host" label="IP/域名" min-width="160" />
            <el-table-column prop="port" label="端口" width="90" />
            <el-table-column label="关联" width="120">
              <template #default="{ row }">
                <el-tag :type="isLinked('host', row.id) ? 'warning' : 'success'">{{ isLinked('host', row.id) ? '额外关联' : '主关联' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="140">
              <template #default="{ row }">
                <el-button v-if="isLinked('host', row.id)" text type="danger" @click="removeLink('host', row.id)">移除</el-button>
                <span v-else class="muted">-</span>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="数据库" name="database">
          <el-select v-model="selectDbIds" multiple filterable style="width:100%" placeholder="选择数据库额外关联到该业务系统">
            <el-option v-for="d in allDatabases" :key="d.id" :label="`${d.name} (${d.db_type}@${d.host}:${d.port}/${d.database})`" :value="d.id" />
          </el-select>
          <div class="link-actions">
            <el-button @click="refreshLinks">刷新</el-button>
            <el-button type="primary" :loading="savingLinks" @click="addSelectedLinks('database')">添加关联</el-button>
          </div>
          <el-table :data="systemAssets.databases" stripe class="link-table">
            <el-table-column prop="name" label="名称" min-width="180" />
            <el-table-column prop="db_type" label="类型" width="120" />
            <el-table-column prop="host" label="主机" min-width="160" />
            <el-table-column prop="port" label="端口" width="90" />
            <el-table-column prop="database" label="数据库" min-width="160" />
            <el-table-column label="关联" width="120">
              <template #default="{ row }">
                <el-tag :type="isLinked('database', row.id) ? 'warning' : 'success'">{{ isLinked('database', row.id) ? '额外关联' : '主关联' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="140">
              <template #default="{ row }">
                <el-button v-if="isLinked('database', row.id)" text type="danger" @click="removeLink('database', row.id)">移除</el-button>
                <span v-else class="muted">-</span>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="中间件" name="middleware">
          <el-select v-model="selectMwIds" multiple filterable style="width:100%" placeholder="选择中间件额外关联到该业务系统">
            <el-option v-for="m in allMiddlewares" :key="m.id" :label="`${m.name} (${m.mw_type}@${m.host}:${m.port})`" :value="m.id" />
          </el-select>
          <div class="link-actions">
            <el-button @click="refreshLinks">刷新</el-button>
            <el-button type="primary" :loading="savingLinks" @click="addSelectedLinks('middleware')">添加关联</el-button>
          </div>
          <el-table :data="systemAssets.middlewares" stripe class="link-table">
            <el-table-column prop="name" label="名称" min-width="180" />
            <el-table-column prop="mw_type" label="类型" width="140" />
            <el-table-column prop="host" label="主机" min-width="160" />
            <el-table-column prop="port" label="端口" width="90" />
            <el-table-column label="关联" width="120">
              <template #default="{ row }">
                <el-tag :type="isLinked('middleware', row.id) ? 'warning' : 'success'">{{ isLinked('middleware', row.id) ? '额外关联' : '主关联' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="140">
              <template #default="{ row }">
                <el-button v-if="isLinked('middleware', row.id)" text type="danger" @click="removeLink('middleware', row.id)">移除</el-button>
                <span v-else class="muted">-</span>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="IP" name="ip">
          <el-select v-model="selectIpIds" multiple filterable style="width:100%" placeholder="选择IP额外关联到该业务系统">
            <el-option v-for="i in allIps" :key="i.id" :label="i.cidr ? `${i.ip}/${i.cidr}` : i.ip" :value="i.id" />
          </el-select>
          <div class="link-actions">
            <el-button @click="refreshLinks">刷新</el-button>
            <el-button type="primary" :loading="savingLinks" @click="addSelectedLinks('ip')">添加关联</el-button>
          </div>
          <el-table :data="systemAssets.ips" stripe class="link-table">
            <el-table-column prop="ip" label="IP" width="160" />
            <el-table-column prop="cidr" label="掩码" width="100" />
            <el-table-column prop="status" label="状态" width="120" />
            <el-table-column prop="idc_name" label="机房" width="160" />
            <el-table-column label="关联" width="120">
              <template #default="{ row }">
                <el-tag :type="isLinked('ip', row.id) ? 'warning' : 'success'">{{ isLinked('ip', row.id) ? '额外关联' : '主关联' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="140">
              <template #default="{ row }">
                <el-button v-if="isLinked('ip', row.id)" text type="danger" @click="removeLink('ip', row.id)">移除</el-button>
                <span v-else class="muted">-</span>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>

      <template #footer>
        <el-button @click="linksVisible=false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { databaseAPI, hostAPI, ipAPI, middlewareAPI, systemsAPI } from '@/api/services'

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

const contactsVisible = ref(false)
const contactsSystemId = ref(null)
const contacts = ref([])
const savingContacts = ref(false)

const contactsTitle = computed(() => {
  const s = systems.value.find(x => x.id === contactsSystemId.value)
  return s ? `联系人 - ${s.name}` : '联系人'
})

const contactForm = reactive({
  name: '',
  role: '',
  phone: '',
  email: '',
  remark: ''
})

const resetContactForm = () => {
  contactForm.name = ''
  contactForm.role = ''
  contactForm.phone = ''
  contactForm.email = ''
  contactForm.remark = ''
}

const openContacts = async (row) => {
  contactsSystemId.value = row.id
  contactsVisible.value = true
  resetContactForm()
  await loadContacts()
}

const loadContacts = async () => {
  if (!contactsSystemId.value) return
  try {
    const data = await systemsAPI.listContacts(contactsSystemId.value)
    contacts.value = data.contacts || []
  } catch (e) {
    ElMessage.error(e.message || '加载失败')
  }
}

const addContact = async () => {
  if (!contactsSystemId.value) return
  if (!contactForm.name.trim()) {
    ElMessage.warning('请输入姓名')
    return
  }
  savingContacts.value = true
  try {
    await systemsAPI.createContact(contactsSystemId.value, {
      name: contactForm.name,
      role: contactForm.role || null,
      phone: contactForm.phone || null,
      email: contactForm.email || null,
      remark: contactForm.remark || null
    })
    ElMessage.success('已添加')
    resetContactForm()
    await loadContacts()
  } catch (e) {
    ElMessage.error(e.message || '添加失败')
  } finally {
    savingContacts.value = false
  }
}

const deleteContact = async (row) => {
  if (!contactsSystemId.value) return
  savingContacts.value = true
  try {
    await systemsAPI.deleteContact(contactsSystemId.value, row.id)
    ElMessage.success('已删除')
    await loadContacts()
  } catch (e) {
    ElMessage.error(e.message || '删除失败')
  } finally {
    savingContacts.value = false
  }
}

const linksVisible = ref(false)
const linksSystemId = ref(null)
const linkTab = ref('host')
const savingLinks = ref(false)

const linksTitle = computed(() => {
  const s = systems.value.find(x => x.id === linksSystemId.value)
  return s ? `关联资产 - ${s.name}` : '关联资产'
})

const allHosts = ref([])
const allDatabases = ref([])
const allMiddlewares = ref([])
const allIps = ref([])

const systemAssets = reactive({
  hosts: [],
  databases: [],
  middlewares: [],
  ips: []
})

const linkedIds = ref({
  host: new Set(),
  database: new Set(),
  middleware: new Set(),
  ip: new Set()
})

const selectHostIds = ref([])
const selectDbIds = ref([])
const selectMwIds = ref([])
const selectIpIds = ref([])

const isLinked = (type, id) => {
  const s = linkedIds.value[type]
  return !!(s && s.has(id))
}

const refreshLinks = async () => {
  if (!linksSystemId.value) return
  try {
    const [a, l] = await Promise.all([systemsAPI.assets(linksSystemId.value), systemsAPI.listLinks(linksSystemId.value)])
    systemAssets.hosts = a.hosts || []
    systemAssets.databases = a.databases || []
    systemAssets.middlewares = a.middlewares || []
    systemAssets.ips = a.ips || []

    linkedIds.value = {
      host: new Set((l.links || []).filter(x => x.asset_type === 'host').map(x => x.asset_id)),
      database: new Set((l.links || []).filter(x => x.asset_type === 'database').map(x => x.asset_id)),
      middleware: new Set((l.links || []).filter(x => x.asset_type === 'middleware').map(x => x.asset_id)),
      ip: new Set((l.links || []).filter(x => x.asset_type === 'ip').map(x => x.asset_id))
    }
  } catch (e) {
    ElMessage.error(e.message || '加载失败')
  }
}

const loadAllAssets = async () => {
  const [h, d, m, i] = await Promise.allSettled([hostAPI.list(), databaseAPI.list(), middlewareAPI.list(), ipAPI.list()])
  if (h.status === 'fulfilled') allHosts.value = h.value.hosts || []
  if (d.status === 'fulfilled') allDatabases.value = d.value.databases || []
  if (m.status === 'fulfilled') allMiddlewares.value = m.value.middlewares || []
  if (i.status === 'fulfilled') allIps.value = i.value.ips || []
}

const openLinks = async (row) => {
  linksSystemId.value = row.id
  linksVisible.value = true
  linkTab.value = 'host'
  selectHostIds.value = []
  selectDbIds.value = []
  selectMwIds.value = []
  selectIpIds.value = []
  await Promise.all([loadAllAssets(), refreshLinks()])
}

const addSelectedLinks = async (type) => {
  if (!linksSystemId.value) return
  const add = []
  const ids = type === 'host' ? selectHostIds.value
    : type === 'database' ? selectDbIds.value
      : type === 'middleware' ? selectMwIds.value
        : selectIpIds.value
  for (const id of ids) add.push({ type, id })
  if (!add.length) {
    ElMessage.warning('请选择要关联的资产')
    return
  }
  savingLinks.value = true
  try {
    await systemsAPI.updateLinks(linksSystemId.value, { add })
    ElMessage.success('已关联')
    if (type === 'host') selectHostIds.value = []
    if (type === 'database') selectDbIds.value = []
    if (type === 'middleware') selectMwIds.value = []
    if (type === 'ip') selectIpIds.value = []
    await refreshLinks()
    await load()
  } catch (e) {
    ElMessage.error(e.message || '操作失败')
  } finally {
    savingLinks.value = false
  }
}

const removeLink = async (type, id) => {
  if (!linksSystemId.value) return
  savingLinks.value = true
  try {
    await systemsAPI.updateLinks(linksSystemId.value, { remove: [{ type, id }] })
    ElMessage.success('已移除')
    await refreshLinks()
    await load()
  } catch (e) {
    ElMessage.error(e.message || '操作失败')
  } finally {
    savingLinks.value = false
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

.contact-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin: 8px 0 12px;
}

.contacts-table {
  margin-top: 6px;
}

.link-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin: 10px 0 12px;
}

.link-table {
  margin-top: 6px;
}

.muted {
  color: #64748b;
}
</style>
