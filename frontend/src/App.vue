<template>
  <el-container class="app-container">
    <el-aside width="200px">
      <div class="logo">
        <el-icon><Coin /></el-icon>
        <span>备份管理平台</span>
      </div>
      <el-menu
        :default-active="activeMenu"
        router
        class="sidebar"
      >
        <el-menu-item index="/dashboard">
          <el-icon><DataLine /></el-icon>
          <span>概览</span>
        </el-menu-item>
        <el-menu-item index="/databases">
          <el-icon><DataBoard /></el-icon>
          <span>数据库</span>
        </el-menu-item>
        <el-menu-item index="/backups">
          <el-icon><DocumentCopy /></el-icon>
          <span>备份记录</span>
        </el-menu-item>
        <el-menu-item index="/schedules">
          <el-icon><Timer /></el-icon>
          <span>定时任务</span>
        </el-menu-item>
      </el-menu>
    </el-aside>
    <el-main>
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const activeMenu = computed(() => route.path)
</script>

<style scoped>
.app-container {
  height: 100vh;
}

.logo {
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 16px;
  font-weight: bold;
  border-bottom: 1px solid #e4e7ed;
}

.sidebar {
  border-right: none;
}
</style>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
}
</style>
