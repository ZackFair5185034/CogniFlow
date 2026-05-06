<script setup lang="ts">
/**
 * Toast 通知组件
 *
 * 支持三种类型：success（成功）、error（错误）、info（信息）
 * 提供全局单例模式，通过 toastApi 调用。
 */
import { ref, watch, onMounted, onUnmounted } from 'vue'

// ============ Toast 类型定义 ============

export type ToastType = 'success' | 'error' | 'info'

export interface ToastOptions {
  message: string
  type?: ToastType
  duration?: number
}

// ============ 全局状态 ============

const toast = ref<{
  show: boolean
  message: string
  type: ToastType
}>({
  show: false,
  message: '',
  type: 'info'
})

let timer: ReturnType<typeof setTimeout> | null = null

// ============ 暴露方法 ============

function show(options: ToastOptions) {
  // 清除之前的定时器
  if (timer) {
    clearTimeout(timer)
  }

  toast.value.message = options.message
  toast.value.type = options.type || 'info'
  toast.value.show = true

  // 自动隐藏
  timer = setTimeout(() => {
    toast.value.show = false
  }, options.duration || 3000)
}

function hide() {
  toast.value.show = false
  if (timer) {
    clearTimeout(timer)
    timer = null
  }
}

// 暴露给外部使用
defineExpose({ show, hide })
</script>

<template>
  <transition name="toast">
    <div
      v-if="toast.show"
      class="toast-notification"
      :class="toast.type"
      @click="hide"
    >
      <!-- 类型图标 -->
      <span v-if="toast.type === 'success'" class="toast-icon">✓</span>
      <span v-else-if="toast.type === 'error'" class="toast-icon">✕</span>
      <span v-else class="toast-icon">ℹ</span>

      <!-- 消息内容 -->
      <span class="toast-message">{{ toast.message }}</span>
    </div>
  </transition>
</template>

<style scoped>
.toast-notification {
  position: fixed;
  bottom: 80px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 24px;
  border-radius: 8px;
  font-size: 14px;
  z-index: 2000;
  cursor: pointer;
  animation: toastIn 0.3s ease;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
}

.toast-notification.success {
  background: linear-gradient(135deg, #00ff88, #00aa66);
  color: #000;
}

.toast-notification.error {
  background: linear-gradient(135deg, #ff4466, #cc0033);
  color: #fff;
}

.toast-notification.info {
  background: #1e1e2e;
  border: 1px solid #2a2a3a;
  color: #ccc;
}

.toast-icon {
  font-size: 16px;
  font-weight: bold;
}

.toast-message {
  white-space: nowrap;
}

@keyframes toastIn {
  from {
    opacity: 0;
    transform: translateX(-50%) translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateX(-50%) translateY(0);
  }
}

.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s ease;
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(20px);
}
</style>
