<template>
  <!-- 404 页面 -->
  <div class="flex h-screen w-full flex-col items-center justify-center bg-gray-50">
    <div class="text-center">
      <div class="text-7xl font-bold text-gray-300 mb-4">404</div>
      <p class="text-xl text-gray-600 mb-6">页面不存在</p>
      <el-button type="primary" @click="$router.push('/qa')">返回首页</el-button>
    </div>
  </div>
</template>

<script setup>
</script>
