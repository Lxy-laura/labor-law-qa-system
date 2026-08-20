<template>
  <!-- 知识库管理页面：统计卡片 + 文档表格，管理员专用 -->
  <div class="h-full p-4 overflow-y-auto custom-scrollbar">
    <!-- 页面标题 -->
    <div class="flex items-center justify-between mb-4">
      <div>
        <h2 class="page-title">知识库管理</h2>
        <p class="text-sm text-gray-400 mt-1">管理劳动合同法律法规知识库文档</p>
      </div>
      <el-button type="primary" :icon="Upload" @click="uploadDialogVisible = true">
        上传文档
      </el-button>
    </div>

    <!-- 统计卡片 -->
    <div class="grid grid-cols-4 gap-4 mb-5">
      <div
        v-for="stat in stats"
        :key="stat.label"
        class="card-container p-5 flex items-center gap-4"
      >
        <div
          class="w-12 h-12 rounded-xl flex items-center justify-center shrink-0"
          :class="stat.bgClass"
        >
          <el-icon :size="24" :color="stat.color">
            <component :is="stat.icon" />
          </el-icon>
        </div>
        <div>
          <div class="text-2xl font-bold text-gray-800">{{ stat.value }}</div>
          <div class="text-xs text-gray-400 mt-0.5">{{ stat.label }}</div>
        </div>
      </div>
    </div>

    <!-- 搜索筛选栏 -->
    <div class="card-container p-4 mb-4">
      <div class="flex items-center gap-3 flex-wrap">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索文档标题..."
          class="!w-64"
          clearable
          :prefix-icon="Search"
          @keyup.enter="loadDocuments"
          @clear="loadDocuments"
        />
        <el-select v-model="filterType" placeholder="文档类型" class="!w-40" clearable @change="loadDocuments">
          <el-option label="法律法规" value="law" />
          <el-option label="部门规章" value="regulation" />
          <el-option label="司法解释" value="judicial" />
          <el-option label="案例库" value="case" />
          <el-option label="办事指南" value="guide" />
        </el-select>
        <el-button type="primary" @click="loadDocuments">查询</el-button>
        <div class="flex-1"></div>
        <el-button :icon="Refresh" @click="refreshAll">刷新</el-button>
      </div>
    </div>

    <!-- 文档表格 -->
    <div class="card-container overflow-hidden">
      <el-table
        :data="documents"
        v-loading="tableLoading"
        stripe
        style="width: 100%"
      >
        <el-table-column label="文档名称" min-width="220">
          <template #default="{ row }">
            <div class="flex items-center gap-2">
              <el-icon class="text-primary"><Document /></el-icon>
              <span class="text-sm text-gray-700">{{ row.title }}</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="类型" width="120">
          <template #default="{ row }">
            <el-tag size="small" :type="typeTagType(row.type)" effect="plain">
              {{ typeLabel(row.type) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="大小" width="100">
          <template #default="{ row }">
            <span class="text-sm text-gray-500">{{ formatFileSize(row.size) }}</span>
          </template>
        </el-table-column>

        <el-table-column label="向量数" width="100" align="center">
          <template #default="{ row }">
            <span class="text-sm text-gray-500">{{ row.chunkCount || '-' }}</span>
          </template>
        </el-table-column>

        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.indexed ? 'success' : 'info'" size="small" effect="plain">
              {{ row.indexed ? '已索引' : '待索引' }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="上传时间" width="170">
          <template #default="{ row }">
            <span class="text-sm text-gray-400">{{ row.uploadTime || row.createdAt }}</span>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" size="small" :icon="View" @click="previewDoc(row)">
              预览
            </el-button>
            <el-button
              text
              type="warning"
              size="small"
              :icon="RefreshRight"
              :loading="row._reindexing"
              @click="reindexDoc(row)"
            >
              重建索引
            </el-button>
            <el-button text type="danger" size="small" :icon="Delete" @click="removeDoc(row)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="flex justify-end p-4 border-t border-gray-50">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :total="pagination.total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="loadDocuments"
          @current-change="loadDocuments"
        />
      </div>
    </div>

    <!-- 上传弹窗 -->
    <el-dialog v-model="uploadDialogVisible" title="上传知识库文档" width="540px">
      <el-form :model="uploadForm" label-width="80px">
        <el-form-item label="文档文件" required>
          <div
            class="flex items-center justify-center border-2 border-dashed border-gray-300 rounded-lg py-8 cursor-pointer hover:border-primary-400 hover:bg-primary-50 transition-colors w-full"
            @click="triggerUpload"
          >
            <div class="text-center">
              <el-icon :size="32" class="text-gray-300 mb-2"><UploadFilled /></el-icon>
              <p class="text-sm text-gray-500">{{ uploadFile ? uploadFile.name : '点击选择文件' }}</p>
              <p class="text-xs text-gray-400 mt-1">支持 .txt / .docx / .pdf / .md，最大 10MB</p>
            </div>
          </div>
          <input ref="uploadInputRef" type="file" class="hidden" accept=".txt,.docx,.pdf,.md" @change="handleUploadChange" />
        </el-form-item>
        <el-form-item label="文档标题">
          <el-input v-model="uploadForm.title" placeholder="请输入文档标题" />
        </el-form-item>
        <el-form-item label="文档类型">
          <el-select v-model="uploadForm.category" placeholder="请选择类型" class="w-full">
            <el-option label="法律法规" value="law" />
            <el-option label="部门规章" value="regulation" />
            <el-option label="司法解释" value="judicial" />
            <el-option label="案例库" value="case" />
            <el-option label="办事指南" value="guide" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="uploadForm.description" type="textarea" :rows="3" placeholder="文档简要描述（选填）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="uploadDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="uploading" @click="confirmUpload">确认上传</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
/**
 * 知识库管理页面（管理员专用）
 * 统计卡片 + 文档表格 + 上传/删除/重建索引
 */
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Upload,
  Search,
  Refresh,
  Document,
  View,
  RefreshRight,
  Delete,
  UploadFilled,
  Files,
  Folder,
  DataLine
} from '@element-plus/icons-vue'
import { getDocuments, uploadDocument, deleteDocument, getKbStats, rebuildIndex } from '../api/kb'

const tableLoading = ref(false)
const searchKeyword = ref('')
const filterType = ref('')
const documents = ref([])
const uploadDialogVisible = ref(false)
const uploading = ref(false)
const uploadFile = ref(null)
const uploadInputRef = ref(null)

const uploadForm = reactive({
  title: '',
  category: '',
  description: ''
})

const pagination = reactive({
  page: 1,
  pageSize: 10,
  total: 0
})

// 统计数据
const stats = ref([
  { label: '文档总数', value: 0, icon: Files, bgClass: 'bg-primary-50', color: '#4F46E5' },
  { label: '已索引', value: 0, icon: DataLine, bgClass: 'bg-green-50', color: '#10B981' },
  { label: '待索引', value: 0, icon: Folder, bgClass: 'bg-amber-50', color: '#F59E0B' },
  { label: '总向量数', value: 0, icon: DataLine, bgClass: 'bg-secondary-50', color: '#06B6D4' }
])

onMounted(() => {
  loadDocuments()
  loadStats()
})

// 加载文档列表
async function loadDocuments() {
  tableLoading.value = true
  try {
    const res = await getDocuments({
      page: pagination.page,
      pageSize: pagination.pageSize,
      keyword: searchKeyword.value,
      type: filterType.value
    })
    documents.value = res.list || []
    pagination.total = res.total || 0
  } catch (e) {
    documents.value = []
  } finally {
    tableLoading.value = false
  }
}

// 加载统计
async function loadStats() {
  try {
    const res = await getKbStats()
    stats.value[0].value = res.totalDocuments || 0
    stats.value[1].value = res.indexed || 0
    stats.value[2].value = res.pending || 0
    stats.value[3].value = res.totalChunks || 0
  } catch (e) {
    // 静默处理
  }
}

// 刷新全部
function refreshAll() {
  loadDocuments()
  loadStats()
}

// 类型标签
function typeLabel(type) {
  const map = { law: '法律法规', regulation: '部门规章', judicial: '司法解释', case: '案例库', guide: '办事指南' }
  return map[type] || '其他'
}
function typeTagType(type) {
  const map = { law: 'danger', regulation: 'warning', judicial: 'success', case: 'info', guide: 'primary' }
  return map[type] || 'info'
}

// 格式化文件大小
function formatFileSize(size) {
  if (!size) return '-'
  if (size < 1024) return size + 'B'
  if (size < 1024 * 1024) return (size / 1024).toFixed(1) + 'KB'
  return (size / (1024 * 1024)).toFixed(1) + 'MB'
}

// 预览文档
function previewDoc(row) {
  ElMessage.info(`预览文档：${row.title}`)
}

// 重建索引
async function reindexDoc(row) {
  row._reindexing = true
  try {
    await rebuildIndex(row.id)
    ElMessage.success('索引重建完成')
    loadDocuments()
    loadStats()
  } catch (e) {
    // 错误已处理
  } finally {
    row._reindexing = false
  }
}

// 删除文档
async function removeDoc(row) {
  try {
    await ElMessageBox.confirm(`确定删除文档「${row.title}」？删除后不可恢复。`, '删除确认', {
      type: 'warning',
      confirmButtonText: '确定删除',
      cancelButtonText: '取消'
    })
    await deleteDocument(row.id)
    ElMessage.success('删除成功')
    loadDocuments()
    loadStats()
  } catch (e) {
    // 取消删除
  }
}

// 触发上传文件选择
function triggerUpload() {
  uploadInputRef.value?.click()
}

// 处理上传文件变化
function handleUploadChange(e) {
  const file = e.target.files[0]
  if (file) {
    if (file.size > 10 * 1024 * 1024) {
      ElMessage.error('文件大小不能超过 10MB')
      return
    }
    uploadFile.value = file
    if (!uploadForm.title) {
      uploadForm.title = file.name.replace(/\.[^/.]+$/, '')
    }
  }
}

// 确认上传
async function confirmUpload() {
  if (!uploadFile.value) {
    ElMessage.warning('请选择要上传的文件')
    return
  }
  uploading.value = true
  try {
    await uploadDocument(uploadFile.value, {
      title: uploadForm.title,
      category: uploadForm.category,
      description: uploadForm.description
    })
    ElMessage.success('上传成功')
    uploadDialogVisible.value = false
    resetUploadForm()
    loadDocuments()
    loadStats()
  } catch (e) {
    // 错误已处理
  } finally {
    uploading.value = false
  }
}

// 重置上传表单
function resetUploadForm() {
  uploadFile.value = null
  uploadForm.title = ''
  uploadForm.category = ''
  uploadForm.description = ''
  if (uploadInputRef.value) uploadInputRef.value.value = ''
}
</script>

<style scoped>
</style>
