# CogniFlow Design Specification v1.0

> 深色主题 AI 推理工具 UI 设计规范

---

## 色彩系统

### 背景色（深色主题）

| Token | Hex | 用途 |
|-------|-----|------|
| `--bg-primary` | `#0a0a0f` | 主背景（最深层） |
| `--bg-secondary` | `#12121a` | 次级背景（卡片/面板） |
| `--bg-card` | `#1a1a24` | 卡片背景 |
| `--bg-hover` | `#22222e` | 悬停状态背景 |
| `--bg-surface-soft` | `#f7f7f5` | 浅色表面（极少数场景） |

### 文字色

| Token | Hex | 用途 |
|-------|-----|------|
| `--text-primary` | `#ffffff` | 主文字 |
| `--text-secondary` | `#a0a0b0` | 次级文字 |
| `--text-muted` | `#606070` | 弱化文字/辅助信息 |

### 边框色

| Token | Hex | 用途 |
|-------|-----|------|
| `--border-color` | `rgba(255, 255, 255, 0.08)` | 默认边框（极淡线条） |
| `--border-active` | `rgba(0, 240, 255, 0.3)` | 聚焦/激活边框 |

### CogniFlow 品牌强调色

| Token | Hex | 用途 |
|-------|-----|------|
| `--accent-cyan` | `#00f0ff` | 主强调色（检测框、进度条、选中态） |
| `--accent-magenta` | `#ff00aa` | 辅助强调色（分类标签、游戏元素） |
| `--accent-green` | `#00ff88` | 成功状态 |
| `--accent-yellow` | `#ffdd00` | 警告/视频相关 |
| `--accent-orange` | `#ff8800` | 次级警告 |
| `--accent-red` | `#ff4466` | 危险/错误状态 |

### 透明度覆盖

```scss
--overlay-light: rgba(255, 255, 255, 0.05);   // 极淡高亮
--overlay-medium: rgba(255, 255, 255, 0.08);   // 中等高亮
--shadow-color: rgba(0, 240, 255, 0.1);        // 青色阴影
```

---

## 字体系统

### 字体族

```scss
--font-sans: 'Inter', 'PingFang SC', 'Microsoft YaHei', sans-serif;
--font-mono: 'JetBrains Mono', 'Fira Code', monospace;
```

### 字号规范

| Token | 字号 | 字重 | 用途 |
|-------|------|------|------|
| `--text-xs` | 12px | 400 | 辅助信息、次级标签 |
| `--text-sm` | 14px | 400 | 正文（当前 14px，历史原因） |
| `--text-base` | 16px | 400 | 较大正文 |
| `--text-lg` | 18px | 600 | 标题 |
| `--text-xl` | 20px | 700 | 页面标题 |

> **注**：字重用于层级表达，而非字号——`weight carries hierarchy, not size`

---

## 间距系统（8px 基准）

| Token | 值 | 用途 |
|-------|-----|------|
| `--spacing-hair` | 1px | 极细分隔线 |
| `--spacing-xxs` | 4px | 紧凑间距 |
| `--spacing-xs` | 8px | 小间距（图标与文字） |
| `--spacing-sm` | 12px | 组件内间距 |
| `--spacing-md` | 16px | 标准间距 |
| `--spacing-lg` | 24px | 区块间距 |
| `--spacing-xl` | 32px | 大区块 |
| `--spacing-xxl` | 48px | 页面级间距 |
| `--spacing-section` | 96px | 段落间距 |

### 响应式间距

```scss
--spacing-page: clamp(16px, 3vw, 32px);       // 页面边距
--spacing-card: clamp(16px, 2vw, 24px);        // 卡片内边距
```

### 面板宽度

```scss
--sidebar-width: clamp(200px, 15vw, 280px);   // 侧边栏
--panel-width: clamp(200px, 18vw, 320px);      // 配置面板
```

---

## 圆角系统

| Token | 值 | 用途 |
|-------|-----|------|
| `--rounded-xs` | 2px | 极小圆角（badge、小标签） |
| `--rounded-sm` | 6px | 小圆角（按钮、输入框） |
| `--rounded-md` | 8px | 中圆角（卡片） |
| `--rounded-lg` | 24px | 大圆角（特殊区块） |
| `--rounded-xl` | 32px | 特大圆角 |
| `--rounded-pill` | 50px | 胶囊形按钮（主要 CTA） |
| `--rounded-full` | 9999px | 全圆角（头像、图标按钮） |

---

## 组件规范

### 检测类别标签（DetClassBadge）

```scss
.det-class {
  padding: 2px 8px;
  border-radius: --rounded-xs (2px);
  font-size: 10px;
  font-weight: 600;
  color: #fff;
  // 颜色由后端 Category.color 决定
}
```

### 检测结果卡片（ResultCard）

```scss
.result-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--rounded-md);  // 8px
  overflow: hidden;
}
```

### 监控台日志条目（ConsoleEntry）

```scss
.console-entry {
  background: rgba(0, 0, 0, 0.15);
  border-radius: var(--rounded-sm);
  margin: 0 4px 2px;
  font-size: 12px;
}
```

### 进度条（ProgressBar）

```scss
.progress-bar-dual {
  height: 6px;
  border-radius: 3px;
  background: var(--border-color);
  overflow: hidden;
}

.progress-playback {
  background: var(--accent-cyan);
  border-radius: 3px;
  box-shadow: 0 0 8px rgba(0, 240, 255, 0.5);
}
```

---

## 状态设计

### 悬停态（Hover）

- 背景：`var(--bg-hover)`
- 边框：`var(--border-active)` 或 `var(--accent-cyan)`
- 过渡：`all 0.15s ease`

### 禁用态（Disabled）

```scss
opacity: 0.3;
cursor: not-allowed;
```

### 聚焦态（Focus）

```scss
outline: 2px solid var(--accent-cyan);
outline-offset: 2px;
```

---

## 阴影规范

```scss
--shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.3);
--shadow-md: 0 4px 12px rgba(0, 0, 0, 0.4);
--shadow-cyan: 0 0 16px rgba(0, 240, 255, 0.2);   // 品牌色阴影
```

---

## 深色主题适配原则

1. **背景层级**：通过明度差异（#0a0a0f → #22222e）建立层次，不依赖阴影
2. **边框策略**：极淡边框 `rgba(255,255,255,0.08)`，聚焦时变为青色
3. **文字层级**：白(#fff) → 灰(#a0a0b0) → 暗灰(#606070)，三级对比
4. **强调色**：Cyan/Magenta 用于需要视觉焦点的场景，不滥用
5. **对比度**：文字与背景对比度 ≥ 4.5:1（WCAG AA）
