<template>
  <el-container v-if="showShell" class="app-container">
    <el-aside width="220px">
      <div class="logo">
        <el-icon><Coin /></el-icon>
        <span>数据库AI自动化运维平台</span>
      </div>
      <el-menu :default-active="activeMenu" router class="sidebar">
        <el-menu-item index="/dashboard">
          <el-icon><DataLine /></el-icon>
          <span>首页</span>
        </el-menu-item>
        <el-menu-item index="/databases">
          <el-icon><DataBoard /></el-icon>
          <span>数据库</span>
        </el-menu-item>
        <el-menu-item index="/backups">
          <el-icon><DocumentCopy /></el-icon>
          <span>备份</span>
        </el-menu-item>
        <el-menu-item index="/schedules">
          <el-icon><Timer /></el-icon>
          <span>定时</span>
        </el-menu-item>

        <el-sub-menu index="/servers">
          <template #title>
            <el-icon><Monitor /></el-icon>
            <span>服务器</span>
          </template>
          <el-menu-item index="/servers/hosts">主机添加</el-menu-item>
          <el-menu-item index="/servers/batch-ops">批量运维</el-menu-item>
          <el-menu-item index="/servers/batch-inspection">批量巡检</el-menu-item>
          <el-menu-item index="/servers/knowledge">知识库</el-menu-item>
        </el-sub-menu>

        <el-sub-menu index="/middleware">
          <template #title>
            <el-icon><Connection /></el-icon>
            <span>中间件</span>
          </template>
          <el-menu-item index="/middleware/deploy">部署</el-menu-item>
          <el-menu-item index="/middleware/inspection">巡检</el-menu-item>
          <el-menu-item index="/middleware/troubleshoot">故障排查</el-menu-item>
          <el-menu-item index="/middleware/knowledge">知识库</el-menu-item>
        </el-sub-menu>

        <el-menu-item index="/data-migration">
          <el-icon><Switch /></el-icon>
          <span>数据迁移</span>
        </el-menu-item>

        <el-sub-menu index="/inspection">
          <template #title>
            <el-icon><List /></el-icon>
            <span>巡检</span>
          </template>
          <el-menu-item index="/inspection/one-click">一键巡检</el-menu-item>
          <el-menu-item index="/inspection/reports">巡检报告</el-menu-item>
        </el-sub-menu>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="topbar">
        <div class="topbar-left">控制台</div>
        <div class="topbar-right">
          <el-input class="search" placeholder="搜索" clearable />
          <el-dropdown trigger="click">
            <div class="user">
              <el-icon><User /></el-icon>
              <span>管理员</span>
              <el-icon><ArrowDown /></el-icon>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>

  <router-view v-else />
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { clearToken } from '@/utils/auth'

const route = useRoute()
const router = useRouter()
const activeMenu = computed(() => route.path)
const showShell = computed(() => !route.meta?.public)

const logout = () => {
  clearToken()
  router.replace('/login')
}
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

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid #e4e7ed;
  background: #ffffff;
}

.topbar-left {
  font-weight: 600;
  color: #0f172a;
}

.topbar-right {
  display: flex;
  align-items: center;
  gap: 14px;
}

.search {
  width: 260px;
}

.user {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  color: #334155;
}

.main {
  padding: 0;
  background: #f5f7fb;
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
