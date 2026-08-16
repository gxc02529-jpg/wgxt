<template>
  <el-dialog
    v-model="visible"
    class="ai-assist-dialog"
    width="min(1160px, 95vw)"
    top="4vh"
    :close-on-click-modal="false"
    :show-close="false"
    append-to-body
    destroy-on-close
  >
    <!-- 自定义头部 -->
    <template #header>
      <div class="ai-head">
        <span class="ai-head__icon" aria-hidden="true">
          <el-icon><MagicStick /></el-icon>
        </span>
        <div class="ai-head__text">
          <h2 class="ai-head__title">AI 协作台</h2>
          <p class="ai-head__sub">窗口内的修改会实时同步到写稿页面；AI 调用记录自动留存在后台</p>
        </div>
      </div>
    </template>

    <div class="ai-body">
      <!-- 左栏：文稿编辑区（与写稿页双向绑定） -->
      <section class="ai-edit">
        <div class="ai-edit__head">
          <h3 class="ai-section-title">文稿内容</h3>
          <div class="ai-tabs" role="group" aria-label="正文显示模式">
            <button
              type="button"
              class="ai-tabs__btn"
              :class="{ 'is-active': editTab === 'edit' }"
              @click="editTab = 'edit'"
            >
              编辑
            </button>
            <button
              type="button"
              class="ai-tabs__btn"
              :class="{ 'is-active': editTab === 'preview' }"
              :disabled="!hasHighlight"
              @click="editTab = 'preview'"
            >
              高亮预览
            </button>
          </div>
        </div>

        <div class="ai-field">
          <label class="ai-label" for="ai-title">标题</label>
          <el-input
            id="ai-title"
            v-model="form.title"
            maxlength="200"
            show-word-limit
            placeholder="输入文稿标题"
          />
        </div>

        <div class="ai-field">
          <label class="ai-label" for="ai-summary">摘要</label>
          <el-input
            id="ai-summary"
            v-model="form.summary"
            type="textarea"
            :rows="2"
            maxlength="500"
            show-word-limit
            placeholder="输入文稿摘要"
          />
        </div>

        <div class="ai-field">
          <label class="ai-label" for="ai-categories">栏目（可多选）</label>
          <el-select
            id="ai-categories"
            v-model="form.category_ids"
            multiple
            placeholder="选择栏目"
            class="ai-category-select"
          >
            <el-option v-for="c in categories" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </div>

        <div class="ai-field ai-field--content">
          <div class="ai-field__row">
            <label class="ai-label" for="ai-content">正文</label>
            <span v-if="highlightHint" class="ai-highlight-hint">{{ highlightHint }}</span>
          </div>
          <RichTextEditor
            v-if="editTab === 'edit'"
            v-model="form.content"
            :min-height="300"
            @text-change="onContentChange"
          />
          <div v-else class="ai-content-preview" v-html="previewHtml || escapedContent"></div>
        </div>
      </section>

      <!-- 右栏：AI 功能面板 -->
      <aside class="ai-tools">
        <div class="ai-tools__head">
          <h3 class="ai-section-title">AI 辅助功能</h3>
          <span class="ai-tools__note">占用资源，按需调用</span>
        </div>

        <!-- 1. AI 分类 -->
        <article class="ai-tool">
          <div class="ai-tool__bar">
            <span class="ai-tool__icon ai-tool__icon--violet" aria-hidden="true">
              <el-icon><Collection /></el-icon>
            </span>
            <div class="ai-tool__meta">
              <span class="ai-tool__name">AI 智能分类</span>
              <span class="ai-tool__desc">根据标题判断所属栏目并自动选中</span>
            </div>
            <el-button
              type="primary"
              size="small"
              :disabled="!canUse('classify')"
              :loading="loading.classify"
              @click="run('classify')"
            >
              调用
            </el-button>
          </div>
          <div v-if="classifyResult" class="ai-tool__result">
            <el-icon class="ai-result-icon ai-result-icon--ok"><CircleCheck /></el-icon>
            <span>识别栏目：<strong>{{ classifyResult }}</strong>（已自动选中）</span>
          </div>
          <!-- 分类纠正：AI 分类不准时手动纠正，沉淀训练数据集并立即选中正确栏目 -->
          <div v-if="classifyResult" class="ai-correction">
            <span class="ai-correction__label">分类不准？选择正确栏目：</span>
            <el-select
              v-model="correctionCategoryId"
              placeholder="选择正确栏目"
              size="small"
              class="ai-correction__select"
            >
              <el-option v-for="c in categories" :key="c.id" :label="c.name" :value="c.id" />
            </el-select>
            <el-button
              type="warning"
              size="small"
              :disabled="!correctionCategoryId"
              :loading="correcting"
              @click="submitCorrection"
            >
              纠正
            </el-button>
          </div>
        </article>

        <!-- 2. AI 生成摘要 -->
        <article class="ai-tool">
          <div class="ai-tool__bar">
            <span class="ai-tool__icon ai-tool__icon--blue" aria-hidden="true">
              <el-icon><Document /></el-icon>
            </span>
            <div class="ai-tool__meta">
              <span class="ai-tool__name">AI 生成摘要</span>
              <span class="ai-tool__desc">根据标题与正文生成一句话摘要</span>
            </div>
            <el-button
              type="primary"
              size="small"
              :disabled="!canUse('summary')"
              :loading="loading.summary"
              @click="run('summary')"
            >
              调用
            </el-button>
          </div>
          <div v-if="summaryResult" class="ai-tool__result">
            <el-icon class="ai-result-icon ai-result-icon--ok"><CircleCheck /></el-icon>
            <span>摘要已生成并回写：<strong>{{ summaryResult }}</strong></span>
          </div>
        </article>

        <!-- 3. AI 多维度审核 -->
        <article class="ai-tool">
          <div class="ai-tool__bar">
            <span class="ai-tool__icon ai-tool__icon--amber" aria-hidden="true">
              <el-icon><Warning /></el-icon>
            </span>
            <div class="ai-tool__meta">
              <span class="ai-tool__name">AI 多维度审核</span>
              <span class="ai-tool__desc">检查色情、暴力、文明用语、涉政风险</span>
            </div>
            <el-button
              type="primary"
              size="small"
              :disabled="!canUse('review')"
              :loading="loading.review"
              @click="run('review')"
            >
              调用
            </el-button>
          </div>
          <div v-if="Object.keys(reviewItems).length" class="ai-tool__result ai-review">
            <span
              v-for="(passed, name) in reviewItems"
              :key="name"
              class="ai-review__chip"
              :class="passed ? 'is-pass' : 'is-fail'"
            >
              <el-icon class="ai-review__chip-icon">
                <CircleCheck v-if="passed" />
                <CircleClose v-else />
              </el-icon>
              {{ name }}：{{ passed ? '通过' : '未通过' }}
            </span>
          </div>
        </article>

        <!-- 4. AI 内容校验 -->
        <article class="ai-tool">
          <div class="ai-tool__bar">
            <span class="ai-tool__icon ai-tool__icon--red" aria-hidden="true">
              <el-icon><EditPen /></el-icon>
            </span>
            <div class="ai-tool__meta">
              <span class="ai-tool__name">AI 内容校验</span>
              <span class="ai-tool__desc">检测错别字、标点等错误，点击可定位高亮</span>
            </div>
            <el-button
              type="primary"
              size="small"
              :disabled="!canUse('check')"
              :loading="loading.check"
              @click="run('check')"
            >
              调用
            </el-button>
          </div>
          <div v-if="checkItems.length" class="ai-tool__result ai-check">
            <button
              v-for="(item, index) in checkItems"
              :key="index"
              type="button"
              class="ai-check__item"
              :class="{ 'is-active': activeCheckIndex === index }"
              @click="locateError(index)"
            >
              <span class="ai-check__type">{{ item['错误类型'] }}</span>
              <span class="ai-check__pos">原文：{{ item['原文位置'] }}</span>
              <span class="ai-check__fix">改：{{ item['修改结果'] }}</span>
              <span class="ai-check__tip">{{ item['修改建议'] }}</span>
            </button>
          </div>
        </article>

        <!-- 5. AI 文稿打分 -->
        <article class="ai-tool">
          <div class="ai-tool__bar">
            <span class="ai-tool__icon ai-tool__icon--green" aria-hidden="true">
              <el-icon><Trophy /></el-icon>
            </span>
            <div class="ai-tool__meta">
              <span class="ai-tool__name">AI 文稿打分</span>
              <span class="ai-tool__desc">从适配度、用语规范等维度为文稿评分</span>
            </div>
            <el-button
              type="primary"
              size="small"
              :disabled="!canUse('score')"
              :loading="loading.score"
              @click="run('score')"
            >
              调用
            </el-button>
          </div>
          <div v-if="scoreItems.length" class="ai-tool__result ai-score">
            <div class="ai-score__total">
              <span class="ai-score__label">总分</span>
              <span class="ai-score__value">{{ scoreTotal }}</span>
            </div>
            <div v-for="(item, index) in scoreItems" :key="index" class="ai-score__row">
              <div class="ai-score__row-head">
                <span>{{ item['维度'] }}</span>
                <span class="ai-score__point">{{ item['得分'] }}</span>
              </div>
              <el-progress
                :percentage="scorePercent(item['得分'])"
                :show-text="false"
                :stroke-width="6"
                class="ai-score__bar"
              />
              <p class="ai-score__tip">建议：{{ item['建议'] }}</p>
            </div>
          </div>
        </article>
      </aside>
    </div>

    <template #footer>
      <el-button @click="visible = false">关闭</el-button>
      <el-button type="primary" @click="visible = false">完成</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import {
  CircleCheck, CircleClose, Collection, Document, EditPen, MagicStick, Trophy, Warning,
} from '@element-plus/icons-vue'
import { aiAssistApi, aiCorrectionApi } from '../api'
import RichTextEditor from './RichTextEditor.vue'
import { stripHtml } from '../utils/text'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  // 写稿页的 form 响应式对象：直接编辑其属性，天然双向绑定
  form: { type: Object, required: true },
  categories: { type: Array, default: () => [] },
})
const emit = defineEmits(['update:modelValue'])

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val),
})

