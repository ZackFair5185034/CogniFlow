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
// UNOCSS-EXCEPTION: 4) 后代选择器修饰子元素
// 尺寸变体只能靠后代选择器 (.cf-loading--small .cf-loading__ring)，utility 表达不了
// @keyframes spin 复用 src/style/_animations.scss:31，不重复定义
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

.cf-loading--small .cf-loading__text {
  font-size: 11px;
}
</style>
