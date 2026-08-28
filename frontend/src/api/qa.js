import http from './http'

/**
 * 多模态问答（结果页追问）。
 * Qwen 真实生成回答可能较慢（专属云首调可超 10s），
 * 故单独放宽超时（覆盖全局 10s），避免前端提前中断导致「无法获取回答」。
 * @param {object} payload { question, herb_name, herb_context }
 * @returns {Promise<object>} { answer, fallback, disclaimer }
 */
export async function askQuestion(payload) {
  const { data } = await http.post('/qa', payload, { timeout: 40000 })
  return data
}
