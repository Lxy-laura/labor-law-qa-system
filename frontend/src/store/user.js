/**
 * Pinia 用户状态管理
 * 管理 token、role、username，提供 login / logout / fetchUserInfo 方法
 */
import { defineStore } from 'pinia'
import { login as loginApi, register as registerApi, getUserInfo } from '../api/auth'

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
      this.token = res.access_token
      this.role = res.role
      this.username = res.username
      this._persist()
      // 登录后立即从服务端同步角色，确保 role 正确
      await this.fetchUserInfo()
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
     * 从服务端获取用户信息，同步角色状态
     * 用于应用启动时校正 localStorage 中可能残留的旧角色
     */
    async fetchUserInfo() {
      if (!this.token) return
      try {
        const info = await getUserInfo()
        if (info.role) {
          this.role = info.role
          this.username = info.username
          this._persist()
        }
      } catch (e) {
        // Token 无效或过期，清除本地状态
        if (e.response && e.response.status === 401) {
          this.logout()
        }
      }
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