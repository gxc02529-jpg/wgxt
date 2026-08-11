<template>
  <div class="container home">
    <!-- 页面唯一主标题（屏幕阅读器） -->
    <h1 class="sr-only">文稿发布首页</h1>

    <!-- 站内公告 -->
    <div v-if="notice" class="notice" role="status">
      <span class="notice__label">公告</span>
      <span class="notice__text">{{ notice }}</span>
    </div>

    <!-- 头条：优先管理员配置的轮播，未配置则展示热门文稿 -->
    <section class="lead" aria-label="头条区域">
      <el-carousel v-if="bannerItems.length" height="380px" class="lead__carousel" :interval="5000">
        <el-carousel-item v-for="(item, i) in bannerItems" :key="i">
          <a :href="item.link || '#'" class="lead__slide">
            <img :src="item.image" :alt="item.title" />
            <div class="lead__mask">
              <h2>{{ item.title }}</h2>
            </div>
          </a>
        </el-carousel-item>
      </el-carousel>

      <article v-else-if="hotArticles[0]" class="lead__story">
        <router-link
          :to="{ name: 'article-detail', params: { id: hotArticles[0].id } }"
          class="lead__link"
        >
          <div class="lead__text">
            <span class="lead__kicker">头条</span>
            <h2 class="lead__title">{{ hotArticles[0].title }}</h2>
            <p v-if="hotArticles[0].summary" class="lead__summary">{{ hotArticles[0].summary }}</p>
            <p class="lead__meta">
              <span>{{ hotArticles[0].author_name }}</span>
              <span>{{ (hotArticles[0].published_at || hotArticles[0].created_at || '').slice(0, 10) }}</span>
              <span>{{ hotArticles[0].view_count }} 阅读</span>
            </p>
          </div>
          <img
            v-if="hotArticles[0].cover_url"
            :src="hotArticles[0].cover_url"
            :alt="hotArticles[0].title"
            class="lead__cover"
          />
          <span v-else class="lead__cover lead__cover--placeholder">
            {{ (hotArticles[0].categories[0]?.name || '文').slice(0, 1) }}
          </span>
        </router-link>
      </article>
    </section>

    <div class="home__grid">
      <!-- 左侧：最新发布 -->
      <section class="index-section">
        <div class="index-section__head">
          <h2>最新发布</h2>
          <router-link to="/search" class="index-section__more">更多 ›</router-link>
        </div>
        <ul class="story-list">
          <li v-for="a in latestArticles" :key="a.id" class="story-list__item">
            <router-link
              :to="{ name: 'article-detail', params: { id: a.id } }"
              class="story-list__link"
            >
              <span v-if="a.categories[0]" class="story-list__tag">{{ a.categories[0].name }}</span>
              <span class="story-list__title">{{ a.title }}</span>
              <span class="story-list__time">{{ (a.published_at || a.created_at || '').slice(0, 10) }}</span>
            </router-link>
          </li>
        </ul>
      </section>

      <!-- 右侧：热门排行 -->
      <aside class="index-section">
        <div class="index-section__head">
          <h2>热门排行</h2>
        </div>
        <ol class="rank-list">
          <li v-for="(a, i) in hotArticles" :key="a.id">
            <router-link :to="{ name: 'article-detail', params: { id: a.id } }">
              <span class="rank-list__no" :class="{ 'rank-list__no--top': i < 3 }">
                {{ String(i + 1).padStart(2, '0') }}
              </span>
              <span class="rank-list__title">{{ a.title }}</span>
              <span class="rank-list__views">{{ a.view_count }} 阅读</span>
            </router-link>
          </li>
        </ol>
      </aside>
    </div>

    <!-- 栏目分区 -->
    <section v-for="cat in sectionCategories" :key="cat.id" class="section">
      <div class="section__head">
        <div class="section__head-text">
          <h2>{{ cat.name }}</h2>
          <p v-if="cat.description" class="section__desc">{{ cat.description }}</p>
        </div>
        <router-link :to="{ name: 'category', params: { slug: cat.slug } }" class="section__more">
          更多 ›
        </router-link>
      </div>
      <div class="section__grid">
        <ArticleCard v-for="a in sectionArticles[cat.id] || []" :key="a.id" :article="a" />
      </div>
      <div v-if="!(sectionArticles[cat.id] || []).length" class="empty">该栏目暂无已发布文稿</div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { articleApi, categoryApi, portalApi } from '../../api'
