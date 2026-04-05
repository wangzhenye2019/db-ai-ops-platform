<template>
  <div class="page-header">
    <div class="breadcrumb-wrapper">
      <el-breadcrumb separator="/">
        <el-breadcrumb-item :to="{ path: '/dashboard' }">
          <el-icon><HomeFilled /></el-icon>
        </el-breadcrumb-item>
        <el-breadcrumb-item v-for="(item, index) in breadcrumbs" :key="index" :to="item.path">
          {{ item.title }}
        </el-breadcrumb-item>
      </el-breadcrumb>
    </div>
    <div class="title-wrapper">
      <h1 class="page-title">{{ title }}</h1>
      <p v-if="description" class="page-description">{{ description }}</p>
    </div>
    <div v-if="$slots.extra" class="extra-wrapper">
      <slot name="extra" />
    </div>
  </div>
</template>

<script setup>
import { HomeFilled } from '@element-plus/icons-vue'

defineProps({
  title: {
    type: String,
    required: true
  },
  description: {
    type: String,
    default: ''
  },
  breadcrumbs: {
    type: Array,
    default: () => []
  }
})
</script>

<style scoped>
.page-header {
  padding: 16px 24px 8px;
  background: #ffffff;
  border-bottom: 1px solid #e4e7ed;
}

.breadcrumb-wrapper {
  margin-bottom: 12px;
}

.title-wrapper {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.page-title {
  font-size: 20px;
  font-weight: 600;
  color: #0f172a;
  margin: 0;
}

.page-description {
  font-size: 13px;
  color: #64748b;
  margin: 0;
}

.extra-wrapper {
  margin-top: 12px;
  display: flex;
  gap: 10px;
}

:deep(.el-breadcrumb__item) {
  display: flex;
  align-items: center;
}

:deep(.el-breadcrumb__inner) {
  display: flex;
  align-items: center;
  gap: 4px;
}
</style>
