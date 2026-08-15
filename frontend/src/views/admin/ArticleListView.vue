<template>
  <div class="article-admin">
    <div class="page-head">
      <h1 class="page-title">文稿管理</h1>
      <el-button type="primary" @click="router.push('/admin/articles/new')">
        写新文稿
      </el-button>
    </div>

    <!-- 筛选栏 -->
    <div class="filters">
      <el-input v-model="filters.keyword" placeholder="标题关键词" clearable style="width: 220px" @keyup.enter="reload" />
      <el-select v-model="filters.status" placeholder="全部状态" clearable style="width: 150px" @change="reload">
        <el-option v-for="(label, value) in statusMap" :key="value" :label="label" :value="value" />
      </el-select>
      <el-button @click="reload">查询</el-button>
    </div>

    <el-table :data="articles" v-loading="loading" style="width: 100%">
      <el-table-column prop="id" label="ID" width="64" />
      <el-table-column prop="title" label="标题" min-width="220" show-overflow-tooltip />
      <el-table-column label="栏目" width="150">
        <template #default="{ row }">
          <el-tag v-for="c in row.categories" :key="c.id" size="small" class="mr-2">{{ c.name }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="author_name" label="作者" width="110" />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="statusTagType(row.status)" size="small">{{ statusMap[row.status] || row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="view_count" label="浏览" width="80" />
      <el-table-column prop="like_count" label="点赞" width="80" />
      <el-table-column prop="favorite_count" label="收藏" width="80" />
      <el-table-column prop="share_count" label="转发" width="80" />
      <el-table-column prop="updated_at" label="更新时间" width="160" />
      <el-table-column label="操作" width="250" fixed="right">
        <template #default="{ row }">
          <el-button v-if="isEditable(row)" link type="primary" @click="router.push(`/admin/articles/${row.id}/edit`)">编辑</el-button>
          <el-button v-if="canSubmit(row)" link type="warning" @click="submit(row)">提交审核</el-button>
          <el-button v-if="isAdmin && row.status === 'published'" link type="info" @click="offline(row)">下线</el-button>
          <el-button v-if="canDelete(row)" link type="danger" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pager">
      <el-pagination
        layout="total, prev, pager, next"
        :total="total"
        :page-size="pageSize"
        :current-page="page"
        @current-change="changePage"
      />
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { articleApi } from '../../api'
import { useAuthStore } from '../../stores/auth'

const router = useRouter()
const auth = useAuthStore()
const isAdmin = auth.isAdmin

const statusMap = {
  draft: '草稿',
  pending_first: '待一审',
  pending_second: '待二审',
  published: '已发布',
  rejected: '已驳回',
  offline: '已下线',
}

const articles = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 10
const loading = ref(false)
const filters = reactive({ keyword: '', status: '' })

function statusTagType(s) {
  return {
    draft: 'info',
    pending_first: 'warning',
    pending_second: 'danger',
    published: 'success',
    rejected: 'danger',
    offline: 'info',
  }[s] || 'info'
}

function isEditable(row) {
  return (row.status === 'draft' || row.status === 'rejected') && (isAdmin || row.author_id === auth.user?.id)
}

function canSubmit(row) {
  return (row.status === 'draft' || row.status === 'rejected') && (isAdmin || row.author_id === auth.user?.id)
}

function canDelete(row) {
  return isAdmin || row.author_id === auth.user?.id
}

async function load() {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize, ...filters }
    const res = isAdmin ? await articleApi.adminList(params) : await articleApi.mine(params)
    articles.value = res.items
    total.value = res.total
  } catch (e) {
    ElMessage.error(String(e))
  } finally {
    loading.value = false
  }
}

function reload() {
  page.value = 1
  load()
}

function changePage(p) {
  page.value = p
  load()
}

async function submit(row) {
  try {
    await articleApi.submit(row.id)
    ElMessage.success('已提交审核（待一审）')
    load()
  } catch (e) {
    ElMessage.error(String(e))
  }
}

async function offline(row) {
  try {
    await articleApi.offline(row.id)
    ElMessage.success('文稿已下线')
    load()
  } catch (e) {
    ElMessage.error(String(e))
  }
}

async function remove(row) {
  try {
    await ElMessageBox.confirm(`确定删除《${row.title}》？删除后不可恢复。`, '删除确认', { type: 'warning' })
    await articleApi.remove(row.id)
    ElMessage.success('已删除')
    load()
  } catch (e) {
    if (e !== 'cancel' && e !== 'close') ElMessage.error(String(e))
  }
}

onMounted(load)
</script>

<style scoped>
.page-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.page-title {
  font-size: 24px;
}

.filters {
  display: flex;
  gap: 10px;
  margin-bottom: 16px;
}

.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.mr-2 {
  margin-right: 6px;
}

.no-city {
  color: var(--color-text-3, #999);
}
</style>

