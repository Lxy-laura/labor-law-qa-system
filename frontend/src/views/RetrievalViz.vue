<template>
  <div class="h-full p-4 overflow-y-auto custom-scrollbar">
    <!-- 页面标题 -->
    <div class="mb-5">
      <h2 class="page-title">检索调试</h2>
      <p class="text-sm text-gray-400 mt-1">RAG 检索增强生成 - 四步管线全流程可视化展示</p>
    </div>

    <!-- 查询输入 -->
    <div class="card-container p-5 mb-5">
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 rounded-lg bg-primary-50 flex items-center justify-center shrink-0">
          <el-icon :size="20" color="#4F46E5"><Search /></el-icon>
        </div>
        <div class="flex-1">
          <el-input
            v-model="queryText"
            placeholder="输入查询语句，如：公司拖欠工资怎么办"
            class="!w-full"
            @keyup.enter="runRetrieval"
          >
            <template #append>
              <el-button type="primary" :icon="Search" :loading="running" @click="runRetrieval">
                运行检索
              </el-button>
            </template>
          </el-input>
        </div>
      </div>
    </div>

    <!-- 管线信息 -->
    <div v-if="pipelineInfo" class="card-container p-4 mb-5">
      <div class="flex flex-wrap items-center gap-4 text-xs">
        <span class="text-gray-400">知识库总块数：<span class="font-bold text-primary">{{ pipelineInfo.total_chunks }}</span></span>
        <span class="text-gray-400">检索算法：<span class="text-gray-600">{{ pipelineInfo.algorithm }}</span></span>
        <span class="text-gray-400">分块大小：<span class="text-gray-600">{{ pipelineInfo.chunk_size }}字</span></span>
        <span class="text-gray-400">模型：<span class="text-gray-600">{{ pipelineInfo.model }}</span></span>
        <span class="text-gray-400">API Key：<span :class="pipelineInfo.has_api_key ? 'text-green-500' : 'text-red-500'">{{ pipelineInfo.has_api_key ? '已配置' : '未配置' }}</span></span>
      </div>
    </div>

    <!-- 四步管线 -->
    <div class="flex items-stretch gap-0 mb-5">
      <div
        v-for="(step, idx) in 4"
        :key="idx"
        class="flex items-stretch flex-1"
      >
        <!-- 步骤卡片 -->
        <div
          class="flex-1 card-container p-4 transition-all duration-300"
          :class="currentStep >= idx ? 'border-primary-300 shadow-card-hover' : 'opacity-60'"
        >
          <div class="flex items-center gap-3 mb-3">
            <div
              class="w-8 h-8 rounded-full flex items-center justify-center text-white text-sm font-bold shrink-0 transition-colors"
              :class="currentStep >= idx ? 'gradient-bg' : 'bg-gray-300'"
            >
              {{ idx + 1 }}
            </div>
            <div>
              <h4 class="text-sm font-semibold text-gray-800">{{ stepNames[idx] }}</h4>
              <p class="text-xs text-gray-400">{{ stepDescs[idx] }}</p>
            </div>
          </div>

          <!-- 步骤内容 -->
          <div class="bg-gray-50 rounded-lg p-3 min-h-[140px]">
            <!-- 已完成：展示结果 -->
            <div v-if="currentStep > idx" class="space-y-2">
              <!-- Step 1: 查询处理 -->
              <template v-if="idx === 0 && stepData.step1">
                <div class="flex items-center gap-2">
                  <span class="text-xs text-gray-400">查询：</span>
                  <span class="text-sm text-gray-700 font-medium">{{ stepData.step1.query }}</span>
                </div>
                <div class="flex flex-wrap gap-1">
                  <span
                    v-for="(t, i) in (stepData.step1.tokens || [])"
                    :key="i"
                    class="text-xs bg-indigo-100 text-indigo-600 px-1.5 py-0.5 rounded"
                  >{{ t }}</span>
                </div>
                <p class="text-xs text-gray-400">Token 数：{{ stepData.step1.token_count }}</p>
                <p class="text-xs text-gray-400">耗时：{{ stepData.step1.time_ms }}ms</p>
              </template>

              <!-- Step 2: BM25 检索 -->
              <template v-else-if="idx === 1 && stepData.step2">
                <div class="flex items-center gap-2">
                  <span class="text-sm text-gray-700">BM25 检索 (rank_bm25)</span>
                </div>
                <p class="text-xs text-gray-400">召回候选文档数：{{ stepData.step2.candidates }}</p>
                <p class="text-xs text-gray-400">检索耗时：{{ stepData.step2.time_ms }}ms</p>
              </template>

              <!-- Step 3: 上下文构建 -->
              <template v-else-if="idx === 2 && stepData.step3">
                <div class="flex items-center gap-2">
                  <span class="text-sm text-gray-700">分数归一化 + Top-K 筛选</span>
                </div>
                <p class="text-xs text-gray-400">保留 Top-K：{{ stepData.step3.topK }} 条</p>
                <p class="text-xs text-gray-400">耗时：{{ stepData.step3.time_ms }}ms</p>
                <div class="flex flex-col gap-1 mt-1">
                  <div
                    v-for="(d, i) in (stepData.step3.ranked || []).slice(0, 3)"
                    :key="i"
                    class="flex items-center gap-1 bg-green-50 rounded px-2 py-1"
                  >
                    <span class="text-xs font-bold text-green-600">#{{ i + 1 }}</span>
                    <span class="text-xs text-gray-600 truncate" style="max-width: 120px">{{ d.title || '文档' + (i+1) }}</span>
                    <span class="text-xs text-green-500">{{ ((d.score || 0) * 100).toFixed(1) }}%</span>
                  </div>
                </div>
              </template>

              <!-- Step 4: 生成回答 -->
              <template v-else-if="idx === 3 && stepData.step4">
                <div class="flex items-center gap-2">
                  <span class="text-sm text-gray-700">LLM 生成回答</span>
                </div>
                <p class="text-xs text-gray-500 leading-relaxed bg-white rounded p-2 max-h-[80px] overflow-y-auto">
                  {{ (stepData.step4.answer || '').substring(0, 200) }}{{ (stepData.step4.answer || '').length > 200 ? '...' : '' }}
                </p>
                <p class="text-xs text-gray-400">模型：{{ stepData.step4.model }}</p>
                <p class="text-xs text-gray-400">耗时：{{ stepData.step4.time_ms }}ms | 字符数：{{ stepData.step4.tokens }}</p>
              </template>
            </div>

            <!-- 进行中：加载动画 -->
            <div v-else-if="currentStep === idx && running" class="flex items-center justify-center h-full">
              <span class="flex gap-1">
                <span class="w-2 h-2 bg-primary rounded-full animate-bounce" style="animation-delay:0s"></span>
                <span class="w-2 h-2 bg-primary rounded-full animate-bounce" style="animation-delay:0.2s"></span>
                <span class="w-2 h-2 bg-primary rounded-full animate-bounce" style="animation-delay:0.4s"></span>
              </span>
            </div>

            <!-- 空闲：等待查询 -->
            <div v-else class="flex items-center justify-center h-full text-gray-300">
              <span class="text-xs">等待查询</span>
            </div>
          </div>
        </div>

        <!-- 箭头 -->
        <div v-if="idx < 3" class="flex items-center justify-center w-8 shrink-0">
          <el-icon :size="18" class="text-gray-300"><ArrowRight /></el-icon>
        </div>
      </div>
    </div>

    <!-- 检索结果详情表格 -->
    <div v-if="currentStep >= 4 && stepData.retrievedDocs && stepData.retrievedDocs.length > 0" class="card-container p-5">
      <h4 class="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
        <el-icon class="text-primary"><Files /></el-icon>
        检索结果详情（共 {{ stepData.retrievedDocs.length }} 条）
      </h4>
      <el-table :data="stepData.retrievedDocs" stripe>
        <el-table-column label="排名" width="80" align="center">
          <template #default="{ $index }">
            <span class="font-bold text-primary">{{ $index + 1 }}</span>
          </template>
        </el-table-column>
        <el-table-column label="文档标题" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            <div class="flex flex-col">
              <span class="text-sm text-gray-700">{{ row.title }}</span>
              <span class="text-xs text-gray-400">{{ row.law }} {{ row.article }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="分类" width="120">
          <template #default="{ row }">
            <el-tag size="small" type="info">{{ row.category || '未分类' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="相关度" width="200">
          <template #default="{ row }">
            <div class="flex items-center gap-2">
              <el-progress
                :percentage="Math.round((row.score || 0) * 100)"
                :color="scoreColor(row.score)"
                :stroke-width="8"
                class="flex-1"
              />
              <span class="text-xs text-gray-500 w-12">{{ ((row.score || 0) * 100).toFixed(1) }}%</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="原始分数" width="100">
          <template #default="{ row }">
            <span class="text-xs text-gray-400">{{ row.raw_score }}</span>
          </template>
        </el-table-column>
        <el-table-column label="内容片段" min-width="300" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="text-xs text-gray-500">{{ row.snippet }}</span>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 空结果提示 -->
    <div v-if="currentStep >= 4 && stepData.retrievedDocs && stepData.retrievedDocs.length === 0" class="card-container p-5 text-center">
      <el-icon :size="40" class="text-gray-300 mb-2"><Files /></el-icon>
      <p class="text-sm text-gray-400">知识库为空或未检索到相关文档</p>
      <p class="text-xs text-gray-300 mt-1">请先在「知识库管理」页面上传法律文档</p>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, ArrowRight, Files } from '@element-plus/icons-vue'
import request from '../api/index'

const queryText = ref('')
const running = ref(false)
const currentStep = ref(-1)
const pipelineInfo = ref(null)

const stepData = reactive({
  step1: null,
  step2: null,
  step3: null,
  step4: null,
  retrievedDocs: null
})

const stepNames = ['查询处理', 'BM25 检索', '上下文构建', '生成回答']
const stepDescs = ['分词与查询构建', '从知识库中召回 Top-K 文档', '归一化排序，选 Top-K', 'LLM 基于上下文生成']

function scoreColor(score) {
  const s = score || 0
  if (s >= 0.8) return '#10B981'
  if (s >= 0.6) return '#F59E0B'
  return '#EF4444'
}

async function runRetrieval() {
  if (!queryText.value.trim()) {
    ElMessage.warning('请输入查询语句')
    return
  }

  running.value = true
  currentStep.value = -1
  pipelineInfo.value = null
  stepData.step1 = null
  stepData.step2 = null
  stepData.step3 = null
  stepData.step4 = null
  stepData.retrievedDocs = null

  try {
    const res = await request.post('/qa/debug', {
      question: queryText.value,
      top_k: 10
    }, {
      timeout: 120000
    })

    // res 已经是 response.data（拦截器返回的）
    const data = res.data || res

    console.log('检索调试返回数据：', data)

    // 设置管线信息
    pipelineInfo.value = data.pipeline_info

    // 逐步展示结果
    const stepKeys = ['step1_query', 'step2_retrieval', 'step3_context', 'step4_generation']
    const localKeys = ['step1', 'step2', 'step3', 'step4']

    for (let i = 0; i < 4; i++) {
      currentStep.value = i
      await new Promise((r) => setTimeout(r, 500))
      stepData[localKeys[i]] = data[stepKeys[i]]
    }

    stepData.retrievedDocs = data.retrieved_docs || []
    currentStep.value = 4
    ElMessage.success('检索流程完成')
  } catch (error) {
    console.error('检索调试失败：', error)
    ElMessage.error(error.message || '检索调试失败，请检查后端服务是否正常运行')
    currentStep.value = -1
  } finally {
    running.value = false
  }
}
</script>

<style scoped>
</style>
