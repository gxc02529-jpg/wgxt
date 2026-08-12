// 统一 API 定义：按模块分组，方便二次开发维护
import client from './client'

// ---- 认证与个人中心 ----
export const authApi = {
  register: (data) => client.post('/auth/register', data),
  login: (data) => client.post('/auth/login', data),
  me: () => client.get('/auth/me'),
  updateMe: (data) => client.put('/auth/me', data),
}

// ---- 栏目 ----
export const categoryApi = {
  list: () => client.get('/categories'),
  manage: () => client.get('/categories/manage'),
  create: (data) => client.post('/categories', data),
  update: (id, data) => client.put(`/categories/${id}`, data),
  remove: (id) => client.delete(`/categories/${id}`),
}

// ---- 分发渠道 ----
export const channelApi = {
  list: () => client.get('/channels'),
  manage: () => client.get('/channels/manage'),
  create: (data) => client.post('/channels', data),
  update: (id, data) => client.put(`/channels/${id}`, data),
  remove: (id) => client.delete(`/channels/${id}`),
  // RSS 订阅地址（第三方平台读取用）
  rssUrl: (id) => `${window.location.origin}/api/channels/${id}/rss`,
}

// ---- 文稿 ----
export const articleApi = {
  list: (params) => client.get('/articles', { params }),
  detail: (id) => client.get(`/articles/${id}`),
  related: (id, params) => client.get(`/articles/${id}/related`, { params }),
  mine: (params) => client.get('/articles/mine', { params }),
  adminList: (params) => client.get('/articles/admin', { params }),
  create: (data) => client.post('/articles', data),
  update: (id, data) => client.put(`/articles/${id}`, data),
  submit: (id) => client.post(`/articles/${id}/submit`),
  offline: (id) => client.post(`/articles/${id}/offline`),
  remove: (id) => client.delete(`/articles/${id}`),
}

// ---- 审核 ----
export const reviewApi = {
  pending: (params) => client.get('/reviews/pending', { params }),
  history: (params) => client.get('/reviews/history', { params }),
  review: (data) => client.post('/reviews', data),
}

// ---- 互动（点赞/收藏/转发）----
export const interactionApi = {
  like: (articleId) => client.post('/interactions/like', null, { params: { article_id: articleId } }),
  unlike: (articleId) => client.delete('/interactions/like', { params: { article_id: articleId } }),
  favorite: (articleId) => client.post('/interactions/favorite', null, { params: { article_id: articleId } }),
  unfavorite: (articleId) => client.delete('/interactions/favorite', { params: { article_id: articleId } }),
  dislike: (articleId) => client.post('/interactions/dislike', null, { params: { article_id: articleId } }),
  undislike: (articleId) => client.delete('/interactions/dislike', { params: { article_id: articleId } }),
  share: (articleId, fingerprint) =>
    client.post('/interactions/share', null, { params: { article_id: articleId, fingerprint } }),
  status: (articleId) => client.get('/interactions/status', { params: { article_id: articleId } }),
  favorites: (params) => client.get('/interactions/favorites', { params }),
}

// ---- 观看历史（记录由后端在文章详情接口中自动写入，这里只做查询）----
export const historyApi = {
  list: (params) => client.get('/history', { params }),
  reportDuration: (articleId, seconds) => client.post(`/history/${articleId}/duration`, { seconds }),
}

// ---- 后台用户行为（管理员）----
export const behaviorApi = {
  viewHistory: (params) => client.get('/admin/behavior/history', { params }),
  dislikes: (params) => client.get('/admin/behavior/dislikes', { params }),
}

// ---- 埋点 ----
export const eventApi = {
  report: (data) => client.post('/events', data),
}

// ---- 资源 ----
export const resourceApi = {
  upload: (formData) =>
    client.post('/resources/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 60000,
    }),
  // 通过线上图片链接下载入库（后端流式下载，限制大小与图片类型）
  uploadByUrl: (data) => client.post('/resources/upload-by-url', data, { timeout: 60000 }),
  list: (params) => client.get('/resources', { params }),
  remove: (id) => client.delete(`/resources/${id}`),
}

// ---- 门户模块 ----
export const portalApi = {
  modules: () => client.get('/portal/modules'),
  create: (data) => client.post('/portal/modules', data),
  update: (key, data) => client.put(`/portal/modules/${key}`, data),
  grayscale: () => client.get('/portal/grayscale'),
}

// ---- 门户主题 ----
export const themeApi = {
  get: () => client.get('/portal/theme'),
  set: (theme) => client.put('/portal/theme', { theme }),
}

// ---- 用户管理 ----
export const userApi = {
  list: (params) => client.get('/users', { params }),
  create: (data) => client.post('/users', data),
  update: (id, data) => client.put(`/users/${id}`, data),
  remove: (id) => client.delete(`/users/${id}`),
}

// ---- 统计 ----
export const statsApi = {
  overview: () => client.get('/stats/overview'),
  trends: (params) => client.get('/stats/trends', { params }),
  topArticles: (params) => client.get('/stats/articles', { params }),
  categories: (params) => client.get('/stats/categories', { params }),
  events: (params) => client.get('/stats/events', { params }),
  userActivity: (params) => client.get('/stats/user-activity', { params }),
}

// ---- 系统设置 ----
export const settingsApi = {
  list: () => client.get('/settings'),
  create: (data) => client.post('/settings', data),
  update: (key, data) => client.put(`/settings/${key}`, data),
  remove: (key) => client.delete(`/settings/${key}`),
}

// ---- Dify 工作流 ----
export const difyApi = {
  list: () => client.get('/dify/workflows'),
  create: (data) => client.post('/dify/workflows', data),
  update: (id, data) => client.put(`/dify/workflows/${id}`, data),
  remove: (id) => client.delete(`/dify/workflows/${id}`),
  run: (id, data) => client.post(`/dify/workflows/${id}/run`, data),
}

// ---- AI 协作台（写稿页 AI 辅助功能，后端当前为占位实现）----
export const aiAssistApi = {
  classify: (data) => client.post('/ai/assist/classify', data),
  summary: (data) => client.post('/ai/assist/summary', data),
  review: (data) => client.post('/ai/assist/review', data),
  check: (data) => client.post('/ai/assist/check', data),
  score: (data) => client.post('/ai/assist/score', data),
}

// ---- 后台 AI 调用记录（管理员）----
export const aiLogApi = {
  list: (params) => client.get('/admin/ai-calls', { params }),
}