import ArticleCard from '../../components/ArticleCard.vue'

const modules = ref([])
const latestArticles = ref([])
const hotArticles = ref([])
const categories = ref([])
const sectionArticles = ref({})

const notice = computed(() => {
  const m = modules.value.find((x) => x.module_key === 'notice')
  return m && typeof m.content === 'string' ? m.content : ''
})

const bannerItems = computed(() => {
  const m = modules.value.find((x) => x.module_key === 'banner')
  return Array.isArray(m?.content) ? m.content : []
})

const sectionCategories = computed(() => categories.value.slice(0, 4))

onMounted(async () => {
  try {
    const [moduleRes, latestRes, hotRes, catRes] = await Promise.all([
      portalApi.modules(),
      articleApi.list({ sort: 'latest', page_size: 8 }),
      articleApi.list({ sort: 'hot', page_size: 6 }),
      categoryApi.list(),
    ])
    modules.value = moduleRes.items
    latestArticles.value = latestRes.items
    hotArticles.value = hotRes.items
    categories.value = catRes.items

    // 并行加载每个栏目分区的最新文稿
    const sections = await Promise.all(
      sectionCategories.value.map(async (cat) => {
        const res = await articleApi.list({ category_id: cat.id, sort: 'latest', page_size: 4 })
        return [cat.id, res.items]
      }),
    )
    sectionArticles.value = Object.fromEntries(sections)
  } catch (e) {
    ElMessage.error(String(e))
  }
})
</script>

<style scoped>
/* Hallmark · genre: editorial · macrostructure: Front Page · design-system: design.md · designed-as-app */
/* Hallmark · pre-emit critique: P4 H4 E4 S4 R4 V4 */
.home {
  padding-top: var(--space-5);
}

.notice {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  border: var(--rule) solid var(--color-rule);
  border-left: 3px solid var(--color-accent-2);
  background: var(--color-accent-2-soft);
  padding: 10px var(--space-4);
  margin-bottom: var(--space-5);
  font-size: var(--text-sm);
}

.notice__label {
  flex-shrink: 0;
  background: var(--color-accent-2);
  color: #fff;
  font-size: var(--text-xs);
  padding: 2px 10px;
  border-radius: 2px;
  font-weight: 600;
}

.lead {
  margin-bottom: var(--space-6);
}

.lead__carousel {
  border-radius: var(--radius-md);
  overflow: hidden;
  border: var(--rule) solid var(--color-rule);
}

.lead__slide {
  position: relative;
  display: block;
  height: 100%;
}

.lead__slide img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.lead__mask {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: flex-end;
  padding: var(--space-6);
  background: linear-gradient(180deg, rgba(15, 23, 42, 0) 35%, rgba(15, 23, 42, 0.82));
  color: #fff;
}

.lead__mask h2 {
  font-family: var(--font-heading);
  font-size: clamp(1.5rem, 3vw + 0.5rem, 2.25rem);
  line-height: var(--leading-tight);
}

.lead__story {
  border: var(--rule) solid var(--color-rule);
  background: var(--color-paper);
}

.lead__link {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(0, 1fr);
  gap: var(--space-6);
  padding: var(--space-6);
  align-items: stretch;
}

.lead__text {
  display: flex;
  flex-direction: column;
  justify-content: center;
  min-width: 0;
}

.lead__kicker {
  align-self: flex-start;
  font-size: var(--text-xs);
  font-weight: 700;
  letter-spacing: 0.12em;
  color: var(--color-accent-2);
  border-bottom: 2px solid var(--color-accent-2);
  padding-bottom: 4px;
  margin-bottom: var(--space-4);
}

.lead__title {
  font-family: var(--font-heading);
  font-size: var(--text-display);
  line-height: var(--leading-tight);
  letter-spacing: var(--tracking-tight);
  color: var(--color-ink);
  transition: color var(--dur-base) var(--ease-out);
}

.lead__link:hover .lead__title {
  color: var(--color-accent);
}

.lead__summary {
  color: var(--color-ink-2);
  font-size: var(--text-lg);
  line-height: var(--leading-normal);
  margin: var(--space-4) 0 0;
}

