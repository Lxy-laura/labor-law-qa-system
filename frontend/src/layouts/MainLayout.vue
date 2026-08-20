<template>
  <div class="flex h-screen w-full overflow-hidden bg-gray-50">
    <Sidebar :collapse="isCollapse" />
    <div class="flex flex-1 flex-col overflow-hidden">
      <TopBar :collapse="isCollapse" @toggle="isCollapse = !isCollapse" />
      <main class="flex-1 overflow-hidden relative">
        <router-view v-slot="{ Component }">
          <component :is="Component" />
        </router-view>
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import Sidebar from '../components/Sidebar.vue'
import TopBar from '../components/TopBar.vue'
const isCollapse = ref(false)
</script>

<style scoped>
</style>