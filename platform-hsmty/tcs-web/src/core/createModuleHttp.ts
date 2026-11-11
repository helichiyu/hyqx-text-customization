import axios, { type AxiosInstance } from 'axios'
import { ElMessage } from 'element-plus'

/**
 * 统一响应结构，Long ID 在 JSON 中以字符串返回。
 */
export interface ApiResult<T> {
  code: string
  message: string
  data: T
}

const SUCCESS_CODE = '0000'

/**
 * 创建模块 HTTP 客户端：统一 /hs-api 相对路径、Cookie 会话与错误处理。
 */
export function createModuleHttp(): AxiosInstance {
  const instance = axios.create({
    baseURL: '/hs-api',
    withCredentials: true,
    timeout: 30_000,
  })

  instance.interceptors.response.use(
    (response) => {
      // 文件流（报告/产物预览）不参与业务信封校验
      if (response.data instanceof Blob) {
        return response
      }
      const body = response.data as Partial<ApiResult<unknown>> | undefined
      if (body && typeof body.code === 'string' && body.code !== SUCCESS_CODE) {
        const message = body.message || '请求失败'
        ElMessage.error(message)
        return Promise.reject(new Error(message))
      }
      return response
    },
    (error: unknown) => {
      const message =
        axios.isAxiosError(error)
          ? ((error.response?.data as Partial<ApiResult<unknown>> | undefined)?.message ||
            error.message ||
            '网络请求失败')
          : error instanceof Error
            ? error.message
            : '网络请求失败'
      ElMessage.error(message)
      return Promise.reject(error instanceof Error ? error : new Error(message))
    },
  )

  return instance
}

export const moduleHttp = createModuleHttp()
