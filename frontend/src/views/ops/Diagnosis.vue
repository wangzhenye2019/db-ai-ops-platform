<template>
  <div class="page">
    <div class="title-row">
      <div class="title">智能诊断</div>
    </div>

    <!-- Select Target -->
    <el-card class="card">
      <el-form inline>
        <el-form-item label="目标类型">
          <el-select v-model="targetType" style="width:140px" @change="loadTargets">
            <el-option label="数据库" value="database" />
            <el-option label="主机" value="host" />
            <el-option label="中间件" value="middleware" />
          </el-select>
        </el-form-item>
        <el-form-item label="选择目标">
          <el-select v-model="targetId" style="width:200px" placeholder="请选择">
            <el-option v-for="t in targets" :key="t.id" :label="t.name" :value="t.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="诊断症状">
          <el-select v-model="selectedSymptoms" multiple placeholder="全部" style="width:300px">
            <el-option v-for="r in rules" :key="r.code" :label="r.symptom" :value="r.code" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="runDiagnosis" :loading="loading">开始诊断</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- Results -->
    <div v-if="results.length" class="results">
      <el-card v-for="(r, i) in results" :key="i" class="result-card">
        <div class="result-header">
          <span class="symptom">{{ r.symptom }}</span>
          <el-tag :type="getSeverityType(r.severity)">{{ getSeverityText(r.severity) }}</el-tag>
          <span class="confidence">置信度: {{ (r.confidence * 100).toFixed(0) }}%</span>
        </div>

        <div class="result-section">
          <div class="section-title">可能原因</div>
          <div class="causes">
            <el-tag v-for="(c, j) in r.causes" :key="j" type="warning" class="cause-tag">{{ c }}</el-tag>
          </div>
        </div>

        <div class="result-section">
          <div class="section-title">检查项</div>
          <ul class="checks">
            <li v-for="(c, j) in r.checks" :key="j">{{ c }}</li>
          </ul>
        </div>

        <div class="result-section">
          <div class="section-title">优化建议</div>
          <ul class="suggestions">
            <li v-for="(s, j) in r.suggestions" :key="j">{{ s }}</li>
          </ul>
        </div>
      </el-card>
    </div>

    <!-- Empty State -->
    <el-empty v-else description="请选择目标并开始诊断" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { diagnosisAPI } from '@/api/services'

const targetType = ref('database')
const targetId = ref(null)
const selectedSymptoms = ref([])
const targets = ref([])
const rules = ref([])
const results = ref([])
const loading = ref(false)

const getSeverityType = (severity) => {
  const types = { critical: 'danger', warning: 'warning', info: 'info' }
  return types[severity] || 'info'
}

const getSeverityText = (severity) => {
  const texts = { critical: '严重', warning: '警告', info: '提示' }
  return texts[severity] || severity
}

const loadTargets = async () => {
  try {
    const res = await diagnosisAPI.getTargets(targetType.value)
    targets.value = res.targets || []
    targetId.value = targets.value.length ? targets.value[0].id : null
  } catch (e) {
    console.error(e)
  }
}

const loadRules = async () => {
  try {
    const res = await diagnosisAPI.getRules()
    rules.value = res.rules || []
  } catch (e) {
    console.error(e)
  }
}

const runDiagnosis = async () => {
  if (!targetId.value) {
    return ElMessage.warning('请选择诊断目标')
  }

  loading.value = true
  try {
    const res = await diagnosisAPI.runDiagnosis({
      target_type: targetType.value,
      target_id: targetId.value,
      symptoms: selectedSymptoms.value.length ? selectedSymptoms.value : []
    })
    results.value = res.results || []
    if (!results.value.length) {
      ElMessage.info('未发现异常')
    }
  } catch (e) {
    ElMessage.error(e.message || '诊断失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadTargets()
  loadRules()
})
</script>

<style scoped>
.page { padding: 16px; }
.title-row { display: flex; align-items: center; justify-content: space-between; padding: 12px 16px; }
.title { font-size: 16px; font-weight: 700; color: #0f172a; }
.card { margin-bottom: 16px; }
.results { display: flex; flex-direction: column; gap: 12px; }
.result-card { margin: 0 8px; }
.result-header { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; }
.symptom { font-size: 16px; font-weight: 600; color: #303133; }
.confidence { color: #909399; font-size: 12px; margin-left: auto; }
.result-section { margin-bottom: 12px; }
.section-title { font-size: 14px; font-weight: 600; color: #606266; margin-bottom: 8px; }
.causes { display: flex; flex-wrap: wrap; gap: 8px; }
.cause-tag { margin: 4px; }
.checks, .suggestions { margin: 0; padding-left: 20px; color: #606266; }
.checks li, .suggestions li { margin: 4px 0; }
.suggestions li { color: #409eff; }
</style>