// -*- coding: utf-8 -*-
/**
 * 规则引擎变量状态 (P1-A 拆分)
 *
 * 独立子 store — 仅管理 variables 列表 (增删改查).
 * graph store 在 loadGraph / saveGraph / importFromJSON / duplicateAsNewGraph
 * 路径需要跨 store 写入 variables, 直接调用 useRuleVariablesStore() 即可
 * (Pinia 同实例, 子 store 可在 graph store 内部访问).
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { VariableType, VariableDefaultValue } from '@/types/api'

export interface Variable {
  name: string
  type: VariableType
  defaultValue?: VariableDefaultValue
  description?: string
}

export const useRuleVariablesStore = defineStore('ruleVariables', () => {
  /** 变量列表 */
  const variables = ref<Variable[]>([])

  function addVariable(variable?: Partial<Variable>): Variable {
    const newVar: Variable = {
      name: variable?.name ?? `var_${variables.value.length + 1}`,
      type: variable?.type ?? 'STRING',
      defaultValue: variable?.defaultValue ?? '',
      description: variable?.description ?? ''
    }
    variables.value.push(newVar)
    return newVar
  }

  function removeVariable(name: string) {
    variables.value = variables.value.filter(v => v.name !== name)
  }

  function updateVariable(name: string, updates: Partial<Variable>) {
    const v = variables.value.find(item => item.name === name)
    if (v) {
      Object.assign(v, updates)
    }
  }

  function getVariable(name: string): Variable | undefined {
    return variables.value.find(v => v.name === name)
  }

  /** 直接替换全部变量 (供 graph store 的 loadGraph / importFromJSON 调用) */
  function setVariables(list: Variable[]) {
    variables.value = list
  }

  /** 清空所有变量 (供 graph store 在切换图前清理) */
  function clearVariables() {
    variables.value = []
  }

  return {
    variables,
    addVariable,
    removeVariable,
    updateVariable,
    getVariable,
    setVariables,
    clearVariables,
  }
})
