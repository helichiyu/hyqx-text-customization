<template>
  <span class="biz-id-wrap">
    <span class="biz-id" :title="displayValue">{{ displayValue }}</span>
    <el-button v-if="canCopy" link type="primary" size="small" @click="copyValue">复制</el-button>
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { ElMessage } from 'element-plus'

const props = withDefaults(defineProps<{
  value?: string | number | null
  copyable?: boolean
}>(), { copyable: true })

const displayValue = computed(() => {
  if (props.value === null || props.value === undefined || props.value === '') return '—'
  return String(props.value)
})

const canCopy = computed(() => props.copyable && displayValue.value !== '—')

async function copyValue() {
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(displayValue.value)
    } else {
      const textarea = document.createElement('textarea')
      textarea.value = displayValue.value
      textarea.style.position = 'fixed'
      textarea.style.opacity = '0'
      document.body.appendChild(textarea)
      textarea.select()
      document.execCommand('copy')
      textarea.remove()
    }
    ElMessage.success('编号已复制')
  } catch {
    ElMessage.error('复制失败，请手动选择编号')
  }
}
</script>
