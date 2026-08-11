<template>
  <div class="auth-page">
    <div class="auth-card">
      <router-link to="/" class="auth-card__brand" aria-label="返回首页">
        <svg viewBox="0 0 32 32" width="26" height="26" aria-hidden="true">
          <rect width="32" height="32" rx="6" fill="#2563EB" />
          <path d="M9 9h14v3H12v4h10v3H12v4h11v3H9z" fill="#fff" />
        </svg>
        <span>在线融媒体文稿平台</span>
      </router-link>

      <h1 class="auth-card__title">注册账号</h1>
      <p class="auth-card__subtitle">可选择注册为普通用户或编辑（编辑可写稿投稿）</p>

      <el-form ref="formRef" :model="form" :rules="rules" label-position="top" size="large">
        <el-form-item label="账号" prop="username">
          <el-input v-model="form.username" placeholder="3-50 位字符" autocomplete="username" />
        </el-form-item>
        <el-form-item label="昵称" prop="nickname">
          <el-input v-model="form.nickname" placeholder="选填" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="form.email" placeholder="选填" autocomplete="email" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" type="password" placeholder="至少 6 位" show-password autocomplete="new-password" />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirm">
          <el-input v-model="form.confirm" type="password" placeholder="再次输入密码" show-password autocomplete="new-password" />
        </el-form-item>
        <el-form-item label="注册身份">
          <el-radio-group v-model="form.role">
            <el-radio value="user">普通用户</el-radio>
            <el-radio value="editor">编辑（可写稿）</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-button type="primary" class="auth-card__submit" :loading="loading" @click="submit">注册</el-button>
      </el-form>

      <p class="auth-card__switch">
        已有账号？
        <router-link :to="{ name: 'login', query: { redirect: redirect } }">去登录</router-link>
      </p>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { authApi } from '../../api'

const route = useRoute()
const router = useRouter()
const formRef = ref()
const loading = ref(false)
const redirect = route.query.redirect || '/'

const form = reactive({ username: '', nickname: '', email: '', password: '', confirm: '', role: 'user' })
const rules = {
  username: [
    { required: true, message: '请输入账号', trigger: 'blur' },
    { min: 3, max: 50, message: '账号长度 3-50 位', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少 6 位', trigger: 'blur' },
  ],
  confirm: [
    { required: true, message: '请再次输入密码', trigger: 'blur' },
    {
      validator: (_rule, value, callback) => {
        if (value !== form.password) callback(new Error('两次输入的密码不一致'))
        else callback()
      },
      trigger: 'blur',
    },
  ],
}

async function submit() {
  await formRef.value.validate()
  loading.value = true
  try {
    await authApi.register({
      username: form.username,
      nickname: form.nickname,
      email: form.email,
      password: form.password,
      role: form.role,
    })
    ElMessage.success('注册成功，请登录')
    router.push({ name: 'login', query: { redirect } })
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
  max-width: 440px;
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