.lead__meta {
  display: flex;
  gap: var(--space-4);
  margin: var(--space-4) 0 0;
  font-size: var(--text-xs);
  color: var(--color-ink-3);
}

.lead__cover {
  width: 100%;
  height: 100%;
  min-height: 240px;
  object-fit: cover;
  border-radius: var(--radius-sm);
  align-self: center;
}

.lead__cover--placeholder {
  display: grid;
  place-items: center;
  font-family: var(--font-heading);
  font-size: 4rem;
  font-weight: 700;
  color: var(--color-accent);
  background: var(--color-primary-soft);
}

.home__grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 340px;
  gap: var(--space-6);
  margin-bottom: var(--space-6);
}

.index-section__head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--space-3);
  border-bottom: 2px solid var(--color-ink);
  padding-bottom: var(--space-2);
  margin-bottom: var(--space-3);
}

.index-section__head h2 {
  font-family: var(--font-heading);
  font-size: var(--text-2xl);
  font-weight: 700;
  color: var(--color-ink);
}

.index-section__more {
  font-size: var(--text-xs);
  color: var(--color-ink-3);
  transition: color var(--dur-base) var(--ease-out);
}

.index-section__more:hover {
  color: var(--color-accent);
}

.story-list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.story-list__item + .story-list__item {
  border-top: var(--rule) solid var(--color-rule);
}

.story-list__link {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) 0;
  color: var(--color-ink);
  font-size: var(--text-base);
}

.story-list__tag {
  flex-shrink: 0;
  font-size: var(--text-xs);
  color: var(--color-accent);
  background: var(--color-primary-soft);
  padding: 2px 8px;
  border-radius: 2px;
}

.story-list__title {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-family: var(--font-heading);
  font-weight: 600;
  transition: color var(--dur-base) var(--ease-out);
}

.story-list__link:hover .story-list__title {
  color: var(--color-accent);
}

.story-list__time {
  flex-shrink: 0;
  color: var(--color-ink-3);
  font-size: var(--text-xs);
}

.rank-list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.rank-list li + li {
  border-top: var(--rule) solid var(--color-rule);
}

.rank-list a {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) 0;
  color: var(--color-ink);
  font-size: var(--text-sm);
}

.rank-list__no {
  flex-shrink: 0;
  font-family: var(--font-heading);
  font-size: var(--text-2xl);
  font-weight: 700;
  color: var(--color-rule-strong);
  line-height: 1;
  min-width: 34px;
}

.rank-list__no--top {
  color: var(--color-accent-2);
}

.rank-list__title {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  transition: color var(--dur-base) var(--ease-out);
}

.rank-list a:hover .rank-list__title {
  color: var(--color-accent);
}

.rank-list__views {
  flex-shrink: 0;
  color: var(--color-ink-3);
  font-size: var(--text-xs);
}

.section {
  margin-bottom: var(--space-6);
}

.section__head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--space-3);
  border-bottom: 2px solid var(--color-ink);
  padding-bottom: var(--space-2);
  margin-bottom: var(--space-3);
}

.section__head-text {
  display: flex;
  align-items: baseline;
  gap: var(--space-3);
  min-width: 0;
}

.section__head h2 {
  font-family: var(--font-heading);
  font-size: var(--text-2xl);
  font-weight: 700;
  color: var(--color-ink);
}

.section__desc {
  color: var(--color-ink-3);
  font-size: var(--text-xs);
  margin: 0;
}

.section__more {
  font-size: var(--text-xs);
  color: var(--color-ink-3);
  transition: color var(--dur-base) var(--ease-out);
}

.section__more:hover {
  color: var(--color-accent);
}

.section__grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 var(--space-6);
}

.empty {
  color: var(--color-ink-3);
  text-align: center;
  padding: var(--space-6) 0;
  font-size: var(--text-sm);
}

@media (max-width: 1024px) {
  .home__grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .index-section__more,
  .section__more {
    min-width: var(--size-touch);
    display: inline-flex;
    align-items: center;
    justify-content: flex-end;
  }

  .lead__link {
    grid-template-columns: 1fr;
    gap: var(--space-4);
    padding: var(--space-4);
  }

  .lead__cover {
    min-height: 180px;
  }

  .section__grid {
    grid-template-columns: 1fr;
  }

  .lead__title {
    font-size: clamp(1.6rem, 8vw, 2.2rem);
  }
}
</style>
