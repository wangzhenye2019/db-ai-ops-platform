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
