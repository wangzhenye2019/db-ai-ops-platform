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
  listReports: (params) => api.get('/inspection/reports', { params }),
  getReport: (id) => api.get(`/inspection/reports/${id}`),
  exportReport: (id, format) => {
    const fmt = format || 'json'
    return api.get(`/inspection/reports/${id}/export?format=${fmt}`, { responseType: 'blob' })
  },
  deleteReport: (id) => api.delete(`/inspection/reports/${id}`)
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

export const systemsAPI = {
  list: () => api.get('/systems'),
  create: (data) => api.post('/systems', data),
  update: (id, data) => api.put(`/systems/${id}`, data),
  delete: (id) => api.delete(`/systems/${id}`),
  assets: (id) => api.get(`/systems/${id}/assets`),
  listLinks: (id) => api.get(`/systems/${id}/links`),
  updateLinks: (id, data) => api.post(`/systems/${id}/links`, data),
  listContacts: (id) => api.get(`/systems/${id}/contacts`),
  createContact: (id, data) => api.post(`/systems/${id}/contacts`, data),
  deleteContact: (id, contactId) => api.delete(`/systems/${id}/contacts/${contactId}`)
}

export const dictAPI = {
  listTags: (params) => api.get('/dict/tags', { params }),
  createTag: (data) => api.post('/dict/tags', data),
  deleteTag: (id) => api.delete(`/dict/tags/${id}`),
  listIdcs: (params) => api.get('/dict/idcs', { params }),
  createIdc: (data) => api.post('/dict/idcs', data),
  updateIdc: (id, data) => api.put(`/dict/idcs/${id}`, data),
  deleteIdc: (id) => api.delete(`/dict/idcs/${id}`)
}

export const credsAPI = {
  list: () => api.get('/credentials'),
  types: () => api.get('/credentials/types'),
  create: (data) => api.post('/credentials', data),
  get: (id, params) => api.get(`/credentials/${id}`, { params }),
  update: (id, data) => api.put(`/credentials/${id}`, data),
  delete: (id) => api.delete(`/credentials/${id}`)
}

export const ipAPI = {
  list: (params) => api.get('/ips', { params }),
  create: (data) => api.post('/ips', data),
  update: (id, data) => api.put(`/ips/${id}`, data),
  delete: (id) => api.delete(`/ips/${id}`),
  statuses: () => api.get('/ips/statuses')
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

export const agentAPI = {
  tools: () => api.get('/agent/tools'),
  createSession: (data) => api.post('/agent/sessions', data),
  getSession: (id) => api.get(`/agent/sessions/${id}`),
  listMessages: (id) => api.get(`/agent/sessions/${id}/messages`),
  sendMessage: (id, data) => api.post(`/agent/sessions/${id}/messages`, data)
}

export const rbacAPI = {
  // Permissions
  listPermissions: () => api.get('/permissions'),
  createPermission: (data) => api.post('/permissions', data),
  deletePermission: (id) => api.delete(`/permissions/${id}`),

  // Roles
  listRoles: () => api.get('/roles'),
  createRole: (data) => api.post('/roles', data),
  getRole: (id) => api.get(`/roles/${id}`),
  updateRole: (id, data) => api.put(`/roles/${id}`, data),
  deleteRole: (id) => api.delete(`/roles/${id}`),

  // Users
  listUsers: () => api.get('/users'),
  createUser: (data) => api.post('/users', data),
  getUser: (id) => api.get(`/users/${id}`),
  updateUser: (id, data) => api.put(`/users/${id}`, data),
  deleteUser: (id) => api.delete(`/users/${id}`),

  // Init
  init: () => api.post('/rbac/init')
}

export const topologyAPI = {
  getTopology: (systemId) => {
    const params = systemId ? `?system_id=${systemId}` : ''
    return api.get(`/topology${params}`)
  },
  getNodeDetail: (nodeType, nodeId) => api.get(`/topology/node/${nodeType}/${nodeId}`)
}

export const metricsAPI = {
  getTypes: () => api.get('/metrics/types'),
  getTargets: (type) => {
    const params = type ? `?type=${type}` : ''
    return api.get(`/metrics/targets${params}`)
  },
  getMetrics: (params) => api.get('/metrics', { params }),
  getLatest: (params) => api.get('/metrics/latest', { params }),
  record: (data) => api.post('/metrics', data)
}

export const slowsqlAPI = {
  listQueries: (params) => api.get('/slowsql/queries', { params }),
  getQuery: (id) => api.get(`/slowsql/queries/${id}`),
  recordQuery: (data) => api.post('/slowsql/queries', data),
  analyzeQuery: (id) => api.post(`/slowsql/queries/${id}/analyze`),
  getStats: (params) => api.get('/slowsql/stats', { params }),
  deleteQuery: (id) => api.delete(`/slowsql/queries/${id}`)
}
