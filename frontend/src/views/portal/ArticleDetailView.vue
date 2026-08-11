<template>
  <div class="container detail">
    <article v-loading="loading" class="detail__doc">
      <template v-if="article">
        <!-- 面包屑 -->
        <nav class="detail__crumb" aria-label="面包屑">
          <router-link to="/">首页</router-link>
          <template v-if="article.categories[0]">
            <span aria-hidden="true">/</span>
            <router-link :to="{ name: 'category', params: { slug: article.categories[0].slug } }">
              {{ article.categories[0].name }}
            </router-link>
          </template>
        </nav>

        <!-- 标题块 -->
        <header class="detail__head">
          <h1 class="detail__title">{{ article.title }}</h1>
          <p v-if="article.summary" class="detail__lead">{{ article.summary }}</p>
          <div class="detail__meta">
            <span class="detail__author">作者：{{ article.author_name }}</span>
            <span>{{ article.published_at }}</span>
            <span>{{ article.view_count }} 阅读</span>
          </div>
        </header>

        <figure v-if="article.cover_url" class="detail__cover">
          <img :src="article.cover_url" :alt="article.title" />
        </figure>

        <!-- 正文（编辑器以 HTML 形式编写，生产环境建议对 content 做 XSS 过滤） -->
        <div class="article-content detail__content" v-html="article.content"></div>

        <!-- 互动栏：点赞 / 收藏 / 转发 -->
        <footer class="detail__actions" role="group" aria-label="文稿互动">
          <button class="action-btn" :class="{ 'action-btn--active': liked }" :disabled="!auth.isLoggedIn" @click="toggleLike">
            <svg v-if="!liked" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <path d="M7 10v12M15 5.88 14 10h5.83a2 2 0 0 1 1.92 2.56l-2.33 8A2 2 0 0 1 17.5 22H4a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2h2.76a2 2 0 0 0 1.79-1.11L12 2a3.13 3.13 0 0 1 3 3.88Z" />
            </svg>
            <svg v-else viewBox="0 0 24 24" width="20" height="20" fill="currentColor" aria-hidden="true">
              <path d="M7 10v12M15 5.88 14 10h5.83a2 2 0 0 1 1.92 2.56l-2.33 8A2 2 0 0 1 17.5 22H4a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2h2.76a2 2 0 0 0 1.79-1.11L12 2a3.13 3.13 0 0 1 3 3.88Z" />
            </svg>
            <span>点赞 {{ article.like_count }}</span>
          </button>

          <button class="action-btn" :class="{ 'action-btn--active': favorited }" :disabled="!auth.isLoggedIn" @click="toggleFavorite">
            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z" />
            </svg>
            <span>收藏 {{ article.favorite_count }}</span>
          </button>

          <button class="action-btn" :disabled="!auth.isLoggedIn" @click="share">
            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <circle cx="18" cy="5" r="3" /><circle cx="6" cy="12" r="3" /><circle cx="18" cy="19" r="3" />
              <path d="m8.59 13.51 6.83 3.98M15.41 6.51l-6.82 3.98" />
            </svg>
            <span>转发 {{ article.share_count }}</span>
          </button>
        </footer>
        <p v-if="!auth.isLoggedIn" class="detail__login-tip">
          <router-link to="/login">登录</router-link> 后可点赞、收藏和转发
        </p>
      </template>
    </article>

    <!-- 相关推荐：同栏目文稿，按发布时间新到旧 -->
    <aside v-if="related.length" class="panel related">
      <h2 class="related__title">相关推荐</h2>
      <p class="related__subtitle">同栏目 · 最新发布</p>
      <ul class="related__list">
        <li v-for="a in related" :key="a.id">
          <router-link :to="{ name: 'article-detail', params: { id: a.id } }" class="related__item">
            <img
              v-if="a.cover_url"
              :src="a.cover_url"
              :alt="a.title"
              class="related__thumb"
              loading="lazy"
            />
            <span v-else class="related__thumb related__thumb--placeholder">
              {{ (a.categories[0]?.name || '文').slice(0, 1) }}
            </span>
            <span class="related__info">
              <span class="related__name">{{ a.title }}</span>
              <span class="related__meta">
                <span v-if="a.categories[0]" class="related__cat">{{ a.categories[0].name }}</span>
                <time>{{ (a.published_at || a.created_at || '').slice(0, 10) }}</time>
              </span>
            </span>
          </router-link>
        </li>
      </ul>
    </aside>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { articleApi, eventApi, interactionApi } from '../../api'
