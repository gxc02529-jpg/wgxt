<template>
  <div class="resource-admin">
    <div class="page-head">
      <h1 class="page-title">资源管理</h1>
      <el-upload :show-file-list="false" :http-request="doUpload" accept="image/*,video/mp4,audio/mpeg,application/pdf">
        <el-button type="primary" :loading="uploading">上传资源</el-button>
      </el-upload>
    </div>

    <el-input
      v-model="keyword"
      placeholder="按文件名搜索"
      clearable
      style="width: 240px; margin-bottom: 14px"
      @keyup.enter="reload"
    />

    <el-table :data="resources" v-loading="loading">
      <el-table-column label="预览" width="120">
        <template #default="{ row }">
          <img
            v-if="row.file_type.startsWith('image')"
            :src="row.url"
            :alt="row.filename"
            class="thumb"
            loading="lazy"
          />
          <el-tag v-else size="small">{{ row.file_type.split('/')[1]?.toUpperCase() }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="filename" label="文件名" min-width="200" show-overflow-tooltip />
      <el-table-column prop="uploader_name" label="上传者" width="110" />
      <el-table-column prop="file_type" label="类型" width="130" />
      <el-table-column label="大小" width="100">
        <template #default="{ row }">{{ formatSize(row.file_size) }}</template>
      </el-table-column>
      <el-table-column prop="created_at" label="上传时间" width="160" />
      <el-table-column label="操作" width="140" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="copyUrl(row)">复制链接</el-button>
          <el-button link type="danger" @click="remove(row)">删除</el-button>
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
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { resourceApi } from '../../api'

const resources = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 10
const loading = ref(false)
const uploading = ref(false)
const keyword = ref('')

function formatSize(bytes) {
  if (!bytes) return '0 B'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

async function load() {
  loading.value = true
  try {
    const res = await resourceApi.list({ page: page.value, page_size: pageSize, keyword: keyword.value })
    resources.value = res.items
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

async function doUpload({ file }) {
  uploading.value = true
  const fd = new FormData()
  fd.append('file', file)
  try {
    await resourceApi.upload(fd)
    ElMessage.success('上传成功')
    load()
  } catch (e) {
    ElMessage.error(String(e))
  } finally {
    uploading.value = false
  }
}

async function copyUrl(row) {
  try {
    await navigator.clipboard.writeText(row.url)
    ElMessage.success('链接已复制')
  } catch {
    ElMessage.info(row.url)
  }
}

async function remove(row) {
  try {
    await ElMessageBox.confirm(`确定删除资源「${row.filename}」？相关引用将失效。`, '删除确认', { type: 'warning' })
    await resourceApi.remove(row.id)
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

.thumb {
  width: 80px;
  height: 50px;
  object-fit: cover;
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border);
}

.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>

