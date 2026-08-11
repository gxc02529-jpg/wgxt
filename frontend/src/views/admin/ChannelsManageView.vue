<template>
  <div class="channels-admin">
    <div class="page-head">
      <h1 class="page-title">渠道管理</h1>
      <el-button type="primary" @click="openForm()">新增渠道</el-button>
    </div>

    <el-alert
      class="channels-tip"
      type="info"
      :closable="false"
      show-icon
      title="渠道用于文稿分发：第三方平台可通过每个渠道的 RSS 链接订阅最近 7 天勾选该渠道的文稿。基础渠道（门户）所有文稿默认包含且不可删除。"
    />

    <el-table :data="channels" v-loading="loading">
      <el-table-column prop="id" label="ID" width="64" />
      <el-table-column label="名称" min-width="160">
        <template #default="{ row }">
          {{ row.name }}
          <el-tag v-if="row.is_default" size="small" type="warning">基础渠道</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="slug" label="标识" width="120" />
      <el-table-column prop="description" label="简介" min-width="220" show-overflow-tooltip />
      <el-table-column prop="article_count" label="文稿数" width="80" />
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag size="small" :type="row.status === 'active' ? 'success' : 'info'">
            {{ row.status === 'active' ? '启用' : '停用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="RSS 链接" min-width="240">
        <template #default="{ row }">
          <el-button link type="primary" @click="openRss(row)">
            {{ channelApi.rssUrl(row.id) }}
          </el-button>
          <el-button link type="success" @click="copyRss(row)">复制</el-button>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="140" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openForm(row)">编辑</el-button>
          <el-button v-if="!row.is_default" link type="danger" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="editing ? '编辑渠道' : '新增渠道'" width="480px">
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
        <el-form-item label="渠道名称" prop="name">
          <el-input v-model="form.name" maxlength="50" />
        </el-form-item>
        <el-form-item label="渠道标识（英文/数字/下划线，用于 RSS 地址）" prop="slug">
          <el-input v-model="form.slug" maxlength="50" :disabled="isDefaultEditing" />
        </el-form-item>
        <el-form-item label="渠道简介" prop="description">
          <el-input v-model="form.description" type="textarea" :rows="3" maxlength="500" show-word-limit />
        </el-form-item>
        <el-form-item label="排序（越小越靠前）">
          <el-input-number v-model="form.sort_order" :min="0" />
        </el-form-item>
        <el-form-item label="状态">
          <el-radio-group v-model="form.status" :disabled="isDefaultEditing">
            <el-radio value="active">启用</el-radio>
            <el-radio value="disabled">停用</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { channelApi } from '../../api'

const channels = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const editing = ref(null)
const saving = ref(false)
const formRef = ref()
const form = reactive({ name: '', slug: '', description: '', sort_order: 0, status: 'active' })
const isDefaultEditing = computed(() => Boolean(editing.value?.is_default))
const rules = {
  name: [{ required: true, message: '请输入渠道名称', trigger: 'blur' }],
  slug: [
    { required: true, message: '请输入渠道标识', trigger: 'blur' },
    { pattern: /^[a-zA-Z0-9_-]+$/, message: '仅支持英文、数字、下划线、短横线', trigger: 'blur' },
  ],
}

async function load() {
  loading.value = true
  try {
    const res = await channelApi.manage()
    channels.value = res.items
  } catch (e) {
    ElMessage.error(String(e))
  } finally {
    loading.value = false
  }
}

function openForm(row) {
  editing.value = row || null
  Object.assign(form, row
    ? {
        name: row.name,
        slug: row.slug,
        description: row.description || '',
        sort_order: row.sort_order,
        status: row.status,
      }
    : { name: '', slug: '', description: '', sort_order: 0, status: 'active' })
  dialogVisible.value = true
}

async function save() {
  await formRef.value.validate()
  saving.value = true
  try {
    const payload = { ...form }
    if (editing.value) {
      await channelApi.update(editing.value.id, payload)
    } else {
      await channelApi.create(payload)
    }
    ElMessage.success('保存成功')
    dialogVisible.value = false
    load()
  } catch (e) {
    ElMessage.error(String(e))
  } finally {
    saving.value = false
  }
}

async function remove(row) {
  try {
    await ElMessageBox.confirm(`确定删除渠道「${row.name}」吗？删除后将解除与文稿的关联。`, '删除确认', {
      type: 'warning',
    })
    await channelApi.remove(row.id)
    ElMessage.success('删除成功')
    load()
  } catch (e) {
    if (e !== 'cancel' && e !== 'close') ElMessage.error(String(e))
  }
}

function copyRss(row) {
  const url = channelApi.rssUrl(row.id)
  navigator.clipboard
    ?.writeText(url)
    .then(() => ElMessage.success('RSS 链接已复制'))
    .catch(() => ElMessage.error('复制失败，请手动复制'))
}

function openRss(row) {
  window.open(channelApi.rssUrl(row.id), '_blank', 'noopener')
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

.channels-tip {
  margin-bottom: 16px;
}
</style>
