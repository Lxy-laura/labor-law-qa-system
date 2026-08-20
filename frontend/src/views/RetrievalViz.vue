<template>
  <!-- 检索可视化页面：四步管线展示 -->
  <div class="h-full p-4 overflow-y-auto custom-scrollbar">
    <!-- 页面标题 -->
    <div class="mb-5">
      <h2 class="page-title">检索可视化</h2>
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
            placeholder="输入查询语句，查看 RAG 检索全流程..."
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

    <!-- 四步管线 -->
    <div class="flex items-stretch gap-0 mb-5">
      <div
        v-for="(step, idx) in pipelineSteps"
        :key="step.name"
        class="flex items-stretch flex-1"
      >
        <!-- 步骤卡片 -->
        <div
          class="flex-1 card-container p-4 transition-all duration-300"
          :class="
            currentStep >= idx
              ? 'border-primary-300 shadow-card-hover'
              : 'opacity-60'
          "
        >
          <div class="flex items-center gap-3 mb-3">
            <div
              class="w-8 h-8 rounded-full flex items-center justify-center text-white text-sm font-bold shrink-0 transition-colors"
              :class="currentStep >= idx ? 'gradient-bg' : 'bg-gray-300'"
            >
              {{ idx + 1 }}
            </div>
            <div>
              <h4 class="text-sm font-semibold text-gray-800">{{ step.name }}</h4>
              <p class="text-xs text-gray-400">{{ step.desc }}</p>
            </div>
          </div>

          <!-- 步骤内容 -->
          <div class="bg-gray-50 rounded-lg p-3 min-h-[120px]">
            <template v-if="currentStep > idx">
              <!-- 已完成步骤展示结果 -->
              <component :is="step.component" :data="stepData[step.key]" />
            </template>
            <template v-else-if="currentStep === idx && running">
              <div class="flex items-center justify-center h-full">
                <span class="flex gap-1">
                  <span class="w-2 h-2 bg-primary rounded-full animate-bounce" style="animation-delay:0s"></span>
                  <span class="w-2 h-2 bg-primary rounded-full animate-bounce" style="animation-delay:0.2s"></span>
                  <span class="w-2 h-2 bg-primary rounded-full animate-bounce" style="animation-delay:0.4s"></span>
                </span>
              </div>
            </template>
            <template v-else>
              <div class="flex items-center justify-center h-full text-gray-300">
                <el-icon :size="24"><Loading /></el-icon>
              </div>
            </template>
          </div>
        </div>

        <!-- 箭头 -->
        <div v-if="idx < pipelineSteps.length - 1" class="flex items-center justify-center w-8 shrink-0">
          <el-icon :size="18" class="text-gray-300"><ArrowRight /></el-icon>
        </div>
      </div>
    </div>

    <!-- 检索结果详情 -->
    <div v-if="currentStep >= 3 && stepData.retrievedDocs" class="card-container p-5">
      <h4 class="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
        <el-icon class="text-primary"><Files /></el-icon>
        检索结果详情
      </h4>
      <el-table :data="stepData.retrievedDocs" stripe>
        <el-table-column label="排名" width="80" align="center">
          <template #default="{ $index }">
            <span class="font-bold text-primary">{{ $index + 1 }}</span>
          </template>
        </el-table-column>
        <el-table-column label="文档标题" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="text-sm text-gray-700">{{ row.title }}</span>
          </template>
        </el-table-column>
        <el-table-column label="相似度" width="200">
          <template #default="{ row }">
            <div class="flex items-center gap-2">
              <el-progress
                :percentage="Math.round((row.score || row.relevance || 0) * 100)"
                :color="scoreColor(row.score || row.relevance)"
                :stroke-width="8"
                class="flex-1"
              />
              <span class="text-xs text-gray-500 w-10">{{ ((row.score || row.relevance || 0) * 100).toFixed(1) }}%</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="内容片段" min-width="300" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="text-xs text-gray-500">{{ row.snippet || row.content }}</span>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup>
/**
 * 检索可视化页面
 * 展示 RAG 四步管线：查询向量化 -> 向量检索 -> 重排序 -> 生成回答
 */
import { ref, reactive, h } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Search,
  ArrowRight,
  Loading,
  Files,
  Document,
  Connection,
  Sort,
  EditPen
} from '@element-plus/icons-vue'
import request from '../api/index'

const queryText = ref('')
const running = ref(false)
const currentStep = ref(-1)

const stepData = reactive({
  embedding: null,
  retrieval: null,
  rerank: null,
  generation: null,
  retrievedDocs: null
})

