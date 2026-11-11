<template>
  <div class="page-stack">
    <PageHeader
      title="素材管理"
      description="跨产线管理素材批次，完成上传、准入校验、移交和任务关联追溯。"
    />

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
            <label class="filter-label">批次名称</label>
            <el-input
              v-model="query.name"
              placeholder="请输入批次名称"
              clearable
              style="width: 200px"
              @keyup.enter="load(1)"
            />
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
                v-for="(s, k) in MAT_STATUS"
                :key="k"
                :label="s.name"
                :value="k"
              />
            </el-select>
          </div>
        </div>
        <div class="search-actions">
          <el-button @click="resetQuery">
            重置
          </el-button>
          <el-button
            type="primary"
            @click="uploadVisible = true"
          >
            + 上传素材
          </el-button>
        </div>
      </div>

      <el-table
        v-loading="loading"
        :data="rows"
      >
        <el-table-column
          label="批次编号"
          width="210"
        >
          <template #default="{ row }">
            <BizIdText :value="row.bizNo" />
          </template>
        </el-table-column>
        <el-table-column
          prop="name"
          label="批次名称"
          min-width="160"
          show-overflow-tooltip
        />
        <el-table-column
          prop="lineName"
          label="产线"
          width="110"
        />
        <el-table-column
          label="状态"
          width="100"
        >
          <template #default="{ row }">
            <el-tag
              :type="statusOf(row).tag"
              effect="light"
            >
              {{ statusOf(row).name }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column
          label="有效/原始条数"
          width="120"
          align="center"
        >
          <template #default="{ row }">
            {{ row.fileCount }} / {{ row.totalCount }}
          </template>
        </el-table-column>
        <el-table-column
          prop="createBy"
          label="上传人"
          width="100"
        />
        <el-table-column
          prop="createTime"
          label="上传时间"
          width="170"
          :formatter="timeFmt"
        />
        <el-table-column
          label="操作"
          width="300"
          fixed="right"
        >
          <template #default="{ row }">
            <el-button
              v-if="row.status === 'uncheked'"
              link
              type="primary"
              size="small"
              @click="openCheck(row)"
            >
              准入校验
            </el-button>
            <el-button
              v-if="row.status === 'checked'"
              link
              type="primary"
              size="small"
              @click="openRelease(row)"
            >
              移交
            </el-button>
            <el-button
              link
              type="primary"
              size="small"
              @click="openDetail(row)"
            >
              详情
            </el-button>
            <el-button
              v-if="row.status !== 'upload_failed'"
              link
              type="primary"
              size="small"
              @click="openEdit(row)"
            >
              编辑
            </el-button>
            <el-button
              v-if="!row.linked && row.status !== 'released'"
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

    <!-- 准入校验确认 -->
    <el-dialog
      v-model="checkVisible"
      class="check-dialog"
      width="980px"
      :title="`准入校验 · ${checkBatch?.name || ''}`"
      @closed="resetCheck"
    >
      <div class="check-intro">
        <div>
          <b>{{ checkBatch?.bizNo }}</b>
          <span class="muted"> · {{ checkBatch?.lineName }} · {{ checkDetail?.fileCount ?? checkBatch?.fileCount ?? 0 }} 条有效素材</span>
        </div>
        <el-tag
          type="warning"
          effect="light"
        >
          确认前不会改变批次状态
        </el-tag>
      </div>
      <el-table
        v-loading="checkLoading"
        :data="checkRows"
        size="small"
        border
        class="check-table"
        :empty-text="checkLoading ? '正在读取校验结果…' : '暂无检查项'"
      >
        <el-table-column
          prop="item"
          label="检查项"
          width="150"
        />
        <el-table-column
          prop="level"
          label="级别"
          width="190"
        />
        <el-table-column
          prop="requirement"
          label="要求"
          min-width="190"
        />
        <el-table-column
          prop="actual"
          label="实际"
          min-width="190"
        />
        <el-table-column
          label="结果"
          width="80"
          align="center"
        >
          <template #default="{ row }">
            <el-tag
              :type="row.ok ? 'success' : 'danger'"
              size="small"
            >
              {{ row.ok ? '通过' : '不通过' }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
      <div
        class="check-note"
        :class="checkPassed ? 'check-note--pass' : 'check-note--fail'"
      >
        <template v-if="checkLoading">
          正在加载批次文件级校验信息。
        </template>
        <template v-else-if="checkPassed">
          必查项全部通过，可确认并标记为「已校验」。
        </template>
        <template v-else>
          存在必查项未通过，请先处理失败文件后再执行准入校验。
        </template>
      </div>
      <template #footer>
        <el-button @click="checkVisible = false">
          关闭
        </el-button>
        <el-button
          type="primary"
          :disabled="!checkPassed || checkLoading"
          :loading="checking"
          @click="confirmCheck"
        >
          通过并标记已校验
        </el-button>
      </template>
    </el-dialog>

    <!-- 移交确认 -->
    <el-dialog
      v-model="releaseVisible"
      width="560px"
      :title="`移交素材批次 · ${releaseBatch?.name || ''}`"
    >
      <div class="release-batch-line">
        <b>批次编号：</b><BizIdText
          v-if="releaseBatch"
          :value="releaseBatch.bizNo"
        />
      </div>
      <div class="release-note">
        移交后该批次进入「已移交」，可被本产线任务引用；移交后不可编辑、不可删除，也不能再修改准入校验结论。
      </div>
      <template #footer>
        <el-button @click="releaseVisible = false">
          取消
        </el-button>
        <el-button
          type="primary"
          :loading="releasing"
          @click="confirmRelease"
        >
          确认移交
        </el-button>
      </template>
    </el-dialog>

    <!-- 上传弹窗 -->
    <el-dialog
      v-model="uploadVisible"
      title="上传素材批次"
      class="tcs-dialog"
    >
      <el-form label-width="90px">
        <el-form-item
          label="产线"
          required
        >
          <el-select
            v-model="uploadForm.line"
            style="width: 100%"
          >
            <el-option
              v-for="(n, l) in LINE_NAMES"
              :key="l"
              :label="n"
              :value="l"
            />
          </el-select>
          <div class="hint">
            允许格式：{{ LINE_WHITELIST_TEXT[uploadForm.line] || '—' }}（ZIP 内逐文件校验，白名单外自动剔除计数）
          </div>
        </el-form-item>
        <el-form-item
          label="批次名称"
          required
        >
          <el-input
            v-model="uploadForm.name"
            placeholder="同产线唯一"
          />
        </el-form-item>
        <el-form-item
          label="素材文件"
          required
        >
          <input
            ref="fileInput"
            type="file"
            multiple
            :accept="acceptOf(uploadForm.line)"
            @change="onFiles"
          >
          <div class="hint">
            已选 {{ uploadForm.files.length }} 个文件
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="uploadVisible = false">
          取消
        </el-button>
        <el-button
          type="primary"
          :loading="uploading"
          @click="doUpload"
        >
          上传
        </el-button>
      </template>
    </el-dialog>

    <!-- 编辑弹窗 -->
    <el-dialog
      v-model="editVisible"
      title="编辑批次基本信息"
      class="tcs-dialog"
    >
      <el-form label-width="90px">
        <el-form-item label="批次名称">
          <el-input v-model="editForm.name" />
        </el-form-item>
        <el-form-item label="产线">
          <el-select
            v-model="editForm.line"
            style="width: 100%"
            :disabled="editing?.linked"
          >
            <el-option
              v-for="(n, l) in LINE_NAMES"
              :key="l"
              :label="n"
              :value="l"
            />
          </el-select>
          <div
            v-if="editing?.linked"
            class="hint"
          >
            已被任务引用，产线不可修改
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">
          取消
        </el-button>
        <el-button
          type="primary"
          @click="doEdit"
        >
          保存
        </el-button>
      </template>
    </el-dialog>

    <!-- 详情抽屉 -->
    <el-drawer
      v-model="detailVisible"
      title="批次详情"
      class="tcs-drawer"
    >
      <template v-if="detail">
        <el-descriptions
          :column="2"
          border
          size="small"
        >
          <el-descriptions-item label="批次编号">
            <BizIdText :value="detail.bizNo" />
          </el-descriptions-item>
          <el-descriptions-item label="名称">
            {{ detail.name }}
          </el-descriptions-item>
          <el-descriptions-item label="产线">
            {{ detail.lineName }}
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="MAT_STATUS[detail.status]?.tag">
              {{ MAT_STATUS[detail.status]?.name }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="有效条数">
            {{ detail.fileCount }}
          </el-descriptions-item>
          <el-descriptions-item label="原始条数">
            {{ detail.totalCount }}
          </el-descriptions-item>
          <el-descriptions-item
            label="关联任务"
            :span="2"
          >
            <span>{{ detail.linkedTaskIds?.length ? `已关联（${detail.linkedTaskIds.length} 个任务）` : '未关联' }}</span>
            <el-button
              v-if="detail.linkedTaskIds?.length"
              link
              type="primary"
              size="small"
              style="margin-left: 10px"
              @click="openLinkedTasks"
            >
              查看关联任务
            </el-button>
          </el-descriptions-item>
        </el-descriptions>

        <h4>剔除汇总</h4>
        <el-empty
          v-if="!detail.rejectSummary?.length"
          description="无剔除"
          :image-size="48"
        />
        <el-tag
          v-for="r in detail.rejectSummary"
          :key="r.reason"
          type="danger"
          effect="plain"
          class="reject-tag"
        >
          {{ r.reason }} × {{ r.count }}
        </el-tag>

        <h4>文件清单</h4>
        <el-table
          :data="detail.files"
          size="small"
          max-height="300"
        >
          <el-table-column
            prop="name"
            label="文件名"
            min-width="180"
            show-overflow-tooltip
          />
          <el-table-column
            prop="ext"
            label="格式"
            width="70"
          />
          <el-table-column
            label="页数"
            width="70"
          >
            <template #default="{ row }">
              {{ row.pageCount ?? '—' }}
            </template>
          </el-table-column>
          <el-table-column
            label="状态"
            width="90"
          >
            <template #default="{ row }">
              <el-tag
                :type="row.status === 'passed' ? 'success' : 'danger'"
                size="small"
              >
                {{ row.status === 'passed' ? '通过' : '剔除' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column
            prop="rejectReason"
            label="剔除原因"
            min-width="160"
            show-overflow-tooltip
          />
        </el-table>

        <h4>变更记录</h4>
        <el-empty
          v-if="!detail.changes?.length"
          description="无变更"
          :image-size="48"
        />
        <el-timeline
          v-else
          style="padding-left: 8px"
        >
          <el-timeline-item
            v-for="(c, i) in detail.changes"
            :key="i"
            :timestamp="c.time"
          >
            {{ c.item === 'name' ? '名称' : '产线' }}：{{ c.oldValue }} → {{ c.newValue }}（{{ c.operator }}）
          </el-timeline-item>
        </el-timeline>
      </template>
    </el-drawer>

    <!-- 关联任务 -->
    <el-dialog
      v-model="linkedTasksVisible"
      title="关联任务"
      width="760px"
    >
      <el-table
        v-loading="linkedTasksLoading"
        :data="linkedTasks"
        size="small"
      >
        <el-table-column
          label="任务编号"
          width="210"
        >
          <template #default="{ row }">
            <BizIdText :value="row.bizNo" />
          </template>
        </el-table-column>
        <el-table-column
          prop="name"
          label="任务名称"
          min-width="220"
          show-overflow-tooltip
        />
        <el-table-column
          label="状态"
          width="100"
        >
          <template #default="{ row }">
            <el-tag
              :type="TASK_STATUS[row.status]?.tag"
              size="small"
            >
              {{ row.statusName }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column
          prop="paramVersion"
          label="参数版本"
          width="90"
        />
        <el-table-column
          label="操作"
          width="80"
          fixed="right"
        >
          <template #default="{ row }">
            <el-button
              link
              type="primary"
              size="small"
              @click="openLinkedTask(row)"
            >
              查看
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      <template #footer>
        <el-button @click="linkedTasksVisible = false">
          关闭
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import PageHeader from '../components/PageHeader.vue'
import BizIdText from '../components/BizIdText.vue'
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  LINE_NAMES, LINE_WHITELIST_TEXT, MAT_STATUS, TASK_STATUS,
  materialPage, materialDetail, materialUpload, materialCheck, materialRelease, taskPage,
  materialEdit, materialDelete, type MatBatchView,
} from '../api'

const router = useRouter()
const query = reactive({ line: '', name: '', status: '', pageNum: 1, pageSize: 10 })
const rows = ref<MatBatchView[]>([])
const total = ref(0)
const loading = ref(false)

const uploadVisible = ref(false)
const uploading = ref(false)
const fileInput = ref<HTMLInputElement>()
const uploadForm = reactive({ line: 'metadata', name: '', files: [] as File[] })

const editVisible = ref(false)
const editing = ref<MatBatchView | null>(null)
const editForm = reactive({ name: '', line: '' })

const detailVisible = ref(false)
const detail = ref<any>(null)

const linkedTasksVisible = ref(false)
const linkedTasksLoading = ref(false)
const linkedTasks = ref<any[]>([])

const checkVisible = ref(false)
const checking = ref(false)
const checkLoading = ref(false)
const checkBatch = ref<MatBatchView | null>(null)
const checkDetail = ref<any>(null)

const releaseVisible = ref(false)
const releasing = ref(false)
const releaseBatch = ref<MatBatchView | null>(null)

interface CheckRow {
  item: string
  level: string
  requirement: string
  actual: string
  ok: boolean
}

function resetQuery() {
  query.line = ''
  query.name = ''
  query.status = ''
  load(1)
}

function statusOf(row: MatBatchView) {
  if (row.linked) return { name: '已关联', tag: 'success' }
  return MAT_STATUS[row.status] || { name: row.status, tag: 'info' }
}

function acceptOf(line: string) {
  return (
    (LINE_WHITELIST_TEXT[line] || '')
      .split(/[\s/]+/)
      .filter(Boolean)
      .map((ext) => '.' + ext)
      .join(',') + ',.zip'
  )
}

function onFiles(e: Event) {
  uploadForm.files = Array.from((e.target as HTMLInputElement).files || [])
}

async function load(page?: number) {
  if (page) query.pageNum = page
  loading.value = true
  try {
    const res = await materialPage({
      line: query.line || undefined,
      name: query.name || undefined,
      status: query.status || undefined,
      page: query.pageNum,
      limit: query.pageSize,
    })
    rows.value = res.rows
    total.value = Number(res.total)
  } finally {
    loading.value = false
  }
}

async function doUpload() {
  if (!uploadForm.name.trim()) return ElMessage.warning('请填写批次名称')
  if (!uploadForm.files.length) return ElMessage.warning('请选择文件')
  uploading.value = true
  try {
    const batch = await materialUpload(uploadForm.line, uploadForm.name.trim(), uploadForm.files)
    ElMessage.success(`上传成功：${batch.bizNo}（已按白名单完成文件级校验）`)
    uploadVisible.value = false
    uploadForm.name = ''
    uploadForm.files = []
    if (fileInput.value) fileInput.value.value = ''
    load(1)
  } finally {
    uploading.value = false
  }
}

function rejectCount(reason: string) {
  const item = (checkDetail.value?.rejectSummary || checkBatch.value?.rejectSummary || [])
    .find((entry: any) => String(entry.reason || '').includes(reason))
  return Number(item?.count || 0)
}

function hasRejectReason(reason: string) {
  return (checkDetail.value?.files || []).some(
    (file: any) => file.status !== 'passed' && String(file.rejectReason || '').includes(reason),
  )
}

const checkRows = computed<CheckRow[]>(() => {
  const batch = checkBatch.value
  if (!batch) return []
  const files = checkDetail.value?.files || []
  const validFiles = files.filter((file: any) => file.status === 'passed')
  const allowed = (LINE_WHITELIST_TEXT[batch.line] || '')
    .split('/')
    .map((item) => item.trim().toUpperCase())
    .filter(Boolean)
  const formats =
    [...new Set(validFiles.map((file: any) => String(file.ext || '').toUpperCase()).filter(Boolean))].join(' / ') || '—'
  const oversized = files.filter((file: any) => Number(file.sizeBytes || 0) > 50 * 1024 * 1024)
  const duplicateCount = rejectCount('重复文件')
  const rows: CheckRow[] = [
    {
      item: '格式',
      level: '必查（自动剔除，不阻断）',
      requirement: allowed.join(' / ') || '—',
      actual: formats,
      ok: validFiles.length > 0,
    },
    {
      item: '批次名称唯一',
      level: '必查',
      requirement: '不重名',
      actual: '不重名',
      ok: true,
    },
    {
      item: '重复文件',
      level: '必查（自动剔除，不阻断）',
      requirement: '哈希一致即剔除',
      actual: `已剔除 ${duplicateCount} 条`,
      ok: validFiles.length > 0,
    },
    {
      item: '单文件大小',
      level: '必查（自动剔除，不阻断）',
      requirement: '≤ 50 MB',
      actual: oversized.length ? `${oversized.length} 个文件超限` : '上传时已校验',
      ok: oversized.length === 0 && validFiles.length > 0,
    },
  ]

  if (batch.line === 'formula' || batch.line === 'layout') {
    const pdfFiles = files.filter((file: any) => String(file.ext || '').toLowerCase() === 'pdf')
    const validPages = pdfFiles.filter((file: any) => file.status === 'passed' && Number(file.pageCount || 0) > 0)
    const brokenPdf = pdfFiles.filter((file: any) => file.status !== 'passed')
    rows.push({
      item: 'PDF 加密 / 损坏',
      level: '必查（自动剔除，不阻断）',
      requirement: '无加密、可解析',
      actual: brokenPdf.length ? `存在 ${brokenPdf.length} 个无法解析文件` : '无加密、可解析',
      ok: pdfFiles.length > 0 && brokenPdf.length === 0,
    })
    rows.push({
      item: '页数',
      level: '必查',
      requirement: '> 0',
      actual: validPages.length ? `${validPages.map((file: any) => file.pageCount).join(' / ')} 页` : '无法读取页数',
      ok: validPages.length > 0,
    })
  } else if (batch.line === 'graphic') {
    const resolutionFailed = hasRejectReason('分辨率')
    rows.push({
      item: '图片分辨率',
      level: '必查（自动剔除，不阻断）',
      requirement: '≥ 600 × 600',
      actual: resolutionFailed ? '存在低于最小分辨率的图片' : '上传时已校验',
      ok: validFiles.length > 0 && !resolutionFailed,
    })
  } else {
    const contentFailed = hasRejectReason('编码') || hasRejectReason('可读字符')
    rows.push({
      item: 'HTML 可读内容',
      level: '必查（自动剔除，不阻断）',
      requirement: '去标签后可读字符 ≥ 20',
      actual: contentFailed ? '存在编码或正文不足文件' : '上传时已校验',
      ok: validFiles.length > 0 && !contentFailed,
    })
  }
  return rows
})

const checkPassed = computed(() => checkRows.value.length > 0 && checkRows.value.every((row) => row.ok))

async function openCheck(row: MatBatchView) {
  checkBatch.value = row
  checkDetail.value = null
  checkVisible.value = true
  checkLoading.value = true
  try {
    checkDetail.value = await materialDetail(row.bizNo)
  } finally {
    checkLoading.value = false
  }
}

function resetCheck() {
  checkBatch.value = null
  checkDetail.value = null
}

async function confirmCheck() {
  if (!checkBatch.value || !checkPassed.value) return
  checking.value = true
  try {
    const result = await materialCheck(checkBatch.value.bizNo)
    if (result?.status === 'upload_failed') ElMessage.warning('准入校验完成，但没有有效素材，批次已标记为上传失败')
    else ElMessage.success('准入校验通过，批次已标记为已校验')
    checkVisible.value = false
    load()
  } finally {
    checking.value = false
  }
}

function openRelease(row: MatBatchView) {
  releaseBatch.value = row
  releaseVisible.value = true
}

async function confirmRelease() {
  if (!releaseBatch.value) return
  releasing.value = true
  try {
    await materialRelease(releaseBatch.value.bizNo)
    ElMessage.success('素材批次已移交，可被本产线任务引用')
    releaseVisible.value = false
    load()
  } finally {
    releasing.value = false
  }
}

function openEdit(row: MatBatchView) {
  editing.value = row
  editForm.name = row.name
  editForm.line = row.line
  editVisible.value = true
}

async function doEdit() {
  if (!editing.value) return
  await materialEdit(editing.value.bizNo, { name: editForm.name, line: editForm.line })
  ElMessage.success('已保存（变更已记录）')
  editVisible.value = false
  load()
}

async function doDelete(row: MatBatchView) {
  await ElMessageBox.confirm(`确认删除批次「${row.name}」？仅未移交且未被任务关联的批次可删除。`, '删除确认', { type: 'warning' })
  await materialDelete(row.bizNo)
  ElMessage.success('已删除')
  load()
}

async function openDetail(row: MatBatchView) {
  detail.value = await materialDetail(row.bizNo)
  detailVisible.value = true
}

async function openLinkedTasks() {
  if (!detail.value) return
  linkedTasksVisible.value = true
  linkedTasksLoading.value = true
  try {
    const ids = new Set((detail.value.linkedTaskIds || []).map(String))
    const result = await taskPage({ line: detail.value.line, page: 1, limit: 500 })
    linkedTasks.value = result.rows.filter((task: any) => ids.has(String(task.id)))
  } finally {
    linkedTasksLoading.value = false
  }
}

function openLinkedTask(row: any) {
  router.push({ path: `/custom-text/task/${row.bizNo}`, query: { fromWb: `/custom-text/wb/${row.line}` } })
}

function timeFmt(_r: any, _c: any, v: string) {
  if (!v || v === 'null') return '—'
  return v.replace('T', ' ').slice(0, 19)
}

onMounted(() => load())
</script>

<style scoped>
.pager { margin-top: 14px; justify-content: flex-end; }
.hint { font-size: var(--tcs-font-size-helper); color: var(--tcs-color-text-secondary); line-height: 1.6; }
.muted { color: var(--tcs-color-text-weak); }
.reject-tag { margin: 0 8px 6px 0; }
.check-dialog :deep(.el-dialog__body) { padding-top: 12px; }
.check-intro { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 12px; color: var(--tcs-color-text); }
.check-table { border-radius: var(--tcs-radius-control); overflow: hidden; }
.check-note { margin-top: 12px; padding: 10px 12px; border: 1px solid var(--tcs-color-border); border-radius: 4px; font-size: var(--tcs-font-size-helper); line-height: 1.6; }
.check-note--pass { border-color: #b7ebc6; background: #f0fdf4; color: #128a57; }
.check-note--fail { border-color: #fecaca; background: #fef2f2; color: #b42318; }
.release-batch-line { margin-bottom: 10px; color: var(--tcs-color-text); }
.release-note { padding: 12px 14px; border: 1px solid var(--tcs-color-border); border-radius: 4px; background: var(--tcs-color-bg-page); color: var(--tcs-color-text); line-height: 1.7; }
h4 { margin: 18px 0 8px; color: var(--tcs-color-title); }
</style>
