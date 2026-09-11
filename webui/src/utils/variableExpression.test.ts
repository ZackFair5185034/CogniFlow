// -*- coding: utf-8 -*-
/**
 * 变量表达式解析器 - 单元测试
 */

import { describe, it, expect, beforeEach } from 'vitest'
import {
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
  BUILTIN_VARIABLES,
} from './variableExpression'

describe('变量表达式解析器', () => {
  // 测试上下文
  let context: ReturnType<typeof createEvaluationContext>

  beforeEach(() => {
    context = createEvaluationContext([
      {
        name: 'username',
        type: 'STRING' as const,
        defaultValue: 'Alice',
        description: '用户名',
      },
      {
        name: 'age',
        type: 'NUMBER' as const,
        defaultValue: 25,
        description: '年龄',
      },
      {
        name: 'isActive',
        type: 'BOOLEAN' as const,
        defaultValue: true,
        description: '是否激活',
      },
      {
        name: 'profile',
        type: 'STRING' as const,
        defaultValue: {
          name: 'Alice Profile',
          email: 'alice@example.com',
          scores: [90, 85, 92],
        },
        description: '用户资料',
      },
    ])
  })

  // ============ hasVariableRef 测试 ============

  describe('hasVariableRef', () => {
    it('应该检测到 {{variable}} 格式的变量引用', () => {
      expect(hasVariableRef('Hello {{username}}')).toBe(true)
      expect(hasVariableRef('Age: {{age}}')).toBe(true)
    })

    it('应该检测到 {{object.property}} 格式的属性访问', () => {
      expect(hasVariableRef('Email: {{profile.email}}')).toBe(true)
    })

    it('对于普通字符串应返回 false', () => {
      expect(hasVariableRef('Hello World')).toBe(false)
      expect(hasVariableRef('No variables here')).toBe(false)
    })

    it('对于空字符串应返回 false', () => {
      expect(hasVariableRef('')).toBe(false)
    })
  })

  // ============ extractVariables 测试 ============

  describe('extractVariables', () => {
    it('应该提取单个变量名', () => {
      expect(extractVariables('Hello {{username}}')).toEqual(['username'])
      expect(extractVariables('Age: {{age}}')).toEqual(['age'])
    })

    it('应该提取多个变量名', () => {
      const result = extractVariables('User {{username}} is {{age}} years old')
      expect(result).toEqual(['username', 'age'])
    })

    it('应该提取嵌套属性路径', () => {
      const result = extractVariables('Email: {{profile.email}}')
      expect(result).toEqual(['profile.email'])
    })

    it('对于无变量字符串应返回空数组', () => {
      expect(extractVariables('No variables here')).toEqual([])
    })
  })

  // ============ isSimpleVariableRef 测试 ============

  describe('isSimpleVariableRef', () => {
    it('应识别完整的 {{variable}} 格式', () => {
      expect(isSimpleVariableRef('{{username}}')).toBe(true)
      expect(isSimpleVariableRef('{{age}}')).toBe(true)
    })

    it('应识别 {{object.property}} 格式', () => {
      expect(isSimpleVariableRef('{{profile.email}}')).toBe(true)
    })

    it('应拒绝包含额外文本的字符串', () => {
      expect(isSimpleVariableRef('Hello {{username}}')).toBe(false)
      expect(isSimpleVariableRef('{{username}} !')).toBe(false)
    })

    it('应拒绝普通字符串', () => {
      expect(isSimpleVariableRef('username')).toBe(false)
    })
  })

  // ============ getVariableRefValue 测试 ============

  describe('getVariableRefValue', () => {
    it('应返回简单变量的值', () => {
      expect(getVariableRefValue('{{username}}', context)).toBe('Alice')
      expect(getVariableRefValue('{{age}}', context)).toBe(25)
      expect(getVariableRefValue('{{isActive}}', context)).toBe(true)
    })

    it('应返回嵌套属性的值', () => {
      expect(getVariableRefValue('{{profile.name}}', context)).toBe('Alice Profile')
      expect(getVariableRefValue('{{profile.email}}', context)).toBe('alice@example.com')
    })

    it('对于不存在的变量应返回 undefined', () => {
      expect(getVariableRefValue('{{nonexistent}}', context)).toBe(undefined)
    })
  })

  // ============ resolvePath 测试 ============

  describe('resolvePath', () => {
    it('应解析简单变量路径', () => {
      expect(resolvePath('username', context)).toBe('Alice')
      expect(resolvePath('age', context)).toBe(25)
    })

    it('应解析嵌套属性路径', () => {
      expect(resolvePath('profile.name', context)).toBe('Alice Profile')
      expect(resolvePath('profile.email', context)).toBe('alice@example.com')
    })

    it('应解析数组索引路径', () => {
      expect(resolvePath('profile.scores[0]', context)).toBe(90)
      expect(resolvePath('profile.scores[1]', context)).toBe(85)
      expect(resolvePath('profile.scores[2]', context)).toBe(92)
    })

    it('对于不存在的路径应返回 undefined', () => {
      expect(resolvePath('nonexistent', context)).toBe(undefined)
      expect(resolvePath('profile.nonexistent', context)).toBe(undefined)
    })

    it('应解析内置变量 $now', () => {
      const result = resolvePath('$now', context)
      expect(result).toBeDefined()
      expect(typeof result).toBe('string')
      // ISO 格式日期
      expect(result).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/)
    })

    it('对于不存在的内置变量应返回 undefined', () => {
      expect(resolvePath('$nonexistent', context)).toBe(undefined)
    })
  })

  // ============ interpolate 测试 ============

  describe('interpolate', () => {
    it('应替换单个变量引用', () => {
      expect(interpolate('Hello {{username}}', context)).toBe('Hello Alice')
      expect(interpolate('Age: {{age}}', context)).toBe('Age: 25')
    })

    it('应替换多个变量引用', () => {
      const result = interpolate('User {{username}} is {{age}} years old', context)
      expect(result).toBe('User Alice is 25 years old')
    })

    it('应替换嵌套属性引用', () => {
      const result = interpolate('Email: {{profile.email}}', context)
      expect(result).toBe('Email: alice@example.com')
    })

    it('对于不存在的变量应保留原占位符', () => {
      expect(interpolate('Hello {{nonexistent}}', context)).toBe('Hello {{nonexistent}}')
    })

    it('对于无变量字符串应原样返回', () => {
      expect(interpolate('Hello World', context)).toBe('Hello World')
    })
  })

  // ============ evaluateExpression 测试 ============

  describe('evaluateExpression', () => {
    it('应求值数学表达式', () => {
      expect(evaluateExpression('1 + 2', context)).toBe(3)
      expect(evaluateExpression('10 - 3', context)).toBe(7)
      expect(evaluateExpression('4 * 5', context)).toBe(20)
      expect(evaluateExpression('10 / 2', context)).toBe(5)
    })

    it('应求值包含变量的数学表达式', () => {
      expect(evaluateExpression('{{age}} + 10', context)).toBe(35)
      expect(evaluateExpression('{{age}} * 2', context)).toBe(50)
    })

    it('应求值比较表达式', () => {
      expect(evaluateExpression('{{age}} > 18', context)).toBe(true)
      expect(evaluateExpression('{{age}} < 18', context)).toBe(false)
    })

    it('应求值逻辑表达式', () => {
      expect(evaluateExpression('{{isActive}} && true', context)).toBe(true)
      expect(evaluateExpression('{{isActive}} || false', context)).toBe(true)
    })

    it('应使用 Math 函数', () => {
      expect(evaluateExpression('Math.max({{age}}, 30)', context)).toBe(30)
      expect(evaluateExpression('Math.min({{age}}, 30)', context)).toBe(25)
    })

    it('对于无效表达式应返回 undefined', () => {
      expect(evaluateExpression('invalid expression !!!', context)).toBe(undefined)
    })
  })

  // ============ evaluate 测试 ============

  describe('evaluate', () => {
    it('应直接返回简单变量引用', () => {
      expect(evaluate('{{username}}', context)).toBe('Alice')
      expect(evaluate('{{age}}', context)).toBe(25)
    })

    it('应求值包含变量的表达式', () => {
      expect(evaluate('{{age}} + 10', context)).toBe(35)
    })

    it('应求值普通数学表达式', () => {
      expect(evaluate('1 + 2 + 3', context)).toBe(6)
    })

    it('对于空输入应返回 undefined', () => {
      expect(evaluate('', context)).toBe('')
    })
  })

  // ============ isValidVariableName 测试 ============

  describe('isValidVariableName', () => {
    it('应接受有效的变量名', () => {
      expect(isValidVariableName('username')).toBe(true)
      expect(isValidVariableName('userName')).toBe(true)
      expect(isValidVariableName('user_name')).toBe(true)
      expect(isValidVariableName('_private')).toBe(true)
      expect(isValidVariableName('age123')).toBe(true)
    })

    it('应拒绝无效的变量名', () => {
      expect(isValidVariableName('123user')).toBe(false)
      expect(isValidVariableName('user-name')).toBe(false)
      expect(isValidVariableName('user name')).toBe(false)
    })
  })

  // ============ isValidExpression 测试 ============

  describe('isValidExpression', () => {
    it('应接受有效的表达式', () => {
      expect(isValidExpression('1 + 2')).toBe(true)
      expect(isValidExpression('{{age}} > 18')).toBe(true)
      expect(isValidExpression('Math.max(1, 2)')).toBe(true)
    })

    it('应拒绝无效的表达式', () => {
      expect(isValidExpression('')).toBe(false)
    })
  })

  // ============ formatVariableRef 测试 ============

  describe('formatVariableRef', () => {
    it('应格式化变量引用', () => {
      expect(formatVariableRef('username')).toBe('{{username}}')
      expect(formatVariableRef('age')).toBe('{{age}}')
    })
  })

  // ============ formatVariableType 测试 ============

  describe('formatVariableType', () => {
    it('应返回正确的中文标签', () => {
      expect(formatVariableType('STRING')).toBe('字符串')
      expect(formatVariableType('NUMBER')).toBe('数字')
      expect(formatVariableType('BOOLEAN')).toBe('布尔')
      expect(formatVariableType('IMAGE')).toBe('图像')
      expect(formatVariableType('BBOX')).toBe('边界框')
    })
  })

  // ============ getVariableTypeColor 测试 ============

  describe('getVariableTypeColor', () => {
    // 2026-09-12: 随设计令牌 v2 更新 —— 变量类型色改用低眩光调, 并让出品牌青。
    // NUMBER 原为 #00f0ff (v1 的品牌色), 品牌色改为 #22d3ee 后此处改用该值。
    it('应为每种类型返回正确的颜色', () => {
      expect(getVariableTypeColor('STRING')).toBe('#9a9ab2')
      expect(getVariableTypeColor('NUMBER')).toBe('#22d3ee')
      expect(getVariableTypeColor('BOOLEAN')).toBe('#b158e4')
      expect(getVariableTypeColor('IMAGE')).toBe('#58e49e')
      expect(getVariableTypeColor('BBOX')).toBe('#e48b58')
    })

    it('对于未知类型应返回默认颜色', () => {
      expect(getVariableTypeColor('UNKNOWN' as any)).toBe('#9a9ab2')
    })
  })

  // ============ createEvaluationContext 测试 ============

  describe('createEvaluationContext', () => {
    it('应正确创建上下文', () => {
      const ctx = createEvaluationContext([
        { name: 'test', type: 'STRING' as const, defaultValue: 'value' },
      ])

      expect(ctx.variables.get('test')).toBeDefined()
      expect(ctx.variables.get('test')?.defaultValue).toBe('value')
    })

    it('应包含内置变量', () => {
      expect(context.builtins).toBeDefined()
      expect(context.builtins?.['$now']).toBeDefined()
    })

    it('内置变量 $now 应返回动态时间', () => {
      const $now = context.builtins?.['$now']
      expect(typeof $now).toBe('function')

      const result = (($now as () => string))()
      expect(result).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/)
    })
  })

  // ============ BUILTIN_VARIABLES 测试 ============

  describe('BUILTIN_VARIABLES', () => {
    it('应包含所有预定义的内置变量', () => {
      expect(BUILTIN_VARIABLES['$now']).toBeDefined()
      expect(BUILTIN_VARIABLES['$graph.id']).toBe(null)
      expect(BUILTIN_VARIABLES['$execution.id']).toBe(null)
      expect(BUILTIN_VARIABLES['$node.id']).toBe(null)
      expect(BUILTIN_VARIABLES['$node.label']).toBe(null)
    })

    it('$now 应返回 ISO 格式的日期字符串', () => {
      const $now = BUILTIN_VARIABLES['$now'] as () => string
      expect($now()).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/)
    })
  })
})
