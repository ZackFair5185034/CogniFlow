#!/usr/bin/env node
// postinstall 钩子：修复 file: 模式下 .pnpm 软链缺失问题
// pnpm 11 在 file: 引用时偶尔漏建 .pnpm/<file+...>/node_modules/@vue-flow/core/ 软链
// 导致 Vite dev server 解析 @vue-flow/core/dist/style.css 失败

import { existsSync, mkdirSync, symlinkSync, readlinkSync } from 'node:fs'
import { dirname, resolve } from 'node:path'

const PROJECT = process.cwd()
const FORK_SRC = '/home/wanglei/vue-flow/packages/core'
const WEBUI_PNPM = resolve(PROJECT, 'node_modules/.pnpm')

if (!existsSync(WEBUI_PNPM)) {
  console.log('[fix-symlink] no .pnpm dir, skipping')
  process.exit(0)
}

const { readdirSync } = await import('node:fs')
let fixed = 0
for (const dir of readdirSync(WEBUI_PNPM)) {
  if (!dir.startsWith('@vue-flow+core@file+')) continue
  const target = resolve(WEBUI_PNPM, dir, 'node_modules/@vue-flow/core')
  if (existsSync(target)) {
    // 已存在，校验是否指向正确源
    try {
      const link = readlinkSync(target)
      if (link === FORK_SRC) continue
    } catch {}
  }
  // 创建缺失的目录和软链
  const inner = dirname(target)
  if (!existsSync(inner)) mkdirSync(inner, { recursive: true })
  try {
    if (existsSync(target)) {
      // 已存在但指向不对，移除
      const { unlinkSync } = await import('node:fs')
      unlinkSync(target)
    }
    symlinkSync(FORK_SRC, target)
    fixed++
    console.log(`[fix-symlink] created: ${dir}/node_modules/@vue-flow/core -> ${FORK_SRC}`)
  } catch (e) {
    console.warn(`[fix-symlink] failed: ${dir} (${e.message})`)
  }
}

if (fixed > 0) {
  console.log(`[fix-symlink] fixed ${fixed} vue-flow core symlink(s)`)
} else {
  console.log('[fix-symlink] all symlinks OK')
}
