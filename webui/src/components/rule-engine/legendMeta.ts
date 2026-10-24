// -*- coding: utf-8 -*-
/**
 * 图例元数据 - 节点分类与端口类型说明。
 *
 * 单独成文件的原因: `<script setup>` 里不允许 `export` 语法,
 * 而这些常量需要被单测直接引用。
 */

/**
 * 图例展示的节点分类。
 * key 与 `--cat-*` CSS 变量名一一对应, 颜色取自 `src/style/_variables.scss`。
 */
export const LEGEND_CATEGORIES = [
  { key: 'input', label: '输入' },
  { key: 'detection', label: '检测' },
  { key: 'processing', label: '处理' },
  { key: 'action', label: '动作' },
  { key: 'logic', label: '逻辑' },
  { key: 'output', label: '输出' },
] as const

/**
 * 图例展示的端口类型。
 * 取自后端 `backend/services/rule_engine/port_types.py` 的常用类型。
 */
export const LEGEND_PORT_TYPES = [
  { type: 'ANY', label: '任意' },
  { type: 'IMAGE', label: '图像' },
  { type: 'BOOLEAN', label: '布尔' },
  { type: 'TRIGGER', label: '触发' },
  { type: 'CONTROL', label: '控制' },
  { type: 'STRING', label: '文本' },
] as const
