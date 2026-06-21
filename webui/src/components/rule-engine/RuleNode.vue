<template>
  <!--
    v-memo (Phase B + LOD-1): 拖拽时只让 wrapper transform 变化,
    节点壳内部 vdom 完全跳过 patch, 50 节点场景渲染开销从 O(N) 降到 O(1).
    依赖选择依据: 拖动时 data.id/status/category 都不变.
    lodLevel 也在依赖里: 缩放/展开切换时强制 patch 一次, 之后稳定.
    selected 走 VueFlow wrapper 的 CSS class, 不需列入依赖.
  -->
  <div
    v-memo="[data.id, data.status, data.category, lodLevel, isExpanded, hasMissingRequired, isDisabled]"
    v-bind="$attrs"
    class="rule-node"
    :class="[`category-${data.category}`, `lod-${lodLevel}`, { expanded: isCollapsed, 'missing-required': hasMissingRequired, 'is-disabled': isDisabled }]"
    :data-status="data.status || 'idle'"
    :data-lod="lodLevel"
    :data-expanded="isCollapsed ? 'true' : 'false'"
    :data-missing-required="hasMissingRequired ? 'true' : 'false'"
    :data-disabled="isDisabled ? 'true' : 'false'"
    @contextmenu.prevent="emit('contextmenu', $event)"
    @dblclick.stop="emit('dblclick', $event)"
  >
    <!-- ========== LOD 0/1 通用: 标题栏 ========== -->
    <div class="node-header">
      <div
        class="node-icon"
        :class="data.category"
      >
        <SvgIcon :name="data.category" />
      </div>
      <div class="node-title">
        <span class="node-label">{{ data.label || data.type }}</span>
        <!-- P1-1 (2026-06-19): 必填端口未连警告 (LOD 1+) -->
        <span
          v-if="hasMissingRequired && lodLevel >= 1"
          class="missing-required-badge"
          :title="missingRequiredTitle"
        >⚠ {{ missingRequiredHandles.length }}</span>
      </div>
      <!-- Phase 19.5+: 单节点折叠/展开按钮 (替代工具栏全局按钮) -->
      <button
        v-if="lodLevel >= 1"
        class="node-collapse-btn"
        :title="isCollapsed ? '展开节点' : '折叠节点 (隐藏内嵌配置)'"
        @click.stop="toggleSelf"
        @dblclick.stop
      >
        <SvgIcon :name="isCollapsed ? 'expand-all' : 'collapse-all'" />
      </button>
    </div>

    <!-- ========== LOD 1: 端口区域 + 端口名 (LOD 0 隐藏) ==========
         Phase 17.1+: 显示端口名 label (老大反馈: 不知道连接点是什么意思)
         紧凑显示: input 在 Handle 右侧, output 在 Handle 左侧 -->
    <template v-if="lodLevel >= 1">
      <div
        v-if="(data.inputs?.length || 0) > 0 || (data.outputs?.length || 0) > 0"
        class="node-ports"
      >
        <div
          v-for="input in data.inputs"
          :key="'in-' + input.name"
          class="port-item port-in"
          :class="{ 'is-missing-required': input.required && !isInputConnected(input.name) }"
        >
          <Handle
            :id="input.name"
            type="target"
            :position="Position.Left"
            :class="['node-handle', `type-${(input.type ?? 'any').toLowerCase()}`, { 'is-connected': isInputConnected(input.name), 'is-missing-required': input.required && !isInputConnected(input.name) }]"
          />
          <span
            v-if="input.label || input.name"
            class="port-label"
            :title="input.label || input.name"
          >
            {{ input.label || input.name }}
            <!-- P1-1 (2026-06-19): 必填端口加 * -->
            <span
              v-if="input.required"
              class="required-marker"
            >*</span>
          </span>
        </div>
        <div
          v-for="output in data.outputs"
          :key="'out-' + output.name"
          class="port-item port-out"
        >
          <span
            v-if="output.label || output.name"
            class="port-label"
            :title="output.label || output.name"
          >{{ output.label || output.name }}</span>
          <Handle
            :id="output.name"
            type="source"
            :position="Position.Right"
            :class="['node-handle', `type-${(output.type ?? 'any').toLowerCase()}`, { 'is-connected': isOutputConnected(output.name) }]"
          />
        </div>
      </div>
    </template>

    <!-- 执行状态指示 (所有级别) -->
    <div
      v-if="data.status && data.status !== 'idle'"
      class="node-status"
    >
      <div
        class="status-indicator"
        :class="data.status"
        :title="statusTitle"
      />
    </div>

    <!-- ========== 节点内嵌配置 (Phase 19.3+: 默认全展开显示, 双击折叠到 200px) ==========
         2026-06-21 修复: 移除 @mousedown.stop
           原因: .stop 会 stopPropagation, 导致 mousedown 无法冒泡到
           .vue-flow__viewport 上的 d3-drag handler, 用户抓配置区拖不动节点.
           保留 @click.stop / @dblclick.stop: 防止点击配置时触发节点选中/折叠切换.
           拖拽排除由 useCogniFlowDrag.ts 的 d3-drag filter 兜底:
           `if (target.closest('.node-config-section')) return false` -->
    <div
      v-if="isExpanded"
      class="node-config-section"
      @click.stop
      @dblclick.stop
    >
      <NodeConfigEditor
        mode="inline"
        :node-id="data.id"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * RuleNode - 节点壳 (Phase LOD-2)
 *
 * 三级 LOD 渲染:
 *   LOD 0 (zoom < 0.5): 仅标题 + 类型图标 (极小, 不可连边)
 *   LOD 1 (0.5 ≤ zoom < 1.0): 标题 + 类型图标 + 端口 (无摘要, 清爽)
 *   LOD 2 (zoom ≥ 1.0 或双击展开): 完整内嵌配置 NodeConfigEditor
 *
 * v-memo 依赖: [data.id, data.status, data.category, lodLevel]
 * - 拖动时所有字段不变 → v-memo 命中 → 0 patch
 * - lodLevel 在依赖里: 缩放/展开切换时强制 patch 一次, 之后稳定
 * - selected 走 CSS (outline) 不触发组件更新
 * - summaryText 已被移除 (Phase 17.1+), 不再是依赖
 */
