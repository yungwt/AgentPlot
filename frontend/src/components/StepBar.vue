<script setup>
import { computed, ref } from 'vue'
import {
  NSteps,
  NStep,
  NButton,
  NProgress,
  NText,
  NCard,
  NSpace,
} from 'naive-ui'
import { useSessionStore } from '@/stores/session'
import { useJobStore } from '@/stores/job'
import * as api from '@/api'

const session = useSessionStore()
const jobs = useJobStore()

const stepDefs = [
  { name: '大纲', api: api.stepOutline, requires: () => true, completed: () => session.hasOutline },
  { name: '内容', api: api.stepContent, requires: () => session.hasOutline, completed: () => session.hasContent },
  { name: '布局', api: api.stepLayout, requires: () => session.hasContent, completed: () => session.hasLayout },
  { name: '图片', api: api.stepImages, requires: () => session.hasLayout, completed: () => session.hasImages },
  { name: 'PPT',  api: api.stepPpt,    requires: () => session.hasImages,  completed: () => session.hasPpt },
]

// 1-based: 0=初始, 1=大纲完成, ..., 5=全部完成（含 PPT）
//
// 直接采用后端给出的连续进度（session.current_step），前端不再自己按
// "hasPpt → hasImages → …" 的优先级重推一遍：那种写法只要 pptx 存在就
// 返回 5，遇到"有 pptx 但中间产物缺失"的会话会让步骤条全部显示为已完成。
const currentStep = computed(() => session.currentStep)

const activeJob = computed(() => {
  for (const id in jobs.jobs) {
    const j = jobs.jobs[id]
    if (j.status === 'pending' || j.status === 'running') return j
  }
  return null
})

// 找到第一个未完成的步骤
const nextStepDef = computed(() => {
  for (const def of stepDefs) {
    if (!def.completed()) return def
  }
  return null
})

// 未完成的剩余步骤数量
const remainingCount = computed(() => stepDefs.filter((d) => !d.completed()).length)

// 一键执行状态
const chainActive = ref(false)
const chainProgress = ref({ current: 0, total: 0, stepName: '' })

// ---------- 单步按钮 ----------
const runNextLabel = computed(() => {
  if (!session.sessionId) return '请先创建会话'
  if (chainActive.value) return '一键执行中…'
  if (activeJob.value) return '正在执行…'
  if (!nextStepDef.value) return '已完成全部步骤'
  return `执行下一步：${nextStepDef.value.name}`
})

const runNextDisabled = computed(() => {
  return !session.sessionId || !!activeJob.value || chainActive.value || !nextStepDef.value
})

const runNextType = computed(() => {
  if (!nextStepDef.value) return 'default'
  return 'primary'
})

async function onRunNext() {
  if (!nextStepDef.value || !session.sessionId) return
  await jobs.startStep(session.sessionId, nextStepDef.value.api, {
    onSuccess: () => session.refresh(),
    onError: (e) => console.error(e),
  })
}

// ---------- 一键执行按钮 ----------
const runChainLabel = computed(() => {
  if (!session.sessionId) return '一键执行'
  if (chainActive.value) return `一键执行中 (${chainProgress.value.current}/${chainProgress.value.total})`
  if (activeJob.value) return '正在执行…'
  if (!nextStepDef.value) return '全部已完成'
  return `一键执行剩余 ${remainingCount.value} 步`
})

const runChainDisabled = computed(() => {
  return !session.sessionId || !!activeJob.value || chainActive.value || !nextStepDef.value
})

const runChainType = computed(() => {
  if (chainActive.value) return 'warning'
  if (!nextStepDef.value) return 'default'
  return 'info'
})

async function onRunChain() {
  if (!session.sessionId || chainActive.value || activeJob.value || !nextStepDef.value) return

  // 快照剩余步骤，避免循环中 nextStepDef 不断变化
  const remaining = stepDefs.filter((d) => !d.completed())
  chainProgress.value = { current: 0, total: remaining.length, stepName: '' }
  chainActive.value = true

  try {
    for (let i = 0; i < remaining.length; i++) {
      const def = remaining[i]
      chainProgress.value = { current: i + 1, total: remaining.length, stepName: def.name }
      await jobs.runStep(session.sessionId, def.api)
      await session.refresh()
    }
  } catch (e) {
    console.error('chain failed:', e)
  } finally {
    chainActive.value = false
    chainProgress.value = { current: 0, total: 0, stepName: '' }
  }
}

// ---------- 进度条显示 ----------
const progressInfo = computed(() => {
  if (chainActive.value) {
    const { current, total, stepName } = chainProgress.value
    return {
      percentage: total > 0 ? Math.round((current / total) * 100) : 0,
      stage: `一键执行：${stepName} (${current}/${total})`,
    }
  }
  if (activeJob.value) {
    return {
      percentage: Math.round((activeJob.value.progress ?? 0) * 100),
      stage: activeJob.value.stage,
    }
  }
  return null
})
</script>

<template>
  <div class="stepbar">
    <n-card :bordered="false" class="bar-card">
      <div class="bar-inner">
        <n-steps :current="currentStep + 1" status="process" class="steps">
          <n-step
            v-for="(def, idx) in stepDefs"
            :key="def.name"
            :title="def.name"
          />
        </n-steps>

        <n-space :size="8" class="run-area">
          <n-button
            :type="runChainType"
            :disabled="runChainDisabled"
            :loading="chainActive"
            size="medium"
            @click="onRunChain"
          >
            {{ runChainLabel }}
          </n-button>

          <n-button
            :type="runNextType"
            :disabled="runNextDisabled"
            :loading="!!activeJob && !chainActive"
            size="medium"
            @click="onRunNext"
          >
            {{ runNextLabel }}
          </n-button>
        </n-space>
      </div>

      <div v-if="progressInfo" style="margin-top: 12px;">
        <n-progress
          :percentage="progressInfo.percentage"
          :show-indicator="true"
        />
        <n-text depth="3">{{ progressInfo.stage }}</n-text>
      </div>
    </n-card>
  </div>
</template>

<style scoped>
.stepbar {
  padding: var(--gap-md) var(--gap-lg) var(--gap-sm);
}
.bar-card {
  background: var(--card-bg);
  border: var(--card-border);
}
.bar-inner {
  display: flex;
  align-items: center;
  gap: var(--gap-lg);
}
.steps {
  flex: 1;
  min-width: 0;
}
.run-area {
  flex-shrink: 0;
}
</style>