<template>
  <!-- 资源选择器：从资源库选择图片作为封面，支持上传新资源 -->
  <div class="resource-picker">
    <div v-if="modelValue" class="resource-picker__preview">
      <img :src="modelValue" alt="当前封面预览" />
      <button type="button" class="resource-picker__remove" aria-label="移除封面" @click="$emit('update:modelValue', '')">×</button>
    </div>
    <el-button type="primary" plain @click="open">选择图片</el-button>

    <el-dialog v-model="visible" title="选择资源" width="720px" top="6vh">
      <div class="resource-picker__toolbar">
        <el-upload
          :show-file-list="false"
          :http-request="doUpload"
          accept="image/*"
        >
          <el-button type="primary" :loading="uploading">上传新图片</el-button>
        </el-upload>
      </div>

      <div v-loading="loading" class="resource-picker__grid">
        <button
          v-for="r in resources"
          :key="r.id"
          type="button"
          class="resource-picker__item"
          :class="{ 'is-selected': modelValue === r.url }"
          @click="choose(r.url)"
        >
          <img :src="r.url" :alt="r.filename" loading="lazy" />
          <span>{{ r.filename }}</span>
        </button>
        <el-empty v-if="!loading && !resources.length" description="暂无资源，请先上传" />
      </div>

      <div class="resource-picker__pager">
        <el-pagination
          layout="prev, pager, next"
          :total="total"
          :page-size="pageSize"
          :current-page="page"
          @current-change="load"
        />
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { resourceApi } from '../api'

const props = defineProps({
  modelValue: { type: String, default: '' },
})
const emit = defineEmits(['update:modelValue'])

const visible = ref(false)
const resources = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 12
const loading = ref(false)
const uploading = ref(false)

async function load(p) {
  if (p) page.value = p
  loading.value = true
  try {
    const res = await resourceApi.list({ page: page.value, page_size: pageSize })
    resources.value = res.items
    total.value = res.total
  } catch (e) {
    ElMessage.error(String(e))
  } finally {
    loading.value = false
  }
}

async function doUpload({ file }) {
  uploading.value = true
  const fd = new FormData()
  fd.append('file', file)
  try {
    await resourceApi.upload(fd)
    ElMessage.success('上传成功')
    load(1)
  } catch (e) {
    ElMessage.error(String(e))
  } finally {
    uploading.value = false
  }
}

function choose(url) {
  emit('update:modelValue', url)
  visible.value = false
}

function open() {
  visible.value = true
  load(1)
}
</script>

<style scoped>
.resource-picker {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.resource-picker__preview {
  position: relative;
  width: 160px;
  aspect-ratio: 16 / 10;
  border-radius: var(--radius-sm);
  overflow: hidden;
  border: 1px solid var(--color-border);
}

.resource-picker__preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.resource-picker__remove {
  position: absolute;
  top: 4px;
  right: 4px;
  width: 24px;
  height: 24px;
  border: none;
  border-radius: 50%;
  background: rgba(15, 23, 42, 0.65);
  color: #fff;
  line-height: 1;
}

.resource-picker__toolbar {
  margin-bottom: 14px;
}

.resource-picker__grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  min-height: 120px;
}

.resource-picker__item {
  border: 2px solid var(--color-border);
  border-radius: var(--radius-sm);
  padding: 6px;
  background: var(--color-surface);
  overflow: hidden;
}

.resource-picker__item.is-selected {
  border-color: var(--color-primary);
  background: var(--color-primary-soft);
}

.resource-picker__item img {
  width: 100%;
  aspect-ratio: 16 / 10;
  object-fit: cover;
  border-radius: 4px;
  margin-bottom: 6px;
}

.resource-picker__item span {
  display: block;
  font-size: 12px;
  color: var(--color-text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.resource-picker__pager {
  display: flex;
  justify-content: center;
  margin-top: 14px;
}
</style>
