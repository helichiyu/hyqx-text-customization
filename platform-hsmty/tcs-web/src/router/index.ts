import { createRouter, createWebHistory, type RouteRecordRaw, type Router } from 'vue-router'
import { qiankunWindow } from 'vite-plugin-qiankun/dist/helper'

import { collectModuleRoutes } from '@/core/register'

const HOME_ROUTE: RouteRecordRaw = {
  path: '/',
  redirect: '/custom-text',
}

/**
 * 创建路由：模块路由由 src/modules/<domain>/register.ts 自动注册。
 */
export function createAppRouter(): Router {
  const base = qiankunWindow.__POWERED_BY_QIANKUN__ ? '/sdom-hsmty/' : import.meta.env.BASE_URL

  return createRouter({
    history: createWebHistory(base),
    routes: [HOME_ROUTE, ...collectModuleRoutes()],
  })
}
