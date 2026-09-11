<script setup>
import { ref } from 'vue'
import {
  NCard,
  NSpin,
  NEmpty,
  NText,
  NSpace,
  NButton,
  NTag,
} from 'naive-ui'
import { useSessionStore } from '@/stores/session'
import { useJobStore } from '@/stores/job'
import { useArtifact } from '@/composables/useArtifact'
import * as api from '@/api'

const session = useSessionStore()
const jobs = useJobStore()
const { data: images, loading, error, reload } = useArtifact(
  () => session.sessionId,
  () => session.hasImages,
  (sid) => api.listImages(sid),
)

const regeneratingPages = ref(new Set())
const expandedDesc = ref(new Set())

/**
 * 页码显示：0 是封面页（layout_planner 约定 封面=0，内容页从 1 开始），
 * 不能直接显示成"第 0 页"。
 */
function pageLabel(page) {
  if (page == null) return '第 ? 页'
  return page === 0 ? '封面' : `第 ${page} 页`
}

async function onRegenerate(page) {
  if (!session.sessionId || page == null) return
  regeneratingPages.value.add(page)
  await jobs.startStep(session.sessionId, (sid) => api.regenerateImage(sid, page), {
    onSuccess: async () => {
      regeneratingPages.value.delete(page)
      await session.refresh()
      await reload()
    },
    onError: (e) => {
      regeneratingPages.value.delete(page)
      error.value = e
    },
  })
}

function toggleDesc(page) {
  if (expandedDesc.value.has(page)) {
    expandedDesc.value.delete(page)
  } else {
    expandedDesc.value.add(page)
  }
}
</script>

<template>
  <div>
    <n-spin :show="loading">
      <n-empty v-if="!images?.length && !loading" description="暂无图片" />
      <n-text v-if="error" type="error">{{ error }}</n-text>

      <div class="grid">
        <n-card
          v-for="img in images ?? []"
          :key="img.filename ?? `missing-${img.page}`"
          hoverable
          :class="['card', { 'card-fail': !img.url }]"
        >
          <template #header>
            <span>{{ pageLabel(img.page) }}</span>
            <n-tag
              v-if="!img.url"
              size="small"
              type="warning"
              :bordered="false"
              style="margin-left: 8px"
            >
              未生成
            </n-tag>
            <n-tag
              v-else
              size="small"
              :bordered="false"
              style="margin-left: 8px"
            >
              {{ img.ext }}
            </n-tag>
          </template>

          <div class="img-wrap">
            <n-spin :show="regeneratingPages.has(img.page)">
              <img
                v-if="img.url"
                :src="img.url"
                class="preview-img"
                :alt="`${pageLabel(img.page)}配图`"
                draggable="false"
              />
              <div v-else class="placeholder-fail">
                <div class="placeholder-icon">!</div>
                <div class="placeholder-text">配图未生成</div>
              </div>
            </n-spin>
          </div>

          <div v-if="img.description" class="desc">
            <n-text depth="3" class="desc-label">配图描述</n-text>
            <n-text
              v-if="expandedDesc.has(img.page) || img.description.length <= 120"
              class="desc-text"
            >
              {{ img.description }}
            </n-text>
            <n-text v-else class="desc-text desc-clamp">
              {{ img.description }}
            </n-text>
            <n-button
              v-if="img.description.length > 120"
              size="tiny"
              text
              @click="toggleDesc(img.page)"
            >
              {{ expandedDesc.has(img.page) ? '收起' : '展开' }}
            </n-button>
          </div>

          <template #action>
            <n-space justify="end">
              <n-button
                size="small"
                type="primary"
                :loading="regeneratingPages.has(img.page)"
                :disabled="regeneratingPages.has(img.page) || img.page == null"
                @click="onRegenerate(img.page)"
              >
                重新生成
              </n-button>
            </n-space>
          </template>
        </n-card>
      </div>
    </n-spin>
  </div>
</template>

<style scoped>
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: var(--gap-md);
}
.card {
  background: var(--card-bg);
  border: var(--card-border);
}
.card-fail {
  border-color: rgba(255, 159, 67, 0.35);
}
.placeholder-fail {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  border: 1.5px dashed rgba(255, 159, 67, 0.35);
  border-radius: var(--radius-sm);
  background: rgba(255, 159, 67, 0.06);
  color: var(--text-2, rgba(255, 255, 255, 0.55));
}
.placeholder-icon {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: rgba(255, 159, 67, 0.18);
  color: #ff9f43;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  font-weight: bold;
}
.placeholder-text {
  font-size: 13px;
  letter-spacing: 1px;
}
.img-wrap {
  width: 100%;
  aspect-ratio: 16 / 9;
  background: var(--bg-3);
  border-radius: var(--radius-sm);
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 6px;
  box-sizing: border-box;
}
.preview-img {
  display: block;
  max-width: 100%;
  max-height: 100%;
  width: auto;
  height: auto;
  object-fit: contain;
  user-select: none;
}
.desc {
  margin-top: 10px;
  padding: var(--gap-sm) 10px;
  background: var(--bg-3);
  border-radius: var(--radius-sm);
  font-size: var(--fs-sm);
  line-height: 1.55;
}
.desc-label {
  display: block;
  font-size: var(--fs-xs);
  margin-bottom: var(--gap-xs);
  opacity: 0.6;
  letter-spacing: 0.5px;
}
.desc-text {
  white-space: pre-wrap;
  word-break: break-word;
  display: block;
}
.desc-clamp {
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
