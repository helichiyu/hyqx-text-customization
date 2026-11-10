import { moduleHttp } from '@/core/createModuleHttp'

/**
 * 模块探活，对应后端 /hs-api/tcs/health。
 */
export function health() {
  return moduleHttp.get('/tcs/health')
}
