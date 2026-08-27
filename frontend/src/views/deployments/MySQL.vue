<template>
  <div class="mysql-deployment-page">
    <PageHeader title="MySQL 自动化部署" subtitle="基于 dbops Ansible 自动化资产，以受控任务方式完成 MySQL 安装与拓扑编排。" />

    <el-alert
      title="执行前请确认目标为空白主机，并已将 SSH 主机指纹写入部署控制器的 known_hosts 文件。"
      type="warning"
      :closable="false"
      show-icon
      class="safety-alert"
    />

    <el-card shadow="never" class="form-card">
      <template #header>
        <div class="card-header"><span>部署需求</span><small>密码仅通过已加密的凭据引用，绝不会写入任务参数。</small></div>
      </template>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="142px" class="deployment-form">
        <el-form-item label="部署拓扑" prop="topology">
          <el-radio-group v-model="form.topology" @change="onTopologyChange">
            <el-radio-button label="single-node">单节点</el-radio-button>
            <el-radio-button label="master-slave">一主多从</el-radio-button>
            <el-radio-button label="mgr">MGR 组复制</el-radio-button>
          </el-radio-group>
          <div class="field-help">{{ topologyHelp }}</div>
        </el-form-item>

        <el-form-item label="目标 Linux 主机" prop="target_ids">
          <el-select v-model="form.target_ids" multiple filterable collapse-tags placeholder="选择已经登记并启用的目标主机" class="wide-control">
            <el-option v-for="host in eligibleHosts" :key="host.id" :label="`${host.name} (${host.host}:${host.port})`" :value="host.id">
              <span>{{ host.name }}</span><span class="option-address">{{ host.host }}:{{ host.port }}</span>
            </el-option>
          </el-select>
          <div class="field-help">主从拓扑中第一个主机为主库；MGR 必须选 3–9 台主机。</div>
        </el-form-item>

        <el-divider content-position="left">MySQL 参数</el-divider>
        <el-row :gutter="18">
          <el-col :xs="24" :sm="12">
            <el-form-item label="MySQL 版本" prop="mysql_version">
              <el-select v-model="form.mysql_version" class="wide-control">
                <el-option label="MySQL 8.4.6 (LTS)" value="8.4.6" />
                <el-option label="MySQL 8.0.41" value="8.0.41" />
                <el-option label="MySQL 5.7.44" value="5.7.44" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="监听端口" prop="mysql_port">
              <el-input-number v-model="form.mysql_port" :min="1024" :max="65535" class="wide-control" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="数据目录根路径" prop="mysql_data_dir_base">
              <el-input v-model.trim="form.mysql_data_dir_base" class="wide-control" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="服务器规格" prop="server_specs">
              <el-input v-model.trim="form.server_specs" placeholder="auto 或 4c8g" class="wide-control" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="管理员用户名" prop="mysql_admin_user">
              <el-input v-model.trim="form.mysql_admin_user" class="wide-control" />
            </el-form-item>
          </el-col>
          <el-col v-if="form.topology !== 'single-node'" :xs="24" :sm="12">
            <el-form-item label="复制授权来源" prop="replication_grant_hosts">
              <el-input v-model.trim="form.replication_grant_hosts" placeholder="% 或指定 CIDR/网段" class="wide-control" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-divider content-position="left">安全确认</el-divider>
        <el-form-item label="初始化凭据" prop="initial_credential_id">
          <el-select v-model="form.initial_credential_id" filterable placeholder="选择 DB_PASSWORD 或 GENERIC 凭据" class="wide-control">
            <el-option v-for="credential in databaseCredentials" :key="credential.id" :label="`${credential.name} (${credential.cred_type})`" :value="credential.id" />
          </el-select>
          <div class="field-help">凭据内容可以是管理员密码文本，或包含 <code>mysql_admin_password</code> 的 JSON 对象。</div>
        </el-form-item>
        <el-form-item label="执行模式">
          <el-checkbox v-model="form.dry_run">仅预演，不连接目标主机</el-checkbox>
        </el-form-item>
        <el-form-item prop="confirmed">
          <el-checkbox v-model="form.confirmed">我已核验主机、拓扑和凭据，确认此操作会在远端执行安装和配置变更。</el-checkbox>
        </el-form-item>
        <el-form-item>
          <el-button :loading="submitting" @click="submitDeployment(true)">生成部署预演</el-button>
          <el-button type="primary" :loading="submitting" @click="submitDeployment(false)">确认并执行部署</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" class="task-card">
      <template #header>
        <div class="card-header"><span>部署任务</span><el-button text type="primary" @click="loadTasks">刷新</el-button></div>
      </template>
      <el-table :data="tasks" v-loading="loadingTasks" row-key="id" empty-text="暂无 MySQL 部署任务">
        <el-table-column prop="id" label="任务 ID" width="86" />
        <el-table-column label="拓扑" min-width="112"><template #default="{ row }">{{ row.payload?.topology || '-' }}</template></el-table-column>
        <el-table-column label="目标" min-width="155"><template #default="{ row }">{{ targetText(row) }}</template></el-table-column>
        <el-table-column label="状态" width="112"><template #default="{ row }"><el-tag :type="statusType(row.status)">{{ statusText(row.status) }}</el-tag></template></el-table-column>
        <el-table-column label="创建时间" min-width="175"><template #default="{ row }">{{ formatTime(row.created_at) }}</template></el-table-column>
        <el-table-column label="操作" width="92" fixed="right"><template #default="{ row }"><el-button text type="primary" @click="openTask(row)">查看</el-button></template></el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="detailVisible" title="部署任务详情" width="760px" destroy-on-close>
      <template v-if="selectedTask">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="任务 ID">{{ selectedTask.id }}</el-descriptions-item>
          <el-descriptions-item label="状态">{{ statusText(selectedTask.status) }}</el-descriptions-item>
          <el-descriptions-item label="模式">{{ selectedTask.result?.mode || '-' }}</el-descriptions-item>
          <el-descriptions-item label="退出码">{{ selectedTask.result?.exit_code ?? '-' }}</el-descriptions-item>
          <el-descriptions-item label="目标主机" :span="2">{{ (selectedTask.result?.preview?.target_addresses || []).join(', ') || '-' }}</el-descriptions-item>
        </el-descriptions>
        <p v-if="selectedTask.error_message" class="task-error">{{ selectedTask.error_message }}</p>
        <h4>标准输出（已脱敏）</h4>
        <pre>{{ selectedTask.result?.stdout || '暂无输出' }}</pre>
        <h4>错误输出（已脱敏）</h4>
        <pre>{{ selectedTask.result?.stderr || '暂无输出' }}</pre>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import PageHeader from '../../components/PageHeader.vue'
