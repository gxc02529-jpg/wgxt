<template>
  <div class="portal-admin">
    <h1 class="page-title">门户设置</h1>

    <!-- 首页轮播配置 -->
    <section class="panel">
      <div class="panel__head">
        <h2>首页轮播图</h2>
        <el-switch v-model="bannerModule.enabled" active-text="启用" @change="saveModule('banner')" />
      </div>
      <p class="panel__tip">配置展示在首页顶部的轮播，图片建议 16:9，可填写文章详情页链接。</p>

      <div class="banner-editor">
        <div v-for="(slide, i) in bannerSlides" :key="i" class="banner-editor__row">
          <el-input v-model="slide.title" placeholder="轮播标题" style="width: 200px" />
          <el-input v-model="slide.image" placeholder="图片 URL" style="flex: 1" />
          <el-input v-model="slide.link" placeholder="链接（如 /article/1）" style="width: 200px" />
          <el-button type="danger" plain @click="removeSlide(i)">移除</el-button>
        </div>
        <el-button type="primary" plain @click="addSlide">添加一张轮播</el-button>
      </div>
      <div class="panel__actions">
        <el-button type="primary" :loading="savingBanner" @click="saveModule('banner')">保存轮播配置</el-button>
      </div>
    </section>

    <!-- 站内公告 -->
    <section class="panel">
      <div class="panel__head">
        <h2>站内公告</h2>
        <el-switch v-model="noticeModule.enabled" active-text="启用" @change="saveModule('notice')" />
      </div>
      <el-input
        v-model="noticeText"
        type="textarea"
        :rows="3"
        maxlength="200"
        show-word-limit
        placeholder="展示在门户首页顶部的公告文本"
      />
      <div class="panel__actions">
        <el-button type="primary" :loading="savingNotice" @click="saveModule('notice')">保存公告</el-button>
      </div>
    </section>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { portalApi } from '../../api'

const bannerModule = ref({ module_key: 'banner', title: '', content: [], enabled: true })
const noticeModule = ref({ module_key: 'notice', title: '', content: '', enabled: true })
const bannerSlides = ref([])
const noticeText = ref('')
const savingBanner = ref(false)
const savingNotice = ref(false)

onMounted(async () => {
  try {
    const res = await portalApi.modules()
    const banner = res.items.find((m) => m.module_key === 'banner')
    const notice = res.items.find((m) => m.module_key === 'notice')
    if (banner) {
      bannerModule.value = banner
      bannerSlides.value = Array.isArray(banner.content) ? [...banner.content] : []
    }
    if (notice) {
      noticeModule.value = notice
      noticeText.value = typeof notice.content === 'string' ? notice.content : ''
    }
  } catch (e) {
    ElMessage.error(String(e))
  }
})

function addSlide() {
  bannerSlides.value.push({ title: '', image: '', link: '' })
}

function removeSlide(i) {
  bannerSlides.value.splice(i, 1)
}

async function saveModule(key) {
  const fn = key === 'banner' ? savingBanner : savingNotice
  fn.value = true
  try {
    if (key === 'banner') {
      const data = {
        module_key: 'banner',
        title: bannerModule.value.title,
        content: bannerSlides.value.filter((s) => s.image),
        enabled: bannerModule.value.enabled,
      }
      await portalApi.update('banner', data)
    } else {
      const data = {
        module_key: 'notice',
        title: noticeModule.value.title,
        content: noticeText.value,
        enabled: noticeModule.value.enabled,
      }
      await portalApi.update('notice', data)
    }
    ElMessage.success('保存成功')
  } catch (e) {
    ElMessage.error(String(e))
  } finally {
    fn.value = false
  }
}
</script>

<style scoped>
.page-title {
  font-size: 24px;
  margin-bottom: 16px;
}

.panel {
  background: var(--color-surface);
  border-radius: var(--radius-md);
  padding: 20px;
  box-shadow: var(--shadow-card);
  margin-bottom: 20px;
}

.panel__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 2px solid var(--color-primary);
  padding-bottom: 10px;
  margin-bottom: 12px;
}

.panel__head h2 {
  font-size: 18px;
}

.panel__tip {
  color: var(--color-text-muted);
  font-size: 13px;
  margin: 0 0 14px;
}

.banner-editor {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 14px;
}

.banner-editor__row {
  display: flex;
  gap: 10px;
}

.panel__actions {
  display: flex;
  justify-content: flex-end;
}

@media (max-width: 900px) {
  .banner-editor__row {
    flex-wrap: wrap;
  }
}
</style>

