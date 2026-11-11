<template>
  <div
    v-loading="loading"
    class="page-stack"
  >
    <PageHeader
      v-if="task"
      title="任务详情"
      description="查看生产结果、归集版本、条件复核和交付状态。"
    >
      <template #actions>
        <el-button @click="goBack">
          返回任务列表
        </el-button>
        <el-button
          v-if="task.status === 'draft'"
          type="primary"
          @click="act('submit')"
        >
          提交
        </el-button>
        <el-button
          v-if="task.status === 'pending'"
          type="primary"
          @click="act('start')"
        >
          启动执行
        </el-button>
        <el-button
          v-if="task.status === 'quality'"
          type="success"
          @click="act('collect')"
        >
          去归集
        </el-button>
        <el-button
          v-if="task.status === 'waitreview' || task.status === 'quality'"
          type="warning"
          plain
          @click="openReject()"
        >
          重跑任务
        </el-button>
        <el-button
          v-if="task.status === 'draft'"
          type="danger"
          plain
          @click="act('delete')"
        >
          删除
        </el-button>
        <el-button @click="load">
          刷新
        </el-button>
      </template>
    </PageHeader>

    <section
      v-if="task"
      class="detail-card progress-card"
    >
      <div class="card-title-row">
        <div class="detail-card-title">
          任务进度
        </div>
        <span class="progress-value">{{ overallProgress }}% · {{ progressLabel }}</span>
      </div>
      <div class="progress-line">
        <i :style="{ width: `${overallProgress}%` }" />
      </div>
      <div class="stage-chips">
        <div
          v-for="(name, i) in stageNames"
          :key="i"
          class="stage-chip"
          :class="stageState(i + 1)"
        >
          <span class="stage-chip-no">{{ i + 1 }}</span>
          <span>{{ name }}</span>
          <span class="stage-chip-status">{{ stageStateText(i + 1) }}</span>
        </div>
      </div>
      <div
        v-if="latestError"
        class="error-callout"
      >
        <div>
          <b>第 {{ latestError.stageNo }} 环节“{{ latestError.stageName }}”运行失败：</b>
          <span class="error-message">{{ runError(latestError) }}</span>
        </div>
        <el-button
          v-if="task.status === 'pending'"
          size="small"
          type="danger"
          @click="act('start')"
        >
          重新启动任务
        </el-button>
        <el-button
          v-else-if="task.status === 'waitreview' || task.status === 'quality'"
          size="small"
          type="danger"
          @click="openReject(latestError.stageNo)"
        >
          从本环节重跑
        </el-button>
      </div>
    </section>

    <section
      v-if="task"
      class="detail-card overview-card"
    >
      <div class="detail-card-title">
        任务概览
      </div>
      <div class="overview-grid">
        <div class="overview-item">
          <label>任务ID</label>
          <span><BizIdText :value="task.bizNo" /></span>
        </div>
        <div class="overview-item overview-item-wide">
          <label>任务名称</label>
          <span>{{ task.name }}</span>
        </div>
        <div class="overview-item">
          <label>所属产线</label>
          <span>{{ task.lineName }}</span>
        </div>
        <div
          v-if="task.line === 'graphic'"
          class="overview-item"
        >
          <label>图片大类</label>
          <span>{{ task.imageClass || '未指定' }}</span>
        </div>
        <div class="overview-item overview-item-wide">
          <label>关联素材批次</label>
          <span v-if="task.batch">
            <BizIdText :value="task.batch.bizNo" />
            <span class="overview-muted"> · {{ task.batch.name }}（有效 {{ task.batch.fileCount ?? 0 }} 条）</span>
          </span>
          <span
            v-else
            class="muted"
          >未关联</span>
        </div>
        <div class="overview-item">
          <label>参数版本</label>
          <span>
            {{ task.paramVersion || '—' }}
            <el-button
              link
              type="primary"
              size="small"
              @click="openParamSnapshot"
            >查看快照</el-button>
          </span>
        </div>
        <div class="overview-item">
          <label>置信度阈值</label>
          <span>
            <span class="mono">{{ task.threshold ?? '—' }}</span>
            <el-button
              link
              type="primary"
              size="small"
              @click="openThreshold"
            >调整</el-button>
          </span>
        </div>
        <div class="overview-item">
          <label>优先级</label>
          <span><el-tag
            :type="PRIORITIES[task.priority]?.tag"
            size="small"
          >{{ PRIORITIES[task.priority]?.name || '—' }}</el-tag></span>
        </div>
        <div class="overview-item">
          <label>任务状态</label>
          <span><el-tag
            :type="TASK_STATUS[task.status]?.tag"
            size="small"
          >{{ task.statusName }}</el-tag></span>
        </div>
        <div class="overview-item">
          <label>创建人</label>
          <span>{{ task.createBy || '—' }}</span>
        </div>
        <div class="overview-item">
          <label>创建时间</label>
          <span>{{ fmt(task.createTime) }}</span>
        </div>
        <div class="overview-item">
          <label>当前环节</label>
          <span>第 {{ task.currentStage || 0 }}/{{ task.stageNames?.length || 3 }} 环节</span>
        </div>
      </div>
    </section>

    <section
      v-if="task"
      class="detail-card dataset-detail-card"
    >
      <div class="card-title-row">
        <div>
          <div class="detail-card-title">
            数据集明细
          </div>
          <div class="detail-card-subtitle">
            <template v-if="task.datasets?.length">
              {{ task.datasets[0].bizNo }} · {{ task.datasets[0].semVer }} · 共 {{ taskDatasetTotal }} 条 · 第 {{ taskDatasetPage }} / {{ taskDatasetPageCount }} 页
            </template>
            <template v-else>
              任务执行完成后生成可复核的数据集条目
            </template>
          </div>
        </div>
        <el-button
          v-if="task.datasets?.length"
          link
          type="primary"
          size="small"
          @click="openDataset(task.datasets[0].bizNo)"
        >
          完整明细
        </el-button>
      </div>

      <template v-if="task.datasets?.length">
        <div class="dataset-toolbar">
          <div class="dataset-filter">
            <label>复核范围</label>
            <el-select
              v-model="taskDatasetFilter"
              placeholder="全部"
              clearable
              style="width: 150px"
              @change="loadTaskDataset(1)"
            >
              <el-option
                label="全部"
                value=""
              />
              <el-option
                label="待复核"
                value="待复核"
              />
              <el-option
                label="已确认(A)"
                value="已确认"
              />
              <el-option
                label="已修正(B)"
                value="已修正"
              />
              <el-option
                label="已剔除(C)"
                value="已剔除"
              />
            </el-select>
          </div>
          <div class="dataset-filter">
            <label>低置信阈值</label>
            <el-input-number
              v-model="taskDatasetThreshold"
              :min="0"
              :max="1"
              :step="0.01"
              :precision="2"
              controls-position="right"
              style="width: 125px"
            />
          </div>
          <div class="dataset-toolbar-spacer" />
          <el-button
            v-if="activeTaskReviewOrder"
            type="primary"
            @click="openReview(activeTaskReviewOrder.bizNo)"
          >
            条件复核
          </el-button>
          <el-button
            v-else
            type="primary"
            :disabled="!taskDatasetItems.some(canAddToReview)"
            @click="addTaskDatasetToReview"
          >
            条件复核
          </el-button>
        </div>

        <el-table
          v-loading="taskDatasetLoading"
          :data="taskDatasetItems"
          size="small"
          class="dataset-table"
        >
          <el-table-column
            prop="itemKey"
            label="条目编号"
            min-width="210"
            show-overflow-tooltip
          />
          <el-table-column
            :label="recognitionConfidenceLabel"
            width="105"
            align="center"
          >
            <template #default="{ row }">
              <span :class="confidenceClass(itemRecognitionConfidence(row))">{{ formatConfidence(itemRecognitionConfidence(row)) }}</span>
            </template>
          </el-table-column>
          <el-table-column
            :label="semanticConfidenceLabel"
            width="125"
            align="center"
          >
            <template #default="{ row }">
              <span :class="confidenceClass(itemSemanticConfidence(row))">{{ formatConfidence(itemSemanticConfidence(row)) }}</span>
            </template>
          </el-table-column>
          <el-table-column
            label="低置信项"
            width="90"
            align="center"
          >
            <template #default="{ row }">
              <span :class="{ 'danger-text': itemLowConfidenceCount(row) > 0 }">{{ itemLowConfidenceCount(row) }}</span>
            </template>
          </el-table-column>
          <el-table-column
            label="低置信原因"
            min-width="230"
            show-overflow-tooltip
          >
            <template #default="{ row }">
              <span class="small muted">{{ itemLowConfidenceReason(row) }}</span>
            </template>
          </el-table-column>
          <el-table-column
            label="复核状态"
            width="100"
            align="center"
          >
            <template #default="{ row }">
              <el-tag
                size="small"
                :type="reviewTag(row.reviewStatus)"
              >
                {{ row.reviewStatus || '—' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column
            label="修正状态"
            width="100"
            align="center"
          >
            <template #default="{ row }">
              <span class="small">{{ row.revisionStatus || '—' }}</span>
            </template>
          </el-table-column>
          <el-table-column
            label="操作"
            width="72"
            fixed="right"
          >
            <template #default="{ row }">
              <el-button
                link
                type="primary"
                size="small"
                @click="openTaskDatasetItem(row)"
              >
                查看
              </el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-pagination
          v-model:current-page="taskDatasetPage"
          class="pager"
          layout="total, prev, pager, next"
          :total="taskDatasetTotal"
          :page-size="taskDatasetPageSize"
          @current-change="loadTaskDataset()"
        />
      </template>
      <div
        v-else
        class="empty-block"
      >
        任务尚未归集，完成质量治理后生成候选数据集版本。
      </div>
    </section>

    <section
      v-if="task"
      class="detail-card execution-card"
    >
      <div class="card-title-row">
        <div>
          <div class="detail-card-title">
            环节执行
          </div>
          <div class="detail-card-subtitle">
            记录算子尝试、样本进度、跳过与失败信息
          </div>
        </div>
        <el-switch
          v-model="showAllRuns"
          size="small"
          active-text="全部尝试"
        />
      </div>
      <el-table
        :data="displayedRuns"
        size="small"
        class="run-table"
      >
        <el-table-column
          label="环节"
          width="110"
        >
          <template #default="{ row }">
            <b>{{ row.stageNo }}. {{ row.stageName }}</b>
          </template>
        </el-table-column>
        <el-table-column
          prop="operatorTag"
          label="算子"
          width="160"
          show-overflow-tooltip
        />
        <el-table-column
          label="状态"
          width="76"
        >
          <template #default="{ row }">
            <el-tag
              :type="runTag(row.status)"
              size="small"
            >
              {{ runName(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column
          prop="attempt"
          label="尝试"
          width="52"
          align="center"
        />
        <el-table-column
          label="样本进度"
          min-width="190"
        >
          <template #default="{ row }">
            <div
              v-if="row.progress"
              class="progress-cell"
            >
              <el-progress
                :percentage="progressPercent(row.progress)"
                :stroke-width="6"
                :status="progressStatus(row.progress)"
              />
              <div class="progress-meta">
                {{ progressText(row.progress) }}
              </div>
            </div>
            <span
              v-else
              class="muted"
            >—</span>
          </template>
        </el-table-column>
        <el-table-column
          label="摘要"
          min-width="210"
        >
          <template #default="{ row }">
            <span
              v-if="row.summary"
              class="mono small"
            >{{ summaryText(row.summary) }}</span>
            <span
              v-else
              class="muted"
            >—</span>
          </template>
        </el-table-column>
        <el-table-column
          label="跳过/失败"
          width="105"
        >
          <template #default="{ row }">
            <el-tag
              v-if="row.skipped?.length"
              type="info"
              size="small"
            >
              跳过 {{ row.skipped.length }}
            </el-tag>
            <el-tooltip
              v-if="row.failed?.length"
              :content="runError(row)"
              placement="top"
            >
              <el-tag
                type="danger"
                size="small"
                style="margin-left: 4px"
              >
                失败 {{ row.failed.length }}
              </el-tag>
            </el-tooltip>
            <span
              v-if="!row.skipped?.length && !row.failed?.length"
              class="muted"
            >—</span>
          </template>
        </el-table-column>
        <el-table-column
          label="时间"
          width="170"
        >
          <template #default="{ row }">
            <span class="small">{{ fmt(row.startTime) }}<br>{{ fmt(row.endTime) }}</span>
          </template>
        </el-table-column>
        <el-table-column
          label="产物"
          width="64"
          fixed="right"
        >
          <template #default="{ row }">
            <el-button
              size="small"
              link
              type="primary"
              :disabled="row.status === 'running'"
              @click="openFiles(row)"
            >
              文件
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <el-dialog
      v-model="paramSnapshotVisible"
      class="tcs-dialog"
      title="参数快照（创建时锁定）"
      width="640px"
    >
      <el-table
        :data="task?.paramSnapshot || []"
        size="small"
      >
        <el-table-column
          prop="name"
          label="参数名"
          width="180"
        />
        <el-table-column
          label="取值"
          min-width="200"
        >
          <template #default="{ row }">
            <span class="mono">{{ typeof row.value === 'object' ? JSON.stringify(row.value) : row.value }}</span>
          </template>
        </el-table-column>
        <el-table-column
          prop="desc"
          label="说明"
          min-width="220"
        />
      </el-table>
    </el-dialog>

    <!-- 驳回重跑 -->
    <el-dialog
      v-model="rejectVisible"
      title="驳回重跑"
      width="440px"
    >
      <el-form label-width="90px">
        <el-form-item label="重跑起点">
          <el-select
            v-model="rejectStage"
            style="width: 100%"
          >
            <el-option
              v-for="(n, i) in stageNames"
              :key="i"
              :label="`第 ${i + 1} 环节 · ${n}`"
              :value="i + 1"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <div class="hint">
        从所选环节开始重跑，之前环节复用已有产物；进行中的复核单将作废。
      </div>
      <template #footer>
        <el-button @click="rejectVisible = false">
          取消
        </el-button>
        <el-button
          type="warning"
          @click="doReject"
        >
          确认驳回
        </el-button>
      </template>
    </el-dialog>

    <!-- 阈值调整 -->
    <el-dialog
      v-model="thresholdVisible"
      title="调整置信度阈值"
      width="400px"
    >
      <el-input-number
        v-model="thresholdValue"
        :min="0"
        :max="1"
        :step="0.01"
        :precision="2"
      />
      <div class="hint">
        已有复核结论后阈值锁定，不可再调整。
      </div>
      <template #footer>
        <el-button @click="thresholdVisible = false">
          取消
        </el-button>
        <el-button
          type="primary"
          @click="saveThreshold"
        >
          保存
        </el-button>
      </template>
    </el-dialog>

    <!-- 产物文件抽屉 -->
    <el-drawer
      v-model="filesVisible"
      :title="`产物文件 · 第 ${filesRun?.stageNo} 环节 ${filesRun?.operatorTag || ''}`"
      class="tcs-drawer"
    >
      <el-table
        v-loading="filesLoading"
        :data="files"
        size="small"
      >
        <el-table-column
          prop="name"
          label="文件"
          min-width="260"
          show-overflow-tooltip
        />
        <el-table-column
          label="大小"
          width="90"
        >
          <template #default="{ row }">
            {{ humanSize(row.size) }}
          </template>
        </el-table-column>
        <el-table-column
          label="操作"
          width="140"
        >
          <template #default="{ row }">
            <el-button
              link
              type="primary"
              size="small"
              @click="previewFile(row)"
            >
              预览
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-drawer>

    <!-- 文件预览 -->
    <el-dialog
      v-model="previewVisible"
      :title="previewName"
      width="70%"
      top="6vh"
    >
      <img
        v-if="previewKind === 'image'"
        :src="previewUrl"
        style="max-width: 100%"
      >
      <iframe
        v-else-if="previewKind === 'pdf'"
        :src="previewUrl"
        class="preview-frame"
      />
      <pre
        v-else
        class="preview-text"
      >{{ previewText }}</pre>
    </el-dialog>

    <!-- 数据集明细 -->
    <el-drawer
      v-model="dsVisible"
      title="数据集明细"
      class="tcs-drawer"
    >
      <div class="toolbar">
        <el-select
          v-model="dsFilter"
          placeholder="复核状态"
          clearable
          style="width: 150px"
          @change="loadDatasetItems(1)"
        >
          <el-option
            label="已确认(A)"
            value="已确认"
          />
          <el-option
            label="已修正(B)"
            value="已修正"
          />
          <el-option
            label="已剔除(C)"
            value="已剔除"
          />
        </el-select>
        <el-tag size="small">
          共 {{ dsTotal }} 条
        </el-tag>
      </div>
      <el-table
        :data="dsItems"
        size="small"
      >
        <el-table-column
          prop="itemKey"
          label="行标识"
          width="150"
          show-overflow-tooltip
        />
        <el-table-column
          label="复核状态"
          width="100"
        >
          <template #default="{ row }">
            <el-tag
              size="small"
              :type="reviewTag(row.reviewStatus)"
            >
              {{ row.reviewStatus || '—' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column
          label="置信度"
          width="80"
        >
          <template #default="{ row }">
            {{ row.confidence ?? '—' }}
          </template>
        </el-table-column>
        <el-table-column
          label="数据"
          min-width="320"
        >
          <template #default="{ row }">
            <span class="mono small">{{ compact(row.payload) }}</span>
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
              @click="openDsItem(row)"
            >
              查看
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination
        v-model:current-page="dsPage"
        class="pager"
        layout="total, prev, pager, next"
        :total="dsTotal"
        :page-size="10"
        @current-change="loadDatasetItems()"
      />
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
import PageHeader from '../components/PageHeader.vue'
import BizIdText from '../components/BizIdText.vue'
import DatasetItemViewer from '../components/DatasetItemViewer.vue'
import { computed, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  TASK_STATUS, PRIORITIES,
  taskDetail, taskSubmit, taskStart, taskReject, taskCollect, taskThreshold, taskDelete,
  artifactList, artifactBlob, datasetDetail, reviewAddFromDataset,
} from '../api'

const props = defineProps<{ taskRef: string }>()
const route = useRoute()
const router = useRouter()
const taskBizNo = String(props.taskRef || route.params.taskRef)

const task = ref<any>(null)
const stageNames = computed<string[]>(() => task.value?.stageNames || [])
const loading = ref(false)
const timer = ref<number>()

const rejectVisible = ref(false)
const rejectStage = ref(1)
const thresholdVisible = ref(false)
const thresholdValue = ref(0.8)
const paramSnapshotVisible = ref(false)
const showAllRuns = ref(false)

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

const taskDatasetItems = ref<any[]>([])
const taskDatasetTotal = ref(0)
const taskDatasetPage = ref(1)
const taskDatasetPageSize = 10
const taskDatasetFilter = ref('')
const taskDatasetThreshold = ref(0.8)
const taskDatasetLoading = ref(false)

const taskDatasetPageCount = computed(() =>
  Math.max(1, Math.ceil(taskDatasetTotal.value / taskDatasetPageSize)),
)
const activeTaskReviewOrder = computed(() => {
  const orders = task.value?.reviewOrders || []
  return orders.find((order: any) => order.status === 'pending' || order.status === 'doing') || null
})
const recognitionConfidenceLabel = computed(() => {
  if (task.value?.line === 'layout') return '框选置信度'
  if (task.value?.line === 'graphic') return 'OCR 置信度'
  if (task.value?.line === 'metadata') return '事实抽取置信度'
  return '识别置信度'
})
const semanticConfidenceLabel = computed(() => {
  if (task.value?.line === 'layout') return '判定置信度'
  if (task.value?.line === 'graphic') return '描述置信度'
  if (task.value?.line === 'metadata') return '元信息补全置信度'
  return '语义标注置信度'
})

const orderedRuns = computed(() =>
  [...(task.value?.stageRuns || [])].sort((a: any, b: any) => Number(a.id) - Number(b.id)),
)

const latestRuns = computed(() => {
  const seen = new Set<string>()
  const result: any[] = []
  for (let i = orderedRuns.value.length - 1; i >= 0; i--) {
    const run = orderedRuns.value[i]
    const key = `${run.stageNo}|${run.operatorTag}`
    if (!seen.has(key)) {
      seen.add(key)
      result.push(run)
    }
  }
  return result.sort(
    (a, b) => Number(a.stageNo) - Number(b.stageNo) || String(a.operatorTag).localeCompare(String(b.operatorTag)),
  )
})

const displayedRuns = computed(() =>
  showAllRuns.value ? [...orderedRuns.value].reverse() : latestRuns.value,
)

const latestError = computed(() => latestRuns.value.find((run) => run.status === 'error') || null)

const overallProgress = computed(() => {
  const names = task.value?.stageNames || []
  if (!names.length) return 0
  const done = names.filter((_: string, index: number) => stageState(index + 1) === 'done').length
  return Math.round((done / names.length) * 100)
})

const progressLabel = computed(() => {
  const status = task.value?.status
  if (status === 'processing') return '处理中'
  if (status === 'pending') return '待启动'
  if (status === 'draft') return '草稿'
  if (status === 'waitreview') return '待复核'
  if (status === 'quality') return '待归集'
  if (status === 'collected') return '已归集'
  return task.value?.statusName || '—'
})

function latestRunsForStage(stage: number) {
  return latestRuns.value.filter((run) => Number(run.stageNo) === stage)
}

function stageState(stage: number) {
  const status = task.value?.status
  if (status === 'quality' || status === 'collected') return 'done'
  const runs = latestRunsForStage(stage)
  if (runs.some((run) => run.status === 'error')) return 'error'
  if (runs.some((run) => run.status === 'running')) return 'running'
  if (runs.length > 0 && runs.every((run) => run.status === 'done')) return 'done'
  const current = Number(task.value?.currentStage || 0)
  if (status === 'processing' && current >= stage) return 'running'
  if (status === 'waitreview' && current >= stage) return 'done'
  return 'waiting'
}

function stageStateText(stage: number) {
  return ({ done: '完成', error: '失败', running: '执行中', waiting: '未执行' } as Record<string, string>)[
    stageState(stage)
  ]
}

function runError(run: any) {
  const failure = run?.failed?.[0]
  const message = failure?.error || failure?.reason || '算子执行失败'
  return String(message).slice(0, 500)
}

function goBack() {
  router.push((route.query.fromWb as string) || `/custom-text/wb/${task.value?.line || 'metadata'}`)
}

function openParamSnapshot() {
  paramSnapshotVisible.value = true
}

function lastDoneRun(tag?: string) {
  const done = (task.value?.stageRuns || []).filter(
    (r: any) => r.status === 'done' && (!tag || r.operatorTag === tag),
  )
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
  return Object.entries(summary)
    .slice(0, 6)
    .map(([k, v]) => `${k}=${typeof v === 'object' ? JSON.stringify(v) : v}`)
    .join('  ')
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

function openReview(orderBizNo: string) {
  router.push({ path: '/custom-text/review', query: { orderBizNo } })
}

function asNumber(value: any) {
  if (value == null || value === '') return null
  const number = Number(value)
  return Number.isNaN(number) ? null : number
}

function minValues(values: any[]) {
  const numbers = values.map(asNumber).filter((value): value is number => value != null)
  return numbers.length ? Math.min(...numbers) : null
}

function itemRecognitionConfidence(row: any) {
  const payload = row?.payload || {}
  if (task.value?.line === 'layout') {
    return (
      asNumber(payload.confidence?.bbox) ??
      minValues((payload.elements || []).map((element: any) => element.bboxConf))
    )
  }
  if (task.value?.line === 'graphic') {
    return asNumber(payload.confidence?.ocr) ?? asNumber(payload.confidence?.type)
  }
  if (task.value?.line === 'metadata') {
    return asNumber(payload.extractConfidence) ?? asNumber(payload.facts?.extractConfidence)
  }
  return (
    asNumber(payload.recognitionConfidence) ??
    asNumber(payload.confidence?.recognition) ??
    asNumber(payload.confidence)
  )
}

function itemSemanticConfidence(row: any) {
  const payload = row?.payload || {}
  if (task.value?.line === 'layout') {
    return (
      asNumber(payload.confidence?.type) ??
      minValues((payload.elements || []).map((element: any) => element.typeConf))
    )
  }
  if (task.value?.line === 'graphic') {
    return asNumber(payload.confidence?.desc) ?? asNumber(payload.confidence?.ocr)
  }
  if (task.value?.line === 'metadata') {
    return asNumber(payload.fillConfidence) ?? asNumber(payload.fields?.fillConfidence)
  }
  return asNumber(payload.semanticConfidence) ?? asNumber(payload.confidence?.semantic)
}

function formatConfidence(value: number | null) {
  return value == null || Number.isNaN(value) ? '—' : value.toFixed(2)
}

function confidenceClass(value: number | null) {
  if (value == null || Number.isNaN(value)) return 'muted'
  if (value < taskDatasetThreshold.value) return 'confidence-low'
  if (value < 0.8) return 'confidence-warning'
  return 'confidence-ok'
}

function itemLowConfidenceCount(row: any) {
  const threshold = Number(taskDatasetThreshold.value || 0.8)
  if (task.value?.line === 'layout') {
    const elements = row?.payload?.elements || []
    if (elements.length) {
      return elements.filter(
        (element: any) =>
          (asNumber(element.bboxConf) ?? 1) < threshold || (asNumber(element.typeConf) ?? 1) < threshold,
      ).length
    }
  }
  const values = [itemRecognitionConfidence(row), itemSemanticConfidence(row)].filter(
    (value): value is number => value != null && !Number.isNaN(value),
  )
  if (values.length) return values.filter((value) => value < threshold).length
  return Number(row?.payload?.lowConfidenceCount || 0)
}

function itemLowConfidenceReason(row: any) {
  const backendReason =
    row?.payload?.lowConfidenceReasons || row?.payload?.reviewReason || row?.payload?.reason
  if (backendReason) return backendReason
  const threshold = Number(taskDatasetThreshold.value || 0.8)
  const reasons: string[] = []
  if (task.value?.line === 'layout') {
    const elements = row?.payload?.elements || []
    const bboxLow = elements.some((element: any) => (asNumber(element.bboxConf) ?? 1) < threshold)
    const typeLow = elements.some((element: any) => (asNumber(element.typeConf) ?? 1) < threshold)
    if (bboxLow) reasons.push('框选置信度偏低')
    if (typeLow) reasons.push('判定置信度偏低')
  } else {
    const recognition = itemRecognitionConfidence(row)
    const semantic = itemSemanticConfidence(row)
    const recognitionLabel = task.value?.line === 'metadata' ? '事实抽取置信度偏低' : '识别置信度偏低'
    const semanticLabel = task.value?.line === 'metadata' ? '元信息补全置信度偏低' : '语义标注置信度偏低'
    if (recognition != null && recognition < threshold) reasons.push(recognitionLabel)
    if (semantic != null && semantic < threshold) reasons.push(semanticLabel)
  }
  return reasons.join('；') || (row?.reviewStatus === '待复核' ? '待复核' : '—')
}

function isLowConfidence(row: any) {
  return (
    itemLowConfidenceCount(row) > 0 ||
    row?.reviewStatus === '待复核' ||
    row?.payload?.reviewStatus === '待复核'
  )
}

function canAddToReview(row: any) {
  const status = row?.reviewStatus
  return isLowConfidence(row) && (!status || status === '未进入复核')
}

async function loadTaskDataset(page?: number) {
  const dataset = task.value?.datasets?.[0]
  if (!dataset?.bizNo) {
    taskDatasetItems.value = []
    taskDatasetTotal.value = 0
    return
  }
  if (page) taskDatasetPage.value = page
  taskDatasetLoading.value = true
  try {
    const d = await datasetDetail(dataset.bizNo, {
      reviewStatus: taskDatasetFilter.value || undefined,
      page: taskDatasetPage.value,
      limit: taskDatasetPageSize,
    })
    taskDatasetItems.value = d.items.rows
    taskDatasetTotal.value = Number(d.items.total)
  } finally {
    taskDatasetLoading.value = false
  }
}

function openTaskDatasetItem(row: any) {
  dsItems.value = taskDatasetItems.value
  dsTotal.value = taskDatasetTotal.value
  const index = taskDatasetItems.value.indexOf(row)
  dsItemIndex.value = index < 0 ? 0 : index
  dsItemVisible.value = true
}

async function addTaskDatasetToReview() {
  const candidates = taskDatasetItems.value.filter(canAddToReview)
  if (!candidates.length) {
    ElMessage.info('当前页没有需要新加入复核的条目')
    return
  }
  let added = 0
  for (const item of candidates) {
    try {
      await reviewAddFromDataset(String(item.id))
      added += 1
    } catch {
      // 已被加入复核或当前条目不可加入时继续处理其他条目
    }
  }
  if (added) ElMessage.success(`已加入复核 ${added} 条低置信条目`)
  else ElMessage.info('当前低置信条目已在复核任务中')
  await load()
  await loadTaskDataset()
}

async function load() {
  loading.value = true
  try {
    task.value = await taskDetail(taskBizNo)
    if (task.value?.datasets?.length) {
      if (!taskDatasetItems.value.length) taskDatasetThreshold.value = Number(task.value.threshold || 0.8)
      await loadTaskDataset()
    } else {
      taskDatasetItems.value = []
      taskDatasetTotal.value = 0
    }
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
    await taskDelete(taskBizNo)
    ElMessage.success('已删除')
    router.push((route.query.fromWb as string) || '/custom-text')
    return
  }
  if (kind === 'start') {
    await ElMessageBox.confirm('确认启动任务？将按算子链依次执行全部环节。', '启动确认', { type: 'warning' })
    await taskStart(taskBizNo)
    ElMessage.success('已启动')
  }
  if (kind === 'submit') {
    await taskSubmit(taskBizNo)
    ElMessage.success('已提交')
  }
  if (kind === 'collect') {
    await taskCollect(taskBizNo)
    ElMessage.success('已归集')
  }
  load()
}

function openReject(stageNo = 1) {
  rejectStage.value = Math.min(Math.max(Number(stageNo) || 1, 1), task.value?.stageNames?.length || 3)
  rejectVisible.value = true
}

async function doReject() {
  await taskReject(taskBizNo, rejectStage.value)
  ElMessage.success('已驳回，从所选环节重跑')
  rejectVisible.value = false
  load()
}

function openThreshold() {
  thresholdValue.value = Number(task.value.threshold)
  thresholdVisible.value = true
}

async function saveThreshold() {
  await taskThreshold(taskBizNo, thresholdValue.value)
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

async function openDataset(reference: string) {
  dsId.value = reference
  dsFilter.value = ''
  dsVisible.value = true
  loadDatasetItems(1)
}

async function loadDatasetItems(page?: number) {
  if (page) dsPage.value = page
  const d = await datasetDetail(dsId.value!, {
    reviewStatus: dsFilter.value || undefined,
    page: dsPage.value,
    limit: 10,
  })
  dsItems.value = d.items.rows
  dsTotal.value = d.items.total
}

load()
onUnmounted(() => {
  window.clearTimeout(timer.value)
  closePreview()
})
</script>

<style scoped>
.mono { font-family: var(--tcs-font-mono); }
.small { font-size: var(--tcs-font-size-helper); }
.muted { color: var(--tcs-color-text-secondary); }
.danger-text { color: var(--tcs-color-danger); }

.detail-card {
  padding: 16px;
  border: 1px solid var(--tcs-color-border);
  border-radius: 8px;
  background: var(--tcs-color-surface);
}
.card-title-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 12px;
}
.detail-card-title { color: #263b55; font-size: 15px; font-weight: 650; line-height: 1.4; }
.detail-card-subtitle { margin-top: 3px; color: var(--tcs-color-text-secondary); font-size: var(--tcs-font-size-helper); }
.progress-value { color: var(--tcs-color-primary); font-size: 13px; white-space: nowrap; }
.progress-line { height: 6px; overflow: hidden; border-radius: 99px; background: #eaf2fb; }
.progress-line i { display: block; height: 100%; border-radius: 99px; background: var(--tcs-color-primary); transition: width 240ms ease; }
.stage-chips { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; }
.stage-chip {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  min-height: 27px;
  padding: 3px 9px 3px 5px;
  border: 1px solid #d8e9fc;
  border-radius: 4px;
  background: #f6fbff;
  color: #4d79a6;
  font-size: var(--tcs-font-size-helper);
}
.stage-chip.done { border-color: #d9f7be; background: #e8f7ef; color: #128a57; }
.stage-chip.error { border-color: #fecaca; background: #fee4e2; color: #b42318; }
.stage-chip.running { border-color: #8fa3ff; background: #eef4ff; color: var(--tcs-color-primary); }
.stage-chip.waiting { color: #7c8ca1; }
.stage-chip-no {
  display: inline-grid;
  place-items: center;
  width: 19px;
  height: 19px;
  border-radius: 50%;
  background: #dcecff;
  color: #4474b8;
  font-size: 11px;
  font-weight: 700;
}
.stage-chip.done .stage-chip-no { background: #bcebd0; color: #128a57; }
.stage-chip.error .stage-chip-no { background: #ffd1cf; color: #b42318; }
.stage-chip.running .stage-chip-no { background: #dbe5ff; color: var(--tcs-color-primary); }
.stage-chip-status { opacity: 0.82; }
.error-callout {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
  margin-top: 14px;
  padding: 11px 14px;
  border: 1px solid #fecaca;
  border-radius: 5px;
  background: #fee4e2;
  color: #a8071a;
  font-size: 13px;
}
.error-callout .error-message { display: block; margin-top: 3px; line-height: 1.55; word-break: break-word; }
.error-callout .el-button { flex: none; }
.overview-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 16px 28px; }
.overview-item { min-width: 0; }
.overview-item label { display: block; margin-bottom: 4px; color: #8b98a9; font-size: var(--tcs-font-size-helper); }
.overview-item > span { display: block; color: #3d5b7d; line-height: 1.55; overflow-wrap: anywhere; }
.overview-muted { color: var(--tcs-color-text-secondary); font-size: var(--tcs-font-size-helper); }
.execution-card .run-table { margin-top: 4px; }
.dataset-toolbar { display: flex; align-items: flex-end; gap: 18px; margin: 2px 0 14px; flex-wrap: wrap; }
.dataset-filter { display: flex; flex-direction: column; gap: 5px; }
.dataset-filter label { color: var(--tcs-color-text-secondary); font-size: var(--tcs-font-size-helper); }
.dataset-toolbar-spacer { flex: 1; }
.dataset-table { margin-top: 2px; }
.confidence-low { color: #f04438; font-weight: 600; }
.confidence-warning { color: #f79009; font-weight: 600; }
.confidence-ok { color: #128a57; }

.progress-cell { min-width: 180px; }
.progress-meta { margin-top: 4px; color: var(--tcs-color-text-secondary); font-size: var(--tcs-font-size-helper); }
.empty-block { padding: 18px 12px; border: 1px dashed var(--tcs-color-border-strong); border-radius: 5px; color: var(--tcs-color-text-secondary); font-size: var(--tcs-font-size-helper); text-align: center; }
.toolbar { display: flex; gap: 10px; margin-bottom: 12px; }
.pager { margin-top: 12px; justify-content: flex-end; }
.preview-text { max-height: 62vh; overflow: auto; background: var(--tcs-color-bg-page); padding: 12px; font-size: var(--tcs-font-size-helper); line-height: 1.6; white-space: pre-wrap; word-break: break-all; }
.preview-frame { width: 100%; height: 70vh; border: 0; border-radius: var(--tcs-radius-control); background: #fff; }
.hint { font-size: var(--tcs-font-size-helper); color: var(--tcs-color-text-secondary); }
@media (max-width: 1100px) {
  .overview-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
</style>
