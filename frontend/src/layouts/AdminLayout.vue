<template>
  <!-- 管理后台布局：侧边菜单 + 顶栏 + 内容区 -->
  <el-container class="admin-layout">
    <el-aside width="220px" class="admin-aside">
      <div class="admin-brand">
        <router-link to="/admin">
          <strong>文稿发布后台</strong>
        </router-link>
      </div>
      <el-menu :default-active="activeMenu" router class="admin-menu">
        <el-menu-item v-if="auth.isAdmin" index="/admin">
          <el-icon><Odometer /></el-icon>
          <span>仪表盘</span>
        </el-menu-item>
        <el-menu-item index="/admin/articles">
          <el-icon><Document /></el-icon>
          <span>文稿管理</span>
        </el-menu-item>
        <el-menu-item v-if="auth.isAdmin" index="/admin/reviews">
          <el-icon><Checked /></el-icon>
          <span>审核管理</span>
        </el-menu-item>
        <el-menu-item v-if="auth.isAdmin" index="/admin/categories">
          <el-icon><FolderOpened /></el-icon>
          <span>栏目管理</span>
        </el-menu-item>
        <el-menu-item v-if="auth.isAdmin" index="/admin/users">
          <el-icon><User /></el-icon>
          <span>用户管理</span>
        </el-menu-item>
        <el-menu-item index="/admin/resources">
          <el-icon><Picture /></el-icon>
          <span>资源管理</span>
        </el-menu-item>
        <el-menu-item v-if="auth.isAdmin" index="/admin/portal">
          <el-icon><SetUp /></el-icon>
          <span>门户设置</span>
        </el-menu-item>
        <el-menu-item v-if="auth.isAdmin" index="/admin/stats">
          <el-icon><DataAnalysis /></el-icon>
          <span>数据统计</span>
        </el-menu-item>
        <el-menu-item v-if="auth.isAdmin" index="/admin/settings">
          <el-icon><Setting /></el-icon>
          <span>系统设置</span>
        </el-menu-item>
        <el-menu-item v-if="auth.isAdmin" index="/admin/dify">
          <el-icon><Connection /></el-icon>
          <span>Dify 工作流</span>
        </el-menu-item>
        <el-menu-item v-if="auth.isAdmin" index="/admin/theme">
          <el-icon><Brush /></el-icon>
          <span>门户主题</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="admin-header">
        <div class="admin-header__left">
          <router-link to="/" class="back-link">
            <el-icon><Back /></el-icon>
            返回门户
          </router-link>
        </div>
        <el-dropdown trigger="click">
          <button class="admin-user">
            <el-avatar :size="30" :src="auth.user?.avatar || undefined">
              {{ (auth.user?.nickname || 'A').slice(0, 1) }}
            </el-avatar>
            <span>{{ auth.user?.nickname || auth.user?.username }}</span>
          </button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item @click="auth.logout(); router.push('/login')">退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </el-header>

      <el-main class="admin-main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  Back, Brush, Checked, Connection, DataAnalysis, Document, FolderOpened, Odometer, Picture, Setting, SetUp, User,
} from '@element-plus/icons-vue'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

// 高亮当前菜单项（编辑页归入文稿管理）
const activeMenu = computed(() => {
  if (route.path.startsWith('/admin/articles')) return '/admin/articles'
  return route.path
})
</script>

<style scoped>
.admin-layout {
  min-height: 100dvh;
}

.admin-aside {
  background: #0f172a;
  color: #cbd5e1;
}

.admin-brand {
  padding: 18px 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.admin-brand a {
  color: #fff;
  font-family: var(--font-heading);
  font-size: 18px;
}

.admin-menu {
  border-right: none;
  background: transparent;
  --el-menu-bg-color: transparent;
  --el-menu-text-color: #cbd5e1;
  --el-menu-hover-bg-color: rgba(255, 255, 255, 0.08);
  --el-menu-active-color: #fff;
}

.admin-menu .el-menu-item.is-active {
  background: var(--color-primary);
}

.admin-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
}

.back-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--color-text-secondary);
  font-size: 14px;
}

.admin-user {
  display: flex;
  align-items: center;
  gap: 8px;
  border: none;
  background: none;
  color: var(--color-text);
  font-size: 14px;
  padding: 4px 8px;
  border-radius: var(--radius-sm);
}

.admin-main {
  background: var(--color-bg);
  padding: 20px;
}
</style>
