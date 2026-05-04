<template>
  <!-- 规则设计器 - 顶层全屏页面，不走 App 布局 -->
  <router-view v-if="$route.meta.layout === 'none'" />

  <!-- 普通页面 - 带 App 布局 -->
  <div v-else class="app-container">
    <!-- 背景效果 -->
    <div class="bg-grid"></div>
    <div class="bg-glow"></div>
    <div class="scanline"></div>

    <!-- 侧边导航 -->
    <aside class="sidebar" :class="{ collapsed }">
      <div class="logo">
        <img class="logo-icon" src="/logo.svg" alt="CogniFlow">
        <div class="logo-text">
          <span class="logo-title">CogniFlow</span>
          <span class="logo-sub">Visual Perception</span>
        </div>
      </div>

      <nav class="nav-menu">
        <router-link
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          class="nav-item"
          :class="{ active: isNavActive(item.path) }"
        >
          <component :is="item.icon" class="nav-icon" />
          <span class="nav-text">{{ item.label }}</span>
          <span class="nav-indicator"></span>
        </router-link>
      </nav>

      <div class="sidebar-footer">
        <div class="status-dot" :class="{ online: isOnline }"></div>
        <span class="status-text">{{ isOnline ? '系统在线' : '离线' }}</span>
      </div>

      <!-- 折叠按钮：放在侧边栏内部，绝对定位 -->
      <button class="collapse-btn" :class="{ collapsed }" @click="toggleSidebar" :title="collapsed ? '展开菜单' : '收起菜单'">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
          <line x1="3" y1="6" x2="21" y2="6" class="top-line"></line>
          <line x1="3" y1="12" x2="21" y2="12" class="mid-line"></line>
          <line x1="3" y1="18" x2="21" y2="18" class="bot-line"></line>
        </svg>
      </button>
    </aside>

    <!-- 主内容区 -->
    <main class="main-content">
      <header class="top-bar">
        <div class="top-actions">
          <span class="time-display">{{ currentTime }}</span>
          <button class="action-btn" @click="refreshData">
            <RefreshIcon />
          </button>
        </div>
      </header>

      <div class="content-area">
        <router-view v-slot="{ Component }">
          <transition name="page-fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, h } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const isOnline = ref(true)
const currentTime = ref('')
const collapsed = ref(false)

const toggleSidebar = () => {
  collapsed.value = !collapsed.value
}

const HomeIcon = () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
  h('path', { d: 'M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z' }),
  h('polyline', { points: '9 22 9 12 15 12 15 22' })
])

const FolderIcon = () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
  h('path', { d: 'M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z' })
])

const BoxIcon = () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
  h('path', { d: 'M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 003 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0021 16z' }),
  h('polyline', { points: '3.27 6.96 12 12.01 20.73 6.96' }),
  h('line', { x1: '12', y1: '22.08', x2: '12', y2: '12' })
])

const ChartIcon = () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
  h('line', { x1: '18', y1: '20', x2: '18', y2: '10' }),
  h('line', { x1: '12', y1: '20', x2: '12', y2: '4' }),
  h('line', { x1: '6', y1: '20', x2: '6', y2: '14' })
])

const RocketIcon = () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
  h('path', { d: 'M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 00-2.91-.09z' }),
  h('path', { d: 'M12 15l-3-3a22 22 0 012-3.95A12.88 12.88 0 0122 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 01-4 2z' }),
  h('path', { d: 'M9 12H4s.55-3.03 2-4c1.62-1.08 5 0 5 0' }),
  h('path', { d: 'M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5' })
])

const FlowIcon = () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
  h('circle', { cx: '5', cy: '12', r: '3' }),
  h('circle', { cx: '19', cy: '12', r: '3' }),
  h('path', { d: 'M8 12h8M13 9l3 3-3 3' })
])

const RefreshIcon = () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
  h('polyline', { points: '23 4 23 10 17 10' }),
  h('polyline', { points: '1 20 1 14 7 14' }),
  h('path', { d: 'M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15' })
])

