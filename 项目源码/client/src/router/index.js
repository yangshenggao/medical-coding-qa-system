/**
 * Vue Router路由配置
 * 定义页面路由和导航守卫（权限控制）
 */
import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { title: '登录' }
  },
  {
    path: '/',
    component: () => import('../views/Layout.vue'),
    redirect: '/whodrug',
    children: [
      {
        path: 'home',
        name: 'Home',
        component: () => import('../views/Home.vue'),
        meta: { title: '首页', requireAdmin: true }
      },
      {
        path: 'whodrug',
        name: 'WhodrugQuery',
        component: () => import('../views/WhodrugQuery.vue'),
        meta: { title: 'WHODrug编码查询' }
      },
      {
        path: 'meddra',
        name: 'MeddraSearch',
        component: () => import('../views/MeddraSearch.vue'),
        meta: { title: 'MedDRA术语搜索' }
      },
      {
        path: 'user-manage',
        name: 'UserManage',
        component: () => import('../views/UserManage.vue'),
        meta: { title: '用户管理', requireAdmin: true }
      },
      {
        path: 'import',
        name: 'DataImport',
        component: () => import('../views/DataImport.vue'),
        meta: { title: '数据导入', requireAdmin: true }
      },
      {
        path: 'knowledge-base',
        name: 'KnowledgeBase',
        component: () => import('../views/KnowledgeBase.vue'),
        meta: { title: '知识库管理', requireAdmin: true }
      },
      {
        path: 'document',
        name: 'Document',
        component: () => import('../views/Document.vue'),
        meta: { title: '文档管理', requireAdmin: true }
      },
      {
        path: 'chat',
        name: 'Chat',
        component: () => import('../views/Chat.vue'),
        meta: { title: '智能问答' }
      },
      {
        path: 'chat-history',
        name: 'ChatHistory',
        component: () => import('../views/ChatHistory.vue'),
        meta: { title: '对话历史' }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  const userInfo = JSON.parse(localStorage.getItem('userInfo') || 'null')

  if (!token && to.path !== '/login') {
    return next('/login')
  }

  if (token && to.path === '/login') {
    return next('/')
  }

  if (to.meta.requireAdmin && userInfo?.role !== 'admin') {
    return next('/whodrug')
  }

  document.title = to.meta.title ? `${to.meta.title} - 医学编码问答系统` : '医学编码问答系统'
  next()
})

export default router
