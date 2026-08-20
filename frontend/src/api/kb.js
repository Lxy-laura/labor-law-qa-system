/**
 * 知识库管理 API
 * 文档的增删查改
 */
import request from './index'

/**
 * 获取文档列表
 * @param {Object} params - { page, pageSize, keyword, type }
 * @returns {Promise} - { list, total, page, pageSize }
 */
export function getDocuments(params) {
  return request({
    url: '/kb/documents',
    method: 'get',
    params
  })
}

/**
 * 上传文档到知识库
 * @param {File} file
 * @param {Object} metadata - { title, category, description }
 * @param {Function} onUploadProgress
 * @returns {Promise}
 */
export function uploadDocument(file, metadata, onUploadProgress) {
  const formData = new FormData()
  formData.append('file', file)
  if (metadata) {
    Object.keys(metadata).forEach((key) => {
      formData.append(key, metadata[key])
    })
  }
  return request({
    url: '/kb/documents',
    method: 'post',
    data: formData,
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress
  })
}

/**
 * 删除知识库文档
 * @param {string} documentId
 * @returns {Promise}
 */
export function deleteDocument(documentId) {
  return request({
    url: `/kb/documents/${documentId}`,
    method: 'delete'
  })
}

/**
 * 获取知识库统计信息
 * @returns {Promise} - { totalDocuments, totalSize, byCategory }
 */
export function getKbStats() {
  return request({
    url: '/kb/stats',
    method: 'get'
  })
}

/**
 * 重建向量索引
 * @param {string} documentId
 * @returns {Promise}
 */
export function rebuildIndex(documentId) {
  return request({
    url: `/kb/documents/${documentId}/reindex`,
    method: 'post'
  })
}
