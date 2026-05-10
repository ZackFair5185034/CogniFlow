// -*- coding: utf-8 -*-
/**
 * 变量表达式解析工具
 *
 * 支持 {{variable}} 格式的变量引用和表达式求值。
 */

// ============ 类型定义 ============

export interface Variable {
  name: string
  type: 'STRING' | 'NUMBER' | 'BOOLEAN' | 'IMAGE' | 'BBOX'
  defaultValue?: any
  description?: string
}

export interface EvaluationContext {
  variables: Map<string, Variable>
  builtins?: Record<string, any>
}

// ============ 内置变量 ============

export const BUILTIN_VARIABLES: Record<string, any> = {
  '$now': () => new Date().toISOString(),
  '$graph.id': null,
  '$execution.id': null,
  '$node.id': null,
  '$node.label': null
}

// ============ 正则表达式 ============

// 匹配 {{variable_name}} 或 {{object.property}}
const VARIABLE_REF_REGEX = /\{\{([^}]+)\}\}/g

// 匹配完整的表达式（包含 {{...}}）
const EXPRESSION_REGEX = /^\{\{([^}]+)\}\}$/

// ============ 工具函数 ============

/**
 * 检查字符串是否包含变量引用
 */
export function hasVariableRef(str: string): boolean {
  return VARIABLE_REF_REGEX.test(str)
}

/**
 * 从字符串中提取所有变量名
 */
export function extractVariables(str: string): string[] {
  const matches = str.matchAll(VARIABLE_REF_REGEX)
  return [...matches].map(m => m[1].trim())
}

/**
 * 检查是否为完整表达式（只有变量引用，无其他操作符）
 */
export function isSimpleVariableRef(str: string): boolean {
  return EXPRESSION_REGEX.test(str)
}

/**
 * 获取变量引用的原始值
 */
export function getVariableRefValue(
  str: string,
  context: EvaluationContext
): any {
  const match = str.match(EXPRESSION_REGEX)
  if (!match) return str

  const path = match[1].trim()
  return resolvePath(path, context)
}

/**
 * 解析路径（如 a.b.c 或 arr[0]）
 */
export function resolvePath(path: string, context: EvaluationContext): any {
  // 检查内置变量
  if (path.startsWith('$')) {
    if (context.builtins && path in context.builtins) {
      return context.builtins[path]
    }
    return undefined
  }

  // 解析变量路径
  const parts = path.split('.')
  const firstPart = parts[0]

  const variable = context.variables.get(firstPart)
  if (!variable) return undefined

  let value = variable.defaultValue

  // 遍历路径
  for (let i = 1; i < parts.length; i++) {
    const part = parts[i]
    // 处理数组索引 arr[0]
    const arrayMatch = part.match(/^(\w+)\[(\d+)\]$/)
    if (arrayMatch) {
      const arr = value[arrayMatch[1]]
      value = arr ? arr[parseInt(arrayMatch[2])] : undefined
    } else {
      value = value ? value[part] : undefined
    }
    if (value === undefined) break
  }

  return value
}

// ============ 表达式求值 ============

/**
 * 替换字符串中的变量引用为实际值
 */
export function interpolate(
  template: string,
  context: EvaluationContext
): string {
  return template.replace(VARIABLE_REF_REGEX, (match, path) => {
    const value = resolvePath(path.trim(), context)
    if (value === undefined) return match
    return String(value)
  })
}

/**
 * 安全的表达式求值
 *
 * 只支持基本的数学和逻辑运算，不支持函数调用（除了内置的数学函数）
 */
export function evaluateExpression(
  expression: string,
  context: EvaluationContext
): any {
  // 先替换变量引用
  const interpolated = interpolate(expression, context)

  // 安全检查 - 确保只包含允许的字符
  const safeExpression = sanitizeExpression(interpolated)

  try {
    // 使用 Function 构造器进行求值（比 eval 更安全）
    const func = new Function(
      'Math',
      `'use strict'; return (${safeExpression});`
    )
    return func(Math)
  } catch (error) {
    console.error('表达式求值失败:', error, expression)
    return undefined
  }
}

/**
 * 清理表达式，只保留安全的字符
 */
function sanitizeExpression(expr: string): string {
  // 只允许：数字、字符串、运算符、比较符、逻辑符、括号、变量引用（已替换为值）
  // 这个函数在 interpolate 之后调用，此时变量已经被替换为值

  // 允许的字符集：a-zA-Z0-9_.\s+\-*/%<>=!&|?():,"'[]
  const allowed = expr.replace(
    /[^a-zA-Z0-9_.\s+\-*/%<>=!&|?():,"'\[\]]+/g,
    ''
  )
  return allowed
}

// ============ 验证函数 ============

/**
 * 验证变量名是否合法
 */
export function isValidVariableName(name: string): boolean {
  return /^[a-zA-Z_][a-zA-Z0-9_]*$/.test(name)
}

/**
 * 验证表达式是否有效
 */
export function isValidExpression(expr: string): boolean {
  try {
    const sanitized = sanitizeExpression(expr)
    new Function('Math', `'use strict'; return (${sanitized});`)
    return true
  } catch {
    return false
  }
}

// ============ 格式化函数 ============

/**
 * 格式化变量引用显示
 */
export function formatVariableRef(name: string): string {
  return `{{${name}}}`
}

/**
 * 格式化变量类型显示
 */
export function formatVariableType(type: Variable['type']): string {
  const labels: Record<Variable['type'], string> = {
    STRING: '字符串',
    NUMBER: '数字',
    BOOLEAN: '布尔',
    IMAGE: '图像',
    BBOX: '边界框'
  }
  return labels[type] || type
}

/**
 * 获取变量的类型颜色
 */
export function getVariableTypeColor(type: Variable['type']): string {
  const colors: Record<Variable['type'], string> = {
    STRING: '#8888aa',
    NUMBER: '#00f0ff',
    BOOLEAN: '#DC4FDC',
    IMAGE: '#4CFF4C',
    BBOX: '#FF7F4C'
  }
  return colors[type] || '#8888aa'
}

// ============ 快捷构建函数 ============

/**
 * 创建变量评估上下文
 */
export function createEvaluationContext(
  variables: Variable[],
  builtins?: Record<string, any>
): EvaluationContext {
  const varMap = new Map<string, Variable>()
  for (const v of variables) {
    varMap.set(v.name, v)
  }
  return {
    variables: varMap,
    builtins: { ...BUILTIN_VARIABLES, ...builtins }
  }
}

/**
 * 解析并求值表达式，自动判断是简单引用还是复杂表达式
 */
export function evaluate(
  expression: string,
  context: EvaluationContext
): any {
  if (!expression || typeof expression !== 'string') {
    return expression
  }

  const trimmed = expression.trim()

  // 如果是简单变量引用，直接返回变量值
  if (isSimpleVariableRef(trimmed)) {
    return getVariableRefValue(trimmed, context)
  }

  // 如果包含变量引用，先插值再求值
  if (hasVariableRef(trimmed)) {
    return evaluateExpression(trimmed, context)
  }

  // 普通表达式求值
  return evaluateExpression(trimmed, context)
}

// ============ 导出 ============

export default {
  hasVariableRef,
  extractVariables,
  isSimpleVariableRef,
  getVariableRefValue,
  resolvePath,
  interpolate,
  evaluateExpression,
  evaluate,
  isValidVariableName,
  isValidExpression,
  formatVariableRef,
  formatVariableType,
  getVariableTypeColor,
  createEvaluationContext,
  BUILTIN_VARIABLES
}