const navItems = [
  { path: '/', label: '控制台', icon: HomeIcon },
  { path: '/atlas', label: '图集管理', icon: FolderIcon },
  { path: '/models', label: '模型管理', icon: BoxIcon },
  { path: '/training', label: '模型训练', icon: ChartIcon },
  { path: '/launch', label: '模型测试', icon: RocketIcon },
  { path: '/rule-engine', label: '规则引擎', icon: FlowIcon },
]

const pageTitles: Record<string, string> = {
  '/': '控制台',
  '/atlas': '图集管理',
  '/atlas/': '图集详情',
  '/models': '模型管理',
  '/training': '模型训练',
  '/launch': '模型测试',
  '/rule-engine': '规则引擎',
}

const currentPageTitle = computed(() => {
  const path = route.path
  if (path.endsWith('/') && path !== '/') {
    return pageTitles[path.slice(0, -1)] || '详情'
  }
  return pageTitles[path] || 'CogniFlow'
})

const isNavActive = (path: string) => {
  if (path === '/') {
    return route.path === '/'
  }
  return route.path.startsWith(path)
}

const refreshData = () => {
  window.location.reload()
}

let timeInterval: number
onMounted(() => {
  const updateTime = () => {
    const now = new Date()
    const year = now.getFullYear()
    const month = String(now.getMonth() + 1).padStart(2, '0')
    const day = String(now.getDate()).padStart(2, '0')
    const hour = String(now.getHours()).padStart(2, '0')
    const minute = String(now.getMinutes()).padStart(2, '0')
    const second = String(now.getSeconds()).padStart(2, '0')
    const weekDays = ['日', '一', '二', '三', '四', '五', '六']
    const weekDay = weekDays[now.getDay()]
    currentTime.value = `${year}/${month}/${day} ${hour}:${minute}:${second} 星期${weekDay}`
  }
  updateTime()
  timeInterval = window.setInterval(updateTime, 1000)
})

onUnmounted(() => {
  clearInterval(timeInterval)
})
</script>

<style lang="scss">
// App 布局专用样式
// 公共样式已抽取到 @/style/index.scss

.app-container {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

// 背景效果
.bg-grid {
  position: fixed;
  inset: 0;
  background-image:
    linear-gradient(rgba(0, 240, 255, 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0, 240, 255, 0.03) 1px, transparent 1px);
  background-size: 50px 50px;
  pointer-events: none;
  z-index: 0;
}

.bg-glow {
  position: fixed;
  top: -50%;
  left: -50%;
  width: 200%;
  height: 200%;
  background:
    radial-gradient(ellipse at 20% 20%, rgba(0, 240, 255, 0.08) 0%, transparent 50%),
    radial-gradient(ellipse at 80% 80%, rgba(255, 0, 170, 0.06) 0%, transparent 50%);
  pointer-events: none;
  z-index: 0;
  animation: glowPulse 10s ease-in-out infinite;
}

.scanline {
  position: fixed;
  inset: 0;
  background: repeating-linear-gradient(
    0deg,
    transparent,
    transparent 2px,
    rgba(0, 0, 0, 0.1) 2px,
    rgba(0, 0, 0, 0.1) 4px
  );
  pointer-events: none;
  z-index: 1000;
  opacity: 0.3;
}

// 侧边栏
.sidebar {
  width: clamp(180px, 12vw, 240px);
  background: var(--bg-secondary);
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  padding: 20px 0;
  position: relative;
  z-index: 11;
  flex-shrink: 0;
  transition: width 0.3s ease;
  overflow: hidden;

  &::before {
    content: '';
    position: absolute;
    top: 0;
    right: 0;
    width: 1px;
    height: 100%;
    background: linear-gradient(180deg, var(--accent-cyan), var(--accent-magenta));
    opacity: 0.5;
  }

  &.collapsed {
    width: 64px;

    .logo-text,
    .nav-text,
    .nav-indicator {
      display: none;
    }

    .logo {
      justify-content: center;
      padding: 0 12px 30px;
    }

    .nav-item {
      justify-content: center;
      padding: 14px;
    }

    .sidebar-footer {
      padding: 15px 12px;
      justify-content: center;

      .status-text {
        display: none;
      }
    }
  }
}

.collapse-btn {
  position: absolute;
  top: 50%;
  right: 8px;
  transform: translateY(-50%);
  width: 28px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  transition: color 0.2s ease;
  z-index: 20;

  &:hover {
    color: var(--accent-cyan);
  }

  svg {
    width: 20px;
    height: 20px;
    transition: transform 0.3s ease, opacity 0.3s ease;
  }

  line {
    transition: transform 0.3s ease, opacity 0.3s ease;
    transform-origin: center;
  }

  &.collapsed {
    svg {
      transform: translateX(4px);
    }

    .top-line {
      transform: translateX(3px);
      opacity: 0.6;
    }

    .mid-line {
      transform: translateX(6px);
      opacity: 0.4;
    }

    .bot-line {
      transform: translateX(3px);
      opacity: 0.6;
    }
  }
}

.logo {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 20px 30px;
  border-bottom: 1px solid var(--border-color);
}

.logo-icon {
  width: 40px;
  height: 40px;
  animation: iconPulse 3s ease-in-out infinite;
}

.logo-text {
  display: flex;
  flex-direction: column;
}

.logo-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: 1px;
}

