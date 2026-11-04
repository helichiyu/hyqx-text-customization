<template>
  <div class="page-stack">
    <PageHeader title="数据集管理" description="管理候选、已发布和已回滚数据集，查看质量报告、交付记录与回滚留痕。" />

    <el-tabs v-model="tab" @tab-change="onTabChange">
      <el-tab-pane label="数据集" name="datasets">
        <el-card shadow="never">
          <div class="search-panel">
            <div class="search-fields">
              <div class="filter-field">
                <label class="filter-label">产线</label>
                <el-select v-model="query.line" placeholder="全部产线" clearable style="width: 160px" @change="load(1)">
                  <el-option v-for="(n, l) in LINE_NAMES" :key="l" :label="n" :value="l" />
                </el-select>
              </div>
              <div class="filter-field">
                <label class="filter-label">状态</label>
                <el-select v-model="query.status" placeholder="全部状态" clearable style="width: 160px" @change="load(1)">
                  <el-option v-for="(s, k) in DS_STATUS" :key="k" :label="s.name" :value="k" />
                </el-select>
              </div>
              <div class="filter-field">
                <label class="filter-label">编号 / 版本</label>
                <el-input v-model="query.keyword" placeholder="请输入编号或版本" clearable style="width: 200px" @keyup.enter="load(1)" />
              </div>
            </div>
            <div class="search-actions">
              <el-button @click="resetQuery">重置</el-button>
              <el-button @click="load()">刷新</el-button>
            </div>
          </div>

          <el-table :data="rows" v-loading="loading">
            <el-table-column label="数据集编号" width="210"><template #default="{ row }"><BizIdText :value="row.bizNo" /></template></el-table-column>
            <el-table-column prop="lineName" label="产线" width="110" />
            <el-table-column prop="semVer" label="语义版本" width="100" />
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="DS_STATUS[row.status]?.tag" effect="light">{{ row.statusName }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="有效/跳过" width="110" align="center">
              <template #default="{ row }">{{ row.itemCount }} / {{ row.skipCount }}</template>
            </el-table-column>
            <el-table-column prop="publishBy" label="发布人" width="90" />
            <el-table-column prop="publishTime" label="发布时间" width="170" :formatter="timeFmt" />
            <el-table-column prop="createTime" label="创建时间" width="170" :formatter="timeFmt" />
            <el-table-column label="操作" width="300" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" size="small" @click="openDetail(row)">预览</el-button>
                <el-button v-if="row.status === 'candidate'" link type="primary" size="small" @click="doPublish(row)">发布</el-button>
                <el-button v-if="row.status === 'published'" link type="primary" size="small" @click="downloadReport(row)">报告</el-button>
                <el-button v-if="row.status === 'published'" link type="danger" size="small" @click="doRollback(row)">回滚</el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-pagination class="pager" layout="total, prev, pager, next" :total="total"
            v-model:current-page="query.pageNum" :page-size="query.pageSize" @current-change="load()" />
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="交付记录" name="deliveries">
        <el-card shadow="never">
          <el-table :data="deliveries" v-loading="deliveryLoading">
            <el-table-column label="交付编号" width="210"><template #default="{ row }"><BizIdText :value="row.bizNo" /></template></el-table-column>
            <el-table-column prop="datasetBizNo" label="数据集" width="190" />
            <el-table-column prop="lineName" label="产线" width="110" />
            <el-table-column prop="type" label="交付类型" width="140" />
            <el-table-column prop="filename" label="文件名" min-width="200" />
            <el-table-column prop="operator" label="操作人" width="90" />
            <el-table-column prop="time" label="时间" width="170" :formatter="timeFmt" />
          </el-table>
          <el-pagination class="pager" layout="total, prev, pager, next" :total="deliveryTotal"
            v-model:current-page="deliveryPageNum" :page-size="10" @current-change="loadDeliveries()" />
        </el-card>
      </el-tab-pane>
    </el-tabs>

    <!-- 详情抽屉 -->
    <el-drawer v-model="detailVisible" title="数据集详情" class="wbdz-drawer" @closed="detail = null">
      <template v-if="detail">
        <el-descriptions :column="3" border size="small">
          <el-descriptions-item label="编号"><BizIdText :value="detail.bizNo" /></el-descriptions-item>
          <el-descriptions-item label="产线">{{ detail.lineName }}</el-descriptions-item>
          <el-descriptions-item label="语义版本">{{ detail.semVer }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="DS_STATUS[detail.status]?.tag">{{ detail.statusName }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="有效条数">{{ detail.itemCount }}</el-descriptions-item>
          <el-descriptions-item label="跳过条数">{{ detail.skipCount }}</el-descriptions-item>
          <el-descriptions-item label="来源任务">
            {{ detail.task ? `${detail.task.bizNo} · ${detail.task.name}` : '—' }}
          </el-descriptions-item>
          <el-descriptions-item label="发布人">{{ detail.publishBy || '—' }}</el-descriptions-item>
          <el-descriptions-item label="发布时间">{{ fmtTime(detail.publishTime) }}</el-descriptions-item>
        </el-descriptions>

        <div class="toolbar" style="margin-top: 14px">
          <el-select v-model="itemFilter" placeholder="复核范围" clearable style="width: 150px" @change="loadItems(1)">
            <el-option label="已进入复核" value="待复核" />
            <el-option label="未进入复核" value="未进入复核" />
            <el-option label="已确认(A)" value="已确认" />
            <el-option label="已修正(B)" value="已修正" />
            <el-option label="已剔除(C)" value="已剔除" />
          </el-select>
          <el-tag size="small">共 {{ itemTotal }} 条（C 剔除 {{ detail.skipCount }} 条）</el-tag>
          <el-button link type="primary" size="small" @click="openSkips">跳过/失败清单（{{ skipRows.length }}）</el-button>
          <div style="flex: 1" />
          <el-button v-if="detail.task" size="small" @click="editThreshold">
            置信度阈值 {{ detail.task.threshold || '—' }}
          </el-button>
          <div style="flex: 1" />
          <el-button v-if="detail.status === 'candidate'" type="success" @click="doPublish(detail)">发布</el-button>
          <el-button v-if="detail.status === 'published'" @click="downloadReport(detail)">下载质量报告</el-button>
          <el-button v-if="detail.status === 'published'" type="danger" plain @click="doRollback(detail)">回滚</el-button>
        </div>

        <el-table :data="items" size="small" border max-height="420">
          <el-table-column type="expand">
            <template #default="{ row }">
              <pre class="json">{{ pretty(row.payload) }}</pre>
            </template>
          </el-table-column>
          <el-table-column prop="itemKey" label="行标识" width="160" show-overflow-tooltip />
          <el-table-column label="复核状态" width="100">
            <template #default="{ row }">
              <el-tag size="small" :type="reviewTag(row.reviewStatus)">{{ row.reviewStatus || '—' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="revisionStatus" label="修订" width="100" />
          <el-table-column prop="confidence" label="置信度" width="80" />
          <el-table-column label="数据" min-width="360">
            <template #default="{ row }">
              <span class="mono small">{{ compact(row.payload) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="70" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" size="small" @click="openViewer(row)">查看</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-pagination class="pager" layout="total, prev, pager, next" :total="itemTotal"
          v-model:current-page="itemPage" :page-size="10" @current-change="loadItems()" />

        <div class="two-col">
          <div>
            <h4>交付记录</h4>
            <el-empty v-if="!detail.deliveries?.length" description="暂无交付" :image-size="48" />
            <el-timeline v-else style="padding-left: 6px">
              <el-timeline-item v-for="d in detail.deliveries" :key="d.bizNo" :timestamp="fmtTime(d.time)">
                {{ d.type }}：{{ d.filename }}（{{ d.operator }}）
              </el-timeline-item>
            </el-timeline>
          </div>
          <div>
            <h4>回滚记录</h4>
            <el-empty v-if="!detail.rollbacks?.length" description="暂无回滚" :image-size="48" />
            <el-timeline v-else style="padding-left: 6px">
              <el-timeline-item v-for="r in detail.rollbacks" :key="r.bizNo" :timestamp="fmtTime(r.time)" type="danger">
                {{ r.reason }}（{{ r.operator }}）
              </el-timeline-item>
            </el-timeline>
          </div>
        </div>
      </template>
    </el-drawer>

    <DatasetItemViewer
      v-model="viewerVisible"
      :item="items[viewerIndex]"
      :line="detail?.line || ''"
      :run-id="detail?.runId"
      :image-run-id="detail?.imageRunId"
      :can-prev="viewerIndex > 0"
      :can-next="viewerIndex < items.length - 1"
      :can-add="detail?.status === 'candidate'"
      @prev="viewerIndex--"
      @next="viewerIndex++"
      @add="addToReview"
    />

    <!-- 跳过 / 失败清单（来自各环节执行记录） -->
    <el-dialog v-model="skipVisible" title="跳过 / 失败清单" class="wbdz-dialog">
      <el-empty v-if="!skipRows.length" description="该任务无跳过或失败记录" />
      <el-table v-else :data="skipRows" size="small" border max-height="460">
        <el-table-column prop="stage" label="环节" width="110" />
        <el-table-column prop="kind" label="类型" width="70">
          <template #default="{ row }">
            <el-tag size="small" :type="row.kind === '失败' ? 'danger' : 'info'">{{ row.kind }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="item" label="条目" min-width="180" show-overflow-tooltip />
        <el-table-column prop="reason" label="原因" min-width="260" show-overflow-tooltip />
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import PageHeader from '@/components/PageHeader.vue'
import BizIdText from '@/components/BizIdText.vue'
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import DatasetItemViewer from '@/components/DatasetItemViewer.vue'
import {
  LINE_NAMES, DS_STATUS,
  datasetPage, datasetDetail, datasetPublish, datasetRollback, deliveryPage,
  taskDetail, reviewAddFromDataset, taskThreshold, downloadBlob, saveBlob,
} from '@/api'

const tab = ref('datasets')

const query = reactive({ line: '', status: '', keyword: '', pageNum: 1, pageSize: 10 })
const rows = ref<any[]>([])
const total = ref(0)
const loading = ref(false)

const deliveries = ref<any[]>([])
const deliveryTotal = ref(0)
const deliveryPageNum = ref(1)
const deliveryLoading = ref(false)

const detailVisible = ref(false)
const detail = ref<any>(null)
const items = ref<any[]>([])
const itemTotal = ref(0)
const itemPage = ref(1)
const itemFilter = ref('')
const skipVisible = ref(false)
const skipRows = ref<any[]>([])
const viewerVisible = ref(false)
const viewerIndex = ref(0)

function resetQuery() {
  query.line = ''
  query.status = ''
  query.keyword = ''
  load(1)
}
function timeFmt(_r: any, _c: any, v: string) {
  return fmtTime(v)
}

function fmtTime(v?: string) {
  if (!v || v === 'null' || v === 'undefined') return '—'
  return v.replace('T', ' ').slice(0, 19)
}

function pretty(v: any) {
  return JSON.stringify(v || {}, null, 2)
}

function compact(v: any) {
  const s = JSON.stringify(v || {})
  return s.length > 320 ? s.slice(0, 320) + '…' : s
}

function reviewTag(s?: string) {
  return s === '已确认' ? 'success' : s === '已修正' ? 'warning' : s === '已剔除' ? 'danger' : 'info'
}

async function load(page?: number) {
  if (page) query.pageNum = page
  loading.value = true
  try {
    const res = await datasetPage({
      line: query.line || undefined, status: query.status || undefined,
      keyword: query.keyword || undefined, pageNum: query.pageNum, pageSize: query.pageSize,
    })
    rows.value = res.records
    total.value = Number(res.total)
  } finally {
    loading.value = false
  }
}

/** 任务级低置信阈值：任一复核结论后后端拒绝修改（阈值锁定）。 */
async function editThreshold() {
  const taskId = detail.value?.task?.id
  if (!taskId) return
  const { value } = await ElMessageBox.prompt('阈值取值 (0,1]，已有复核结论后锁定。', '调整置信度阈值', {
    inputValue: String(detail.value.task.threshold || 0.8),
    inputPattern: /^(0?\.\d+|1(\.0+)?)$/,
    inputErrorMessage: '请输入 0–1 之间的数值',
  })
  await taskThreshold(String(taskId), Number(value))
  ElMessage.success('阈值已更新')
  detail.value = await datasetDetail(detail.value.id)
}

async function addToReview() {
  const item = items.value[viewerIndex.value]
  if (!item) return
  await reviewAddFromDataset(String(item.id))
  ElMessage.success('已加入复核任务')
  viewerVisible.value = false
  detail.value = await datasetDetail(detail.value.id)
  await loadItems()
}

function openViewer(row: any) {
  const idx = items.value.indexOf(row)
  viewerIndex.value = idx < 0 ? 0 : idx
  viewerVisible.value = true
}

/** 跳过/失败清单：聚合来源任务各环节执行记录（重跑记录同样展示，带环节名）。 */
async function openSkips() {
  const taskId = detail.value?.task?.id
  if (!taskId) return
  const t = await taskDetail(taskId)
  const out: any[] = []
  for (const run of t.stageRuns || []) {
    const collect = (arr: any[], kind: string) => {
      for (const e of arr || []) {
        if (e == null) continue
        const obj = typeof e === 'object' ? e : { reason: String(e) }
        const item = obj.fileName || obj.name || obj.docId || obj.pageId || obj.imageId
          || obj.instanceId || obj.uniqueId || '—'
        const reason = obj.reason || obj.code || obj.error
          || (typeof e === 'string' ? e : JSON.stringify(e))
        out.push({ stage: run.stageName || `环节${run.stageNo}`, kind, item, reason })
      }
    }
    collect(run.skipped, '跳过')
    collect(run.failed, '失败')
  }
  skipRows.value = out
  skipVisible.value = true
}

async function loadDeliveries(page?: number) {
  if (page) deliveryPageNum.value = page
  deliveryLoading.value = true
  try {
    const res = await deliveryPage({ pageNum: deliveryPageNum.value, pageSize: 10 })
    deliveries.value = res.records
    deliveryTotal.value = Number(res.total)
  } finally {
    deliveryLoading.value = false
  }
}

function onTabChange(name: string | number) {
  if (name === 'deliveries') loadDeliveries(1)
  else load()
}

async function openDetail(row: any) {
  detail.value = await datasetDetail(row.id)
  itemFilter.value = ''
  items.value = []
  itemTotal.value = 0
  skipRows.value = []
  detailVisible.value = true
  loadItems(1)
}

async function loadItems(page?: number) {
  if (!detail.value) return
  if (page) itemPage.value = page
  const d = await datasetDetail(detail.value.id, {
    reviewStatus: itemFilter.value || undefined, pageNum: itemPage.value, pageSize: 10,
  })
  items.value = d.items.records
  itemTotal.value = d.items.total
}

async function doPublish(row: any) {
  await ElMessageBox.confirm(`确认发布数据集「${row.bizNo}」？发布前须复核单全部闭环；发布后版本号将计入交付。`, '发布确认', { type: 'warning' })
  await datasetPublish(row.id)
  ElMessage.success('已发布')
  if (detail.value?.id === row.id) detail.value = await datasetDetail(row.id)
  load()
}

async function doRollback(row: any) {
  const { value } = await ElMessageBox.prompt('请填写回滚原因（必填留痕）', '回滚数据集', {
    inputPlaceholder: '如：复核遗漏，需重新加工',
    inputValidator: (v) => (!!v && v.trim().length > 0) || '回滚原因不能为空',
  })
  await datasetRollback(row.id, value.trim())
  ElMessage.success('已回滚')
  if (detail.value?.id === row.id) detail.value = await datasetDetail(row.id)
  load()
}

async function downloadReport(row: any) {
  const blob = await downloadBlob(`/api/dataset/${row.id}/report`)
  saveBlob(blob, `质量报告_${row.bizNo}_${row.semVer || ''}.txt`)
  ElMessage.success('报告已下载（含交付记录）')
  if (detailVisible.value && detail.value?.id === row.id) detail.value = await datasetDetail(row.id)
}

onMounted(() => load())
</script>

<style scoped>

.pager { margin-top: 14px; justify-content: flex-end; }
.mono { font-family: var(--wbdz-font-mono); }
.small { font-size: var(--wbdz-font-caption); }
.json { background: var(--wbdz-bg-page); padding: 10px; font-size: var(--wbdz-font-caption); margin: 0 0 0 48px; max-height: 240px; overflow: auto; white-space: pre-wrap; word-break: break-all; }
.two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-top: 8px; }
h4 { margin: 16px 0 8px; color: var(--wbdz-title); font-size: var(--wbdz-font-body); }
</style>
