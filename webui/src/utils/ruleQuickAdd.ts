// -*- coding: utf-8 -*-
/**
 * 空画布「快速添加」选点 —— 按分类各取一个代表节点。
 *
 * 背景 (Task 13): 旧实现是 `nodeDefinitions.slice(0, 4)`, 取的是节点注册顺序
 * 最靠前的 4 个, 结果全部落在 input / trigger 分类 —— 用户在空画布上根本看不到
 * 「检测」「动作」这类节点, 误以为产品没有这些能力。
 *
 * 单独成文件的原因: `<script setup>` 内不允许 `export`, 而该逻辑需要被单测覆盖。
 */
import type { NodeDefinition } from '@/types/api'

/**
 * 按分类各取第一个节点 —— 输出顺序 = 分类首次出现的顺序。
 *
 * @param defs 节点定义全量列表
 * @returns 每个分类一个代表节点
 */
export function pickQuickAddNodes(defs: NodeDefinition[]): NodeDefinition[] {
  const picked = new Map<string, NodeDefinition>()
  for (const def of defs) {
    const cat = def.category || 'other'
    if (!picked.has(cat)) {
      picked.set(cat, def)
    }
  }
  return Array.from(picked.values())
}
