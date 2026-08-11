<template>
  <div class="category-admin">
    <div class="page-head">
      <h1 class="page-title">栏目管理</h1>
      <el-button type="primary" @click="openForm()">新增栏目</el-button>
    </div>

    <el-table :data="categories" v-loading="loading">
      <el-table-column prop="id" label="ID" width="64" />
      <el-table-column prop="name" label="名称" width="140" />
      <el-table-column prop="slug" label="标识" width="140" />
      <el-table-column prop="description" label="简介" min-width="240" show-overflow-tooltip />
      <el-table-column prop="sort_order" label="排序" width="80" />
      <el-table-column prop="article_count" label="文稿数" width="90" />
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag size="small" :type="row.status === 'active' ? 'success' : 'info'">
            {{ row.status === 'active' ? '启用' : '隐藏' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="140" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openForm(row)">编辑</el-button>
          <el-button link type="danger" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="editing ? '编辑栏目' : '新增栏目'" width="480px">
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
        <el-form-item label="栏目名称" prop="name">
          <el-input v-model="form.name" maxlength="50" />
        </el-form-item>
        <el-form-item label="栏目标识（英文/数字/下划线，用于网址）" prop="slug">
          <el-input v-model="form.slug" maxlength="50" :disabled="Boolean(editing)" />
        </el-form-item>
        <el-form-item label="栏目简介" prop="description">
          <el-input v-model="form.description" type="textarea" :rows="3" maxlength="500" show-word-limit />
        </el-form-item>
        <el-form-item label="排序（越小越靠前）">
          <el-input-number v-model="form.sort_order" :min="0" />
        </el-form-item>
        <el-form-item label="状态">
          <el-radio-group v-model="form.status">
            <el-radio value="active">启用</el-radio>
            <el-radio value="hidden">隐藏</el-radio>
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
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { categoryApi } from '../../api'

const categories = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const editing = ref(null)
const saving = ref(false)
const formRef = ref()
const form = reactive({ name: '', slug: '', description: '', sort_order: 0, status: 'active' })
const rules = {
  name: [{ required: true, message: '请输入栏目名称', trigger: 'blur' }],
  slug: [
    { required: true, message: '请输入栏目标识', trigger: 'blur' },
    { pattern: /^[a-zA-Z0-9_-]+$/, message: '仅支持英文、数字、下划线、短横线', trigger: 'blur' },
  ],
}

async function load() {
  loading.value = true
  try {
    const res = await categoryApi.manage()
    categories.value = res.items
  } catch (e) {
    ElMessage.error(String(e))
  } finally {
    loading.value = false
  }
}

function openForm(row) {
  editing.value = row || null
  Object.assign(form, row ? {
    name: row.name,
    slug: row.slug,
    description: row.description || '',
    sort_order: row.sort_order,
    status: row.status,
  } : { name: '', slug: '', description: '', sort_order: 0, status: 'active' })
  dialogVisible.value = true
}

async function save() {
  await formRef.value.validate()
  saving.value = true
  try {
    if (editing.value) {
      await categoryApi.update(editing.value.id, form)
      ElMessage.success('保存成功')
    } else {
      await categoryApi.create(form)
      ElMessage.success('创建成功')
    }
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
    await ElMessageBox.confirm(`确定删除栏目「${row.name}」？该栏目下的文稿关联将被解除。`, '删除确认', { type: 'warning' })
    await categoryApi.remove(row.id)
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
</style>

