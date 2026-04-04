<template>
  <div class="page">
    <div class="title-row">
      <div class="title">通知渠道管理</div>
      <div class="actions">
        <el-button @click="load" :icon="Refresh">刷新</el-button>
        <el-button type="primary" @click="openCreate" :icon="Plus">新建渠道</el-button>
      </div>
    </div>

    <el-row :gutter="16">
      <el-col :span="8" v-for="channel in channels" :key="channel.id">
        <el-card class="channel-card" :class="{ disabled: !channel.enabled }">
          <div class="channel-header">
            <div class="channel-icon">
              <el-icon :size="28" :color="channelTypeColor(channel.channel_type)">
                <component :is="channelTypeIcon(channel.channel_type)" />
              </el-icon>
            </div>
            <div class="channel-info">
              <div class="channel-name">{{ channel.name }}</div>
              <el-tag size="small" :type="channel.enabled ? 'success' : 'info'">
                {{ channel.enabled ? '启用' : '禁用' }}
              </el-tag>
            </div>
            <el-dropdown trigger="click">
              <el-button link :icon="More" />
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item @click="testChannel(channel)">发送测试</el-dropdown-item>
                  <el-dropdown-item @click="openEdit(channel)">编辑</el-dropdown-item>
                  <el-dropdown-item divided type="danger" @click="onDelete(channel)">删除</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>

          <el-divider />

          <div class="channel-detail">
            <div class="detail-item">
              <span class="label">类型</span>
              <span class="value">{{ channelTypeLabel(channel.channel_type) }}</span>
            </div>
            <div class="detail-item" v-if="channel.config.url">
              <span class="label">URL</span>
              <span class="value">{{ maskUrl(channel.config.url) }}</span>
            </div>
            <div class="detail-item" v-if="channel.config.smtp_host">
              <span class="label">SMTP</span>
              <span class="value">{{ channel.config.smtp_host }}</span>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 创建/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑通知渠道' : '新建通知渠道'" width="600px">
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
        <el-row :gutter="12">
          <el-col :span="16">
            <el-form-item label="渠道名称" prop="name">
              <el-input v-model="form.name" placeholder="例如：运维值班群" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="渠道类型" prop="channel_type">
              <el-select v-model="form.channel_type" style="width:100%" @change="onTypeChange">
                <el-option label="Webhook" value="webhook" />
                <el-option label="邮件" value="email" />
                <el-option label="企业微信" value="wechat" />
                <el-option label="钉钉" value="dingtalk" />
                <el-option label="飞书" value="feishu" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <!-- Webhook 配置 -->
        <template v-if="form.channel_type === 'webhook'">
          <el-form-item label="Webhook URL">
            <el-input v-model="form.config.url" placeholder="https://..." />
          </el-form-item>
          <el-form-item label="签名密钥（可选）">
            <el-input v-model="form.config.secret" type="password" show-password />
          </el-form-item>
        </template>

        <!-- 邮件配置 -->
        <template v-if="form.channel_type === 'email'">
          <el-row :gutter="12">
            <el-col :span="16">
              <el-form-item label="SMTP 服务器">
                <el-input v-model="form.config.smtp_host" placeholder="smtp.example.com" />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="端口">
                <el-input-number v-model="form.config.smtp_port" :min="1" :max="65535" style="width:100%" />
              </el-form-item>
            </el-col>
          </el-row>
          <el-row :gutter="12">
            <el-col :span="12">
              <el-form-item label="用户名">
                <el-input v-model="form.config.smtp_user" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="密码">
                <el-input v-model="form.config.smtp_password" type="password" show-password />
              </el-form-item>
            </el-col>
          </el-row>
          <el-form-item label="发件人">
            <el-input v-model="form.config.from_addr" placeholder="alert@example.com" />
          </el-form-item>
          <el-form-item label="收件人（逗号分隔）">
            <el-input v-model="toAddrsText" type="textarea" :rows="2" />
          </el-form-item>
        </template>

        <!-- 企业微信配置 -->
        <template v-if="form.channel_type === 'wechat'">
          <el-row :gutter="12">
            <el-col :span="12">
              <el-form-item label="CorpID">
                <el-input v-model="form.config.corp_id" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="AgentID">
                <el-input v-model="form.config.agent_id" />
              </el-form-item>
            </el-col>
          </el-row>
          <el-form-item label="Secret">
            <el-input v-model="form.config.secret" type="password" show-password />
          </el-form-item>
          <el-form-item label="接收用户（可选，默认@all）">
            <el-input v-model="form.config.to_user" placeholder="UserID1|UserID2" />
          </el-form-item>
        </template>

        <!-- 钉钉配置 -->
        <template v-if="form.channel_type === 'dingtalk'">
          <el-form-item label="Webhook">
            <el-input v-model="form.config.webhook" placeholder="https://oapi.dingtalk.com/robot/send?access_token=..." />
          </el-form-item>
          <el-form-item label="加签密钥（可选）">
            <el-input v-model="form.config.secret" type="password" show-password />
          </el-form-item>
          <el-form-item>
            <el-switch v-model="form.config.at_all" active-text="@所有人" />
          </el-form-item>
        </template>

        <!-- 飞书配置 -->
        <template v-if="form.channel_type === 'feishu'">
          <el-form-item label="Webhook">
            <el-input v-model="form.config.webhook" placeholder="https://open.feishu.cn/open-apis/bot/v2/hook/..." />
          </el-form-item>
          <el-form-item label="加签密钥（可选）">
            <el-input v-model="form.config.secret" type="password" show-password />
          </el-form-item>
        </template>

        <el-form-item label="启用">
          <el-switch v-model="form.enabled" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button @click="testForm">发送测试</el-button>
        <el-button type="primary" :loading="saving" @click="onSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh, More, Link, Message, ChatDotRound, Bell, Promotion } from '@element-plus/icons-vue'

