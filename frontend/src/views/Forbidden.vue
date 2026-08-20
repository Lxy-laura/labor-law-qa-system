<template>
  <!-- 403 无权限页面 -->
  <div class="flex h-screen w-full flex-col items-center justify-center bg-gray-50">
    <div class="text-center">
      <div class="text-7xl font-bold text-gray-300 mb-4">403</div>
      <p class="text-xl text-gray-600 mb-2">无访问权限</p>
      <p class="text-sm text-gray-400 mb-6">您没有权限访问该页面，请联系管理员</p>
      <el-button type="primary" @click="$router.push('/qa')">返回首页</el-button>
    </div>
  </div>
</template>

<script setup>
</script>
