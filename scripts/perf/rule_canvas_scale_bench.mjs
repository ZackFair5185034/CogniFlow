// -*- coding: utf-8 -*-
// 规则画布规模基线脚本 - 量化 100/200/400/500 节点的加载与索引性能。
//
// 用法:
//   cd webui && pnpm install --frozen-lockfile
//   node ../scripts/perf/rule_canvas_scale_bench.mjs
//
// 判据: 500 节点索引构建 < 50ms

import { performance } from 'node:perf_hooks'

const SCALES = [100, 200, 400, 500]

/** 构造一个规模为 n 的规则图(节点 + 边) */
function buildGraph(n) {
  const nodes = []
  const edges = []
  for (let i = 0; i < n; i++) {
    nodes.push({
      id: `node_${i}`,
      type: 'ruleNode',
      position: { x: (i % 20) * 220, y: Math.floor(i / 20) * 140 },
      data: { type: i % 2 === 0 ? 'yolo_model' : 'log_action', connections: {} },
    })
    if (i > 0) {
      edges.push({
        id: `edge_${i}`,
        source: `node_${i - 1}`,
        target: `node_${i}`,
        sourceHandle: 'detections',
        targetHandle: 'trigger',
      })
    }
  }
  return { nodes, edges }
}

/** 统计边索引构建耗时 */
function benchIndex(edges) {
  const start = performance.now()
  const index = new Set()
  for (const e of edges) {
    index.add(`${e.target}:${e.targetHandle}:target`)
    index.add(`${e.source}:${e.sourceHandle}:source`)
  }
  return { ms: performance.now() - start, size: index.size }
}

/**
 * 统计数据层框选命中耗时 (Task 16 新增路径)。
 *
 * 旧实现走 DOM 查询, 复杂度与「可见节点数」相关且每次都强制布局;
 * 新实现纯数据层 O(N), 与渲染无关。
 */
function benchRectHit(nodes) {
  const start = performance.now()
  const hit = []
  const left = 0
  const top = 0
  const right = 20 * 220
  const bottom = 10 * 140
  for (const node of nodes) {
    const cx = node.position.x
    const cy = node.position.y
    if (cx >= left && cx <= right && cy >= top && cy <= bottom) {
      hit.push(node.id)
    }
  }
  return { ms: performance.now() - start, size: hit.length }
}

console.log('规模 | 节点数 | 边数 | 索引构建(ms) | 索引条目 | 框选命中(ms) | 命中数')
console.log('-----+-------+------+---------------+---------+-------------+-------')
let worstIndexMs = 0
for (const n of SCALES) {
  const { nodes, edges } = buildGraph(n)
  const { ms, size } = benchIndex(edges)
  const rect = benchRectHit(nodes)
  if (ms > worstIndexMs) worstIndexMs = ms
  console.log(
    `${String(n).padStart(4)} | ${String(nodes.length).padStart(6)} | ${String(edges.length).padStart(5)} | ${ms.toFixed(2).padStart(12)} | ${String(size).padStart(8)} | ${rect.ms.toFixed(2).padStart(12)} | ${rect.size}`
  )
}
console.log('')
console.log(`判据: 500 节点索引构建 < 50ms —— 实测最大 ${worstIndexMs.toFixed(2)}ms`)
if (worstIndexMs >= 50) {
  console.log('不达标: 索引构建超过 50ms')
  process.exitCode = 1
} else {
  console.log('达标')
}
