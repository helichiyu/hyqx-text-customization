<template>
  <div class="page-stack">
    <PageHeader title="参数配置" description="维护公共素材规则和四条产线参数，草稿发布后由新任务锁定版本快照。" />

    <el-card shadow="never">
      <el-tabs v-model="active" @tab-change="load">
        <el-tab-pane v-for="t in tabs" :key="t.line" :label="t.name" :name="t.line" />
      </el-tabs>

      <div v-loading="loading">
        <el-alert v-if="hasDraft" type="warning" :closable="false" show-icon
          title="存在未发布草稿" description="草稿仅用于编辑，任务创建时锁定的是已发布版本；编辑完成后请发布。" style="margin-bottom: 12px" />

        <div class="bar">
          <div>
            <b>{{ config.lineName || tabName }}</b>
            <span class="muted" style="margin-left: 10px">
              当前最新版本：
              <span class="mono">{{ config.latest?.version || '暂无' }}</span>
              <template v-if="config.latest?.publishedAt">（{{ fmtTime(config.latest.publishedAt) }} · {{ config.latest.publishedBy }}）</template>
            </span>
          </div>
          <div style="flex: 1" />
          <el-button @click="formatRows">校验参数</el-button>
          <el-button type="primary" plain :loading="saving" @click="saveDraft">保存草稿</el-button>
          <el-button type="success" :loading="publishing" @click="publish">发布新版本</el-button>
        </div>

        <el-table :data="rows" size="small" border>
          <el-table-column label="序号" width="60" align="center">
            <template #default="{ $index }">{{ $index + 1 }}</template>
          </el-table-column>
          <el-table-column label="参数名" width="260">
            <template #default="{ row }">
              <el-input v-model="row.name" size="small" placeholder="如 单文件大小上限(MB)" />
            </template>
          </el-table-column>
          <el-table-column label="取值" min-width="220">
            <template #default="{ row }">
              <el-input v-model="row.value" size="small" placeholder="如 50 / 4-8 / true" />
            </template>
          </el-table-column>
          <el-table-column label="说明" min-width="260">
            <template #default="{ row }">
              <el-input v-model="row.desc" size="small" placeholder="参数含义与影响" />
            </template>
          </el-table-column>
          <el-table-column label="操作" width="70" align="center">
            <template #default="{ $index }">
              <el-button link type="danger" size="small" @click="rows.splice($index, 1)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-button class="add-btn" size="small" @click="rows.push({ name: '', value: '', desc: '' })">+ 新增参数组</el-button>

        <el-collapse style="margin-top: 16px">
          <el-collapse-item title="JSON 视图（发布内容预览）" name="json">
            <pre class="json">{{ jsonPreview }}</pre>
          </el-collapse-item>
        </el-collapse>

        <h4>历史版本</h4>
        <el-table :data="config.versions || []" size="small">
          <el-table-column prop="version" label="版本" width="100" />
          <el-table-column prop="publishedBy" label="发布人" width="120" />
          <el-table-column prop="publishedAt" label="发布时间" width="180" :formatter="(_r: any, _c: any, v: string) => fmtTime(v)" />
          <el-table-column label="参数组数" width="100" align="center">
            <template #default="{ row }">{{ row.content?.length || 0 }}</template>
          </el-table-column>
          <el-table-column label="操作" width="100">
            <template #default="{ row }">
              <el-button link type="primary" size="small" @click="openVersion(row)">查看</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>

    <el-dialog v-model="versionVisible" :title="`版本 ${version?.version} 内容`" class="wbdz-dialog">
      <el-table :data="version?.content || []" size="small" border max-height="420">
        <el-table-column prop="name" label="参数名" width="200" />
        <el-table-column prop="value" label="取值" width="180" />
        <el-table-column prop="desc" label="说明" min-width="220" />
      </el-table>
      <template #footer>
        <el-button @click="versionVisible = false">关闭</el-button>
        <el-button type="primary" plain @click="useVersion">载入编辑器</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import PageHeader from '@/components/PageHeader.vue'
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { LINE_NAMES, paramLineConfig, paramSaveDraft, paramPublish } from '@/api'

