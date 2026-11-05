import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes: RouteRecordRaw[] = [
  { path: '/login', component: () => import('@/views/Login.vue'), meta: { title: '登录' } },
  {
    path: '/',
    component: () => import('@/layout/MainLayout.vue'),
    redirect: '/wb/metadata',
    children: [
      {
        path: 'wb/:line',
        component: () => import('@/views/Workbench.vue'),
        props: true,
        meta: { title: '产线工作台' },
      },
      {
        path: 'task/:bizNo',
        component: () => import('@/views/TaskDetail.vue'),
        props: true,
        meta: { title: '任务详情' },
      },
      {
        path: 'material',
        component: () => import('@/views/Material.vue'),
        meta: { title: '素材管理' },
      },
      {
        path: 'review',
        component: () => import('@/views/Review.vue'),
        meta: { title: '条件复核' },
      },
      {
        path: 'dataset',
        component: () => import('@/views/Dataset.vue'),
        meta: { title: '数据集管理' },
      },
      {
        path: 'params',
        component: () => import('@/views/Params.vue'),
        meta: { title: '参数配置' },
      },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.path !== '/login' && !auth.logged) return '/login'
  if (to.path === '/login' && auth.logged) return '/'
  return true
})

export default router