import { credsAPI, deploymentAPI, hostAPI, opsAPI } from '../../api/services'

const formRef = ref()
const submitting = ref(false)
const loadingTasks = ref(false)
const hosts = ref([])
const credentials = ref([])
const tasks = ref([])
const detailVisible = ref(false)
const selectedTask = ref(null)
let pollingTimer = null

const form = ref({
  topology: 'single-node',
  target_ids: [],
  mysql_version: '8.4.6',
  mysql_port: 3306,
  mysql_data_dir_base: '/database/mysql',
  server_specs: 'auto',
  mysql_admin_user: 'admin',
  replication_grant_hosts: '%',
  initial_credential_id: null,
  confirmed: false,
  dry_run: false
})

const eligibleHosts = computed(() => hosts.value.filter(item => item.enabled && item.os_type === 'linux'))
const databaseCredentials = computed(() => credentials.value.filter(item => item.enabled && ['db_password', 'generic'].includes(item.cred_type)))
const topologyHelp = computed(() => ({
  'single-node': '在一台已登记 Linux 主机上安装单实例 MySQL。',
  'master-slave': '按所选顺序配置一主多从：第一个主机为主库，其余为从库。',
  mgr: '在 3–9 台主机上部署 MySQL Group Replication。'
}[form.value.topology]))

const validateTargetCount = (_rule, value, callback) => {
  const count = (value || []).length
  if (form.value.topology === 'single-node' && count !== 1) return callback(new Error('单节点部署只能选择一台主机'))
  if (form.value.topology === 'master-slave' && count < 2) return callback(new Error('一主多从至少选择两台主机'))
  if (form.value.topology === 'mgr' && (count < 3 || count > 9)) return callback(new Error('MGR 必须选择 3–9 台主机'))
  callback()
}

