/**
 * 认证相关 API
 * 登录 / 注册
 */
import request from './index'

/**
 * 用户登录
 * @param {Object} data - { username, password }
 * @returns {Promise} - { token, role, username }
 */
export function login(data) {
  return request({
    url: '/auth/login',
    method: 'post',
    data
  })
}

/**
 * 用户注册
 * @param {Object} data - { username, password }
 * @returns {Promise}
 */
export function register(data) {
  return request({
    url: '/auth/register',
    method: 'post',
    data
  })
}

/**
 * 获取当前用户信息
 * @returns {Promise}
 */
export function getUserInfo() {
  return request({
    url: '/auth/info',
    method: 'get'
  })
}
