<script setup>
import { NCard, NSpin, NEmpty, NText, NSpace, NTag } from 'naive-ui'
import { useSessionStore } from '@/stores/session'
import { useArtifact } from '@/composables/useArtifact'
import * as api from '@/api'

const session = useSessionStore()
const { data: outline, loading, error } = useArtifact(
  () => session.sessionId,
  () => session.hasOutline,
  (sid) => api.getOutline(sid),
)
</script>

<template>
  <div>
    <n-spin :show="loading">
      <n-empty v-if="!outline && !loading" description="暂无数据" />
      <n-text v-if="error" type="error">{{ error }}</n-text>

      <div v-if="outline" class="grid">
        <n-card
          v-for="(slide, idx) in outline.slides ?? []"
          :key="idx"
          :title="`第 ${idx + 1} 页`"
          hoverable
          class="card"
        >
          <div class="slide-title">{{ slide.title }}</div>
          <n-text depth="3" class="slide-desc">
            {{ slide.subtitle ?? '' }}
          </n-text>
          <n-space
            v-if="slide.bullet_points?.length"
            style="margin-top: 8px"
            size="small"
          >
            <n-tag
              v-for="(kp, i) in slide.bullet_points"
              :key="i"
              size="small"
              type="info"
              :bordered="false"
            >
              {{ kp }}
            </n-tag>
          </n-space>
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
.slide-title {
  font-size: var(--fs-lg);
  font-weight: 600;
  margin-bottom: 6px;
}
.slide-desc {
  font-size: var(--fs-base);
  line-height: 1.5;
}
</style>