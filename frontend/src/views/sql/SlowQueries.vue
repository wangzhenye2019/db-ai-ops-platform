<template>
  <div class="page">
    <div class="title-row">
      <div class="title">慢SQL分析</div>
      <div class="actions">
        <el-select v-model="databaseId" placeholder="选择数据库" clearable style="width:180px" @change="loadQueries">
          <el-option v-for="d in databases" :key="d.id" :label="d.name" :value="d.id" />
        </el-select>
        <el-button @click="loadQueries">刷新</el-button>
      </div>
    </div>

    <!-- Stats Cards -->
    <el-row :gutter="16" class="stats-row">
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-label">慢SQL总数</div>
          <div class="stat-value">{{ stats.total }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-label">平均执行时间</div>
          <div class="stat-value">{{ stats.avg_time }}s</div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card class="stat-card">
          <div class="stat-label">高频慢SQL TOP5</div>
          <div class="top-list">
            <div v-for="(q, i) in stats.top_queries?.slice(0, 5)" :key="i" class="top-item">
              <span class="sql-text">{{ q.sql_text?.slice(0, 40) }}...</span>
              <span class="sql-count">{{ q.count }}次</span>
            </div>
            <div v-if="!stats.top_queries?.length" class="empty">暂无数据</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Query List -->
    <el-card class="card">
      <el-table :data="queries" stripe v-loading="loading" @row-click="showDetail">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="sql_text" label="SQL" min-width="300">
          <template #default="{ row }">
            <code class="sql-code">{{ row.sql_text?.slice(0, 80) }}{{ row.sql_text?.length > 80 ? '...' : '' }}</code>
          </template>
        </el-table-column>
        <el-table-column label="执行时间" width="120">
          <template #default="{ row }">
            <el-tag :type="row.execute_time > 5 ? 'danger' : row.execute_time > 2 ? 'warning' : 'success'">
              {{ row.execute_time }}s
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="rows_sent" label="返回行" width="100" />
        <el-table-column prop="rows_examined" label="扫描行" width="100" />
        <el-table-column prop="timestamp" label="时间" width="180" />
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button text @click.stop="analyze(row)">分析</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination
        v-model:current-page="page"
        :page-size="20"
        :total="total"
        layout="total, prev, pager, next"
        @current-change="loadQueries"
        style="margin-top: 16px; justify-content: center;"
      />
    </el-card>

    <!-- Detail Drawer -->
    <el-drawer v-model="detailVisible" :title="`SQL #${detailData.id}`" size="600px">
      <div v-if="detailData" class="detail-content">
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="数据库">{{ detailData.database_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="类型">{{ detailData.db_type }}</el-descriptions-item>
          <el-descriptions-item label="执行时间">{{ detailData.execute_time }}s</el-descriptions-item>
          <el-descriptions-item label="返回行数">{{ detailData.rows_sent }}</el-descriptions-item>
          <el-descriptions-item label="扫描行数">{{ detailData.rows_examined }}</el-descriptions-item>
          <el-descriptions-item label="用户">{{ detailData.user || '-' }}</el-descriptions-item>
        </el-descriptions>

        <div class="sql-section">
          <h4>SQL语句</h4>
          <pre class="sql-block">{{ detailData.sql_text }}</pre>
        </div>

        <div v-if="detailData.analysis" class="analysis-section">
          <h4>分析结果</h4>
          <el-tag :type="getScoreType(detailData.analysis.score)" class="score-tag">
            评分: {{ detailData.analysis.score }}
          </el-tag>
          <div class="risks" v-if="detailData.analysis.risks?.length">
            <div class="risk-label">⚠️ 风险项:</div>
            <ul>
              <li v-for="(r, i) in detailData.analysis.risks" :key="i">{{ r }}</li>
            </ul>
          </div>
          <div class="patterns" v-if="detailData.analysis.patterns?.length">
            <div class="pattern-label">💡 模式:</div>
            <ul>
              <li v-for="(p, i) in detailData.analysis.patterns" :key="i">{{ p }}</li>
            </ul>
          </div>
        </div>

        <div v-if="detailData.suggestion" class="suggestion-section">
          <h4>优化建议</h4>
          <pre class="suggestion-block">{{ detailData.suggestion }}</pre>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { slowsqlAPI, databaseAPI } from '@/api/services'

const queries = ref([])
const loading = ref(false)
const page = ref(1)
const total = ref(0)
const databaseId = ref(null)
const databases = ref([])
const stats = ref({ total: 0, avg_time: 0, top_queries: [] })
const detailVisible = ref(false)
const detailData = ref(null)

const getScoreType = (score) => {
  if (score >= 80) return 'success'
  if (score >= 60) return 'warning'
  return 'danger'
}

const loadDatabases = async () => {
  try {
    const res = await databaseAPI.list()
    databases.value = res.databases || []
  } catch (e) {
    console.error(e)
  }
}

const loadQueries = async () => {
  loading.value = true
  try {
    const res = await slowsqlAPI.listQueries({
      page: page.value,
      per_page: 20,
      database_id: databaseId.value
    })
    queries.value = res.queries || []
    total.value = res.total || 0
  } catch (e) {
    ElMessage.error(e.message || '加载失败')
  } finally {
    loading.value = false
  }
}

const loadStats = async () => {
  try {
    const res = await slowsqlAPI.getStats({ days: 7 })
    stats.value = res
  } catch (e) {
    console.error(e)
  }
}

const showDetail = async (row) => {
  try {
    const res = await slowsqlAPI.getQuery(row.id)
    detailData.value = res
    detailVisible.value = true
  } catch (e) {
    ElMessage.error(e.message || '加载失败')
  }
}

const analyze = async (row) => {
  try {
    await slowsqlAPI.analyzeQuery(row.id)
    ElMessage.success('分析完成')
    await showDetail(row)
    await loadStats()
  } catch (e) {
    ElMessage.error(e.message || '分析失败')
  }
}

onMounted(() => {
  loadDatabases()
  loadQueries()
  loadStats()
})
</script>

<style scoped>
.page { padding: 16px; }
.title-row { display: flex; align-items: center; justify-content: space-between; padding: 12px 16px; }
.title { font-size: 16px; font-weight: 700; color: #0f172a; }
.actions { display: flex; gap: 8px; }
.stats-row { margin-bottom: 16px; }
.stat-card { text-align: center; }
.stat-label { color: #909399; font-size: 14px; }
.stat-value { font-size: 28px; font-weight: 600; color: #303133; margin-top: 8px; }
.top-list { text-align: left; font-size: 12px; }
.top-item { display: flex; justify-content: space-between; padding: 4px 0; border-bottom: 1px dashed #eee; }
.sql-text { color: #606266; max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.sql-count { color: #409eff; }
.empty { color: #909399; text-align: center; padding: 20px; }
.card { margin: 0 8px; }
.sql-code { font-size: 12px; color: #303133; }
.detail-content { padding: 16px; }
.sql-section, .analysis-section, .suggestion-section { margin-top: 20px; }
.sql-section h4, .analysis-section h4, .suggestion-section h4 { margin-bottom: 12px; color: #303133; }
.sql-block { background: #f5f7fa; padding: 12px; border-radius: 4px; font-size: 12px; white-space: pre-wrap; word-break: break-all; }
.suggestion-block { background: #f0f9ff; padding: 12px; border-radius: 4px; font-size: 12px; white-space: pre-wrap; }
.score-tag { margin-bottom: 12px; }
.risks, .patterns { margin: 8px 0; }
.risk-label { color: #e6a23c; font-weight: 600; }
.pattern-label { color: #909399; font-weight: 600; }
.risks ul, .patterns ul { margin: 4px 0; padding-left: 20px; }
</style>