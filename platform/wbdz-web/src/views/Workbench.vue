<template>
  <div>
    <div class="stat-row">
      <el-card v-for="s in stats" :key="s.key" shadow="hover" class="stat" :class="s.cls">
        <div class="stat-value">{{ s.value }}</div>
        <div class="stat-label">{{ s.label }}</div>
      </el-card>
    </div>

    <el-card shadow="never">
      <div class="toolbar">
        <el-input v-model="query.name" placeholder="任务名称/编号" clearable style="width: 200px" @keyup.enter="load(1)" />
        <el-select v-model="query.status" placeholder="状态" clearable style="width: 130px">
          <el-option v-for="(s, k) in TASK_STATUS" :key="k" :label="s.name" :value="k" />
        </el-select>
        <el-select v-model="query.priority" placeholder="优先级" clearable style="width: 120px">
          <el-option v-for="(p, k) in PRIORITIES" :key="k" :label="p.name" :value="k" />
        </el-select>
        <el-button type="primary" @click="load(1)">查询</el-button>
        <div style="flex: 1" />
        <el-button type="primary" @click="openCreate">新建任务</el-button>
        <el-button @click="load()">刷新</el-button>
      </div>

      <el-table :data="rows" v-loading="loading">
        <el-table-column label="任务编号" width="210"><template #default="{ row }"><BizIdText :value="row.bizNo" /></template></el-table-column>
        <el-table-column prop="name" label="任务名称" min-width="170" show-overflow-tooltip />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="TASK_STATUS[row.status]?.tag" effect="light">{{ row.statusName }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="环节进度" width="150">
          <template #default="{ row }">
            <el-progress :percentage="progressOf(row)" :stroke-width="8" :format="() => `第 ${row.currentStage}/3 环节`" />
          </template>
        </el-table-column>
        <el-table-column label="优先级" width="80">
          <template #default="{ row }">
            <el-tag :type="PRIORITIES[row.priority]?.tag" size="small">{{ PRIORITIES[row.priority]?.name }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="batchName" label="素材批次" min-width="150" show-overflow-tooltip />
        <el-table-column prop="paramVersion" label="参数版本" width="90" />
        <el-table-column prop="threshold" label="阈值" width="70" />
        <el-table-column prop="datasetCount" label="数据集" width="70" align="center" />
        <el-table-column prop="createTime" label="创建时间" width="170" :formatter="timeFmt" />
        <el-table-column label="操作" width="240" fixed="right">
          <template #default="{ row }">
            <el-button v-if="row.status === 'draft'" size="small" type="primary" @click="doSubmit(row)">提交</el-button>
            <el-button v-if="row.status === 'pending'" size="small" type="primary" @click="doStart(row)">启动</el-button>
            <el-button size="small" @click="goDetail(row)">详情</el-button>
            <el-button v-if="row.status === 'draft'" size="small" type="danger" plain @click="doDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination class="pager" layout="total, prev, pager, next" :total="total"
        v-model:current-page="query.pageNum" :page-size="query.pageSize" @current-change="load()" />
    </el-card>

    <!-- 新建任务 -->
    <el-dialog v-model="createVisible" title="新建任务" class="wbdz-dialog">
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
          <el-radio-group v-model="form.imageClass">
            <el-radio-button v-for="c in IMAGE_CLASSES" :key="c" :value="c">{{ c }}</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="优先级">
          <el-radio-group v-model="form.priority">
            <el-radio-button v-for="(p, k) in PRIORITIES" :key="k" :value="k">{{ p.name }}</el-radio-button>
          </el-radio-group>
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
        <el-button type="primary" :loading="creating" @click="doCreate">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import BizIdText from '@/components/BizIdText.vue'
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  LINE_NAMES, IMAGE_CLASSES, PRIORITIES, TASK_STATUS,
  taskPage, taskCreate, taskSubmit, taskStart, taskDelete,
  materialPage, paramLineConfig, type TaskView, type MatBatchView,
} from '@/api'

const props = defineProps<{ line: string }>()
const route = useRoute()
const router = useRouter()
const line = computed(() => props.line || (route.params.line as string))

const query = reactive({ status: '', name: '', priority: '', pageNum: 1, pageSize: 10 })
const rows = ref<TaskView[]>([])
const total = ref(0)
const loading = ref(false)

const stats = ref([
  { key: 'total', label: '任务总数', value: 0, cls: '' },
  { key: 'running', label: '处理中', value: 0, cls: 'blue' },
  { key: 'waitreview', label: '待复核', value: 0, cls: 'red' },
  { key: 'quality', label: '待归集', value: 0, cls: 'green' },
  { key: 'collected', label: '已归集', value: 0, cls: 'gray' },
])

const createVisible = ref(false)
const creating = ref(false)
const batches = ref<MatBatchView[]>([])
const versions = ref<any[]>([])
const form = reactive<any>({
  name: '', batchId: undefined, priority: 'mid', imageClass: '', paramVersion: '', threshold: 0.8,
})

function progressOf(row: TaskView) {
  if (row.status === 'collected') return 100
  return Math.min(100, Math.round(((row.currentStage - 1) / 3) * 100))
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
    total.value = res.total
    const all = await taskPage({ line: line.value, pageNum: 1, pageSize: 500 })
    stats.value[0].value = all.total
    stats.value[1].value = all.records.filter((r) => r.status === 'processing' || r.status === 'pending').length
    stats.value[2].value = all.records.filter((r) => r.status === 'waitreview').length
    stats.value[3].value = all.records.filter((r) => r.status === 'quality').length
    stats.value[4].value = all.records.filter((r) => r.status === 'collected').length
  } finally {
    loading.value = false
  }
}

