import { defineStore } from 'pinia'
import { reactive } from 'vue'
import * as api from '@/api'

export const useJobStore = defineStore('job', () => {
  const jobs = reactive({}) // job_id -> {status, stage, progress, error, sessionId}
  const timers = reactive({}) // job_id -> intervalId

  function ensure(id, sessionId) {
    if (!jobs[id]) {
      jobs[id] = {
        status: 'pending',
        stage: '排队中',
        progress: 0,
        error: null,
        sessionId,
      }
    }
  }

  function clear(id) {
    if (timers[id]) {
      clearInterval(timers[id])
      delete timers[id]
    }
    delete jobs[id]
  }

  // 内部：清理一个 job（interval + 字典）
  function _finish(id) {
    if (timers[id]) {
      clearInterval(timers[id])
      delete timers[id]
    }
    delete jobs[id]
  }

  /**
   * 启动一个 step：triggerFn(sid) 返回 { job_id } | { skipped, reason }。
   * 之后每 1.5s 轮询一次，status=success/error 时停轮询并触发回调。
   * 后端返回 skipped（即产物已存在，无需重新生成）时，立刻触发 onSuccess。
   */
  async function startStep(sid, triggerFn, opts = {}) {
    const res = await triggerFn(sid)
    if (res && res.skipped) {
      opts.onSuccess?.()
      return { skipped: true, reason: res.reason }
    }
    const { job_id } = res
    ensure(job_id, sid)
    timers[job_id] = setInterval(async () => {
      try {
        const data = await api.getJob(sid, job_id)
        Object.assign(jobs[job_id], {
          status: data.status,
          stage: data.stage,
          progress: data.progress,
          error: data.error,
        })
        if (data.status === 'success') {
          _finish(job_id)
          opts.onSuccess?.()
        } else if (data.status === 'error') {
          _finish(job_id)
          opts.onError?.(data.error)
        }
      } catch (e) {
        _finish(job_id)
        opts.onError?.(e.message)
      }
    }, 1500)
    return { jobId: job_id }
  }

  /**
   * startStep 的 Promise 版：返回一个 Promise，在 job 完成（success/error）时 resolve/reject。
   * 用于"一键执行剩余步骤"这种需要串行等待的场景。
   * 同时把 startStep 自身抛错（triggerFn 网络失败等）也通过 reject 传出，
   * 避免链式调用卡死。
   */
  function runStep(sid, triggerFn) {
    return new Promise((resolve, reject) => {
      let resolved = false
      startStep(sid, triggerFn, {
        onSuccess: (data) => {
          resolved = true
          resolve(data)
        },
        onError: (err) => {
          resolved = true
          reject(new Error(err))
        },
      }).catch((e) => {
        if (!resolved) reject(e)
      })
    })
  }

  return { jobs, timers, startStep, clear, runStep }
})