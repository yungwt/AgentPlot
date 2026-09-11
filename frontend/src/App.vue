<script setup>
import { ref } from 'vue'
import {
  darkTheme,
  zhCN,
  dateZhCN,
  NConfigProvider,
  NMessageProvider,
  NDialogProvider,
  NNotificationProvider,
  NLoadingBarProvider,
} from 'naive-ui'
import TopBar from './components/TopBar.vue'
import SidebarConfig from './components/SidebarConfig.vue'
import SideDrawer from './components/SideDrawer.vue'
import StepBar from './components/StepBar.vue'
import StepTabs from './components/StepTabs.vue'

const drawerShow = ref(false)
</script>

<template>
  <n-config-provider :theme="darkTheme" :locale="zhCN" :date-locale="dateZhCN">
    <n-loading-bar-provider>
      <n-message-provider>
        <n-notification-provider>
          <n-dialog-provider>
            <div class="app-shell">
              <TopBar @open-drawer="drawerShow = true" />
              <div class="body">
                <aside class="sidebar">
                  <SidebarConfig />
                </aside>
                <main class="main">
                  <StepBar />
                  <StepTabs />
                </main>
              </div>
              <SideDrawer v-model:show="drawerShow" />
            </div>
          </n-dialog-provider>
        </n-notification-provider>
      </n-message-provider>
    </n-loading-bar-provider>
  </n-config-provider>
</template>

<style>
.app-shell {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: var(--bg-0);
  color: var(--text-1);
}
.body {
  display: grid;
  grid-template-columns: 320px 1fr;
  flex: 1;
  min-height: 0;
}
.sidebar {
  background: var(--bg-1);
  border-right: 1px solid var(--border);
  overflow-y: auto;
}
.main {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-width: 0;
}

/* 全局：所有 n-card 加轻阴影，浮起感（不影响样式，只加 box-shadow） */
:global(.n-card) {
  box-shadow: var(--shadow-sm);
}
/* 全局：主按钮 hover 加品牌色发光圆环 */
:global(.n-button--primary-type:not(.n-button--disabled):hover) {
  box-shadow: 0 0 0 3px var(--brand-glow);
}

/* 中等花活：步骤条当前态圆圈呼吸 + 完成态绿色发光 */
@keyframes step-pulse {
  0%, 100% { box-shadow: 0 0 0 0 var(--brand-glow); }
  50%      { box-shadow: 0 0 0 6px transparent; }
}
:global(.n-step-indicator--process > .n-step-indicator-slot) {
  animation: step-pulse 1.6s ease-in-out infinite;
}
:global(.n-step-indicator--finish > .n-step-indicator-slot) {
  box-shadow: 0 0 8px var(--success-glow);
}
</style>