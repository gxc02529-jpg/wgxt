<template>
  <div class="article-edit">
    <div class="page-head">
      <h1 class="page-title">{{ isEdit ? '编辑文稿' : '写新文稿' }}</h1>
      <div>
        <el-button @click="router.push('/admin/articles')">返回列表</el-button>
        <el-button type="primary" :loading="saving" @click="save(false)">保存草稿</el-button>
        <el-button type="warning" :loading="submitting" @click="save(true)">提交审核</el-button>
      </div>
    </div>

    <el-form ref="formRef" :model="form" :rules="rules" label-position="top" class="edit-form">
      <el-form-item label="标题" prop="title">
        <el-input v-model="form.title" maxlength="200" show-word-limit placeholder="请输入文稿标题" />
      </el-form-item>

      <div class="form-row">
        <el-form-item label="所属栏目（可多选）" prop="category_ids" class="form-row__item">
          <el-select v-model="form.category_ids" multiple placeholder="选择栏目" style="width: 100%">
            <el-option v-for="c in categories" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="城市（同城搜索使用）" class="form-row__item">
          <el-select
            v-model="form.city"
            placeholder="选择城市（留空表示全国/不限定）"
            clearable
            filterable
            allow-create
            default-first-option
            style="width: 100%"
          >
            <el-option v-for="c in cityPreset" :key="c" :label="c" :value="c" />
          </el-select>
        </el-form-item>
      </div>

      <div class="form-row">
        <el-form-item label="摘要" class="form-row__item">
          <el-input v-model="form.summary" maxlength="500" show-word-limit type="textarea" :rows="2" placeholder="一句话摘要，展示在列表页" />
        </el-form-item>
        <el-form-item label="封面图（从资源库选择）" class="form-row__item">
          <ResourcePicker v-model="form.cover_url" />
        </el-form-item>
      </div>

      <el-form-item label="正文内容（支持 HTML）">
        <div class="editor-toolbar">
          <el-button size="small" @click="previewMode = !previewMode">
            {{ previewMode ? '编辑模式' : '预览模式' }}
          </el-button>
        </div>
        <el-input
          v-if="!previewMode"
          v-model="form.content"
          type="textarea"
          :rows="14"
          placeholder="支持 HTML 标签，如 &lt;p&gt;段落&lt;/p&gt;、&lt;img src=&quot;资源URL&quot;&gt;"
        />
        <div v-else class="content-preview article-content" v-html="form.content || '<p style=&quot;color:#94a3b8&quot;>暂无内容</p>'"></div>
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { articleApi, categoryApi } from '../../api'
import { CITY_PRESET } from '../../stores/city'
import ResourcePicker from '../../components/ResourcePicker.vue'

const route = useRoute()
const router = useRouter()
const isEdit = Boolean(route.params.id)
const formRef = ref()
const categories = ref([])
const saving = ref(false)
const submitting = ref(false)
const previewMode = ref(false)
const cityPreset = CITY_PRESET

const form = reactive({
  title: '',
  summary: '',
  cover_url: '',
  category_ids: [],
  city: '',
  content: '',
})

const rules = {
  title: [{ required: true, message: '请输入标题', trigger: 'blur' }],
  category_ids: [{ required: true, type: 'array', min: 1, message: '请至少选择一个栏目', trigger: 'change' }],
}

onMounted(async () => {
  try {
    const catRes = await categoryApi.list()
    categories.value = catRes.items
    if (isEdit) {
      const detail = await articleApi.detail(route.params.id)
      Object.assign(form, {
        title: detail.title,
        summary: detail.summary,
        cover_url: detail.cover_url,
        content: detail.content || '',
        category_ids: detail.categories.map((c) => c.id),
        city: detail.city || '',
      })
    }
  } catch (e) {
    ElMessage.error(String(e))
  }
})

async function save(submitReview) {
  await formRef.value.validate()
  if (submitReview && !form.content.trim()) {
    ElMessage.warning('正文不能为空')
    return
  }
  const fn = submitReview ? submitting : saving
  fn.value = true
  try {
    const payload = {
      title: form.title,
      summary: form.summary,
      cover_url: form.cover_url,
      content: form.content,
      category_ids: form.category_ids,
      city: form.city || '',
    }
    const res = isEdit
      ? await articleApi.update(route.params.id, payload)
      : await articleApi.create(payload)
    const id = res.article?.id
    if (submitReview) {
      await articleApi.submit(id)
      ElMessage.success('已提交审核（待一审）')
    } else {
      ElMessage.success('草稿已保存')
    }
    router.push('/admin/articles')
  } catch (e) {
    ElMessage.error(String(e))
  } finally {
    fn.value = false
  }
}
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

.edit-form {
  background: var(--color-surface);
  border-radius: var(--radius-md);
  padding: 24px;
  box-shadow: var(--shadow-card);
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.editor-toolbar {
  margin-bottom: 8px;
}

.content-preview {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  padding: 16px;
  min-height: 220px;
}

@media (max-width: 768px) {
  .form-row {
    grid-template-columns: 1fr;
  }
}
</style>

