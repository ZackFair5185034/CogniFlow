<template>
  <div
    class="cf-loading"
    :class="[
      `cf-loading--${size}`,
      { 'cf-loading--overlay': overlay }
    ]"
  >
    <div class="cf-loading__container">
      <div class="cf-loading__ring" />
      <p
        v-if="text"
        class="cf-loading__text"
      >
        {{ text }}
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  size?: 'small' | 'medium' | 'large'
  text?: string
  overlay?: boolean
}>(), {
  size: 'medium',
  overlay: false,
})
</script>

<style lang="scss" scoped>
.cf-loading {
  display: flex;
  align-items: center;
  justify-content: center;
}

.cf-loading--overlay {
  position: absolute;
  inset: 0;
  background: rgba(13, 13, 20, 0.85);
  z-index: 100;
}

.cf-loading__container {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

/* 认知循环 — 旋转圆环 */
.cf-loading__ring {
  border-radius: 50%;
  border-style: solid;
  border-color: var(--border-color);
  border-top-color: var(--accent-blue);
  animation: spin 0.8s linear infinite;
}

.cf-loading--small .cf-loading__ring {
  width: 16px;
  height: 16px;
  border-width: 2px;
}

.cf-loading--medium .cf-loading__ring {
  width: 24px;
  height: 24px;
  border-width: 2.5px;
}

.cf-loading--large .cf-loading__ring {
  width: 32px;
  height: 32px;
  border-width: 3px;
}

/* 文字 */
.cf-loading__text {
  font-size: 13px;
  color: var(--text-secondary);
  white-space: nowrap;
}

.cf-loading--small .cf-loading__text {
  font-size: 11px;
}
</style>
