<template>
  <!-- 智能问答页面：三栏布局 -->
  <div class="flex h-full">
    <!-- ===== 左栏：对话历史 ===== -->
    <div class="w-64 shrink-0 bg-white border-r border-gray-200 flex flex-col">
      <!-- 新建对话按钮 -->
      <div class="p-3 border-b border-gray-100">
        <el-button
          type="primary"
          class="w-full"
          :icon="Plus"
          @click="newConversation"
        >
          新建对话
        </el-button>
      </div>

      <!-- 历史列表 -->
      <div class="flex-1 overflow-y-auto custom-scrollbar p-2">
        <div
          v-for="conv in conversations"
          :key="conv.id"
          class="group flex items-center gap-2 px-3 py-2.5 rounded-lg cursor-pointer transition-colors mb-1"
          :class="
            conv.id === currentConvId
              ? 'bg-primary-50 text-primary'
              : 'text-gray-600 hover:bg-gray-50'
          "
          @click="selectConversation(conv.id)"
        >
          <el-icon :size="16" class="shrink-0"><ChatLineRound /></el-icon>
          <span class="text-sm truncate flex-1">{{ conv.title }}</span>
          <el-icon
            class="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-red-500 transition-all"
            @click.stop="deleteConv(conv.id)"
          >
            <Delete />
          </el-icon>
        </div>
        <div v-if="conversations.length === 0" class="text-center py-8 text-sm text-gray-400">
          暂无对话记录
        </div>
      </div>
    </div>

    <!-- ===== 中栏：聊天区 ===== -->
    <div class="flex-1 flex flex-col bg-gray-50 min-w-0">
      <!-- 消息列表 -->
      <div ref="messageListRef" class="flex-1 overflow-y-auto custom-scrollbar px-6 py-4">
        <!-- 欢迎引导 -->
        <div v-if="messages.length === 0" class="flex flex-col items-center justify-center h-full">
          <div class="w-16 h-16 rounded-2xl gradient-bg flex items-center justify-center mb-4">
            <el-icon :size="32" color="#fff"><ChatLineRound /></el-icon>
          </div>
          <h2 class="text-xl font-semibold text-gray-700 mb-2">劳动合同纠纷智能问答</h2>
          <p class="text-sm text-gray-400 mb-6">输入您的问题，获取专业法律解答</p>
          <!-- 推荐问题 -->
          <div class="grid grid-cols-2 gap-3 max-w-2xl w-full">
            <div
              v-for="item in suggestedQuestions"
              :key="item.text"
              class="card-container p-4 cursor-pointer hover:border-primary-200 transition-colors"
              @click="askSuggested(item.text)"
            >
              <div class="flex items-start gap-2">
                <el-icon class="text-primary mt-0.5"><QuestionFilled /></el-icon>
                <div>
                  <p class="text-sm font-medium text-gray-700">{{ item.text }}</p>
                  <p class="text-xs text-gray-400 mt-1">{{ item.desc }}</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 消息气泡 -->
        <div v-for="msg in messages" :key="msg.id" class="mb-6">
          <!-- 用户消息 -->
          <div v-if="msg.role === 'user'" class="flex justify-end">
            <div class="flex items-start gap-3 max-w-[80%]">
              <div class="bg-primary text-white rounded-2xl rounded-tr-sm px-4 py-3">
                <p class="text-sm leading-relaxed whitespace-pre-wrap">{{ msg.content }}</p>
              </div>
              <div class="w-8 h-8 rounded-full bg-primary-100 flex items-center justify-center shrink-0">
                <el-icon color="#4F46E5"><User /></el-icon>
              </div>
            </div>
          </div>

          <!-- AI 消息 -->
          <div v-else class="flex justify-start">
            <div class="flex items-start gap-3 max-w-[80%]">
              <div class="w-8 h-8 rounded-full gradient-bg flex items-center justify-center shrink-0">
                <el-icon color="#fff"><Service /></el-icon>
              </div>
              <div class="bg-white border border-gray-100 rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm">
                <!-- 加载中 -->
                <div v-if="msg.loading" class="flex items-center gap-2 text-gray-400">
                  <span class="text-sm">正在思考中</span>
                  <span class="flex gap-1">
                    <span class="w-1.5 h-1.5 bg-gray-300 rounded-full animate-bounce" style="animation-delay:0s"></span>
                    <span class="w-1.5 h-1.5 bg-gray-300 rounded-full animate-bounce" style="animation-delay:0.2s"></span>
                    <span class="w-1.5 h-1.5 bg-gray-300 rounded-full animate-bounce" style="animation-delay:0.4s"></span>
                  </span>
                </div>
                <!-- 回答内容 -->
                <template v-else>
                  <p class="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">{{ msg.content }}</p>

                  <!-- 引用来源入口 -->
                  <div v-if="msg.sources && msg.sources.length" class="mt-3 pt-3 border-t border-gray-50">
                    <div
                      class="flex items-center gap-1 text-xs text-secondary cursor-pointer hover:underline"
                      @click="showSources(msg.sources)"
                    >
                      <el-icon><Link /></el-icon>
                      <span>引用 {{ msg.sources.length }} 个来源</span>
                      <el-icon><ArrowRight /></el-icon>
                    </div>
                  </div>

                  <!-- 相似案例 -->
                  <div v-if="msg.similarCases && msg.similarCases.length" class="mt-3 pt-3 border-t border-gray-50">
                    <p class="text-xs font-medium text-gray-500 mb-2 flex items-center gap-1">
                      <el-icon><Files /></el-icon>
                      相似案例推荐
                    </p>
                    <div v-for="c in msg.similarCases" :key="c.title" class="mb-2">
                      <div class="bg-gray-50 rounded-lg p-2 cursor-pointer hover:bg-gray-100 transition-colors" @click="showCaseDetail(c)">
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
                  <div v-if="msg.services" class="mt-3 pt-3 border-t border-gray-50">
                    <p class="text-xs font-medium text-gray-500 mb-2 flex items-center gap-1">
                      <el-icon><Service /></el-icon>
                      落地服务指引
                    </p>
                    <div class="space-y-2">
                      <!-- 电话服务 -->
                      <div v-for="phone in msg.services.phones" :key="phone.number"
                        class="flex items-center gap-3 bg-green-50 rounded-lg p-2"
                      >
                        <div class="w-8 h-8 rounded-full bg-green-100 flex items-center justify-center shrink-0">
                          <el-icon color="#10B981"><Phone /></el-icon>
                        </div>
                        <div>
                          <p class="text-sm font-medium text-gray-700">{{ phone.name }}：{{ phone.number }}</p>
                          <p class="text-xs text-gray-500">{{ phone.desc }}</p>
                        </div>
                      </div>
                      <!-- 行动指引 -->
                      <div v-if="msg.services.actions && msg.services.actions.length">
                        <p class="text-xs text-gray-500 mb-1">建议行动步骤：</p>
                        <div v-for="(action, idx) in msg.services.actions" :key="idx"
                          class="flex items-start gap-2 mb-1.5"
                        >
                          <div class="w-5 h-5 rounded-full bg-primary text-white text-xs flex items-center justify-center shrink-0 mt-0.5">
                            {{ idx + 1 }}
                          </div>
                          <p class="text-xs text-gray-600 leading-relaxed">{{ action }}</p>
                        </div>
                      </div>
                    </div>
                  </div>
                </template>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 输入区 -->
      <div class="border-t border-gray-200 bg-white p-4">
        <div class="flex items-end gap-3">
          <el-input
            v-model="inputText"
            type="textarea"
            :rows="2"
            placeholder="请输入您的劳动合同纠纷问题，按 Enter 发送，Shift+Enter 换行"
            resize="none"
            class="flex-1"
            @keydown.enter="handleSend"
          />
          <el-button
            type="primary"
            :icon="Promotion"
            :loading="sending"
            :disabled="!inputText.trim()"
            @click="handleSend"
          >
            发送
          </el-button>
        </div>
        <p class="text-xs text-gray-400 mt-2 text-center">
          AI 回答基于法律法规检索生成，仅供参考，不构成正式法律意见
        </p>
      </div>
    </div>

    <!-- ===== 右栏：引用溯源 ===== -->
    <div class="w-80 shrink-0 bg-white border-l border-gray-200 flex flex-col">
      <div class="px-4 py-3 border-b border-gray-100">
        <h3 class="text-sm font-semibold text-gray-700 flex items-center gap-2">
          <el-icon><Link /></el-icon>
          引用溯源
        </h3>
      </div>
      <div class="flex-1 overflow-y-auto custom-scrollbar p-3">
        <template v-if="currentSources.length">
          <SourceCard
            v-for="(src, idx) in currentSources"
            :key="idx"
            :source="src"
            @click="viewSource"
          />
        </template>
        <div v-else class="flex flex-col items-center justify-center h-full text-gray-400">
          <el-icon :size="40"><Document /></el-icon>
          <p class="text-sm mt-2">AI 回答的引用来源将在此显示</p>
        </div>
      </div>
    </div>

    <!-- 案例详情弹窗 -->
    <el-dialog v-model="caseDialogVisible" title="案例详情" width="600px">
      <div v-if="currentCase" class="space-y-4">
        <h4 class="text-lg font-semibold text-gray-800">{{ currentCase.title }}</h4>
        <div class="flex gap-2">
          <el-tag size="small">{{ currentCase.court }}</el-tag>
          <el-tag size="small" type="info">{{ currentCase.date }}</el-tag>
          <el-tag size="small" type="success">{{ currentCase.result }}</el-tag>
        </div>
        <div>
          <p class="text-sm font-medium text-gray-600 mb-1">案件概述</p>
          <p class="text-sm text-gray-500 leading-relaxed">{{ currentCase.summary }}</p>
        </div>
        <div v-if="currentCase.legalBasis">
          <p class="text-sm font-medium text-gray-600 mb-1">裁判依据</p>
          <p class="text-sm text-gray-500 leading-relaxed">{{ currentCase.legalBasis }}</p>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