// 各功能需要满足的输入条件
const NEEDS = {
  classify: ['title'],
  summary: ['title', 'content'],
  review: ['title', 'content'],
  check: ['content'],
  score: ['content'],
}

// 功能键→后端 feature_type 的映射（用于恢复最近一次任务）
const FEATURE_TYPE = { classify: 1, summary: 2, review: 3, check: 4, score: 5 }

const editTab = ref('edit')
const loading = reactive({ classify: false, summary: false, review: false, check: false, score: false })
const classifyResult = ref('')
const correctionCategoryId = ref(null)
const correcting = ref(false)
const summaryResult = ref('')
const reviewItems = ref([])
const checkItems = ref([])
const activeCheckIndex = ref(-1)
const scoreItems = ref([])
const scoreTotal = ref('')

// 异步任务轮询：每 2 秒一次，最长 5 分钟（当前假实现秒级完成，接入真实模型后保持即可）
const POLL_INTERVAL_MS = 2000
const POLL_MAX_TIMES = 150
let pollAbort = false

// 正文纯文本（优先用编辑器同步的 content_source，缺失时剥离 HTML，用于启用判断与高亮定位）
const contentText = computed(() => {
  const source = props.form?.content_source || ''
  return (source.trim() || stripHtml(props.form?.content || '')).trim()
})

