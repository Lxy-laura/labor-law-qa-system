/**
 * 数据分析 API
 */
import request from './index'

/**
 * 获取分析概览数据
 * @returns {Promise} - { totalQuestions, totalUsers, totalDocuments, ... }
 */
export function getAnalytics() {
  return request({
    url: '/analytics/overview',
    method: 'get'
  })
}

/**
 * 获取问答趋势数据
 * @param {Object} params - { startDate, endDate, granularity }
 * @returns {Promise}
 */
export function getQaTrend(params) {
  return request({
    url: '/analytics/qa-trend',
    method: 'get',
    params
  })
}

/**
 * 获取热门问题分类
 * @returns {Promise}
 */
export function getHotCategories() {
  return request({
    url: '/analytics/hot-categories',
    method: 'get'
  })
}

/**
 * 获取用户活跃度数据
 * @returns {Promise}
 */
export function getUserActivity(params) {
  return request({
    url: '/analytics/user-activity',
    method: 'get',
    params
  })
}

/**
 * 获取检索质量指标
 * @returns {Promise}
 */
export function getRetrievalMetrics() {
  return request({
    url: '/analytics/retrieval-metrics',
    method: 'get'
  })
}