/**
 * 智能问答页面
 * 三栏布局：对话历史（左）+ 聊天区（中）+ 引用溯源（右）
 * AI 回答后展示：引用溯源、相似案例、落地服务（12333/12348电话+行动指引）
 */
import { ref, reactive, nextTick, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Plus,
  ChatLineRound,
  Delete,
  User,
  Service,
  Link,
  ArrowRight,
  Files,
  Phone,
  QuestionFilled,
  Promotion,
  Document
} from '@element-plus/icons-vue'
import SourceCard from '../components/SourceCard.vue'
import { askQuestion, getConversations, deleteConversation, createConversation } from '../api/qa'

const inputText = ref('')
const sending = ref(false)
const messageListRef = ref(null)
const currentConvId = ref('')
const currentSources = ref([])
const caseDialogVisible = ref(false)
const currentCase = ref(null)
const route = useRoute()

// 对话历史
const conversations = ref([])

// 当前对话消息列表
const messages = ref([])

// 推荐问题
const suggestedQuestions = [
  { text: '公司拖欠工资怎么办？', desc: '了解拖欠工资的维权途径' },
  { text: '试用期可以不交社保吗？', desc: '试用期社保缴纳规定' },
  { text: '公司单方面调岗合法吗？', desc: '调岗调薪的法律边界' },
  { text: '解除劳动合同补偿标准', desc: '经济补偿金计算方式' }
]

