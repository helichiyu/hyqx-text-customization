import type { BusinessModule } from '@/core/register'

/**
 * 文本定制化生产模块注册定义。
 *
 * component key、菜单 component 与页面路径保持一致，便于动态菜单解析。
 */
const customTextModule: BusinessModule = {
  key: 'custom-text',
  title: '文本定制化生产',
  routes: [
    {
      path: '/custom-text',
      name: 'custom-text-home',
      component: () => import('./views/Home.vue'),
      meta: {
        title: '文本定制化生产',
        module: 'custom-text',
      },
    },
  ],
  menus: [
    {
      key: 'custom-text',
      title: '文本定制化生产',
      path: '/custom-text',
      component: 'custom-text/Home',
    },
  ],
}

export default customTextModule
