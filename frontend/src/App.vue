<template>
  <el-container v-if="showShell" class="app-container">
    <el-aside width="220px">
      <div class="logo">
        <el-icon><Coin /></el-icon>
        <span>AI智能运维平台</span>
      </div>
      <el-menu :default-active="activeMenu" router class="sidebar">
        <el-menu-item index="/dashboard">
          <el-icon><DataLine /></el-icon>
          <span>首页</span>
        </el-menu-item>
        <el-menu-item index="/agent">
          <el-icon><ChatDotRound /></el-icon>
          <span>智能体</span>
        </el-menu-item>
        <el-sub-menu index="/assets">
          <template #title>
            <el-icon><Collection /></el-icon>
            <span>资产管理</span>
          </template>
          <el-menu-item index="/assets/overview">资产总览</el-menu-item>
          <el-menu-item index="/assets/systems">业务系统</el-menu-item>
          <el-menu-item index="/assets/credentials">凭据库</el-menu-item>
          <el-menu-item index="/assets/groups">资产分组</el-menu-item>
          <el-menu-item index="/assets/list">资产列表</el-menu-item>
          <el-menu-item index="/assets/ips">IP资产</el-menu-item>
          <el-menu-item index="/assets/topology">拓扑图</el-menu-item>
          <el-menu-item index="/assets/idcs">机房区域</el-menu-item>
          <el-menu-item index="/assets/tags">标签体系</el-menu-item>
        </el-sub-menu>
        <el-sub-menu index="/database">
          <template #title>
            <el-icon><DataBoard /></el-icon>
            <span>数据库</span>
          </template>
          <el-menu-item index="/databases">数据库管理</el-menu-item>
          <el-menu-item index="/deployments/mysql">MySQL 自动化部署</el-menu-item>
          <el-menu-item index="/backups">备份记录</el-menu-item>
          <el-menu-item index="/schedules">定时任务</el-menu-item>
          <el-menu-item index="/sql/slow-queries">慢SQL分析</el-menu-item>
          <el-menu-item index="/sql/orders">SQL工单</el-menu-item>
        </el-sub-menu>

        <el-sub-menu index="/servers">
          <template #title>
            <el-icon><Monitor /></el-icon>
            <span>服务器</span>
          </template>
          <el-menu-item index="/servers/hosts">主机添加</el-menu-item>
          <el-menu-item index="/servers/backups">备份</el-menu-item>
          <el-menu-item index="/servers/schedules">定时</el-menu-item>
          <el-menu-item index="/servers/batch-ops">批量运维</el-menu-item>
          <el-menu-item index="/servers/batch-inspection">批量巡检</el-menu-item>
          <el-menu-item index="/ops/diagnosis">智能诊断</el-menu-item>
          <el-menu-item index="/ops/prediction">预测性维护</el-menu-item>
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

        <el-sub-menu index="/monitor">
          <template #title>
            <el-icon><TrendCharts /></el-icon>
            <span>监控</span>
          </template>
          <el-menu-item index="/monitor/performance">性能趋势</el-menu-item>
          <el-menu-item index="/monitor/alert-rules">告警规则</el-menu-item>
          <el-menu-item index="/monitor/alert-history">告警历史</el-menu-item>
        </el-sub-menu>

        <el-menu-item index="/about">
          <el-icon><InfoFilled /></el-icon>
          <span>关于我们</span>
        </el-menu-item>
        <el-sub-menu index="/system">
          <template #title>
            <el-icon><Setting /></el-icon>
            <span>系统</span>
          </template>
          <el-menu-item index="/system/roles">角色管理</el-menu-item>
          <el-menu-item index="/system/users">用户管理</el-menu-item>
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
