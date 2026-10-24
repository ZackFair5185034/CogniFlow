<!-- -*- coding: utf-8 -*- -->
<!--
  节点图例 - 说明分类色板与端口类型。

  2026-10-24: 画布此前没有任何图例, 用户看不出节点顶条/图标的颜色代表什么分类,
  也不知道端口小圆点的颜色对应哪种数据类型。
-->
<script setup lang="ts">
import { ref } from 'vue'
import { LEGEND_CATEGORIES, LEGEND_PORT_TYPES } from './legendMeta'

/** 是否折叠 —— 竖向空间紧张时只留标题条 */
const collapsed = ref(false)
</script>

<template>
  <div class="node-legend ui-card">
    <button
      class="legend-toggle"
      :title="collapsed ? '展开图例' : '折叠图例'"
      @click="collapsed = !collapsed"
    >
      <span class="legend-title-main">图例</span>
      <SvgIcon
        :name="collapsed ? 'chevron-left' : 'chevron-down'"
        class="legend-caret"
      />
    </button>

    <template v-if="!collapsed">
      <div class="legend-section">
        <span class="legend-title">节点分类</span>
        <span
          v-for="cat in LEGEND_CATEGORIES"
          :key="cat.key"
          class="legend-item"
        >
          <i
            class="legend-dot"
            :style="{ background: `var(--cat-${cat.key})` }"
          />
          {{ cat.label }}
        </span>
      </div>
      <div class="legend-section">
        <span class="legend-title">端口类型</span>
        <span
          v-for="port in LEGEND_PORT_TYPES"
          :key="port.type"
          class="legend-item legend-port"
        >
          <code>{{ port.type }}</code>
          {{ port.label }}
        </span>
      </div>
    </template>
  </div>
</template>

<style scoped lang="scss">
.node-legend {
  @apply flex flex-col gap-2 p-3 text-xs;
}
.legend-toggle {
  @apply flex items-center justify-between gap-2 w-full;
  @apply text-xs font-semibold cursor-pointer;
  color: var(--text-muted);
}
.legend-title-main {
  @apply font-semibold;
}
.legend-caret {
  @apply w-3 h-3;
}
.legend-section {
  @apply flex flex-wrap items-center gap-2;
}
.legend-title {
  @apply font-semibold text-[var(--text-muted)] mr-1;
}
.legend-item {
  @apply flex items-center gap-1;
}
.legend-dot {
  @apply inline-block w-2.5 h-2.5 rounded-full;
}
.legend-port code {
  @apply px-1 rounded bg-[var(--bg-primary)] text-[var(--accent)];
}
</style>
