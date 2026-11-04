<template>
  <div class="page-stack" v-loading="loading">
    <PageHeader v-if="task" :title="task.name" eyebrow="任务详情">
      <template #description>
        <span class="sub">
          <BizIdText :value="task.bizNo" />
          <el-tag :type="TASK_STATUS[task.status]?.tag" effect="light">{{ task.statusName }}</el-tag>
          <el-tag :type="PRIORITIES[task.priority]?.tag" size="small">{{ PRIORITIES[task.priority]?.name }}</el-tag>
          <el-tag v-if="task.imageClass" size="small" type="info">{{ task.imageClass }}</el-tag>
          <span class="muted">{{ task.lineName }} · 第 {{ task.currentStage }}/3 环节</span>
          <el-tag v-if="task.running" type="warning" size="small" effect="dark">执行中</el-tag>
        </span>
      </template>
      <template #actions>
        <el-button v-if="task.status === 'draft'" type="primary" @click="act('submit')">提交</el-button>
        <el-button v-if="task.status === 'pending'" type="primary" @click="act('start')">启动执行</el-button>
        <el-button v-if="task.status === 'quality'" type="success" @click="act('collect')">归集</el-button>
        <el-button v-if="task.status === 'waitreview' || task.status === 'quality'" type="warning" @click="openReject">驳回重跑</el-button>
        <el-button v-if="task.status === 'draft'" type="danger" plain @click="act('delete')">删除</el-button>
        <el-button @click="load">刷新</el-button>
      </template>
    </PageHeader>

    <el-card shadow="never" v-if="task">
      <el-descriptions :column="3" border size="small" class="desc">
        <el-descriptions-item label="素材批次">
          {{ task.batch ? `${task.batch.bizNo} · ${task.batch.name}` : '—' }}
          <span class="muted">（有效 {{ task.batch?.fileCount ?? 0 }} 条）</span>
        </el-descriptions-item>
        <el-descriptions-item label="参数版本">{{ task.paramVersion || '—' }}</el-descriptions-item>
        <el-descriptions-item label="置信度阈值">
          <span class="mono">{{ task.threshold }}</span>
          <el-button link type="primary" size="small" @click="openThreshold">调整</el-button>
        </el-descriptions-item>
        <el-descriptions-item label="创建人">{{ task.createBy || '—' }}</el-descriptions-item>
        <el-descriptions-item label="创建时间" :span="2">{{ fmt(task.createTime) }}</el-descriptions-item>
      </el-descriptions>
    </el-card>

    <!-- 环节执行 -->
    <el-card shadow="never" class="block">
      <template #header><b>环节执行</b></template>
      <div class="stages">
        <div v-for="(name, i) in task?.stageNames || []" :key="i" class="stage"
             :class="{ done: task.currentStage > i + 1 || task.status === 'collected', current: task.currentStage === i + 1 && task.status !== 'collected' }">
          <div class="stage-no">{{ i + 1 }}</div>
          <div class="stage-name">{{ name }}</div>
          <div class="stage-sub">{{ runsOf(i + 1).length ? `执行 ${runsOf(i + 1).length} 次` : '未执行' }}</div>
        </div>
      </div>

      <el-table :data="task?.stageRuns || []" size="small" style="margin-top: 12px">
        <el-table-column label="环节" width="90">
          <template #default="{ row }">{{ row.stageNo }}. {{ row.stageName }}</template>
        </el-table-column>
        <el-table-column prop="operatorTag" label="算子" width="160" />
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="runTag(row.status)" size="small">{{ runName(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="attempt" label="尝试" width="60" align="center" />
        <el-table-column label="样本进度" min-width="220">
          <template #default="{ row }">
            <div v-if="row.progress" class="progress-cell">
              <el-progress :percentage="progressPercent(row.progress)" :stroke-width="6" :status="progressStatus(row.progress)" />
              <div class="progress-meta">{{ progressText(row.progress) }}</div>
            </div>
            <span v-else class="muted">—</span>
          </template>
        </el-table-column>
        <el-table-column label="摘要" min-width="220">
          <template #default="{ row }">
            <span v-if="row.summary" class="mono small">{{ summaryText(row.summary) }}</span>
            <span v-else class="muted">—</span>
          </template>
        </el-table-column>
        <el-table-column label="跳过/失败" width="130">
          <template #default="{ row }">
            <el-tag v-if="row.skipped?.length" type="info" size="small">跳过 {{ row.skipped.length }}</el-tag>
            <el-tag v-if="row.failed?.length" type="danger" size="small" style="margin-left: 4px">失败 {{ row.failed.length }}</el-tag>
            <span v-if="!row.skipped?.length && !row.failed?.length" class="muted">—</span>
          </template>
        </el-table-column>
        <el-table-column label="时间" width="230">
          <template #default="{ row }">
            <span class="small">{{ fmt(row.startTime) }}<br />{{ fmt(row.endTime) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="产物" width="80" fixed="right">
          <template #default="{ row }">
            <el-button size="small" link type="primary" :disabled="row.status === 'running'" @click="openFiles(row)">文件</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <div class="two-col">
      <!-- 数据集 -->
      <el-card shadow="never" class="block">
        <template #header><b>数据集（{{ task?.datasets?.length || 0 }}）</b></template>
        <el-table :data="task?.datasets || []" size="small">
          <el-table-column label="编号" min-width="190"><template #default="{ row }"><BizIdText :value="row.bizNo" /></template></el-table-column>
          <el-table-column prop="semVer" label="版本" width="80" />
          <el-table-column label="状态" width="90">
            <template #default="{ row }">
              <el-tag :type="DS_STATUS[row.status]?.tag" size="small">{{ DS_STATUS[row.status]?.name }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="有效/跳过" width="100" align="center">
            <template #default="{ row }">{{ row.itemCount }} / {{ row.skipCount }}</template>
          </el-table-column>
          <el-table-column label="操作" width="80">
            <template #default="{ row }">
              <el-button link type="primary" size="small" @click="openDataset(row.id)">明细</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <!-- 复核单 -->
      <el-card shadow="never" class="block">
        <template #header><b>条件复核单（{{ task?.reviewOrders?.length || 0 }}）</b></template>
        <el-table :data="task?.reviewOrders || []" size="small">
          <el-table-column label="编号" min-width="190"><template #default="{ row }"><BizIdText :value="row.bizNo" /></template></el-table-column>
          <el-table-column prop="stageName" label="环节" width="120" />
          <el-table-column label="状态" width="90">
            <template #default="{ row }">
              <el-tag :type="REVIEW_STATUS[row.status]?.tag" size="small">{{ REVIEW_STATUS[row.status]?.name }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="itemCount" label="条目" width="60" align="center" />
          <el-table-column label="操作" width="80">
            <template #default="{ row }">
              <el-button link type="primary" size="small" @click="openReview(row.id)">去复核</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </div>

    <!-- 参数快照 -->
    <el-card shadow="never" class="block">
      <template #header><b>参数快照（创建时锁定）</b></template>
      <el-table :data="task?.paramSnapshot || []" size="small">
        <el-table-column prop="name" label="参数名" width="240" />
        <el-table-column label="取值" min-width="200">
          <template #default="{ row }">
            <span class="mono">{{ typeof row.value === 'object' ? JSON.stringify(row.value) : row.value }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="desc" label="说明" min-width="220" />
      </el-table>
    </el-card>

    <!-- 驳回重跑 -->
    <el-dialog v-model="rejectVisible" title="驳回重跑" width="440px">
      <el-form label-width="90px">
        <el-form-item label="重跑起点">
          <el-select v-model="rejectStage" style="width: 100%">
            <el-option v-for="(n, i) in task?.stageNames || []" :key="i" :label="`第 ${i + 1} 环节 · ${n}`" :value="i + 1" />
          </el-select>
        </el-form-item>
      </el-form>
      <div class="hint">从所选环节开始重跑，之前环节复用已有产物；进行中的复核单将作废。</div>
      <template #footer>
        <el-button @click="rejectVisible = false">取消</el-button>
        <el-button type="warning" @click="doReject">确认驳回</el-button>
      </template>
    </el-dialog>

    <!-- 阈值调整 -->
    <el-dialog v-model="thresholdVisible" title="调整置信度阈值" width="400px">
      <el-input-number v-model="thresholdValue" :min="0" :max="1" :step="0.01" :precision="2" />
      <div class="hint">已有复核结论后阈值锁定，不可再调整。</div>
      <template #footer>
        <el-button @click="thresholdVisible = false">取消</el-button>
        <el-button type="primary" @click="saveThreshold">保存</el-button>
      </template>
    </el-dialog>

    <!-- 产物文件抽屉 -->
    <el-drawer v-model="filesVisible" :title="`产物文件 · 第 ${filesRun?.stageNo} 环节 ${filesRun?.operatorTag || ''}`" class="wbdz-drawer">
      <el-table :data="files" size="small" v-loading="filesLoading">
        <el-table-column prop="name" label="文件" min-width="260" show-overflow-tooltip />
        <el-table-column label="大小" width="90">
          <template #default="{ row }">{{ humanSize(row.size) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="140">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="previewFile(row)">预览</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-drawer>

    <!-- 文件预览 -->
    <el-dialog v-model="previewVisible" :title="previewName" width="70%" top="6vh">
      <img v-if="previewKind === 'image'" :src="previewUrl" style="max-width: 100%" />
      <iframe v-else-if="previewKind === 'pdf'" :src="previewUrl" class="preview-frame" />
      <pre v-else class="preview-text">{{ previewText }}</pre>
    </el-dialog>

    <!-- 数据集明细 -->
    <el-drawer v-model="dsVisible" title="数据集明细" class="wbdz-drawer">
      <div class="toolbar">
        <el-select v-model="dsFilter" placeholder="复核状态" clearable style="width: 150px" @change="loadDatasetItems(1)">
          <el-option label="已确认(A)" value="已确认" />
          <el-option label="已修正(B)" value="已修正" />
          <el-option label="已剔除(C)" value="已剔除" />
        </el-select>
        <el-tag size="small">共 {{ dsTotal }} 条</el-tag>
      </div>
      <el-table :data="dsItems" size="small">
        <el-table-column prop="itemKey" label="行标识" width="150" show-overflow-tooltip />
        <el-table-column label="复核状态" width="100">
          <template #default="{ row }">
            <el-tag size="small" :type="reviewTag(row.reviewStatus)">{{ row.reviewStatus || '—' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="置信度" width="80">
          <template #default="{ row }">{{ row.confidence ?? '—' }}</template>
        </el-table-column>
        <el-table-column label="数据" min-width="320">
          <template #default="{ row }">
            <span class="mono small">{{ compact(row.payload) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="70" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openDsItem(row)">查看</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination class="pager" layout="total, prev, pager, next" :total="dsTotal"
        v-model:current-page="dsPage" :page-size="10" @current-change="loadDatasetItems()" />
    </el-drawer>

    <DatasetItemViewer
      v-model="dsItemVisible"
      :item="dsItems[dsItemIndex]"
      :line="task?.line || ''"
      :run-id="dsRunId"
      :image-run-id="dsImageRunId"
      :can-prev="dsItemIndex > 0"
      :can-next="dsItemIndex < dsItems.length - 1"
      :can-add="task?.status !== 'collected'"
      @prev="dsItemIndex--"
      @next="dsItemIndex++"
      @add="addDsItemToReview"
    />
  </div>
</template>

<script setup lang="ts">
import PageHeader from '@/components/PageHeader.vue'
import BizIdText from '@/components/BizIdText.vue'
import { computed, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import DatasetItemViewer from '@/components/DatasetItemViewer.vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  TASK_STATUS, PRIORITIES, DS_STATUS, REVIEW_STATUS,
  taskDetail, taskSubmit, taskStart, taskReject, taskCollect, taskThreshold, taskDelete,
  artifactList, artifactBlob, datasetDetail, reviewAddFromDataset,
} from '@/api'

const props = defineProps<{ id: string }>()
const route = useRoute()
const router = useRouter()
const taskId = String(props.id || route.params.id)

const task = ref<any>(null)
const loading = ref(false)
const timer = ref<number>()

const rejectVisible = ref(false)
const rejectStage = ref(1)
const thresholdVisible = ref(false)
const thresholdValue = ref(0.8)

const filesVisible = ref(false)
const filesLoading = ref(false)
const filesRun = ref<any>(null)
const files = ref<{ name: string; size: number }[]>([])

const previewVisible = ref(false)
const previewName = ref('')
const previewKind = ref<'text' | 'image' | 'pdf' | 'other'>('text')
const previewText = ref('')
const previewUrl = ref('')

const dsVisible = ref(false)
const dsId = ref<string>()
const dsItems = ref<any[]>([])
const dsTotal = ref(0)
const dsPage = ref(1)
const dsFilter = ref('')
const dsItemVisible = ref(false)
const dsItemIndex = ref(0)
function lastDoneRun(tag?: string) {
  const done = (task.value?.stageRuns || []).filter((r: any) =>
    r.status === 'done' && (!tag || r.operatorTag === tag))
  return done.length ? done[done.length - 1].id : null
}

const dsRunId = computed(() => {
  if (task.value?.line === 'layout') return lastDoneRun('lay_page_detect')
  return lastDoneRun()
})

const dsImageRunId = computed(() =>
  task.value?.line === 'layout' ? lastDoneRun('lay_page_render') : null,
)

async function addDsItemToReview() {
  const item = dsItems.value[dsItemIndex.value]
  if (!item) return
  await reviewAddFromDataset(String(item.id))
  ElMessage.success('已加入复核任务')
  dsItemVisible.value = false
  await loadDatasetItems()
  await load()
}

function openDsItem(row: any) {
  const idx = dsItems.value.indexOf(row)
  dsItemIndex.value = idx < 0 ? 0 : idx
  dsItemVisible.value = true
}

function runsOf(stage: number) {
  return (task.value?.stageRuns || []).filter((r: any) => r.stageNo === stage)
}

function runTag(s: string) {
  return ({ running: 'warning', done: 'success', error: 'danger' } as Record<string, string>)[s] || 'info'
}

function runName(s: string) {
  return ({ running: '执行中', done: '完成', error: '失败' } as Record<string, string>)[s] || s
}

function progressPercent(p: any) {
  if (p?.status === 'completed') return 100
  const total = Number(p?.total || 0)
  const processed = Number(p?.processed || 0)
  return total > 0 ? Math.min(100, Math.round((processed / total) * 100)) : 0
}

function progressStatus(p: any) {
  if (p?.status === 'completed') return 'success'
  if (p?.status === 'failed') return 'exception'
  return undefined
}

function progressText(p: any) {
  const total = Number(p?.total || 0)
  const processed = Number(p?.processed || 0)
  const succeeded = Number(p?.succeeded || 0)
  const skipped = Number(p?.skipped || 0)
  const failed = Number(p?.failed || 0)
  const current = p?.currentItem ? ` · 当前 ${p.currentItem}` : ''
  if (p?.status === 'running') return `已处理 ${processed}/${total}${current}`
  return `已处理 ${processed}/${total} · 成功 ${succeeded} · 跳过 ${skipped} · 失败 ${failed}${current}`
}
function summaryText(summary: Record<string, any>) {
  return Object.entries(summary).slice(0, 6).map(([k, v]) => `${k}=${typeof v === 'object' ? JSON.stringify(v) : v}`).join('  ')
}

function fmt(v?: string) {
  if (!v || v === 'null') return '—'
  return v.replace('T', ' ').slice(0, 19)
}

function humanSize(n: number) {
  if (n >= 1024 * 1024) return (n / 1024 / 1024).toFixed(1) + ' MB'
  if (n >= 1024) return (n / 1024).toFixed(1) + ' KB'
  return n + ' B'
}

function compact(v: any) {
  const s = JSON.stringify(v || {})
  return s.length > 260 ? s.slice(0, 260) + '…' : s
}

function reviewTag(s?: string) {
  return s === '已确认' ? 'success' : s === '已修正' ? 'warning' : s === '已剔除' ? 'danger' : 'info'
}

async function load() {
  loading.value = true
  try {
    task.value = await taskDetail(taskId)
    schedulePoll()
  } finally {
    loading.value = false
  }
}

function schedulePoll() {
  window.clearTimeout(timer.value)
  if (task.value?.running || task.value?.status === 'processing') {
    timer.value = window.setTimeout(load, 5000)
  }
}

async function act(kind: 'submit' | 'start' | 'collect' | 'delete') {
  if (kind === 'delete') {
    await ElMessageBox.confirm(`确认删除任务「${task.value.name}」？`, '删除确认', { type: 'warning' })
    await taskDelete(taskId)
    ElMessage.success('已删除')
    router.push(route.query.fromWb as string || '/')
    return
  }
  if (kind === 'start') {
    await ElMessageBox.confirm('确认启动任务？将按算子链依次执行全部环节。', '启动确认', { type: 'warning' })
    await taskStart(taskId)
    ElMessage.success('已启动')
  }
  if (kind === 'submit') { await taskSubmit(taskId); ElMessage.success('已提交') }
  if (kind === 'collect') { await taskCollect(taskId); ElMessage.success('已归集') }
  load()
}

function openReject() {
  rejectStage.value = 1
  rejectVisible.value = true
}

async function doReject() {
  await taskReject(taskId, rejectStage.value)
  ElMessage.success('已驳回，从所选环节重跑')
  rejectVisible.value = false
  load()
}

function openThreshold() {
  thresholdValue.value = Number(task.value.threshold)
  thresholdVisible.value = true
}

async function saveThreshold() {
  await taskThreshold(taskId, thresholdValue.value)
  ElMessage.success('阈值已更新')
  thresholdVisible.value = false
  load()
}

async function openFiles(run: any) {
  filesRun.value = run
  filesVisible.value = true
  filesLoading.value = true
  try {
    files.value = await artifactList(run.id)
  } finally {
    filesLoading.value = false
  }
}

function closePreview() {
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
  previewUrl.value = ''
}

async function previewFile(file: { name: string; size: number }) {
  const blob = await artifactBlob(filesRun.value.id, file.name)
  const ext = file.name.split('.').pop()?.toLowerCase() || ''
  previewName.value = file.name
  if (['png', 'jpg', 'jpeg', 'gif'].includes(ext)) {
    closePreview()
    previewKind.value = 'image'
    previewUrl.value = URL.createObjectURL(blob)
  } else if (ext === 'pdf') {
    closePreview()
    previewKind.value = 'pdf'
    previewUrl.value = URL.createObjectURL(blob)
  } else if (['json', 'jsonl', 'txt', 'md', 'csv'].includes(ext)) {
    previewKind.value = 'text'
    previewText.value = await blob.text()
  } else {
    previewKind.value = 'other'
    previewText.value = '该文件类型暂不支持站内预览。可查看产物清单或联系管理员处理。'
  }
  previewVisible.value = true
}

async function openDataset(id: string) {
  dsId.value = id
  dsFilter.value = ''
  dsVisible.value = true
  loadDatasetItems(1)
}

async function loadDatasetItems(page?: number) {
  if (page) dsPage.value = page
  const d = await datasetDetail(dsId.value!, {
    reviewStatus: dsFilter.value || undefined, pageNum: dsPage.value, pageSize: 10,
  })
  dsItems.value = d.items.records
  dsTotal.value = d.items.total
}

function openReview(orderId: string) {
  router.push({ path: '/review', query: { orderId } })
}

load()
onUnmounted(() => {
  window.clearTimeout(timer.value)
  closePreview()
})
</script>

<style scoped>


.sub { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
.mono { font-family: var(--wbdz-font-mono); }
.small { font-size: var(--wbdz-font-caption); }
.muted { color: var(--wbdz-secondary); }

.desc { margin-top: 14px; }
.block { margin-top: 14px; }
.stages { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.stage { border: 1px solid var(--wbdz-border); border-radius: 8px; padding: 12px 14px; position: relative; background: var(--wbdz-bg-page); }
.stage.done { border-color: var(--wbdz-success); background: var(--wbdz-success-light); }
.stage.current { border-color: var(--wbdz-primary); background: var(--wbdz-primary-light); }
.stage-no { width: 24px; height: 24px; line-height: 24px; text-align: center; border-radius: 50%; background: var(--wbdz-primary); color: #fff; font-size: var(--wbdz-font-body); }
.stage.done .stage-no { background: var(--wbdz-success); }
.stage-name { margin-top: 8px; font-weight: 600; color: var(--wbdz-title); }
.stage-sub { font-size: var(--wbdz-font-caption); color: var(--wbdz-secondary); margin-top: 2px; }
.two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.toolbar { display: flex; gap: 10px; margin-bottom: 12px; }
.pager { margin-top: 12px; justify-content: flex-end; }
.progress-cell { min-width: 180px; }
.progress-meta { margin-top: 4px; color: var(--wbdz-secondary); font-size: var(--wbdz-font-caption); }
.preview-text { max-height: 62vh; overflow: auto; background: var(--wbdz-bg-page); padding: 12px; font-size: var(--wbdz-font-caption); line-height: 1.6; white-space: pre-wrap; word-break: break-all; }
.preview-frame { width: 100%; height: 70vh; border: 0; border-radius: var(--wbdz-radius-control); background: #fff; }
.hint { font-size: var(--wbdz-font-caption); color: var(--wbdz-secondary); }
</style>
