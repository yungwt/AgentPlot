/**
 * useArtifact: 通用的"读后端 artifact + 自动刷新"组合式 API。
 *
 * 4 个 Tab 组件原本各自重复 ~15 行代码：
 *   - 拿 session.sessionId / session.hasXxx
 *   - watch hasXxx 变化时 load
 *   - onMounted 跑一次 load
 *   - loading / error ref
 *
 * 用法（以 OutlineTab 为例）：
 *
 *   const { data: outline, loading, error, reload } = useArtifact(
 *     () => session.sessionId,
 *     () => session.hasOutline,
 *     (sid) => api.getOutline(sid),
 *   )
 *
 * reload 在 ImagesTab 用到（重生成单张图后手动刷新列表）。
 */
import { ref, watch, onMounted } from 'vue'

export function useArtifact(getSessionId, getReady, fetcher) {
  const data = ref(null)
  const loading = ref(false)
  const error = ref('')

  async function load() {
    const sid = getSessionId()
    if (!sid || !getReady()) {
      data.value = null
      return
    }
    loading.value = true
    error.value = ''
    try {
      data.value = await fetcher(sid)
    } catch (e) {
      error.value = e.message || String(e)
      data.value = null
    } finally {
      loading.value = false
    }
  }

  watch([getSessionId, getReady], load)
  onMounted(load)

  return { data, loading, error, reload: load }
}
