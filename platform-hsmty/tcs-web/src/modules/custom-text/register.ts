import type { BusinessModule } from '@/core/register'

/**
 * 文本定制化生产模块注册定义。
 *
 * 子应用内页面统一挂在 `/custom-text` 下，避免与主应用路由冲突；
 * component key、菜单 component 与页面路径保持一致，便于动态菜单解析。
 */
const customTextModule: BusinessModule = {
  key: 'custom-text',
  title: '文本定制化生产',
  routes: [
    {
      path: '/custom-text',
      name: 'custom-text',
      component: () => import('./layout/ModuleLayout.vue'),
      redirect: '/custom-text/wb/metadata',
      meta: { title: '文本定制化生产', module: 'custom-text' },
      children: [
        {
          path: 'wb/:line',
          name: 'custom-text-wb',
          component: () => import('./views/Workbench.vue'),
          props: true,
          meta: { title: '产线工作台', module: 'custom-text' },
        },
        {
          path: 'task/:taskRef',
          name: 'custom-text-task',
          component: () => import('./views/TaskDetail.vue'),
          props: true,
          meta: { title: '任务详情', module: 'custom-text' },
        },
        {
          path: 'material',
          name: 'custom-text-material',
          component: () => import('./views/Material.vue'),
          meta: { title: '素材管理', module: 'custom-text' },
        },
        {
          path: 'review',
          name: 'custom-text-review',
          component: () => import('./views/Review.vue'),
          meta: { title: '条件复核', module: 'custom-text' },
        },
        {
          path: 'dataset',
          name: 'custom-text-dataset',
          component: () => import('./views/Dataset.vue'),
          meta: { title: '数据集管理', module: 'custom-text' },
        },
        {
          path: 'params',
          name: 'custom-text-params',
          component: () => import('./views/Params.vue'),
          meta: { title: '参数配置', module: 'custom-text' },
        },
      ],
    },
  ],
  menus: [
    { key: 'custom-text-wb-formula', title: '公式文本工作台', path: '/custom-text/wb/formula', component: 'custom-text/Workbench' },
    { key: 'custom-text-wb-layout', title: '复杂版面工作台', path: '/custom-text/wb/layout', component: 'custom-text/Workbench' },
    { key: 'custom-text-wb-graphic', title: '图文融合工作台', path: '/custom-text/wb/graphic', component: 'custom-text/Workbench' },
    { key: 'custom-text-wb-metadata', title: '文本元信息工作台', path: '/custom-text/wb/metadata', component: 'custom-text/Workbench' },
    { key: 'custom-text-material', title: '素材管理', path: '/custom-text/material', component: 'custom-text/Material' },
    { key: 'custom-text-review', title: '条件复核', path: '/custom-text/review', component: 'custom-text/Review' },
    { key: 'custom-text-dataset', title: '数据集管理', path: '/custom-text/dataset', component: 'custom-text/Dataset' },
    { key: 'custom-text-params', title: '参数配置', path: '/custom-text/params', component: 'custom-text/Params' },
  ],
}

export default customTextModule
