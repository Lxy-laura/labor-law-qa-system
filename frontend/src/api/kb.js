/**
 * 知识库管理 API
 * 文档的增删查改
 */
import request from './index'

/**
 * 获取文档列表
 * @param {Object} params - { page, pageSize, keyword, doc_type }
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
 * @param {Object} metadata - { title, doc_type, description }
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
    url: '/kb/upload',
    method: 'post',
    data: formData,
    // 不要手动设置 Content-Type，让浏览器自动添加 boundary 参数
    // 手动设置会导致 boundary 丢失，服务器无法解析 FormData
    headers: { 'Content-Type': undefined },
    // OCR 处理扫描件 PDF 较慢，设为 5 分钟超时
    timeout: 300000,
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
 * 获取文档详情（含全文内容，用于预览）
 * @param {number} documentId
 * @returns {Promise} - { id, title, content, doc_type, file_size, chunk_count, indexed, created_at }
 */
export function getDocumentDetail(documentId) {
  return request({
    url: `/kb/documents/${documentId}`,
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
