<template>
  <div class="page-stack">
    <PageHeader title="素材管理" description="跨产线管理素材批次，完成上传、准入校验、移交和任务关联追溯。" />

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
            <label class="filter-label">批次名称</label>
            <el-input v-model="query.name" placeholder="请输入批次名称" clearable style="width: 200px" @keyup.enter="load(1)" />
          </div>
          <div class="filter-field">
            <label class="filter-label">状态</label>
            <el-select v-model="query.status" placeholder="全部状态" clearable style="width: 160px" @change="load(1)">
              <el-option v-for="(s, k) in MAT_STATUS" :key="k" :label="s.name" :value="k" />
            </el-select>
          </div>
        </div>
        <div class="search-actions">
          <el-button @click="resetQuery">重置</el-button>
          <el-button type="primary" @click="uploadVisible = true">+ 上传素材</el-button>
        </div>
      </div>

      <el-table :data="rows" v-loading="loading">
        <el-table-column label="批次编号" width="210"><template #default="{ row }"><BizIdText :value="row.bizNo" /></template></el-table-column>
        <el-table-column prop="name" label="批次名称" min-width="160" show-overflow-tooltip />
        <el-table-column prop="lineName" label="产线" width="110" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusOf(row).tag" effect="light">{{ statusOf(row).name }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="有效/原始条数" width="120" align="center">
          <template #default="{ row }">{{ row.fileCount }} / {{ row.totalCount }}</template>
        </el-table-column>
        <el-table-column label="剔除情况" min-width="200">
          <template #default="{ row }">
            <span v-if="!row.rejectSummary?.length" class="muted">—</span>
            <span v-else>{{ rejectText(row) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="createBy" label="上传人" width="100" />
        <el-table-column prop="createTime" label="上传时间" width="170" :formatter="timeFmt" />
        <el-table-column label="操作" width="300" fixed="right">
          <template #default="{ row }">
            <el-button v-if="row.status === 'uncheked'" link type="primary" size="small" @click="doCheck(row)">准入校验</el-button>
            <el-button v-if="row.status === 'checked'" link type="primary" size="small" @click="doRelease(row)">移交</el-button>
            <el-button link type="primary" size="small" @click="openDetail(row)">详情</el-button>
            <el-button v-if="row.status !== 'upload_failed'" link type="primary" size="small" @click="openEdit(row)">编辑</el-button>
            <el-button v-if="!row.linked && row.status !== 'released'" link type="danger" size="small" @click="doDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination class="pager" layout="total, prev, pager, next" :total="total"
        v-model:current-page="query.pageNum" :page-size="query.pageSize" @current-change="load()" />
    </el-card>

    <!-- 上传弹窗 -->
    <el-dialog v-model="uploadVisible" title="上传素材批次" class="wbdz-dialog">
      <el-form label-width="90px">
        <el-form-item label="产线" required>
          <el-select v-model="uploadForm.line" style="width: 100%">
            <el-option v-for="(n, l) in LINE_NAMES" :key="l" :label="n" :value="l" />
          </el-select>
          <div class="hint">允许格式：{{ LINE_WHITELIST_TEXT[uploadForm.line] || '—' }}（ZIP 内逐文件校验，白名单外自动剔除计数）</div>
        </el-form-item>
        <el-form-item label="批次名称" required>
          <el-input v-model="uploadForm.name" placeholder="同产线唯一" />
        </el-form-item>
        <el-form-item label="素材文件" required>
          <input ref="fileInput" type="file" multiple :accept="acceptOf(uploadForm.line)" @change="onFiles" />
          <div class="hint">已选 {{ uploadForm.files.length }} 个文件</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="uploadVisible = false">取消</el-button>
        <el-button type="primary" :loading="uploading" @click="doUpload">上传</el-button>
      </template>
    </el-dialog>

    <!-- 编辑弹窗 -->
    <el-dialog v-model="editVisible" title="编辑批次基本信息" class="wbdz-dialog">
      <el-form label-width="90px">
        <el-form-item label="批次名称">
          <el-input v-model="editForm.name" />
        </el-form-item>
        <el-form-item label="产线">
          <el-select v-model="editForm.line" style="width: 100%" :disabled="editing?.linked">
            <el-option v-for="(n, l) in LINE_NAMES" :key="l" :label="n" :value="l" />
          </el-select>
          <div v-if="editing?.linked" class="hint">已被任务引用，产线不可修改</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" @click="doEdit">保存</el-button>
      </template>
    </el-dialog>

    <!-- 详情抽屉 -->
    <el-drawer v-model="detailVisible" title="批次详情" class="wbdz-drawer">
      <template v-if="detail">
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="批次编号"><BizIdText :value="detail.bizNo" /></el-descriptions-item>
          <el-descriptions-item label="名称">{{ detail.name }}</el-descriptions-item>
          <el-descriptions-item label="产线">{{ detail.lineName }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="MAT_STATUS[detail.status]?.tag">{{ MAT_STATUS[detail.status]?.name }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="有效条数">{{ detail.fileCount }}</el-descriptions-item>
          <el-descriptions-item label="原始条数">{{ detail.totalCount }}</el-descriptions-item>
          <el-descriptions-item label="关联任务" :span="2">
            {{ detail.linkedTaskIds?.length ? `已关联（${detail.linkedTaskIds.length} 个任务）` : '未关联' }}
          </el-descriptions-item>
        </el-descriptions>

        <h4>剔除汇总</h4>
        <el-empty v-if="!detail.rejectSummary?.length" description="无剔除" :image-size="48" />
        <el-tag v-for="r in detail.rejectSummary" :key="r.reason" type="danger" effect="plain" class="reject-tag">
          {{ r.reason }} × {{ r.count }}
        </el-tag>

        <h4>文件清单</h4>
        <el-table :data="detail.files" size="small" max-height="300">
          <el-table-column prop="name" label="文件名" min-width="180" show-overflow-tooltip />
          <el-table-column prop="ext" label="格式" width="70" />
          <el-table-column label="页数" width="70">
            <template #default="{ row }">{{ row.pageCount ?? '—' }}</template>
          </el-table-column>
          <el-table-column label="状态" width="90">
            <template #default="{ row }">
              <el-tag :type="row.status === 'passed' ? 'success' : 'danger'" size="small">
                {{ row.status === 'passed' ? '通过' : '剔除' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="rejectReason" label="剔除原因" min-width="160" show-overflow-tooltip />
        </el-table>

        <h4>变更记录</h4>
        <el-empty v-if="!detail.changes?.length" description="无变更" :image-size="48" />
        <el-timeline v-else style="padding-left: 8px">
          <el-timeline-item v-for="(c, i) in detail.changes" :key="i" :timestamp="c.time">
            {{ c.item === 'name' ? '名称' : '产线' }}：{{ c.oldValue }} → {{ c.newValue }}（{{ c.operator }}）
          </el-timeline-item>
        </el-timeline>
      </template>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import PageHeader from '@/components/PageHeader.vue'
import BizIdText from '@/components/BizIdText.vue'
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  LINE_NAMES, LINE_WHITELIST_TEXT, MAT_STATUS,
  materialPage, materialDetail, materialUpload, materialCheck, materialRelease,
  materialEdit, materialDelete, type MatBatchView,
} from '@/api'

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

function rejectText(row: MatBatchView) {
  return row.rejectSummary.map((r) => `${r.reason}×${r.count}`).join('；')
}

function acceptOf(line: string) {
  return (LINE_WHITELIST_TEXT[line] || '').split(/[\s/]+/).filter(Boolean).map((e) => '.' + e).join(',') + ',.zip'
}

function onFiles(e: Event) {
  uploadForm.files = Array.from((e.target as HTMLInputElement).files || [])
}

async function load(page?: number) {
  if (page) query.pageNum = page
  loading.value = true
  try {
    const res = await materialPage({
      line: query.line || undefined, name: query.name || undefined, status: query.status || undefined,
      pageNum: query.pageNum, pageSize: query.pageSize,
    })
    rows.value = res.records
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

async function doCheck(row: MatBatchView) {
  await materialCheck(row.bizNo)
  ElMessage.success('准入校验完成')
  load()
}

async function doRelease(row: MatBatchView) {
  await materialRelease(row.bizNo)
  ElMessage.success('已移交')
  load()
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

function timeFmt(_r: any, _c: any, v: string) {
  if (!v || v === 'null') return '—'
  return v.replace('T', ' ').slice(0, 19)
}

onMounted(() => load())
</script>

<style scoped>

.pager { margin-top: 14px; justify-content: flex-end; }
.hint { font-size: var(--wbdz-font-caption); color: var(--wbdz-secondary); line-height: 1.6; }
.muted { color: var(--wbdz-weaker); }
.reject-tag { margin: 0 8px 6px 0; }
h4 { margin: 18px 0 8px; color: var(--wbdz-title); }
</style>