const channels = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const saving = ref(false)
const formRef = ref()
const editingId = ref(null)

const form = reactive({
  name: '',
  channel_type: 'webhook',
  enabled: true,
  config: {}
})

const toAddrsText = computed({
  get: () => form.config.to_addrs?.join(', ') || '',
  set: (val) => { form.config.to_addrs = val.split(',').map(s => s.trim()).filter(Boolean) }
})

const rules = {
  name: [{ required: true, message: '请输入渠道名称', trigger: 'blur' }],
  channel_type: [{ required: true, message: '请选择渠道类型', trigger: 'change' }]
}

const channelTypeIcon = (type) => {
  const map = {
    webhook: Link,
    email: Message,
    wechat: ChatDotRound,
    dingtalk: Bell,
    feishu: Promotion
  }
  return map[type] || Link
}

const channelTypeColor = (type) => {
  const map = {
    webhook: '#409eff',
    email: '#67c23a',
    wechat: '#07c160',
    dingtalk: '#007fff',
    feishu: '#3370ff'
  }
  return map[type] || '#909399'
}

const channelTypeLabel = (type) => {
  const map = {
    webhook: 'Webhook',
    email: '邮件',
    wechat: '企业微信',
    dingtalk: '钉钉',
    feishu: '飞书'
  }
  return map[type] || type
}

const maskUrl = (url) => {
  if (!url) return '-'
  if (url.length < 30) return url
  return url.substring(0, 30) + '...'
}

const load = async () => {
  loading.value = true
  try {
    const res = await fetch('/api/alerts/channels')
    const data = await res.json()
    channels.value = data.data?.channels || []
  } catch (e) {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

const resetForm = () => {
  editingId.value = null
  Object.assign(form, {
    name: '',
    channel_type: 'webhook',
    enabled: true,
    config: {}
  })
  formRef.value?.clearValidate?.()
}

const openCreate = () => {
  resetForm()
  dialogVisible.value = true
}

const openEdit = (row) => {
  editingId.value = row.id
  Object.assign(form, {
    name: row.name,
    channel_type: row.channel_type,
    enabled: row.enabled,
    config: { ...row.config }
  })
  dialogVisible.value = true
}

const onTypeChange = () => {
  form.config = {}
}

const onSave = async () => {
  await formRef.value?.validate(async (valid) => {
    if (!valid) return
    saving.value = true
    try {
      const url = editingId.value ? `/api/alerts/channels/${editingId.value}` : '/api/alerts/channels'
      const method = editingId.value ? 'PUT' : 'POST'
      const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form)
      })
      const data = await res.json()
      if (data.success) {
        ElMessage.success('保存成功')
        dialogVisible.value = false
        load()
      } else {
        ElMessage.error(data.message)
      }
    } catch (e) {
      ElMessage.error('保存失败')
    } finally {
      saving.value = false
    }
  })
}

const testChannel = async (channel) => {
  try {
    const res = await fetch(`/api/alerts/channels/${channel.id}/test`, { method: 'POST' })
    const data = await res.json()
    if (data.success) {
      ElMessage.success('测试消息已发送')
    } else {
      ElMessage.error(data.message)
    }
  } catch (e) {
    ElMessage.error('测试失败')
  }
}

const testForm = async () => {
  // 临时保存后测试
  try {
    const res = await fetch('/api/alerts/channels/test', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(form)
    })
    const data = await res.json()
    if (data.success) {
      ElMessage.success('测试消息已发送')
    } else {
      ElMessage.error(data.message)
    }
  } catch (e) {
    ElMessage.error('测试失败')
  }
}

const onDelete = async (row) => {
  try {
    await ElMessageBox.confirm(`确认删除渠道「${row.name}」？`, '提示', { type: 'warning' })
    const res = await fetch(`/api/alerts/channels/${row.id}`, { method: 'DELETE' })
    const data = await res.json()
    if (data.success) {
      ElMessage.success('删除成功')
      load()
    } else {
      ElMessage.error(data.message)
    }
  } catch {}
}

onMounted(load)
</script>

<style scoped>
.page { padding: 16px; }
.title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  margin-bottom: 16px;
}
.title {
  font-size: 18px;
  font-weight: 600;
  color: #0f172a;
}
.actions { display: flex; gap: 10px; }

.channel-card {
  margin-bottom: 16px;
  transition: all 0.3s;
}
.channel-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}
.channel-card.disabled {
  opacity: 0.6;
}

.channel-header {
  display: flex;
  align-items: center;
  gap: 12px;
}
.channel-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  background: #f5f7fa;
  display: flex;
  align-items: center;
  justify-content: center;
}
.channel-info {
  flex: 1;
}
.channel-name {
  font-size: 16px;
  font-weight: 600;
  color: #0f172a;
  margin-bottom: 4px;
}
.channel-detail {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.detail-item {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
}
.detail-item .label {
  color: #909399;
}
.detail-item .value {
  color: #606266;
  font-family: monospace;
}
</style>
