<template>
  <div class="page">
    <div class="title-row">
      <div class="title">资产列表</div>
      <el-button @click="load">刷新</el-button>
    </div>

    <el-card class="card">
      <el-row :gutter="12" class="filters">
        <el-col :span="6">
          <el-select v-model="type" style="width:100%" placeholder="类型">
            <el-option label="全部" value="" />
            <el-option label="主机" value="host" />
            <el-option label="数据库" value="database" />
            <el-option label="中间件" value="middleware" />
          </el-select>
        </el-col>
        <el-col :span="6">
          <el-select v-model="groupId" style="width:100%" placeholder="分组" clearable>
            <el-option v-for="g in groups" :key="g.id" :label="g.name" :value="g.id" />
          </el-select>
        </el-col>
        <el-col :span="12">
          <el-input v-model="q" placeholder="搜索（名称/地址）" clearable @keyup.enter="load" />
        </el-col>
      </el-row>

      <el-table :data="assets" stripe>
        <el-table-column prop="type" label="类型" width="120" />
        <el-table-column prop="label" label="资产" min-width="460" />
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
        <el-table-column label="环境" width="100">
          <template #default="{ row }">
            <span>{{ row.data?.env || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="启用" width="100">
          <template #default="{ row }">
            <el-tag :type="row.data?.enabled ? 'success' : 'info'">{{ row.data?.enabled ? '是' : '否' }}</el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { assetsAPI } from '@/api/services'

const assets = ref([])
const groups = ref([])
const type = ref('')
const groupId = ref(null)
const q = ref('')

const load = async () => {
  try {
    const [g, a] = await Promise.all([
      assetsAPI.listGroups(),
      assetsAPI.listAssets({ type: type.value || undefined, group_id: groupId.value || undefined, q: q.value || undefined })
    ])
    groups.value = g.groups || []
    assets.value = a.assets || []
  } catch (e) {
    ElMessage.error(e.message || '加载失败')
  }
}

watch([type, groupId], () => load())

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
.filters {
  margin-bottom: 12px;
}
</style>
