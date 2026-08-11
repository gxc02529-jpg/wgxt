// 认证状态：JWT 与用户信息持久化到 localStorage
import { defineStore } from 'pinia'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('wgf_token') || '',
    user: JSON.parse(localStorage.getItem('wgf_user') || 'null'),
  }),

  getters: {
    isLoggedIn: (s) => Boolean(s.token),
    isAdmin: (s) => s.user?.role === 'admin',
    isEditor: (s) => s.user?.role === 'editor' || s.user?.role === 'admin',
  },

  actions: {
    setSession(token, user) {
      this.token = token
      this.user = user
      localStorage.setItem('wgf_token', token)
      localStorage.setItem('wgf_user', JSON.stringify(user))
    },
    setUser(user) {
      this.user = user
      localStorage.setItem('wgf_user', JSON.stringify(user))
    },
    logout() {
      this.token = ''
      this.user = null
      localStorage.removeItem('wgf_token')
      localStorage.removeItem('wgf_user')
    },
  },
})

