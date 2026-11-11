import { defineStore } from 'pinia'

export interface TabItem {
  key: string
  title: string
  path: string
}

/**
 * 模块内多页签：工作台与管理页互不干扰，配合 keep-alive 缓存。
 */
export const useTabsStore = defineStore('custom-text-tabs', {
  state: () => ({
    tabs: [] as TabItem[],
    activeKey: '',
  }),
  actions: {
    open(tab: TabItem) {
      if (!this.tabs.some((t) => t.key === tab.key)) this.tabs.push(tab)
      this.activeKey = tab.key
    },
    close(key: string, fallback?: TabItem) {
      const idx = this.tabs.findIndex((t) => t.key === key)
      this.tabs = this.tabs.filter((t) => t.key !== key)
      if (this.activeKey === key) {
        const next = this.tabs[idx - 1] || this.tabs[idx] || fallback
        this.activeKey = next ? next.key : ''
        return next ? next.path : '/custom-text/wb/metadata'
      }
      return null
    },
  },
})
