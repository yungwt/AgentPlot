<script setup>
import { ref, watch } from 'vue'
import {
  NDrawer,
  NDrawerContent,
  NInput,
  NInputNumber,
  NButton,
  NText,
} from 'naive-ui'
import { useSessionStore } from '@/stores/session'

const props = defineProps({
  show: { type: Boolean, default: false },
})
const emit = defineEmits(['update:show'])

const store = useSessionStore()

// 抽屉里新建会话
const submitting = ref(false)
const errMsg = ref('')
async function onCreate() {
  if (!store.userRequest.trim()) return
  // n-input-number 对手敲的越界值不一定拦截，这里做客户端校验兜底
  if (
    !Number.isInteger(store.pageCount) ||
    store.pageCount < 3 ||
    store.pageCount > 10
  ) {
    errMsg.value = '内容页数需为 3–10 之间的整数'
    return
  }
  submitting.value = true
  errMsg.value = ''
  try {
    await store.create()
    emit('update:show', false)
  } catch (e) {
    errMsg.value = e?.message || '创建失败，请重试'
  } finally {
    submitting.value = false
  }
}

// 关闭时清空表单内容（避免下次打开看到上次的）
watch(
  () => props.show,
  (v) => {
    if (!v) {
      store.userRequest = ''
      store.pageCount = 3
      submitting.value = false
      errMsg.value = ''
    }
  }
)
</script>

<template>
  <n-drawer
    :show="show"
    :width="420"
    placement="right"
    @update:show="emit('update:show', $event)"
  >
    <n-drawer-content title="新建会话" closable>
      <div class="block">
        <n-text class="label">用户需求</n-text>
        <n-input
          v-model:value="store.userRequest"
          type="textarea"
          :rows="5"
          placeholder="例如：介绍 2026 年 AI Agent 的发展趋势"
        />
      </div>

      <div class="block">
        <n-text class="label">内容页数</n-text>
        <n-input-number
          v-model:value="store.pageCount"
          :min="3"
          :max="10"
          style="width: 100%"
        />
      </div>

      <n-button
        type="primary"
        block
        size="large"
        :loading="submitting"
        :disabled="!store.userRequest.trim()"
        @click="onCreate"
      >
        创建会话
      </n-button>
      <n-text v-if="errMsg" type="error" class="err">{{ errMsg }}</n-text>
    </n-drawer-content>
  </n-drawer>
</template>

<style scoped>
.block {
  margin-bottom: var(--gap-lg);
}
.label {
  display: block;
  margin-bottom: 8px;
  font-size: var(--fs-sm);
  color: var(--text-2);
}
.err {
  display: block;
  margin-top: 12px;
  font-size: var(--fs-sm);
  line-height: 1.5;
  word-break: break-all;
}
</style>
