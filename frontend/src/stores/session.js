import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as api from '@/api'

export const useSessionStore = defineStore('session', () => {
  const sessionId = ref('')
  const session = ref(null) // 整个后端返回对象
  const userRequest = ref('')
  const pageCount = ref(3)

  const hasOutline = computed(() => session.value?.has_outline ?? false)
  const hasContent = computed(() => session.value?.has_content ?? false)
  const hasLayout = computed(() => session.value?.has_layout ?? false)
  const hasImages = computed(() => session.value?.has_images ?? false)
  const hasPpt = computed(() => session.value?.has_ppt ?? false)
  const currentStep = computed(() => session.value?.current_step ?? 0)
  const currentStepLabel = computed(
    () => session.value?.current_step_label ?? '未开始'
  )

  async function create() {
    const data = await api.createSession(userRequest.value, pageCount.value)
    sessionId.value = data.session_id
    session.value = data
    // 刷新历史列表：让上一个（以及本次）会话立刻出现在切换下拉里，
    // 否则新建后旧会话要等下次 loadHistory 才能切回去。
    await loadHistory()
    return data
  }

  async function refresh() {
    if (!sessionId.value) return
    session.value = await api.getSession(sessionId.value)
  }

  async function resetTo(target) {
    if (!sessionId.value) return
    session.value = await api.resetSession(sessionId.value, target)
  }

  async function destroy() {
    if (!sessionId.value) return
    const sid = sessionId.value
    await api.deleteSession(sid)
    sessionId.value = ''
    session.value = null
    // 删完顺手刷一下历史列表，避免死链
    await loadHistory()
  }

  // 历史会话列表 + 切换
  const sessions = ref([])
  async function loadHistory() {
    sessions.value = await api.listSessions()
  }
  async function switchTo(sid) {
    if (!sid || sid === sessionId.value) return
    sessionId.value = sid
    await refresh()
  }

  return {
    sessionId,
    session,
    userRequest,
    pageCount,
    hasOutline,
    hasContent,
    hasLayout,
    hasImages,
    hasPpt,
    currentStep,
    currentStepLabel,
    create,
    refresh,
    resetTo,
    destroy,
    sessions,
    loadHistory,
    switchTo,
  }
})