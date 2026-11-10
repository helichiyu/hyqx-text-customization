import type { RouteRecordRaw } from 'vue-router'

/**
 * 菜单项：component 必须能解析到 register.ts 或约定目录中的页面。
 */
export interface MenuItem {
  key: string
  title: string
  path: string
  component: string
}

/**
 * 业务模块注册定义。
 */
export interface BusinessModule {
  key: string
  title: string
  routes: RouteRecordRaw[]
  menus: MenuItem[]
}

interface ModuleRegister {
  default: BusinessModule
}

const moduleFiles = import.meta.glob<ModuleRegister>('../modules/*/register.ts', { eager: true })

/**
 * 自动发现 src/modules/<domain>/register.ts，保持一个 qiankun 子应用内的模块化。
 */
export const businessModules: BusinessModule[] = Object.values(moduleFiles)
  .map((file) => file.default)
  .filter((module): module is BusinessModule => Boolean(module))

export function collectModuleRoutes(): RouteRecordRaw[] {
  return businessModules.flatMap((module) => module.routes)
}

export function collectModuleMenus(): MenuItem[] {
  return businessModules.flatMap((module) => module.menus)
}