.logo-sub {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  color: var(--accent-cyan);
  letter-spacing: 2px;
  text-transform: uppercase;
}

.nav-menu {
  flex: 1;
  padding: 20px 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 20px;
  color: var(--text-secondary);
  text-decoration: none;
  position: relative;
  transition: all 0.3s ease;

  &::before {
    content: '';
    position: absolute;
    left: 0;
    top: 50%;
    transform: translateY(-50%);
    width: 3px;
    height: 0;
    background: var(--accent-cyan);
    transition: height 0.3s ease;
  }

  &:hover {
    background: var(--bg-hover);
    color: var(--text-primary);
  }

  &.active {
    background: linear-gradient(90deg, rgba(0, 240, 255, 0.1), transparent);
    color: var(--accent-cyan);

    &::before {
      height: 24px;
      box-shadow: var(--glow-cyan);
    }

    .nav-indicator {
      opacity: 1;
      box-shadow: var(--glow-cyan);
    }
  }
}

.nav-icon {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
}

.nav-text {
  font-size: 14px;
  font-weight: 500;
  white-space: nowrap;
  transition: opacity 0.3s ease;
}

.nav-indicator {
  margin-left: auto;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--accent-cyan);
  opacity: 0;
  transition: opacity 0.3s ease;
}

.sidebar-footer {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 15px 12px;
  border-top: 1px solid var(--border-color);

  .status-text {
    transition: opacity 0.3s ease, width 0.3s ease;
    white-space: nowrap;
    overflow: hidden;
  }
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--accent-orange);
  box-shadow: 0 0 10px var(--accent-orange);

  &.online {
    background: var(--accent-green);
    box-shadow: 0 0 10px var(--accent-green);
    animation: statusPulse 2s ease-in-out infinite;
  }
}

.status-text {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  color: var(--text-muted);
}

// 主内容区
.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  position: relative;
  z-index: 10;
  overflow: hidden;
}

.top-bar {
  height: 56px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding: 0 20px;
  position: relative;
  flex-shrink: 0;

  &::after {
    content: '';
    position: absolute;
    bottom: 0;
    left: 0;
    width: 100%;
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--accent-cyan), transparent);
    opacity: 0.5;
  }
}

.top-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.time-display {
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
  color: var(--text-secondary);
  letter-spacing: 0.5px;
}

.top-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.action-btn {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s ease;

  &:hover {
    background: var(--bg-hover);
    border-color: var(--accent-cyan);
    color: var(--accent-cyan);
  }

  svg {
    width: 16px;
    height: 16px;
  }
}

.content-area {
  flex: 1;
  padding: 12px 16px;
  overflow-y: auto;
  position: relative;
  background: var(--bg-primary);
  min-width: 0;

  &::-webkit-scrollbar {
    width: 6px;
  }

  &::-webkit-scrollbar-track {
    background: var(--bg-secondary);
  }

  &::-webkit-scrollbar-thumb {
    background: var(--border-color);
    border-radius: 3px;

    &:hover {
      background: var(--text-muted);
    }
  }
}

@keyframes glowPulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}

@keyframes iconPulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.05); }
}

@keyframes statusPulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
</style>
