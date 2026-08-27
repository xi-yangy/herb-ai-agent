import http from './http'
import { getDeviceId } from './herb'

/** 附带设备标识的请求头。 */
function deviceHeader() {
  return { 'X-Device-Id': getDeviceId() }
}

/** 查询当前设备的隐私授权状态列表。 */
export async function listConsents() {
  const { data } = await http.get('/privacy/consents', { headers: deviceHeader() })
  return data
}

/** 更新某一项授权状态（camera/album/microphone）。 */
export async function updateConsent(consentType, granted) {
  const { data } = await http.put(
    '/privacy/consents',
    { consent_type: consentType, granted },
    { headers: deviceHeader() }
  )
  return data
}
