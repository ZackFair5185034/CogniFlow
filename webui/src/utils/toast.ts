// -*- coding: utf-8 -*-
/**
 * Toast 通知 API
 *
 * 提供全局单例模式，允许在任何地方调用 toast 通知。
 * 使用方法：
 *   import { toast } from '@/utils/toast'
 *   toast.success('操作成功')
 *   toast.error('操作失败')
 *   toast.info('提示信息')
 */

import type { ToastOptions, ToastType } from '@/components/common/Toast.vue'

// ============ Toast 实例引用 ============

let toastInstance: {
  show: (options: ToastOptions) => void
  hide: () => void
} | null = null

// ============ 注册函数 ============

/**
 * 注册 Toast 实例（在 App.vue 或 main.ts 中调用）
 */
export function registerToast(instance: typeof toastInstance) {
  toastInstance = instance
}

/**
 * 取消注册
 */
export function unregisterToast() {
  toastInstance = null
}

// ============ Toast API ============

/**
 * 显示成功提示
 */
export function success(message: string, duration?: number) {
  toastInstance?.show({ message, type: 'success', duration })
}

/**
 * 显示错误提示
 */
export function error(message: string, duration?: number) {
  toastInstance?.show({ message, type: 'error', duration })
}

/**
 * 显示信息提示
 */
export function info(message: string, duration?: number) {
  toastInstance?.show({ message, type: 'info', duration })
}

/**
 * 显示自定义提示
 */
export function show(options: ToastOptions) {
  toastInstance?.show(options)
}

/**
 * 手动隐藏
 */
export function hide() {
  toastInstance?.hide()
}

// ============ 导出 ============

export const toast = {
  success,
  error,
  info,
  show,
  hide
}

export default toast
