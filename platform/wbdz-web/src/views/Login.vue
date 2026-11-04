<template>
  <div class="login-wrap">
    <el-card class="login-card">
      <h2 class="title">文本定制化生产平台</h2>
      <el-form :model="form" @submit.prevent="doLogin">
        <el-form-item>
          <el-input v-model="form.username" placeholder="账号" size="large" autofocus />
        </el-form-item>
        <el-form-item>
          <el-input v-model="form.password" type="password" placeholder="密码" size="large" show-password />
        </el-form-item>
        <el-button type="primary" size="large" class="btn" :loading="loading" @click="doLogin">
          登 录
        </el-button>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()
const form = reactive({ username: 'admin', password: '' })
const loading = ref(false)

async function doLogin() {
  if (!form.username || !form.password) {
    ElMessage.warning('请输入账号与密码')
    return
  }
  loading.value = true
  try {
    await auth.login(form.username, form.password)
    router.push('/')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-wrap { height: 100%; display: flex; align-items: center; justify-content: center; background: linear-gradient(135deg, #1d2b36 0%, #256d8b 100%); }
.login-card { width: 380px; padding: 12px 8px; }
.title { text-align: center; margin: 8px 0 24px; color: var(--wbdz-title); }
.btn { width: 100%; }
</style>
