<template>
  <div class="page">
    <div class="title">关于我们</div>
    <el-card class="card">
      <div class="name">AI智能运维平台</div>
      <div class="desc">
        聚焦数据库、服务器与中间件等运维场景，提供资产管理、批量运维、巡检与报告、知识库沉淀等能力。
      </div>
      <el-divider />
      <el-descriptions :column="2" border>
        <el-descriptions-item label="版本">{{ version }}</el-descriptions-item>
        <el-descriptions-item label="定位">AI 辅助运维编排与审计</el-descriptions-item>
        <el-descriptions-item label="能力域">资产 / 运维 / 巡检 / 知识库</el-descriptions-item>
        <el-descriptions-item label="支持">多数据库与多中间件生态</el-descriptions-item>
      </el-descriptions>
    </el-card>
  </div>
</template>

<script setup>
const version = 'v0.4.5'
</script>

<style scoped>
.page {
  padding: 16px;
}
.title {
  font-size: 16px;
  font-weight: 700;
  color: #0f172a;
  padding: 12px 16px;
}
.card {
  margin: 0 8px;
}
.name {
  font-size: 18px;
  font-weight: 800;
  color: #0f172a;
}
.desc {
  margin-top: 8px;
  color: #475569;
  line-height: 1.7;
}
</style>
