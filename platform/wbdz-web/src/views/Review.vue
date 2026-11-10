<template>
  <div class="page-stack">
    <PageHeader title="条件复核" description="集中处理低置信、冲突和输出修复样本，完成 A/B/C 结论与整单闭环。" />

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
              <el-option v-for="(s, k) in REVIEW_STATUS" :key="k" :label="s.name" :value="k" />
            </el-select>
          </div>
        </div>
        <div class="search-actions">
          <el-button @click="resetQuery">重置</el-button>
          <el-button @click="load()">刷新</el-button>
        </div>
      </div>

      <el-table :data="rows" v-loading="loading">
        <el-table-column label="复核单号" width="210"><template #default="{ row }"><BizIdText :value="row.bizNo" /></template></el-table-column>
        <el-table-column prop="lineName" label="产线" width="110" />
        <el-table-column prop="stageName" label="触发环节" width="130" />
        <el-table-column label="触发条件" min-width="220" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="mono small">{{ row.triggerCode }}</span>
            <span class="muted"> · {{ row.triggerDesc }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="itemCount" label="条目" width="70" align="center" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="REVIEW_STATUS[row.status]?.tag" effect="light">{{ row.statusName }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="createTime" label="创建时间" width="170" :formatter="timeFmt" />
        <el-table-column prop="closeBy" label="闭环人" width="90" />
        <el-table-column label="操作" width="110" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openOrder(row.bizNo)">
              {{ row.status === 'done' || row.status === 'void' ? '查看' : '复核' }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination class="pager" layout="total, prev, pager, next" :total="total"
        v-model:current-page="query.pageNum" :page-size="query.pageSize" @current-change="load()" />
    </el-card>

    <!-- 复核工作台 -->
    <el-drawer v-model="orderVisible" class="wbdz-drawer wbdz-drawer--wide review-workbench-drawer" @closed="onDrawerClosed">
      <template #header>
        <div class="workbench-head">
          <div>
            <div class="workbench-title">条件复核<template v-if="order"> · <BizIdText :value="order.bizNo" /></template></div>
            <div class="workbench-subtitle">左侧查看原始素材，右侧核对系统结果；A 确认无误，B 直接修正，C 跳过。</div>
          </div>
        </div>
      </template>
      <template v-if="order">
        <section class="review-context-card">
          <div class="review-context-main">
            <div class="context-line">
              <span><b>来源任务：</b><BizIdText :value="order.taskBizNo || order.taskId || '—'" /></span>
              <span><b>产线：</b>{{ order.lineName }}</span>
              <span><b>触发环节：</b>{{ order.stageName }}</span>
              <span><b>状态：</b><el-tag :type="REVIEW_STATUS[order.status]?.tag" size="small">{{ order.statusName }}</el-tag></span>
            </div>
            <div class="context-reason"><b>触发原因：</b><span class="mono small">{{ order.triggerCode }}</span> · {{ order.triggerDesc }}</div>
          </div>
          <el-button v-if="!locked" type="warning" plain @click="rerunSourceTask">重跑来源任务</el-button>
        </section>

        <div class="review-metrics">
          <div class="review-metric"><label>待复核总条数</label><b>{{ order.items?.length || 0 }}</b></div>
          <div class="review-metric pending"><label>待处理</label><b>{{ metrics.pending }}</b></div>
          <div class="review-metric confirmed"><label>已确认(A)</label><b>{{ metrics.A }}</b></div>
          <div class="review-metric revised"><label>已修正(B)</label><b>{{ metrics.B }}</b></div>
          <div class="review-metric refused"><label>已跳过(C)</label><b>{{ metrics.C }}</b></div>
        </div>

        <div class="review-workspace">
          <aside class="sample-nav">
            <div class="sample-nav-head">待核条目 <span>{{ order.items?.length || 0 }}</span></div>
            <div class="sample-nav-tip">逐条核对，已出结论条目仍可回看</div>
            <div
              v-for="(item, index) in order.items || []"
              :key="item.id"
              class="sample-nav-item"
              :class="{ active: activeReviewIndex === index }"
              @click="activeReviewIndex = index"
            >
              <span class="sample-dot" :class="item.conclusion ? 'pass' : ''" />
              <div class="sample-nav-text">
                <div class="item-id">{{ item.itemKey || `待核条目 ${String(index + 1).padStart(2, '0')}` }}</div>
                <small>{{ item.conclusion ? conclusionName(item.conclusion) : '待处理' }}</small>
              </div>
            </div>
            <div class="sample-nav-pager">共 {{ order.items?.length || 0 }} 条 · 第 {{ activeReviewIndex + 1 }} / {{ order.items?.length || 0 }}</div>
          </aside>

          <section v-if="activeReviewItem" class="inspection-card">
            <div class="inspection-head">
              <div>
                <div class="inspection-title">待核条目 {{ String(activeReviewIndex + 1).padStart(2, '0') }} · {{ activeReviewItem.itemKey }}</div>
                <div class="inspection-meta">{{ activeReviewItem.code }} · {{ activeReviewItem.reason }}</div>
              </div>
              <el-tag :type="activeReviewItem.conclusion ? conclusionTag(activeReviewItem.conclusion) : 'warning'" effect="light">
                {{ activeReviewItem.conclusion ? conclusionName(activeReviewItem.conclusion) : '待复核' }}
              </el-tag>
            </div>

            <div class="focus-banner"><b>本条目争议焦点：</b>{{ itemFocus(activeReviewItem) }}</div>

            <div class="review-compare">
              <div class="compare-pane source-pane">
                <div class="pane-title">原始素材 / 来源内容</div>
                <SourcePreview :item="activeReviewItem" :line="order.line" :run-id="order.runId" :image-run-id="order.imageRunId" />
              </div>
              <div class="compare-pane result-pane">
                <div class="pane-title">系统识别 / 结构化结果</div>
                <el-table :data="reviewFieldRows(activeReviewItem)" size="small" border class="result-table">
                  <el-table-column prop="field" label="字段" width="150" />
                  <el-table-column label="值" min-width="220">
                    <template #default="{ row: field }"><span class="mono small result-value">{{ fieldText(field.value) }}</span></template>
                  </el-table-column>
                  <el-table-column label="置信度" width="86" align="center">
                    <template #default="{ row: field }">
                      <el-tag v-if="field.confidence != null" size="small" :type="confTag(field.confidence)">{{ Number(field.confidence).toFixed(2) }}</el-tag>
                      <span v-else class="muted">—</span>
                    </template>
                  </el-table-column>
                </el-table>
                <template v-if="activeReviewItem.conclusion === 'B'">
                  <div class="pane-title diff-title">修正差异（改前 → 改后）</div>
                  <el-table :data="diffRows(activeReviewItem)" size="small" border>
                    <el-table-column prop="key" label="字段" width="120" />
                    <el-table-column prop="before" label="改前" min-width="120" />
                    <el-table-column prop="after" label="改后" min-width="120" />
                  </el-table>
                </template>
              </div>
            </div>

            <div class="inspection-decision">
              <div class="decision-hint">单条错误点「直接修正」即时生效并留痕；整单完成后提交闭环。</div>
              <div class="decision-actions">
                <el-button v-if="!locked" type="success" @click="conclude(activeReviewItem, 'A')">确认无误 A</el-button>
                <el-button v-if="!locked" type="warning" @click="openFix(activeReviewItem)">直接修正 B</el-button>
                <el-button v-if="!locked" type="danger" @click="conclude(activeReviewItem, 'C')">跳过 C</el-button>
                <el-button v-if="!locked && activeReviewItem.conclusion" link @click="unconclude(activeReviewItem)">撤销当前结论</el-button>
                <span v-if="locked" class="muted">该复核单已闭环，只读查看</span>
              </div>
            </div>
          </section>
          <div v-else class="empty-review-panel">当前复核单没有可展示条目</div>
        </div>

        <div class="workbench-footer">
          <span class="workbench-note">已处理 {{ concludedCount }} / {{ order.items?.length || 0 }} 条</span>
          <div class="workbench-nav">
            <el-button :disabled="activeReviewIndex <= 0" @click="activeReviewIndex--">上一条</el-button>
            <el-button :disabled="activeReviewIndex >= (order.items?.length || 1) - 1" @click="activeReviewIndex++">下一条</el-button>
            <el-button @click="orderVisible = false">暂存并关闭</el-button>
            <el-button type="success" :disabled="!allConcluded || locked" @click="doClose">提交复核结论</el-button>
          </div>
        </div>
      </template>
    </el-drawer>

    <!-- 修正弹窗 -->
    <el-dialog v-model="fixVisible" title="修正条目（仅提交改动字段）" class="wbdz-dialog">
      <el-table :data="fixFields" size="small" max-height="52vh">
        <el-table-column prop="key" label="字段" width="160" />
        <el-table-column label="修正后取值" min-width="380">
          <template #default="{ row }">
            <el-input v-if="row.complex" v-model="row.value" type="textarea" :rows="2" />
            <el-input v-else v-model="row.value" />
          </template>
        </el-table-column>
      </el-table>
      <div class="hint" style="margin-top: 8px">字段类型：数字/布尔按原类型回写，对象/数组按 JSON 解析。</div>
      <template #footer>
        <el-button @click="fixVisible = false">取消</el-button>
        <el-button type="warning" @click="submitFix">保存修正</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import PageHeader from '@/components/PageHeader.vue'
import BizIdText from '@/components/BizIdText.vue'
import SourcePreview from '@/components/SourcePreview.vue'
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  LINE_NAMES, REVIEW_STATUS,
  reviewPage, reviewDetail, reviewConclude, reviewUnconclude, reviewClose, taskReject,
} from '@/api'

const route = useRoute()
const router = useRouter()

const query = reactive({ line: '', status: '', pageNum: 1, pageSize: 10 })
const rows = ref<any[]>([])
const total = ref(0)
const loading = ref(false)

const orderVisible = ref(false)
const order = ref<any>(null)
const activeReviewIndex = ref(0)

const fixVisible = ref(false)
const fixItem = ref<any>(null)
const fixFields = ref<{ key: string; original: any; value: string; complex: boolean }[]>([])

const locked = computed(() => order.value?.status === 'done' || order.value?.status === 'void')
const concludedCount = computed(() => (order.value?.items || []).filter((i: any) => i.conclusion).length)
const metrics = computed(() => {
  const items = order.value?.items || []
  return {
    pending: items.filter((i: any) => !i.conclusion).length,
    A: items.filter((i: any) => i.conclusion === 'A').length,
    B: items.filter((i: any) => i.conclusion === 'B').length,
    C: items.filter((i: any) => i.conclusion === 'C').length,
  }
})
const allConcluded = computed(() => {
  const items = order.value?.items || []
  return items.length > 0 && items.every((i: any) => !!i.conclusion)
})
const activeReviewItem = computed(() => order.value?.items?.[activeReviewIndex.value] || null)

function resetQuery() {
  query.line = ''
  query.status = ''
  load(1)
}
function timeFmt(_r: any, _c: any, v: string) {
  if (!v || v === 'null') return '—'
  return v.replace('T', ' ').slice(0, 19)
}

function fieldRows(payload: any) {
  const rows: { field: string; value: any; confidence?: number | null }[] = []
  const seen = new Set<string>()
  const add = (field: string, value: any, confidence?: number | null) => {
    if (seen.has(field)) return
    seen.add(field)
    rows.push({ field, value, confidence })
  }
  const fields = payload?.fields
  if (fields && typeof fields === 'object') {
    for (const [group, groupValue] of Object.entries(fields)) {
      if (!groupValue || typeof groupValue !== 'object') continue
      for (const [field, raw] of Object.entries(groupValue as Record<string, any>)) {
        if (raw && typeof raw === 'object' && ('value' in raw || 'confidence' in raw)) {
          add(`${group}.${field}`, raw.value, raw.confidence)
        }
      }
    }
  }
  for (const [key, value] of Object.entries(payload || {})) {
    if (['fields', 'confidence', 'beforeValue', 'afterValue', 'slices', 'symbols', 'elements'].includes(key)) continue
    if (value && typeof value === 'object') {
      if ('value' in (value as any) || 'confidence' in (value as any)) {
        add(key, (value as any).value, (value as any).confidence)
      }
      continue
    }
    add(key, value)
  }
  return rows.slice(0, 40)
}

function itemFocus(item: any) {
  return item?.reason || item?.payload?.reviewReason || item?.payload?.lowConfidenceReasons || '请对照左侧原始素材核对右侧系统结果。'
}

function reviewFieldRows(item: any) {
  const payload = item?.payload || {}
  if (order.value?.line === 'formula') {
    return [
      { field: 'LaTeX', value: payload.latex, confidence: payload.recognitionConfidence },
      { field: '符号·含义·单位', value: payload.symbols, confidence: payload.semanticConfidence },
      { field: '章节/编号/上下文', value: payload.context, confidence: payload.semanticConfidence },
      { field: '识别置信度', value: payload.recognitionConfidence },
      { field: '语义标注置信度', value: payload.semanticConfidence },
    ].filter((row) => row.value != null && row.value !== '')
  }
  return fieldRows(payload)
}

function fieldText(value: any) {
  if (value === null || value === undefined || value === '') return '—'
  if (Array.isArray(value)) return value.map((v) => typeof v === 'object' ? JSON.stringify(v) : String(v)).join('；')
  return typeof value === 'object' ? JSON.stringify(value) : String(value)
}

function confTag(value: number) {
  if (value >= 0.8) return 'success'
  if (value >= 0.6) return 'warning'
  return 'danger'
}
function pretty(v: any) {
  return JSON.stringify(v || {}, null, 2)
}

const KEY_FIELDS = ['title', 'name', 'content', 'text', 'formula', 'semantic', 'summary', 'caption', 'docType', 'genre', 'value']
function keyFields(payload: any) {
  if (!payload) return '—'
  return Object.entries(payload)
    .filter(([k]) => KEY_FIELDS.some((f) => k.toLowerCase().includes(f.toLowerCase())))
    .slice(0, 3)
    .map(([k, v]) => `${k}=${typeof v === 'object' ? JSON.stringify(v) : v}`)
    .join('；') || Object.keys(payload).slice(0, 4).join(', ')
}

function conclusionName(c: string) {
  return ({ A: '已确认', B: '已修正', C: '已剔除' } as Record<string, string>)[c] || c
}

function conclusionTag(c: string) {
  return ({ A: 'success', B: 'warning', C: 'danger' } as Record<string, string>)[c] || 'info'
}

function diffRows(row: any) {
  const before = row.beforeValue || {}
  const after = row.afterValue || {}
  return Object.keys(after).map((k) => ({ key: k, before: fmtVal(before[k]), after: fmtVal(after[k]) }))
}

function fmtVal(v: any) {
  return typeof v === 'object' ? JSON.stringify(v) : String(v ?? '')
}

async function load(page?: number) {
  if (page) query.pageNum = page
  loading.value = true
  try {
    const res = await reviewPage({
      line: query.line || undefined, status: query.status || undefined,
      pageNum: query.pageNum, pageSize: query.pageSize,
    })
    rows.value = res.records
    total.value = Number(res.total)
  } finally {
    loading.value = false
  }
}

async function rerunSourceTask() {
  if (!order.value?.taskBizNo && !order.value?.taskId) return
  await ElMessageBox.confirm(
    '确认重跑来源任务？重跑后当前未闭环复核单将自动作废，已有结论仍保留留痕。',
    '重跑来源任务',
    { type: 'warning' },
  )
  await taskReject(String(order.value.taskBizNo || order.value.taskId), 1)
  ElMessage.success('已触发来源任务重跑')
  orderVisible.value = false
  await load()
}
async function openOrder(id: string) {
  order.value = await reviewDetail(id)
  const pending = (order.value?.items || []).findIndex((item: any) => !item.conclusion)
  activeReviewIndex.value = pending >= 0 ? pending : 0
  orderVisible.value = true
}

async function refreshOrder() {
  if (!order.value) return
  const current = activeReviewIndex.value
  order.value = await reviewDetail(order.value.bizNo)
  activeReviewIndex.value = Math.min(current, Math.max(0, (order.value?.items || []).length - 1))
}

async function conclude(row: any, conclusion: 'A' | 'C') {
  const current = activeReviewIndex.value
  await reviewConclude(row.id, conclusion)
  ElMessage.success(conclusion === 'A' ? '已确认' : '已剔除')
  await refreshOrder()
  const items = order.value?.items || []
  const next = items.findIndex((item: any, index: number) => index > current && !item.conclusion)
  if (next >= 0) activeReviewIndex.value = next
}

async function unconclude(row: any) {
  await reviewUnconclude(row.id)
  ElMessage.success('已撤销结论')
  await refreshOrder()
}

function openFix(row: any) {
  fixItem.value = row
  const payload = row.payload || {}
  fixFields.value = Object.entries(payload).map(([k, v]) => ({
    key: k,
    original: v,
    value: typeof v === 'object' ? JSON.stringify(v) : String(v ?? ''),
    complex: typeof v === 'object',
  }))
  fixVisible.value = true
}

async function submitFix() {
  const revised: Record<string, any> = {}
  for (const f of fixFields.value) {
    let v: any
    if (f.complex) {
      try {
        v = JSON.parse(f.value)
      } catch {
        return ElMessage.error(`字段「${f.key}」不是合法 JSON`)
      }
    } else if (typeof f.original === 'number') {
      v = Number(f.value)
    } else if (typeof f.original === 'boolean') {
      v = f.value === 'true'
    } else {
      v = f.value
    }
    if (JSON.stringify(v) !== JSON.stringify(f.original)) revised[f.key] = v
  }
  if (!Object.keys(revised).length) return ElMessage.warning('未检测到改动')
  const current = activeReviewIndex.value
  await reviewConclude(fixItem.value.id, 'B', revised)
  ElMessage.success('已保存修正（改前/改后已留痕）')
  fixVisible.value = false
  await refreshOrder()
  const items = order.value?.items || []
  const next = items.findIndex((item: any, index: number) => index > current && !item.conclusion)
  if (next >= 0) activeReviewIndex.value = next
}

async function doClose() {
  await ElMessageBox.confirm('整单闭环后将回写数据集条目并联动任务状态，确认闭环？', '闭环确认', { type: 'warning' })
  await reviewClose(order.value.bizNo)
  ElMessage.success('复核单已闭环')
  await refreshOrder()
  load()
}

function onDrawerClosed() {
  if (route.query.orderBizNo || route.query.orderId) {
    router.replace({ path: '/review' })
  }
  load()
}

onMounted(async () => {
  await load()
  const orderBizNo = String(route.query.orderBizNo || route.query.orderId || '')
  if (orderBizNo) openOrder(orderBizNo)
})
</script>

<style scoped>
.pager { margin-top: 14px; justify-content: flex-end; }
.mono { font-family: var(--wbdz-font-mono); }
.small { font-size: var(--wbdz-font-caption); }
.muted { color: var(--wbdz-secondary); }
.hint { font-size: var(--wbdz-font-caption); color: var(--wbdz-secondary); }

.review-workbench-drawer :deep(.el-drawer__header) { margin-bottom: 0; padding: 0; border-bottom: 1px solid var(--wbdz-border); }
.review-workbench-drawer :deep(.el-drawer__body) { padding: 0; background: #f4f6fb; }
.workbench-head { width: 100%; padding: 18px 22px 15px; background: #fff; }
.workbench-title { color: var(--wbdz-title); font-size: 18px; font-weight: 650; }
.workbench-subtitle { margin-top: 3px; color: var(--wbdz-secondary); font-size: var(--wbdz-font-caption); }
.review-context-card { display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 13px 16px; margin: 16px 20px 0; border: 1px solid var(--wbdz-border); border-radius: 5px; background: #fff; }
.review-context-main { min-width: 0; }
.context-line { display: flex; flex-wrap: wrap; gap: 8px 22px; color: var(--wbdz-text); font-size: 13px; }
.context-line b { color: var(--wbdz-title); font-weight: 600; }
.context-reason { margin-top: 5px; color: var(--wbdz-secondary); font-size: var(--wbdz-font-caption); }
.review-metrics { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 10px; margin: 14px 20px 0; }
.review-metric { padding: 11px 13px; border: 1px solid var(--wbdz-border); border-radius: 5px; background: #fff; }
.review-metric label { display: block; color: var(--wbdz-secondary); font-size: var(--wbdz-font-caption); }
.review-metric b { display: block; margin-top: 2px; color: var(--wbdz-title); font-size: 20px; font-weight: 650; }
.review-metric.pending b { color: #d92d20; }
.review-metric.confirmed b { color: #128a57; }
.review-metric.revised b { color: #b54708; }
.review-metric.refused b { color: #b42318; }
.review-workspace { display: grid; grid-template-columns: 205px minmax(0, 1fr); gap: 14px; align-items: start; padding: 14px 20px 18px; }
.sample-nav, .inspection-card { border: 1px solid var(--wbdz-border); border-radius: 5px; background: #fff; }
.sample-nav { overflow: hidden; }
.sample-nav-head { display: flex; justify-content: space-between; padding: 12px 13px; border-bottom: 1px solid var(--wbdz-border); color: var(--wbdz-title); font-size: 13px; font-weight: 650; }
.sample-nav-head span { color: var(--wbdz-secondary); font-weight: 500; }
.sample-nav-tip { padding: 8px 13px; border-bottom: 1px solid var(--wbdz-row-line); color: var(--wbdz-secondary); font-size: 11px; }
.sample-nav-item { display: flex; align-items: flex-start; gap: 8px; padding: 10px 13px; border-bottom: 1px solid var(--wbdz-row-line); cursor: pointer; }
.sample-nav-item:hover { background: var(--wbdz-primary-light); }
.sample-nav-item.active { padding-left: 10px; border-left: 3px solid var(--wbdz-primary); background: var(--wbdz-primary-light); }
.sample-nav-text { min-width: 0; }
.sample-nav-text .item-id { overflow: hidden; color: #4e6680; font-family: var(--wbdz-font-mono); font-size: 11px; text-overflow: ellipsis; white-space: nowrap; }
.sample-nav-text small { display: block; margin-top: 2px; color: var(--wbdz-secondary); font-size: 11px; }
.sample-dot { flex: none; width: 8px; height: 8px; margin-top: 5px; border-radius: 50%; background: #c9cdd4; }
.sample-dot.pass { background: var(--wbdz-success); }
.sample-nav-pager { padding: 11px 13px; color: var(--wbdz-secondary); font-size: 11px; }
.inspection-card { min-width: 0; padding: 17px; }
.inspection-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; padding-bottom: 12px; border-bottom: 1px solid var(--wbdz-border); }
.inspection-title { color: var(--wbdz-title); font-size: 16px; font-weight: 650; }
.inspection-meta { margin-top: 3px; color: var(--wbdz-secondary); font-size: var(--wbdz-font-caption); }
.focus-banner { margin-top: 12px; padding: 10px 12px; border: 1px solid #f7d394; border-radius: 4px; background: #fff8e8; color: #8b5b0b; font-size: 13px; line-height: 1.55; }
.review-compare { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 14px; margin-top: 14px; align-items: start; }
.compare-pane { min-width: 0; }
.pane-title { margin-bottom: 8px; color: var(--wbdz-title); font-size: 13px; font-weight: 650; }
.result-table { margin-top: 2px; }
.result-value { display: block; max-height: 180px; overflow: auto; white-space: pre-wrap; word-break: break-word; line-height: 1.6; }
.diff-title { margin-top: 14px; }
.inspection-decision { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-top: 16px; padding-top: 14px; border-top: 1px solid var(--wbdz-border); }
.decision-hint { color: var(--wbdz-secondary); font-size: var(--wbdz-font-caption); line-height: 1.55; }
.decision-actions { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; justify-content: flex-end; }
.empty-review-panel { padding: 36px 12px; border: 1px dashed var(--wbdz-border-strong); background: #fff; color: var(--wbdz-secondary); text-align: center; }
.workbench-footer { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 12px 20px; border-top: 1px solid var(--wbdz-border); background: #fff; }
.workbench-note { color: var(--wbdz-secondary); font-size: var(--wbdz-font-caption); }
.workbench-nav { display: flex; gap: 8px; align-items: center; }
@media (max-width: 1200px) {
  .review-workspace { grid-template-columns: 170px minmax(0, 1fr); }
  .review-compare { grid-template-columns: 1fr; }
  .inspection-decision, .workbench-footer { align-items: flex-start; flex-direction: column; }
  .workbench-nav { width: 100%; justify-content: flex-end; }
}
</style>
