<template>
  <section class="source-preview">
    <div class="source-title">
      来源内容
    </div>

    <el-descriptions
      :column="2"
      border
      size="small"
      class="source-meta"
    >
      <el-descriptions-item label="条目">
        {{ payload.docId || payload.pageId || payload.imageId || payload.instanceId || item.itemKey || '—' }}
      </el-descriptions-item>
      <el-descriptions-item label="文件">
        {{ payload.fileName || '—' }}
      </el-descriptions-item>
    </el-descriptions>

    <div
      v-if="imageUrl"
      class="source-image"
    >
      <img
        :src="imageUrl"
        alt="来源预览"
      >
    </div>

    <template v-if="line === 'metadata'">
      <pre
        v-if="sourceText"
        class="source-text"
      >{{ sourceText }}</pre>
      <el-empty
        v-else
        description="数据集明细仅保留结构化元信息，未携带原始正文片段"
        :image-size="56"
      />
    </template>

    <template v-else-if="line === 'formula'">
      <div class="latex-box">
        {{ payload.latex || '—' }}
      </div>
      <p
        v-if="payload.context?.definition"
        class="source-context"
      >
        {{ payload.context.definition }}
      </p>
      <p
        v-if="!imageUrl"
        class="source-hint"
      >
        当前复核载荷未携带裁切图路径，已展示 LaTeX 与上下文。
      </p>
    </template>

    <template v-else-if="line === 'graphic'">
      <p
        v-if="!imageUrl"
        class="source-hint"
      >
        当前复核载荷未携带原图路径，已展示条目和结构化信息。
      </p>
    </template>

    <template v-else>
      <p class="source-context">
        第 {{ payload.pageNo ?? '—' }} 页
        <span v-if="payload.bbox"> · bbox {{ (payload.bbox || []).join(', ') }}</span>
      </p>
      <p
        v-if="!imageUrl"
        class="source-hint"
      >
        未找到可用的版面页图或框选图层。
      </p>
    </template>
  </section>
</template>

<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from 'vue'
import { artifactBlob } from '../api'

const props = defineProps<{
  item: any
  line: string
  runId?: string | number | null
  imageRunId?: string | number | null
}>()

const payload = computed<any>(() => props.item?.payload || {})
const imageUrl = ref('')
let lastUrl = ''

const sourceText = computed(() => {
  const direct = payload.value.text || payload.value.content || payload.value.originalText
  if (direct) return String(direct)
  const slices = payload.value.slices
  if (Array.isArray(slices)) {
    return slices.map((s: any) => s?.text || '').filter(Boolean).join('\n')
  }
  return ''
})

function release() {
  if (lastUrl) URL.revokeObjectURL(lastUrl)
  lastUrl = ''
  imageUrl.value = ''
}

watch(
  () => [props.item, props.line, props.runId, props.imageRunId],
  async () => {
    release()
    let candidates: { name: string; runId?: string | number | null }[] = []
    if (props.line === 'layout') {
      candidates = [
        { name: payload.value.overlay, runId: props.runId },
        { name: payload.value.image || payload.value.pageImage, runId: props.imageRunId || props.runId },
      ]
    } else if (props.line === 'formula') {
      candidates = [
        { name: payload.value.crop, runId: props.runId },
        { name: payload.value.image, runId: props.runId },
      ]
    } else if (props.line === 'graphic') {
      candidates = [
        { name: payload.value.image || payload.value.originalImage, runId: props.runId },
        { name: payload.value.crop, runId: props.runId },
      ]
    }
    for (const candidate of candidates) {
      const name = String(candidate.name || '').replace(/\\/g, '/')
      if (!name || !candidate.runId) continue
      try {
        const blob = await artifactBlob(candidate.runId, name)
        lastUrl = URL.createObjectURL(blob)
        imageUrl.value = lastUrl
        return
      } catch {
        // 尝试下一个候选路径
      }
    }
  },
  { immediate: true },
)

onUnmounted(release)
</script>

<style scoped>
.source-preview { min-width: 0; }
.source-title, .payload-title { margin-bottom: 8px; color: var(--tcs-color-title); font-size: var(--tcs-font-size-card-title); font-weight: 600; }
.source-meta { margin-bottom: 10px; }
.source-image { display: flex; justify-content: center; margin: 10px 0; padding: 10px; border: 1px solid var(--tcs-color-border); border-radius: var(--tcs-radius-card); background: #fff; }
.source-image img { max-width: 100%; max-height: 360px; object-fit: contain; }
.source-text, .latex-box { margin: 0; padding: 12px; border: 1px solid var(--tcs-color-border); border-radius: var(--tcs-radius-control); background: var(--tcs-color-bg-page); color: var(--tcs-color-text); font-family: var(--tcs-font-mono); font-size: var(--tcs-font-size-helper); line-height: 1.7; white-space: pre-wrap; word-break: break-word; }
.source-context { margin: 10px 0 0; color: var(--tcs-color-text); line-height: 1.65; }
.source-hint { margin: 10px 0 0; color: var(--tcs-color-text-secondary); font-size: var(--tcs-font-size-helper); line-height: 1.6; }
</style>
