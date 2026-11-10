<script setup lang="ts">
import { ref } from 'vue'

import { health } from '../api'

type HealthStatus = 'idle' | 'ok' | 'fail'

const status = ref<HealthStatus>('idle')

async function checkHealth() {
  try {
    await health()
    status.value = 'ok'
  } catch {
    status.value = 'fail'
  }
}
</script>

<template>
  <section class="module-banner">
    <h1>文本定制化生产</h1>
    <p>HSMTY 2.0.1 架构骨架已就绪，业务页面将在迁移阶段接入。</p>
    <div class="actions">
      <el-button
        type="primary"
        @click="checkHealth"
      >
        检查后端
      </el-button>
      <span class="status">状态：{{ status }}</span>
    </div>
  </section>
</template>

<style scoped>
.module-banner {
  padding: 24px;
  margin: 24px;
  background: var(--tcs-color-surface);
  border: 1px solid var(--tcs-color-border);
  border-radius: var(--tcs-radius-card);
}

.module-banner h1 {
  margin: 0 0 8px;
  color: var(--tcs-color-title);
  font-size: var(--tcs-font-size-banner);
  font-weight: 600;
}

.module-banner p {
  margin: 0 0 16px;
  color: var(--tcs-color-text-secondary);
}

.actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.status {
  color: var(--tcs-color-text-weak);
  font-size: var(--tcs-font-size-helper);
}
</style>
