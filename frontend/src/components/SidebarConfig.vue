<script setup>
import { ref, computed, onMounted } from 'vue'
import {
  NText,
  NButton,
  NDropdown,
  NDivider,
  NSpin,
  useDialog,
  useMessage,
} from 'naive-ui'
import { useSessionStore } from '@/stores/session'

const store = useSessionStore()
const dialog = useDialog()
const message = useMessage()

// ---------- 重置 ----------
const RESET_OPTIONS = [
  { key: 0, label: '重置到初始' },
  { key: 1, label: '重置到大纲' },
  { key: 2, label: '重置到内容' },
  { key: 3, label: '重置到布局' },
  { key: 4, label: '重置到图片' },
]

/**
 * 重置确认用居中对话框，而不是 popconfirm。
 *
 * 旧实现把 n-popconfirm 挂在一个 display:none 的 span 上当 trigger，
 * 弹层会被定位到视口左上角（实测 x=0, y=10），用户点完像"没反应"；
 * 且请求失败时没有任何提示、也不刷新状态。
 */
function onResetSelect(key) {
  const target = RESET_OPTIONS.find((o) => o.key === key)
  if (!target) return

  dialog.warning({
    title: '确认重置',
    content: `${target.label}？将删除当前及之后所有产物。`,
    positiveText: '确认重置',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await store.resetTo(target.key)
        message.success(`已${target.label}`)
      } catch (e) {
        message.error(`重置失败：${e?.message || e}`)
      } finally {
        // 删除可能是部分完成的：无论成败都重拉一次真实状态，
        // 避免侧栏 / 步骤条 / 各 Tab 停在重置前的旧状态。
        await store.refresh().catch(() => {})
      }
    },
  })
}

/**
 * 删除当前会话。后端 /api / store 都已就位，这里只补 UI 入口：
 * 居中确认（与重置同模式）+ 调 store.destroy() + 成功失败提示。
 */
async function onDelete() {
  const req = currentSession.value?.user_request || '(无描述)'
  const label = req.length > 30 ? req.slice(0, 30) + '…' : req
  dialog.warning({
    title: '确认删除会话',
    content: `确认删除"${label}"？此操作不可恢复。`,
    positiveText: '确认删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await store.destroy()
        message.success('已删除会话')
      } catch (e) {
        message.error(`删除失败：${e?.message || e}`)
      }
    },
  })
}

// ---------- 会话切换 dropdown ----------
const switching = ref(false)
const sessionOptions = computed(() => {
  const list = store.sessions
  if (!list.length) {
    return [{ key: '__empty__', label: '暂无历史会话', disabled: true }]
  }
  return list.map((s) => ({
    key: s.session_id,
    label: () => formatSessionLabel(s),
  }))
})

function formatSessionLabel(s) {
  // 简单纯文本 label（dropdown 不支持复杂渲染时用）
  const req = (s.user_request || '(无描述)').slice(0, 30)
  return `${req} · ${s.current_step_label || '未开始'}`
}

const pickerLabel = computed(() => {
  if (!store.sessionId) return '选择历史会话'
  return '切换到其他会话…'
})

async function onSwitchSelect(key) {
  if (key === '__empty__') return
  switching.value = true
  try {
    await store.switchTo(key)
  } finally {
    switching.value = false
  }
}

async function refreshHistory() {
  await store.loadHistory()
}

// ---------- 标识展示 ----------
const currentSession = computed(() => {
  // 从 sessions 列表里找当前 sid 对应的条目，读 user_request
  return store.sessions.find((s) => s.session_id === store.sessionId) || null
})

const stepItems = [
  { name: '大纲', get: () => store.hasOutline },
  { name: '内容', get: () => store.hasContent },
  { name: '布局', get: () => store.hasLayout },
  { name: '图片', get: () => store.hasImages },
  { name: 'PPT',  get: () => store.hasPpt },
]

onMounted(() => {
  if (!store.sessions.length) refreshHistory()
})
</script>

<template>
  <div class="sidebar-inner">
    <!-- 当前会话状态 -->
    <div v-if="store.sessionId">
      <n-text depth="3" class="label">当前会话</n-text>
      <div class="session-title">
        {{ currentSession?.user_request || '(无描述)' }}
      </div>

      <div class="status-block">
        <div class="status-row">
          <span class="status-label">当前步骤</span>
          <b class="status-val">{{ store.currentStepLabel }}</b>
        </div>
        <div
          v-for="item in stepItems"
          :key="item.name"
          class="status-row"
        >
          <span class="status-label">{{ item.name }}</span>
          <b :class="['status-val', item.get() ? 'done' : 'pending']">
            {{ item.get() ? '✓' : '—' }}
          </b>
        </div>
      </div>

      <n-divider />

      <!-- 重置 -->
      <n-dropdown
        :options="RESET_OPTIONS"
        trigger="click"
        @select="onResetSelect"
        placement="bottom-start"
      >
        <n-button size="small" block>重置到…</n-button>
      </n-dropdown>

      <!-- 删除当前会话（后端+store 已就位，只补 UI 入口） -->
      <n-button
        size="small"
        block
        type="error"
        ghost
        style="margin-top: 8px;"
        @click="onDelete"
      >
        删除会话
      </n-button>

      <!-- 重置二次确认走 dialog（见 onResetSelect） -->

      <n-divider />
    </div>

    <!-- 会话切换（永远可见） -->
    <n-text depth="3" class="label">会话切换</n-text>
    <n-spin :show="switching">
      <n-dropdown
        :options="sessionOptions"
        trigger="click"
        @select="onSwitchSelect"
        placement="bottom-start"
        style="display: block; margin-top: 6px;"
      >
        <n-button block size="small" :disabled="!store.sessions.length">
          {{ pickerLabel }}
        </n-button>
      </n-dropdown>
    </n-spin>
  </div>
</template>

<style scoped>
.sidebar-inner {
  padding: 16px;
}
.label {
  display: block;
  font-size: var(--fs-xs);
  color: var(--text-2);
  margin-bottom: 4px;
  letter-spacing: 0.5px;
}
.sid-tag {
  display: block;
  font-family: ui-monospace, "Consolas", monospace;
  font-size: var(--fs-xs);
  word-break: break-all;
  padding: 8px 12px;
  margin-bottom: var(--gap-sm);
}
.session-title {
  font-size: var(--fs-base);
  color: var(--text-1);
  font-weight: 500;
  line-height: 1.4;
  margin-bottom: var(--gap-sm);
  word-break: break-word;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.status-block {
  margin-top: var(--gap-xs);
}
.status-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 3px 0;
  font-size: var(--fs-sm);
}
.status-label {
  color: var(--text-2);
}
.status-val {
  color: var(--text-1);
  font-weight: 500;
}
.status-val.done {
  color: var(--success, #18a058);
}
.status-val.pending {
  color: var(--text-3);
}
</style>