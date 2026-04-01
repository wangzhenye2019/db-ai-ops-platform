<template>
  <div class="page">
    <div class="title-row">
      <div class="title">一键巡检</div>
      <el-button type="primary" :loading="running" @click="run">立即巡检</el-button>
    </div>
    <el-card class="card">
      <el-form label-position="top">
        <el-row :gutter="12">
          <el-col :span="8">
            <el-form-item label="范围">
              <el-select v-model="scope" style="width:100%">
                <el-option label="服务器" value="server" />
                <el-option label="中间件" value="middleware" />
                <el-option label="数据库" value="database" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="16">
            <el-form-item label="目标">
              <el-select v-model="targetIds" multiple filterable style="width:100%" placeholder="选择目标">
                <el-option v-for="t in targets" :key="t.id" :label="t.label" :value="t.id" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>

      <el-alert type="info" show-icon :closable="false" title="当前为演示模式：巡检结果为模拟生成，可用于打通流程与报告生成。"/>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { databaseAPI, hostAPI, inspectionAPI, middlewareAPI } from '@/api/services'

const scope = ref('server')
const targetIds = ref([])
const running = ref(false)

const hosts = ref([])
const middlewares = ref([])
const databases = ref([])

const targets = computed(() => {
  if (scope.value === 'server') return hosts.value.map(h => ({ id: h.id, label: `${h.name} (${h.host})` }))
  if (scope.value === 'middleware') return middlewares.value.map(m => ({ id: m.id, label: `${m.name} (${m.mw_type}@${m.host}:${m.port})` }))
  return databases.value.map(d => ({ id: d.id, label: `${d.name} (${d.db_type})` }))
})

const load = async () => {
  const [h, m, d] = await Promise.allSettled([hostAPI.list(), middlewareAPI.list(), databaseAPI.list()])
  if (h.status === 'fulfilled') hosts.value = h.value.hosts || []
  if (m.status === 'fulfilled') middlewares.value = m.value.middlewares || []
  if (d.status === 'fulfilled') databases.value = d.value.databases || []
}

const run = async () => {
  if (!targetIds.value.length) {
    ElMessage.warning('请选择目标')
    return
  }
  running.value = true
  try {
    await inspectionAPI.run({ scope: scope.value, target_ids: targetIds.value })
    ElMessage.success('已发起巡检（演示模式）')
  } catch (e) {
    ElMessage.error(e.message || '发起失败')
  } finally {
    running.value = false
  }
}

watch(scope, () => {
  targetIds.value = []
})

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
</style>
