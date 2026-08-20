<template>
  <!-- 信息研判页面：左侧上传/粘贴 + 右侧风险报告 -->
  <div class="flex h-full gap-4 p-4">
    <!-- ===== 左侧：输入区 ===== -->
    <div class="w-[420px] shrink-0 flex flex-col">
      <div class="card-container flex flex-col h-full overflow-hidden">
        <!-- 标题 -->
        <div class="px-5 py-4 border-b border-gray-100">
          <h3 class="text-base font-semibold text-gray-800 flex items-center gap-2">
            <el-icon class="text-primary"><DocumentChecked /></el-icon>
            合同文本输入
          </h3>
        </div>

        <!-- Tab 切换 -->
        <div class="p-4 flex-1 flex flex-col overflow-hidden">
          <el-tabs v-model="inputTab" class="flex-1 flex flex-col">
            <!-- 粘贴文本 -->
            <el-tab-pane label="粘贴文本" name="paste">
              <el-input
                v-model="contractText"
                type="textarea"
                :rows="16"
                placeholder="请粘贴劳动合同全文内容，或关键条款段落..."
                resize="none"
                class="w-full"
              />
            </el-tab-pane>

            <!-- 上传文件 -->
            <el-tab-pane label="上传文件" name="upload">
              <div
                class="flex flex-col items-center justify-center border-2 border-dashed border-gray-300 rounded-xl py-12 px-6 cursor-pointer transition-colors hover:border-primary-400 hover:bg-primary-50"
                @click="triggerUpload"
                @drop.prevent="handleDrop"
                @dragover.prevent
              >
                <el-icon :size="48" class="text-gray-300 mb-3"><UploadFilled /></el-icon>
                <p class="text-sm text-gray-500 mb-1">点击或拖拽文件到此处上传</p>
                <p class="text-xs text-gray-400">支持 .txt / .docx / .pdf 格式，最大 10MB</p>
              </div>
              <input
                ref="fileInputRef"
                type="file"
                class="hidden"
                accept=".txt,.docx,.pdf"
                @change="handleFileChange"
              />
              <!-- 已选文件信息 -->
              <div v-if="selectedFile" class="mt-4 flex items-center gap-2 bg-gray-50 rounded-lg p-3">
                <el-icon class="text-primary"><Document /></el-icon>
                <span class="text-sm text-gray-700 flex-1 truncate">{{ selectedFile.name }}</span>
                <span class="text-xs text-gray-400">{{ formatFileSize(selectedFile.size) }}</span>
                <el-icon class="text-gray-400 cursor-pointer hover:text-red-500" @click="clearFile"><Close /></el-icon>
              </div>
            </el-tab-pane>
          </el-tabs>
        </div>

        <!-- 操作按钮 -->
        <div class="p-4 border-t border-gray-100">
          <el-button
            type="primary"
            class="w-full"
            size="large"
            :loading="analyzing"
            :icon="Search"
            @click="startAnalyze"
          >
            {{ analyzing ? '分析中...' : '开始风险研判' }}
          </el-button>
          <el-button class="w-full mt-2" @click="loadSample">加载示例合同</el-button>
        </div>
      </div>
    </div>

    <!-- ===== 右侧：风险报告 ===== -->
    <div class="flex-1 flex flex-col min-w-0">
      <div class="card-container flex flex-col h-full overflow-hidden">
        <!-- 报告标题 -->
        <div class="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
          <h3 class="text-base font-semibold text-gray-800 flex items-center gap-2">
            <el-icon class="text-primary"><DataAnalysis /></el-icon>
            风险研判报告
          </h3>
          <el-button v-if="report" text :icon="Download" @click="exportReport">导出报告</el-button>
        </div>

        <!-- 报告内容 -->
        <div class="flex-1 overflow-y-auto custom-scrollbar p-5">
          <!-- 空状态 -->
          <div v-if="!report" class="flex flex-col items-center justify-center h-full text-gray-400">
            <el-icon :size="56"><DocumentChecked /></el-icon>
            <p class="text-sm mt-3">请输入或上传合同文本后开始研判</p>
            <p class="text-xs mt-1">系统将逐条分析条款风险并生成报告</p>
          </div>

          <template v-else>
            <!-- 风险概览 -->
            <div class="mb-5">
              <h4 class="text-sm font-semibold text-gray-600 mb-3">风险概览</h4>
              <div class="grid grid-cols-3 gap-4">
                <div
                  v-for="item in riskSummary"
                  :key="item.label"
                  class="rounded-xl p-4 text-center"
                  :class="item.bgClass"
                >
                  <div class="text-3xl font-bold" :class="item.textClass">{{ item.count }}</div>
                  <div class="text-xs mt-1" :class="item.textClass">{{ item.label }}</div>
                </div>
              </div>
            </div>

            <!-- 综合结论 -->
            <div class="mb-5 card-container p-4 border-l-4" :class="overallRiskBorder">
              <div class="flex items-center gap-2 mb-2">
                <el-icon :color="overallRiskColor"><Warning /></el-icon>
                <h4 class="text-sm font-semibold text-gray-700">综合结论</h4>
              </div>
              <p class="text-sm text-gray-600 leading-relaxed">{{ report.conclusion }}</p>
              <div class="flex items-center gap-2 mt-3">
                <span class="text-xs text-gray-400">综合风险等级：</span>
                <el-tag :type="overallRiskTag" effect="dark">
                  {{ report.riskLevel }}
                </el-tag>
              </div>
            </div>

            <!-- 逐条条款分析 -->
            <div>
              <h4 class="text-sm font-semibold text-gray-600 mb-3">逐条条款分析</h4>
              <div
                v-for="(clause, idx) in report.clauses"
                :key="idx"
                class="card-container mb-3 overflow-hidden"
              >
                <!-- 条款标题 -->
                <div class="flex items-center justify-between px-4 py-3 border-b border-gray-50 cursor-pointer hover:bg-gray-50"
                  @click="toggleClause(idx)"
                >
                  <div class="flex items-center gap-2">
                    <el-tag :type="riskTagType(clause.riskLevel)" size="small" effect="dark">
                      {{ clause.riskLevel }}
                    </el-tag>
                    <span class="text-sm font-medium text-gray-700">{{ clause.title }}</span>
                  </div>
                  <el-icon class="text-gray-400 transition-transform" :class="{ 'rotate-180': expandedClauses.has(idx) }">
                    <ArrowDown />
                  </el-icon>
                </div>

                <!-- 条款详情 -->
                <div v-show="expandedClauses.has(idx)" class="px-4 py-3">
                  <!-- 原文 -->
                  <div class="mb-3">
                    <p class="text-xs text-gray-400 mb-1">合同原文</p>
                    <p class="text-sm text-gray-600 bg-gray-50 rounded-lg p-3 leading-relaxed">"{{ clause.text }}"</p>
                  </div>
                  <!-- 风险说明 -->
                  <div class="mb-3">
                    <p class="text-xs text-gray-400 mb-1">风险说明</p>
                    <p class="text-sm text-gray-600 leading-relaxed">{{ clause.analysis }}</p>
                  </div>
                  <!-- 法律依据 -->
                  <div v-if="clause.legalBasis" class="mb-3">
                    <p class="text-xs text-gray-400 mb-1">法律依据</p>
                    <div class="flex flex-wrap gap-2">
                      <el-tag
                        v-for="(law, lIdx) in clause.legalBasis"
                        :key="lIdx"
                        size="small"
                        type="warning"
                        effect="plain"
                      >
                        {{ law }}
                      </el-tag>
                    </div>
                  </div>
                  <!-- 修改建议 -->
                  <div v-if="clause.suggestion" class="bg-green-50 rounded-lg p-3">
                    <p class="text-xs text-green-600 mb-1 flex items-center gap-1">
                      <el-icon><CircleCheck /></el-icon>
                      修改建议
                    </p>
                    <p class="text-sm text-gray-600 leading-relaxed">{{ clause.suggestion }}</p>
                  </div>
                </div>
              </div>
            </div>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * 信息研判页面
 * 左侧上传/粘贴合同 + 右侧风险报告
 * 展示：风险概览（高/中/合规数量）、逐条条款分析、综合结论
 */
