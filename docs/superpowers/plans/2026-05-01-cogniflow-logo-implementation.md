# CogniFlow Logo 实施方案

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal：** 为 CogniFlow 创建专业的 Logo 和 Favicon 图标

**Architecture：** 使用 SVG 矢量图形创建可无损缩放的 Logo，包含渐变和几何图形组合

**Tech Stack：** SVG（可缩放矢量图形）

---

## 文件清单

| 文件路径 | 操作 | 说明 |
|---------|------|------|
| `webui/public/logo.svg` | 创建 | 主 Logo（256x256，带渐变） |
| `webui/public/favicon.svg` | 创建 | Favicon（32x32，纯色） |
| `webui/index.html` | 修改 | 更新 favicon 引用 |

---

## 实施步骤

### Task 1: 创建主 Logo SVG

**文件：** 创建 `webui/public/logo.svg`

- [ ] **Step 1: 创建 logo.svg 文件**

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256">
  <defs>
    <!-- 紫蓝对角渐变：左下紫到右上蓝 -->
    <linearGradient id="cfGradient" x1="0%" y1="100%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#8B5CF6"/>
      <stop offset="100%" stop-color="#00D4FF"/>
    </linearGradient>
  </defs>

  <!-- C 形（左侧半圆环） -->
  <path d="M 80 48
           A 80 80 0 1 0 80 208"
        fill="none"
        stroke="url(#cfGradient)"
        stroke-width="24"
        stroke-linecap="round"/>

  <!-- F 形（右侧方形框架） -->
  <path d="M 176 48
           L 176 64
           L 112 64
           L 112 112
           L 160 112
           L 160 128
           L 112 128
           L 112 192
           L 176 192"
        fill="none"
        stroke="url(#cfGradient)"
        stroke-width="24"
        stroke-linecap="round"
        stroke-linejoin="round"/>

  <!-- 连接节点（中心交叠处） -->
  <circle cx="128" cy="128" r="12" fill="#00D4FF"/>
  <circle cx="108" cy="108" r="8" fill="#8B5CF6"/>
  <circle cx="148" cy="148" r="8" fill="#00D4FF"/>
</svg>
```

---

### Task 2: 创建 Favicon SVG

**文件：** 创建 `webui/public/favicon.svg`

- [ ] **Step 1: 创建 favicon.svg 文件**

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
  <!-- C 形 -->
  <path d="M 10 6 A 10 10 0 1 0 10 26"
        fill="none"
        stroke="#8B5CF6"
        stroke-width="3"
        stroke-linecap="round"/>
  <!-- F 形 -->
  <path d="M 22 6 L 22 8 L 14 8 L 14 14 L 20 14 L 20 16 L 14 16 L 14 26 L 22 26"
        fill="none"
        stroke="#00D4FF"
        stroke-width="3"
        stroke-linecap="round"
        stroke-linejoin="round"/>
  <!-- 中心节点 -->
  <circle cx="16" cy="16" r="2.5" fill="#8B5CF6"/>
</svg>
```

---

### Task 3: 更新 index.html

**文件：** 修改 `webui/index.html:5`

- [ ] **Step 1: 更新 favicon 引用**

将 `<link rel="icon" type="image/svg+xml" href="/vite.svg" />` 替换为：
```html
<link rel="icon" type="image/svg+xml" href="/favicon.svg" />
```

---

### Task 4: 验证与提交

- [ ] **Step 1: 验证文件存在性**

Run: `ls -la webui/public/logo.svg webui/public/favicon.svg`
Expected: 两个文件存在

- [ ] **Step 2: 提交更改**

```bash
git add webui/public/logo.svg webui/public/favicon.svg webui/index.html
git commit -m "feat(webui): 添加 CogniFlow 专业 Logo 和 Favicon"
```