// 弹窗内编辑器纯文本回调：同步到 content_source（写稿页编辑器同样会更新）
function onContentChange(text) {
  if (props.form) props.form.content_source = text
}

function canUse(key) {
  return NEEDS[key].every((field) => {
    if (field === 'title') return Boolean(props.form?.title?.trim())
    if (field === 'content') return contentText.value.length > 0
    return true
  })
}

function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

// 高亮预览：把正文转为纯文本，再将当前选中错误的「原文位置」包上红色 mark
const hasHighlight = computed(() => activeCheckIndex.value >= 0)
const highlightHint = computed(() => {
  if (!hasHighlight.value) return ''
  const item = checkItems.value[activeCheckIndex.value]
  if (!item) return ''
  return `已定位「${item['原文位置']}」，红色标记为错误位置`
})
const previewHtml = computed(() => {
  if (activeCheckIndex.value < 0) return ''
  const item = checkItems.value[activeCheckIndex.value]
  const pos = item?.['原文位置'] || ''
  const plain = contentText.value
  if (!pos || !plain.includes(pos)) return ''
  return escHtml(plain).split(escHtml(pos)).join(`<mark class="ai-mark">${escHtml(pos)}</mark>`)
})
const escapedContent = computed(() => escHtml(contentText.value))

function locateError(index) {
  activeCheckIndex.value = index
  const item = checkItems.value[index]
  if (!item) return
  if (!contentText.value.includes(item['原文位置'] || '')) {
    ElMessage.warning('正文中未找到该原文位置（可能已被修改）')
    return
  }
  editTab.value = 'preview'
  ElMessage.success(`已在正文中高亮「${item['原文位置']}」`)
}

