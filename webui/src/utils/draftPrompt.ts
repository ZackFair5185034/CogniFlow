// -*- coding: utf-8 -*-
/**
 * 草稿恢复提示框的打开状态跟踪。
 *
 * 背景 (2026-10-24 人工走查发现):
 * 草稿提示框用的是 ElMessageBox —— 它挂在 body 上, **不随组件卸载而消失**。
 * 若用户在弹框打开期间离开页面(或开发期 HMR 重挂载), 旧弹框会残留;
 * 再次进入同一张图又会弹一个 —— 最终多个「恢复草稿」弹框层层叠加,
 * 旧弹框的 Promise 还落进了已卸载的组件, 用户点「放弃」会误清草稿。
 *
 * 这里用「打开序号」跟踪当前草稿提示框的状态, 让组件在卸载时能精确关闭
 * 自己的那一个, 而不是盲目关闭全局 MessageBox。
 *
 * 用序号而不是布尔量的原因: 旧组件的 Promise 回调是异步落地的,
 * 它执行 close 时新组件可能已经打开了新的弹框 —— 布尔量会被误清,
 * 序号可以据此判断「这个 close 还算不算数」。
 */

/** 草稿提示框的打开序号 —— 0 表示当前没有打开的草稿提示框 */
let promptSeq = 0

/** 打开草稿提示框, 返回本次的序号 (关闭时凭此精确配对) */
export function openDraftPrompt(): number {
  promptSeq += 1
  return promptSeq
}

/**
 * 关闭草稿提示框。
 * 只有序号与当前一致时才生效 —— 避免旧组件的异步回调误关新组件的弹框。
 */
export function closeDraftPrompt(seq: number): void {
  if (seq === promptSeq) promptSeq = 0
}

/** 当前是否有未关闭的草稿提示框 */
export function hasActiveDraftPrompt(): boolean {
  return promptSeq !== 0
}

/** 重置模块状态 (供单元测试使用) */
export function resetDraftPromptState(): void {
  promptSeq = 0
}
