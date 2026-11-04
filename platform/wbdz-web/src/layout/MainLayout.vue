<template>
  <el-container class="layout">
    <el-aside width="216px" class="aside">
      <div class="brand">文本定制化生产平台</div>
      <el-menu :default-active="activePath" router class="menu">
        <div class="menu-group">产线工作台</div>
        <el-menu-item v-for="(name, line) in LINE_NAMES" :key="line" :index="`/wb/${line}`">
          <span>{{ name }}</span>
        </el-menu-item>
        <div class="menu-group">公共管理</div>
        <el-menu-item index="/material">素材管理</el-menu-item>
        <el-menu-item index="/review">条件复核</el-menu-item>
        <el-menu-item index="/dataset">数据集管理</el-menu-item>
        <el-menu-item index="/params">参数配置</el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="header">
        <el-breadcrumb separator="/">
          <el-breadcrumb-item>文本定制化生产</el-breadcrumb-item>
          <el-breadcrumb-item>{{ currentTitle }}</el-breadcrumb-item>
        </el-breadcrumb>
        <div class="header-right">
          <span class="user">{{ auth.nickname || auth.username }}</span>
          <el-button link type="danger" @click="logout">退出</el-button>
        </div>
      </el-header>

      <div class="tabs-bar">
        <el-tag
          v-for="t in tabs.tabs"
          :key="t.key"
          :closable="t.key !== homeKey"
          :effect="tabs.activeKey === t.key ? 'dark' : 'plain'"
          class="tab"
          @click="go(t.path)"
          @close="closeTab(t.key)"
        >
          {{ t.title }}
        </el-tag>
      </div>

      <el-main class="main">
        <router-view v-slot="{ Component }">
          <keep-alive>
            <component :is="Component" :key="route.fullPath" />
          </keep-alive>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
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

const activePath = computed(() => {
  if (route.path.startsWith('/wb/')) return route.path
  if (route.path.startsWith('/task/')) return String(route.query.fromWb || route.meta.fromWb || '/wb/metadata')
  return route.path
})

const currentTitle = computed(() => (route.meta.title as string) || '')

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
.layout { height: 100%; }
.aside { background: #1d2b36; color: #fff; display: flex; flex-direction: column; }
.brand { height: 56px; line-height: 56px; text-align: center; font-weight: 600; color: #fff; font-size: var(--wbdz-font-card-title); border-bottom: 1px solid rgba(255,255,255,.08); }
.menu { border-right: none; background: transparent; }
.menu :deep(.el-menu-item) { color: #c6d2dc; height: 44px; }
.menu :deep(.el-menu-item:hover) { background: rgba(255,255,255,.06); color: #fff; }
.menu :deep(.el-menu-item.is-active) { background: var(--wbdz-primary); color: #fff; }
.menu-group { padding: 12px 20px 4px; font-size: var(--wbdz-font-caption); color: #7f96a5; }
.header { background: #fff; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid var(--wbdz-border); height: 56px; }
.header-right { display: flex; align-items: center; gap: 12px; }
.user { color: var(--wbdz-secondary); font-size: var(--wbdz-font-body); }
.tabs-bar { background: #fff; border-bottom: 1px solid var(--wbdz-border); padding: 6px 16px; display: flex; gap: 8px; flex-wrap: wrap; }
.tab { cursor: pointer; }
.main { padding: 16px; overflow: auto; }
</style>
