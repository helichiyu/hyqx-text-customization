import { moduleHttp, type ApiResult } from '@/core/createModuleHttp'
import type { PageResult } from '@/core/types'

// ==================== 通用常量 ====================

/** 产线代码 → 中文名（与后端 LineRegistry 一致） */
export const LINE_NAMES: Record<string, string> = {
  formula: '公式文本',
  layout: '复杂版面',
  graphic: '图文融合',
  metadata: '文本元信息',
}

export const LINE_WHITELIST_TEXT: Record<string, string> = {
  formula: 'pdf / zip',
  layout: 'pdf / zip',
  graphic: 'jpg / jpeg / zip',
  metadata: 'html / zip',
}

/** 图文任务大类（与算子 category 枚举一致） */
export const IMAGE_CLASSES = ['几何', '统计', '表格', '示意']

/** 任务状态 → {名称, tag 类型} */
export const TASK_STATUS: Record<string, { name: string; tag: string }> = {
  draft: { name: '草稿', tag: 'info' },
  pending: { name: '待处理', tag: 'warning' },
  processing: { name: '加工中', tag: 'primary' },
  waitreview: { name: '待复核', tag: 'danger' },
  quality: { name: '待归集', tag: 'success' },
  collected: { name: '已归集', tag: '' },
  reject: { name: '已驳回', tag: 'info' },
}

/** 素材批次状态 */
export const MAT_STATUS: Record<string, { name: string; tag: string }> = {
  uncheked: { name: '未校验', tag: 'warning' },
  checked: { name: '已校验', tag: 'primary' },
  released: { name: '已移交', tag: 'success' },
  upload_failed: { name: '上传失败', tag: 'danger' },
}

/** 复核单状态 */
export const REVIEW_STATUS: Record<string, { name: string; tag: string }> = {
  pending: { name: '待复核', tag: 'danger' },
  doing: { name: '复核中', tag: 'warning' },
  done: { name: '已闭环', tag: 'success' },
  void: { name: '已作废', tag: 'info' },
}

/** 数据集状态 */
export const DS_STATUS: Record<string, { name: string; tag: string }> = {
  candidate: { name: '候选', tag: 'warning' },
  published: { name: '已发布', tag: 'success' },
  rolledback: { name: '已回滚', tag: 'info' },
}

export const PRIORITIES: Record<string, { name: string; tag: string }> = {
  high: { name: '高', tag: 'danger' },
  mid: { name: '中', tag: 'warning' },
  low: { name: '低', tag: 'info' },
}

// ==================== 通用请求封装 ====================

/**
 * 统一解包业务信封。
 *
 * 后端分页入参为 `page` / `limit`，出参为 `{ rows, total, current, limit, totalPage }`；
 * 页面内仍沿用 pageNum / pageSize 命名，只在调用处转换。
 */
async function getData<T>(url: string, params?: Record<string, unknown>): Promise<T> {
  const response = await moduleHttp.get<ApiResult<T>>(url, { params })
  return response.data.data
}

async function postData<T>(url: string, body?: unknown): Promise<T> {
  const response = await moduleHttp.post<ApiResult<T>>(url, body ?? {})
  return response.data.data
}

async function putData<T>(url: string, body?: unknown): Promise<T> {
  const response = await moduleHttp.put<ApiResult<T>>(url, body ?? {})
  return response.data.data
}

async function deleteData<T>(url: string): Promise<T> {
  const response = await moduleHttp.delete<ApiResult<T>>(url)
  return response.data.data
}