import { computed } from 'vue'
import { Position, Handle } from '@vue-flow/core'
import { useRuleEngineStore } from '@/stores/ruleEngine'
import NodeConfigEditor from './NodeConfigEditor.vue'

defineOptions({ inheritAttrs: false })

interface Port {
  name: string
  label?: string
  type: string
  /** P1-1 (2026-06-19): 端口是否必填, 未连时显示 ⚠️ */
  required?: boolean
}

interface NodeData {
  id: string
  type: string
  category: string
  label?: string
  description?: string
  inputs?: Port[]
  outputs?: Port[]
  status?: string
  /** P2-A (2026-06-19): 节点是否禁用 (执行时跳过) */
  disabled?: boolean
}

const props = defineProps<{
  data: NodeData
  selected?: boolean
  /** LOD 等级 0/1 (由父组件 RuleCanvas 计算传入, 可选 — 内部会用 store 回退) */
  lodLevel?: 0 | 1
}>()

const emit = defineEmits<{
  (e: 'contextmenu', event: MouseEvent): void
  /**
   * 双击节点 → 父组件 RuleCanvas 调 store.toggleNodeExpanded(id) 进入 LOD 2
   * 用 .stop 阻止冒泡到 VueFlow, 避免触发框选/拖拽
   */
  (e: 'dblclick', event: MouseEvent): void
}>()

const store = useRuleEngineStore()

// ============ 状态指示器 tooltip ============

const statusTitle = computed(() => {
  switch (props.data.status) {
    case 'running': return '正在执行...'
    case 'success': return '执行成功'
    case 'failed': return '执行失败'
    case 'timeout': return '执行超时'
    default: return ''
  }
})

