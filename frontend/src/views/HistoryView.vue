<template>
  <!-- 提问历史页面：左侧列表 + 右侧气泡式对话展示 -->
  <div class="h-full flex">
    <!-- ===== 左侧：历史记录列表 ===== -->
    <div class="w-[420px] shrink-0 bg-white border-r border-gray-200 flex flex-col">
      <!-- 搜索栏 -->
      <div class="p-4 border-b border-gray-100">
        <el-input
          v-model="searchText"
          placeholder="搜索历史提问..."
          :prefix-icon="Search"
          clearable
          class="w-full"
        />
      </div>

      <!-- 统计信息 -->
      <div class="px-4 py-2 border-b border-gray-50 flex items-center gap-4 text-xs text-gray-400">
        <span>共 {{ filteredList.length }} 条记录</span>
        <el-select v-model="filterCategory" placeholder="全部分类" size="small" class="!w-32">
          <el-option label="全部分类" value="" />
          <el-option label="工资报酬" value="工资" />
          <el-option label="解除终止" value="解除" />
          <el-option label="社保公积金" value="社保" />
          <el-option label="工时休假" value="工时" />
          <el-option label="调岗调薪" value="调岗" />
        </el-select>
      </div>

      <!-- 历史列表 -->
      <div class="flex-1 overflow-y-auto custom-scrollbar">
        <div
          v-for="item in filteredList"
          :key="item.id"
          class="px-4 py-3 border-b border-gray-50 cursor-pointer transition-colors hover:bg-gray-50"
          :class="selectedId === item.id ? 'bg-primary-50 border-l-4 border-l-primary' : ''"
          @click="selectHistory(item)"
        >
          <div class="flex items-start justify-between gap-2 mb-1">
            <p class="text-sm font-medium text-gray-800 line-clamp-2 flex-1">{{ item.question }}</p>
            <el-tag size="small" effect="plain" class="shrink-0">
              {{ item.confidence ? (item.confidence * 100).toFixed(0) + '%' : '-' }}
            </el-tag>
          </div>
          <p class="text-xs text-gray-400 line-clamp-2 mb-1">{{ item.answer }}</p>
          <div class="flex items-center justify-between text-xs text-gray-400">
            <span>{{ formatTime(item.created_at) }}</span>
            <div class="flex items-center gap-1">
              <!-- 标记是否为旧回答（未配置API Key时生成的） -->
              <el-tag v-if="isOldAnswer(item.answer)" size="small" type="warning" effect="plain">旧回答</el-tag>
              <el-icon
                class="cursor-pointer hover:text-yellow-500 transition-colors"
                :class="item.is_favorited ? 'text-yellow-500' : 'text-gray-300'"
                @click.stop="toggleFavorite(item)"
              >
                <Star />
              </el-icon>
            </div>
          </div>
        </div>
        <div v-if="filteredList.length === 0" class="flex flex-col items-center justify-center h-64 text-gray-400">
          <el-icon :size="40"><Clock /></el-icon>
          <p class="text-sm mt-2">暂无提问历史</p>
        </div>
      </div>
    </div>

    <!-- ===== 右侧：气泡式对话展示（与智能问答页面风格一致） ===== -->
    <div class="flex-1 flex flex-col bg-gray-50 min-w-0">
      <!-- 顶部操作栏 -->
      <div v-if="selectedItem" class="flex items-center justify-between px-6 py-3 bg-white border-b border-gray-100">
        <div class="flex items-center gap-2 text-sm text-gray-400">
          <el-icon><Clock /></el-icon>
          <span>{{ formatTime(selectedItem.created_at) }}</span>
          <el-tag v-if="selectedItem.confidence" size="small" type="success" effect="plain">
            置信度 {{ (selectedItem.confidence * 100).toFixed(0) }}%
          </el-tag>
          <el-tag v-if="isOldAnswer(selectedItem.answer)" size="small" type="warning" effect="plain">
            旧回答（法条匹配）
          </el-tag>
        </div>
        <div class="flex items-center gap-2">
          <!-- 重新生成按钮：仅对旧回答显示 -->
          <el-button
            v-if="isOldAnswer(selectedItem.answer)"
            size="small"
            type="primary"
            :icon="Refresh"
            :loading="regenerating"
            @click="regenerateAnswer(selectedItem)"
          >
            重新生成 AI 回答
          </el-button>
          <el-button
            size="small"
            :icon="selectedItem.is_favorited ? StarFilled : Star"
            :type="selectedItem.is_favorited ? 'warning' : 'default'"
            @click="toggleFavorite(selectedItem)"
          >
            {{ selectedItem.is_favorited ? '已收藏' : '收藏' }}
          </el-button>
          <el-button size="small" :icon="ChatLineRound" @click="goToQA(selectedItem.question)">
            继续提问
          </el-button>
          <el-button size="small" :icon="Delete" type="danger" plain @click="deleteHistory(selectedItem)">
            删除
          </el-button>
        </div>
      </div>

      <!-- 消息气泡区域 -->
      <div class="flex-1 overflow-y-auto custom-scrollbar px-6 py-4">
        <div v-if="selectedItem" class="max-w-4xl mx-auto">
          <!-- 用户消息气泡（右对齐，紫色） -->
          <div class="flex justify-end mb-6">
            <div class="flex items-start gap-3 max-w-[80%]">
              <div class="bg-primary text-white rounded-2xl rounded-tr-sm px-4 py-3">
                <p class="text-sm leading-relaxed whitespace-pre-wrap">{{ selectedItem.question }}</p>
              </div>
              <div class="w-8 h-8 rounded-full bg-primary-100 flex items-center justify-center shrink-0">
                <el-icon color="#4F46E5"><User /></el-icon>
              </div>
            </div>
          </div>

          <!-- AI 回答气泡（左对齐，白色） -->
          <div class="flex justify-start mb-4">
            <div class="flex items-start gap-3 max-w-[80%]">
              <div class="w-8 h-8 rounded-full gradient-bg flex items-center justify-center shrink-0">
                <el-icon color="#fff"><Service /></el-icon>
              </div>
              <div class="bg-white border border-gray-100 rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm">
                <!-- 重新生成加载中 -->
                <div v-if="regenerating" class="flex items-center gap-2 text-gray-400 py-2">
                  <span class="text-sm">正在用 AI 重新生成回答</span>
                  <span class="flex gap-1">
                    <span class="w-1.5 h-1.5 bg-gray-300 rounded-full animate-bounce" style="animation-delay:0s"></span>
                    <span class="w-1.5 h-1.5 bg-gray-300 rounded-full animate-bounce" style="animation-delay:0.2s"></span>
                    <span class="w-1.5 h-1.5 bg-gray-300 rounded-full animate-bounce" style="animation-delay:0.4s"></span>
                  </span>
                </div>
                <!-- 回答内容 -->
                <template v-else>
                  <p class="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">{{ displayAnswer }}</p>

                  <!-- 引用来源入口 -->
                  <div v-if="selectedSources.length" class="mt-3 pt-3 border-t border-gray-50">
                    <div
                      class="flex items-center gap-1 text-xs text-secondary cursor-pointer hover:underline"
                      @click="sourcesVisible = !sourcesVisible"
                    >
                      <el-icon><Link /></el-icon>
                      <span>引用 {{ selectedSources.length }} 个来源</span>
                      <el-icon><ArrowRight /></el-icon>
                    </div>
                    <!-- 展开来源列表 -->
                    <div v-if="sourcesVisible" class="mt-2 space-y-2">
                      <div
                        v-for="(src, idx) in selectedSources"
                        :key="idx"
                        class="bg-gray-50 rounded-lg p-2 text-xs"
                      >
                        <div class="flex items-center justify-between mb-1">
                          <span class="font-medium text-gray-600">{{ src.law }} {{ src.article }}</span>
                          <el-tag size="small" effect="plain">
                            相关度 {{ src.relevance ? (src.relevance * 100).toFixed(0) : 0 }}%
                          </el-tag>
                        </div>
                        <p class="text-gray-500 line-clamp-2">{{ src.content }}</p>
                      </div>
                    </div>
                  </div>

                  <!-- 相似案例 -->
                  <div v-if="selectedCases.length" class="mt-3 pt-3 border-t border-gray-50">
                    <p class="text-xs font-medium text-gray-500 mb-2 flex items-center gap-1">
                      <el-icon><Files /></el-icon>
                      相似案例推荐
                    </p>
                    <div v-for="c in selectedCases" :key="c.title" class="mb-2">
                      <div class="bg-gray-50 rounded-lg p-2">
                        <p class="text-sm font-medium text-gray-700 truncate">{{ c.title }}</p>
                        <p class="text-xs text-gray-400 mt-0.5 line-clamp-2">{{ c.summary }}</p>
                        <div class="flex items-center gap-2 mt-1">
                          <el-tag size="small" effect="plain">{{ c.court || '基层法院' }}</el-tag>
                          <el-tag size="small" type="success" effect="plain">{{ c.result || '胜诉' }}</el-tag>
                        </div>
                      </div>
                    </div>
                  </div>

                  <!-- 落地服务 -->
                  <div v-if="selectedServices && selectedServices.length" class="mt-3 pt-3 border-t border-gray-50">
                    <p class="text-xs font-medium text-gray-500 mb-2 flex items-center gap-1">
                      <el-icon><Service /></el-icon>
                      落地服务指引
                    </p>
                    <div class="space-y-2">
                      <div v-for="(svc, idx) in selectedServices" :key="idx"
                        class="flex items-center gap-3 bg-green-50 rounded-lg p-2"
                      >
                        <div class="w-8 h-8 rounded-full bg-green-100 flex items-center justify-center shrink-0">
                          <el-icon color="#10B981"><Phone /></el-icon>
                        </div>
                        <div>
                          <p class="text-sm font-medium text-gray-700">{{ svc.service_type }}：{{ svc.hotline }}</p>
                          <p class="text-xs text-gray-500">{{ svc.institution }}</p>
                        </div>
                      </div>
                    </div>
                  </div>
                </template>
              </div>
            </div>
          </div>
        </div>

        <!-- 空状态 -->
        <div v-else class="flex flex-col items-center justify-center h-full text-gray-400">
          <el-icon :size="48"><Document /></el-icon>
          <p class="text-sm mt-3">选择左侧历史记录查看详情</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * 提问历史页面
 * 左侧列表 + 右侧气泡式对话展示（与智能问答页面风格一致）
 * 支持对旧回答（法条匹配）重新生成 AI 回答
 */
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Search, Clock, User, Service, Star, StarFilled,
  ChatLineRound, Delete, Document, Link, ArrowRight,
  Refresh, Files, Phone
} from '@element-plus/icons-vue'
import {
  getConversations, getConversationMessages,
  deleteConversation, toggleFavoriteApi, regenerateAnswer as regenerateAnswerApi
} from '../api/qa'