function scorePercent(point) {
  const match = String(point || '').match(/(\d+)\s*\/\s*(\d+)/)
  if (!match) return 0
  return Math.round((Number(match[1]) / Number(match[2])) * 100)
}

// 提交分类纠正：保存训练样本（标题+正文+模型分类+纠正分类），并把纠正栏目选中到当前文稿
async function submitCorrection() {
  const hit = props.categories.find((c) => c.id === correctionCategoryId.value)
  if (!hit) return
  correcting.value = true
  try {
    await aiCorrectionApi.submit({
      title: props.form.title || '',
      content: contentText.value,
      model_category: classifyResult.value,
      corrected_category: hit.name,
      article_id: props.form.id || null,
      draft_key: props.form?.draft_key || null,
    })
    // 纠正结果应用到当前文稿：自动选中纠正栏目
    if (!props.form.category_ids.includes(hit.id)) props.form.category_ids.push(hit.id)
    ElMessage.success(`已纠正为「${hit.name}」并自动选中，样本已加入训练数据集`)
    correctionCategoryId.value = null
  } catch (e) {
    ElMessage.error(String(e))
  } finally {
    correcting.value = false
  }
}

function applyResult(key, data, silent = false) {
  if (key === 'classify') {
    classifyResult.value = data.category_name
    const hit = props.categories.find((c) => c.name === data.category_name)
    if (hit) {
      if (!props.form.category_ids.includes(hit.id)) props.form.category_ids.push(hit.id)
      if (!silent) ElMessage.success(`已自动选中栏目「${hit.name}」`)
    } else if (!silent) {
      ElMessage.warning(`识别到栏目「${data.category_name}」，但栏目列表中不存在`)
    }
  } else if (key === 'summary') {
    summaryResult.value = data.summary
    props.form.summary = data.summary
    if (!silent) ElMessage.success('摘要已回写到摘要输入框')
  } else if (key === 'review') {
    reviewItems.value = data
  } else if (key === 'check') {
    checkItems.value = data.items || []
    activeCheckIndex.value = -1
  } else if (key === 'score') {
    scoreItems.value = data.items || []
    scoreTotal.value = data['总分'] || ''
  }
}

async function pollTaskResult(key, taskId) {
  let data = null
  for (let i = 0; i < POLL_MAX_TIMES; i++) {
    if (pollAbort) return null
    await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS))
    if (pollAbort) return null
    const status = await aiAssistApi.getTask(taskId)
    if (status.status === 'success') {
      data = status.result
      break
    }
    if (status.status === 'failed') {
      throw new Error(status.error || 'AI 任务执行失败，请稍后重试')
    }
  }
  if (!data) throw new Error('AI 任务处理超时，可稍后在后台「AI 调用记录」中查看')
  applyResult(key, data)
  return data
}