// ============ LOD 默认值 + 派生属性 ============

/**
 * LOD 等级: 优先使用 prop (父组件计算传入), 否则从 store 全局 map 查询.
 * 来自 store 时是响应式的 — 缩放切换会触发重新计算.
 */
const lodLevel = computed<0 | 1>(() => {
  if (props.lodLevel !== undefined) return props.lodLevel
  // Phase 19.7+: 选中状态走 VueFlow 官方 API (selectedNodeIds), 不再从 store 读
  return store.getLodLevel(props.data.id)
})

/**
 * 节点是否处于"全展开"状态 (端口+配置+标题都显示, 280px 宽).
 * 语义 (Phase 19.3+): 默认全展开, 双击 -> 折叠到 200px (只保留标题+端口, 隐藏配置).
 * 反转历史: Phase 17.1~19.2 是默认折叠+双击展开, Phase 19.3 老大拍板默认展开.
 */
const isExpanded = computed<boolean>(() => {
  // expandedNodeIds 集合保留 API 名字, 但语义反转为"折叠中的节点"
  return !store.expandedNodeIds.has(props.data.id)
})

/**
 * 节点是否处于"折叠"状态 (双击触发的, 配置区 hidden, 200px 宽).
 * 这是 .expanded CSS 修饰符的开关 — CSS 期望折叠态 = 激活 .expanded class.
 * isExpanded 和 isCollapsed 必须严格互补, 避免 CSS 误用.
 */
const isCollapsed = computed<boolean>(() => {
  return store.expandedNodeIds.has(props.data.id)
})

// Phase 19.5+: 节点自身折叠/展开 (节点右上角按钮)
function toggleSelf() {
  store.toggleNodeExpanded(props.data.id)
}

// ============ Handle 连接状态 (store 全局索引 O(1) 查询) ============

function isInputConnected(handleId: string): boolean {
  return store.isHandleConnected(props.data.id, handleId, 'target')
}

function isOutputConnected(handleId: string): boolean {
  return store.isHandleConnected(props.data.id, handleId, 'source')
}

// ============ P1-1 (2026-06-19): 未连必填端口检测 ============

/**
 * 必填输入端口的 handle id 列表 (未连时)
 * 触发器节点通常无 input ports, 不参与校验
 */
const missingRequiredHandles = computed<string[]>(() => {
  if (!props.data.inputs) return []
  const missing: string[] = []
  for (const input of props.data.inputs) {
    if (input.required && !isInputConnected(input.name)) {
      missing.push(input.name)
    }
  }
  return missing
})

/** 节点是否有缺失必填输入端口 */
const hasMissingRequired = computed(() => missingRequiredHandles.value.length > 0)

/** 节点标题旁 ⚠️ tooltip 详情 */
const missingRequiredTitle = computed(() => {
  if (!hasMissingRequired.value) return ''
  return `缺失必填输入端口: ${missingRequiredHandles.value.join(', ')}`
})

// ============ P2-A (2026-06-19): 节点禁用状态 ============

/** 节点是否处于禁用态 (执行时被跳过) */
const isDisabled = computed(() => {
  // 双数据源: data.disabled (持久化) 或 store.disabledNodeIds (UI 即时)
  if (props.data.disabled === true) return true
  return store.isNodeDisabled(props.data.id)
})
</script>

<style scoped lang="scss">
/* ============================================
 * 终极轻量节点壳样式 (Phase B 重构)
 * ============================================ */
