<template>
  <div class="behavior-admin">
    <div class="page-head">
      <h1 class="page-title">用户行为</h1>
    </div>

    <el-tabs v-model="activeTab" @tab-change="onTabChange">
      <!-- 观看历史 -->
      <el-tab-pane label="观看历史" name="history">
        <div class="filter-bar">
          <el-input
            v-model="keyword"
            placeholder="搜索用户名 / 昵称 / 文稿标题"
            clearable
            style="width: 300px"
            @keyup.enter="load"
            @clear="load"
          />
          <el-button type="primary" @click="load">查询</el-button>
        </div>
        <el-alert
          class="summary-tip"
          type="info"
          :closable="false"
          show-icon
          :title="`共 ${total} 条观看记录，累计观看时长 ${formatDuration(totalWatchSeconds)}`"
        />
        <el-table :data="items" v-loading="loading">
          <el-table-column label="用户" width="160">
            <template #default="{ row }">{{ row.nickname }}（{{ row.username }}）</template>
          </el-table-column>
          <el-table-column prop="article_title" label="文稿" min-width="240" show-overflow-tooltip />
          <el-table-column label="最近观看时间" width="170">
            <template #default="{ row }">{{ row.viewed_at }}</template>
          </el-table-column>
          <el-table-column label="累计观看时长" width="130">
            <template #default="{ row }">{{ formatDuration(row.watch_seconds) }}</template>
          </el-table-column>
          <el-table-column prop="watch_count" label="观看次数" width="90" />
          <el-table-column label="操作" width="90" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="openArticle(row.article_id)">查看文稿</el-button>
            </template>
          </el-table-column>
        </el-table>
        <div class="pager">
          <el-pagination
            layout="prev, pager, next"
            :total="total"
            :page-size="pageSize"
            :current-page="page"
            @current-change="load"
          />
        </div>
      </el-tab-pane>

      <!-- 不感兴趣 -->
      <el-tab-pane label="不感兴趣" name="dislikes">
        <el-table :data="dislikeItems" v-loading="dislikeLoading">
          <el-table-column label="用户" width="160">
            <template #default="{ row }">{{ row.nickname }}（{{ row.username }}）</template>
          </el-table-column>
          <el-table-column prop="article_title" label="文稿" min-width="240" show-overflow-tooltip />
          <el-table-column label="标记时间" width="170">
            <template #default="{ row }">{{ row.created_at }}</template>
          </el-table-column>
          <el-table-column label="操作" width="90" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="openArticle(row.article_id)">查看文稿</el-button>
            </template>
          </el-table-column>
        </el-table>
        <div class="pager">
          <el-pagination
            layout="prev, pager, next"
            :total="dislikeTotal"
            :page-size="pageSize"
            :current-page="dislikePage"
            @current-change="loadDislikes"
          />
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { behaviorApi } from '../../api'

const activeTab = ref('history')
const keyword = ref('')

// 观看历史
const items = ref([])
const total = ref(0)
const totalWatchSeconds = ref(0)
const page = ref(1)
const pageSize = 10
const loading = ref(false)

// 不感兴趣
const dislikeItems = ref([])
const dislikeTotal = ref(0)
const dislikePage = ref(1)
const dislikeLoading = ref(false)

function formatDuration(seconds) {
  const s = Number(seconds) || 0
  if (s <= 0) return '0 秒'
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  const sec = s % 60
  return [h ? `${h} 小时` : '', m ? `${m} 分` : '', sec ? `${sec} 秒` : ''].filter(Boolean).join(' ') || '0 秒'
}

async function load(p) {
  if (p) page.value = p
  loading.value = true
  try {
    const res = await behaviorApi.viewHistory({
      keyword: keyword.value || undefined,
      page: page.value,
      page_size: pageSize,
    })
    items.value = res.items
    total.value = res.total
    totalWatchSeconds.value = res.total_watch_seconds
  } catch (e) {
    ElMessage.error(String(e))
  } finally {
    loading.value = false
  }
}

async function loadDislikes(p) {
  if (p) dislikePage.value = p
  dislikeLoading.value = true
  try {
    const res = await behaviorApi.dislikes({
      keyword: keyword.value || undefined,
      page: dislikePage.value,
      page_size: pageSize,
    })
    dislikeItems.value = res.items
    dislikeTotal.value = res.total
  } catch (e) {
    ElMessage.error(String(e))
  } finally {
    dislikeLoading.value = false
  }
}

function onTabChange() {
  if (activeTab.value === 'history') {
    load()
  } else {
    loadDislikes()
  }
}

function openArticle(id) {
  window.open(`/article/${id}`, '_blank', 'noopener')
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

.filter-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 12px;
}

.summary-tip {
  margin-bottom: 12px;
}

.pager {
  display: flex;
  justify-content: center;
  margin-top: 16px;
}
</style>
