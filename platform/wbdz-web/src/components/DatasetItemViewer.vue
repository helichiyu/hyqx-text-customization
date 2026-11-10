<template>
  <el-drawer :model-value="modelValue" :title="title" class="wbdz-drawer" @update:model-value="emit('update:modelValue', $event)">
    <template v-if="item">
      <div class="viewer">
        <div class="pane left">
          <SourcePreview :item="item" :line="line" :run-id="runId" :image-run-id="imageRunId" />
        </div>

        <div class="pane right">
          <h4>系统识别结果</h4>

          <template v-if="line === 'metadata'">
            <div v-for="group in metadataGroups" :key="group.key" class="group">
              <h5>{{ group.name }}</h5>
              <el-table :data="group.rows" size="small" border>
                <el-table-column prop="field" label="字段" width="150" />
                <el-table-column label="值" min-width="240">
                  <template #default="{ row }">
                    <span v-if="row.value == null" class="muted">—</span>
                    <template v-else-if="Array.isArray(row.value)">
                      <el-tag v-for="(v, i) in row.value" :key="i" size="small" class="chip">{{ v }}</el-tag>
                    </template>
                    <span v-else>{{ row.value }}</span>
                  </template>
                </el-table-column>
                <el-table-column label="置信度" width="90" align="center">
                  <template #default="{ row }">
                    <el-tag v-if="row.confidence != null" size="small" :type="confTag(row.confidence)">
                      {{ row.confidence }}
                    </el-tag>
                    <span v-else class="muted">—</span>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </template>

          <template v-else-if="line === 'layout'">
            <el-descriptions :column="3" border size="small">
              <el-descriptions-item label="页码">{{ payload.pageNo ?? '—' }}</el-descriptions-item>
              <el-descriptions-item label="元素数">{{ payload.elements?.length || 0 }}</el-descriptions-item>
              <el-descriptions-item label="低置信项">{{ payload.lowConfidenceCount ?? '—' }}</el-descriptions-item>
            </el-descriptions>
            <p v-if="payload.lowConfidenceReasons" class="hint">低置信原因：{{ payload.lowConfidenceReasons }}</p>
            <el-table :data="payload.elements || []" size="small" border max-height="440" style="margin-top: 10px">
              <el-table-column prop="readingOrder" label="顺序" width="60" align="center" />
              <el-table-column prop="type" label="类型" width="90" />
              <el-table-column prop="elementId" label="元素" width="100" />
              <el-table-column label="bbox" min-width="150">
                <template #default="{ row }">{{ (row.bbox || []).join(', ') }}</template>
              </el-table-column>
              <el-table-column prop="bboxConf" label="框选" width="80" align="center" />
              <el-table-column prop="typeConf" label="判定" width="80" align="center" />
            </el-table>
          </template>

          <template v-else-if="line === 'formula'">
            <div class="latex-box">{{ payload.latex || '—' }}</div>
            <el-table :data="payload.symbols || []" size="small" border style="margin-top: 10px">
              <el-table-column prop="symbol" label="符号" width="110" />
              <el-table-column prop="meaning" label="含义" min-width="180" />
              <el-table-column prop="unit" label="单位" width="100" />
            </el-table>
            <el-descriptions :column="1" border size="small" style="margin-top: 10px">
              <el-descriptions-item label="章节">{{ payload.context?.chapter || '—' }}</el-descriptions-item>
              <el-descriptions-item label="编号">{{ payload.context?.number || '—' }}</el-descriptions-item>
              <el-descriptions-item label="上下文">{{ payload.context?.definition || '—' }}</el-descriptions-item>
            </el-descriptions>
          </template>

          <template v-else-if="line === 'graphic'">
            <el-table :data="graphicRows" size="small" border>
              <el-table-column prop="field" label="描述字段" width="160" />
              <el-table-column prop="value" label="内容" min-width="280" />
            </el-table>
            <el-descriptions :column="3" border size="small" style="margin-top: 10px">
              <el-descriptions-item label="判型置信度">{{ payload.confidence?.type ?? '—' }}</el-descriptions-item>
              <el-descriptions-item label="OCR 置信度">{{ payload.confidence?.ocr ?? '—' }}</el-descriptions-item>
              <el-descriptions-item label="描述置信度">{{ payload.confidence?.desc ?? '—' }}</el-descriptions-item>
            </el-descriptions>
            <p v-if="payload.lowConfidenceReasons" class="hint">低置信原因：{{ payload.lowConfidenceReasons }}</p>
          </template>

          <el-descriptions v-if="line === 'metadata'" :column="3" border size="small" style="margin-top: 12px">
            <el-descriptions-item label="事实抽取置信度">{{ payload.extractConfidence ?? '—' }}</el-descriptions-item>
            <el-descriptions-item label="元信息补全置信度">{{ payload.fillConfidence ?? '—' }}</el-descriptions-item>
            <el-descriptions-item label="复核状态">{{ item.reviewStatus || '—' }}</el-descriptions-item>
          </el-descriptions>
          <el-descriptions v-else-if="line !== 'graphic'" :column="3" border size="small" style="margin-top: 12px">
            <el-descriptions-item label="条目置信度">{{ item.confidence ?? '—' }}</el-descriptions-item>
            <el-descriptions-item label="复核状态">{{ item.reviewStatus || '—' }}</el-descriptions-item>
            <el-descriptions-item label="修正状态">{{ item.revisionStatus || '—' }}</el-descriptions-item>
          </el-descriptions>
        </div>
      </div>
    </template>

    <template #footer>
      <el-button
        v-if="canAdd || inReview"
        type="primary"
        plain
        :disabled="inReview || !canAdd"
        @click="emit('add')"
      >
        {{ inReview ? '已在复核任务中' : '加入复核任务' }}
      </el-button>
      <span style="flex: 1" />
      <el-button :disabled="!canPrev" @click="emit('prev')">上一条</el-button>
      <el-button :disabled="!canNext" @click="emit('next')">下一条</el-button>
      <el-button @click="emit('update:modelValue', false)">关闭</el-button>
    </template>
  </el-drawer>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import SourcePreview from '@/components/SourcePreview.vue'

