import { businessModules } from '@/core/register'

/**
 * OBU 版组合入口：Cookie SSO 登录态由主应用注入，
 * 业务模块在同一个 qiankun 子应用内按模块注册。
 */
export const obuEdition = {
  name: 'obu',
  authMode: 'cookie-sso' as const,
  modules: businessModules.map((module) => module.key),
}
