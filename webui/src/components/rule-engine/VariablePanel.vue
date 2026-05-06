<script setup lang="ts">
/**
 * 变量管理面板组件
 *
 * 提供变量的 CRUD 操作界面，支持添加、删除、编辑变量。
 */
import { ref, computed } from 'vue'
import SvgIcon from '@/components/SvgIcon.vue'

// ============ 类型定义 ============

export type VariableType = 'STRING' | 'NUMBER' | 'BOOLEAN' | 'IMAGE' | 'BBOX'

export interface Variable {
  name: string
  type: VariableType
  defaultValue?: any
  description?: string
}

// ============ Props & Emits ============

const props = defineProps<{
  variables: Variable[]
  disabled?: boolean
}>()

const emit = defineEmits<{
  (e: 'add'): void
  (e: 'remove', index: number): void
  (e: 'update', index: number, field: keyof Variable, value: any): void
}>()

// ============ 状态 ============

const expanded = ref(true)

// ============ 常量 ============

const VARIABLE_TYPES: Array<{ value: VariableType; label: string; color: string }> = [
  { value: 'STRING', label: '字符串', color: '#8888aa' },
  { value: 'NUMBER', label: '数字', color: '#00f0ff' },
  { value: 'BOOLEAN', label: '布尔', color: '#DC4FDC' },
  { value: 'IMAGE', label: '图像', color: '#4CFF4C' },
  { value: 'BBOX', label: '边界框', color: '#FF7F4C' }
]

// ============ 方法 ============

function handleAdd() {
  emit('add')
}

function handleRemove(index: number) {
  emit('remove', index)
}

function handleUpdate(index: number, field: keyof Variable, value: any) {
  emit('update', index, field, value)
}

function getTypeColor(type: VariableType): string {
  return VARIABLE_TYPES.find(t => t.value === type)?.color || '#8888aa'
}

function getTypeLabel(type: VariableType): string {
  return VARIABLE_TYPES.find(t => t.value === type)?.label || type
}
</script>

<template>
  <div class="variable-panel">
    <!-- 面板头部 -->
    <div class="panel-header" @click="expanded = !expanded">
      <span class="panel-title">📌 变量</span>
      <span class="panel-count">{{ variables.length }}</span>
      <SvgIcon
        class="chevron"
        :class="{ expanded }"
        name="chevron"
      />
    </div>

    <!-- 变量列表 -->
    <div v-show="expanded" class="panel-body">
      <div v-if="variables.length === 0" class="empty-state">
        暂无变量，请点击下方按钮添加
      </div>

      <div
        v-for="(variable, index) in variables"
        :key="index"
        class="variable-item"
      >
        <!-- 变量名 -->
        <input
          type="text"
          :value="variable.name"
          @input="handleUpdate(index, 'name', ($event.target as HTMLInputElement).value)"
          class="var-name-input"
          placeholder="变量名"
          :disabled="disabled"
        />

        <!-- 变量类型 -->
        <select
          :value="variable.type"
          @change="handleUpdate(index, 'type', ($event.target as HTMLSelectElement).value)"
          class="var-type-select"
          :disabled="disabled"
        >
          <option
            v-for="t in VARIABLE_TYPES"
            :key="t.value"
            :value="t.value"
          >
            {{ t.label }}
          </option>
        </select>

        <!-- 删除按钮 -->
        <button
          class="var-remove-btn"
          @click="handleRemove(index)"
          :disabled="disabled"
          title="删除变量"
        >
          <SvgIcon name="close" :size="14" />
        </button>
      </div>

      <!-- 添加按钮 -->
      <button
        class="add-var-btn"
        @click="handleAdd"
        :disabled="disabled"
      >
        <SvgIcon name="plus" :size="14" />
        添加变量
      </button>
    </div>
  </div>
</template>

<style scoped>
.variable-panel {
  background: var(--bg-secondary, #1a1a24);
  border: 1px solid var(--border-color, #2a2a3a);
  border-radius: 8px;
  overflow: hidden;
}

.panel-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  cursor: pointer;
  user-select: none;
  transition: background 0.2s;
}

.panel-header:hover {
  background: var(--bg-hover, #22222e);
}

.panel-title {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary, #e0e0e8);
}

.panel-count {
  font-size: 11px;
  color: var(--text-muted, #8888aa);
  background: var(--bg-primary, #12121a);
  padding: 2px 6px;
  border-radius: 10px;
}

.chevron {
  width: 14px;
  height: 14px;
  color: var(--text-muted, #8888aa);
  transition: transform 0.2s;
  margin-left: auto;
}

.chevron.expanded {
  transform: rotate(90deg);
}

.panel-body {
  padding: 8px 12px 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.empty-state {
  font-size: 12px;
  color: var(--text-muted, #8888aa);
  text-align: center;
  padding: 16px 0;
}

.variable-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.var-name-input {
  flex: 1;
  min-width: 0;
  background: var(--bg-input, #0e0e16);
  border: 1px solid var(--border-color, #2a2a3a);
  border-radius: 4px;
  padding: 6px 8px;
  font-size: 12px;
  color: var(--text-primary, #e0e0e8);
  font-family: monospace;
}

.var-name-input:focus {
  outline: none;
  border-color: var(--accent-cyan, #00f0ff);
}

.var-name-input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.var-type-select {
  width: 80px;
  background: var(--bg-input, #0e0e16);
  border: 1px solid var(--border-color, #2a2a3a);
  border-radius: 4px;
  padding: 6px 4px;
  font-size: 11px;
  color: var(--text-primary, #e0e0e8);
  cursor: pointer;
}

.var-type-select:focus {
  outline: none;
  border-color: var(--accent-cyan, #00f0ff);
}

.var-type-select:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.var-remove-btn {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  border-radius: 4px;
  color: var(--text-muted, #8888aa);
  cursor: pointer;
  transition: all 0.2s;
  flex-shrink: 0;
}

.var-remove-btn:hover:not(:disabled) {
  background: var(--bg-hover, #22222e);
  color: var(--accent-red, #ff4c4c);
}

.var-remove-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.add-var-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  width: 100%;
  padding: 8px;
  background: transparent;
  border: 1px dashed var(--border-color, #2a2a3a);
  border-radius: 4px;
  font-size: 12px;
  color: var(--text-muted, #8888aa);
  cursor: pointer;
  transition: all 0.2s;
}

.add-var-btn:hover:not(:disabled) {
  border-color: var(--accent-cyan, #00f0ff);
  color: var(--accent-cyan, #00f0ff);
  background: rgba(0, 240, 255, 0.05);
}

.add-var-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}
</style>
