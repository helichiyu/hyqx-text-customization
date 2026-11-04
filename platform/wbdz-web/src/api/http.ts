import axios from 'axios'
import { ElMessage } from 'element-plus'

/** 统一响应信封 */
export interface ApiEnvelope<T = any> {
  code: number
  msg: string
  data: T
}

export interface PageResult<T = any> {
  total: number
  pageNum: number
  pageSize: number
  records: T[]
}

const http = axios.create({ baseURL: '', timeout: 60_000 })

http.interceptors.request.use((cfg) => {
  const token = localStorage.getItem('wbdz_token')
  if (token) cfg.headers.Authorization = `Bearer ${token}`
  return cfg
})

http.interceptors.response.use(
  (resp) => {
    const body = resp.data
    // 文件流（报告下载等）直接透传
    if (body instanceof Blob) return body
    if (body && typeof body.code === 'number') {
      if (body.code !== 0) {
        ElMessage.error(body.msg || '请求失败')
        return Promise.reject(new Error(body.msg))
      }
      return body.data
    }
    return body
  },
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('wbdz_token')
      if (location.pathname !== '/login') location.href = '/login'
    } else {
      ElMessage.error(err.response?.data?.msg || err.message || '网络错误')
    }
    return Promise.reject(err)
  },
)

/** 统一 GET（信封拆包） */
export async function get<T = any>(url: string, params?: Record<string, any>): Promise<T> {
  return http.get(url, { params }) as Promise<T>
}

/** 统一 POST */
export async function post<T = any>(url: string, body?: any): Promise<T> {
  return http.post(url, body ?? {}) as Promise<T>
}

/** 统一 PUT */
export async function put<T = any>(url: string, body?: any): Promise<T> {
  return http.put(url, body ?? {}) as Promise<T>
}

/** 统一 DELETE */
export async function del<T = any>(url: string): Promise<T> {
  return http.delete(url) as Promise<T>
}

/** 文件上传（multipart） */
export async function upload<T = any>(url: string, form: FormData): Promise<T> {
  return http.post(url, form, { headers: { 'Content-Type': 'multipart/form-data' } }) as Promise<T>
}

/** 认证请求头（报告下载等 window.open 场景不可用时用 blob） */
export async function downloadBlob(url: string): Promise<Blob> {
  return http.get(url, { responseType: 'blob' }) as Promise<Blob>
}

export default http
