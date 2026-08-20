<template>
  <!-- 登录页面：卡片式布局 -->
  <div class="flex h-screen w-full items-center justify-center bg-gradient-to-br from-primary-50 via-white to-secondary-50">
    <!-- 左侧品牌区 -->
    <div class="hidden lg:flex flex-col justify-center w-[420px] h-[560px] mr-8 px-8 text-white rounded-2xl gradient-bg shadow-2xl">
      <div class="mb-8">
        <div class="w-14 h-14 rounded-2xl bg-white/20 flex items-center justify-center mb-4">
          <el-icon :size="32" color="#fff"><ScaleToOriginal /></el-icon>
        </div>
        <h1 class="text-2xl font-bold mb-2">劳动合同纠纷</h1>
        <h1 class="text-2xl font-bold">智能问答系统</h1>
      </div>
      <p class="text-white/80 text-sm leading-relaxed mb-6">
        基于 RAG 检索增强生成技术，为您提供劳动合同法律法规智能问答、
        合同风险研判、知识库管理等一站式服务。
      </p>
      <div class="space-y-3">
        <div class="flex items-center gap-2 text-white/90 text-sm">
          <el-icon><CircleCheckFilled /></el-icon>
          <span>智能问答，秒级响应</span>
        </div>
        <div class="flex items-center gap-2 text-white/90 text-sm">
          <el-icon><CircleCheckFilled /></el-icon>
          <span>引用溯源，权威可靠</span>
        </div>
        <div class="flex items-center gap-2 text-white/90 text-sm">
          <el-icon><CircleCheckFilled /></el-icon>
          <span>合同研判，风险预警</span>
        </div>
        <div class="flex items-center gap-2 text-white/90 text-sm">
          <el-icon><CircleCheckFilled /></el-icon>
          <span>落地服务，指引维权</span>
        </div>
      </div>
    </div>

    <!-- 右侧登录卡片 -->
    <div class="w-[420px] bg-white rounded-2xl shadow-card-hover p-8">
      <!-- 标题 -->
      <div class="mb-6">
        <h2 class="text-2xl font-bold text-gray-800 mb-1">
          {{ isRegister ? '注册账号' : '欢迎回来' }}
        </h2>
        <p class="text-sm text-gray-400">
          {{ isRegister ? '创建您的账号开始使用' : '请登录您的账号继续使用' }}
        </p>
      </div>

      <!-- 表单 -->
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        size="large"
        label-position="top"
        @submit.prevent="handleSubmit"
      >
        <el-form-item prop="username" label="用户名">
          <el-input
            v-model="form.username"
            placeholder="请输入用户名"
            :prefix-icon="User"
            clearable
          />
        </el-form-item>

        <el-form-item prop="password" label="密码">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="请输入密码"
            :prefix-icon="Lock"
            show-password
            @keyup.enter="handleSubmit"
          />
        </el-form-item>

        <el-form-item v-if="isRegister" prop="confirmPassword" label="确认密码">
          <el-input
            v-model="form.confirmPassword"
            type="password"
            placeholder="请再次输入密码"
            :prefix-icon="Lock"
            show-password
          />
        </el-form-item>

        <el-button
          type="primary"
          class="w-full mt-2"
          :loading="loading"
          @click="handleSubmit"
        >
          {{ isRegister ? '注册' : '登录' }}
        </el-button>
      </el-form>

      <!-- 切换登录/注册 -->
      <div class="text-center mt-5">
        <span class="text-sm text-gray-400">
          {{ isRegister ? '已有账号？' : '还没有账号？' }}
        </span>
        <span
          class="text-sm text-primary cursor-pointer hover:underline ml-1"
          @click="isRegister = !isRegister"
        >
          {{ isRegister ? '去登录' : '立即注册' }}
        </span>
      </div>

      <!-- 快捷登录提示 -->
      <div v-if="!isRegister" class="mt-6 pt-4 border-t border-gray-100">
        <p class="text-xs text-gray-400 text-center mb-3">快捷体验账号</p>
        <div class="flex gap-2">
          <el-button
            size="small"
            class="flex-1"
            @click="quickLogin('testuser', '123456')"
          >
            普通用户
          </el-button>
          <el-button
            size="small"
            type="primary"
            plain
            class="flex-1"
            @click="quickLogin('admin', 'admin123')"
          >
            管理员
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * 登录页面
 * 用户名密码登录 / 注册，卡片式美观布局
 */
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../store/user'
import { ElMessage } from 'element-plus'
import {
  User,
  Lock,
  ScaleToOriginal,
  CircleCheckFilled
} from '@element-plus/icons-vue'

const router = useRouter()
const userStore = useUserStore()

const formRef = ref(null)
const isRegister = ref(false)
const loading = ref(false)

const form = reactive({
  username: '',
  password: '',
  confirmPassword: ''
})

// 表单校验规则
const rules = reactive({
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, message: '用户名至少 3 个字符', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少 6 个字符', trigger: 'blur' }
  ],
  confirmPassword: [
    {
      required: true,
      validator: (rule, value, callback) => {
        if (!value) {
          callback(new Error('请再次输入密码'))
        } else if (value !== form.password) {
          callback(new Error('两次输入的密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
})

// 快捷登录
function quickLogin(username, password) {
  form.username = username
  form.password = password
  handleSubmit()
}

// 提交表单
async function handleSubmit() {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return

    loading.value = true
    try {
      if (isRegister.value) {
        await userStore.register(form.username, form.password)
        ElMessage.success('注册成功，请登录')
        isRegister.value = false
        form.password = ''
        form.confirmPassword = ''
      } else {
        await userStore.login(form.username, form.password)
        ElMessage.success('登录成功')
        router.push('/qa')
      }
    } catch (error) {
      // 错误已在拦截器处理
    } finally {
      loading.value = false
    }
  })
}
</script>

<style scoped>
</style>
