import axios from 'axios'
import { clearToken, getToken } from '@/utils/auth'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000
})

// Request interceptor
api.interceptors.request.use(
  config => {
    const token = getToken()
    if (token) {
      config.headers = config.headers || {}
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// Response interceptor
api.interceptors.response.use(
  response => response.data,
  async error => {
    const status = error.response?.status
    if (status === 401) {
      clearToken()
      try {
        const router = (await import('@/router')).default
        router.replace('/login')
      } catch {
      }
    }
    const message = error.response?.data?.error || error.message || '请求失败'
    console.error('API Error:', message)
    return Promise.reject(new Error(message))
  }
)

export default api
