<template>
  <div class="page-stack">
    <PageHeader :title="`${LINE_NAMES[line]}工作台`" :description="pageDescription" />

    <el-card shadow="never">
      <div class="statbar">
        <div v-for="s in stats" :key="s.key" class="stat">
          <div class="stat-num" :class="s.cls">{{ s.value }}</div>
          <div class="stat-label">{{ s.label }}</div>
        </div>
      </div>
    </el-card>

    <el-card shadow="never">
      <div class="search-panel">
        <div class="search-fields">
          <div class="filter-field">
            <label class="filter-label">任务名称</label>
            <el-input v-model="query.name" placeholder="请输入任务名称" clearable style="width: 200px" @keyup.enter="load(1)" />
          </div>
          <div class="filter-field">
            <label class="filter-label">状态</label>
            <el-select v-model="query.status" placeholder="全部状态" clearable style="width: 160px" @change="load(1)">
              <el-option v-for="(s, k) in TASK_STATUS" :key="k" :label="s.name" :value="k" />
            </el-select>
          </div>
          <div class="filter-field">
            <label class="filter-label">优先级</label>
            <el-select v-model="query.priority" placeholder="全部优先级" clearable style="width: 160px" @change="load(1)">
              <el-option v-for="(p, k) in PRIORITIES" :key="k" :label="p.name" :value="k" />
            </el-select>
          </div>
        </div>
        <div class="search-actions">
          <el-button @click="resetQuery">重置</el-button>
          <el-button type="primary" @click="openCreate">+ 新建任务</el-button>
          <el-button @click="goMaterial">上传素材</el-button>
        </div>
      </div>

      <el-table :data="rows" v-loading="loading">
        <el-table-column label="任务编号" width="220"><template #default="{ row }"><BizIdText :value="row.bizNo" /></template></el-table-column>
        <el-table-column prop="name" label="任务名称" min-width="220" show-overflow-tooltip />
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="TASK_STATUS[row.status]?.tag" effect="light">{{ row.statusName }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="优先级" width="90">
          <template #default="{ row }">
            <el-tag :type="PRIORITIES[row.priority]?.tag" size="small">{{ PRIORITIES[row.priority]?.name }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="paramVersion" label="参数版本" width="110" />
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button v-if="row.status === 'draft'" link type="primary" size="small" @click="openEdit(row)">继续编辑</el-button>
            <el-button v-else-if="row.status === 'pending'" link type="primary" size="small" @click="doStart(row)">启动</el-button>
            <el-button v-else-if="row.status === 'waitreview'" link type="primary" size="small" @click="goReview">去复核</el-button>
            <el-button v-else-if="row.status === 'quality'" link type="primary" size="small" @click="goDataset">去归集</el-button>
            <span v-else-if="row.status === 'collected'" class="muted">已归集</span>
            <el-button v-else link type="primary" size="small" @click="goDetail(row)">继续处理</el-button>
            <span class="sep">·</span>
            <el-button link type="primary" size="small" @click="goDetail(row)">详情</el-button>
            <template v-if="row.status === 'draft'">
              <span class="sep">·</span>
              <el-button link type="danger" size="small" @click="doDelete(row)">删除</el-button>
            </template>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination class="pager" layout="total, prev, pager, next" :total="total"
        v-model:current-page="query.pageNum" :page-size="query.pageSize" @current-change="load()" />      <div class="hint"><b>任务流转：</b>待启动 → 加工中 → 待归集 / 待复核 → 已归集。四条产线不提供暂停、终止或撤销任务操作。</div>
    </el-card>

    <!-- 新建任务 -->
    <el-dialog v-model="createVisible" :title="editingTaskId ? '编辑任务' : '新建任务'" class="wbdz-dialog">
      <el-form label-width="100px">
        <el-form-item label="任务名称" required>
          <el-input v-model="form.name" placeholder="如：2026Q4 政策文本元信息批次" />
        </el-form-item>
        <el-form-item label="素材批次" required>
          <el-select v-model="form.batchId" style="width: 100%" placeholder="仅可选择已移交批次" no-data-text="暂无已移交批次，请先在素材管理中完成校验与移交">
            <el-option v-for="b in batches" :key="b.id" :label="`${b.bizNo} · ${b.name}（${b.fileCount} 条）`" :value="b.id" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="line === 'graphic'" label="图片大类" required>
          <el-select v-model="form.imageClass" style="width: 100%" placeholder="请选择图片大类">
            <el-option v-for="c in IMAGE_CLASSES" :key="c" :label="c" :value="c" />
          </el-select>
        </el-form-item>
        <el-form-item label="优先级">
          <el-select v-model="form.priority" style="width: 100%">
            <el-option v-for="(p, k) in PRIORITIES" :key="k" :label="p.name" :value="k" />
          </el-select>
        </el-form-item>
        <el-form-item label="参数版本">
          <el-select v-model="form.paramVersion" style="width: 100%" placeholder="默认取当前产线最新版本" clearable>
            <el-option v-for="v in versions" :key="v.version" :label="`${v.version}（${v.publishedBy || '-'}）`" :value="v.version" />
          </el-select>
          <div class="hint">创建后参数快照即锁定，后续参数发布不影响本任务。</div>
        </el-form-item>
        <el-form-item label="置信度阈值">
          <el-input-number v-model="form.threshold" :min="0" :max="1" :step="0.01" :precision="2" />
          <span class="hint" style="margin-left: 10px">低于该值的条目进入条件复核（默认 0.80）</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <template v-if="editingTaskId">
          <el-button :loading="creating" @click="doCreate(false)">保存草稿</el-button>
          <el-button type="primary" :loading="creating" @click="doCreate(true)">保存并待启动</el-button>
        </template>
        <template v-else>
          <el-button :loading="creating" @click="doCreate(false)">保存草稿</el-button>
          <el-button type="primary" :loading="creating" @click="doCreate(true)">创建并待启动</el-button>
        </template>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import PageHeader from '@/components/PageHeader.vue'
import BizIdText from '@/components/BizIdText.vue'
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  LINE_NAMES, IMAGE_CLASSES, PRIORITIES, TASK_STATUS,
  taskPage, taskCreate, taskUpdate, taskSubmit, taskStart, taskDelete,
  materialPage, paramLineConfig, type TaskView, type MatBatchView,
} from '@/api'

const props = defineProps<{ line: string }>()
const route = useRoute()
const router = useRouter()
const line = computed(() => props.line || (route.params.line as string))

const LINE_DESCRIPTIONS: Record<string, string> = {
  formula: '公式文本定制化数据的任务编排与全流程加工；素材上传与维护已统一提取至公共素材管理。',
  layout: '复杂版面定制化数据的任务编排、逐页检测与质量校验；素材统一从公共素材库引用。',
  graphic: '图文融合定制化数据的区域定位、判型和描述生成；任务创建时锁定图片大类。',
  metadata: '文本元信息定制化数据的切片、体裁判定、事实抽取和字段补全；素材统一从公共素材库引用。',
}
const pageDescription = computed(() => LINE_DESCRIPTIONS[line.value] || '产线任务编排与全流程加工。')

const query = reactive({ status: '', name: '', priority: '', pageNum: 1, pageSize: 10 })
const rows = ref<TaskView[]>([])
const total = ref(0)
const loading = ref(false)

const stats = ref([
  { key: 'waitreview', label: '待复核', value: 0, cls: '' },
  { key: 'quality', label: '待归集', value: 0, cls: 'green' },
  { key: 'pending', label: '待处理', value: 0, cls: 'warn' },
])

const createVisible = ref(false)
const editingTaskId = ref<string | null>(null)
const creating = ref(false)
const batches = ref<MatBatchView[]>([])
const versions = ref<any[]>([])
const form = reactive<any>({
  name: '', batchId: undefined, priority: 'mid', imageClass: '', paramVersion: '', threshold: 0.8,
})

function resetQuery() {
  query.name = ''
  query.status = ''
  query.priority = ''
  load(1)
}

async function load(page?: number) {
  if (page) query.pageNum = page
  loading.value = true
  try {
    const res = await taskPage({
      line: line.value, status: query.status || undefined, name: query.name || undefined,
      priority: query.priority || undefined, pageNum: query.pageNum, pageSize: query.pageSize,
    })
    rows.value = res.records
    total.value = Number(res.total)
    const all = await taskPage({ line: line.value, pageNum: 1, pageSize: 500 })
    stats.value[0].value = all.records.filter((r) => r.status === 'waitreview').length
    stats.value[1].value = all.records.filter((r) => r.status === 'quality').length
    stats.value[2].value = all.records.filter((r) => r.status === 'pending' || r.status === 'reject').length
  } finally {
    loading.value = false
  }
}

async function loadTaskDialogOptions() {
  const [b, p] = await Promise.all([
    materialPage({ line: line.value, status: 'released', pageNum: 1, pageSize: 100 }),
    paramLineConfig(line.value),
  ])
  batches.value = b.records
  versions.value = (p.versions || []).filter((v: any) => v.version && v.version !== 'draft')
}

async function openCreate() {
  editingTaskId.value = null
  form.name = ''
  form.batchId = undefined
  form.priority = 'mid'
  form.imageClass = ''
  form.paramVersion = ''
  form.threshold = 0.8
  await loadTaskDialogOptions()
  createVisible.value = true
}

async function openEdit(row: TaskView) {
  editingTaskId.value = row.id
  form.name = row.name
  form.batchId = row.batchId
  form.priority = row.priority || 'mid'
  form.imageClass = row.imageClass || ''
  form.paramVersion = row.paramVersion || ''
  form.threshold = Number(row.threshold ?? 0.8)
  await loadTaskDialogOptions()
  createVisible.value = true
}

async function doCreate(submitAfter: boolean) {
  if (!form.name.trim()) return ElMessage.warning('请填写任务名称')
  if (!form.batchId) return ElMessage.warning('请选择素材批次')
  if (line.value === 'graphic' && !form.imageClass) return ElMessage.warning('图文融合任务必须选择图片大类')
  creating.value = true
  try {
    const body = {
      name: form.name.trim(), batchId: form.batchId,
      priority: form.priority, imageClass: form.imageClass || undefined,
      paramVersion: form.paramVersion || undefined, threshold: form.threshold,
    }
    const task: any = editingTaskId.value
      ? await taskUpdate(editingTaskId.value, body)
      : await taskCreate({ ...body, line: line.value })
    if (submitAfter) {
      await taskSubmit(String(task.id))
      ElMessage.success(editingTaskId.value ? `任务已保存并进入待处理：${task.bizNo}` : `任务已创建并进入待处理：${task.bizNo}`)
    } else {
      ElMessage.success(editingTaskId.value ? `任务已保存：${task.bizNo}` : `任务已保存草稿：${task.bizNo}`)
    }
    createVisible.value = false
    load(1)
  } finally {
    creating.value = false
  }
}


async function doStart(row: TaskView) {
  await ElMessageBox.confirm(`确认启动任务「${row.name}」？启动后将按算子链依次执行。`, '启动确认', { type: 'warning' })
  await taskStart(row.id)
  ElMessage.success('任务已启动')
  load()
}

async function doDelete(row: TaskView) {
  await ElMessageBox.confirm(`确认删除草稿任务「${row.name}」？`, '删除确认', { type: 'warning' })
  await taskDelete(row.id)
  ElMessage.success('已删除')
  load()
}

function goMaterial() {
  router.push('/material')
}

function goReview() {
  router.push('/review')
}

function goDataset() {
  router.push('/dataset')
}
function goDetail(row: TaskView) {
  router.push({ path: `/task/${row.id}`, query: { fromWb: `/wb/${line.value}` } })
}

function timeFmt(_r: any, _c: any, v: string) {
  if (!v || v === 'null') return '—'
  return v.replace('T', ' ').slice(0, 19)
}

watch(line, () => load(1))
onMounted(() => load())

defineExpose({ lineName: LINE_NAMES[line.value] })
</script>

<style scoped>
.statbar { display: flex; }
.stat { flex: 1; padding: 16px 10px; text-align: center; border-right: 1px solid var(--wbdz-border); }
.stat:last-child { border-right: 0; }
.stat-num { color: var(--wbdz-title); font-size: 22px; font-weight: 650; }
.stat-num.warn { color: var(--wbdz-warning); }
.stat-num.green { color: var(--wbdz-success); }
.stat-label { margin-top: 2px; color: var(--wbdz-text); font-size: var(--wbdz-font-caption); }
.muted { color: var(--wbdz-weaker); }
.sep { margin: 0 7px; color: var(--wbdz-weaker); }

.pager { margin: 14px 0 0; justify-content: flex-end; }
.hint { margin: 10px 0 16px; color: var(--wbdz-secondary); font-size: var(--wbdz-font-caption); line-height: 1.6; }
</style>
