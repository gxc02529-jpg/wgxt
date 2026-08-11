<template>
  <div class="settings-page">
    <el-card shadow="never">
      <template #header>
        <div class="settings-header">
          <span class="settings-header__title">系统设置</span>
          <span class="settings-header__tip">
            新增配置键后，此处会自动按值类型渲染对应控件（开关 / 数字 / 输入框 / JSON）
          </span>
        </div>
      </template>

      <el-skeleton v-if="loading" :rows="3" animated />
      <el-empty v-else-if="!settings.length" description="暂无配置项" />

      <div v-for="s in settings" :key="s.config_key" class="setting-row">
        <div class="setting-row__info">
          <div class="setting-row__title">{{ s.description || s.config_key }}</div>
          <code class="setting-row__key">{{ s.config_key }}</code>
        </div>
        <div class="setting-row__control">
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
            class="setting-row__input"
          />
          <el-input v-else v-model="s.value" class="setting-row__input" />
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
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { settingsApi } from '../../api'

const settings = ref([])
const loading = ref(true)

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
</script>

<style scoped>
.settings-header {
  display: flex;
  align-items: baseline;
  gap: 12px;
}

.settings-header__title {
  font-size: 15px;
  font-weight: 600;
}

.settings-header__tip {
  font-size: 12px;
  color: var(--color-text-muted);
}

.setting-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 0;
  border-bottom: 1px solid var(--color-border);
}

.setting-row:last-child {
  border-bottom: none;
}

.setting-row__title {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 4px;
}

.setting-row__key {
  font-size: 12px;
  color: var(--color-text-muted);
}

.setting-row__control {
  display: flex;
  align-items: center;
  gap: 10px;
}

.setting-row__input {
  width: 320px;
}
</style>
