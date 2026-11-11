<template>
  <div class="custom-text-app">
    <header class="topbar">
      <button
        class="brand"
        type="button"
        @click="go('/custom-text/wb/formula')"
      >
        文
      </button>
      <button
        class="module-name"
        type="button"
        @click="go('/custom-text/wb/formula')"
      >
        文本定制化生产
      </button>
      <div class="crumb">
        {{ breadcrumbText }}
      </div>
      <div class="user">
        {{ userName }}
        <span class="avatar">{{ avatarChar }}</span>
      </div>
    </header>

    <div class="shell">
      <aside class="sidebar">
        <div class="nav-group">
          产线工作台
        </div>
        <button
          v-for="(name, line) in LINE_NAMES"
          :key="line"
          type="button"
          class="nav"
          :class="{ active: activePath === `/custom-text/wb/${line}` }"
          @click="go(`/custom-text/wb/${line}`)"
        >
          <span
            class="nav-dot"
            :style="{ background: LINE_COLORS[line] }"
          />
          {{ name }}
        </button>

        <div class="nav-group">
          公共管理
        </div>
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
        <nav
          class="tabs-bar"
          aria-label="已打开页面"
        >
          <button
            v-for="tab in tabs.tabs"
            :key="tab.key"
            type="button"
            class="page-tab"
            :class="{ active: tabs.activeKey === tab.key }"
            @click="go(tab.path)"
          >
            <span>{{ tab.title }}</span>
            <span
              v-if="tab.key !== homeKey"
              class="page-tab__close"
              @click.stop="closeTab(tab.key)"
            >×</span>
          </button>
        </nav>

        <main class="content">
          <router-view v-slot="{ Component }">
            <keep-alive>
              <component
                :is="Component"
                :key="route.fullPath"
              />
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
import { useAuthStore } from '@/core/auth'
import { LINE_NAMES } from '../api'
import { useTabsStore } from '../stores/tabs'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const tabs = useTabsStore()

const homeKey = 'custom-text-wb-metadata'
const LINE_COLORS: Record<string, string> = {
  formula: '#722ed1',
  layout: '#08979c',
  graphic: '#b45309',
  metadata: '#c41d7f',
}
const commonNav = [
  { path: '/custom-text/material', name: '素材管理' },
  { path: '/custom-text/review', name: '条件复核' },
  { path: '/custom-text/dataset', name: '数据集管理' },
  { path: '/custom-text/params', name: '参数配置' },
]

const userName = computed(() => auth.currentUser?.name || '用户')
const avatarChar = computed(() => userName.value.slice(0, 1))

const activePath = computed(() => {
  if (route.path.startsWith('/custom-text/wb/')) return route.path
  if (route.path.startsWith('/custom-text/task/')) {
    return String(route.query.fromWb || route.meta.fromWb || '/custom-text/wb/metadata')
  }
  return route.path
})

const currentTitle = computed(() => (route.meta.title as string) || '')
const breadcrumbText = computed(() => {
  if (route.path.startsWith('/custom-text/wb/')) {
    const code = route.path.slice('/custom-text/wb/'.length)
    return `主页 / 产线工作台 / ${LINE_NAMES[code] || '工作台'}`
  }
  if (route.path.startsWith('/custom-text/task/')) return '主页 / 产线工作台 / 任务详情'
  return `主页 / ${currentTitle.value || '文本定制化生产'}`
})

function titleFor(path: string): string {
  if (path.startsWith('/custom-text/wb/')) {
    return (LINE_NAMES[path.slice('/custom-text/wb/'.length)] || '工作台') + '工作台'
  }
  if (path.startsWith('/custom-text/task/')) return '任务详情'
  return (
    {
      '/custom-text/material': '素材管理',
      '/custom-text/review': '条件复核',
      '/custom-text/dataset': '数据集管理',
      '/custom-text/params': '参数配置',
    } as Record<string, string>
  )[path] || ''
}

