import { defineStore } from 'pinia'

/**
 * 全局应用状态。
 * 后端连通性 + 当前识别结果（Result 页展示与写历史使用）+ 用户登录态。
 */
export const useAppStore = defineStore('app', {
  state: () => ({
    backendOnline: false,
    // 最近一次后端连通性检测时间（顶栏状态时间戳展示，格式如 "14:32:05"）
    lastCheckTime: '',
    // 最近一次识别结果：{ imageBase64, result }，由首页识别后写入
    lastRecognition: null,
    // 当前登录用户：{ id, username }，从 localStorage 恢复
    user: JSON.parse(localStorage.getItem('herb_user') || 'null'),
  }),
  getters: {
    isLoggedIn: (state) => state.user !== null,
  },
  actions: {
    setBackendOnline(online) {
      this.backendOnline = online
      this.lastCheckTime = new Date().toLocaleTimeString('zh-CN', { hour12: false })
    },
    setLastRecognition(imageBase64, result) {
      this.lastRecognition = { imageBase64, result }
    },
    clearRecognition() {
      this.lastRecognition = null
    },
    /** 设置登录态（token 存入 localStorage）。 */
    setUser(user) {
      this.user = user
      localStorage.setItem('herb_user', JSON.stringify(user))
    },
    /** 退出登录：清空用户态与 token。 */
    logout() {
      this.user = null
      localStorage.removeItem('herb_user')
      localStorage.removeItem('herb_token')
    },
  },
})
