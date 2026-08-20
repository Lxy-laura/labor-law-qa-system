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
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          class="!w-64"
          @change="loadAll"
        />
        <el-button :icon="Refresh" @click="loadAll">刷新</el-button>
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
          <div class="text-xs mt-0.5" :class="item.trend > 0 ? 'text-green-500' : 'text-red-500'">
            {{ item.trend > 0 ? '+' : '' }}{{ item.trend }}% 较上周
          </div>
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
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * 数据分析页面
 * 四宫格图表：问答趋势 + 问题分类分布 + 用户活跃度 + 检索质量指标
 * 使用 ECharts 渲染
 */
import { ref, reactive, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import {
  Refresh,
  TrendCharts,
  PieChart,
  Histogram,
  DataLine,
  ChatLineRound,
  User,
  Document
} from '@element-plus/icons-vue'
import { getAnalytics } from '../api/analytics'

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

const dateRange = ref([])

// 概览统计
const overviewStats = ref([
  { label: '累计问答数', value: '12,586', trend: 12.5, icon: ChatLineRound, bgClass: 'bg-primary-50', color: '#4F46E5' },
  { label: '活跃用户数', value: '3,247', trend: 8.3, icon: User, bgClass: 'bg-secondary-50', color: '#06B6D4' },
  { label: '知识库文档', value: '856', trend: 3.2, icon: Document, bgClass: 'bg-green-50', color: '#10B981' },
  { label: '平均响应时间', value: '1.3s', trend: -5.6, icon: DataLine, bgClass: 'bg-amber-50', color: '#F59E0B' }
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

// 加载所有数据
async function loadAll() {
  // 尝试从后端获取数据，失败则使用模拟数据
  try {
    const res = await getAnalytics()
    if (res) {
      updateOverview(res)
      renderTrendChart(res.trend)
      renderCategoryChart(res.categories)
      renderActivityChart(res.activity)
      renderQualityChart(res.quality)
      return
    }
  } catch (e) {
    // 使用模拟数据
  }

  // 模拟数据
  renderTrendChart()
  renderCategoryChart()
  renderActivityChart()
  renderQualityChart()
}

// 更新概览
function updateOverview(data) {
  if (!data) return
  overviewStats.value[0].value = data.totalQuestions?.toLocaleString() || overviewStats.value[0].value
  overviewStats.value[1].value = data.totalUsers?.toLocaleString() || overviewStats.value[1].value
  overviewStats.value[2].value = data.totalDocuments?.toString() || overviewStats.value[2].value
  overviewStats.value[3].value = data.avgResponseTime || overviewStats.value[3].value
}

// 图表1：问答趋势（折线图）
function renderTrendChart(data) {
  const days = Array.from({ length: 30 }, (_, i) => `${i + 1}日`)
  const questions = data?.questions || Array.from({ length: 30 }, () => Math.floor(Math.random() * 200 + 100))
  const users = data?.users || Array.from({ length: 30 }, () => Math.floor(Math.random() * 80 + 20))

  trendChart?.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['提问数', '活跃用户'], bottom: 0 },
    grid: { top: 20, left: 50, right: 20, bottom: 40 },
    xAxis: { type: 'category', data: days, axisLabel: { fontSize: 10, interval: 4 } },
    yAxis: { type: 'value', axisLabel: { fontSize: 10 } },
    series: [
      {
        name: '提问数',
        type: 'line',
        smooth: true,
        data: questions,
        itemStyle: { color: '#4F46E5' },
        areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(79, 70, 229, 0.25)' },
          { offset: 1, color: 'rgba(79, 70, 229, 0.01)' }
        ]) }
      },
      {
        name: '活跃用户',
        type: 'line',
        smooth: true,
        data: users,
        itemStyle: { color: '#06B6D4' },
        areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(6, 182, 212, 0.25)' },
          { offset: 1, color: 'rgba(6, 182, 212, 0.01)' }
        ]) }
      }
    ]
  })
}

// 图表2：问题分类分布（饼图）
function renderCategoryChart(data) {
  const categoryData = data || [
    { name: '工资报酬', value: 3580 },
    { name: '解除终止', value: 2940 },
    { name: '社保公积金', value: 2100 },
    { name: '工时休假', value: 1560 },
    { name: '调岗调薪', value: 1280 },
    { name: '其他', value: 1126 }
  ]

  categoryChart?.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { bottom: 0, type: 'scroll', fontSize: 10 },
    series: [
      {
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['50%', '45%'],
        avoidLabelOverlap: false,
        itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
        label: { show: false },
        emphasis: { label: { show: true, fontSize: 14, fontWeight: 'bold' } },
        data: categoryData,
        color: ['#4F46E5', '#06B6D4', '#818CF8', '#22D3EE', '#A5B4FC', '#67E8F9']
      }
    ]
  })
}

// 图表3：用户活跃度（柱状图）
function renderActivityChart(data) {
  const hours = ['0-2', '2-4', '4-6', '6-8', '8-10', '10-12', '12-14', '14-16', '16-18', '18-20', '20-22', '22-24']
  const counts = data || [15, 8, 5, 30, 180, 350, 220, 310, 280, 400, 250, 80]

  activityChart?.setOption({
    tooltip: { trigger: 'axis' },
    grid: { top: 20, left: 50, right: 20, bottom: 30 },
    xAxis: { type: 'category', data: hours, axisLabel: { fontSize: 10 } },
    yAxis: { type: 'value', axisLabel: { fontSize: 10 } },
    series: [
      {
        type: 'bar',
        data: counts,
        barWidth: '60%',
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#4F46E5' },
            { offset: 1, color: '#06B6D4' }
          ]),
          borderRadius: [4, 4, 0, 0]
        }
      }
    ]
  })
}

// 图表4：检索质量指标（雷达图）
function renderQualityChart(data) {
  const radarData = data || [85, 78, 92, 88, 76, 90]

  qualityChart?.setOption({
    tooltip: {},
    radar: {
      indicator: [
        { name: '召回率', max: 100 },
        { name: '准确率', max: 100 },
        { name: '响应速度', max: 100 },
        { name: '答案相关度', max: 100 },
        { name: '引用准确率', max: 100 },
        { name: '用户满意度', max: 100 }
      ],
      radius: '65%',
      axisName: { fontSize: 11, color: '#6b7280' }
    },
    series: [
      {
        type: 'radar',
        data: [
          {
            value: radarData,
            name: '检索质量',
            areaStyle: { color: 'rgba(79, 70, 229, 0.2)' },
            lineStyle: { color: '#4F46E5' },
            itemStyle: { color: '#4F46E5' }
          }
        ]
      }
    ]
  })
}
</script>

<style scoped>
</style>
