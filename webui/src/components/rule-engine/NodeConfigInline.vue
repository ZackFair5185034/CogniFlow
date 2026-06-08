<template>
  <!--
    NodeConfigInline - LOD 2 节点内联配置 (Phase LOD-1)
    仅支持 4 种基础 widget: text / number / slider / dropdown
    复杂 widget (multiselect / model-select) 仍走右侧 NodeConfigEditor
  -->
  <div class="node-config-inline">
    <div
      v-for="entry in schemaEntries"
      :key="entry.key"
      class="nci-field"
    >
      <label class="nci-label">
        {{ entry.schema.title || entry.key }}
        <span
          v-if="entry.schema.description"
          class="nci-hint"
          :title="entry.schema.description"
        >?</span>
      </label>

      <!-- text -->
      <template v-if="entry.schema.widget === 'text' || !entry.schema.widget">
        <el-input
          :model-value="getValue(entry.key) as string"
          size="small"
          :placeholder="String(entry.schema.default ?? '')"
          @update:model-value="(v: string | number) => updateConfig(entry.key, v)"
        />
      </template>

      <!-- number -->
      <template v-else-if="entry.schema.widget === 'number'">
        <el-input-number
          :model-value="getValue(entry.key) as number"
          :min="entry.schema.minimum"
          :max="entry.schema.maximum"
          :step="entry.schema.step"
          :controls="false"
          size="small"
          class="nci-number"
          @update:model-value="(v: number | undefined) => updateConfig(entry.key, v ?? null)"
        />
      </template>

      <!-- slider -->
      <template v-else-if="entry.schema.widget === 'slider'">
        <div class="nci-slider-row">
          <el-slider
            :model-value="getValue(entry.key) as number"
            :min="entry.schema.minimum ?? 0"
            :max="entry.schema.maximum ?? 100"
            :step="entry.schema.step"
            size="small"
            @update:model-value="(v: number | number[]) => updateConfig(entry.key, Array.isArray(v) ? v[0] : v)"
          />
          <span class="nci-slider-value">{{ getValue(entry.key) }}</span>
        </div>
      </template>

      <!-- dropdown -->
      <template v-else-if="entry.schema.widget === 'dropdown'">
        <el-select
          :model-value="getValue(entry.key) as string | number | boolean"
          size="small"
          class="nci-select"
          @update:model-value="(v: string | number | boolean) => updateConfig(entry.key, v)"
        >
          <el-option
            v-for="opt in (entry.schema.enum ?? [])"
            :key="String(opt)"
            :value="opt"
            :label="String(opt)"
          />
        </el-select>
      </template>

      <!-- 复杂 widget 降级提示 -->
      <template v-else>
        <div class="nci-degraded">
          <span class="nci-degraded-text">
            ⚙ {{ entry.schema.widget }} (请用右侧面板)
          </span>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * NodeConfigInline - 节点内联配置组件
 *
 * 与 NodeConfigEditor 的关系:
 * - NodeConfigEditor: 右侧属性面板, 支持所有 widget (含 multiselect/model-select)
 * - NodeConfigInline: 节点内嵌, 仅 4 种基础 widget, 复杂 widget 降级提示
 *
 * 性能要点:
 * - 每个字段独立 v-for, 不共享 v-memo (字段变化只重渲染自己)
 * - store.updateConfig 是内层 mutate, 不触发全图 diff
 * - 适合 5-10 字段的简单节点, 复杂节点仍建议用右侧面板
 */
import { computed } from 'vue'
import { useRuleEngineStore } from '@/stores/ruleEngine'
import type { ConfigSchemaProperty } from '@/types/api'

const props = defineProps<{
  nodeId: string
  configSchema: Record<string, ConfigSchemaProperty>
  config: Record<string, unknown>
}>()

const store = useRuleEngineStore()

/** 过滤掉不渲染的字段: hidden 字段 / title/description-only 元字段 */
const schemaEntries = computed<Array<{ key: string; schema: ConfigSchemaProperty }>>(() => {
  const out: Array<{ key: string; schema: ConfigSchemaProperty }> = []
  for (const [key, schema] of Object.entries(props.configSchema)) {
    if (!schema.hidden && schema.widget !== 'display') {
      out.push({ key, schema })
    }
  }
  return out
})

function getValue(key: string): unknown {
  return props.config?.[key] ?? props.configSchema[key]?.default ?? null
}

function updateConfig(key: string, value: unknown) {
  store.updateNodeConfig(props.nodeId, key, value as never)
}
</script>

<style scoped lang="scss">
.node-config-inline {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.nci-field {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.nci-label {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 10px;
  color: rgba(255, 255, 255, 0.5);
  font-weight: 500;
}

.nci-hint {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.5);
  font-size: 9px;
  cursor: help;
  flex-shrink: 0;
}

.nci-slider-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.nci-slider-value {
  font-size: 10px;
  font-family: 'JetBrains Mono', monospace;
  color: rgba(255, 255, 255, 0.7);
  min-width: 32px;
  text-align: right;
  flex-shrink: 0;
}

.nci-number {
  width: 100%;
}

.nci-select {
  width: 100%;
}

.nci-degraded {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  background: rgba(255, 255, 255, 0.04);
  border-radius: 4px;
  font-size: 10px;
}

.nci-degraded-text {
  color: rgba(255, 255, 255, 0.4);
}
</style>
