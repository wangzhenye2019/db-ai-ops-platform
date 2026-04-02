import api from './index'

export const authAPI = {
  login: (data) => api.post('/auth/login', data),
  me: () => api.get('/auth/me')
}

export const databaseAPI = {
  // Get all databases
  list: () => api.get('/databases'),

  // Create database
  create: (data) => api.post('/databases', data),

  // Get database details
  get: (id) => api.get(`/databases/${id}`),

  // Update database
  update: (id, data) => api.put(`/databases/${id}`, data),

  // Delete database
  delete: (id) => api.delete(`/databases/${id}`),

  // Test connection
  test: (id) => api.post(`/databases/${id}/test`),

  // Get database types
  getTypes: () => api.get('/databases/types')
}

export const backupAPI = {
  // List backups
  list: (params) => api.get('/backups', { params }),

  // Create backup
  create: (data) => api.post('/backups', data),

  // Get backup details
  get: (id) => api.get(`/backups/${id}`),

  // Delete backup
  delete: (id) => api.delete(`/backups/${id}`),

  // Get statistics
  stats: () => api.get('/backups/stats'),

  // Cleanup old backups
  cleanup: () => api.post('/backups/cleanup')
}

export const scheduleAPI = {
  // List schedules
  list: () => api.get('/schedules'),

  // Create schedule
  create: (data) => api.post('/schedules', data),

  // Get schedule details
  get: (id) => api.get(`/schedules/${id}`),

  // Update schedule
  update: (id, data) => api.put(`/schedules/${id}`, data),

  // Delete schedule
  delete: (id) => api.delete(`/schedules/${id}`),

  // Toggle schedule
  toggle: (id) => api.post(`/schedules/${id}/toggle`),

  // Get cron help
  cronHelp: () => api.get('/schedules/cron-help')
}

export const hostAPI = {
  list: () => api.get('/hosts'),
  create: (data) => api.post('/hosts', data),
  get: (id) => api.get(`/hosts/${id}`),
  update: (id, data) => api.put(`/hosts/${id}`, data),
  delete: (id) => api.delete(`/hosts/${id}`),
  getOsTypes: () => api.get('/hosts/os-types')
}

export const middlewareAPI = {
  list: () => api.get('/middlewares'),
  create: (data) => api.post('/middlewares', data),
  get: (id) => api.get(`/middlewares/${id}`),
  update: (id, data) => api.put(`/middlewares/${id}`, data),
  delete: (id) => api.delete(`/middlewares/${id}`),
  getTypes: () => api.get('/middlewares/types')
}

export const kbAPI = {
  listArticles: (params) => api.get('/kb/articles', { params }),
  createArticle: (data) => api.post('/kb/articles', data),
  getArticle: (id) => api.get(`/kb/articles/${id}`),
  updateArticle: (id, data) => api.put(`/kb/articles/${id}`, data),
  deleteArticle: (id) => api.delete(`/kb/articles/${id}`),
  scopes: () => api.get('/kb/scopes')
}

export const opsAPI = {
  listTasks: () => api.get('/ops/tasks'),
  createTask: (data) => api.post('/ops/tasks', data),
  getTask: (id) => api.get(`/ops/tasks/${id}`)
}

export const inspectionAPI = {
  run: (data) => api.post('/inspection/run', data),
  listReports: () => api.get('/inspection/reports'),
  getReport: (id) => api.get(`/inspection/reports/${id}`)
}

export const auditAPI = {
  list: (params) => api.get('/audit/logs', { params })
}

export const assetsAPI = {
  summary: () => api.get('/assets/summary'),
  listAssets: (params) => api.get('/assets', { params }),
  listGroups: () => api.get('/assets/groups'),
  createGroup: (data) => api.post('/assets/groups', data),
  updateGroup: (id, data) => api.put(`/assets/groups/${id}`, data),
  deleteGroup: (id) => api.delete(`/assets/groups/${id}`),
  listGroupMembers: (id) => api.get(`/assets/groups/${id}/members`),
  updateGroupMembers: (id, data) => api.post(`/assets/groups/${id}/members`, data)
}

export const importAPI = {
  downloadTemplate: (resource, format) =>
    api.get(`/import/templates/${resource}`, { params: { format }, responseType: 'blob' }),
  importFile: (resource, file, options = {}) => {
    const dryRun = !!options.dryRun
    const mode = options.mode || 'insert'
    const form = new FormData()
    form.append('file', file)
    return api.post(`/import/${resource}`, form, {
      params: { dry_run: dryRun ? 1 : 0, mode },
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  }
}
