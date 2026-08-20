<template>
  <!-- 数据分析页面：四宫格图表，用 ECharts -->
  <div class="h-full p-4 overflow-y-auto custom-scrollbar">
    <!-- 页面标题 + 统计概览 -->
    <div class="flex items-center justify-between mb-5">
      <div>
        <h2 class="page-title">数据分析</h2>
        <p class="text-sm text-gray-400 mt-1">系统运行数据统计与分析</p>
      </div>
      <div class="flex items-center gap-2">
        <el-button :icon="Refresh" :loading="loading" @click="loadAll">刷新</el-button>
      </div>
    </div>

    <!-- 概览数字 -->
    <div class="grid grid-cols-4 gap-4 mb-5">
      <div v-for="item in overviewStats" :key="item.label"
        class="card-container p-5 flex items-center gap-4">
        <div class="w-12 h-12 rounded-xl flex items-center justify-center shrink-0" :class="item.bgClass">
          <el-icon :size="24" :color="item.color"><component :is="item.icon" /></el-icon>
        </div>
        <div>
          <div class="text-2xl font-bold text-gray-800">{{ item.value }}</div>
          <div class="text-xs text-gray-400 mt-0.5">{{ item.label }}</div>
        </div>
      </div>
    </div>

    <!-- 四宫格图表 -->
    <div class="grid grid-cols-2 gap-4">
      <!-- 图表1：问答趋势 -->
      <div class="card-container p-5">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-sm font-semibold text-gray-700 flex items-center gap-2">
            <el-icon class="text-primary"><TrendCharts /></el-icon>
            问答趋势分析
          </h3>
          <el-tag size="small" effect="plain">近30天</el-tag>
        </div>
        <div ref="trendChartRef" style="height: 280px;"></div>
        <div v-if="trendEmpty" class="text-center text-sm text-gray-400 py-8">暂无问答数据</div>
      </div>

      <!-- 图表2：问题分类分布 -->
      <div class="card-container p-5">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-sm font-semibold text-gray-700 flex items-center gap-2">
            <el-icon class="text-secondary"><PieChart /></el-icon>
            问题分类分布
          </h3>
          <el-tag size="small" effect="plain">按法律领域</el-tag>
        </div>
        <div ref="categoryChartRef" style="height: 280px;"></div>
        <div v-if="categoryEmpty" class="text-center text-sm text-gray-400 py-8">暂无分类数据</div>
      </div>

      <!-- 图表3：用户活跃度 -->
      <div class="card-container p-5">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-sm font-semibold text-gray-700 flex items-center gap-2">
            <el-icon class="text-primary"><Histogram /></el-icon>
            用户活跃度
          </h3>
          <el-tag size="small" effect="plain">按时段</el-tag>
        </div>
        <div ref="activityChartRef" style="height: 280px;"></div>
        <div v-if="activityEmpty" class="text-center text-sm text-gray-400 py-8">暂无活跃度数据</div>
      </div>

      <!-- 图表4：检索质量指标 -->
      <div class="card-container p-5">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-sm font-semibold text-gray-700 flex items-center gap-2">
            <el-icon class="text-secondary"><DataLine /></el-icon>
            检索质量指标
          </h3>
          <el-tag size="small" effect="plain">多维度评估</el-tag>
        </div>
        <div ref="qualityChartRef" style="height: 280px;"></div>
        <div v-if="qualityEmpty" class="text-center text-sm text-gray-400 py-8">暂无质量指标数据</div>
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * 数据分析页面
 * 所有数据均从后端接口实时获取，不使用任何写死的模拟数据
 * 四宫格图表：问答趋势 + 问题分类分布 + 用户活跃度 + 检索质量指标
 */
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import {
  Refresh, TrendCharts, PieChart, Histogram, DataLine,
  ChatLineRound, User, Document
} from '@element-plus/icons-vue'
import {
  getAnalytics, getQaTrend, getHotCategories,
  getUserActivity, getRetrievalMetrics
} from '../api/analytics'

// 图表 DOM 引用
const trendChartRef = ref(null)
const categoryChartRef = ref(null)
const activityChartRef = ref(null)
const qualityChartRef = ref(null)

// ECharts 实例
let trendChart = null
let categoryChart = null
let activityChart = null
let qualityChart = null

const loading = ref(false)

// 空数据提示
const trendEmpty = ref(false)
const categoryEmpty = ref(false)
const activityEmpty = ref(false)
const qualityEmpty = ref(false)

// 概览统计（初始为 -- 占位，从后端获取后填充）
const overviewStats = ref([
  { label: '累计问答数', value: '--', icon: ChatLineRound, bgClass: 'bg-primary-50', color: '#4F46E5' },
  { label: '活跃用户数', value: '--', icon: User, bgClass: 'bg-secondary-50', color: '#06B6D4' },
  { label: '知识库文档', value: '--', icon: Document, bgClass: 'bg-green-50', color: '#10B981' },
  { label: '研判总数', value: '--', icon: DataLine, bgClass: 'bg-amber-50', color: '#F59E0B' }
])

onMounted(() => {
  nextTick(() => {
    initCharts()
    loadAll()
  })
})

onUnmounted(() => {
  trendChart?.dispose()
  categoryChart?.dispose()
  activityChart?.dispose()
  qualityChart?.dispose()
  window.removeEventListener('resize', handleResize)
})

window.addEventListener('resize', handleResize)

function handleResize() {
  trendChart?.resize()
  categoryChart?.resize()
  activityChart?.resize()
  qualityChart?.resize()
}