import { ref, reactive, computed } from 'vue'
import { ElMessage } from 'element-plus'
import {
  DocumentChecked,
  UploadFilled,
  Document,
  Close,
  Search,
  DataAnalysis,
  Warning,
  ArrowDown,
  CircleCheck,
  Download
} from '@element-plus/icons-vue'
import { analyzeContract, uploadAndAnalyze } from '../api/judge'

const inputTab = ref('paste')
const contractText = ref('')
const selectedFile = ref(null)
const fileInputRef = ref(null)
const analyzing = ref(false)
const report = ref(null)
const expandedClauses = reactive(new Set())

// 示例合同文本
const sampleContract = `甲方：XX科技有限公司
乙方：张某

第一条 合同期限
本合同为固定期限劳动合同，合同期自2024年1月1日起至2024年12月31日止。

第二条 工作内容与地点
乙方担任销售岗位，工作地点由甲方根据业务需要随时调整。

第三条 工作时间与休息休假
乙方实行不定时工作制，加班费已包含在月度绩效奖金中，甲方不再另行支付。

第四条 劳动报酬
乙方月工资为基本工资3000元，绩效工资根据甲方考核决定。甲方有权根据经营状况调整乙方薪酬。

第五条 保密与竞业限制
乙方离职后两年内不得从事同行业工作，竞业限制补偿金为乙方离职前月工资的20%。

第六条 合同解除
乙方提前离职需提前60天书面通知甲方，否则需支付违约金3万元。`

