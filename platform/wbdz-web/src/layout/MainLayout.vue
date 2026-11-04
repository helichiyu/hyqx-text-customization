<template>
  <div class="app">
    <header class="topbar">
      <button class="brand" type="button" @click="go('/wb/formula')">文</button>
      <div class="top-nav">
        <span class="top-pill active">产品中心</span>
        <span class="top-pill">领航者视图</span>
      </div>
      <button class="system-name" type="button" @click="go('/wb/formula')">文本定制化生产</button>
      <div class="crumb">{{ breadcrumbText }}</div>
      <span class="settings">设置</span>
      <div class="user">
        {{ auth.nickname || auth.username }}
        <span class="avatar">{{ avatarChar }}</span>
      </div>
    </header>

    <div class="shell">
      <aside class="sidebar">
        <div class="nav-group">产线工作台</div>
        <button
          v-for="(name, line) in LINE_NAMES"
          :key="line"
          type="button"
          class="nav"
          :class="{ active: activePath === `/wb/${line}` }"
          @click="go(`/wb/${line}`)"
        >
          <span class="nav-dot" :style="{ background: LINE_COLORS[line] }" />
          {{ name }}
        </button>

        <div class="nav-group">公共管理</div>
        <button
          v-for="item in commonNav"
          :key="item.path"
          type="button"
          class="nav"
          :class="{ active: activePath === item.path }"
          @click="go(item.path)"
        >
          {{ item.name }}
        </button>
      </aside>

      <section class="main">
        <nav class="tabs-bar" aria-label="已打开页面">
          <button
            v-for="t in tabs.tabs"
            :key="t.key"
            type="button"
            class="page-tab"
            :class="{ active: tabs.activeKey === t.key }"
            @click="go(t.path)"
          >
            <span>{{ t.title }}</span>
            <span v-if="t.key !== homeKey" class="page-tab__close" @click.stop="closeTab(t.key)">×</span>
          </button>
        </nav>

        <main class="content">
          <router-view v-slot="{ Component }">
            <keep-alive>
              <component :is="Component" :key="route.fullPath" />
            </keep-alive>
          </router-view>
        </main>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useTabsStore } from '@/stores/tabs'
import { LINE_NAMES } from '@/api'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const tabs = useTabsStore()

const homeKey = 'wb-metadata'
const LINE_COLORS: Record<string, string> = {
  formula: '#722ed1',
  layout: '#08979c',
  graphic: '#b45309',
  metadata: '#c41d7f',
}
const commonNav = [
  { path: '/material', name: '素材管理' },
  { path: '/review', name: '条件复核' },
  { path: '/dataset', name: '数据集管理' },
  { path: '/params', name: '参数配置' },
]

const activePath = computed(() => {
  if (route.path.startsWith('/wb/')) return route.path
  if (route.path.startsWith('/task/')) return String(route.query.fromWb || route.meta.fromWb || '/wb/metadata')
  return route.path
})

const currentTitle = computed(() => (route.meta.title as string) || '')
const avatarChar = computed(() => (auth.nickname || auth.username || '用').slice(0, 1))
const breadcrumbText = computed(() => {
  if (route.path.startsWith('/wb/')) {
    const code = route.path.slice(4)
    return `主页 / 产线工作台 / ${LINE_NAMES[code] || '工作台'}`
  }
  if (route.path.startsWith('/task/')) return '主页 / 产线工作台 / 任务详情'
  return `主页 / ${currentTitle.value || '文本定制化生产'}`
})

function titleFor(path: string): string {
  if (path.startsWith('/wb/')) {
    return (LINE_NAMES[path.slice(4)] || '工作台') + '工作台'
  }
  if (path.startsWith('/task/')) return '任务详情'
  return ({ '/material': '素材管理', '/review': '条件复核', '/dataset': '数据集管理', '/params': '参数配置' } as Record<string, string>)[path] || ''
}

watch(
  () => route.path,
  (path) => {
    if (path === '/login') return
    const key = path.startsWith('/task/') ? path : path
    tabs.open({ key, title: titleFor(path), path })
  },
  { immediate: true },
)

