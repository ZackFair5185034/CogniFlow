// -*- coding: utf-8 -*-
/**
 * 规则引擎 store - 共享工具函数
 *
 * 被 graph.ts / execution.ts / variables.ts 共用的 utilities.
 */

import type { ConfigSchemaProperty, VariableDefaultValue } from '@/types/api'

/** 序列化时需要丢弃的 VueFlow 内部字段 (DOM 引用、计算尺寸等) */
export const VUEFLOW_INTERNAL_KEYS = [
  'selected', 'dragging', 'parentNode', 'dimensions', 'handleBounds',
  'internals', 'events', 'selectable', 'deletable', 'focusable',
  'updatable', 'resizing', 'initialized', 'resizer', 'dragHandle',
] as const

/**
 * 深拷贝节点/边用于历史快照 - 使用 JSON 路线避免 structuredClone 撞上 DOM/Proxy。
 * 在 JSON 序列化前剥离 VueFlow 内部字段（DOM 引用、循环引用根）。
 *
 * 注意：data/position 必须浅 spread（连同嵌套的 data.config），
 * 否则 updateNodeConfig 的内层 mutate（`node.data.config[key] = value`）会
 * 污染所有持有同一引用的历史快照，导致 undo/redo 实际不工作。
 */
export function cloneForHistory<T>(items: T[]): T[] {
  return items.map(item => {
    const cleaned: any = {}
    for (const key in item) {
      if ((VUEFLOW_INTERNAL_KEYS as readonly string[]).includes(key)) continue
      const value = (item as any)[key]
      if (key === 'data' && value && typeof value === 'object') {
        cleaned.data = value.config
          ? { ...value, config: { ...value.config } }
          : { ...value }
      } else if (key === 'position' && value && typeof value === 'object') {
        cleaned.position = { ...value }
      } else {
        cleaned[key] = value
      }
    }
    return cleaned as T
  })
}

/**
 * 从 config_schema 提取默认配置值。
 */
export function getDefaultConfig(
  schema: Record<string, ConfigSchemaProperty>
): Record<string, VariableDefaultValue> {
  const config: Record<string, VariableDefaultValue> = {}
  for (const [key, prop] of Object.entries(schema)) {
    if (prop.default !== undefined) {
      config[key] = prop.default
    }
  }
  return config
}