const router = useRouter()

const searchText = ref('')
const filterCategory = ref('')
const selectedId = ref(null)
const selectedItem = ref(null)
const historyList = ref([])
const selectedSources = ref([])
const selectedCases = ref([])
const selectedServices = ref([])
const sourcesVisible = ref(false)
const regenerating = ref(false)

// 判断是否为旧回答（未配置 API Key 时生成的法条匹配结果）
const OLD_ANSWER_MARKER = '未配置 DeepSeek API Key'

function isOldAnswer(answer) {
  return answer && answer.includes(OLD_ANSWER_MARKER)
}

// 显示的回答内容：如果是旧回答，去掉末尾的警告提示
const displayAnswer = computed(() => {
  if (!selectedItem.value || !selectedItem.value.answer) return ''
  const answer = selectedItem.value.answer
  if (isOldAnswer(answer)) {
    // 去掉警告行
    const lines = answer.split('\n')
    const filtered = lines.filter(line => !line.includes(OLD_ANSWER_MARKER))
    return filtered.join('\n').trim()
  }
  return answer
})

onMounted(() => {
  loadHistory()
})

async function loadHistory() {
  try {
    const res = await getConversations()
    historyList.value = res.list || res || []
    if (historyList.value.length > 0) {
      selectHistory(historyList.value[0])
    }
  } catch (e) {
    historyList.value = []
  }
}

