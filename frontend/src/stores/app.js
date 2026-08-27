import { defineStore } from 'pinia'

/**
 * 全局应用状态。
 * 后端连通性 + 当前识别结果（Result 页展示与写历史使用）。
 */
export const useAppStore = defineStore('app', {
  state: () => ({
    backendOnline: false,
    // 最近一次识别结果：{ imageBase64, result }，由首页识别后写入
    lastRecognition: null,
  }),
  actions: {
    setBackendOnline(online) {
      this.backendOnline = online
    },
    setLastRecognition(imageBase64, result) {
      this.lastRecognition = { imageBase64, result }
    },
    clearRecognition() {
      this.lastRecognition = null
    },
  },
})
