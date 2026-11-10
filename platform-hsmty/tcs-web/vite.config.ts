import { fileURLToPath, URL } from 'node:url'

import vue from '@vitejs/plugin-vue'
import { defineConfig, loadEnv } from 'vite'
import qiankun from 'vite-plugin-qiankun'

/**
 * 文本定制化生产 Web 构建配置。
 *
 * - 端口由 VITE_PORT 控制，默认 9848；
 * - 生产部署路径由 VITE_PUBLIC_PATH 控制，默认 /sdom-hsmty/；
 * - /hs-api 通过相对路径代理到平台后端，浏览器不保存 Token。
 */
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  // 默认独立运行保留 HMR；需要以子应用方式联调时设置 VITE_QIANKUN_DEV=true
  const useDevMode = env.VITE_QIANKUN_DEV === 'true'

  return {
    base: env.VITE_PUBLIC_PATH || '/sdom-hsmty/',
    plugins: [
      vue(),
      qiankun('custom-text', { useDevMode }),
    ],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
      },
    },
    server: {
      port: Number(env.VITE_PORT || 9848),
      proxy: {
        '/hs-api': {
          target: env.VITE_API_PROXY_TARGET || 'http://localhost:8080',
          changeOrigin: true,
        },
      },
    },
  }
})
