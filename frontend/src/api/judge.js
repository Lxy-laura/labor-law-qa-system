/**
 * 信息研判 API
 * 合同条款风险分析
 */
import request from './index'

/**
 * 分析合同文本
 * @param {Object} data - { text, fileName }
 * @returns {Promise} - { summary, clauses, conclusion }
 */
export function analyzeContract(data) {
  return request({
    url: '/judge/analyze',
    method: 'post',
    data
  })
}

/**
 * 上传合同文件并分析
 * @param {File} file
 * @param {Function} onUploadProgress - 上传进度回调
 * @returns {Promise}
 */
export function uploadAndAnalyze(file, onUploadProgress) {
  const formData = new FormData()
  formData.append('file', file)
  return request({
    url: '/judge/upload',
    method: 'post',
    data: formData,
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress
  })
}

/**
 * 获取研判历史记录
 * @returns {Promise}
 */
export function getJudgeHistory() {
  return request({
    url: '/judge/history',
    method: 'get'
  })
}