const tabs = [
  { line: 'common', name: '公共规则' },
  ...Object.entries(LINE_NAMES).map(([line, name]) => ({ line, name })),
]

const active = ref('common')
const loading = ref(false)
const saving = ref(false)
const publishing = ref(false)
const config = ref<any>({})
const hasDraft = ref(false)
const rows = ref<{ name: string; value: string; desc: string }[]>([])
const versionVisible = ref(false)
const version = ref<any>(null)

const tabName = computed(() => tabs.find((t) => t.line === active.value)?.name || active.value)

const jsonPreview = computed(() =>
  JSON.stringify(rows.value.filter((r) => r.name.trim()).map((r) => ({ name: r.name, value: r.value, desc: r.desc })), null, 2),
)

function fmtTime(v?: string) {
  if (!v || v === 'null' || v === 'undefined') return '—'
  return v.replace('T', ' ').slice(0, 19)
}

function toRows(content: any[]) {
  return (content || []).map((c) => ({
    name: c.name ?? '', value: c.value == null ? '' : String(typeof c.value === 'object' ? JSON.stringify(c.value) : c.value),
    desc: c.desc ?? '',
  }))
}

async function load() {
  loading.value = true
  try {
    const c = await paramLineConfig(active.value)
    config.value = c
    hasDraft.value = !!c.hasDraft
    rows.value = toRows(c.draft?.content || [])
  } finally {
    loading.value = false
  }
}

function validate(): boolean {
  const valid = rows.value.filter((r) => r.name.trim() && String(r.value).trim())
  if (!valid.length) {
    ElMessage.warning('至少保留一个填写完整的参数组（name 与 value 均非空）')
    return false
  }
  const names = valid.map((r) => r.name.trim())
  if (new Set(names).size !== names.length) {
    ElMessage.warning('参数名不能重复')
    return false
  }
  return true
}

function contentJson() {
  return JSON.stringify(rows.value.filter((r) => r.name.trim()).map((r) => ({
    name: r.name.trim(), value: r.value, desc: r.desc,
  })))
}

function formatRows() {
  if (!validate()) return
  ElMessage.success('参数校验通过')
}

async function saveDraft() {
  if (!validate()) return
  saving.value = true
  try {
    await paramSaveDraft(active.value, contentJson())
    ElMessage.success('草稿已保存')
    await load()
  } finally {
    saving.value = false
  }
}

async function publish() {
  if (!validate()) return
  await ElMessageBox.confirm(`确认以当前编辑内容发布 ${tabName.value} 的新版本？发布后草稿清除，任务将可选用新版本。`, '发布确认', { type: 'warning' })
  publishing.value = true
  try {
    const v: any = await paramPublish(active.value, contentJson())
    ElMessage.success(`已发布 ${v.version}`)
    await load()
  } finally {
    publishing.value = false
  }
}

function openVersion(v: any) {
  version.value = v
  versionVisible.value = true
}

function useVersion() {
  rows.value = toRows(version.value?.content || [])
  versionVisible.value = false
  ElMessage.info('已载入编辑器，保存草稿或发布后生效')
}

onMounted(load)
</script>

<style scoped>
.bar { display: flex; align-items: center; gap: 10px; margin: 4px 0 14px; flex-wrap: wrap; }
.muted { color: var(--wbdz-secondary); font-size: var(--wbdz-font-body); }
.mono { font-family: var(--wbdz-font-mono); }
.add-btn { margin-top: 10px; }
.json { background: var(--wbdz-bg-page); padding: 12px; font-size: var(--wbdz-font-caption); margin: 0; max-height: 300px; overflow: auto; white-space: pre-wrap; }
h4 { margin: 20px 0 10px; color: var(--wbdz-title); font-size: var(--wbdz-font-body); }
</style>
