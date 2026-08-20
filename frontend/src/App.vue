<template>
  <div id="app-root" class="h-full w-full">
    <router-view />
  </div>
</template>

<script setup>
/**
 * 根组件
 * 根据登录状态显示登录页或主布局
 */
import { useUserStore } from './store/user'

const userStore = useUserStore()

// 应用启动时从 localStorage 恢复用户状态
userStore.restoreFromStorage()
</script>

<style scoped>
#app-root {
  font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif;
}
</style>
