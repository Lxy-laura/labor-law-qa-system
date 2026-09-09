<template>
  <!-- 顶部栏：标题 + 折叠按钮 + 用户信息 -->
  <header
    class="flex items-center justify-between h-14 px-4 bg-white border-b border-gray-200 shrink-0"
  >
    <!-- 左侧：折叠按钮 + 页面标题 -->
    <div class="flex items-center gap-3">
      <el-button
        text
        class="!p-2"
        @click="$emit('toggle')"
      >
        <el-icon :size="20">
          <Fold v-if="!collapse" />
          <Expand v-else />
        </el-icon>
      </el-button>
      <span class="text-base font-semibold text-gray-800">
        {{ currentTitle }}
      </span>
    </div>

    <!-- 右侧：用户信息 + 退出 -->
    <div class="flex items-center gap-4">
      <!-- 角色标签 -->
      <el-tag
        :type="userStore.isAdmin ? 'warning' : 'primary'"
        size="small"
        effect="plain"
      >
        {{ userStore.isAdmin ? '管理员' : '普通用户' }}
      </el-tag>

      <!-- 用户下拉菜单 -->
      <el-dropdown @command="handleCommand">
        <div class="flex items-center gap-2 cursor-pointer hover:bg-gray-50 px-2 py-1 rounded-lg transition-colors">
          <div class="w-8 h-8 rounded-full gradient-bg flex items-center justify-center text-white text-sm font-medium">
            {{ avatarText }}
          </div>
          <span class="text-sm text-gray-700">{{ userStore.username || '用户' }}</span>
          <el-icon class="text-gray-400"><ArrowDown /></el-icon>
        </div>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="profile" :icon="User">
              <span>个人信息</span>
            </el-dropdown-item>
            <el-dropdown-item command="logout" :icon="SwitchButton" divided>
              <span>退出登录</span>
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>

    <!-- 个人信息弹窗 -->
    <el-dialog
      v-model="profileVisible"
      title="个人信息"
      width="480px"
      :close-on-click-modal="true"
    >
      <div v-loading="profileLoading" class="space-y-5">
        <!-- 头像 + 用户名 -->
        <div class="flex items-center gap-4 pb-4 border-b border-gray-100">
          <div class="w-16 h-16 rounded-full gradient-bg flex items-center justify-center text-white text-2xl font-bold shrink-0">
            {{ avatarText }}
          </div>
          <div>
            <h3 class="text-lg font-semibold text-gray-800">{{ profileData.username || userStore.username }}</h3>
            <el-tag
              :type="userStore.isAdmin ? 'warning' : 'primary'"
              size="small"
              effect="plain"
              class="mt-1"
            >
              {{ userStore.isAdmin ? '管理员' : '普通用户' }}
            </el-tag>
          </div>
        </div>

        <!-- 基本信息 -->
        <div class="space-y-3">
          <h4 class="text-sm font-semibold text-gray-500">基本信息</h4>
          <div class="grid grid-cols-2 gap-3">
            <div class="bg-gray-50 rounded-lg p-3">
              <p class="text-xs text-gray-400 mb-1">用户名</p>
              <p class="text-sm text-gray-700 font-medium">{{ profileData.username || '-' }}</p>
            </div>
            <div class="bg-gray-50 rounded-lg p-3">
              <p class="text-xs text-gray-400 mb-1">用户ID</p>
              <p class="text-sm text-gray-700 font-medium">{{ profileData.user_id || '-' }}</p>
            </div>
            <div class="bg-gray-50 rounded-lg p-3">
              <p class="text-xs text-gray-400 mb-1">邮箱</p>
              <p class="text-sm text-gray-700 font-medium truncate">{{ profileData.email || '-' }}</p>
            </div>
            <div class="bg-gray-50 rounded-lg p-3">
              <p class="text-xs text-gray-400 mb-1">注册时间</p>
              <p class="text-sm text-gray-700 font-medium">{{ profileData.created_at || '-' }}</p>
            </div>
          </div>
        </div>

        <!-- 使用统计 -->
        <div class="space-y-3">
          <h4 class="text-sm font-semibold text-gray-500">使用统计</h4>
          <div class="grid grid-cols-3 gap-3">
            <div class="bg-indigo-50 rounded-lg p-4 text-center">
              <p class="text-2xl font-bold text-indigo-600">{{ profileData.stats?.question_count ?? 0 }}</p>
              <p class="text-xs text-gray-500 mt-1">提问总数</p>
            </div>
            <div class="bg-green-50 rounded-lg p-4 text-center">
              <p class="text-2xl font-bold text-green-600">{{ profileData.stats?.favorite_count ?? 0 }}</p>
              <p class="text-xs text-gray-500 mt-1">收藏总数</p>
            </div>
            <div class="bg-amber-50 rounded-lg p-4 text-center">
              <p class="text-2xl font-bold text-amber-600">{{ profileData.stats?.feedback_count ?? 0 }}</p>
              <p class="text-xs text-gray-500 mt-1">反馈总数</p>
            </div>
          </div>
        </div>
      </div>

      <!-- 底部按钮 -->
      <template #footer>
        <el-button @click="profileVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </header>
</template>

<script setup>
/**
 * 顶部栏组件
 * 显示当前页面标题、用户角色与用户信息，提供退出功能和个人信息查看
 */
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '../store/user'
import { ElMessageBox, ElMessage } from 'element-plus'
import { getUserInfo } from '../api/auth'
import {
  Fold,
  Expand,
  ArrowDown,
  User,
  SwitchButton
} from '@element-plus/icons-vue'

defineProps({
  collapse: { type: Boolean, default: false }
})
defineEmits(['toggle'])

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

// 当前页面标题
const currentTitle = computed(() => route.meta.title || '劳动合同纠纷智能问答系统')

// 头像首字
const avatarText = computed(() => {
  const name = userStore.username || 'U'
  return name.charAt(0).toUpperCase()
})

// 个人信息弹窗状态
const profileVisible = ref(false)
const profileLoading = ref(false)
const profileData = ref({})

// 下拉菜单命令处理
async function handleCommand(command) {
  if (command === 'profile') {
    // 打开个人信息弹窗
    profileVisible.value = true
    profileLoading.value = true
    profileData.value = {}
    try {
      const info = await getUserInfo()
      profileData.value = info
    } catch (error) {
      ElMessage.error('获取用户信息失败')
    } finally {
      profileLoading.value = false
    }
  } else if (command === 'logout') {
    ElMessageBox.confirm('确定要退出登录吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
      .then(() => {
        userStore.logout()
        ElMessage.success('已退出登录')
        router.push('/login')
      })
      .catch(() => {})
  }
}
</script>

<style scoped>
</style>
