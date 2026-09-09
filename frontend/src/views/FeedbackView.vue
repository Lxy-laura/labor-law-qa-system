<template>
  <!-- 用户反馈页面 -->
  <!-- 普通用户：查看自己提交的反馈记录 -->
  <!-- 管理员：查看所有用户的反馈记录 -->
  <div class="h-full p-4 overflow-y-auto custom-scrollbar">
    <!-- 页面标题 -->
    <div class="flex items-center justify-between mb-5">
      <div>
        <h2 class="page-title">{{ isAdmin ? '用户反馈管理' : '我的反馈' }}</h2>
        <p class="text-sm text-gray-400 mt-1">
          {{ isAdmin ? '查看所有用户对问答回答的评价与建议' : '查看您提交的问答反馈记录' }}
        </p>
      </div>
      <div class="flex items-center gap-3">
        <el-select
          v-if="isAdmin"
          v-model="filterRating"
          placeholder="全部评分"
          class="!w-32"
          @change="loadFeedback"
        >
          <el-option label="全部评分" value="" />
          <el-option label="5星" value="5" />
          <el-option label="4星" value="4" />
          <el-option label="3星" value="3" />
          <el-option label="2星" value="2" />
          <el-option label="1星" value="1" />
        </el-select>
        <el-button :icon="Refresh" @click="loadFeedback">刷新</el-button>
      </div>
    </div>

    <!-- 评分概览 -->
    <div class="grid grid-cols-5 gap-3 mb-5">
      <div
        v-for="star in [5, 4, 3, 2, 1]"
        :key="star"
        class="card-container p-4 text-center"
      >
        <div class="flex items-center justify-center gap-0.5 mb-1">
          <el-icon
            v-for="n in 5"
            :key="n"
            :size="14"
            :color="n <= star ? '#F59E0B' : '#E5E7EB'"
          >
            <Star />
          </el-icon>
        </div>
        <div class="text-xl font-bold text-gray-800">{{ ratingStats[star] || 0 }}</div>
        <div class="text-xs text-gray-400 mt-0.5">{{ star }}星评价</div>
      </div>
    </div>

    <!-- 反馈列表 -->
    <div class="card-container">
      <el-table :data="feedbackList" stripe style="width: 100%">
        <el-table-column label="评分" width="120" align="center">
          <template #default="{ row }">
            <div class="flex items-center justify-center gap-0.5">
              <el-icon
                v-for="n in 5"
                :key="n"
                :size="14"
                :color="n <= row.rating ? '#F59E0B' : '#E5E7EB'"
              >
                <Star />
              </el-icon>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="提问内容" min-width="250" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="text-sm text-gray-700">{{ row.question }}</span>
          </template>
        </el-table-column>

        <el-table-column label="回答摘要" min-width="300" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="text-xs text-gray-500">{{ row.answer }}</span>
          </template>
        </el-table-column>

        <el-table-column label="反馈评论" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.comment" class="text-sm text-gray-600">{{ row.comment }}</span>
            <span v-else class="text-xs text-gray-400">无评论</span>
          </template>
        </el-table-column>

        <!-- 管理员才能看到用户名列 -->
        <el-table-column v-if="isAdmin" label="用户" width="100" align="center">
          <template #default="{ row }">
            <el-tag size="small" effect="plain">{{ row.username || '匿名用户' }}</el-tag>
          </template>
        </el-table-column>

        <el-table-column label="反馈时间" width="160" align="center">
          <template #default="{ row }">
            <span class="text-xs text-gray-400">{{ formatTime(row.created_at) }}</span>
          </template>
        </el-table-column>
      </el-table>

      <!-- 空状态 -->
      <div v-if="feedbackList.length === 0 && !loading" class="flex flex-col items-center justify-center py-16 text-gray-400">
        <el-icon :size="48"><ChatDotRound /></el-icon>
        <p class="text-sm mt-3">
          {{ isAdmin ? '暂无用户反馈' : '您还没有提交过反馈，请在智能问答页面评价回答' }}
        </p>
      </div>

      <!-- 加载中状态 -->
      <div v-if="loading" class="flex items-center justify-center py-16 text-gray-400">
        <el-icon class="is-loading" :size="24"><Loading /></el-icon>
        <span class="text-sm ml-2">正在加载反馈数据...</span>
      </div>

      <!-- 分页（仅管理员有分页） -->
      <div v-if="isAdmin && total > pageSize" class="flex justify-center py-4">
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :total="total"
          layout="prev, pager, next"
          @current-change="loadFeedback"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * 用户反馈页面
 * 普通用户：查看自己提交的反馈记录（调用 /api/qa/feedback/my）
 * 管理员：查看所有用户的反馈记录（调用 /api/qa/feedback）
 */
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, Star, ChatDotRound, Loading } from '@element-plus/icons-vue'
import { getFeedbackList, getMyFeedback } from '../api/qa'
import { useUserStore } from '../store/user'

const userStore = useUserStore()
const isAdmin = computed(() => userStore.isAdmin)

const filterRating = ref('')
const feedbackList = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = 20
const loading = ref(false)
const ratingStats = reactive({ 5: 0, 4: 0, 3: 0, 2: 0, 1: 0 })

onMounted(() => {
  loadFeedback()
})

async function loadFeedback() {
  loading.value = true
  try {
    let res
    if (isAdmin.value) {
      // 管理员：获取所有用户的反馈
      res = await getFeedbackList({
        rating: filterRating.value || undefined,
        page: currentPage.value,
        pageSize
      })
    } else {
      // 普通用户：获取自己的反馈
      res = await getMyFeedback()
    }

    feedbackList.value = res.list || res.items || res || []
    total.value = res.total || feedbackList.value.length

    // 更新评分统计
    if (res.stats) {
      Object.assign(ratingStats, res.stats)
    } else {
      // 本地计算统计
      Object.keys(ratingStats).forEach((k) => (ratingStats[k] = 0))
      feedbackList.value.forEach((f) => {
        if (ratingStats[f.rating] !== undefined) {
          ratingStats[f.rating]++
        }
      })
    }
  } catch (e) {
    feedbackList.value = []
    ElMessage.error('反馈数据加载失败，请确保后端服务已启动')
  } finally {
    loading.value = false
  }
}

function formatTime(time) {
  if (!time) return ''
  return time.replace('T', ' ').substring(0, 16)
}
</script>

<style scoped>
</style>