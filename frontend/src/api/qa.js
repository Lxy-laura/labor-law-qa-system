/**
 * 智能问答 API
 */
import request from './index'

/**
 * 提交问题获取 AI 回答
 * @param {Object} data - { question, conversationId }
 * @returns {Promise} - { answer, sources, similarCases, services }
 */
export function askQuestion(data) {
  return request({
    url: '/qa/ask',
    method: 'post',
    data
  })
}

/**
 * 获取对话历史列表
 * @returns {Promise}
 */
export function getConversations() {
  return request({
    url: '/qa/conversations',
    method: 'get'
  })
}

/**
 * 获取某个对话的详细消息记录
 * @param {string} conversationId
 * @returns {Promise}
 */
export function getConversationMessages(conversationId) {
  return request({
    url: `/qa/conversations/${conversationId}`,
    method: 'get'
  })
}

/**
 * 删除对话历史
 * @param {string} conversationId
 * @returns {Promise}
 */
export function deleteConversation(conversationId) {
  return request({
    url: `/qa/conversations/${conversationId}`,
    method: 'delete'
  })
}

/**
 * 新建对话
 * @returns {Promise} - { conversationId }
 */
export function createConversation() {
  return request({
    url: '/qa/conversations',
    method: 'post'
  })
}
