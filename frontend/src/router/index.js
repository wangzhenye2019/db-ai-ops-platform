import { createRouter, createWebHistory } from 'vue-router'
import { getToken } from '@/utils/auth'

const lazyView = (path) => () => import(path)
const Dashboard = lazyView('@/views/Dashboard.vue')
const Databases = lazyView('@/views/Databases.vue')
const Backups = lazyView('@/views/Backups.vue')
const Schedules = lazyView('@/views/Schedules.vue')
const Login = lazyView('@/views/Login.vue')
const AssetsOverview = lazyView('@/views/assets/Overview.vue')
const AssetSystems = lazyView('@/views/assets/Systems.vue')
const AssetCredentials = lazyView('@/views/assets/Credentials.vue')
const AssetGroups = lazyView('@/views/assets/Groups.vue')
const AssetList = lazyView('@/views/assets/List.vue')
const IPAssets = lazyView('@/views/assets/IPAssets.vue')
const AssetIdcs = lazyView('@/views/assets/Idcs.vue')
const AssetTags = lazyView('@/views/assets/Tags.vue')
const Hosts = lazyView('@/views/servers/Hosts.vue')
const ServerBackups = lazyView('@/views/servers/Backups.vue')
const ServerSchedules = lazyView('@/views/servers/Schedules.vue')
const HostBatchOps = lazyView('@/views/servers/BatchOps.vue')
const HostBatchInspection = lazyView('@/views/servers/BatchInspection.vue')
const HostKnowledge = lazyView('@/views/servers/Knowledge.vue')
const MiddlewareDeploy = lazyView('@/views/middleware/Deploy.vue')
const MiddlewareInspection = lazyView('@/views/middleware/Inspection.vue')
const MiddlewareTroubleshoot = lazyView('@/views/middleware/Troubleshoot.vue')
const MiddlewareKnowledge = lazyView('@/views/middleware/Knowledge.vue')
const DataMigration = lazyView('@/views/DataMigration.vue')
const OneClickInspection = lazyView('@/views/inspection/OneClick.vue')
const InspectionReports = lazyView('@/views/inspection/Reports.vue')
const About = lazyView('@/views/About.vue')
const Agent = lazyView('@/views/Agent.vue')
const SystemRoles = lazyView('@/views/system/Roles.vue')
const SystemUsers = lazyView('@/views/system/Users.vue')
const Topology = lazyView('@/views/assets/Topology.vue')
const Performance = lazyView('@/views/monitor/Performance.vue')
const SlowQueries = lazyView('@/views/sql/SlowQueries.vue')
const Diagnosis = lazyView('@/views/ops/Diagnosis.vue')
const Prediction = lazyView('@/views/ops/Prediction.vue')
const MySQLDeployment = lazyView('@/views/deployments/MySQL.vue')

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
    path: '/deployments/mysql',
    component: MySQLDeployment,
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
  },
  {
    path: '/ops/diagnosis',
    component: Diagnosis,
    meta: { requiresAuth: true }
  },
  {
    path: '/ops/prediction',
    component: Prediction,
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
