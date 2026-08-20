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
          {{ source.title }}
        </span>
      </div>
      <el-tag size="small" type="primary" effect="plain" class="shrink-0">
        {{ source.relevance != null ? Math.round(source.relevance * 100) : 95 }}%
      </el-tag>
    </div>

    <!-- 来源类型 -->
    <div class="flex items-center gap-2 mb-2">
      <el-tag size="small" :type="typeTagType" effect="plain">
        {{ typeLabel }}
      </el-tag>
      <span v-if="source.source" class="text-xs text-gray-400">
        {{ source.source }}
      </span>
    </div>

    <!-- 内容片段 -->
    <p class="text-xs text-gray-500 leading-relaxed line-clamp-3">
      {{ source.snippet || source.content || source.summary }}
    </p>

    <!-- 页码/章节信息 -->
    <div v-if="source.page || source.chapter" class="flex items-center gap-3 mt-2 pt-2 border-t border-gray-50">
      <span v-if="source.chapter" class="text-xs text-gray-400">
        <el-icon><Collection /></el-icon>
        {{ source.chapter }}
      </span>
      <span v-if="source.page" class="text-xs text-gray-400">
        <el-icon><Document /></el-icon>
        第 {{ source.page }} 页
      </span>
    </div>
  </div>
</template>

<script setup>
/**
 * 引用溯源卡片
 * 展示 AI 回答所引用的来源文档信息
 */
import { computed } from 'vue'
import { Document, Collection } from '@element-plus/icons-vue'

const props = defineProps({
  source: {
    type: Object,
    required: true,
    default: () => ({})
  }
})

const emit = defineEmits(['click'])

// 来源类型标签
const typeLabel = computed(() => {
  const typeMap = {
    law: '法律法规',
    regulation: '部门规章',
    case: '案例',
    guide: '办事指南',
    document: '文档'
  }
  return typeMap[props.source.type] || '文档'
})

// 标签颜色
const typeTagType = computed(() => {
  const colorMap = {
    law: 'danger',
    regulation: 'warning',
    case: 'success',
    guide: 'info',
    document: 'primary'
  }
  return colorMap[props.source.type] || 'primary'
})

function handleClick() {
  emit('click', props.source)
}
</script>

<style scoped>
</style>
