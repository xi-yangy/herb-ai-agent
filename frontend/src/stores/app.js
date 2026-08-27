import { defineStore } from 'pinia'

/**
 * 全局应用状态（骨架阶段仅占位）。
 * 后续 P0 阶段可扩展：识别状态、用户登录态、授权状态等。
 */
export const useAppStore = defineStore('app', {
  state: () => ({
    backendOnline: false,
  }),
  actions: {
    setBackendOnline(online) {
      this.backendOnline = online
    },
  },
})
