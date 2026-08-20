<template>
  <!-- 主布局：侧边栏 + 顶部栏 + 内容区 -->
  <div class="flex h-screen w-full overflow-hidden bg-gray-50">
    <!-- 侧边栏 -->
    <Sidebar :collapse="isCollapse" />

    <!-- 右侧区域 -->
    <div class="flex flex-1 flex-col overflow-hidden">
      <!-- 顶部栏 -->
      <TopBar :collapse="isCollapse" @toggle="isCollapse = !isCollapse" />

      <!-- 主内容区 -->
      <main class="flex-1 overflow-y-auto custom-scrollbar">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </main>
    </div>
  </div>
</template>

<script setup>
/**
 * 主布局组件
 * 组合 Sidebar + TopBar + 内容区
 */
import { ref } from 'vue'
import Sidebar from '../components/Sidebar.vue'
import TopBar from '../components/TopBar.vue'

const isCollapse = ref(false)
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
