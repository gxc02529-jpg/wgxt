<template>
  <div class="settings-page">
    <div class="admin-head">
      <span class="admin-head__icon">
        <el-icon><Setting /></el-icon>
      </span>
      <div class="admin-head__text">
        <h1 class="admin-head__title">系统设置</h1>
        <p class="admin-head__sub">功能开关与全局配置项管理</p>
      </div>
    </div>

    <!-- 功能设置：注册开放 + 对象存储 -->
    <div class="admin-card">
      <div class="table-toolbar">
        <span class="settings-group">功能设置</span>
      </div>
      <div class="settings-list">
        <div class="settings-row">
          <div class="settings-row__info">
            <div class="settings-row__title">注册成为编辑</div>
            <p class="settings-row__desc">开启后用户可直接注册为编辑写手；关闭后编辑账号仅可在后台创建</p>
          </div>
          <div class="settings-row__control">
            <el-switch
              v-model="registerEditorEnabled"
              active-text="开启"
              inactive-text="关闭"
              @change="saveRegisterEditor"
            />
          </div>
        </div>

        <div class="settings-row">
          <div class="settings-row__info">
            <div class="settings-row__title">对象存储（OSS）</div>
            <p class="settings-row__desc">
              endpoint 留空时上传到本地服务器；配置后新上传文件写入 S3 兼容对象存储（bucket 需公开读）
            </p>
          </div>
          <div class="settings-row__control">
            <span class="status-badge" :class="ossConfigured ? 'status-badge--blue' : 'status-badge--gray'">
              {{ ossConfigured ? '已启用' : '本地存储' }}
            </span>
            <el-button type="primary" plain size="small" @click="openOssDialog">配置</el-button>
          </div>
        </div>
      </div>
    </div>

    <!-- 其他配置：新增配置键后自动按值类型渲染 -->
    <div class="admin-card">
      <div class="table-toolbar">
        <span class="settings-group">其他配置</span>
      </div>
      <el-skeleton v-if="loading" :rows="3" animated class="settings-skeleton" />
      <el-empty v-else-if="!otherSettings.length" description="暂无其他配置项" />
      <div v-for="s in otherSettings" :key="s.config_key" class="settings-row">
        <div class="settings-row__info">
          <div class="settings-row__title">{{ s.description || s.config_key }}</div>
          <code class="settings-row__key">{{ s.config_key }}</code>
        </div>
        <div class="settings-row__control">
          <el-switch
            v-if="s.value_type === 'bool'"
            v-model="s.value"
            active-text="开启"
            inactive-text="关闭"
            @change="saveSetting(s)"
          />
          <el-input-number v-else-if="s.value_type === 'int'" v-model="s.value" />
          <el-input
            v-else-if="s.value_type === 'json'"
            v-model="s.editable"
            type="textarea"
            :rows="4"
            class="settings-row__input"
          />
          <el-input v-else v-model="s.value" class="settings-row__input" />
          <el-button
            v-if="s.value_type !== 'bool'"
            type="primary"
            size="small"
            :loading="s.saving"
            @click="saveSetting(s)"
          >
            保存
          </el-button>
        </div>
      </div>
    </div>

    <!-- 对象存储配置弹窗 -->
    <el-dialog v-model="ossDialogVisible" title="对象存储（OSS）配置" width="560px" destroy-on-close>
      <el-alert
        type="info"
        :closable="false"
        show-icon
        title="支持阿里云 OSS、腾讯云 COS、MinIO、AWS S3 等；bucket 需设置为公开读"
        class="oss-dialog__tip"
      />
      <el-form label-position="top">
        <div class="oss-form__grid">
          <el-form-item label="Endpoint（服务地址）">
            <el-input v-model="ossForm.endpoint" placeholder="如 https://oss-cn-hangzhou.aliyuncs.com 或 http://127.0.0.1:9000" />
          </el-form-item>
          <el-form-item label="Bucket（存储桶）">
            <el-input v-model="ossForm.bucket" placeholder="需允许公开读" />
          </el-form-item>
          <el-form-item label="Region">
            <el-input v-model="ossForm.region" placeholder="默认 us-east-1（MinIO 可随意）" />
          </el-form-item>
          <el-form-item label="Access Key">
            <el-input v-model="ossForm.access_key" placeholder="Access Key" />
          </el-form-item>
          <el-form-item label="Secret Key">
            <el-input v-model="ossForm.secret_key" type="password" show-password placeholder="已设置显示 ****，留空保留原值" />
          </el-form-item>
          <el-form-item label="Path Prefix（可选）">
            <el-input v-model="ossForm.path_prefix" placeholder="如 articles/" />
          </el-form-item>
          <el-form-item label="公开访问前缀（可选）" class="oss-form__wide">
            <el-input
              v-model="ossForm.public_base_url"
              placeholder="留空按 endpoint/bucket/key 拼接；虚拟主机风格或 CDN 时填写完整前缀"
            />
          </el-form-item>
        </div>
      </el-form>
      <template #footer>
        <el-button v-if="ossConfigured" @click="clearOssConfig">清空（切回本地）</el-button>
        <el-button @click="ossDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingOss" @click="saveOssConfig">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Setting } from '@element-plus/icons-vue'
