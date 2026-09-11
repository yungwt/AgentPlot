import axios from 'axios'

const http = axios.create({
  baseURL: '/',
  timeout: 0, // 长步骤不超时
})

http.interceptors.response.use(
  (resp) => resp.data,
  (err) => {
    // FastAPI 的 detail 可能是字符串，也可能是 422 的对象数组
    const detail = err?.response?.data?.detail
    let msg
    if (typeof detail === 'string') {
      msg = detail
    } else if (Array.isArray(detail)) {
      msg = detail
        .map((e) => `${(e.loc || []).slice(1).join('.') || '参数'}: ${e.msg}`)
        .join('；')
    } else {
      msg = err?.message || '请求失败'
    }
    return Promise.reject(new Error(msg))
  },
)

// ---- sessions ----
export const createSession = (user_request, page_count) =>
  http.post('/api/sessions', { user_request, page_count })

export const listSessions = () => http.get('/api/sessions')

export const getSession = (session_id) =>
  http.get(`/api/sessions/${session_id}`)

export const deleteSession = (session_id) =>
  http.delete(`/api/sessions/${session_id}`)

export const resetSession = (session_id, target_step) =>
  http.post(`/api/sessions/${session_id}/reset`, null, {
    params: { target_step },
  })

// ---- steps ----
export const stepOutline = (sid) => http.post(`/api/sessions/${sid}/steps/outline`)
export const stepContent = (sid) => http.post(`/api/sessions/${sid}/steps/content`)
export const stepLayout = (sid) => http.post(`/api/sessions/${sid}/steps/layout`)
export const stepImages = (sid) => http.post(`/api/sessions/${sid}/steps/images`)
export const stepPpt = (sid) => http.post(`/api/sessions/${sid}/steps/ppt`)

// ---- jobs ----
export const getJob = (sid, jid) => http.get(`/api/sessions/${sid}/jobs/${jid}`)

// ---- artifacts ----
export const getOutline = (sid) => http.get(`/api/sessions/${sid}/outline`)
export const getContent = (sid) => http.get(`/api/sessions/${sid}/content`)
export const getLayout = (sid) => http.get(`/api/sessions/${sid}/layout`)
export const listImages = (sid) => http.get(`/api/sessions/${sid}/images`)

export const getPptUrl = (sid) => `/api/sessions/${sid}/ppt`

// ---- image single-page ----
export const regenerateImage = (sid, page) =>
  http.post(`/api/sessions/${sid}/images/${page}/regenerate`)

export const deleteImage = (sid, page) =>
  http.delete(`/api/sessions/${sid}/images/${page}`)