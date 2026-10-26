<!-- -*- coding: utf-8 -*- -->
<!--
  右侧属性面板 - 把节点参数编辑从「双击展开 LOD2 节点壳」外置到常驻侧栏。

  2026-10-24: 画布此前没有右侧属性面板, 改节点参数只能在 LOD2 展开的节点内部
  操作 —— 节点一多就找不到、也看不清当前改的是谁。本组件只做「壳」:
  头部(图标/名称/类型/关闭) + 端口摘要 + 配置区。

  配置区直接复用 NodeConfigEditor (panel 模式), 不重写控件渲染:
  10 种 widget / 变量绑定 / 模型选择 / 文件选择都已在 NodeConfigEditor 内实现,
  重写一遍必然漏控件。
-->
<script setup lang="ts">
import { computed } from 'vue'
import NodeConfigEditor from './NodeConfigEditor.vue'
import type { RuleNodeData } from '@/types/api'

const props = defineProps<{
  /** 当前选中节点的数据（未选中为 null） */
  node: RuleNodeData | null
  /** 当前选中节点 id（未选中为 null） */
  nodeId: string | null
}>()

const emit = defineEmits<{
  /** 用户点关闭 —— 父组件负责取消选中 */
  (e: 'close'): void
}>()

/** 输入端口摘要 */
const inputPorts = computed(() => props.node?.inputs ?? [])

/** 输出端口摘要 */
const outputPorts = computed(() => props.node?.outputs ?? [])

/**
 * 分类图标配色 —— 取自 `_variables.scss` 的 `--cat-<name>-bg` / `--cat-<name>-fg`。
 * 分类名不在已知集合时回退到中性底色（CSS 变量天然 fallback）。
 */
const categoryStyle = computed(() => {
  const cat = props.node?.category ?? ''
  return {
    background: `var(--cat-${cat}-bg, var(--bg-hover))`,
    color: `var(--cat-${cat}-fg, var(--text-primary))`,
  }
})
</script>

<template>
  <aside class="node-inspector ui-card">
    <!-- 未选中节点: 占位提示 (右栏常驻, 空面板不该看起来像坏了) -->
    <div
      v-if="!node || !nodeId"
      class="inspector-placeholder"
    >
      <SvgIcon name="edit" />
      <p>选择一个节点以编辑参数</p>
      <p class="inspector-tip">
        单击节点选中 · 双击节点展开节点壳
      </p>
    </div>

    <template v-else>
      <header class="inspector-header">
        <span
          class="inspector-icon"
          :class="node.category"
          :style="categoryStyle"
        >
          <SvgIcon :name="node.category" />
        </span>
        <div class="inspector-titles">
          <h3>{{ node.label ?? node.type }}</h3>
          <span class="inspector-type">{{ node.type }}</span>
        </div>
        <button
          class="ui-btn ui-btn-small"
          title="关闭属性面板"
          @click="emit('close')"
        >
          ×
        </button>
      </header>

      <p
        v-if="node.description"
        class="inspector-desc"
      >
        {{ node.description }}
      </p>

      <!-- 端口摘要: 让用户不展开节点就知道该往哪连 -->
      <div class="inspector-ports">
        <div class="port-group">
          <span class="port-group-title">输入</span>
          <span
            v-for="p in inputPorts"
            :key="`in-${p.name}`"
            class="port-chip"
            :title="`${p.name} (${p.type})`"
          >
            {{ p.label ?? p.name }}
            <code>{{ p.type }}</code>
          </span>
          <span
            v-if="inputPorts.length === 0"
            class="port-empty"
          >无</span>
        </div>
        <div class="port-group">
          <span class="port-group-title">输出</span>
          <span
            v-for="p in outputPorts"
            :key="`out-${p.name}`"
            class="port-chip"
            :title="`${p.name} (${p.type})`"
          >
            {{ p.label ?? p.name }}
            <code>{{ p.type }}</code>
          </span>
          <span
            v-if="outputPorts.length === 0"
            class="port-empty"
          >无</span>
        </div>
      </div>

      <!-- 配置区: 复用 NodeConfigEditor (panel 模式) -->
      <div class="inspector-config">
        <NodeConfigEditor
          :node-id="nodeId"
          mode="panel"
        />
      </div>
    </template>
  </aside>
</template>

<style scoped lang="scss">
.node-inspector {
  @apply flex flex-col gap-2 p-3;
  @apply w-full shrink-0 overflow-hidden;
}

.inspector-placeholder {
  @apply flex flex-col items-center justify-center gap-1 py-8 text-center;
  color: var(--text-muted);
}

.inspector-placeholder p {
  @apply text-xs;
}

.inspector-tip {
  @apply text-[11px] opacity-70;
}

.inspector-header {
  @apply flex items-center gap-2 shrink-0;
}

.inspector-icon {
  @apply w-7 h-7 rounded-md flex items-center justify-center shrink-0;
}

.inspector-titles {
  @apply flex flex-col gap-0.5 min-w-0 flex-1;
}

.inspector-titles h3 {
  @apply text-sm font-semibold truncate;
  color: var(--text-primary);
}

.inspector-type {
  @apply text-[11px] truncate;
  color: var(--text-muted);
  font-family: var(--font-family-mono);
}

.inspector-desc {
  @apply text-xs shrink-0;
  color: var(--text-muted);
}

.inspector-ports {
  @apply flex flex-col gap-1.5 shrink-0 pb-2;
  border-bottom: 1px solid var(--border-color);
}

.port-group {
  @apply flex flex-wrap items-center gap-1;
}

.port-group-title {
  @apply text-[11px] font-semibold w-8 shrink-0;
  color: var(--text-muted);
}

.port-chip {
  @apply inline-flex items-center gap-1 px-1.5 py-0.5 rounded-sm text-[11px];
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  color: var(--text-primary);
}

.port-chip code {
  @apply text-[10px];
  color: var(--accent);
  font-family: var(--font-family-mono);
}

.port-empty {
  @apply text-[11px];
  color: var(--text-muted);
}

/* 配置区占满剩余高度, 内部 nce-body 自行滚动 */
.inspector-config {
  @apply flex-1 min-h-0 overflow-hidden;
}

/* NodeConfigEditor 自带头部, 与本组件头部重复 —— 隐藏 */
.inspector-config :deep(.nce-header) {
  display: none;
}
</style>