const filteredList = computed(() => {
  let list = historyList.value
  if (searchText.value) {
    const kw = searchText.value.toLowerCase()
    list = list.filter(
      (item) =>
        item.question?.toLowerCase().includes(kw) ||
        item.answer?.toLowerCase().includes(kw)
    )
  }
  if (filterCategory.value) {
    list = list.filter((item) => item.question?.includes(filterCategory.value))
  }
  return list
})

async function selectHistory(item) {
  selectedId.value = item.id
  selectedItem.value = item
  sourcesVisible.value = false

  // 尝试加载对话详情（包含引用来源）
  try {
    const detail = await getConversationMessages(item.id)
    if (detail) {
      selectedItem.value = detail
      // 解析引用来源
      if (detail.citations && Array.isArray(detail.citations)) {
        selectedSources.value = detail.citations
      } else {
        selectedSources.value = []
      }
    }
  } catch (e) {
    selectedSources.value = []
  }
}

// 重新生成 AI 回答
async function regenerateAnswer(item) {
  regenerating.value = true
  try {
    const res = await regenerateAnswerApi(item.id)
    // 更新显示
    selectedItem.value = {
      ...selectedItem.value,
      answer: res.answer,
      confidence: res.confidence
    }
    if (res.citations && Array.isArray(res.citations)) {
      selectedSources.value = res.citations
    }
    if (res.cases) {
      selectedCases.value = res.cases
    }
    if (res.landing_services) {
      selectedServices.value = res.landing_services
    }
    // 更新列表中的数据
    const idx = historyList.value.findIndex(h => h.id === item.id)
    if (idx !== -1) {
      historyList.value[idx].answer = res.answer
      historyList.value[idx].confidence = res.confidence
    }
    ElMessage.success('回答已用 AI 重新生成')
  } catch (e) {
    ElMessage.error('重新生成失败，请稍后重试')
  } finally {
    regenerating.value = false
  }
}

async function toggleFavorite(item) {
  try {
    await toggleFavoriteApi(item.id)
    item.is_favorited = !item.is_favorited
    ElMessage.success(item.is_favorited ? '已收藏' : '已取消收藏')
  } catch (e) {
    ElMessage.error('操作失败')
  }
}

async function deleteHistory(item) {
  try {
    await ElMessageBox.confirm('确定删除该提问记录？', '提示', { type: 'warning' })
    await deleteConversation(item.id)
    historyList.value = historyList.value.filter((h) => h.id !== item.id)
    if (selectedId.value === item.id) {
      selectedItem.value = null
      selectedId.value = null
      selectedSources.value = []
    }
    ElMessage.success('已删除')
  } catch (e) {
    // 取消或失败
  }
}

function goToQA(question) {
  router.push({ path: '/qa', query: { q: question } })
}

function formatTime(time) {
  if (!time) return ''
  return time.replace('T', ' ').substring(0, 16)
}
</script>

<style scoped>
</style>