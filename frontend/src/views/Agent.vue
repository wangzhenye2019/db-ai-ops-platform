<template>
  <div class="page">
    <div class="title-row">
      <div class="title">智能体（ChatOps）</div>
      <div class="actions">
        <el-button @click="openTools">工具</el-button>
        <el-button type="primary" @click="newSession">新会话</el-button>
      </div>
    </div>

    <el-card class="card">
      <div ref="scrollRef" class="messages">
        <div v-for="m in messages" :key="m.id" class="msg" :class="`role-${m.role}`">
          <div class="meta">
            <span class="role">{{ roleLabel(m.role) }}</span>
            <span class="time">{{ m.created_at }}</span>
          </div>
          <pre class="content">{{ m.content }}</pre>
        </div>
      </div>

      <div v-if="pending" class="pending">
        <div class="pending-title">待确认执行</div>
        <pre class="pending-body">{{ JSON.stringify(pending, null, 2) }}</pre>
        <div class="pending-actions">
          <el-button type="primary" :loading="sending" @click="confirmPending">执行</el-button>
          <el-button :disabled="sending" @click="cancelPending">取消</el-button>
        </div>
      </div>

      <div class="composer">
        <el-input
          v-model="input"
          type="textarea"
          :rows="3"
          placeholder="例如：备份统计；搜索主机 10.0.0.10；在 10.0.0.10 执行 `uptime`"
          @keydown.enter.exact.prevent="send()"
        />
        <div class="composer-actions">
          <el-button type="primary" :loading="sending" @click="send">发送</el-button>
        </div>
      </div>
    </el-card>

    <el-dialog v-model="toolsVisible" title="工具列表" width="760px">
      <el-table :data="tools" stripe>
        <el-table-column prop="name" label="名称" width="200" />
        <el-table-column prop="description" label="说明" min-width="280" />
        <el-table-column prop="readonly" label="只读" width="100">
          <template #default="{ row }">
            <span class="muted">{{ row.readonly ? '是' : '否' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="参数" min-width="260">
          <template #default="{ row }">
            <el-button text @click="viewSchema(row)">查看</el-button>
          </template>
        </el-table-column>
      </el-table>
      <template #footer>
        <el-button @click="toolsVisible=false">关闭</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="schemaVisible" title="参数 Schema" width="760px">
      <el-input v-model="schemaText" type="textarea" :rows="18" readonly />
      <template #footer>
        <el-button @click="schemaVisible=false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { agentAPI } from '@/api/services'

const SESSION_KEY = 'agentSessionId'

const sessionId = ref(null)
const messages = ref([])
const pending = ref(null)
const input = ref('')
const sending = ref(false)
const scrollRef = ref()

const toolsVisible = ref(false)
const tools = ref([])
const schemaVisible = ref(false)
const schemaText = ref('')

const roleLabel = (r) => {
  if (r === 'user') return '你'
  if (r === 'assistant') return '智能体'
  if (r === 'tool') return '工具'
  return r || ''
}

const scrollToBottom = async () => {
  await nextTick()
  const el = scrollRef.value
  if (!el) return
  el.scrollTop = el.scrollHeight
}

const load = async () => {
  if (!sessionId.value) return
  const data = await agentAPI.listMessages(sessionId.value)
  messages.value = data.messages || []
  pending.value = data.session?.state?.pending || data.pending || null
  await scrollToBottom()
}

const ensureSession = async () => {
  const saved = localStorage.getItem(SESSION_KEY)
  if (saved) {
    sessionId.value = Number(saved)
    try {
      await load()
      return
    } catch {
      localStorage.removeItem(SESSION_KEY)
      sessionId.value = null
    }
  }
  const s = await agentAPI.createSession({ title: 'ChatOps' })
  sessionId.value = s.id
  localStorage.setItem(SESSION_KEY, String(s.id))
  await load()
}

const newSession = async () => {
  const s = await agentAPI.createSession({ title: 'ChatOps' })
  sessionId.value = s.id
  localStorage.setItem(SESSION_KEY, String(s.id))
  messages.value = []
  pending.value = null
  await load()
}

const send = async (opts = {}) => {
  if (!sessionId.value) return
  const text = (opts.content ?? input.value ?? '').trim()
  if (!text && !opts.confirm && !opts.cancel) {
    ElMessage.warning('请输入内容')
    return
  }
  sending.value = true
  try {
    const res = await agentAPI.sendMessage(sessionId.value, {
      content: text,
      confirm: !!opts.confirm,
      cancel: !!opts.cancel
    })
    const out = res.messages || []
    for (const m of out) messages.value.push(m)
    pending.value = res.pending || res.session?.state?.pending || null
    input.value = ''
    await scrollToBottom()
  } catch (e) {
    ElMessage.error(e.message || '发送失败')
  } finally {
    sending.value = false
  }
}

const confirmPending = async () => {
  await send({ content: '确认', confirm: true })
}

const cancelPending = async () => {
  await send({ content: '取消', cancel: true })
}

const openTools = async () => {
  toolsVisible.value = true
  try {
    const data = await agentAPI.tools()
    tools.value = data.tools || []
  } catch (e) {
    ElMessage.error(e.message || '加载失败')
  }
}

const viewSchema = async (row) => {
  schemaText.value = JSON.stringify(row.parameters || {}, null, 2)
  schemaVisible.value = true
}

onMounted(async () => {
  try {
    await ensureSession()
  } catch (e) {
    ElMessageBox.alert(e.message || '初始化失败', '提示')
  }
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
.messages {
  height: calc(100vh - 320px);
  overflow: auto;
  padding: 12px;
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
}
.msg {
  padding: 10px 12px;
  border-radius: 8px;
  margin-bottom: 10px;
  border: 1px solid #eef2f7;
}
.role-user {
  background: #f8fafc;
}
.role-assistant {
  background: #f0f9ff;
}
.role-tool {
  background: #f8fef2;
}
.meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}
.role {
  font-weight: 600;
  color: #0f172a;
}
.time {
  color: #94a3b8;
  font-size: 12px;
}
.content {
  white-space: pre-wrap;
  margin: 0;
  color: #0f172a;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
  font-size: 12px;
}
.pending {
  margin-top: 12px;
  padding: 12px;
  border: 1px solid #fde68a;
  background: #fffbeb;
  border-radius: 8px;
}
.pending-title {
  font-weight: 700;
  margin-bottom: 8px;
  color: #92400e;
}
.pending-body {
  margin: 0;
  white-space: pre-wrap;
  font-size: 12px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
  color: #0f172a;
}
.pending-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
  margin-top: 10px;
}
.composer {
  margin-top: 12px;
}
.composer-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 8px;
}
.muted {
  color: #64748b;
}
</style>