// 风险概览数据
const riskSummary = computed(() => {
  if (!report.value) return []
  const clauses = report.value.clauses || []
  return [
    {
      label: '高风险条款',
      count: clauses.filter((c) => c.riskLevel === '高风险').length,
      bgClass: 'bg-red-50',
      textClass: 'text-red-500'
    },
    {
      label: '中风险条款',
      count: clauses.filter((c) => c.riskLevel === '中风险').length,
      bgClass: 'bg-amber-50',
      textClass: 'text-amber-500'
    },
    {
      label: '合规条款',
      count: clauses.filter((c) => c.riskLevel === '合规').length,
      bgClass: 'bg-green-50',
      textClass: 'text-green-500'
    }
  ]
})

// 综合风险等级样式
const overallRiskTag = computed(() => {
  const level = report.value?.riskLevel
  if (level === '高风险') return 'danger'
  if (level === '中风险') return 'warning'
  return 'success'
})
const overallRiskColor = computed(() => {
  const level = report.value?.riskLevel
  if (level === '高风险') return '#EF4444'
  if (level === '中风险') return '#F59E0B'
  return '#10B981'
})
const overallRiskBorder = computed(() => {
  const level = report.value?.riskLevel
  if (level === '高风险') return 'border-l-red-500'
  if (level === '中风险') return 'border-l-amber-500'
  return 'border-l-green-500'
})

// 风险标签类型
function riskTagType(level) {
  if (level === '高风险') return 'danger'
  if (level === '中风险') return 'warning'
  return 'success'
}

// 触发文件上传
function triggerUpload() {
  fileInputRef.value?.click()
}

// 处理文件选择
function handleFileChange(e) {
  const file = e.target.files[0]
  if (file) {
    if (file.size > 10 * 1024 * 1024) {
      ElMessage.error('文件大小不能超过 10MB')
      return
    }
    selectedFile.value = file
  }
}

// 拖拽上传
function handleDrop(e) {
  const file = e.dataTransfer.files[0]
  if (file) {
    selectedFile.value = file
  }
}

// 清除文件
function clearFile() {
  selectedFile.value = null
  if (fileInputRef.value) fileInputRef.value.value = ''
}

// 格式化文件大小
function formatFileSize(size) {
  if (size < 1024) return size + 'B'
  if (size < 1024 * 1024) return (size / 1024).toFixed(1) + 'KB'
  return (size / (1024 * 1024)).toFixed(1) + 'MB'
}

// 加载示例
function loadSample() {
  contractText.value = sampleContract
  inputTab.value = 'paste'
  ElMessage.success('已加载示例合同')
}

// 展开/折叠条款
function toggleClause(idx) {
  if (expandedClauses.has(idx)) {
    expandedClauses.delete(idx)
  } else {
    expandedClauses.add(idx)
  }
}

// 开始研判
async function startAnalyze() {
  if (inputTab.value === 'paste') {
    if (!contractText.value.trim()) {
      ElMessage.warning('请先粘贴合同文本')
      return
    }
    analyzing.value = true
    report.value = null
    expandedClauses.clear()

    try {
      const res = await analyzeContract({ text: contractText.value })
      report.value = res
      // 默认展开所有高风险条款
      res.clauses?.forEach((c, idx) => {
        if (c.riskLevel === '高风险') expandedClauses.add(idx)
      })
      ElMessage.success('研判完成')
    } catch (error) {
      // 错误已处理
    } finally {
      analyzing.value = false
    }
  } else {
    // 文件上传
    if (!selectedFile.value) {
      ElMessage.warning('请先选择文件')
      return
    }
    analyzing.value = true
    report.value = null
    expandedClauses.clear()

    try {
      const res = await uploadAndAnalyze(selectedFile.value)
      report.value = res
      res.clauses?.forEach((c, idx) => {
        if (c.riskLevel === '高风险') expandedClauses.add(idx)
      })
      ElMessage.success('研判完成')
    } catch (error) {
      // 错误已处理
    } finally {
      analyzing.value = false
    }
  }
}

// 导出报告
function exportReport() {
  ElMessage.success('报告导出功能开发中')
}
</script>

<style scoped>
</style>
