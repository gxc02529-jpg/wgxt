<template>
  <div class="article-admin">
    <div class="admin-head">
      <span class="admin-head__icon" aria-hidden="true">
        <el-icon><Document /></el-icon>
      </span>
      <div class="admin-head__text">
        <h1 class="admin-head__title">文稿管理</h1>
        <p class="admin-head__sub">管理全站文稿的编写、审核与发布状态</p>
      </div>
      <div class="admin-head__actions">
        <el-button type="primary" @click="router.push('/admin/articles/new')">
          <el-icon><EditPen /></el-icon>
          写新文稿
        </el-button>
        <el-button type="danger" plain :disabled="!selectedRows.length" @click="batchRemove">
          <el-icon><Delete /></el-icon>
          批量删除{{ selectedRows.length ? `（${selectedRows.length}）` : '' }}
        </el-button>
      </div>
    </div>

    <div class="admin-card">
      <!-- 筛选栏 -->
      <div class="admin-card__toolbar">
        <el-input
          v-model="filters.keyword"
          placeholder="标题关键词"
          clearable
          style="width: 240px"
          @keyup.enter="reload"
        />
        <el-select v-model="filters.status" placeholder="全部状态" clearable style="width: 150px" @change="reload">
          <el-option v-for="(label, value) in statusMap" :key="value" :label="label" :value="value" />
        </el-select>
        <el-button @click="reload">
          <el-icon><Search /></el-icon>
          查询
        </el-button>
      </div>

      <el-table :data="articles" v-loading="loading" style="width: 100%" @selection-change="handleSelectionChange">
        <el-table-column type="selection" width="48" :selectable="isSelectable" />
        <el-table-column label="文稿" min-width="280">
          <template #default="{ row }">
            <div class="cell-media">
              <img v-if="row.cover_url" :src="row.cover_url" :alt="row.title" class="cell-thumb" loading="lazy" />
              <span v-else class="cell-thumb cell-thumb--empty">
                {{ (row.categories[0]?.name || '文').slice(0, 1) }}
              </span>
              <div class="cell-title">
                <span class="cell-title__main" :title="row.title">{{ row.title }}</span>
                <span class="cell-title__sub">#{{ row.id }} · {{ row.author_name }} · {{ row.updated_at }}</span>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="栏目" width="170">
          <template #default="{ row }">
            <div class="tag-list">
              <span v-for="c in row.categories" :key="c.id" class="mini-tag">{{ c.name }}</span>
              <span v-if="!row.categories.length" class="mini-tag mini-tag--empty">未分类</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <span class="status-badge" :class="statusBadgeClass(row.status)">
              {{ statusMap[row.status] || row.status }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="数据" width="210">
          <template #default="{ row }">
            <div class="stat-line">
              <span class="stat-line__item"><el-icon><View /></el-icon>{{ row.view_count }} 浏览</span>
              <span class="stat-line__item">点赞 {{ row.like_count }}</span>
              <span class="stat-line__item">收藏 {{ row.favorite_count }}</span>
              <span class="stat-line__item">转发 {{ row.share_count }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="250" fixed="right">
          <template #default="{ row }">
            <div class="row-actions">
              <el-button v-if="isEditable(row)" link type="primary" @click="router.push(`/admin/articles/${row.id}/edit`)">
                <el-icon><EditPen /></el-icon>
                编辑
              </el-button>
              <el-button v-if="canSubmit(row)" link type="warning" @click="submit(row)">
                <el-icon><Promotion /></el-icon>
                提交审核
              </el-button>
              <el-button v-if="isAdmin && row.status === 'published'" link type="info" @click="offline(row)">
                <el-icon><SwitchButton /></el-icon>
                下线
              </el-button>
              <el-button v-if="canDelete(row)" link type="danger" @click="remove(row)">
                <el-icon><Delete /></el-icon>
                删除
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <div class="admin-pager">
        <span class="admin-pager__info">共 <strong>{{ total }}</strong> 篇文稿</span>
        <el-pagination
          layout="total, prev, pager, next"
          :total="total"
          :page-size="pageSize"
          :current-page="page"
          @current-change="changePage"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Delete, Document, EditPen, Promotion, Search, SwitchButton, View,
} from '@element-plus/icons-vue'
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
const selectedRows = ref([])

function statusBadgeClass(s) {
  return {
    draft: 'status-badge--gray',
    pending_first: 'status-badge--orange',
    pending_second: 'status-badge--red',
    published: 'status-badge--green',
    rejected: 'status-badge--red',
    offline: 'status-badge--gray',
  }[s] || 'status-badge--gray'
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

// 仅可删除的文稿行允许勾选（管理员或作者本人）
function isSelectable(row) {
  return canDelete(row)
}

function handleSelectionChange(rows) {
  selectedRows.value = rows
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

async function batchRemove() {
  if (!selectedRows.value.length) return
  try {
    await ElMessageBox.confirm(
      `确定删除选中的 ${selectedRows.value.length} 篇文稿？删除后不可恢复。`,
      '批量删除确认',
      { type: 'warning' },
    )
  } catch {
    return
  }
  let ok = 0
  let fail = 0
  for (const row of selectedRows.value) {
    try {
      await articleApi.remove(row.id)
      ok++
    } catch {
      fail++
    }
  }
  selectedRows.value = []
  if (fail) {
    ElMessage.warning(`已删除 ${ok} 篇，失败 ${fail} 篇`)
  } else {
    ElMessage.success(`已删除 ${ok} 篇文稿`)
  }
  load()
}

onMounted(load)
</script>

<style scoped>
</style>

