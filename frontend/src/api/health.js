import http from './http'

/**
 * 健康检查：探测后端连通状态。
 * @returns {Promise<boolean>} 后端是否可用
 */
export async function checkHealth() {
  try {
    const { data } = await http.get('/health')
    return data?.status === 'ok'
  } catch {
    return false
  }
}