watch(
  () => route.path,
  (path) => {
    const key = path.startsWith('/custom-text/task/')
      ? path
      : path.replace('/custom-text/', '') === 'wb/metadata'
        ? homeKey
        : path
    tabs.open({ key, title: titleFor(path), path })
  },
  { immediate: true },
)

function go(path: string) {
  router.push(path)
}

function closeTab(key: string) {
  const fallback = { key: homeKey, title: '文本元信息工作台', path: '/custom-text/wb/metadata' }
  const next = tabs.close(key, fallback)
  if (next) router.push(next)
}
</script>

<style scoped>
.custom-text-app {
  display: flex;
  flex-direction: column;
  height: 100vh;
  min-width: 1180px;
  background: var(--tcs-color-bg-page);
  color: var(--tcs-color-text);
  font-family: var(--tcs-font-family);
  font-size: var(--tcs-font-size-body);
}
.topbar {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  height: 56px;
  border-bottom: 1px solid var(--tcs-color-border);
  background: linear-gradient(90deg, rgba(230, 220, 255, 0.55), rgba(220, 235, 255, 0.65) 50%, rgba(240, 245, 255, 0.7));
}
.brand {
  width: 32px;
  height: 32px;
  margin-left: 24px;
  border: 0;
  border-radius: 8px;
  background: var(--tcs-color-primary);
  color: #fff;
  font-size: 16px;
  font-weight: 700;
  cursor: pointer;
}
.module-name {
  margin-left: 12px;
  border: 0;
  background: transparent;
  color: var(--tcs-color-title);
  font-family: var(--tcs-font-family);
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
}
.crumb { margin-left: 28px; color: var(--tcs-color-text-secondary); font-size: 14px; }
.user {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-right: 24px;
  margin-left: auto;
  color: var(--tcs-color-text);
  font-size: 14px;
}
.avatar {
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--tcs-color-success);
  color: #fff;
  font-size: 12px;
}
.shell { display: flex; flex: 1; min-height: 0; }
.sidebar {
  width: 220px;
  flex: 0 0 auto;
  padding: 10px 0;
  overflow: auto;
  background: #fff;
  border-right: 1px solid var(--tcs-color-border);
}
.nav-group { padding: 8px 16px 6px; color: var(--tcs-color-text-weak); font-size: 12px; line-height: 32px; }
.nav {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  height: 44px;
  padding: 0 16px;
  border: 0;
  border-left: 3px solid transparent;
  background: transparent;
  color: var(--tcs-color-text);
  font-family: var(--tcs-font-family);
  font-size: 14px;
  text-align: left;
  cursor: pointer;
}
.nav:hover { background: var(--tcs-color-table-head); }
.nav.active { padding-left: 13px; border-left-color: var(--tcs-color-primary); color: var(--tcs-color-primary); font-weight: 500; }
.nav-dot { width: 8px; height: 8px; flex: 0 0 auto; border-radius: 50%; }
.main { display: flex; flex: 1; flex-direction: column; min-width: 0; }
.tabs-bar {
  display: flex;
  flex: 0 0 auto;
  align-items: flex-end;
  gap: 4px;
  height: 40px;
  padding: 0 16px;
  overflow: auto;
  background: #fff;
  border-bottom: 1px solid var(--tcs-color-border);
}
.page-tab {
  display: flex;
  flex: none;
  align-items: center;
  gap: 8px;
  height: 40px;
  padding: 0 12px;
  border: 0;
  border-top: 2px solid transparent;
  background: transparent;
  color: var(--tcs-color-text);
  font-family: var(--tcs-font-family);
  font-size: 14px;
  white-space: nowrap;
  cursor: pointer;
}
.page-tab:hover { color: var(--tcs-color-primary); }
.page-tab.active { border-top-color: var(--tcs-color-primary); color: var(--tcs-color-primary); font-weight: 600; }
.page-tab__close {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  color: var(--tcs-color-text-secondary);
  font-size: 16px;
  line-height: 1;
}
.page-tab__close:hover { color: var(--tcs-color-danger); background: var(--tcs-color-danger-soft); }
.content { flex: 1; padding: 16px 20px 32px; overflow: auto; }
</style>