import { portalApi, settingsApi } from '../../api'

// 功能设置里单独管理的配置键（从「其他配置」自动渲染列表中排除，避免重复）
const MANAGED_KEYS = ['register_editor_enabled', 'oss_config']

const settings = ref([])
const loading = ref(true)
const otherSettings = computed(() => settings.value.filter((s) => !MANAGED_KEYS.includes(s.config_key)))

// 注册为编辑的开放策略
const registerEditorEnabled = ref(true)

// S3 兼容对象存储配置
const ossConfigured = ref(false)
const ossDialogVisible = ref(false)
const savingOss = ref(false)
const ossForm = ref({
  endpoint: '', bucket: '', region: '', access_key: '', secret_key: '', path_prefix: '', public_base_url: '',
})

onMounted(async () => {
  try {
    const res = await settingsApi.list()
    settings.value = res.items.map((s) => ({
      ...s,
      // JSON 类型以文本形式编辑，保存时再解析
      editable:
        s.value_type === 'json' && s.value !== null && typeof s.value === 'object'
          ? JSON.stringify(s.value, null, 2)
          : String(s.value ?? ''),
      saving: false,
    }))
  } catch (e) {
    ElMessage.error(String(e))
  } finally {
    loading.value = false
  }
  try {
    const res = await portalApi.registerEditor()
    registerEditorEnabled.value = res.enabled
  } catch {
    // 拉取失败按开启处理
  }
  try {
    const res = await portalApi.ossConfig()
    ossConfigured.value = res.configured
    ossForm.value = { ...res.config }
  } catch {
    // 拉取失败按本地模式处理
  }
})

async function saveSetting(s) {
  let value = s.value
  if (s.value_type === 'json') {
    try {
      value = JSON.parse(s.editable || 'null')
    } catch {
      ElMessage.error('JSON 格式不正确，请检查后重试')
      return
    }
  }
  s.saving = true
  try {
    await settingsApi.update(s.config_key, { value, value_type: s.value_type })
    ElMessage.success(`「${s.description || s.config_key}」已保存`)
  } catch (e) {
    ElMessage.error(String(e))
  } finally {
    s.saving = false
  }
}

// 保存注册为编辑的开放策略
async function saveRegisterEditor() {
  try {
    await portalApi.setRegisterEditor(registerEditorEnabled.value)
    ElMessage.success(registerEditorEnabled.value ? '已开放编辑注册' : '已关闭编辑注册')
  } catch (e) {
    registerEditorEnabled.value = !registerEditorEnabled.value
    ElMessage.error(String(e))
  }
}

function openOssDialog() {
  ossDialogVisible.value = true
}

// 保存 OSS 配置（secret_key 传 **** 保留原值，传空清空）
async function saveOssConfig() {
  savingOss.value = true
  try {
    const res = await portalApi.setOssConfig(ossForm.value)
    ossConfigured.value = res.configured
    ossForm.value = { ...res.config }
    ossDialogVisible.value = false
    ElMessage.success(res.configured ? 'OSS 配置已保存，新上传文件将写入对象存储' : '已切换为本地存储')
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '保存失败')
  } finally {
    savingOss.value = false
  }
}

// 清空 OSS 配置，切回本地存储
async function clearOssConfig() {
  try {
    await ElMessageBox.confirm('清空后将恢复为本地存储，已上传到 OSS 的文件不会自动迁移。确定清空吗？', '提示', {
      type: 'warning',
    })
  } catch {
    return
  }
  ossForm.value = {
    endpoint: '', bucket: '', region: '', access_key: '', secret_key: '', path_prefix: '', public_base_url: '',
  }
  await saveOssConfig()
}
</script>

<style scoped>
.settings-group {
  font-weight: 600;
  color: var(--color-text);
  font-size: 14px;
}

.settings-list {
  padding: 0 16px;
}

.settings-skeleton {
  padding: 16px;
}

.settings-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 0;
  border-bottom: 1px solid var(--color-border);
}

.settings-row:last-child {
  border-bottom: none;
}

.settings-row__info {
  min-width: 0;
}

.settings-row__title {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 3px;
}

.settings-row__desc {
  margin: 0;
  font-size: 12px;
  color: var(--color-text-muted);
  line-height: 1.6;
}

.settings-row__key {
  font-size: 12px;
  color: var(--color-text-muted);
}

.settings-row__control {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.settings-row__input {
  width: 320px;
}

/* ---- OSS 配置弹窗 ---- */
.oss-dialog__tip {
  margin-bottom: 14px;
}

.oss-form__grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0 16px;
}

.oss-form__wide {
  grid-column: 1 / -1;
}

@media (max-width: 720px) {
  .settings-row {
    flex-direction: column;
    align-items: stretch;
  }

  .settings-row__control {
    justify-content: flex-end;
  }

  .settings-row__input {
    width: 100%;
  }

  .oss-form__grid {
    grid-template-columns: 1fr;
  }
}
</style>
