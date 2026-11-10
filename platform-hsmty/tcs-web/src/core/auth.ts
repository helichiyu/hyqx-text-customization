import { defineStore } from 'pinia'
import { ref } from 'vue'

/**
 * 当前登录用户快照，由主应用通过 qiankun props 下发。
 */
export interface CurrentUser {
  id: string
  name: string
  permissions: string[]
}

/**
 * 登录态由 UAP/SSO Cookie 承载：子应用不保存 Token、不解析 Cookie，
 * 只消费主应用下发的用户与权限，接口鉴权以后端 @PreAuthorize 为最终边界。
 */
export const useAuthStore = defineStore('auth', () => {
  const currentUser = ref<CurrentUser | null>(null)

  function applyUser(user?: CurrentUser) {
    currentUser.value = user ?? null
  }

  function hasPermission(code: string): boolean {
    return currentUser.value?.permissions.includes(code) ?? false
  }

  return { currentUser, applyUser, hasPermission }
})
