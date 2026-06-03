<template>
  <!-- 规则设计器 - 顶层全屏页面，不走 App 布局 -->
  <router-view v-if="$route.meta.layout === 'none'" />

  <!-- 普通页面 - 带 App 布局 -->
  <div
    v-else
    class="app-container"
  >
    <!-- 侧边导航 -->
    <aside
      class="sidebar"
      :class="{ collapsed }"
    >
      <button
        class="collapse-btn"
        :class="{ collapsed }"
        :title="collapsed ? '展开菜单' : '收起菜单'"
        @click="toggleSidebar"
      >
        <SvgIcon :name="collapsed ? 'chevron-right' : 'chevron-left'" />
      </button>
      <div class="logo">
        <img
          class="logo-icon"
          src="/logo.svg"
          alt="CogniFlow"
        >
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
          <SvgIcon
            :name="item.icon"
            class="nav-icon"
          />
          <span class="nav-text">{{ item.label }}</span>
        </router-link>
      </nav>

      <div class="sidebar-footer">
        <div
          class="status-dot"
          :class="{ online: isOnline }"
        />
        <span class="status-text">{{ isOnline ? '系统在线' : '离线' }}</span>
      </div>
    </aside>

    <!-- 主内容区 -->
    <main class="main-content">
      <header class="top-bar">
        <div class="top-actions">
          <span class="time-display">{{ currentTime }}</span>
          <button
            class="action-btn"
            title="刷新"
            @click="refreshData"
          >
            <SvgIcon name="refresh" />
          </button>
        </div>
      </header>

      <div class="content-area">
        <router-view v-slot="{ Component }">
          <transition
            name="page-fade"
            mode="out-in"
          >
            <component :is="Component" />
          </transition>
        </router-view>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">

const route = useRoute()
const isOnline = ref(true)
const currentTime = ref('')
const collapsed = ref(false)

const toggleSidebar = () => {
  collapsed.value = !collapsed.value
}

const navItems = [
  { path: '/', label: '控制台', icon: 'home' },
  { path: '/atlas', label: '图集管理', icon: 'folder' },
  { path: '/models', label: '模型管理', icon: 'box' },
  { path: '/training', label: '模型训练', icon: 'chart' },
  { path: '/launch', label: '模型测试', icon: 'rocket' },
  { path: '/rule-engine', label: '规则引擎', icon: 'flow' },
]

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
.app-container {
  display: flex;
  height: 100vh;
  overflow: hidden;
  position: relative;
}

// 侧边栏
.sidebar {
  width: clamp(180px, 12vw, 240px);
  background: var(--bg-secondary);
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  position: relative;
  z-index: 11;
  flex-shrink: 0;
  transition: width 0.2s ease;
  overflow: visible;

  &.collapsed {
    width: 60px;

    .logo-text,
    .nav-text {
      display: none;
    }

    .logo {
      justify-content: center;
      padding: 10px 12px;
    }

    .nav-item {
      justify-content: center;
      padding: 12px;
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
  right: -12px;
  top: 50%;
  transform: translateY(-50%);
  width: 12px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-left: none;
  border-radius: 0 4px 4px 0;
  color: var(--text-muted);
  cursor: pointer;
  z-index: 20;
  padding: 0;
  transition: color 0.15s;

  &:hover {
    color: var(--text-secondary);
  }

  svg {
    width: 10px;
    height: 10px;
  }
}

.logo {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 4px;
  height: 48px;
  border-bottom: 1px solid var(--border-color);
}

.logo-icon {
  width: 36px;
  height: 36px;
  flex-shrink: 0;
}

.logo-text {
  display: flex;
  align-items: center;
  flex-direction: column;
  justify-content: space-around;
  height: 100%;
}

.logo-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: 0.3px;
  line-height: 1;
}

.logo-sub {
  font-family: var(--font-family-mono);
  font-size: 9px;
  color: var(--text-muted);
  letter-spacing: 1px;
  text-transform: uppercase;
  line-height: 1;
}

.nav-menu {
  flex: 1;
  padding: 10px 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  margin: 0 8px;
  border-radius: 6px;
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 13px;
  font-weight: 500;
  transition: all 0.15s ease;

  &:hover {
    background: var(--bg-hover);
    color: var(--text-primary);
  }

  &.active {
    background: var(--accent-blue-muted);
    color: var(--accent-blue);
  }
}

.nav-icon {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
}

.nav-text {
  white-space: nowrap;
  transition: opacity 0.2s ease;
}

.sidebar-footer {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 15px 12px;
  border-top: 1px solid var(--border-color);

  .status-text {
    transition: opacity 0.2s ease, width 0.2s ease;
    white-space: nowrap;
    overflow: hidden;
  }
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--color-warning);
  flex-shrink: 0;

  &.online {
    background: var(--color-success);
  }
}

.status-text {
  font-family: var(--font-family-mono);
  font-size: 10px;
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
  height: 48px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding: 0 20px;
  flex-shrink: 0;
}

.top-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.time-display {
  font-family: var(--font-family-mono);
  font-size: 12px;
  color: var(--text-muted);
}

.action-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 6px;
  color: var(--text-muted);
  cursor: pointer;
  transition: all 0.15s ease;

  &:hover {
    background: var(--bg-hover);
    color: var(--text-secondary);
  }

  svg {
    width: 15px;
    height: 15px;
  }
}

.content-area {
  flex: 1;
  padding: 16px 20px;
  overflow-y: auto;
  position: relative;
  background: var(--bg-primary);
  min-width: 0;

  &::-webkit-scrollbar {
    width: 6px;
  }

  &::-webkit-scrollbar-track {
    background: transparent;
  }

  &::-webkit-scrollbar-thumb {
    background: var(--border-color);
    border-radius: 3px;

    &:hover {
      background: var(--text-muted);
    }
  }
}

// 页面切换淡入淡出
.page-fade-enter-active,
.page-fade-leave-active {
  transition: opacity 0.2s ease;
}

.page-fade-enter-from,
.page-fade-leave-to {
  opacity: 0;
}
</style>
