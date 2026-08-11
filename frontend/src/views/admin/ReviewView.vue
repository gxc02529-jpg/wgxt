<template>
  <div class="review-page">
    <h1 class="page-title">审核管理</h1>

    <el-tabs v-model="activeTab" @tab-change="reload">
      <el-tab-pane label="待一审" name="level1">
        <el-table :data="list" v-loading="loading">
          <el-table-column prop="id" label="ID" width="64" />
          <el-table-column prop="title" label="标题" min-width="240" show-overflow-tooltip />
          <el-table-column label="栏目" width="160">
            <template #default="{ row }">
              <el-tag v-for="c in row.categories" :key="c.id" size="small" class="mr-2">{{ c.name }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="author_name" label="作者" width="110" />
          <el-table-column prop="updated_at" label="提交时间" width="160" />
          <el-table-column label="操作" width="120" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="openReview(row)">审核</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="待二审" name="level2">
        <el-table :data="list" v-loading="loading">
          <el-table-column prop="id" label="ID" width="64" />
          <el-table-column prop="title" label="标题" min-width="240" show-overflow-tooltip />
          <el-table-column label="栏目" width="160">
            <template #default="{ row }">
              <el-tag v-for="c in row.categories" :key="c.id" size="small" class="mr-2">{{ c.name }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="author_name" label="作者" width="110" />
          <el-table-column prop="updated_at" label="一审通过时间" width="160" />
          <el-table-column label="操作" width="120" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="openReview(row)">审核</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="审核记录" name="history">
        <el-input v-model="historyKeyword" placeholder="按文稿标题筛选" clearable style="width: 240px; margin-bottom: 12px" @keyup.enter="reload" />
        <el-table :data="history" v-loading="loading">
          <el-table-column prop="id" label="ID" width="64" />
          <el-table-column prop="article_title" label="文稿" min-width="220" show-overflow-tooltip />
          <el-table-column label="级别" width="90">
            <template #default="{ row }">
              <el-tag size="small" :type="row.review_level === 1 ? 'warning' : 'danger'">
                {{ row.review_level === 1 ? '一审' : '二审' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="结果" width="90">
            <template #default="{ row }">
              <el-tag size="small" :type="row.action === 'approve' ? 'success' : 'danger'">
                {{ row.action === 'approve' ? '通过' : '驳回' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="comment" label="意见" min-width="160" show-overflow-tooltip />
          <el-table-column prop="reviewer_name" label="审核人" width="100" />
          <el-table-column prop="created_at" label="时间" width="160" />
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <div class="pager">
      <el-pagination
        layout="total, prev, pager, next"
        :total="total"
        :page-size="pageSize"
        :current-page="page"
        @current-change="changePage"
      />
    </div>

    <!-- 审核对话框：预览文稿 + 通过/驳回 -->
    <el-dialog v-model="dialogVisible" title="文稿审核" width="720px" top="5vh">
      <div v-if="current" class="review-content">
        <h2 class="review-content__title">{{ current.title }}</h2>
        <p class="review-content__meta">
          作者：{{ current.author_name }} ｜ 栏目：{{ current.categories.map((c) => c.name).join('、') }}
        </p>
        <img v-if="current.cover_url" :src="current.cover_url" :alt="current.title" class="review-content__cover" />
        <div class="article-content review-content__body" v-html="current.content"></div>
      </div>
      <el-form label-position="top">
        <el-form-item label="审核意见">
          <el-input v-model="reviewForm.comment" type="textarea" :rows="3" placeholder="填写审核意见（可空）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="danger" :loading="reviewing" @click="doReview('reject')">驳回</el-button>
        <el-button type="primary" :loading="reviewing" @click="doReview('approve')">通过</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { articleApi, reviewApi } from '../../api'

const activeTab = ref('level1')
const list = ref([])
const history = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 10
const loading = ref(false)
const historyKeyword = ref('')
const dialogVisible = ref(false)
const current = ref(null)
const reviewing = ref(false)
const reviewForm = reactive({ comment: '' })

async function load() {
  loading.value = true
  try {
    if (activeTab.value === 'history') {
      const res = await reviewApi.history({ page: page.value, page_size: pageSize, keyword: historyKeyword.value })
      history.value = res.items
      total.value = res.total
    } else {
      const level = activeTab.value === 'level1' ? 1 : 2
      const res = await reviewApi.pending({ level, page: page.value, page_size: pageSize })
      list.value = res.items
      total.value = res.total
    }
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

async function openReview(row) {
  try {
    current.value = await articleApi.detail(row.id)
    reviewForm.comment = ''
    dialogVisible.value = true
  } catch (e) {
    ElMessage.error(String(e))
  }
}

async function doReview(action) {
  reviewing.value = true
  try {
    await reviewApi.review({
      article_id: current.value.id,
      level: activeTab.value === 'level1' ? 1 : 2,
      action,
      comment: reviewForm.comment,
    })
    ElMessage.success(action === 'approve' ? '已通过' : '已驳回')
    dialogVisible.value = false
    load()
  } catch (e) {
    ElMessage.error(String(e))
  } finally {
    reviewing.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.page-title {
  font-size: 24px;
  margin-bottom: 16px;
}

.review-content {
  max-height: 420px;
  overflow: auto;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  padding: 16px;
  margin-bottom: 16px;
}

.review-content__title {
  font-size: 20px;
  margin-bottom: 6px;
}

.review-content__meta {
  color: var(--color-text-muted);
  font-size: 13px;
  margin: 0 0 12px;
}

.review-content__cover {
  border-radius: var(--radius-sm);
  margin-bottom: 12px;
  max-height: 240px;
}

.review-content__body {
  font-size: 15px;
}

.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.mr-2 {
  margin-right: 6px;
}
</style>

