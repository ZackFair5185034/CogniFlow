<script setup lang="ts">
/**
 * 变量管理面板组件
 *
 * 提供变量的 CRUD 操作界面，支持添加、删除、编辑变量。
 */

// ============ 类型定义 ============

export type VariableType = 'STRING' | 'NUMBER' | 'BOOLEAN' | 'IMAGE' | 'BBOX'

/** 变量默认值类型 */
export type VariableDefaultValue = string | number | boolean | null

export interface Variable {
  name: string
  type: VariableType
  defaultValue?: VariableDefaultValue
  description?: string
}

// ============ Props & Emits ============

defineProps<{
  variables: Variable[]
  disabled?: boolean
}>()

const emit = defineEmits<{
  (e: 'add'): void
  (e: 'remove', index: number): void
  (e: 'update', index: number, field: keyof Variable, value: VariableDefaultValue): void
}>()

// ============ 状态 ============

const expanded = ref(true)

// ============ 常量 ============

const VARIABLE_TYPES: Array<{ value: VariableType; label: string; color: string }> = [
  { value: 'STRING', label: '字符串', color: '#8888aa' },
  { value: 'NUMBER', label: '数字', color: '#5898ff' },
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

function handleUpdate(index: number, field: keyof Variable, value: VariableDefaultValue) {
  emit('update', index, field, value)
}
</script>

<template>
  <div class="variable-panel">
    <!-- 面板头部 -->
    <div
      class="panel-header"
      @click="expanded = !expanded"
    >
      <span class="panel-title">📌 变量</span>
      <span class="panel-count">{{ variables.length }}</span>
      <SvgIcon
        class="chevron"
        :class="{ expanded }"
        name="chevron"
      />
    </div>

    <!-- 变量列表 -->
    <div
      v-show="expanded"
      class="panel-body"
    >
      <div
        v-if="variables.length === 0"
        class="empty-state"
      >
        暂无变量，请点击下方按钮添加
      </div>

      <div
        v-for="(variable, index) in variables"
        :key="index"
        class="variable-item"
      >
        <!-- 变量名 -->
        <el-input
          type="text"
          :model-value="variable.name"
          placeholder="变量名"
          :disabled="disabled"
          @update:model-value="handleUpdate(index, 'name', $event as string)"
        />

        <!-- 变量类型 -->
        <el-select
          :model-value="variable.type"
          class="var-type-select"
          :disabled="disabled"
          @update:model-value="handleUpdate(index, 'type', $event as VariableType)"
        >
          <el-option
            v-for="t in VARIABLE_TYPES"
            :key="t.value"
            :value="t.value"
            :label="t.label"
          />
        </el-select>

        <!-- 删除按钮 -->
        <button
          class="var-remove-btn"
          :disabled="disabled"
          title="删除变量"
          @click="handleRemove(index)"
        >
          <SvgIcon
            name="close"
            :size="14"
          />
        </button>
      </div>

      <!-- 添加按钮 -->
      <button
        class="add-var-btn"
        :disabled="disabled"
        @click="handleAdd"
      >
        <SvgIcon
          name="plus"
          :size="14"
        />
        添加变量
      </button>
    </div>
  </div>
</template>

<style scoped lang="scss">
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

:deep(.el-input) {
  flex: 1;
  min-width: 0;

  .el-input__wrapper {
    background: var(--bg-input, #0e0e16);
    border: 1px solid var(--border-color, #2a2a3a);
    border-radius: 4px;
    padding: 6px 8px;
    font-size: 12px;
    color: var(--text-primary, #e0e0e8);
    font-family: monospace;
    box-shadow: none;
  }

  .el-input__wrapper:hover {
    border-color: var(--accent-blue, #5898ff);
  }

  .el-input__wrapper.is-focus {
    border-color: var(--accent-blue, #5898ff);
    box-shadow: 0 0 0 1px var(--accent-blue, #5898ff) inset;
  }

  .el-input.is-disabled .el-input__wrapper {
    opacity: 0.5;
    cursor: not-allowed;
  }
}

.var-type-select {
  width: 80px;
}

:deep(.el-select) {
  width: 80px;

  .el-select__wrapper {
    background: var(--bg-input, #0e0e16);
    border: 1px solid var(--border-color, #2a2a3a);
    border-radius: 4px;
    padding: 6px 8px;
    font-size: 11px;
    color: var(--text-primary, #e0e0e8);
    box-shadow: none;
    min-height: unset;
    height: auto;
  }

  .el-select__wrapper:hover {
    border-color: var(--accent-blue, #5898ff);
  }

  .el-select__wrapper.is-focus {
    border-color: var(--accent-blue, #5898ff);
    box-shadow: 0 0 0 1px var(--accent-blue, #5898ff) inset;
  }

  .el-select__caret {
    color: var(--text-muted, #8888aa);
  }

  .el-select__selected-item {
    color: var(--text-primary, #e0e0e8);
  }

  .el-select__placeholder {
    color: var(--text-muted, #8888aa);
  }
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
  border-color: var(--accent-blue, #5898ff);
  color: var(--accent-blue, #5898ff);
  background: rgba(0, 240, 255, 0.05);
}

.add-var-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}
</style>