// 消息自增 ID
let msgId = 0

onMounted(async () => {
  await loadConversations()
  // 如果从历史/收藏页面跳转来且携带了问题参数，自动填入并发送
  const q = route.query.q
  if (q) {
    inputText.value = q
    await nextTick()
    handleSend()
  }
})

// 加载对话列表
async function loadConversations(selectFirst = true) {
  try {
    const res = await getConversations()
    conversations.value = res.list || res || []
    if (selectFirst && conversations.value.length > 0) {
      selectConversation(conversations.value[0].id)
    }
  } catch (e) {
    conversations.value = []
  }
}

// 新建对话
function newConversation() {
  currentConvId.value = 'conv_' + Date.now()
  messages.value = []
  currentSources.value = []
  conversations.value.unshift({
    id: currentConvId.value,
    title: '新对话 ' + new Date().toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
  })
}

// 选择对话 - 加载历史消息
function selectConversation(id) {
  currentConvId.value = id
  const conv = conversations.value.find((c) => c.id === id)
  if (conv) {
    // 重建消息列表：用户问题 + AI 回答
    messages.value = [
      {
        id: ++msgId,
        role: 'user',
        content: conv.question
      },
      {
        id: ++msgId,
        role: 'assistant',
        content: conv.answer,
        loading: false,
        sources: [],
        similarCases: [],
        services: null
      }
    ]
    currentSources.value = []
    scrollToBottom()
  } else {
    messages.value = []
    currentSources.value = []
  }
}