const rules = {
  target_ids: [{ validator: validateTargetCount, trigger: 'change' }],
  mysql_version: [{ required: true, message: '请选择 MySQL 版本', trigger: 'change' }],
  mysql_data_dir_base: [{ required: true, pattern: /^\/[A-Za-z0-9_./-]+$/, message: '请输入安全的绝对 Linux 路径', trigger: 'blur' }],
  server_specs: [{ required: true, pattern: /^(auto|[1-9]\d{0,2}c[1-9]\d{0,3}g)$/, message: '格式为 auto 或 4c8g', trigger: 'blur' }],
  mysql_admin_user: [{ required: true, pattern: /^[A-Za-z_][A-Za-z0-9_]{0,31}$/, message: '仅限字母、数字与下划线', trigger: 'blur' }],
  initial_credential_id: [{ required: true, message: '请选择初始化凭据', trigger: 'change' }],
  confirmed: [{ validator: (_rule, value, callback) => value ? callback() : callback(new Error('执行前必须明确确认')), trigger: 'change' }]
}

function statusType (status) {
  return ({ success: 'success', failed: 'danger', running: 'warning', pending: 'info' })[status] || 'info'
}

function statusText (status) {
  return ({ success: '成功', failed: '失败', running: '执行中', pending: '待执行' })[status] || status || '-'
}

function targetText (task) {
  const targets = task.result?.preview?.target_addresses || task.payload?.target_ids || []
  return Array.isArray(targets) ? targets.join(', ') : String(targets)
}

function formatTime (value) {
  return value ? new Date(value).toLocaleString() : '-'
}

function onTopologyChange () {
  formRef.value?.validateField('target_ids')
}

async function loadTasks () {
  loadingTasks.value = true
  try {
    const { data } = await opsAPI.listTasks()
    tasks.value = (data.tasks || []).filter(item => item.category === 'database' && item.action === 'mysql-deploy')
    if (selectedTask.value) selectedTask.value = tasks.value.find(item => item.id === selectedTask.value.id) || selectedTask.value
  } catch (error) {
    ElMessage.error(error.response?.data?.error || '加载部署任务失败')
  } finally {
    loadingTasks.value = false
  }
}

async function loadResources () {
  try {
    const [hostResponse, credentialResponse] = await Promise.all([hostAPI.list(), credsAPI.list()])
    hosts.value = hostResponse.data.hosts || []
    credentials.value = credentialResponse.data.credentials || []
  } catch (error) {
    ElMessage.error(error.response?.data?.error || '加载主机或凭据失败')
  }
}

async function submitDeployment (forceDryRun) {
  try {
    await formRef.value.validate()
    const payload = { ...form.value, dry_run: forceDryRun || form.value.dry_run }
    if (!payload.dry_run) {
      await ElMessageBox.confirm('该操作将通过 SSH 在所选主机执行 MySQL 安装和配置。是否继续？', '确认执行部署', { type: 'warning', confirmButtonText: '执行', cancelButtonText: '取消' })
    }
    submitting.value = true
    const { data } = await deploymentAPI.createMysqlDeployment(payload)
    ElMessage.success(payload.dry_run ? '部署预演任务已完成' : '部署任务已创建')
    await loadTasks()
    selectedTask.value = tasks.value.find(item => item.id === data.id) || data
    detailVisible.value = true
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') ElMessage.error(error.response?.data?.error || error.message || '创建部署任务失败')
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  await Promise.all([loadResources(), loadTasks(), deploymentAPI.mysqlOptions()])
  pollingTimer = window.setInterval(() => {
    if (tasks.value.some(item => ['pending', 'running'].includes(item.status))) loadTasks()
  }, 5000)
})

onBeforeUnmount(() => {
  if (pollingTimer) window.clearInterval(pollingTimer)
})
</script>

<style scoped>
.mysql-deployment-page { padding: 2px 0 24px; }
.safety-alert, .form-card, .task-card { margin-bottom: 18px; }
.card-header { display: flex; justify-content: space-between; align-items: baseline; font-weight: 600; }
.card-header small, .field-help { color: var(--el-text-color-secondary); font-size: 12px; font-weight: 400; }
.field-help { line-height: 1.55; margin-top: 6px; }
.wide-control { width: 100%; }
.option-address { float: right; color: var(--el-text-color-secondary); font-size: 12px; margin-left: 14px; }
.task-error { color: var(--el-color-danger); margin: 18px 0 10px; }
pre { max-height: 260px; overflow: auto; white-space: pre-wrap; overflow-wrap: anywhere; background: #111827; color: #e5e7eb; border-radius: 6px; padding: 12px; font-size: 12px; line-height: 1.55; }
</style>