import { useAuthStore } from '../../stores/auth'

const route = useRoute()
const auth = useAuthStore()
const article = ref(null)
const related = ref([])
const loading = ref(true)
const liked = ref(false)
const favorited = ref(false)

onMounted(async () => {
  const id = Number(route.params.id)
  try {
    const [detail, statusRes] = await Promise.all([
      articleApi.detail(id),
      auth.isLoggedIn ? interactionApi.status(id) : Promise.resolve({ liked: false, favorited: false }),
    ])
    article.value = detail
    liked.value = statusRes.liked
    favorited.value = statusRes.favorited

    // 观看埋点：进入详情页即上报
    eventApi.report({ event_type: 'view', article_id: id }).catch(() => {})
    article.value.view_count += 1 // 本地乐观加一，避免刷新

    // 相关推荐：同栏目已发布文稿（后端按发布时间新到旧返回）
    const res = await articleApi.related(id, { limit: 6 })
    related.value = res.items
  } catch (e) {
    ElMessage.error(String(e))
  } finally {
    loading.value = false
  }
})

async function toggleLike() {
  try {
    const res = liked.value ? await interactionApi.unlike(article.value.id) : await interactionApi.like(article.value.id)
    liked.value = res.liked
    article.value.like_count = res.like_count ?? article.value.like_count
  } catch (e) {
    ElMessage.error(String(e))
  }
}

async function toggleFavorite() {
  try {
    const res = favorited.value
      ? await interactionApi.unfavorite(article.value.id)
      : await interactionApi.favorite(article.value.id)
    favorited.value = res.favorited
    article.value.favorite_count = res.favorite_count ?? article.value.favorite_count
  } catch (e) {
    ElMessage.error(String(e))
  }
}

async function share() {
  try {
    await interactionApi.share(article.value.id)
    article.value.share_count += 1
    // 复制链接到剪贴板（失败时降级提示）
    try {
      await navigator.clipboard.writeText(window.location.href)
      ElMessage.success('转发成功，链接已复制')
    } catch {
      ElMessage.success('转发成功')
    }
  } catch (e) {
    ElMessage.error(String(e))
  }
}
</script>

<style scoped>
/* Hallmark · genre: editorial · macrostructure: Long Document · design-system: design.md · designed-as-app */
/* Hallmark · pre-emit critique: P4 H4 E4 S4 R4 V4 */
.detail {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: var(--space-6);
  padding-top: var(--space-5);
  align-items: start;
}

.detail__doc {
  min-width: 0;
  background: var(--color-paper);
  padding: var(--space-6);
}

.detail__crumb {
  display: flex;
  gap: var(--space-2);
  font-size: var(--text-xs);
  color: var(--color-ink-3);
  margin-bottom: var(--space-5);
}

.detail__crumb a {
  /* 扩展触控热区，视觉位置不变 */
  padding: 10px 12px;
  margin: -10px -12px;
  color: var(--color-ink-3);
  transition: color var(--dur-base) var(--ease-out);
}

.detail__crumb a:hover {
  color: var(--color-accent);
}

.detail__head {
  border-bottom: var(--rule) solid var(--color-rule);
  margin-bottom: var(--space-5);
}

.detail__title {
  font-family: var(--font-heading);
  font-size: var(--text-display);
  line-height: var(--leading-tight);
  letter-spacing: var(--tracking-tight);
  color: var(--color-ink);
  margin-bottom: var(--space-4);
}

.detail__lead {
  color: var(--color-ink-2);
  font-size: var(--text-lg);
  line-height: var(--leading-normal);
  border-left: 3px solid var(--color-accent-2);
  padding-left: var(--space-4);
  margin: 0 0 var(--space-4);
}

.detail__meta {
  display: flex;
  gap: var(--space-4);
  color: var(--color-ink-3);
  font-size: var(--text-xs);
  padding-bottom: var(--space-4);
}

