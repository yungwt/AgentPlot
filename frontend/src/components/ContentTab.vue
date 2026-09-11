<script setup>
import { NCard, NSpin, NEmpty, NText, NSpace, NTag } from 'naive-ui'
import { useSessionStore } from '@/stores/session'
import { useArtifact } from '@/composables/useArtifact'
import * as api from '@/api'

const session = useSessionStore()
const { data: content, loading, error } = useArtifact(
  () => session.sessionId,
  () => session.hasContent,
  (sid) => api.getContent(sid),
)
</script>

<template>
  <div>
    <n-spin :show="loading">
      <n-empty v-if="!content && !loading" description="暂无数据" />
      <n-text v-if="error" type="error">{{ error }}</n-text>

      <div v-if="content" class="grid">
        <n-card
          v-for="slide in content.slides ?? []"
          :key="slide.page_number"
          :title="`第 ${slide.page_number} 页`"
          hoverable
          class="card"
        >
          <template #header-extra>
            <n-tag size="small" :bordered="false">{{ slide.subtitle || '内容' }}</n-tag>
          </template>
          <div class="slide-title">{{ slide.title }}</div>
          <n-space vertical size="small" style="margin-top: 12px">
            <div
              v-for="(p, i) in slide.paragraphs ?? []"
              :key="i"
              class="para"
            >
              <n-tag size="tiny" :bordered="false" type="info">{{ p.type }}</n-tag>
              <n-text class="para-text">{{ p.text }}</n-text>
            </div>
          </n-space>
        </n-card>
      </div>
    </n-spin>
  </div>
</template>

<style scoped>
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: var(--gap-md);
}
.card {
  background: var(--card-bg);
  border: var(--card-border);
}
.slide-title {
  font-size: var(--fs-lg);
  font-weight: 600;
}
.para {
  display: flex;
  gap: var(--gap-sm);
  align-items: flex-start;
}
.para-text {
  font-size: var(--fs-base);
  line-height: 1.5;
}
</style>