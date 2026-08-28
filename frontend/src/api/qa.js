import http from './http'

/**
 * 多模态问答（结果页追问）。
 * @param {object} payload { question, herb_name, herb_context }
 * @returns {Promise<object>} { answer, fallback, disclaimer }
 */
export async function askQuestion(payload) {
  const { data } = await http.post('/qa', payload)
  return data
}
