import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '@/views/Dashboard.vue'
import Databases from '@/views/Databases.vue'
import Backups from '@/views/Backups.vue'
import Schedules from '@/views/Schedules.vue'

const routes = [
  {
    path: '/',
    redirect: '/dashboard'
  },
  {
    path: '/dashboard',
    component: Dashboard
  },
  {
    path: '/databases',
    component: Databases
  },
  {
    path: '/backups',
    component: Backups
  },
  {
    path: '/schedules',
    component: Schedules
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