async function run(key) {
  loading[key] = true
  pollAbort = false
  try {
    const payload = {
      title: props.form.title || '',
      summary: props.form.summary || '',
      // AI 入参使用纯文本正文（content_source），避免把 HTML 标签交给模型
      content: contentText.value,
      article_id: props.form.id || null,
      draft_key: props.form?.draft_key || null,
      category_ids: props.form.category_ids || [],
    }
    const submitRes = await aiAssistApi[key](payload)
    const taskId = submitRes?.task_id
    if (!taskId) throw new Error('AI 任务提交失败，请稍后重试')
    await pollTaskResult(key, taskId)
  } catch (e) {
    ElMessage.error(String(e))
  } finally {
    loading[key] = false
  }
}

// 重新打开弹窗时恢复最近一次任务：已成功直接回写；失败允许重调；running 继续轮询
async function restoreLatestResults() {
  // 恢复依据：已有文稿按 ID；未保存的新建草稿按 draft_key（关闭重开不丢上次结果）
  const articleId = props.form?.id || null
  const draftKey = props.form?.draft_key || null
  if (!articleId && !draftKey) return
  const running = []
  for (const [key, featureType] of Object.entries(FEATURE_TYPE)) {
    try {
      const latest = await aiAssistApi.latestTask(featureType, articleId, draftKey)
      if (latest.status === 'success') {
        applyResult(key, latest.result, true)
      } else if (latest.status === 'pending' || latest.status === 'running') {
        loading[key] = true
        running.push({ key, taskId: latest.task_id })
      }
    } catch {
      // 无历史任务，正常展示空状态
    }
  }
  await Promise.all(
    running.map(async ({ key, taskId }) => {
      try { await pollTaskResult(key, taskId) } catch { /* 错误已提示 */ } finally { loading[key] = false }
    }),
  )
}

// 每次打开弹窗时：清空临时状态后尝试恢复最近一次结果
watch(
  () => props.modelValue,
  (val) => {
    if (val) {
      pollAbort = false
      editTab.value = 'edit'
      classifyResult.value = ''
      correctionCategoryId.value = null
      summaryResult.value = ''
      reviewItems.value = []
      checkItems.value = []
      activeCheckIndex.value = -1
      scoreItems.value = []
      scoreTotal.value = ''
      Object.keys(loading).forEach((key) => { loading[key] = false })
      restoreLatestResults()
    } else {
      // 关闭弹窗：中止进行中的轮询，避免组件销毁后仍在后台查询
      pollAbort = true
    }
  },
)
</script>

<style scoped>
/* AI 协作台弹窗：flat 风格 + 项目设计令牌，左编辑 / 右 AI 功能双栏 */
.ai-assist-dialog :deep(.el-dialog) {
  border-radius: var(--radius-lg, 16px);
  overflow: hidden;
  box-shadow: var(--shadow-float, 0 10px 30px rgba(30, 41, 59, 0.12));
}

