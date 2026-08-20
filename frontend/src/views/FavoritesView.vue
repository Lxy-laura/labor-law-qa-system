<template>
  <!-- 我的收藏页面 -->
  <div class="h-full p-4 overflow-y-auto custom-scrollbar">
    <!-- 页面标题 -->
    <div class="flex items-center justify-between mb-5">
      <div>
        <h2 class="page-title">我的收藏</h2>
        <p class="text-sm text-gray-400 mt-1">收藏的优质问答记录</p>
      </div>
      <div class="flex items-center gap-2">
        <el-input
          v-model="searchText"
          placeholder="搜索收藏..."
          :prefix-icon="Search"
          clearable
          class="!w-64"
        />
      </div>
    </div>

    <!-- 收藏列表 -->
    <div v-if="filteredList.length > 0" class="grid grid-cols-2 gap-4">
      <div
        v-for="item in filteredList"
        :key="item.id"
        class="card-container p-5 cursor-pointer hover:border-primary-200 transition-all"
      >
        <!-- 问题 -->
        <div class="flex items-start gap-3 mb-3">
          <div class="w-8 h-8 rounded-full bg-primary-100 flex items-center justify-center shrink-0">
            <el-icon color="#4F46E5"><ChatLineRound /></el-icon>
          </div>
          <div class="flex-1 min-w-0">
            <p class="text-sm font-medium text-gray-800 line-clamp-2">{{ item.question }}</p>
            <p class="text-xs text-gray-400 mt-1">{{ formatTime(item.created_at) }}</p>
          </div>
          <el-icon
            class="text-yellow-500 cursor-pointer hover:text-yellow-600 shrink-0"
            @click.stop="removeFavorite(item)"
          >
            <StarFilled />
          </el-icon>
        </div>

        <!-- 回答预览 -->
        <div class="bg-gray-50 rounded-lg p-3 mb-3">
          <p class="text-xs text-gray-500 line-clamp-3 leading-relaxed">{{ item.answer }}</p>
        </div>

        <!-- 底部操作 -->
        <div class="flex items-center justify-between">
          <el-tag v-if="item.confidence" size="small" type="success" effect="plain">
            置信度 {{ (item.confidence * 100).toFixed(0) }}%
          </el-tag>
          <div class="flex items-center gap-2 ml-auto">
            <el-button size="small" :icon="View" @click="viewDetail(item)">查看详情</el-button>
            <el-button size="small" type="primary" :icon="ChatLineRound" @click="goToQA(item.question)">
              继续提问
            </el-button>
          </div>
        </div>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-else class="flex flex-col items-center justify-center h-96 text-gray-400">
      <el-icon :size="56"><Star /></el-icon>
      <p class="text-sm mt-3">暂无收藏记录</p>
      <p class="text-xs mt-1">在提问历史中点击星标即可收藏</p>
      <el-button class="mt-4" type="primary" @click="goToQA()">去提问</el-button>
    </div>

    <!-- 详情弹窗 -->
    <el-dialog v-model="detailVisible" title="收藏详情" width="640px">
      <div v-if="currentDetail" class="space-y-4">
        <div>
          <p class="text-xs text-gray-400 mb-1">提问内容</p>
          <p class="text-sm text-gray-800 leading-relaxed">{{ currentDetail.question }}</p>
        </div>
        <el-divider />
        <div>
          <p class="text-xs text-gray-400 mb-1">AI 回答</p>
          <p class="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">{{ currentDetail.answer }}</p>
        </div>
        <div class="flex items-center gap-4 text-xs text-gray-400">
          <span>收藏时间：{{ formatTime(currentDetail.created_at) }}</span>
          <el-tag v-if="currentDetail.confidence" size="small" type="success" effect="plain">
            置信度 {{ (currentDetail.confidence * 100).toFixed(0) }}%
          </el-tag>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
/**
 * 我的收藏页面
 * 展示用户收藏的问答记录，支持搜索、查看详情、取消收藏
 */
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  Search, Star, StarFilled, ChatLineRound, View
} from '@element-plus/icons-vue'
import { getFavorites, toggleFavoriteApi } from '../api/qa'

const router = useRouter()

const searchText = ref('')
const favoriteList = ref([])
const detailVisible = ref(false)
const currentDetail = ref(null)

onMounted(() => {
  loadFavorites()
})

async function loadFavorites() {
  try {
    const res = await getFavorites()
    favoriteList.value = res.list || res || []
  } catch (e) {
    favoriteList.value = []
  }
}

const filteredList = computed(() => {
  if (!searchText.value) return favoriteList.value
  const kw = searchText.value.toLowerCase()
  return favoriteList.value.filter(
    (item) =>
      item.question?.toLowerCase().includes(kw) ||
      item.answer?.toLowerCase().includes(kw)
  )
})

async function removeFavorite(item) {
  try {
    await toggleFavoriteApi(item.id)
    favoriteList.value = favoriteList.value.filter((f) => f.id !== item.id)
    ElMessage.success('已取消收藏')
  } catch (e) {
    ElMessage.error('操作失败')
  }
}

function viewDetail(item) {
  currentDetail.value = item
  detailVisible.value = true
}

function goToQA(question) {
  if (question) {
    router.push({ path: '/qa', query: { q: question } })
  } else {
    router.push('/qa')
  }
}

function formatTime(time) {
  if (!time) return ''
  return time.replace('T', ' ').substring(0, 16)
}
</script>

<style scoped>
</style>