// -*- coding: utf-8 -*-
/**
 * 端口类型兼容矩阵 store - 前端连线校验的唯一依据。
 *
 * 后端 `backend/services/rule_engine/port_types.py` 是矩阵的唯一事实源,
 * 通过 `GET /api/rule-engine/port-compatibility` 下发。
 * 前端不再硬编码兼容规则(旧实现只有 4 条, 与后端 14 类漂移,
 * 导致 BOOLEAN->TRIGGER 的边被 VueFlow 静默丢弃, 动作层事实上不可达)。
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { ruleEngineApi } from '@/api/index'
import type { PortCompatibilityResponse } from '@/types/api'

export const useRulePortsStore = defineStore('rulePorts', () => {
  /** 源类型 -> 兼容的目标类型列表 */
  const matrix = ref<Record<string, string[]>>({})
  /** 全部端口类型 */
  const types = ref<string[]>([])
  /** 是否已成功加载 */
  const loaded = ref(false)

  /**
   * 加载端口兼容矩阵。
   * 失败时保持 loaded=false, isCompatible 走 fail-loud 分支(拒绝而非静默放行)。
   */
  async function loadPorts(): Promise<void> {
    const res = await ruleEngineApi.getPortCompatibility()
    const data = res.data as PortCompatibilityResponse
    matrix.value = data.matrix ?? {}
    types.value = data.types ?? []
    loaded.value = true
  }

  /**
   * 判断源端口类型能否连接到目标端口类型。
   * 矩阵未加载时一律返回 false —— 让用户看到明确的错误提示,
   * 而不是像旧实现那样让 VueFlow 静默丢弃连线。
   */
  function isCompatible(sourceType: string, targetType: string): boolean {
    if (!loaded.value) return false
    if (!sourceType || !targetType) return false
    if (sourceType === 'ANY' || targetType === 'ANY') return true
    const allowed = matrix.value[sourceType]
    if (!allowed) return false
    return allowed.includes(targetType)
  }

  return { matrix, types, loaded, loadPorts, isCompatible }
})
