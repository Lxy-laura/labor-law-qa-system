/**
 * Pinia 用户状态管理
 * 管理 token、role、username，提供 login / logout 方法
 */
import { defineStore } from 'pinia'
import { login as loginApi, register as registerApi } from '../api/auth'

export const useUserStore = defineStore('user', {
  state: () => ({
    token: localStorage.getItem('token') || '',
    role: localStorage.getItem('role') || '',
    username: localStorage.getItem('username') || ''
  }),

  getters: {
    // 是否已登录
    isLoggedIn: (state) => !!state.token,
    // 是否为管理员
    isAdmin: (state) => state.role === 'admin'
  },

  actions: {
    /**
     * 登录
     * @param {string} username 用户名
     * @param {string} password 密码
     */
    async login(username, password) {
      const res = await loginApi({ username, password })
      this.token = res.token
      this.token = res.access_token
      this.username = res.username
      this._persist()
      return res
    },

    /**
     * 注册
     */
    async register(username, password) {
      const res = await registerApi({ username, password })
      return res
    },

    /**
     * 退出登录
     */
    logout() {
      this.token = ''
      this.role = ''
      this.username = ''
      localStorage.removeItem('token')
      localStorage.removeItem('role')
      localStorage.removeItem('username')
    },

    /**
     * 从 localStorage 恢复状态
     */
    restoreFromStorage() {
      this.token = localStorage.getItem('token') || ''
      this.role = localStorage.getItem('role') || ''
      this.username = localStorage.getItem('username') || ''
    },

    /**
     * 持久化到 localStorage
     */
    _persist() {
      if (this.token) localStorage.setItem('token', this.token)
      if (this.role) localStorage.setItem('role', this.role)
      if (this.username) localStorage.setItem('username', this.username)
    }
  }
})