// 初始化图表
function initCharts() {
  trendChart = echarts.init(trendChartRef.value)
  categoryChart = echarts.init(categoryChartRef.value)
  activityChart = echarts.init(activityChartRef.value)
  qualityChart = echarts.init(qualityChartRef.value)
}

// 加载所有数据（全部从后端实时获取）
async function loadAll() {
  loading.value = true
  try {
    await Promise.all([
      loadOverview(),
      loadTrend(),
      loadCategories(),
      loadActivity(),
      loadQuality()
    ])
  } catch (e) {
    // 已在各自函数中处理错误
  } finally {
    loading.value = false
  }
}

// 加载概览数据
async function loadOverview() {
  try {
    const res = await getAnalytics()
    if (res) {
      overviewStats.value[0].value = res.totalQuestions?.toLocaleString() || '0'
      overviewStats.value[1].value = res.totalUsers?.toLocaleString() || '0'
      overviewStats.value[2].value = res.totalDocuments?.toString() || '0'
      overviewStats.value[3].value = res.totalJudgments?.toString() || '0'
    }
  } catch (e) {
    overviewStats.value.forEach(s => s.value = '0')
  }
}

// 加载问答趋势
async function loadTrend() {
  try {
    const res = await getQaTrend({ days: 30 })
    const dates = res.dates || []
    const questions = res.questions || []
    const users = res.users || []

    if (dates.length === 0) {
      trendEmpty.value = true
      trendChart?.setOption({ series: [] })
      return
    }
    trendEmpty.value = false

    trendChart?.setOption({
      tooltip: { trigger: 'axis' },
      legend: { data: ['提问数', '活跃用户'], bottom: 0 },
      grid: { top: 20, left: 50, right: 20, bottom: 40 },
      xAxis: { type: 'category', data: dates, axisLabel: { fontSize: 10, interval: Math.ceil(dates.length / 8) } },
      yAxis: { type: 'value', axisLabel: { fontSize: 10 } },
      series: [
        {
          name: '提问数', type: 'line', smooth: true, data: questions,
          itemStyle: { color: '#4F46E5' },
          areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(79, 70, 229, 0.25)' },
            { offset: 1, color: 'rgba(79, 70, 229, 0.01)' }
          ]) }
        },
        {
          name: '活跃用户', type: 'line', smooth: true, data: users,
          itemStyle: { color: '#06B6D4' },
          areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(6, 182, 212, 0.25)' },
            { offset: 1, color: 'rgba(6, 182, 212, 0.01)' }
          ]) }
        }
      ]
    })
  } catch (e) {
    trendEmpty.value = true
    trendChart?.setOption({ series: [] })
  }
}

// 加载问题分类
async function loadCategories() {
  try {
    const res = await getHotCategories()
    const data = res || []

    if (!data.length || data.every(d => d.value === 0)) {
      categoryEmpty.value = true
      categoryChart?.setOption({ series: [] })
      return
    }
    categoryEmpty.value = false

    categoryChart?.setOption({
      tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
      legend: { bottom: 0, type: 'scroll', fontSize: 10 },
      series: [{
        type: 'pie', radius: ['40%', '70%'], center: ['50%', '45%'],
        avoidLabelOverlap: false,
        itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
        label: { show: false },
        emphasis: { label: { show: true, fontSize: 14, fontWeight: 'bold' } },
        data: data,
        color: ['#4F46E5', '#06B6D4', '#818CF8', '#22D3EE', '#A5B4FC', '#67E8F9']
      }]
    })
  } catch (e) {
    categoryEmpty.value = true
    categoryChart?.setOption({ series: [] })
  }
}

// 加载用户活跃度
async function loadActivity() {
  try {
    const res = await getUserActivity()
    const labels = res.labels || ['0-2','2-4','4-6','6-8','8-10','10-12','12-14','14-16','16-18','18-20','20-22','22-24']
    const counts = res.counts || []

    if (counts.length === 0 || counts.every(c => c === 0)) {
      activityEmpty.value = true
      activityChart?.setOption({ series: [] })
      return
    }
    activityEmpty.value = false

    activityChart?.setOption({
      tooltip: { trigger: 'axis' },
      grid: { top: 20, left: 50, right: 20, bottom: 30 },
      xAxis: { type: 'category', data: labels, axisLabel: { fontSize: 10 } },
      yAxis: { type: 'value', axisLabel: { fontSize: 10 } },
      series: [{
        type: 'bar', data: counts, barWidth: '60%',
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#4F46E5' },
            { offset: 1, color: '#06B6D4' }
          ]),
          borderRadius: [4, 4, 0, 0]
        }
      }]
    })
  } catch (e) {
    activityEmpty.value = true
    activityChart?.setOption({ series: [] })
  }
}

// 加载检索质量指标
async function loadQuality() {
  try {
    const res = await getRetrievalMetrics()
    const indicators = res.indicators || []

    if (indicators.length === 0) {
      qualityEmpty.value = true
      qualityChart?.setOption({ series: [] })
      return
    }
    qualityEmpty.value = false

    const names = indicators.map(i => i.name)
    const values = indicators.map(i => i.value)

    qualityChart?.setOption({
      tooltip: {},
      radar: {
        indicator: names.map(n => ({ name: n, max: 100 })),
        radius: '65%',
        axisName: { fontSize: 11, color: '#6b7280' }
      },
      series: [{
        type: 'radar',
        data: [{
          value: values, name: '检索质量',
          areaStyle: { color: 'rgba(79, 70, 229, 0.2)' },
          lineStyle: { color: '#4F46E5' },
          itemStyle: { color: '#4F46E5' }
        }]
      }]
    })
  } catch (e) {
    qualityEmpty.value = true
    qualityChart?.setOption({ series: [] })
  }
}
</script>

<style scoped>
</style>