async function uploadData<T>(url: string, form: FormData): Promise<T> {
  const response = await moduleHttp.post<ApiResult<T>>(url, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return response.data.data
}

async function downloadBlob(url: string, params?: Record<string, unknown>): Promise<Blob> {
  const response = await moduleHttp.get<Blob>(url, { params, responseType: 'blob' })
  return response.data
}

// ==================== 业务类型 ====================

export interface MatBatchView {
  id: string
  bizNo: string
  name: string
  line: string
  lineName: string
  status: string
  fileCount: number
  totalCount: number
  rejectSummary: { reason: string; count: number }[]
  createBy: string
  createTime: string
  linked?: boolean
  linkedTaskCount?: number
}

export interface TaskView {
  id: string
  bizNo: string
  name: string
  line: string
  lineName: string
  status: string
  statusName: string
  priority: string
  imageClass?: string
  paramVersion: string
  threshold: number
  currentStage: number
  batchId?: string
  batchBizNo?: string
  batchName?: string
  datasetCount?: number
}

// ==================== 素材 ====================

export const materialPage = (params: Record<string, unknown>) =>
  getData<PageResult<MatBatchView>>('/tcs/material', params)

export const materialDetail = (reference: string) =>
  getData<any>(`/tcs/material/${encodeURIComponent(reference)}`)

export const materialUpload = (line: string, name: string, files: File[]) => {
  const form = new FormData()
  form.append('line', line)
  form.append('name', name)
  files.forEach((file) => form.append('files', file))
  return uploadData<MatBatchView>('/tcs/material/upload', form)
}

export const materialCheck = (reference: string) =>
  postData<MatBatchView>(`/tcs/material/${encodeURIComponent(reference)}/check`)

export const materialRelease = (reference: string) =>
  postData<MatBatchView>(`/tcs/material/${encodeURIComponent(reference)}/release`)

export const materialEdit = (reference: string, body: { name?: string; line?: string }) =>
  putData<MatBatchView>(`/tcs/material/${encodeURIComponent(reference)}`, body)

export const materialDelete = (reference: string) =>
  deleteData<void>(`/tcs/material/${encodeURIComponent(reference)}`)

// ==================== 参数配置 ====================

export const paramOverview = () =>
  getData<{ line: string; lineName: string; version: string; publishedAt: string }[]>(
    '/tcs/param/overview',
  )

export const paramLineConfig = (line: string) => getData<any>(`/tcs/param/${encodeURIComponent(line)}`)

export const paramSaveDraft = (line: string, content: string) =>
  putData<void>(`/tcs/param/${encodeURIComponent(line)}/draft`, { line, content })

export const paramPublish = (line: string, content?: string) =>
  postData<any>(
    `/tcs/param/${encodeURIComponent(line)}/publish`,
    content === undefined ? undefined : { line, content },
  )

// ==================== 任务 ====================

export const taskPage = (params: Record<string, unknown>) =>
  getData<PageResult<TaskView>>('/tcs/task', params)

export const taskDetail = (reference: string) =>
  getData<any>(`/tcs/task/${encodeURIComponent(reference)}`)

export const taskCreate = (body: Record<string, unknown>) => postData<any>('/tcs/task', body)

export const taskUpdate = (reference: string, body: Record<string, unknown>) =>
  putData<any>(`/tcs/task/${encodeURIComponent(reference)}`, body)

export const taskSubmit = (reference: string) =>
  postData<void>(`/tcs/task/${encodeURIComponent(reference)}/submit`)

export const taskStart = (reference: string) =>
  postData<void>(`/tcs/task/${encodeURIComponent(reference)}/start`)

export const taskReject = (reference: string, fromStage: number) =>
  postData<void>(`/tcs/task/${encodeURIComponent(reference)}/reject`, { fromStage })

export const taskCollect = (reference: string) =>
  postData<void>(`/tcs/task/${encodeURIComponent(reference)}/collect`)

export const taskThreshold = (reference: string, threshold: number) =>
  putData<void>(`/tcs/task/${encodeURIComponent(reference)}/threshold`, { threshold })

export const taskDelete = (reference: string) =>
  deleteData<void>(`/tcs/task/${encodeURIComponent(reference)}`)

// ==================== 条件复核 ====================

export const reviewPage = (params: Record<string, unknown>) =>
  getData<PageResult<any>>('/tcs/review', params)

export const reviewDetail = (reference: string) =>
  getData<any>(`/tcs/review/${encodeURIComponent(reference)}`)

export const reviewConclude = (
  itemId: string | number,
  conclusion: 'A' | 'B' | 'C',
  revisedPayload?: Record<string, unknown>,
) =>
  postData<void>(`/tcs/review/item/${itemId}/conclude`, {
    conclusion,
    revisedPayload,
  })

export const reviewUnconclude = (itemId: string | number) =>
  postData<void>(`/tcs/review/item/${itemId}/unconclude`)

export const reviewAddFromDataset = (datasetItemId: string | number) =>
  postData<{ orderId: string; orderBizNo: string }>(`/tcs/review/item/${datasetItemId}/add`)

export const reviewClose = (reference: string) =>
  postData<void>(`/tcs/review/${encodeURIComponent(reference)}/close`)

// ==================== 数据集 ====================

export const datasetPage = (params: Record<string, unknown>) =>
  getData<PageResult<any>>('/tcs/dataset', params)

export const datasetDetail = (reference: string, params?: Record<string, unknown>) =>
  getData<any>(`/tcs/dataset/${encodeURIComponent(reference)}`, params)

export const datasetPublish = (reference: string) =>
  postData<any>(`/tcs/dataset/${encodeURIComponent(reference)}/publish`)

export const datasetRollback = (reference: string, reason: string) =>
  postData<any>(`/tcs/dataset/${encodeURIComponent(reference)}/rollback`, { reason })

export const datasetReport = (reference: string) =>
  downloadBlob(`/tcs/dataset/${encodeURIComponent(reference)}/report`)

export const deliveryPage = (params: Record<string, unknown>) =>
  getData<PageResult<any>>('/tcs/dataset/deliveries', params)

// ==================== 产物文件 ====================

export const artifactList = (runId: string | number) =>
  getData<{ name: string; size: number }[]>('/tcs/artifact/list', { runId })

/** 环节产物文件（Cookie 会话取 blob，预览/下载共用） */
export const artifactBlob = (runId: string | number, name: string) =>
  downloadBlob('/tcs/artifact/file', { runId, name })

/** 保存 blob 为本地文件 */
export function saveBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  setTimeout(() => URL.revokeObjectURL(url), 3000)
}

/** 模块探活，对应后端 /hs-api/tcs/health。 */
export function health() {
  return getData<string>('/tcs/health')
}

export { downloadBlob }
