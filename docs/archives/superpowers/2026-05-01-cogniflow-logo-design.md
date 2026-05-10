# CogniFlow Logo 设计规范

## 1. 概念与愿景

CogniFlow 是一个通用视觉感知处理框架，集模型训练、测试、推理、规则引擎于一体。Logo 需要传达"融合"与"智能感知"的核心概念，同时具备科技感与专业性。

## 2. 设计方向

- **形态**: 抽象几何拼接型
- **风格**: 科技感、未来感、简洁有力
- **配色**: 紫蓝撞色对角渐变

## 3. 设计方案："CF交织"

### 3.1 主 Logo（256x256）

**核心概念：**
- 左侧半圆环缺口形成"C"形，紫色
- 右侧方形框架形成"F"形，青蓝色
- 两图形中心交叠处有3个连接节点，形成数据流动网络
- 整体构图形成"C"+"F"交织融合的视觉效果

**SVG 结构：**

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

**渐变规格：**
- 渐变 ID：`cfGradient`
- 起点：左下角 `#8B5CF6`（紫色）
- 终点：右上角 `#00D4FF`（青蓝色）
- 渐变角度：对角线（135度）

### 3.2 Favicon（32x32 & 16x16）

**简化版本设计：**
- 保留"C"形半圆和"F"形框架的交叉形态
- 中心3个节点简化为1个核心圆点
- 线条宽度适当加粗以适应小尺寸
- 使用纯色或双色线条（不使用渐变）

**32x32 规格：**

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

### 3.3 颜色规范

| 颜色名称 | 色值 | 用途 |
|---------|------|------|
| 紫色 | `#8B5CF6` | Logo 主体色、C 形、节点点缀 |
| 青蓝色 | `#00D4FF` | Logo 主体色、F 形、节点点缀 |
| 深色背景 | `#1a1a2e` | Logo 容器背景（可选） |
| 白色 | `#FFFFFF` | 节点高光、强调元素 |

### 3.4 尺寸规范

| 用途 | 推荐尺寸 | 最小尺寸 |
|------|---------|---------|
| 主 Logo | 256x256 | 64x64 |
| Favicon | 32x32 | 16x16 |
| 网站标题栏 | 32x32 | 16x16 |

## 4. 文件输出

### 4.1 文件列表

| 文件路径 | 尺寸 | 格式 |
|---------|------|------|
| `webui/public/logo.svg` | 256x256 | SVG |
| `webui/public/favicon.svg` | 32x32 | SVG |

### 4.2 更新文件

- `webui/index.html` - 更新 favicon 引用
- `webui/src/App.vue` - 添加主 Logo 引用

## 5. 验收标准

1. Logo 清晰可辨，在 64x64 以上尺寸完整呈现
2. Favicon 在 16x16 下仍然可识别为 CF 交织图形
3. 紫蓝渐变平滑自然，无色带断层
4. 深色背景下有足够的对比度
5. SVG 文件可无损缩放