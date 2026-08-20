<template>
  <!-- 侧边栏：根据 role 动态显示菜单 -->
  <aside
    class="flex flex-col bg-white border-r border-gray-200 transition-all duration-300"
    :style="{ width: collapse ? '64px' : '220px' }"
  >
    <!-- Logo 区域 -->
    <div class="flex items-center h-14 px-4 border-b border-gray-100 shrink-0">
      <div class="w-8 h-8 rounded-lg gradient-bg flex items-center justify-center shrink-0">
        <el-icon :size="18" color="#fff"><ScaleToOriginal /></el-icon>
      </div>
      <span
        v-if="!collapse"
        class="ml-2 text-sm font-bold text-gray-800 whitespace-nowrap"
      >
        劳动法智能问答
      </span>
    </div>

    <!-- 菜单列表 -->
    <nav class="flex-1 py-3 overflow-y-auto custom-scrollbar">
      <div
        v-for="item in visibleMenus"
        :key="item.path"
        class="flex items-center mx-2 mb-1 px-3 py-2.5 rounded-lg cursor-pointer transition-colors duration-150"
        :class="
          isActive(item.path)
            ? 'bg-primary-50 text-primary font-medium'
            : 'text-gray-600 hover:bg-gray-50 hover:text-gray-800'
        "
        @click="navigate(item.path)"
      >
        <el-icon :size="18" class="shrink-0">
          <component :is="item.icon" />
        </el-icon>
        <span v-if="!collapse" class="ml-3 text-sm whitespace-nowrap">
          {{ item.label }}
        </span>
      </div>
    </nav>

    <!-- 底部版本信息 -->
    <div v-if="!collapse" class="px-4 py-3 border-t border-gray-100 shrink-0">
      <p class="text-xs text-gray-400">Version 1.0.0</p>
    </div>
  </aside>
</template>

<script setup>
/**
 * 侧边栏组件
 * 根据 role 动态显示菜单（普通用户可见问答/历史/收藏，管理员可见全部）
 */
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '../store/user'
import {
  ChatLineRound,
  Files,
  DataAnalysis,
  Connection,
  ScaleToOriginal,
  Clock,
  Star,
  ChatDotRound
} from '@element-plus/icons-vue'

defineProps({
  collapse: { type: Boolean, default: false }
})

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

// 完整菜单列表
const allMenus = [
  { path: '/qa', label: '智能问答', icon: ChatLineRound, requireAdmin: false },
  { path: '/history', label: '提问历史', icon: Clock, requireAdmin: false },
  { path: '/favorites', label: '我的收藏', icon: Star, requireAdmin: false },
  { path: '/knowledge-base', label: '知识库管理', icon: Files, requireAdmin: true },
  { path: '/analytics', label: '数据分析', icon: DataAnalysis, requireAdmin: true },
  { path: '/retrieval-viz', label: '检索调试', icon: Connection, requireAdmin: true },
  { path: '/feedback', label: '用户反馈', icon: ChatDotRound, requireAdmin: true }
]

// 根据角色过滤可见菜单
const visibleMenus = computed(() => {
  return allMenus.filter((item) => !item.requireAdmin || userStore.isAdmin)
})

// 判断当前路由是否激活
function isActive(path) {
  return route.path === path
}

function navigate(path) {
  router.push(path)
}
</script>

<style scoped>
</style>