// 删除对话
async function deleteConv(id) {
  try {
    await ElMessageBox.confirm('确定删除该对话？', '提示', { type: 'warning' })
    await deleteConversation(id)
    conversations.value = conversations.value.filter((c) => c.id !== id)
    if (currentConvId.value === id) {
      messages.value = []
      currentSources.value = []
    }
    ElMessage.success('已删除')
  } catch (e) {
    // 取消删除
  }
}

// 点击推荐问题
function askSuggested(text) {
  inputText.value = text
  handleSend()
}

// 发送消息
async function handleSend(e) {
  // Enter 发送，Shift+Enter 换行
  if (e && e.shiftKey) return
  if (e) e.preventDefault()

  const text = inputText.value.trim()
  if (!text || sending.value) return

  // 确保有对话
  if (!currentConvId.value) {
    newConversation()
  }

  // 添加用户消息
  messages.value.push({
    id: ++msgId,
    role: 'user',
    content: text
  })

  inputText.value = ''
  sending.value = true

  // 添加 AI 加载消息
  const aiMsg = reactive({
    id: ++msgId,
    role: 'assistant',
    content: '',
    loading: true,
    sources: [],
    similarCases: [],
    services: null
  })
  messages.value.push(aiMsg)

  await scrollToBottom()

  try {
    const res = await askQuestion({ question: text, conversationId: currentConvId.value })
    aiMsg.loading = false
    aiMsg.content = res.answer
    // 后端字段映射：citations -> sources, cases -> similarCases, landing_services -> services
    aiMsg.sources = res.sources || res.citations || []
    aiMsg.similarCases = res.similarCases || res.cases || []
    aiMsg.services = res.services || res.landing_services || null

    // 更新右侧引用
    if (aiMsg.sources.length) {
      currentSources.value = aiMsg.sources
    }

    // 重新加载对话列表（不切换当前选中的对话，保留引用来源等展示）
    loadConversations(false)

    await scrollToBottom()
  } catch (error) {
    aiMsg.loading = false
    aiMsg.content = '抱歉，回答时出现了错误，请稍后重试。'
  } finally {
    sending.value = false
  }
}

// 滚动到底部
async function scrollToBottom() {
  await nextTick()
  if (messageListRef.value) {
    messageListRef.value.scrollTop = messageListRef.value.scrollHeight
  }
}

// 显示引用来源
function showSources(sources) {
  currentSources.value = sources
}

// 查看来源详情
function viewSource(source) {
  ElMessage.info(`查看来源：${source.title}`)
}

// 显示案例详情
function showCaseDetail(caseInfo) {
  currentCase.value = caseInfo
  caseDialogVisible.value = true
}
</script>

<style scoped>
</style>