.ai-assist-dialog :deep(.el-dialog__header) {
  padding: 18px 24px;
  margin: 0;
  border-bottom: 1px solid var(--color-rule, #e2e8f0);
}

.ai-assist-dialog :deep(.el-dialog__body) {
  padding: 0;
  max-height: calc(100dvh - 220px);
  overflow: hidden;
}

.ai-assist-dialog :deep(.el-dialog__footer) {
  padding: 12px 24px;
  border-top: 1px solid var(--color-rule, #e2e8f0);
}

.ai-head {
  display: flex;
  align-items: center;
  gap: 14px;
}

.ai-head__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  flex-shrink: 0;
  border-radius: 12px;
  color: #fff;
  font-size: 22px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
}

.ai-head__title {
  margin: 0;
  font-family: var(--font-heading);
  font-size: 20px;
  font-weight: 700;
  color: var(--color-ink, #1e293b);
  line-height: 1.2;
}

.ai-head__sub {
  margin: 4px 0 0;
  font-size: 13px;
  color: var(--color-ink-3, #94a3b8);
}

.ai-body {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 400px;
  min-height: 480px;
}

/* ---- 左栏：文稿编辑 ---- */
.ai-edit {
  padding: 20px 24px;
  border-right: 1px solid var(--color-rule, #e2e8f0);
  overflow-y: auto;
  max-height: calc(100dvh - 220px);
}

.ai-edit__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
}

.ai-section-title {
  margin: 0;
  font-family: var(--font-heading);
  font-size: 15px;
  font-weight: 700;
  color: var(--color-ink, #1e293b);
}

.ai-tabs {
  display: inline-flex;
  gap: 2px;
  padding: 2px;
  background: var(--color-paper-2, #f1f5f9);
  border: 1px solid var(--color-rule, #e2e8f0);
  border-radius: 8px;
}

.ai-tabs__btn {
  border: none;
  background: transparent;
  color: var(--color-ink-2, #64748b);
  font-size: 12px;
  font-weight: 600;
  min-height: 28px;
  padding: 0 14px;
  border-radius: 6px;
  cursor: pointer;
  transition: background-color 150ms cubic-bezier(0.16, 1, 0.3, 1),
    color 150ms cubic-bezier(0.16, 1, 0.3, 1);
}

.ai-tabs__btn:hover:not(:disabled) {
  color: var(--color-ink, #1e293b);
}

.ai-tabs__btn:focus-visible {
  outline: 2px solid var(--color-primary, #2563eb);
  outline-offset: 1px;
}

.ai-tabs__btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.ai-tabs__btn.is-active {
  background: var(--color-surface, #fff);
  color: var(--color-primary, #2563eb);
  box-shadow: 0 1px 3px rgba(30, 41, 59, 0.08);
}

.ai-field {
  margin-bottom: 14px;
}

.ai-label {
  display: block;
  margin-bottom: 6px;
  font-size: 13px;
  font-weight: 600;
  color: var(--color-ink-2, #64748b);
}

.ai-field__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.ai-highlight-hint {
  font-size: 12px;
  color: var(--color-danger, #dc2626);
}

.ai-category-select {
  width: 100%;
}

.ai-content-preview {
  min-height: 240px;
  border: 1px solid var(--color-rule, #e2e8f0);
  border-radius: var(--radius-sm, 6px);
  padding: 12px 14px;
  background: var(--color-paper, #fff);
  color: var(--color-ink, #1e293b);
  font-size: 14px;
  line-height: var(--leading-normal, 1.6);
  white-space: pre-wrap;
  word-break: break-word;
  overflow-y: auto;
  max-height: 300px;
}

/* 错误高亮标记 */
.ai-content-preview :deep(.ai-mark) {
  background: rgba(220, 38, 38, 0.16);
  color: #b91c1c;
  font-weight: 700;
  padding: 0 2px;
  border-radius: 3px;
  box-shadow: 0 0 0 1px rgba(220, 38, 38, 0.35);
}

/* ---- 右栏：AI 功能面板 ---- */
.ai-tools {
  padding: 20px 20px 24px;
  background: var(--color-paper-2, #f8fafc);
  overflow-y: auto;
  max-height: calc(100dvh - 220px);
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.ai-tools__head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 2px;
}

.ai-tools__note {
  font-size: 12px;
  color: var(--color-ink-3, #94a3b8);
}

.ai-tool {
  background: var(--color-surface, #fff);
  border: 1px solid var(--color-rule, #e2e8f0);
  border-radius: 12px;
  padding: 12px 14px;
  transition: border-color 150ms cubic-bezier(0.16, 1, 0.3, 1),
    box-shadow 150ms cubic-bezier(0.16, 1, 0.3, 1);
}

.ai-tool:hover {
  border-color: var(--color-rule-strong, #cbd5e1);
  box-shadow: 0 2px 8px rgba(30, 41, 59, 0.05);
}

.ai-tool__bar {
  display: flex;
  align-items: center;
  gap: 10px;
}

.ai-tool__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  flex-shrink: 0;
  border-radius: 10px;
  font-size: 18px;
}

.ai-tool__icon--violet { background: #ede9fe; color: #7c3aed; }
.ai-tool__icon--blue { background: #dbeafe; color: #2563eb; }
.ai-tool__icon--amber { background: #fef3c7; color: #d97706; }
.ai-tool__icon--red { background: #fee2e2; color: #dc2626; }
.ai-tool__icon--green { background: #dcfce7; color: #16a34a; }

.ai-tool__meta {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
  flex: 1;
}

.ai-tool__name {
  font-size: 13px;
  font-weight: 700;
  color: var(--color-ink, #1e293b);
}

.ai-tool__desc {
  font-size: 12px;
  color: var(--color-ink-3, #94a3b8);
  line-height: 1.4;
}

.ai-tool :deep(.el-button) {
  flex-shrink: 0;
  min-height: 32px;
}

.ai-tool__result {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px dashed var(--color-rule, #e2e8f0);
  font-size: 12px;
  line-height: 1.5;
  color: var(--color-ink-2, #64748b);
}

.ai-result-icon {
  flex-shrink: 0;
  margin-top: 2px;
}

.ai-result-icon--ok {
  color: var(--color-success, #16a34a);
}

/* 分类纠正区 */
.ai-correction {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px dashed var(--color-rule, #e2e8f0);
  flex-wrap: wrap;
}

.ai-correction__label {
  font-size: 12px;
  color: var(--color-ink-2, #64748b);
}

.ai-correction__select {
  width: 140px;
  flex-shrink: 0;
}

/* 审核结果 chips */
.ai-review {
  flex-wrap: wrap;
}

.ai-review__chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
}

.ai-review__chip-icon {
  font-size: 13px;
}

.ai-review__chip.is-pass {
  background: #dcfce7;
  color: #15803d;
}

.ai-review__chip.is-fail {
  background: #fee2e2;
  color: #b91c1c;
}

/* 校验错误列表 */
.ai-check {
  flex-direction: column;
  width: 100%;
}

.ai-check__item {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
  width: 100%;
  text-align: left;
  border: 1px solid var(--color-rule, #e2e8f0);
  border-radius: 8px;
  background: var(--color-paper, #fff);
  padding: 8px 10px;
  font-size: 12px;
  color: var(--color-ink-2, #64748b);
  cursor: pointer;
  transition: border-color 150ms cubic-bezier(0.16, 1, 0.3, 1),
    background-color 150ms cubic-bezier(0.16, 1, 0.3, 1);
}

.ai-check__item:hover {
  border-color: var(--color-danger, #dc2626);
}

.ai-check__item:focus-visible {
  outline: 2px solid var(--color-danger, #dc2626);
  outline-offset: 1px;
}

.ai-check__item.is-active {
  border-color: var(--color-danger, #dc2626);
  background: #fef2f2;
}

.ai-check__type {
  font-weight: 700;
  color: var(--color-danger, #dc2626);
}

.ai-check__pos,
.ai-check__fix {
  color: var(--color-ink, #1e293b);
}

.ai-check__tip {
  color: var(--color-ink-3, #94a3b8);
}

/* 打分结果 */
.ai-score {
  flex-direction: column;
  width: 100%;
}

.ai-score__total {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 8px;
}

.ai-score__label {
  font-size: 12px;
  color: var(--color-ink-3, #94a3b8);
}

.ai-score__value {
  font-family: var(--font-heading);
  font-size: 26px;
  font-weight: 800;
  color: var(--color-primary, #2563eb);
  line-height: 1;
}

.ai-score__row {
  margin-bottom: 8px;
}

.ai-score__row-head {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: var(--color-ink-2, #64748b);
  margin-bottom: 4px;
}

.ai-score__point {
  font-weight: 700;
  color: var(--color-ink, #1e293b);
  font-variant-numeric: tabular-nums;
}

.ai-score__bar :deep(.el-progress-bar__outer) {
  background: var(--color-rule, #e2e8f0);
}

.ai-score__tip {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--color-ink-3, #94a3b8);
}

/* ---- 响应式 ---- */
@media (max-width: 900px) {
  .ai-body {
    grid-template-columns: 1fr;
  }

  .ai-edit {
    border-right: none;
    border-bottom: 1px solid var(--color-rule, #e2e8f0);
    max-height: none;
  }
}
</style>