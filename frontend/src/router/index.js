/**
 * 路由配置
 * 含路由守卫：未登录跳转登录页，普通用户访问管理页跳转 403
 */
import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '../store/user'
import MainLayout from '../layouts/MainLayout.vue'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { title: '登录' }
  },
  {
    path: '/',
    component: MainLayout,
    redirect: '/qa',
    children: [
      {
        path: 'qa',
        name: 'QA',
        component: () => import('../views/QA.vue'),
        meta: { title: '智能问答' }
      },
      {
        path: 'judge',
        name: 'Judge',
        component: () => import('../views/Judge.vue'),
        meta: { title: '信息研判' }
      },
      {
        path: 'knowledge-base',
        name: 'KnowledgeBase',
        component: () => import('../views/KnowledgeBase.vue'),
        meta: { title: '知识库管理', requireAdmin: true }
      },
      {
        path: 'retrieval-viz',
        name: 'RetrievalViz',
        component: () => import('../views/RetrievalViz.vue'),
        meta: { title: '检索可视化', requireAdmin: true }
      },
      {
        path: 'analytics',
        name: 'Analytics',
        component: () => import('../views/Analytics.vue'),
        meta: { title: '数据分析', requireAdmin: true }
      }
    ]
  },
  {
    path: '/403',
    name: 'Forbidden',
    component: () => import('../views/Forbidden.vue'),
    meta: { title: '无权限' }
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('../views/NotFound.vue'),
    meta: { title: '页面不存在' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

/**
 * 全局前置守卫
 */
router.beforeEach((to, from, next) => {
  // 设置页面标题
  document.title = to.meta.title
    ? `${to.meta.title} - 劳动合同纠纷智能问答系统`
    : '劳动合同纠纷智能问答系统'

  const userStore = useUserStore()

  // 未登录跳转登录页
  if (!userStore.isLoggedIn && to.name !== 'Login' && to.name !== 'Forbidden' && to.name !== 'NotFound') {
    next({ name: 'Login' })
    return
  }

  // 已登录用户不能访问登录页
  if (userStore.isLoggedIn && to.name === 'Login') {
    next({ name: 'QA' })
    return
  }

  // 管理员路由权限校验
  if (to.meta.requireAdmin && !userStore.isAdmin) {
    next({ name: 'Forbidden' })
    return
  }

  next()
})

export default router
