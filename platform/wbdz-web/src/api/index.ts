import { get, post, put, del, upload, downloadBlob, type PageResult } from './http'

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

// ==================== 认证 ====================

export const login = (username: string, password: string) =>
  post<{ token: string }>('/api/auth/login', { username, password })

export const me = () => get<{ id: string; username: string; nickname: string }>('/api/auth/me')

// ==================== 素材 ====================

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

export const materialPage = (params: Record<string, any>) =>
  get<PageResult<MatBatchView>>('/api/material', params)

export const materialDetail = (id: string) => get<any>(`/api/material/${id}`)

export const materialUpload = (line: string, name: string, files: File[]) => {
  const form = new FormData()
  form.append('line', line)
  form.append('name', name)
  files.forEach((f) => form.append('files', f))
  return upload<MatBatchView>('/api/material/upload', form)
}

export const materialCheck = (id: string) => post(`/api/material/${id}/check`)
export const materialRelease = (id: string) => post(`/api/material/${id}/release`)
export const materialEdit = (id: string, body: { name?: string; line?: string }) =>
  put(`/api/material/${id}`, body)
export const materialDelete = (id: string) => del(`/api/material/${id}`)

// ==================== 参数配置 ====================

export const paramOverview = () =>
  get<{ line: string; lineName: string; version: string; publishedAt: string }[]>(
    '/api/param/overview',
  )

export const paramLineConfig = (line: string) => get<any>(`/api/param/${line}`)

export const paramSaveDraft = (line: string, content: string) =>
  put(`/api/param/${line}/draft`, { line, content })

export const paramPublish = (line: string, content?: string) =>
  post(`/api/param/${line}/publish`, content === undefined ? undefined : { line, content })

// ==================== 任务 ====================

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

export const taskPage = (params: Record<string, any>) =>
  get<PageResult<TaskView>>('/api/task', params)

export const taskDetail = (id: string) => get<any>(`/api/task/${id}`)

export const taskCreate = (body: Record<string, any>) => post('/api/task', body)
export const taskUpdate = (id: string, body: Record<string, any>) => put(`/api/task/${id}`, body)
export const taskSubmit = (id: string) => post(`/api/task/${id}/submit`)
export const taskStart = (id: string) => post(`/api/task/${id}/start`)
export const taskReject = (id: string, fromStage: number) =>
  post(`/api/task/${id}/reject`, { fromStage })
export const taskCollect = (id: string) => post(`/api/task/${id}/collect`)
export const taskThreshold = (id: string, threshold: number) =>
  put(`/api/task/${id}/threshold`, { threshold })
export const taskDelete = (id: string) => del(`/api/task/${id}`)

// ==================== 条件复核 ====================

export const reviewPage = (params: Record<string, any>) =>
  get<PageResult<any>>('/api/review', params)
export const reviewDetail = (id: string) => get<any>(`/api/review/${id}`)
export const reviewConclude = (itemId: string, conclusion: string, revisedPayload?: any) =>
  post(`/api/review/item/${itemId}/conclude`, { conclusion, revisedPayload })
export const reviewUnconclude = (itemId: string) => post(`/api/review/item/${itemId}/unconclude`)
export const reviewAddFromDataset = (datasetItemId: string) =>
  post<{ orderId: string; orderBizNo: string }>(`/api/review/item/${datasetItemId}/add`)
export const reviewClose = (id: string) => post(`/api/review/${id}/close`)

// ==================== 数据集 ====================

export const datasetPage = (params: Record<string, any>) =>
  get<PageResult<any>>('/api/dataset', params)
export const datasetDetail = (id: string, params?: Record<string, any>) =>
  get<any>(`/api/dataset/${id}`, params)
export const datasetPublish = (id: string) => post(`/api/dataset/${id}/publish`)
export const datasetRollback = (id: string, reason: string) =>
  post(`/api/dataset/${id}/rollback`, { reason })
export const deliveryPage = (params: Record<string, any>) =>
  get<PageResult<any>>('/api/dataset/deliveries', params)

// ==================== 产物文件 ====================

export const artifactList = (runId: string) =>
  get<{ name: string; size: number }[]>('/api/artifact/list', { runId })

export const artifactFileUrl = (runId: string, name: string, download = false) =>
  `/api/artifact/file?runId=${runId}&name=${encodeURIComponent(name)}&download=${download}`

/** 环节产物文件（带认证头取 blob，预览/下载共用） */
export const artifactBlob = (runId: string, name: string) =>
  downloadBlob(`/api/artifact/file?runId=${runId}&name=${encodeURIComponent(name)}`)

/** 保存 blob 为本地文件 */
export function saveBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  setTimeout(() => URL.revokeObjectURL(url), 3000)
}

/** 报告下载（带认证头转 blob） */
export { downloadBlob } from './http'
