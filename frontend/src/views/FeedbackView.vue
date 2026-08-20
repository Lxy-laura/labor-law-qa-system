<template>
  <!-- 用户反馈页面（管理员） -->
  <div class="h-full p-4 overflow-y-auto custom-scrollbar">
    <!-- 页面标题 -->
    <div class="flex items-center justify-between mb-5">
      <div>
        <h2 class="page-title">用户反馈</h2>
        <p class="text-sm text-gray-400 mt-1">查看用户对问答回答的评价与建议</p>
      </div>
      <div class="flex items-center gap-3">
        <el-select v-model="filterRating" placeholder="全部评分" class="!w-32" @change="loadFeedback">
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

        <el-table-column label="用户" width="100" align="center">
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
      <div v-if="feedbackList.length === 0" class="flex flex-col items-center justify-center py-16 text-gray-400">
        <el-icon :size="48"><ChatDotRound /></el-icon>
        <p class="text-sm mt-3">暂无用户反馈</p>
      </div>

      <!-- 分页 -->
      <div v-if="total > pageSize" class="flex justify-center py-4">
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
 * 用户反馈页面（管理员功能）
 * 查看所有用户对问答回答的评分和评论
 */
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, Star, ChatDotRound } from '@element-plus/icons-vue'
import { getFeedbackList } from '../api/qa'

const filterRating = ref('')
const feedbackList = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = 20
const ratingStats = reactive({ 5: 0, 4: 0, 3: 0, 2: 0, 1: 0 })

onMounted(() => {
  loadFeedback()
})

async function loadFeedback() {
  try {
    const res = await getFeedbackList({
      rating: filterRating.value || undefined,
      page: currentPage.value,
      pageSize
    })
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
    // 后端未实现时使用模拟数据
    feedbackList.value = []
    ElMessage.info('反馈数据加载中，请确保后端服务已启动')
  }
}

function formatTime(time) {
  if (!time) return ''
  return time.replace('T', ' ').substring(0, 16)
}
</script>

<style scoped>
</style>