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
  </header>
</template>

<script setup>
/**
 * 顶部栏组件
 * 显示当前页面标题、用户角色与用户信息，提供退出功能
 */
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '../store/user'
import { ElMessageBox, ElMessage } from 'element-plus'
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

// 下拉菜单命令处理
function handleCommand(command) {
  if (command === 'logout') {
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
