import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '@/views/Dashboard.vue'
import Databases from '@/views/Databases.vue'
import Backups from '@/views/Backups.vue'
import Schedules from '@/views/Schedules.vue'
import Login from '@/views/Login.vue'
import { getToken } from '@/utils/auth'
import AssetsOverview from '@/views/assets/Overview.vue'
import AssetSystems from '@/views/assets/Systems.vue'
import AssetCredentials from '@/views/assets/Credentials.vue'
import AssetGroups from '@/views/assets/Groups.vue'
import AssetList from '@/views/assets/List.vue'
import IPAssets from '@/views/assets/IPAssets.vue'
import AssetIdcs from '@/views/assets/Idcs.vue'
import AssetTags from '@/views/assets/Tags.vue'
import Hosts from '@/views/servers/Hosts.vue'
import ServerBackups from '@/views/servers/Backups.vue'
import ServerSchedules from '@/views/servers/Schedules.vue'
import HostBatchOps from '@/views/servers/BatchOps.vue'
import HostBatchInspection from '@/views/servers/BatchInspection.vue'
import HostKnowledge from '@/views/servers/Knowledge.vue'
import MiddlewareDeploy from '@/views/middleware/Deploy.vue'
import MiddlewareInspection from '@/views/middleware/Inspection.vue'
import MiddlewareTroubleshoot from '@/views/middleware/Troubleshoot.vue'
import MiddlewareKnowledge from '@/views/middleware/Knowledge.vue'
import DataMigration from '@/views/DataMigration.vue'
import OneClickInspection from '@/views/inspection/OneClick.vue'
import InspectionReports from '@/views/inspection/Reports.vue'
import About from '@/views/About.vue'
import Agent from '@/views/Agent.vue'
import SystemRoles from '@/views/system/Roles.vue'
import SystemUsers from '@/views/system/Users.vue'
import Topology from '@/views/assets/Topology.vue'
import Performance from '@/views/monitor/Performance.vue'
import SlowQueries from '@/views/sql/SlowQueries.vue'

const routes = [
  {
    path: '/',
    redirect: '/dashboard'
  },
  {
    path: '/login',
    component: Login,
    meta: { public: true }
  },
  {
    path: '/dashboard',
    component: Dashboard,
    meta: { requiresAuth: true }
  },
  {
    path: '/assets/overview',
    component: AssetsOverview,
    meta: { requiresAuth: true }
  },
  {
    path: '/assets/systems',
    component: AssetSystems,
    meta: { requiresAuth: true }
  },
  {
    path: '/assets/credentials',
    component: AssetCredentials,
    meta: { requiresAuth: true }
  },
  {
    path: '/assets/groups',
    component: AssetGroups,
    meta: { requiresAuth: true }
  },
  {
    path: '/assets/list',
    component: AssetList,
    meta: { requiresAuth: true }
  },
  {
    path: '/assets/ips',
    component: IPAssets,
    meta: { requiresAuth: true }
  },
  {
    path: '/assets/idcs',
    component: AssetIdcs,
    meta: { requiresAuth: true }
  },
  {
    path: '/assets/tags',
    component: AssetTags,
    meta: { requiresAuth: true }
  },
  {
    path: '/databases',
    component: Databases,
    meta: { requiresAuth: true }
  },
  {
    path: '/backups',
    component: Backups,
    meta: { requiresAuth: true }
  },
  {
    path: '/schedules',
    component: Schedules,
    meta: { requiresAuth: true }
  },
  {
    path: '/servers/hosts',
    component: Hosts,
    meta: { requiresAuth: true }
  },
  {
    path: '/servers/backups',
    component: ServerBackups,
    meta: { requiresAuth: true }
  },
  {
    path: '/servers/schedules',
    component: ServerSchedules,
    meta: { requiresAuth: true }
  },
  {
    path: '/servers/batch-ops',
    component: HostBatchOps,
    meta: { requiresAuth: true }
  },
  {
    path: '/servers/batch-inspection',
    component: HostBatchInspection,
    meta: { requiresAuth: true }
  },
  {
    path: '/servers/knowledge',
    component: HostKnowledge,
    meta: { requiresAuth: true }
  },
  {
    path: '/middleware/deploy',
    component: MiddlewareDeploy,
    meta: { requiresAuth: true }
  },
  {
    path: '/middleware/inspection',
    component: MiddlewareInspection,
    meta: { requiresAuth: true }
  },
  {
    path: '/middleware/troubleshoot',
    component: MiddlewareTroubleshoot,
    meta: { requiresAuth: true }
  },
  {
    path: '/middleware/knowledge',
    component: MiddlewareKnowledge,
    meta: { requiresAuth: true }
  },
  {
    path: '/data-migration',
    component: DataMigration,
    meta: { requiresAuth: true }
  },
  {
    path: '/inspection/one-click',
    component: OneClickInspection,
    meta: { requiresAuth: true }
  },
  {
    path: '/inspection/reports',
    component: InspectionReports,
    meta: { requiresAuth: true }
  },
  {
    path: '/about',
    component: About,
    meta: { requiresAuth: true }
  },
  {
    path: '/agent',
    component: Agent,
    meta: { requiresAuth: true }
  },
  {
    path: '/system/roles',
    component: SystemRoles,
    meta: { requiresAuth: true }
  },
  {
    path: '/system/users',
    component: SystemUsers,
    meta: { requiresAuth: true }
  },
  {
    path: '/assets/topology',
    component: Topology,
    meta: { requiresAuth: true }
  },
  {
    path: '/monitor/performance',
    component: Performance,
    meta: { requiresAuth: true }
  },
  {
    path: '/sql/slow-queries',
    component: SlowQueries,
    meta: { requiresAuth: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to) => {
  if (to.meta.public) return true
  if (to.meta.requiresAuth && !getToken()) return { path: '/login' }
  if (to.path === '/login' && getToken()) return { path: '/dashboard' }
  return true
})

export default router
