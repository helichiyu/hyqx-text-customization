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
            <el-button link type="primary" size="small" @click="openOrder(row.id)">
              {{ row.status === 'done' || row.status === 'void' ? '查看' : '复核' }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination class="pager" layout="total, prev, pager, next" :total="total"
        v-model:current-page="query.pageNum" :page-size="query.pageSize" @current-change="load()" />
    </el-card>

    <!-- 复核工作台 -->
    <el-drawer v-model="orderVisible" :title="order ? `条件复核 · ${order.bizNo}` : '条件复核'" class="wbdz-drawer wbdz-drawer--wide" @closed="onDrawerClosed">
      <template v-if="order">
        <el-descriptions :column="3" border size="small">
          <el-descriptions-item label="产线">{{ order.lineName }}</el-descriptions-item>
          <el-descriptions-item label="触发环节">{{ order.stageName }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="REVIEW_STATUS[order.status]?.tag">{{ order.statusName }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="触发条件" :span="2">
            <span class="mono small">{{ order.triggerCode }}</span> · {{ order.triggerDesc }}
          </el-descriptions-item>
          <el-descriptions-item label="进度">{{ concludedCount }} / {{ order.items?.length || 0 }}</el-descriptions-item>
        </el-descriptions>

        <div class="order-bar">
          <span class="hint">逐条出结论：A 确认 · B 修正（记录改前/改后） · C 剔除；结论保存后不立即闭环。</span>
          <div style="flex: 1" />
          <el-tag size="small" type="info">待处理 {{ metrics.pending }}</el-tag>
          <el-tag size="small" type="success">已确认A {{ metrics.A }}</el-tag>
          <el-tag size="small" type="warning">已修正B {{ metrics.B }}</el-tag>
          <el-tag size="small" type="danger">已剔除C {{ metrics.C }}</el-tag>
          <el-button v-if="order.status !== 'done' && order.status !== 'void'" type="warning" plain @click="rerunSourceTask">重跑来源任务</el-button>
          <el-button type="success" :disabled="!allConcluded || order.status === 'done' || order.status === 'void'" @click="doClose">
            整单闭环
          </el-button>
        </div>

        <el-table :data="order.items || []" size="small" border>
          <el-table-column type="expand">
            <template #default="{ row }">
              <div class="review-grid">
                <div class="review-col">
                  <div class="payload-title">复核条目</div>
                  <el-descriptions :column="1" border size="small">
                    <el-descriptions-item label="行标识">{{ row.itemKey || '—' }}</el-descriptions-item>
                    <el-descriptions-item label="触发码">{{ row.code || '—' }}</el-descriptions-item>
                    <el-descriptions-item label="触发原因">{{ row.reason || '—' }}</el-descriptions-item>
                    <el-descriptions-item label="当前结论">{{ row.conclusion ? conclusionName(row.conclusion) : '待复核' }}</el-descriptions-item>
                    <el-descriptions-item label="复核人">{{ row.operator || '—' }}</el-descriptions-item>
                  </el-descriptions>
                  <el-collapse class="raw-collapse">
                    <el-collapse-item title="原始 JSON" name="raw">
                      <pre class="json">{{ pretty(row.payload) }}</pre>
                    </el-collapse-item>
                  </el-collapse>
                </div>

                <div class="review-col">
                  <SourcePreview :item="row" :line="order.line" :run-id="order.runId" :image-run-id="order.imageRunId" />
                </div>

                <div class="review-col">
                  <div class="payload-title">字段与置信度</div>
                  <el-table :data="fieldRows(row.payload)" size="small" border max-height="320">
                    <el-table-column prop="field" label="字段" min-width="150" show-overflow-tooltip />
                    <el-table-column label="值" min-width="180">
                      <template #default="{ row: field }">
                        <span class="mono small">{{ fieldText(field.value) }}</span>
                      </template>
                    </el-table-column>
                    <el-table-column label="置信度" width="80" align="center">
                      <template #default="{ row: field }">
                        <el-tag v-if="field.confidence != null" size="small" :type="confTag(field.confidence)">
                          {{ field.confidence }}
                        </el-tag>
                        <span v-else class="muted">—</span>
                      </template>
                    </el-table-column>
                  </el-table>
                  <template v-if="row.conclusion === 'B'">
                    <div class="payload-title diff-title">修正差异（改前 → 改后）</div>
                    <el-table :data="diffRows(row)" size="small" border>
                      <el-table-column prop="key" label="字段" width="120" />
                      <el-table-column prop="before" label="改前" min-width="120" />
                      <el-table-column prop="after" label="改后" min-width="120" />
                    </el-table>
                  </template>
                </div>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="itemKey" label="行标识" width="140" show-overflow-tooltip />
          <el-table-column label="触发原因" min-width="220">
            <template #default="{ row }">
              <span class="mono small">{{ row.code }}</span>
              <div class="muted small">{{ row.reason }}</div>
            </template>
          </el-table-column>
          <el-table-column label="关键字段" min-width="260">
            <template #default="{ row }">
              <span class="mono small">{{ keyFields(row.payload) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="结论" width="90" align="center">
            <template #default="{ row }">
              <el-tag v-if="row.conclusion" :type="conclusionTag(row.conclusion)" size="small">
                {{ conclusionName(row.conclusion) }}
              </el-tag>
              <span v-else class="muted">待复核</span>
            </template>
          </el-table-column>
          <el-table-column prop="operator" label="复核人" width="90" />
          <el-table-column label="操作" width="220" fixed="right">
            <template #default="{ row }">
              <template v-if="!locked">
                <el-button size="small" :type="row.conclusion === 'A' ? 'primary' : 'default'" @click="conclude(row, 'A')">确认</el-button>
                <el-button size="small" :type="row.conclusion === 'B' ? 'warning' : 'default'" @click="openFix(row)">修正</el-button>
                <el-button size="small" :type="row.conclusion === 'C' ? 'danger' : 'default'" @click="conclude(row, 'C')">剔除</el-button>
                <el-button v-if="row.conclusion" link size="small" @click="unconclude(row)">撤销</el-button>
              </template>
              <span v-else class="muted">已闭环</span>
            </template>
          </el-table-column>
        </el-table>
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
  if (!order.value?.taskId) return
  await ElMessageBox.confirm(
    '确认重跑来源任务？重跑后当前未闭环复核单将自动作废，已有结论仍保留留痕。',
    '重跑来源任务',
    { type: 'warning' },
  )
  await taskReject(String(order.value.taskId), 1)
  ElMessage.success('已触发来源任务重跑')
  orderVisible.value = false
  await load()
}
async function openOrder(id: string) {
  order.value = await reviewDetail(id)
  orderVisible.value = true
}

async function refreshOrder() {
  if (order.value) order.value = await reviewDetail(order.value.id)
}

async function conclude(row: any, conclusion: 'A' | 'C') {
  await reviewConclude(row.id, conclusion)
  ElMessage.success(conclusion === 'A' ? '已确认' : '已剔除')
  await refreshOrder()
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
  await reviewConclude(fixItem.value.id, 'B', revised)
  ElMessage.success('已保存修正（改前/改后已留痕）')
  fixVisible.value = false
  await refreshOrder()
}

async function doClose() {
  await ElMessageBox.confirm('整单闭环后将回写数据集条目并联动任务状态，确认闭环？', '闭环确认', { type: 'warning' })
  await reviewClose(order.value.id)
  ElMessage.success('复核单已闭环')
  await refreshOrder()
  load()
}

function onDrawerClosed() {
  if (route.query.orderId) {
    router.replace({ path: '/review' })
  }
  load()
}

onMounted(async () => {
  await load()
  const orderId = String(route.query.orderId || '')
  if (orderId) openOrder(orderId)
})
</script>

<style scoped>

.pager { margin-top: 14px; justify-content: flex-end; }
.mono { font-family: var(--wbdz-font-mono); }
.small { font-size: var(--wbdz-font-caption); }
.muted { color: var(--wbdz-secondary); }
.hint { font-size: var(--wbdz-font-caption); color: var(--wbdz-secondary); }
.order-bar { display: flex; align-items: center; gap: 10px; margin: 12px 0; }
.review-grid { display: grid; grid-template-columns: minmax(200px, 0.72fr) minmax(300px, 1.2fr) minmax(300px, 1fr); gap: 16px; padding: 12px 16px; }
.review-col { min-width: 0; }
.payload-title { font-weight: 600; margin-bottom: 8px; color: var(--wbdz-title); font-size: var(--wbdz-font-body); }
.diff-title { margin-top: 14px; }
.raw-collapse { margin-top: 10px; }
.json { background: var(--wbdz-bg-page); padding: 10px; max-height: 260px; overflow: auto; font-size: var(--wbdz-font-caption); margin: 0; white-space: pre-wrap; word-break: break-all; }
@media (max-width: 1200px) { .review-grid { grid-template-columns: 1fr; } }
</style>