async function openCreate() {
  form.name = ''
  form.batchId = undefined
  form.priority = 'mid'
  form.imageClass = ''
  form.paramVersion = ''
  form.threshold = 0.8
  const [b, p] = await Promise.all([
    materialPage({ line: line.value, status: 'released', pageNum: 1, pageSize: 100 }),
    paramLineConfig(line.value),
  ])
  batches.value = b.records
  versions.value = (p.versions || []).filter((v: any) => v.version && v.version !== 'draft')
  createVisible.value = true
}

async function doCreate() {
  if (!form.name.trim()) return ElMessage.warning('请填写任务名称')
  if (!form.batchId) return ElMessage.warning('请选择素材批次')
  if (line.value === 'graphic' && !form.imageClass) return ElMessage.warning('图文融合任务必须选择图片大类')
  creating.value = true
  try {
    const task: any = await taskCreate({
      name: form.name.trim(), line: line.value, batchId: form.batchId,
      priority: form.priority, imageClass: form.imageClass || undefined,
      paramVersion: form.paramVersion || undefined, threshold: form.threshold,
    })
    ElMessage.success(`任务已创建（草稿）：${task.bizNo}`)
    createVisible.value = false
    load(1)
  } finally {
    creating.value = false
  }
}

async function doSubmit(row: TaskView) {
  await taskSubmit(row.id)
  ElMessage.success('已提交，等待启动')
  load()
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
.stat-row { display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; margin-bottom: 14px; }
.stat { text-align: center; }
.stat-value { font-size: var(--wbdz-font-stat); font-weight: 600; color: var(--wbdz-title); }
.stat-label { font-size: var(--wbdz-font-body); color: var(--wbdz-secondary); margin-top: 4px; }
.stat.blue .stat-value { color: var(--wbdz-primary); }
.stat.red .stat-value { color: var(--wbdz-danger); }
.stat.green .stat-value { color: var(--wbdz-success); }
.stat.gray .stat-value { color: var(--wbdz-secondary); }
.toolbar { display: flex; gap: 10px; margin-bottom: 14px; align-items: center; }
.pager { margin-top: 14px; justify-content: flex-end; }
.hint { font-size: var(--wbdz-font-caption); color: var(--wbdz-secondary); line-height: 1.6; }
</style>