.detail__author {
  color: var(--color-accent);
  font-weight: 500;
}

.detail__cover {
  margin: 0 0 var(--space-5);
  border: var(--rule) solid var(--color-rule);
  border-radius: var(--radius-sm);
  overflow: hidden;
}

.detail__cover img {
  width: 100%;
  object-fit: cover;
}

.detail__content {
  max-width: var(--measure);
  color: var(--color-ink);
}

/* 长文首段首字下沉（仅当正文第一个元素是段落时生效） */
.detail__content > p:first-child::first-letter {
  font-family: var(--font-heading);
  font-size: 3.1em;
  line-height: 0.85;
  font-weight: 700;
  float: left;
  padding-right: 8px;
  color: var(--color-ink);
}

.detail__actions {
  display: flex;
  gap: var(--space-3);
  margin-top: var(--space-6);
  padding-top: var(--space-5);
  border-top: var(--rule) solid var(--color-rule);
}

.action-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  border: var(--rule) solid var(--color-rule-strong);
  background: var(--color-paper);
  color: var(--color-ink-2);
  border-radius: 999px;
  padding: 8px 18px;
  font-size: var(--text-sm);
  min-height: 40px;
  transition: border-color var(--dur-base) var(--ease-out),
    color var(--dur-base) var(--ease-out),
    background var(--dur-base) var(--ease-out);
}

.action-btn:hover:not(:disabled) {
  border-color: var(--color-accent);
  color: var(--color-accent);
}

.action-btn--active {
  background: var(--color-primary-soft);
  border-color: var(--color-accent);
  color: var(--color-accent);
  font-weight: 600;
}

.action-btn:disabled {
  opacity: 0.55;
}

.detail__login-tip {
  margin: var(--space-3) 0 0;
  font-size: var(--text-xs);
  color: var(--color-ink-3);
}

.related {
  align-self: start;
  position: sticky;
  top: 96px;
  background: var(--color-paper);
  border: var(--rule) solid var(--color-rule);
  border-radius: var(--radius-sm);
  padding: var(--space-5);
}

.related__title {
  font-family: var(--font-heading);
  font-size: var(--text-xl);
  font-weight: 700;
  color: var(--color-ink);
  padding-bottom: var(--space-3);
  border-bottom: 2px solid var(--color-ink);
  margin: 0 0 var(--space-2);
}

.related__subtitle {
  color: var(--color-ink-3);
  font-size: var(--text-xs);
  margin: 0 0 var(--space-3);
}

.related__list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.related__list li + li {
  border-top: var(--rule) solid var(--color-rule);
}

.related__item {
  display: flex;
  gap: var(--space-3);
  padding: var(--space-3) 0;
  color: var(--color-ink);
}

.related__item:hover .related__name {
  color: var(--color-accent);
}

.related__thumb {
  flex: 0 0 76px;
  width: 76px;
  height: 52px;
  border-radius: var(--radius-sm);
  object-fit: cover;
  background: var(--color-primary-soft);
}

.related__thumb--placeholder {
  display: grid;
  place-items: center;
  font-family: var(--font-heading);
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--color-accent);
}

.related__info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.related__name {
  font-size: var(--text-sm);
  line-height: var(--leading-snug);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  transition: color var(--dur-base) var(--ease-out);
}

.related__meta {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-xs);
  color: var(--color-ink-3);
}

.related__cat {
  color: var(--color-accent);
  background: var(--color-primary-soft);
  padding: 1px 8px;
  border-radius: 2px;
  font-weight: 500;
}

.related__meta time {
  flex-shrink: 0;
}

@media (max-width: 1024px) {
  .detail {
    grid-template-columns: 1fr;
  }

  .related {
    position: static;
  }
}

@media (max-width: 768px) {
  .detail__doc {
    padding: var(--space-4);
  }

  .detail__title {
    font-size: clamp(1.7rem, 8vw, 2.3rem);
  }

  .detail__actions {
    flex-wrap: wrap;
  }

  .action-btn {
    flex: 1;
    justify-content: center;
    min-height: var(--size-touch);
  }
}
</style>