.rule-node {
  background: linear-gradient(180deg, #2d2d30 0%, #252528 100%);
  border: 1px solid #404044;
  border-radius: 6px;
  width: 280px;  /* Phase 19.3+: LOD 1 默认 280px 全展开 (端口+配置+标题) */
  font-size: 12px;
  color: #e0e0e0;
  position: relative;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,0.05),
    0 2px 8px rgba(0,0,0,0.3);
  /* === GPU 合成层提示 (Tier 0 性能优化) ===
     - contain: layout style  隔离子树对外部布局/样式影响 (去掉 paint! paint containment
       等同 overflow:hidden, 会裁切超出节点壳的 Handle 圆 → 老大反馈"只能看到半个圆")
     - will-change: transform  提示浏览器提前创建独立合成层
     - translateZ(0) + backface-visibility: hidden  兜底强制 layer,避免子像素抖动 */
  contain: layout style;
  will-change: transform;
  transform: translateZ(0);
  backface-visibility: hidden;
  overflow: visible !important;
  /* ========== 2026-06-19: 节点默认 cursor ==========
     Vue Flow 默认给 .vue-flow__node 设了 cursor: grab,
     但我们 2026-06-19 限制了拖动只在 .node-header 触发,
     因此节点的"非标题栏"区域不应再显示 grab, 否则误导用户.
     此处显式覆盖回 default, 标题栏 .node-header 单独设 grab. */
  cursor: default;
}

/* 拖动期间彻底关闭 transition,避免每帧补间触发样式重算 */
.vue-flow__node.dragging .rule-node,
.vue-flow__node.selected.dragging .rule-node {
  transition: none !important;
}

/* P2-I (Phase 17.1): 节点状态切换瞬间禁用 transition
   执行期 50 节点从 idle → running → success 时, transition 期间浏览器 schedule paint
   ~3-5ms/帧. 选中态/拖动态走 .dragging/.selected 锁;
   这里补一刀: data-status 变化时也立即生效, 不补间. */
.rule-node[data-status='running'],
.rule-node[data-status='success'],
.rule-node[data-status='failed'] {
  transition: none !important;
}

/* 标题栏 */
.node-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  border-bottom: 1px solid rgba(255,255,255,0.03);
  /* 2026-06-19: 标题栏 cursor 用 default, 用户明确反馈不喜欢小手样式 */
  cursor: default;
}

/* 展开按钮 (LOD 1 提示) */
.node-expand-btn {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 4px;
  color: rgba(255, 255, 255, 0.5);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s ease;

  &:hover {
    background: rgba(0, 240, 255, 0.1);
    border-color: rgba(0, 240, 255, 0.3);
    color: #00f0ff;
  }
}

/* ========== 2026-06-19: 端口区 cursor ==========
     端口区本身不参与拖动, 但因内嵌 Handle 的 crosshair,
     鼠标进入 .node-ports 应保持 default. */
.node-ports {
  cursor: default;
}

/* ========== 2026-06-19: 配置区 cursor ==========
     内嵌配置 (LOD 2) 的输入控件需要 text 样式,
     但因为 .node-config-section 的 mousedown 已 .stop 阻止冒泡,
     不会触发拖动, cursor 自然继承 .rule-node 的 default.
     这里加 cursor: text 让用户明确知道这是输入区. */
.node-config-section {
  cursor: text;
}

/* ========== LOD 0 极简模式 ========== */
.rule-node.lod-0 {
  width: 120px;
  min-height: 32px;
  border-radius: 4px;
  box-shadow: none;

  .node-header {
    padding: 4px 8px;
    border-bottom: none;
  }
  .node-icon {
    width: 16px;
    height: 16px;
  }
  .node-icon svg { width: 10px; height: 10px; }
  .node-label { font-size: 11px; }
  .node-ports { display: none; }
  .node-config-section { display: none; }   // 极简模式隐藏配置
}

/* ========== 折叠修饰符 (Phase 19.3+: expanded 类 = 折叠态) ========== */
/*
 * 默认 LOD 1 节点 280px 全展开 (端口+配置+标题).
 * 双击 -> 节点加进 expandedNodeIds -> .expanded 修饰符激活 -> 折叠到 200px (隐藏配置).
 * 设计取舍: 折叠态保留端口, 用户仍能继续接线.
 *           节点壳宽度变化 (200px <-> 280px) 走 v-memo, 拖动期 0 性能损失.
 */
.rule-node.lod-1.expanded {
  width: 200px;

  .node-config-section {
    display: none;  // 折叠态强制隐藏配置区
  }
}

