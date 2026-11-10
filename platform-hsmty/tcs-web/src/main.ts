import { createApp, type App as VueApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import { qiankunWindow, renderWithQiankun, type QiankunProps } from 'vite-plugin-qiankun/dist/helper'

import 'element-plus/dist/index.css'
import '@/styles/index.css'

import App from './App.vue'
import { useAuthStore, type CurrentUser } from '@/core/auth'
import { createAppRouter } from './router'

let app: VueApp | null = null

/**
 * 挂载应用。主应用通过 qiankun props 下发容器、当前用户与权限。
 */
function render(props: QiankunProps = {}) {
  const mountNode = props.container
    ? props.container.querySelector('#app')
    : document.querySelector('#app')

  if (!mountNode) {
    throw new Error('未找到 #app 挂载节点')
  }

  app = createApp(App)
  app.use(createPinia())
  app.use(createAppRouter())
  app.use(ElementPlus, { locale: zhCn })

  // 登录态由 UAP/SSO Cookie 承载，子应用只接收主应用下发的用户快照
  useAuthStore().applyUser(props.user as CurrentUser | undefined)

  app.mount(mountNode as Element)
}

renderWithQiankun({
  bootstrap() {
    // 子应用首次加载完成
  },
  mount(props) {
    render(props)
  },
  unmount() {
    app?.unmount()
    app = null
  },
  update() {
    // 主应用参数变化时按需刷新，当前无跨页共享状态
  },
})

if (!qiankunWindow.__POWERED_BY_QIANKUN__) {
  render()
}
