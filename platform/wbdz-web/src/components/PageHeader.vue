<template>
  <section class="page-header">
    <div class="page-header__main">
      <div v-if="eyebrow" class="page-header__eyebrow">{{ eyebrow }}</div>
      <h1 class="page-header__title">{{ title }}</h1>
      <p v-if="description || $slots.description" class="page-header__description">
        <slot name="description">{{ description }}</slot>
      </p>
    </div>
    <div v-if="$slots.actions" class="page-header__actions">
      <slot name="actions" />
    </div>
  </section>
</template>

<script setup lang="ts">
defineProps<{
  title: string
  description?: string
  eyebrow?: string
}>()
</script>

<style scoped>
.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
  padding: 0;
  border: 0;
  background: transparent;
}
.page-header__main { min-width: 0; }
.page-header__eyebrow { margin-bottom: 5px; color: var(--wbdz-primary); font-size: var(--wbdz-font-caption); font-weight: 600; letter-spacing: 0.04em; }
.page-header__title { margin: 0; color: var(--wbdz-title); font-size: var(--wbdz-font-banner); font-weight: 600; line-height: 28px; }
.page-header__description { margin: 4px 0 0; color: var(--wbdz-secondary); font-size: var(--wbdz-font-body); line-height: 1.6; }
.page-header__actions { display: flex; flex: none; flex-wrap: wrap; align-items: center; justify-content: flex-end; gap: 8px; }
@media (max-width: 760px) {
  .page-header { flex-direction: column; }
  .page-header__actions { width: 100%; justify-content: flex-end; }
}
</style>