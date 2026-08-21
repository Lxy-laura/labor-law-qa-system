<template>
  <!-- 引用来源卡片组件 -->
  <div
    class="card-container p-4 mb-3 cursor-pointer transition-all duration-200 hover:shadow-card-hover hover:border-primary-200"
    @click="handleClick"
  >
    <!-- 来源标题与相关度 -->
    <div class="flex items-start justify-between mb-2">
      <div class="flex items-center gap-2 flex-1 min-w-0">
        <el-icon :size="16" class="text-primary shrink-0">
          <Document />
        </el-icon>
        <span class="text-sm font-medium text-gray-800 truncate">
          {{ source.law }} {{ source.article }}
        </span>
      </div>
      <el-tag size="small" type="primary" effect="plain" class="shrink-0">
        {{ normalizedRelevance }}%
      </el-tag>
    </div>

    <!-- 内容片段 -->
    <p class="text-xs text-gray-500 leading-relaxed line-clamp-3">
      {{ source.snippet || source.content || source.summary }}
    </p>
  </div>
</template>

<script setup>
/**
 * 引用溯源卡片
 * 展示 AI 回答所引用的来源文档信息
 * relevance 已由后端归一化到 0-1 范围，前端只需 × 100 显示百分比
 */
import { computed } from 'vue'
import { Document } from '@element-plus/icons-vue'

const props = defineProps({
  source: {
    type: Object,
    required: true,
    default: () => ({})
  }
})

const emit = defineEmits(['click'])

// 相关度百分比：relevance 范围 0-1，直接 × 100
const normalizedRelevance = computed(() => {
  const val = props.source.relevance
  if (val == null) return 0
  // 限制在 0-1 范围内，然后 × 100
  const clamped = Math.min(1, Math.max(0, val))
  return Math.round(clamped * 100)
})

function handleClick() {
  emit('click', props.source)
}
</script>

<style scoped>
</style>