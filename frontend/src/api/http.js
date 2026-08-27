import axios from 'axios'

/**
 * axios 实例：baseURL 指向 /api，由 Vite 代理转发到后端。
 */
const http = axios.create({
  baseURL: '/api',
  timeout: 10000,
})

// 请求拦截：注入 Authorization Bearer token（登录态）
http.interceptors.request.use((config) => {
  const token = localStorage.getItem('herb_token')
  if (token) {
    config.headers = config.headers || {}
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截：统一错误提示（骨架阶段仅记录，不打断调用方）
http.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('[api] request failed:', error?.message)
    return Promise.reject(error)
  }
)

export default http
