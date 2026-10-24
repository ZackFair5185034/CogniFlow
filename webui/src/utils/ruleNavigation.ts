// -*- coding: utf-8 -*-
/**
 * 规则引擎路由路径工具。
 *
 * 2026-10-24: 「复制为新」此前硬编码跳转 `/rule-engine/${newId}`, 而实际路由是
 * `/rule-engine/design/:id` —— 点「复制为新」跳到不存在的路由, 白屏无反应。
 * 路径拼接收敛到这里, 便于单测锁定。
 */

/** 规则图设计器路由路径 */
export function ruleCanvasPath(graphId: number | string): string {
  return `/rule-engine/design/${graphId}`
}

/** 规则图列表路由路径 */
export function ruleListPath(): string {
  return '/rule-engine'
}
