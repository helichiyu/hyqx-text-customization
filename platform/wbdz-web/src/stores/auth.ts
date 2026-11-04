import { defineStore } from 'pinia'
import { login as apiLogin, me } from '@/api'

/** 登录态（单角色，JWT 本地保存） */
export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('wbdz_token') || '',
    nickname: '',
    username: '',
  }),
  getters: {
    logged: (s) => !!s.token,
  },
  actions: {
    async login(username: string, password: string) {
      const { token } = await apiLogin(username, password)
      this.token = token
      localStorage.setItem('wbdz_token', token)
      await this.fetchMe()
    },
    async fetchMe() {
      const user = await me()
      this.nickname = user.nickname
      this.username = user.username
    },
    logout() {
      this.token = ''
      this.nickname = ''
      localStorage.removeItem('wbdz_token')
    },
  },
})
