<script setup>
const emit = defineEmits(['open-drawer'])
</script>

<template>
  <header class="topbar">
    <div class="brand">
      <span class="brand-logo">AgentPlot</span>
    </div>

    <div class="spacer"></div>

    <div class="actions">
      <n-button type="primary" @click="emit('open-drawer')">
        + 新建会话
      </n-button>
    </div>
  </header>
</template>

<style scoped>
.topbar {
  display: flex;
  align-items: center;
  gap: var(--gap-lg);
  padding: 10px 20px;
  background: var(--bg-1);
  border-bottom: 1px solid var(--border);
  height: 56px;
}
.brand {
  display: flex;
  align-items: baseline;
  gap: 10px;
}
.brand-logo {
  font-size: var(--fs-xl);
  font-weight: 800;
  letter-spacing: 0.5px;
  background: var(--brand-gradient);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
.spacer {
  flex: 1;
}
.actions {
  display: flex;
  gap: var(--gap-sm);
}
</style>