// 四步管线定义
const pipelineSteps = [
  {
    name: '查询向量化',
    desc: '将用户问题编码为向量',
    key: 'embedding',
    component: {
      render() {
        return h('div', { class: 'space-y-2' }, [
          h('div', { class: 'flex items-center gap-2' }, [
            h('span', { class: 'text-xs text-gray-400' }, '输入查询：'),
            h('span', { class: 'text-sm text-gray-700 font-medium' }, this.data?.query || '-')
          ]),
          h('div', { class: 'flex flex-wrap gap-1' },
            (this.data?.vector || [0.123, -0.456, 0.789, 0.012, -0.345]).slice(0, 8).map((v, i) =>
              h('span', { key: i, class: 'text-xs bg-primary-100 text-primary px-1.5 py-0.5 rounded' }, v.toFixed(3))
            )
          ),
          h('p', { class: 'text-xs text-gray-400' }, `向量维度：${this.data?.dim || 768}`)
        ])
      },
      props: ['data']
    }
  },
  {
    name: '向量检索',
    desc: '从知识库中召回 Top-K 文档',
    key: 'retrieval',
    component: {
      render() {
        const docs = this.data?.candidates || 5
        return h('div', { class: 'space-y-2' }, [
          h('div', { class: 'flex items-center gap-2' }, [
            h('el-icon', { color: '#06B6D4' }, [h(Connection)]),
            h('span', { class: 'text-sm text-gray-700' }, `检索知识库 (Faiss)`)
          ]),
          h('p', { class: 'text-xs text-gray-400' }, `召回候选文档数：${docs}`),
          h('p', { class: 'text-xs text-gray-400' }, `检索耗时：${this.data?.time || '45ms'}`)
        ])
      },
      props: ['data']
    }
  },
  {
    name: '重排序',
    desc: '对候选结果精排',
    key: 'rerank',
    component: {
      render() {
        return h('div', { class: 'space-y-2' }, [
          h('div', { class: 'flex items-center gap-2' }, [
            h('el-icon', { color: '#F59E0B' }, [h(Sort)]),
            h('span', { class: 'text-sm text-gray-700' }, 'Cross-Encoder 精排')
          ]),
          h('p', { class: 'text-xs text-gray-400' }, `重排后保留：${this.data?.topK || 3} 条`),
          h('div', { class: 'flex gap-2' },
            (this.data?.ranked || []).map((d, i) =>
              h('div', { key: i, class: 'flex items-center gap-1 bg-green-50 rounded px-2 py-1' }, [
                h('span', { class: 'text-xs font-bold text-green-600' }, `#${i + 1}`),
                h('span', { class: 'text-xs text-gray-600 truncate max-w-[120px]' }, d.title || `文档${i + 1}`),
                h('span', { class: 'text-xs text-green-500' }, `${((d.score || 0.9 - i * 0.1) * 100).toFixed(1)}%`)
              ])
            )
          )
        ])
      },
      props: ['data']
    }
  },
  {
    name: '生成回答',
    desc: 'LLM 基于上下文生成',
    key: 'generation',
    component: {
      render() {
        return h('div', { class: 'space-y-2' }, [
          h('div', { class: 'flex items-center gap-2' }, [
            h('el-icon', { color: '#4F46E5' }, [h(EditPen)]),
            h('span', { class: 'text-sm text-gray-700' }, 'LLM 生成回答')
          ]),
          h('p', { class: 'text-xs text-gray-500 leading-relaxed bg-white rounded p-2' },
            this.data?.answer || '基于检索到的法律条文和案例，为您生成回答...'
          ),
          h('p', { class: 'text-xs text-gray-400' }, `生成耗时：${this.data?.time || '1.2s'} | Token：${this.data?.tokens || 256}`)
        ])
      },
      props: ['data']
    }
  }
]

// 分数颜色
function scoreColor(score) {
  const s = score || 0
  if (s >= 0.8) return '#10B981'
  if (s >= 0.6) return '#F59E0B'
  return '#EF4444'
}

// 运行检索
async function runRetrieval() {
  if (!queryText.value.trim()) {
    ElMessage.warning('请输入查询语句')
    return
  }

  running.value = true
  currentStep.value = -1
  Object.keys(stepData).forEach((k) => (stepData[k] = null))

  // 模拟逐步执行
  const steps = ['embedding', 'retrieval', 'rerank', 'generation']
  for (let i = 0; i < steps.length; i++) {
    currentStep.value = i
    await new Promise((r) => setTimeout(r, 800))

    if (i === 0) {
      stepData.embedding = {
        query: queryText.value,
        vector: Array.from({ length: 8 }, () => (Math.random() * 2 - 1)),
        dim: 768,
        time: '12ms'
      }
    } else if (i === 1) {
      stepData.retrieval = {
        candidates: 10,
        time: '45ms'
      }
    } else if (i === 2) {
      stepData.rerank = {
        topK: 3,
        ranked: [
          { title: '劳动合同法第三十条', score: 0.92 },
          { title: '工资支付暂行规定', score: 0.85 },
          { title: '最高人民法院司法解释', score: 0.71 }
        ]
      }
    } else if (i === 3) {
      stepData.generation = {
        answer: '根据《劳动合同法》第三十条规定，用人单位应当按照劳动合同约定和国家规定，向劳动者及时足额支付劳动报酬...',
        time: '1.2s',
        tokens: 256
      }
      stepData.retrievedDocs = stepData.rerank.ranked.map((d) => ({
        ...d,
        snippet: '用人单位应当按照劳动合同约定和国家规定，向劳动者及时足额支付劳动报酬。用人单位拖欠或者未足额支付劳动报酬的...'
      }))
    }
  }

  currentStep.value = 4
  running.value = false
  ElMessage.success('检索流程完成')
}
</script>

<style scoped>
</style>
