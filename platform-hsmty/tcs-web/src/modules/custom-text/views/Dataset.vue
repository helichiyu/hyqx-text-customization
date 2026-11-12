<template>
  <div class="page-stack">
    <PageHeader
      title="数据集管理"
      description="管理候选、已发布和已回滚数据集，查看质量报告、交付记录与回滚留痕。"
    />

    <el-tabs
      v-model="tab"
      @tab-change="onTabChange"
    >
      <el-tab-pane
        label="数据集"
        name="datasets"
      >
        <el-card shadow="never">
          <div class="search-panel">
            <div class="search-fields">
              <div class="filter-field">
                <label class="filter-label">产线</label>
                <el-select
                  v-model="query.line"
                  placeholder="全部产线"
                  clearable
                  style="width: 160px"
                  @change="load(1)"
                >
                  <el-option
                    v-for="(n, l) in LINE_NAMES"
                    :key="l"
                    :label="n"
                    :value="l"
                  />
                </el-select>
              </div>
              <div class="filter-field">
                <label class="filter-label">状态</label>
                <el-select
                  v-model="query.status"
                  placeholder="全部状态"
                  clearable
                  style="width: 160px"
                  @change="load(1)"
                >
                  <el-option
                    v-for="(s, k) in DS_STATUS"
                    :key="k"
                    :label="s.name"
                    :value="k"
                  />
                </el-select>
              </div>
              <div class="filter-field">
                <label class="filter-label">编号 / 版本</label>
                <el-input
                  v-model="query.keyword"
                  placeholder="请输入编号或版本"
                  clearable
                  style="width: 200px"
                  @keyup.enter="load(1)"
                />
              </div>
            </div>
            <div class="search-actions">
              <el-button @click="resetQuery">
                重置
              </el-button>
              <el-button @click="load()">
                刷新
              </el-button>
            </div>
          </div>

          <el-table
            v-loading="loading"
            :data="rows"
          >
            <el-table-column
              label="数据集编号"
              width="210"
            >
              <template #default="{ row }">
                <BizIdText :value="row.bizNo" />
              </template>
            </el-table-column>
            <el-table-column
              prop="lineName"
              label="产线"
              width="110"
            />
            <el-table-column
              prop="semVer"
              label="语义版本"
              width="100"
            />
            <el-table-column
              label="状态"
              width="100"
            >
              <template #default="{ row }">
                <el-tag
                  :type="DS_STATUS[row.status]?.tag"
                  effect="light"
                >
                  {{ row.statusName }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column
              label="有效/跳过"
              width="110"
              align="center"
            >
              <template #default="{ row }">
                {{ row.itemCount }} / {{ row.skipCount }}
              </template>
            </el-table-column>
            <el-table-column
              prop="publishBy"
              label="发布人"
              width="90"
            />
            <el-table-column
              prop="publishTime"
              label="发布时间"
              width="170"
              :formatter="timeFmt"
            />
            <el-table-column
              prop="createTime"
              label="创建时间"
              width="170"
              :formatter="timeFmt"
            />
            <el-table-column
              label="操作"
              width="430"
            >
              <template #default="{ row }">
                <el-button
                  link
                  type="primary"
                  size="small"
                  @click="openDetail(row)"
                >
                  预览
                </el-button>
                <el-button
                  v-if="row.status === 'candidate'"
                  link
                  type="primary"
                  size="small"
                  @click="doPublish(row)"
                >
                  发布
                </el-button>
                <el-button
                  v-if="row.status === 'published'"
                  link
                  type="primary"
                  size="small"
                  @click="downloadReport(row)"
                >
                  下载报告
                </el-button>
                <el-button
                  v-if="row.status === 'published'"
                  link
                  type="primary"
                  size="small"
                  @click="openDeliveryRecords(row)"
                >
                  交付记录
                </el-button>
                <el-button
                  v-if="row.status === 'published'"
                  link
                  type="danger"
                  size="small"
                  @click="doRollback(row)"
                >
                  回滚
                </el-button>
                <el-button
                  v-if="row.status !== 'published'"
                  link
                  type="danger"
                  size="small"
                  @click="doDelete(row)"
                >
                  删除
                </el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-pagination
            v-model:current-page="query.pageNum"
            class="pager"
            layout="total, prev, pager, next"
            :total="total"
            :page-size="query.pageSize"
            @current-change="load()"
          />
        </el-card>
      </el-tab-pane>

      <el-tab-pane
        label="交付记录"
        name="deliveries"
      >
        <el-card shadow="never">
          <el-table
            v-loading="deliveryLoading"
            :data="deliveries"
          >
            <el-table-column
              label="交付编号"
              width="210"
            >
              <template #default="{ row }">
                <BizIdText :value="row.bizNo" />
              </template>
            </el-table-column>
            <el-table-column
              prop="datasetBizNo"
              label="数据集"
              width="190"
            />
            <el-table-column
              prop="lineName"
              label="产线"
              width="110"
            />
            <el-table-column
              prop="type"
              label="交付类型"
              width="140"
            />
            <el-table-column
              prop="filename"
              label="文件名"
              min-width="200"
            />
            <el-table-column
              prop="operator"
              label="操作人"
              width="90"
            />
            <el-table-column
              prop="time"
              label="时间"
              width="170"
              :formatter="timeFmt"
            />
          </el-table>
          <el-pagination
            v-model:current-page="deliveryPageNum"
            class="pager"
            layout="total, prev, pager, next"
            :total="deliveryTotal"
            :page-size="10"
            @current-change="loadDeliveries()"
          />
        </el-card>
      </el-tab-pane>
    </el-tabs>

    <!-- 数据集站内预览 -->
    <el-dialog
      v-model="detailVisible"
      :title="`数据集站内预览 · ${detail?.bizNo || ''}`"
      width="1120px"
      top="5vh"
      class="tcs-dialog dataset-preview-dialog"
      @closed="detail = null"
    >
      <template v-if="detail">
        <el-descriptions
          :column="2"
          border
          size="small"
          class="preview-meta"
        >
          <el-descriptions-item label="所属产线">
            {{ detail.lineName }}
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="DS_STATUS[detail.status]?.tag">
              {{ detail.statusName }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="来源任务">
            <template v-if="detail.task">
              <BizIdText :value="detail.task.bizNo" />
            </template><template v-else>
              —
            </template>
          </el-descriptions-item>
          <el-descriptions-item label="来源任务名称">
            {{ detail.task?.name || '—' }}
          </el-descriptions-item>
          <el-descriptions-item label="质量版本">
            <el-tag effect="plain">
              {{ detail.semVer || '—' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="内容条数">
            {{ detail.itemCount ?? 0 }}<span
              v-if="detail.skipCount"
              class="preview-muted"
            >（已剔除 C 跳过 {{ detail.skipCount }} 条）</span>
          </el-descriptions-item>
        </el-descriptions>

        <section class="preview-panel">
          <div class="preview-panel-title">
            条件复核
          </div>
          <div
            v-if="!openReviewOrders.length"
            class="review-clear"
          >
            无未闭环条件复核单
          </div>
          <el-table
            v-else
            :data="openReviewOrders"
            size="small"
            border
          >
            <el-table-column
              label="复核单编号"
              width="210"
            >
              <template #default="{ row }">
                <BizIdText :value="row.bizNo" />
              </template>
            </el-table-column>
            <el-table-column
              prop="stageName"
              label="触发环节"
              width="140"
            />
            <el-table-column
              label="状态"
              width="100"
            >
              <template #default="{ row }">
                <el-tag
                  size="small"
                  :type="REVIEW_STATUS[row.status]?.tag"
                >
                  {{ REVIEW_STATUS[row.status]?.name || row.status }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column
              prop="itemCount"
              label="条目"
              width="80"
              align="center"
            />
            <el-table-column
              label="操作"
              width="80"
            >
              <template #default="{ row }">
                <el-button
                  link
                  type="primary"
                  size="small"
                  @click="openReviewOrder(row.bizNo)"
                >
                  去复核
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </section>

        <section class="preview-panel">
          <div class="preview-panel-title">
            结果结构预览（最多展示 5 条）
          </div>
          <el-table
            :data="items.slice(0, 5)"
            size="small"
            border
          >
            <el-table-column
              prop="itemKey"
              label="数据条目ID"
              width="210"
              show-overflow-tooltip
            />
            <el-table-column
              v-for="column in previewColumns"
              :key="column.key"
              :label="column.label"
              min-width="150"
            >
              <template #default="{ row }">
                <span class="preview-value">{{ previewValue(row, column.key) }}</span>
              </template>
            </el-table-column>
            <el-table-column
              label="置信度"
              width="86"
              align="center"
            >
              <template #default="{ row }">
                {{ itemConfidence(row) }}
              </template>
            </el-table-column>
            <el-table-column
              label="操作"
              width="70"
              fixed="right"
            >
              <template #default="{ row }">
                <el-button
                  link
                  type="primary"
                  size="small"
                  @click="openViewer(row)"
                >
                  查看
                </el-button>
              </template>
            </el-table-column>
          </el-table>
          <div class="preview-caption">
            共 {{ detail.itemCount ?? itemTotal }} 条；此处仅展示前 5 条结构预览，点击“查看”可查看完整条目。
          </div>
        </section>

        <div class="preview-hint">
          各状态版本均可站内预览；仅已发布版本可下载 TXT 质量报告，报告不包含原始业务数据。在线预览不登记交付记录。
        </div>
      </template>
      <template #footer>
        <el-button @click="detailVisible = false">
          关闭
        </el-button>
        <el-button
          v-if="detail?.status === 'candidate'"
          type="success"
          @click="doPublish(detail)"
        >
          发布
        </el-button>
        <el-button
          v-if="detail?.status === 'published'"
          type="primary"
          @click="downloadReport(detail)"
        >
          下载质量报告
        </el-button>
      </template>
    </el-dialog>

    <!-- 单数据集交付记录 -->
    <el-dialog
      v-model="deliveryDialogVisible"
      :title="`交付记录 · ${deliveryDialogDataset?.bizNo || ''}`"
      width="1120px"
      top="6vh"
      class="tcs-dialog"
    >
      <el-table
        v-loading="deliveryDialogLoading"
        :data="deliveryDialogRows"
        size="small"
      >
        <el-table-column
          label="交付编号"
          width="210"
        >
          <template #default="{ row }">
            <BizIdText :value="row.bizNo" />
          </template>
        </el-table-column>
        <el-table-column
          prop="type"
          label="交付类型"
          width="140"
        />
        <el-table-column
          prop="filename"
          label="文件名"
          min-width="380"
          show-overflow-tooltip
        />
        <el-table-column
          prop="operator"
          label="操作人"
          width="90"
        />
        <el-table-column
          prop="time"
          label="时间"
          width="180"
          :formatter="timeFmt"
        />
      </el-table>
      <template #footer>
        <el-button @click="deliveryDialogVisible = false">
          关闭
        </el-button>
      </template>
    </el-dialog>

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
  </div>
</template>

<script setup lang="ts">
import PageHeader from '../components/PageHeader.vue'
import BizIdText from '../components/BizIdText.vue'
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import DatasetItemViewer from '../components/DatasetItemViewer.vue'
import {
  LINE_NAMES, DS_STATUS, REVIEW_STATUS,
  datasetPage, datasetDetail, datasetPublish, datasetRollback, datasetDelete, datasetReport,
  deliveryPage,
  taskDetail, reviewAddFromDataset, saveBlob,
} from '../api'

const router = useRouter()
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
const reviewOrders = ref<any[]>([])
const viewerVisible = ref(false)
const viewerIndex = ref(0)
const deliveryDialogVisible = ref(false)
const deliveryDialogLoading = ref(false)
const deliveryDialogRows = ref<any[]>([])
const deliveryDialogDataset = ref<any>(null)

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

const openReviewOrders = computed(() => reviewOrders.value.filter((order: any) =>
  order.status === 'pending' || order.status === 'doing'))

const previewColumns = computed(() => {
  const line = detail.value?.line
  if (line === 'formula') return [
    { key: 'latex', label: '公式 LaTeX 表达' },
    { key: 'symbols', label: '变量符号·含义·单位' },
    { key: 'context', label: '章节/编号/上下文定位' },
  ]
  if (line === 'layout') return [
    { key: 'pageNo', label: '页码' },
    { key: 'elements', label: '元素与结构' },
    { key: 'readingOrder', label: '阅读顺序' },
  ]
  if (line === 'graphic') return [
    { key: 'imageType', label: '图片类型' },
    { key: 'description', label: '结构化描述' },
    { key: 'ocr', label: '提取文字（OCR）' },
  ]
  return [
    { key: 'basic', label: '基础分类' },
    { key: 'related', label: '主题与关联' },
    { key: 'structured', label: '结构化元信息' },
  ]
})

function clipPreview(value: any, max = 90) {
  if (value == null || value === '') return '—'
  const text = typeof value === 'object' ? JSON.stringify(value) : String(value)
  return text.length > max ? text.slice(0, max) + '…' : text
}

function previewValue(row: any, key: string) {
  const payload = row?.payload || {}
  if (key === 'latex') return clipPreview(payload.latex)
  if (key === 'symbols') return clipPreview(payload.symbols)
  if (key === 'context') return clipPreview(payload.context)
  if (key === 'pageNo') return payload.pageNo ?? '—'
  if (key === 'elements') return `${payload.elementCount ?? payload.elements?.length ?? 0} 个元素${payload.lowConfidenceCount ? ` · 低置信 ${payload.lowConfidenceCount}` : ''}`
  if (key === 'readingOrder') return clipPreview(payload.readingOrder)
  if (key === 'imageType') return clipPreview(payload.imageType || payload.type)
  if (key === 'description') return clipPreview(payload.description || payload.desc)
  if (key === 'ocr') return clipPreview(payload.ocr || payload.text)
  if (key === 'basic') return clipPreview(payload.basic)
  if (key === 'related') return clipPreview(payload.related)
  if (key === 'structured') return clipPreview(payload.structured)
  return clipPreview(payload[key])
}

function itemConfidence(row: any) {
  const payload = row?.payload || {}
  const line = detail.value?.line
  const value = line === 'layout' ? payload.confidence?.bbox
    : line === 'graphic' ? payload.confidence?.ocr
    : line === 'metadata' ? payload.fillConfidence
    : payload.recognitionConfidence
  const number = value == null ? Number(row?.confidence) : Number(value)
  return Number.isFinite(number) ? number.toFixed(2) : '—'
}

function openReviewOrder(orderBizNo: string) {
  router.push({ path: '/custom-text/review', query: { orderBizNo } })
}

async function load(page?: number) {
  if (page) query.pageNum = page
  loading.value = true
  try {
    const res = await datasetPage({
      line: query.line || undefined, status: query.status || undefined,
      keyword: query.keyword || undefined, page: query.pageNum, limit: query.pageSize,
    })
    rows.value = res.rows
    total.value = Number(res.total)
  } finally {
    loading.value = false
  }
}

async function addToReview() {
  const item = items.value[viewerIndex.value]
  if (!item) return
  await reviewAddFromDataset(String(item.id))
  ElMessage.success('已加入复核任务')
  viewerVisible.value = false
  detail.value = await datasetDetail(detail.value.bizNo)
  await loadItems()
  await loadReviewOrders()
}

function openViewer(row: any) {
  const idx = items.value.indexOf(row)
  viewerIndex.value = idx < 0 ? 0 : idx
  viewerVisible.value = true
}

async function loadDeliveries(page?: number) {
  if (page) deliveryPageNum.value = page
  deliveryLoading.value = true
  try {
    const res = await deliveryPage({ page: deliveryPageNum.value, limit: 10 })
    deliveries.value = res.rows
    deliveryTotal.value = Number(res.total)
  } finally {
    deliveryLoading.value = false
  }
}

async function openDeliveryRecords(row: any) {
  deliveryDialogDataset.value = row
  deliveryDialogRows.value = []
  deliveryDialogVisible.value = true
  deliveryDialogLoading.value = true
  try {
    const res = await deliveryPage({ page: 1, limit: 500 })
    deliveryDialogRows.value = res.rows.filter((item: any) => item.datasetBizNo === row.bizNo)
  } finally {
    deliveryDialogLoading.value = false
  }
}

function onTabChange(name: string | number) {
  if (name === 'deliveries') loadDeliveries(1)
  else load()
}

async function openDetail(row: any) {
  detail.value = await datasetDetail(row.bizNo)
  items.value = []
  itemTotal.value = 0
  detailVisible.value = true
  await Promise.all([loadItems(), loadReviewOrders()])
}

async function loadItems() {
  if (!detail.value) return
  const d = await datasetDetail(detail.value.bizNo, { page: 1, limit: 5 })
  items.value = d.items?.rows || []
  itemTotal.value = d.items?.total || 0
}

async function loadReviewOrders() {
  reviewOrders.value = []
  if (detail.value?.task?.bizNo) {
    const task = await taskDetail(detail.value.task.bizNo)
    reviewOrders.value = task.reviewOrders || []
  }
}

async function doPublish(row: any) {
  await ElMessageBox.confirm(`确认发布数据集「${row.bizNo}」？发布前须复核单全部闭环；发布后版本号将计入交付。`, '发布确认', { type: 'warning' })
  await datasetPublish(row.bizNo)
  ElMessage.success('已发布，来源任务状态已同步为已归集')
  if (detail.value?.bizNo === row.bizNo) detail.value = await datasetDetail(row.bizNo)
  load()
}

async function doDelete(row: any) {
  await ElMessageBox.confirm(
    `确认删除数据集「${row.bizNo}」？其条目会一并删除，且不可恢复；已发布的数据集请先回滚。`,
    '删除确认',
    { type: 'warning' },
  )
  await datasetDelete(row.bizNo)
  ElMessage.success('已删除')
  if (detail.value?.bizNo === row.bizNo) detail.value = null
  load()
}

async function doRollback(row: any) {
  const { value } = await ElMessageBox.prompt('请填写回滚原因（必填留痕）', '回滚数据集', {
    inputPlaceholder: '如：复核遗漏，需重新加工',
    inputValidator: (v) => (!!v && v.trim().length > 0) || '回滚原因不能为空',
  })
  await datasetRollback(row.bizNo, value.trim())
  ElMessage.success('已回滚')
  if (detail.value?.bizNo === row.bizNo) detail.value = await datasetDetail(row.bizNo)
  load()
}

function reportStamp() {
  const now = new Date()
  const pad = (value: number) => String(value).padStart(2, '0')
  return `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}_${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`
}

async function downloadReport(row: any) {
  const blob = await datasetReport(row.bizNo)
  saveBlob(blob, `${row.bizNo}_质量报告_${reportStamp()}.txt`)
  ElMessage.success('报告已下载（含交付记录）')
  if (detailVisible.value && detail.value?.bizNo === row.bizNo) {
    detail.value = await datasetDetail(row.bizNo)
    await loadReviewOrders()
  }
}

onMounted(() => load())
</script>

<style scoped>
.pager { margin-top: 14px; justify-content: flex-end; }
.mono { font-family: var(--tcs-font-mono); }
.small { font-size: var(--tcs-font-size-helper); }
.dataset-preview-dialog :deep(.el-dialog__body) { padding: 16px 20px 8px; }
.preview-meta { margin-bottom: 14px; }
.preview-panel { margin-top: 14px; padding: 14px; border: 1px solid var(--tcs-color-border); border-radius: 5px; background: #fff; }
.preview-panel-title { margin-bottom: 10px; color: var(--tcs-color-title); font-size: 15px; font-weight: 650; }
.review-clear { padding: 10px 12px; border: 1px dashed #b7ebc6; border-radius: 4px; background: #f0fdf4; color: #128a57; font-size: 13px; }
.preview-value { display: block; max-height: 52px; overflow: hidden; color: var(--tcs-color-text); font-size: var(--tcs-font-size-helper); line-height: 1.55; overflow-wrap: anywhere; }
.preview-caption { margin-top: 9px; color: var(--tcs-color-text-secondary); font-size: var(--tcs-font-size-helper); }
.preview-hint { margin-top: 14px; padding: 10px 12px; border: 1px solid #d6e4ff; border-radius: 4px; background: #f6f9ff; color: #4d6f94; font-size: var(--tcs-font-size-helper); line-height: 1.6; }
.preview-muted { margin-left: 3px; color: var(--tcs-color-text-secondary); font-size: var(--tcs-font-size-helper); }
</style>
