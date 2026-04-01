import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '@/views/Dashboard.vue'
import Databases from '@/views/Databases.vue'
import Backups from '@/views/Backups.vue'
import Schedules from '@/views/Schedules.vue'
import Login from '@/views/Login.vue'
import { getToken } from '@/utils/auth'

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
