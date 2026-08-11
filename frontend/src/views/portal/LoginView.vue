<template>
  <div class="auth-page">
    <div class="auth-card">
      <router-link to="/" class="auth-card__brand" aria-label="返回首页">
        <svg viewBox="0 0 32 32" width="26" height="26" aria-hidden="true">
          <rect width="32" height="32" rx="6" fill="#2563EB" />
          <path d="M9 9h14v3H12v4h10v3H12v4h11v3H9z" fill="#fff" />
        </svg>
        <span>文稿发布</span>
      </router-link>

      <h1 class="auth-card__title">欢迎回来</h1>
      <p class="auth-card__subtitle">登录文稿发布，参与点赞、收藏与转发</p>

      <el-form ref="formRef" :model="form" :rules="rules" label-position="top" size="large" @submit.prevent="submit">
        <el-form-item label="账号" prop="username">
          <el-input v-model="form.username" placeholder="请输入账号" autocomplete="username" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="请输入密码"
            show-password
            autocomplete="current-password"
            @keyup.enter="submit"
          />
        </el-form-item>
        <el-button type="primary" class="auth-card__submit" :loading="loading" @click="submit">
          登录
        </el-button>
      </el-form>

      <p class="auth-card__switch">
        还没有账号？
        <router-link :to="{ name: 'register', query: { redirect: redirect } }">立即注册</router-link>
      </p>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { authApi } from '../../api'
import { useAuthStore } from '../../stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const formRef = ref()
const loading = ref(false)
const redirect = route.query.redirect || '/'

const form = reactive({ username: '', password: '' })
const rules = {
  username: [{ required: true, message: '请输入账号', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

async function submit() {
  await formRef.value.validate()
  loading.value = true
  try {
    const res = await authApi.login(form)
    auth.setSession(res.access_token, res.user)
    ElMessage.success('登录成功')
    router.push(redirect)
  } catch (e) {
    ElMessage.error(String(e))
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
/* Hallmark · genre: editorial · macrostructure: Form · design-system: design.md · designed-as-app */
/* Hallmark · pre-emit critique: P4 H4 E4 S4 R4 V4 */
.auth-page {
  min-height: calc(100dvh - 280px);
  display: grid;
  place-items: center;
  padding: var(--space-6) var(--space-4);
}

.auth-card {
  width: 100%;
  max-width: 420px;
  background: var(--color-paper);
  border: var(--rule) solid var(--color-rule);
  border-top: 3px solid var(--color-accent);
  border-radius: var(--radius-sm);
  padding: var(--space-6);
}

.auth-card__brand {
  display: flex;
  align-items: center;
  gap: 8px;
  font-family: var(--font-heading);
  font-size: 18px;
  font-weight: 700;
  color: var(--color-ink);
  margin-bottom: var(--space-6);
}

.auth-card__title {
  font-family: var(--font-heading);
  font-size: var(--text-3xl);
  font-weight: 700;
  color: var(--color-ink);
  margin-bottom: var(--space-2);
}

.auth-card__subtitle {
  color: var(--color-ink-2);
  margin: 0 0 var(--space-5);
  font-size: var(--text-sm);
}

.auth-card__submit {
  width: 100%;
  min-height: var(--size-touch);
  margin-top: var(--space-1);
}

.auth-card__switch {
  text-align: center;
  color: var(--color-ink-2);
  font-size: var(--text-sm);
  margin: var(--space-5) 0 0;
}

.auth-card__switch a {
  display: inline-flex;
  align-items: center;
  min-height: var(--size-touch);
  padding: 0 6px;
  color: var(--color-accent);
  font-weight: 500;
}
</style>
