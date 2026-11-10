import { defineStore } from 'pinia'

/**
 * 全局轻量状态：只承载跨页面共享的模块标识，不缓存业务数据。
 */
export const useAppStore = defineStore('app', {
  state: () => ({
    activeModule: 'custom-text',
  }),
  actions: {
    setActiveModule(key: string) {
      this.activeModule = key
    },
  },
})