function go(path: string) {
  router.push(path)
}

function closeTab(key: string) {
  const fallback = { key: homeKey, title: '文本元信息工作台', path: '/wb/metadata' }
  const next = tabs.close(key, fallback)
  if (next) router.push(next)
}

function logout() {
  auth.logout()
  router.push('/login')
}
</script>

<style scoped>
.app { height: 100vh; display: flex; flex-direction: column; }
.topbar { height: 56px; flex: 0 0 auto; display: flex; align-items: center; border-bottom: 1px solid var(--wbdz-border); background: linear-gradient(90deg, rgba(230, 220, 255, .55), rgba(220, 235, 255, .65) 50%, rgba(240, 245, 255, .7)); }
.brand { width: 32px; height: 32px; margin-left: 24px; border: 0; border-radius: 8px; background: var(--wbdz-primary); color: #fff; font-size: 16px; font-weight: 700; cursor: pointer; }
.top-nav { display: flex; gap: 8px; margin-left: 28px; }
.top-pill { padding: 4px 14px; border-radius: 999px; color: var(--wbdz-text); font-size: 13px; cursor: pointer; }
.top-pill.active { background: var(--wbdz-title); color: #fff; }
.system-name { margin-left: 10px; border: 0; background: transparent; color: var(--wbdz-title); font-family: var(--wbdz-font-family); font-size: 16px; font-weight: 600; cursor: pointer; }
.crumb { margin-left: 28px; color: var(--wbdz-secondary); font-size: 14px; }
.settings { margin-left: auto; margin-right: 16px; color: var(--wbdz-text); font-size: 14px; cursor: pointer; }
.user { display: flex; align-items: center; gap: 8px; margin-right: 24px; color: var(--wbdz-text); font-size: 14px; }
.avatar { width: 28px; height: 28px; border-radius: 50%; display: grid; place-items: center; background: var(--wbdz-success); color: #fff; font-size: 12px; }
.shell { min-height: 0; display: flex; flex: 1; }
.sidebar { width: 220px; flex: 0 0 auto; padding: 10px 0; overflow: auto; background: #fff; border-right: 1px solid var(--wbdz-border); }
.nav-group { padding: 8px 16px 6px; color: var(--wbdz-weaker); font-size: 12px; line-height: 32px; }
.nav { width: 100%; height: 44px; padding: 0 16px; display: flex; align-items: center; gap: 10px; border: 0; border-left: 3px solid transparent; background: transparent; color: var(--wbdz-text); font-family: var(--wbdz-font-family); font-size: 14px; text-align: left; cursor: pointer; }
.nav:hover { background: var(--wbdz-table-header); }
.nav.active { padding-left: 13px; border-left-color: var(--wbdz-primary); color: var(--wbdz-primary); font-weight: 500; }
.nav-dot { width: 8px; height: 8px; flex: 0 0 auto; border-radius: 50%; }
.main { min-width: 0; flex: 1; display: flex; flex-direction: column; }
.tabs-bar { height: 40px; flex: 0 0 auto; display: flex; align-items: flex-end; gap: 4px; padding: 0 16px; overflow: auto; background: #fff; border-bottom: 1px solid var(--wbdz-border); }
.page-tab { height: 40px; padding: 0 12px; display: flex; flex: none; align-items: center; gap: 8px; border: 0; border-top: 2px solid transparent; background: transparent; color: var(--wbdz-text); font-family: var(--wbdz-font-family); font-size: 14px; white-space: nowrap; cursor: pointer; }
.page-tab:hover { color: var(--wbdz-primary); }
.page-tab.active { border-top-color: var(--wbdz-primary); color: var(--wbdz-primary); font-weight: 600; }
.page-tab__close { width: 16px; height: 16px; display: inline-flex; align-items: center; justify-content: center; border-radius: 50%; color: var(--wbdz-secondary); font-size: 16px; line-height: 1; }
.page-tab__close:hover { color: var(--wbdz-danger); background: var(--wbdz-danger-light); }
.content { flex: 1; padding: 16px 20px 32px; overflow: auto; }
</style>