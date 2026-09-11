<script setup>
import {
  NCard,
  NSpin,
  NEmpty,
  NText,
  NSpace,
  NTag,
  NCollapse,
  NCollapseItem,
} from 'naive-ui'
import { useSessionStore } from '@/stores/session'
import { useArtifact } from '@/composables/useArtifact'
import * as api from '@/api'

const session = useSessionStore()
const { data: layout, loading, error } = useArtifact(
  () => session.sessionId,
  () => session.hasLayout,
  (sid) => api.getLayout(sid),
)

function pre(slide) {
  return JSON.stringify(slide, null, 2)
}

function layoutTypeLabel(type) {
  return {
    cover: '封面',
    content: '内容',
    section: '分节',
    summary: '总结',
    closing: '结语',
    agenda: '目录',
  }[type] || type
}

function layoutTitle(slide) {
  // 封面页不参与页码编号，避免和首页内容重复
  if (slide.layout_type === 'cover') return '封面'
  return `第 ${slide.page_number} 页 · ${layoutTypeLabel(slide.layout_type)}`
}
</script>

<template>
  <div>
    <n-spin :show="loading">
      <n-empty v-if="!layout && !loading" description="暂无数据" />
      <n-text v-if="error" type="error">{{ error }}</n-text>

      <div v-if="layout" class="grid">
        <n-card
          v-for="slide in layout.slides ?? []"
          :key="slide.page_number"
          :title="layoutTitle(slide)"
          hoverable
          class="card"
        >
          <template #header-extra>
            <n-tag size="small" :bordered="false" type="info">{{ slide.page_type }}</n-tag>
          </template>

          <n-space size="small" style="margin-bottom: 8px">
            <n-tag size="small" :bordered="false">背景: {{ slide.background_color }}</n-tag>
            <n-tag size="small" :bordered="false">文本块: {{ (slide.text_blocks ?? []).length }}</n-tag>
            <n-tag
              v-if="slide.image"
              size="small"
              type="success"
              :bordered="false"
            >
              图片: {{ slide.image.chart_type }}
            </n-tag>
            <n-tag
              v-if="(slide.decorations ?? []).length"
              size="small"
              :bordered="false"
            >
              装饰: {{ slide.decorations.length }}
            </n-tag>
          </n-space>

          <div v-if="slide.image" class="img-desc">
            <n-text depth="3">{{ slide.image.description }}</n-text>
          </div>

          <n-collapse style="margin-top: 8px">
            <n-collapse-item title="查看完整 JSON" name="json">
              <pre class="json">{{ pre(slide) }}</pre>
            </n-collapse-item>
          </n-collapse>
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
.img-desc {
  font-size: var(--fs-base);
  line-height: 1.5;
  padding: 8px 0;
}
.json {
  font-size: var(--fs-xs);
  background: var(--bg-3);
  padding: var(--gap-sm);
  border-radius: var(--radius-sm);
  overflow-x: auto;
  max-height: 240px;
  margin: 0;
}
</style>