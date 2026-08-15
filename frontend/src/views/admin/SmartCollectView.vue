<template>
  <div class="smart-collect-page">
    <div class="page-head">
      <div>
        <h1 class="page-title">智能采编</h1>
        <p class="page-description">创建采编任务，保存联网搜索发现的新闻线索，并可随时回看历史结果。</p>
      </div>
      <el-button type="primary" plain @click="router.push({ name: 'admin-smart-collect-evaluation' })">
        相关性评估
      </el-button>
    </div>

    <el-card shadow="never" class="create-card">
      <template #header><strong>新建采编任务</strong></template>
      <el-form :model="form" inline class="search-form" @submit.prevent="createTask">
        <el-form-item label="新闻主题" class="query-item">
          <el-input
            v-model="form.query"
            placeholder="例如：OpenAI 发布新模型"
            clearable
            maxlength="200"
          />
        </el-form-item>
        <el-form-item label="时间范围">
          <el-select v-model="form.time_range" style="width: 130px">
            <el-option label="最近一天" value="day" />
            <el-option label="最近一周" value="week" />
            <el-option label="最近一月" value="month" />
            <el-option label="最近一年" value="year" />
          </el-select>
        </el-form-item>
        <el-form-item label="最大结果数">
          <el-input-number v-model="form.max_results" :min="1" :max="20" :step="1" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" native-type="submit" :loading="creating">创建并搜索</el-button>
        </el-form-item>
      </el-form>

      <el-alert
        v-if="createError"
        :title="createError"
        type="error"
        show-icon
        :closable="false"
      />
    </el-card>

    <el-card shadow="never">
      <template #header>
        <div class="history-head">
          <strong>历史采编任务</strong>
          <div class="history-actions">
            <el-select
              v-model="filters.status"
              placeholder="全部状态"
              clearable
              style="width: 130px"
              @change="handleFilterChange"
            >
              <el-option label="进行中" value="running" />
              <el-option label="已完成" value="completed" />
              <el-option label="失败" value="failed" />
            </el-select>
            <el-button :loading="loading" @click="loadTasks">刷新</el-button>
          </div>
        </div>
      </template>

      <el-table v-loading="loading" :data="tasks" empty-text="暂无采编任务">
        <el-table-column prop="id" label="任务ID" width="90" />
        <el-table-column prop="query" label="新闻主题" min-width="220" show-overflow-tooltip />
        <el-table-column v-if="auth.isAdmin" prop="creator_name" label="创建人" width="130" />
        <el-table-column label="时间范围" width="100">
          <template #default="{ row }">{{ timeRangeText[row.time_range] || row.time_range }}</template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusMeta[row.status]?.type || 'info'">
              {{ statusMeta[row.status]?.label || row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="result_count" label="线索数" width="90" />
        <el-table-column prop="credits_used" label="Credits" width="90" />
        <el-table-column label="创建时间" min-width="170">
          <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openTask(row.id)">查看详情</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :total="pagination.total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          @current-change="loadTasks"
          @size-change="handleSizeChange"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import { smartCollectApi } from '../../api'
import { useAuthStore } from '../../stores/auth'

const router = useRouter()
const auth = useAuthStore()

const form = reactive({ query: '', time_range: 'week', max_results: 20 })
const filters = reactive({ status: '' })
const pagination = reactive({ page: 1, pageSize: 10, total: 0 })
const tasks = ref([])
const creating = ref(false)
const loading = ref(false)
const createError = ref('')
const pollTimers = new Map()
const locallyCreatedTaskIds = new Set()
let pageDestroyed = false

const POLL_INTERVAL_MS = 2500

const timeRangeText = { day: '最近一天', week: '最近一周', month: '最近一月', year: '最近一年' }
const statusMeta = {
  running: { label: '进行中', type: 'warning' },
  completed: { label: '已完成', type: 'success' },
  failed: { label: '失败', type: 'danger' },
}

function formatDate(value) {
  return value ? new Date(value).toLocaleString('zh-CN', { hour12: false }) : '-'
}

function stopTaskPolling(taskId) {
  const timer = pollTimers.get(taskId)
  if (timer) clearTimeout(timer)
  pollTimers.delete(taskId)
}

function scheduleTaskPolling(taskId, delay = POLL_INTERVAL_MS) {
  if (pageDestroyed || pollTimers.has(taskId)) return
  const timer = setTimeout(() => {
    pollTimers.delete(taskId)
    pollTask(taskId)
  }, delay)
  pollTimers.set(taskId, timer)
}

function syncRunningTaskPolling() {
  tasks.value.forEach((task) => {
    if (task.status === 'running') scheduleTaskPolling(task.id)
    else stopTaskPolling(task.id)
  })
}

async function pollTask(taskId) {
  if (pageDestroyed) return
  try {
    const detail = await smartCollectApi.getTask(taskId)
    const index = tasks.value.findIndex((task) => task.id === taskId)
    if (index !== -1) {
      tasks.value[index] = { ...tasks.value[index], ...detail }
    }
    if (detail.status === 'running') {
      scheduleTaskPolling(taskId)
      return
    }
    stopTaskPolling(taskId)
    if (locallyCreatedTaskIds.delete(taskId)) {
      if (detail.status === 'completed') {
        ElMessage.success(`采编任务 #${taskId} 已完成，共保存 ${detail.result_count} 条线索`)
      } else {
        ElMessage.error(detail.error_message || `采编任务 #${taskId} 执行失败`)
      }
    }
  } catch {
    // 短暂网络异常不把后台任务误判为失败，页面存续期间继续轮询。
    scheduleTaskPolling(taskId)
  }
}

async function loadTasks() {
  loading.value = true
  try {
    const result = await smartCollectApi.listTasks({
      page: pagination.page,
      page_size: pagination.pageSize,
      status: filters.status || undefined,
    })
    tasks.value = result.items || []
    pagination.total = result.total || 0
    syncRunningTaskPolling()
  } catch (error) {
    ElMessage.error(String(error || '历史任务加载失败'))
  } finally {
    loading.value = false
  }
}

function handleFilterChange() {
  pagination.page = 1
  loadTasks()
}

function handleSizeChange() {
  pagination.page = 1
  loadTasks()
}

function openTask(id) {
  router.push({ name: 'admin-smart-collect-task', params: { id } })
}

async function createTask() {
  if (creating.value) return
  const query = form.query.trim()
  if (!query) {
    ElMessage.warning('请输入新闻主题')
    return
  }

  creating.value = true
  createError.value = ''
  try {
    const result = await smartCollectApi.createTask({
      query,
      time_range: form.time_range,
      max_results: form.max_results,
    })
    locallyCreatedTaskIds.add(result.task_id)
    filters.status = ''
    pagination.page = 1
    ElMessage.success(result.message || '采编任务已创建，正在处理中')
    await loadTasks()
    scheduleTaskPolling(result.task_id, 0)
  } catch (error) {
    createError.value = String(error || '采编任务执行失败，请稍后重试')
  } finally {
    creating.value = false
  }
}

onMounted(loadTasks)
onBeforeUnmount(() => {
  pageDestroyed = true
  pollTimers.forEach((timer) => clearTimeout(timer))
  pollTimers.clear()
})
</script>

<style scoped>
.page-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; margin-bottom: 16px; }
.page-title { margin: 0; font-size: 24px; }
.page-description { margin: 6px 0 0; color: var(--color-text-muted); font-size: 14px; }
.create-card { margin-bottom: 16px; }
.search-form { display: flex; align-items: flex-end; flex-wrap: wrap; gap: 4px; }
.query-item { flex: 1; min-width: 280px; }
.query-item :deep(.el-form-item__content), .query-item :deep(.el-input) { width: 100%; }
.history-head, .history-actions { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.pagination-wrap { display: flex; justify-content: flex-end; padding-top: 16px; }
@media (max-width: 900px) {
  .page-head { align-items: stretch; flex-direction: column; }
  .search-form { align-items: stretch; }
  .query-item { flex-basis: 100%; }
  .history-head { align-items: flex-start; flex-direction: column; }
}
</style>