const props = defineProps<{
  modelValue: boolean
  item: any
  line: string
  runId?: string | null
  imageRunId?: string | null
  canPrev?: boolean
  canNext?: boolean
  canAdd?: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void
  (e: 'prev'): void
  (e: 'next'): void
  (e: 'add'): void
}>()

const inReview = computed(() => {
  const s = props.item?.reviewStatus
  return !!s && s !== '未进入复核'
})

const payload = computed<any>(() => props.item?.payload || {})
const title = computed(() => {
  const key = props.item?.itemKey ? ` · ${props.item.itemKey}` : ''
  return `数据集明细查看${key}`
})


function confTag(v: number) {
  if (v >= 0.8) return 'success'
  if (v >= 0.6) return 'warning'
  return 'danger'
}

const GROUP_NAMES: Record<string, string> = {
  basic: '基础信息',
  related: '关联信息',
  structured: '结构化信息',
}

const metadataGroups = computed(() => {
  const groups = payload.value.fields || payload.value || {}
  return Object.keys(GROUP_NAMES)
    .filter((key) => groups[key] && typeof groups[key] === 'object')
    .map((key) => ({
      key,
      name: GROUP_NAMES[key],
      rows: Object.entries(groups[key]).map(([field, raw]: [string, any]) => ({
        field,
        value: raw && typeof raw === 'object' && 'value' in raw ? raw.value : raw,
        confidence: raw && typeof raw === 'object' ? raw.confidence : undefined,
      })),
    }))
})

const graphicRows = computed(() =>
  Object.entries(payload.value.description || {}).map(([field, value]) => ({
    field,
    value: Array.isArray(value) ? value.join('；') : String(value ?? '—'),
  })),
)
</script>

<style scoped>
.viewer {
  display: grid;
  grid-template-columns: minmax(280px, 1fr) minmax(320px, 1.2fr);
  gap: 20px;
}
.pane h4 {
  margin: 0 0 10px;
}
.pane h5 {
  margin: 14px 0 6px;
}
.left {
  border-right: 1px solid var(--el-border-color-lighter);
  padding-right: 18px;
}
.hint {
  color: var(--el-text-color-secondary);
  font-size: var(--wbdz-font-caption);
  margin-top: 8px;
}
.muted {
  color: var(--el-text-color-placeholder);
}
.chip {
  margin: 2px 4px 2px 0;
}
</style>
