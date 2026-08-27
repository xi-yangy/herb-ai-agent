import http from './http'
import { getDeviceId } from './herb'

/** 附带设备标识的请求头。 */
function deviceHeader() {
  return { 'X-Device-Id': getDeviceId() }
}

/** 注册新用户，返回 { token, user }。 */
export async function register(username, password) {
  const { data } = await http.post('/auth/register', { username, password })
  return data
}

/** 登录，返回 { token, user }。 */
export async function login(username, password) {
  const { data } = await http.post('/auth/login', { username, password })
  return data
}

/** 获取当前登录用户（需 Bearer token）。 */
export async function getMe() {
  const { data } = await http.get('/auth/me')
  return data
}

/** 将当前设备的匿名历史合并到登录用户。 */
export async function migrateHistory() {
  const { data } = await http.post('/history/migrate', {}, { headers: deviceHeader() })
  return data
}

/** 将当前设备的匿名收藏合并到登录用户。 */
export async function migrateFavorites() {
  const { data } = await http.post('/favorites/migrate', {}, { headers: deviceHeader() })
  return data
}
