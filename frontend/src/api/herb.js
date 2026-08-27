import http from './http'

/** 生成或读取稳定的设备标识（匿名用户维度，收藏/历史使用）。 */
export function getDeviceId() {
  const KEY = 'herb_device_id'
  let id = localStorage.getItem(KEY)
  if (!id) {
    // 简易随机 ID：时间戳 + 随机数，保证同设备稳定
    id = `dev-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`
    localStorage.setItem(KEY, id)
  }
  return id
}

/** 附带设备标识的请求头。 */
function deviceHeader() {
  return { 'X-Device-Id': getDeviceId() }
}

/**
 * 图片识别。
 * @param {string} imageBase64 图片 base64（可含 data:image 前缀）
 * @param {string} channel 触发通道：camera / album
 * @returns {Promise<object>} 识别结果（含 name/safety_level/herb）
 */
export async function recognize(imageBase64, channel) {
  const { data } = await http.post('/recognize', { image_base64: imageBase64, channel })
  return data
}

/** 查询药材列表。 */
export async function listHerbs() {
  const { data } = await http.get('/herbs')
  return data
}

/** 查询药材详情。 */
export async function getHerb(herbId) {
  const { data } = await http.get(`/herbs/${herbId}`)
  return data
}

/** 查询识别历史。 */
export async function listHistory() {
  const { data } = await http.get('/history', { headers: deviceHeader() })
  return data
}

/** 新增识别历史（识别成功后由前端写入）。 */
export async function createHistory(payload) {
  const { data } = await http.post('/history', payload, { headers: deviceHeader() })
  return data
}

/** 清空识别历史。 */
export async function clearHistory() {
  const { data } = await http.delete('/history', { headers: deviceHeader() })
  return data
}

/** 查询收藏列表。 */
export async function listFavorites() {
  const { data } = await http.get('/favorites', { headers: deviceHeader() })
  return data
}

/** 新增收藏。 */
export async function addFavorite(herbId) {
  const { data } = await http.post('/favorites', { herb_id: herbId }, { headers: deviceHeader() })
  return data
}

/** 取消收藏。 */
export async function removeFavorite(herbId) {
  const { data } = await http.delete(`/favorites/${herbId}`, { headers: deviceHeader() })
  return data
}
