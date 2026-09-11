<script setup>
import { ref } from 'vue'
import { NTabs, NTabPane, NEmpty } from 'naive-ui'
import { useSessionStore } from '@/stores/session'
import OutlineTab from './OutlineTab.vue'
import ContentTab from './ContentTab.vue'
import LayoutTab from './LayoutTab.vue'
import ImagesTab from './ImagesTab.vue'
import PptTab from './PptTab.vue'

const session = useSessionStore()
const active = ref('outline')
</script>

<template>
  <div class="tabs-wrap">
    <n-tabs v-model:value="active" type="line" animated display-directive="show:lazy">
      <n-tab-pane name="outline" tab="大纲">
        <OutlineTab v-if="session.hasOutline" />
        <n-empty v-else description="尚未生成大纲，请先执行“大纲”步骤" />
      </n-tab-pane>

      <n-tab-pane name="content" tab="内容">
        <ContentTab v-if="session.hasContent" />
        <n-empty v-else description="尚未生成内容，请先执行“内容”步骤" />
      </n-tab-pane>

      <n-tab-pane name="layout" tab="布局">
        <LayoutTab v-if="session.hasLayout" />
        <n-empty v-else description="尚未生成布局，请先执行“布局”步骤" />
      </n-tab-pane>

      <n-tab-pane name="images" tab="图片">
        <ImagesTab v-if="session.hasImages" />
        <n-empty v-else description="尚未生成图片，请先执行“图片”步骤" />
      </n-tab-pane>

      <n-tab-pane name="ppt" tab="PPT">
        <PptTab v-if="session.hasPpt" />
        <n-empty v-else description="尚未生成 PPT，请先执行“PPT”步骤" />
      </n-tab-pane>
    </n-tabs>
  </div>
</template>

<style scoped>
.tabs-wrap {
  padding: 0 var(--gap-lg) var(--gap-lg);
  flex: 1;
  overflow: auto;
}
</style>