.node-icon {
  width: 20px;
  height: 20px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.node-icon svg {
  width: 12px;
  height: 12px;
}

.node-title {
  flex: 1;
  min-width: 0;
}

.node-label {
  font-weight: 600;
  font-size: 12px;
  color: #fff;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: block;
}

// Phase 19.5+: 节点右上角折叠/展开按钮
.node-collapse-btn {
  flex-shrink: 0;
  width: 18px;
  height: 18px;
  margin-left: 4px;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 3px;
  color: #c0c0c8;
  cursor: pointer;
  transition: all 0.15s ease;

  svg {
    width: 12px;
    height: 12px;
  }

  &:hover {
    background: rgba(0, 240, 255, 0.15);
    border-color: var(--accent-blue, #00f0FF);
    color: #00f0FF;
  }

  &:active {
    transform: scale(0.92);
  }
}

/* 分类头部渐变 */
.category-input .node-header { background: linear-gradient(90deg, rgba(76,255,76,0.2), rgba(76,255,76,0.05)); }
.category-detection .node-header { background: linear-gradient(90deg, rgba(88,152,255,0.2), rgba(88,152,255,0.05)); }
.category-processing .node-header { background: linear-gradient(90deg, rgba(255,255,76,0.2), rgba(255,255,76,0.05)); }
.category-action .node-header { background: linear-gradient(90deg, rgba(255,127,76,0.2), rgba(255,127,76,0.05)); }
.category-logic .node-header { background: linear-gradient(90deg, rgba(220,79,220,0.2), rgba(220,79,220,0.05)); }
.category-output .node-header { background: linear-gradient(90deg, rgba(255,76,76,0.2), rgba(255,76,76,0.05)); }

/* 分类图标颜色 */
.category-input .node-icon { background: rgba(76, 255, 76, 0.15); color: #4CFF4C; }
.category-detection .node-icon { background: rgba(0, 240, 255, 0.15); color: #00f0FF; }
.category-processing .node-icon { background: rgba(255, 255, 76, 0.15); color: #FFFF4C; }
.category-action .node-icon { background: rgba(255, 127, 76, 0.2); color: #FF7F4C; }
.category-logic .node-icon { background: rgba(220, 79, 220, 0.15); color: #DC4FDC; }
.category-output .node-icon { background: rgba(255, 76, 76, 0.15); color: #FF4C4C; }

/* 节点摘要 — Phase 17.1+ 已移除, 删死样式 */

/* 节点悬停态 */
.rule-node:hover {
  border-color: #505055;
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,0.08),
    0 4px 16px rgba(0,0,0,0.4);
}

/* 节点执行状态高亮 */
.rule-node[data-status='running'] {
  border-color: #5898ff;
  box-shadow:
    inset 0 1px 0 rgba(88,152,255,0.15),
    0 0 0 1px rgba(88,152,255,0.4),
    0 0 18px rgba(88,152,255,0.25);
}
.rule-node[data-status='success'] {
  border-color: #4CFF4C;
  box-shadow:
    inset 0 1px 0 rgba(76,255,76,0.12),
    0 0 0 1px rgba(76,255,76,0.3),
    0 0 12px rgba(76,255,76,0.18);
}
.rule-node[data-status='failed'] {
  border-color: #FF4C4C;
  box-shadow:
    inset 0 1px 0 rgba(255,76,76,0.12),
    0 0 0 1px rgba(255,76,76,0.3),
    0 0 14px rgba(255,76,76,0.2);
}
.rule-node[data-status='timeout'] {
  border-color: #FFA500;
  box-shadow:
    inset 0 1px 0 rgba(255,165,0,0.12),
    0 0 0 1px rgba(255,165,0,0.3),
    0 0 14px rgba(255,165,0,0.2);
}

/* ========== 节点内嵌配置区 (Phase 19.3+: 默认显示, 折叠态 hidden) ========== */
.node-config-section {
  padding: 8px 10px;
  border-top: 1px solid rgba(255, 255, 255, 0.04);
  background: rgba(0, 0, 0, 0.12);
  max-height: 320px;        // 防止节点太高遮住其他节点
  overflow-y: auto;         // 配置项多时节点内滚动
  &::-webkit-scrollbar { width: 6px; }
  &::-webkit-scrollbar-track { background: transparent; }
  &::-webkit-scrollbar-thumb {
    background: rgba(255, 255, 255, 0.1);
    border-radius: 3px;
    &:hover { background: rgba(255, 255, 255, 0.2); }
  }
}

/* 端口区域 */
.node-ports {
  padding: 6px 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.port-item {
  display: flex;
  align-items: center;
  padding: 0 8px;
  min-height: 20px;
  font-size: 10px;
  color: rgba(255, 255, 255, 0.6);
  /* 关键: .port-item 是 Handle 的父容器, 自身不应拦截鼠标事件,
     否则 mousedown 会落在 .port-item 而不是 .vue-flow__handle, 导致
     d3-drag filter 检测不到 handle, VueFlow Handle 的 onPointerDown 也不触发. */
  pointer-events: none;
  /* 必须: 让 Handle 的 position: absolute 相对于 port-item 而非 node wrapper,
     VueFlow 默认 .vue-flow__handle-right { top: 50% } 把所有右侧 handle 叠在节点中央,
     多个 handle 互相重叠导致 elementFromPoint 只能命中最后一个. */
  position: relative;
}

/* 端口文字 label (Phase 17.1+: 显示端口名, 让用户知道连接点是什么)
   - 紧凑字号 10px
   - input: Handle 在左 label 在右 (默认顺序, 跟 flex 流向一致)
   - output: label 在左 Handle 在右 (见模板, span 在前 Handle 在后) */
.port-label {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.55);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 110px;
  pointer-events: none;        // 不拦截 Handle 鼠标事件
  font-family: 'JetBrains Mono', 'Menlo', monospace;  // 等宽字体让名字对齐
  flex-shrink: 0;
}

/* 但 Handle 必须能接收事件 */
:deep(.vue-flow__handle) {
  pointer-events: all !important;
}

.port-in {
  justify-content: flex-start;
}

.port-out {
  justify-content: flex-end;
}

/* Handle (节点连接点) */
:deep(.vue-flow__handle) {
  width: 10px;
  height: 10px;
  border: 1.5px solid #404044;
  background: #1a1a20;
  transition: border-color 0.15s, background 0.15s;
  overflow: visible !important;
}

/* 显式确认 Handle 在有 connectable 标识时允许事件穿透。
   VueFlow 自带 CSS 中 .vue-flow__handle.connectable 设置 pointer-events: all，
   但 scoped :deep() 选择器优先级可能意外占优，此处重声明以确保交互性 */
:deep(.vue-flow__handle.connectable) {
  pointer-events: all;
  cursor: crosshair;
}

/* ========== P2-B (2026-06-19): 端口吸附高亮 ==========
   全局开关: 当用户在拖连线时, 所有 handles 放大 + 发光
   .is-connecting 由 RuleCanvas 加到 .vue-flow 容器 */
:deep(.vue-flow.is-connecting) .vue-flow__handle.connectable {
  width: 14px !important;
  height: 14px !important;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
  box-shadow: 0 0 0 2px rgba(0, 240, 255, 0.4), 0 0 12px rgba(0, 240, 255, 0.6);
  animation: handle-pulse 1s ease-in-out infinite;
}

@keyframes handle-pulse {
  0%, 100% { box-shadow: 0 0 0 2px rgba(0, 240, 255, 0.4), 0 0 12px rgba(0, 240, 255, 0.6); }
  50% { box-shadow: 0 0 0 3px rgba(0, 240, 255, 0.7), 0 0 18px rgba(0, 240, 255, 0.9); }
}

:deep(.vue-flow__handle.type-image) { border-color: #4CFF4C; }
:deep(.vue-flow__handle.type-bbox) { border-color: #00f0FF; }
:deep(.vue-flow__handle.type-model) { border-color: #FFA500; }
:deep(.vue-flow__handle.type-string) { border-color: #FFFF4C; }
:deep(.vue-flow__handle.type-control),
:deep(.vue-flow__handle.type-trigger) { border-color: #DC4FDC; }
:deep(.vue-flow__handle.type-any) { border-color: #888; }

:deep(.vue-flow__handle.is-connected) {
  background: currentColor;
}

/* ========== P1-1 (2026-06-19): 未连必填端口视觉提示 ========== */

/* 必填端口的 * 标记 */
.required-marker {
  color: #ff5252;
  font-weight: 700;
  margin-left: 2px;
}

/* 必填未连的 handle: 红框 + 呼吸光晕 */
:deep(.vue-flow__handle.is-missing-required) {
  border-color: #ff5252 !important;
  border-width: 2px !important;
  box-shadow: 0 0 0 2px rgba(255, 82, 82, 0.25), 0 0 8px rgba(255, 82, 82, 0.6);
  animation: required-pulse 1.5s ease-in-out infinite;
}

@keyframes required-pulse {
  0%, 100% { box-shadow: 0 0 0 2px rgba(255, 82, 82, 0.25), 0 0 8px rgba(255, 82, 82, 0.6); }
  50% { box-shadow: 0 0 0 3px rgba(255, 82, 82, 0.4), 0 0 14px rgba(255, 82, 82, 0.9); }
}

/* 节点标题旁的 ⚠️ 徽标 */
.missing-required-badge {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  margin-left: 6px;
  padding: 1px 6px;
  border-radius: 8px;
  background: rgba(255, 82, 82, 0.15);
  border: 1px solid rgba(255, 82, 82, 0.4);
  color: #ff5252;
  font-size: 10px;
  font-weight: 600;
  cursor: help;
  flex-shrink: 0;
}

/* 节点整体: 有缺失必填时标题栏轻微红色提示 */
.rule-node.missing-required .node-header {
  background: linear-gradient(90deg, rgba(255, 82, 82, 0.12), rgba(255, 82, 82, 0.04));
}

/* 拖动期间 Vue Flow 默认 .vue-flow__node.dragging 会设 grabbing, 同样覆盖为 default
   (用户 2026-06-19 反馈不喜欢任何小手样式, 拖动期间保持普通箭头) */
:deep(.vue-flow__node.dragging),
:deep(.vue-flow__node.dragging) .rule-node {
  cursor: default !important;
}

/* ========== P2-A (2026-06-19): 节点禁用样式 ========== */
.rule-node.is-disabled {
  opacity: 0.4;
  filter: grayscale(0.7);
  border-style: dashed;
  /* 阻止 hover 抬升感, 让"已禁用"更明显 */
  transition: opacity 0.15s ease;
}

.rule-node.is-disabled:hover {
  opacity: 0.6;
  border-color: #888;
  box-shadow: none;
}

/* 禁用节点标题旁加 [已禁用] 标识 */
.rule-node.is-disabled .node-label::after {
  content: ' ⏸';
  color: #888;
  font-size: 10px;
  margin-left: 4px;
}

/* 状态指示器 */
.node-status {
  position: absolute;
  top: 6px;
  right: 6px;
  pointer-events: none;
}

.status-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.status-indicator.running {
  background: #5898ff;
  box-shadow: 0 0 6px rgba(88, 152, 255, 0.7);
  animation: pulse 1.2s ease-in-out infinite;
}

.status-indicator.success {
  background: #4CFF4C;
  box-shadow: 0 0 6px rgba(76, 255, 76, 0.6);
}

.status-indicator.failed {
  background: #FF4C4C;
  box-shadow: 0 0 6px rgba(255, 76, 76, 0.6);
}

.status-indicator.timeout {
  background: #FFA500;
  box-shadow: 0 0 6px rgba(255, 165, 0, 0.6);
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.6; transform: scale(0.85); }
}
</style>
