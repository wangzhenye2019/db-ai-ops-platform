<template>
  <div class="page">
    <div class="title-row">
      <div class="title">资产总览</div>
      <el-button @click="load">刷新</el-button>
    </div>

    <el-row :gutter="16" class="kpi-row">
      <el-col :span="6">
        <el-card class="kpi-card">
          <div class="kpi-top">
            <div class="kpi-icon" style="background:#e0f2fe;color:#0284c7">
              <el-icon><Monitor /></el-icon>
            </div>
            <div class="kpi-title">主机</div>
          </div>
          <div class="kpi-value">{{ counts.hosts }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="kpi-card">
          <div class="kpi-top">
            <div class="kpi-icon" style="background:#dcfce7;color:#16a34a">
              <el-icon><DataBoard /></el-icon>
            </div>
            <div class="kpi-title">数据库</div>
          </div>
          <div class="kpi-value">{{ counts.databases }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="kpi-card">
          <div class="kpi-top">
            <div class="kpi-icon" style="background:#fff7ed;color:#ea580c">
              <el-icon><Connection /></el-icon>
            </div>
            <div class="kpi-title">中间件</div>
          </div>
          <div class="kpi-value">{{ counts.middlewares }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="kpi-card">
          <div class="kpi-top">
            <div class="kpi-icon" style="background:#f1f5f9;color:#334155">
              <el-icon><Collection /></el-icon>
            </div>
            <div class="kpi-title">分组</div>
          </div>
          <div class="kpi-value">{{ counts.groups }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" class="bottom-row">
      <el-col :span="24">
        <el-card class="card">
          <template #header>
            <div class="card-title">最近资产</div>
          </template>
          <el-table :data="recent" stripe>
            <el-table-column prop="type" label="类型" width="120" />
            <el-table-column prop="label" label="资产" min-width="360" />
            <el-table-column label="业务系统" min-width="160">
              <template #default="{ row }">
                <span>{{ row.data?.business_system_name || '-' }}</span>
              </template>
            </el-table-column>
            <el-table-column label="负责人" width="120">
              <template #default="{ row }">
                <span>{{ row.data?.owner || '-' }}</span>
              </template>
            </el-table-column>
            <el-table-column label="启用" width="100">
              <template #default="{ row }">
                <el-tag :type="row.data?.enabled ? 'success' : 'info'">{{ row.data?.enabled ? '是' : '否' }}</el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { assetsAPI } from '@/api/services'

const counts = ref({ hosts: 0, databases: 0, middlewares: 0, groups: 0 })
const recent = ref([])

const load = async () => {
  try {
    const [s, a] = await Promise.all([assetsAPI.summary(), assetsAPI.listAssets({})])
    counts.value = s.counts || counts.value
    recent.value = (a.assets || []).slice(0, 10)
  } catch (e) {
    ElMessage.error(e.message || '加载失败')
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
.kpi-row,
.bottom-row {
  padding: 0 8px 16px 8px;
}
.kpi-card {
  border-radius: 10px;
}
.kpi-top {
  display: flex;
  align-items: center;
  gap: 10px;
}
.kpi-icon {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.kpi-title {
  color: #475569;
  font-size: 13px;
}
.kpi-value {
  margin-top: 10px;
  font-size: 26px;
  font-weight: 800;
  color: #0f172a;
}
.card-title {
  font-weight: 600;
  color: #0f172a;
}
</style>
