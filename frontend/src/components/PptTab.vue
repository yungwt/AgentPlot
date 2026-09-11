<script setup>
import { computed } from 'vue'
import { NCard, NEmpty, NButton, NSpace, NText } from 'naive-ui'
import { useSessionStore } from '@/stores/session'
import * as api from '@/api'

const session = useSessionStore()

const pptUrl = computed(() =>
  session.sessionId ? api.getPptUrl(session.sessionId) : ''
)
</script>

<template>
  <div>
    <n-empty
      v-if="!session.hasPpt"
      description="尚未生成 PPT，请先执行“PPT”步骤"
    />
    <n-card v-else :bordered="false" class="card">
      <n-space vertical size="medium">
        <n-text strong style="font-size: 16px">演示文稿已生成</n-text>
        <n-space>
          <n-button
            type="primary"
            tag="a"
            :href="pptUrl"
            download="presentation.pptx"
          >
            下载 PPT
          </n-button>
          <n-button tag="a" :href="pptUrl" target="_blank">
            在浏览器打开
          </n-button>
        </n-space>
      </n-space>
    </n-card>
  </div>
</template>

<style scoped>
.card {
  background: #20222a;
}
</style>