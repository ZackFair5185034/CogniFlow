# CogniFlow 项目规范

## 1. 项目概述

CogniFlow 是一个通用视觉感知处理框架，集模型训练、模型测试、模型推理、规则引擎于一体，支持图像/视频采集、视觉特征提取、目标检测、模型训练部署和可视化规则编排。

## 2. 代码规范

### 2.1 注释要求

**所有注释必须使用中文**

- 所有 Python 文件的头部注释
- 类和函数的 docstring
- 代码行内注释
- README 和文档

### 2.2 注释格式

```python
# -*- coding: utf-8 -*-
"""模块名称 - 模块功能描述。

详细的功能说明和使用示例。
"""

class ClassName:
    """类名 - 类功能描述。

    类的详细说明，包含参数和返回值说明。
    """

    def method(self, param1: str, param2: int) -> bool:
        """方法名称 - 方法功能描述。

        Args:
            param1: 参数1的描述
            param2: 参数2的描述

        Returns:
            返回值的描述
        """
        # 代码行内注释也使用中文
        result = do_something()  # 中文注释说明
        return result
```

### 2.3 命名规范

- 类名：`PascalCase`（如 `ScreenCapture`）
- 函数名：`snake_case`（如 `capture_frame`）
- 常量：`UPPER_SNAKE_CASE`（如 `MAX_BUFFER_SIZE`）
- 私有成员：前缀 `_`（如 `_internal_method`）

### 2.4 代码风格

- 使用 4 空格缩进
- 每行最大长度：100 字符
- 使用类型注解
- 推荐使用 `from typing import` 进行类型导入

## 3. 项目结构

```
CogniFlow/
├── app.py                       # 应用入口
├── backend/                      # FastAPI 后端
│   ├── __init__.py
│   ├── database.py              # SQLAlchemy ORM + SQLite
│   ├── schemas.py               # Pydantic 模型
│   ├── websocket_manager.py     # WebSocket 管理
│   ├── core/                    # 模型基础设施
│   │   ├── backends/           # 推理设备自动检测
│   │   ├── formats/            # 多格式处理器 (YOLO/ONNX/OpenVINO)
│   │   └── export/            # 模型导出器
│   ├── routers/                 # API 路由
│   │   ├── atlas.py            # 图集管理
│   │   ├── image.py            # 图片管理
│   │   ├── annotation.py       # 标注管理
│   │   ├── category.py         # 类别管理（树形目录）
│   │   ├── model.py            # 模型管理 + 多格式文件
│   │   ├── training.py         # 训练管理 + 进度推送
│   │   ├── yolo_training.py   # YOLO 训练核心
│   │   ├── inference.py        # 图片/视频推理（双线程流水线）
│   │   ├── ws_stream.py       # 视频流 WebSocket 推送
│   │   ├── launch.py          # 模型启动（⚠️仅模拟）
│   │   ├── rule_engine.py     # 规则图 CRUD + 执行
│   │   ├── websocket.py        # 通用 WebSocket
│   │   ├── simple_detector.py  # 简单检测器
│   │   └── detection_dataset.py # 检测数据集
│   ├── services/
│   │   └── rule_engine/         # 规则引擎核心
│   │       ├── executor.py      # Kahn 拓扑排序 + 层内并行
│   │       ├── graph_manager.py # 图 CRUD + 验证
│   │       ├── models.py        # 数据模型定义
│   │       ├── exceptions.py    # 异常定义
│   │       ├── registry.py      # 节点注册表
│   │       ├── scheduler.py     # Cron 定时调度
│   │       ├── websocket_manager.py # 规则 WS 推送
│   │       └── nodes/          # 节点实现
│   │           ├── base.py            # 节点基类
│   │           ├── triggers.py        # 触发器
│   │           ├── conditions.py      # 条件
│   │           ├── actions.py         # 动作
│   │           ├── logic.py           # 逻辑
│   │           ├── detection_nodes.py # 检测节点
│   │           ├── input_nodes.py     # 输入节点
│   │           ├── output_nodes.py    # 输出节点
│   │           └── processing_nodes.py # 处理节点
│   ├── utils/                  # 工具模块
│   │   ├── frame_buffer.py     # 帧缓冲区
│   │   └── frame_extract_manager.py # 帧提取管理
│   ├── test_export/            # 导出测试数据
│   │   ├── images/
│   │   └── labels/
│   └── tests/                  # 单元测试
│       └── test_rule_engine/
├── engine/                     # 核心视觉感知包
│   ├── __init__.py            # 包初始化
│   ├── config/                 # 配置模块
│   │   ├── schema.py          # 配置数据类
│   │   └── default.yaml       # 默认配置
│   ├── core/                   # 核心模块
│   │   ├── data_input/        # 数据输入
│   │   │   ├── capture/       # 屏幕采集
│   │   │   └── storage/       # 数据集管理
│   │   ├── vision/            # 视觉处理
│   │   │   ├── features/      # 特征提取
│   │   │   ├── detector/      # 目标检测
│   │   │   └── preprocessor/ # 图像预处理
│   │   ├── rl/               # 强化学习（⚠️未集成）
│   │   │   ├── algorithms/    # PPO/SAC
│   │   │   ├── environment/   # 环境封装
│   │   │   └── trainer/       # 训练器
│   │   └── control/           # 控制接口
│   │       └── input_emulator/ # 输入模拟
│   ├── models/                 # 模型定义
│   │   ├── encoder/
│   │   └── heads/
│   ├── utils/                  # 工具函数
│   └── annotation/             # 标注工具
├── webui/                      # Vue3 前端
│   ├── src/
│   │   ├── api/              # API 调用封装
│   │   ├── components/       # 公共组件
│   │   ├── icons/            # SVG 图标集
│   │   ├── router/           # 路由配置（9 条路由）
│   │   ├── stores/           # Pinia 状态管理
│   │   ├── types/            # TypeScript 类型定义
│   │   ├── utils/            # 工具函数
│   │   ├── views/            # 页面组件（9 个页面）
│   │   ├── style/            # 深色主题设计系统
│   │   ├── App.vue           # 根组件
│   │   └── main.ts           # 入口文件
│   ├── public/               # 静态资源
│   └── COGNIFLOW_DESIGN.md  # 设计规范
├── data/                       # 统一数据目录
│   ├── datasets/             # 训练数据集
│   ├── checkpoints/          # 模型权重
│   ├── model_cache/         # 模型缓存
│   ├── inference_output/     # 推理结果
│   ├── runs/               # YOLO 训练输出
│   └── database/           # SQLite 数据库
├── docs/                      # 文档
├── tests/                     # 单元测试
└── requirements.txt         # 项目依赖
```

## 4. Git 规范

### 4.1 分支命名

- `main` - 主分支，稳定版本
- `develop` - 开发分支
- `feature/<feature-name>` - 功能分支
- `fix/<bug-name>` - 修复分支
- `refactor/<scope>` - 重构分支

### 4.2 提交信息格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Type 类型：**
- `feat`: 新功能
- `fix`: 修复bug
- `docs`: 文档更新
- `style`: 代码格式（不影响功能）
- `refactor`: 重构
- `test`: 测试相关
- `chore`: 构建/工具相关

**示例：**
```
feat(vision): 添加ResNet50骨干网络支持

- 支持ResNet50作为CNN编码器骨干
- 更新配置文件添加resnet50选项
- 添加对应的单元测试

Closes #123
```

### 4.4 项目名称

- 项目全称：CogniFlow
- Python 包名：`engine`（历史原因保留）
- 文档中一律使用 **CogniFlow** 作为项目名称

### 4.3 Gitignore 规则

- Python 缓存：`__pycache__/`、`.pyc`
- 虚拟环境：`venv/`、`env/`
- IDE 配置：`.idea/`、`.vscode/`
- 日志文件：`logs/*.log`
- 数据目录：`data/`（统一数据目录）
- 模型文件：`*.pt`、`.pth`、`.onnx`、`.engine`
- 敏感信息：`.env`、`*.key`
- 前端构建产物：`webui/dist/`

## 5. 测试规范

- 所有新功能必须包含单元测试
- 使用 `pytest` 框架
- 测试文件放在 `tests/` 目录
- 覆盖率目标：核心模块 > 80%
- **运行规则引擎测试必须用 `PYTHONPATH=.`**：backend 测试用 `from backend.xxx import` 但项目无 conftest/pyproject.toml，`backend/` 不在 `sys.path`。命令：`PYTHONPATH=. python -m pytest backend/tests/`
- 已知遗留失败 1 个：`test_node_executors.py::TestImagePreprocessorNode::test_fallback_when_cv2_missing` — 假设 cv2 不可用，但环境 cv2 已装，走正常错误路径。与本次 phase 无关。

## 6. 文档维护

- **统一格式**：所有设计文档均为 Markdown（`.md`），位于 `docs/*-md/` 目录
- **目录结构**：
  - `docs/research-md/` — 架构设计、技术调研（10 份）
  - `docs/guides-md/` — 使用指南（3 份）
  - `docs/plans-md/` — 迭代计划（4 份）
  - `docs/archives-md/` — 已完成阶段归档（15 份）
  - `docs/dev-md/` — 开发参考（节点手册等）
  - `docs/文档中心.md` — 顶级入口
- **总览索引**：`docs/research-md/rule-engine-index.md`（项目入口，含阶段规划、节点清单、状态评估）
- **HTML → MD 转换器**（仅历史保留）：`scripts/docs/html_to_md.py`（基于 `html.parser`，支持标题/表格/列表/代码块/加粗/多语言嗅探）
- **直接编辑 MD**：2026-06-03 起 HTML 源已清空，新文档直接编辑 MD 文件

## 7. 依赖管理

- 使用 `requirements.txt` 管理依赖
- 开发依赖放在 `extras_require["dev"]`
- 定期更新依赖版本

## 8. WebUI 前端规范

### 7.1 技术栈

- **构建工具**: Vite 8.x
- **CSS 引擎**: UnoCSS (原子化 CSS)
- **框架**: Vue 3.4+ (Composition API)
- **语言**: TypeScript 5.3+
- **UI 组件库**: Element Plus 2.5+
- **代码检查**: ESLint 9.x (Flat Config)

### 7.2 项目结构

```
webui/
├── src/
│   ├── api/               # API 调用封装
│   ├── components/        # 公共组件
│   ├── icons/             # SVG 图标集
│   ├── router/            # 路由配置
│   ├── stores/            # Pinia 状态管理
│   ├── types/             # TypeScript 类型定义
│   ├── utils/             # 工具函数
│   ├── views/             # 页面组件
│   ├── App.vue            # 根组件
│   └── main.ts            # 入口文件
├── public/                # 静态资源
├── uno.config.ts          # UnoCSS 配置
├── eslint.config.ts       # ESLint 9 配置（Flat Config）
├── vite.config.ts         # Vite 配置
├── tsconfig.json          # TypeScript 配置
└── package.json
```

### 7.3 样式体系

CogniFlow WebUI 样式系统由 SCSS 模块组成，定义在 `webui/src/style/` 目录：

```
style/
├── _variables.scss         # CSS 变量（:root）+ SCSS 变量
├── _animations.scss        # @keyframes 动画定义
├── _element-plus-vars.scss # Element Plus CSS 变量主题
├── _element-plus.scss      # Element Plus 全局样式覆盖
├── _common.scss            # .ui-* 组件样式
└── index.scss              # 主入口，@use 导入所有模块
```

#### 按钮体系

全局统一的 `.ui-btn` 按钮体系，定义在 `_common.scss`：

| 类名 | 用途 | 说明 |
|------|------|------|
| `.ui-btn` | 默认按钮 | `padding: 10px 20px`，`font-size: 14px`，`border-radius: 8px`，透明背景+边框 |
| `.ui-btn-primary` | 主操作按钮 | 青色渐变背景 |
| `.ui-btn-success` | 成功操作 | 绿色渐变背景 |
| `.ui-btn-danger` | 危险操作 | 红色渐变背景 |
| `.ui-btn-small` | 紧凑按钮 | `padding: 4px 8px`，`font-size: 13px` |
| `.ui-btn-icon` | 图标按钮 | 36×36 方形，透明背景 |
| `.ui-tag` | 标签 | `.ui-tag-cyan`、`.ui-tag-green`、`.ui-tag-yellow`、`.ui-tag-magenta` |
| `.ui-card` | 卡片容器 | 背景+边框+圆角，悬停顶部渐变条 |
| `.ui-input` | 输入框 | 全宽，深色背景 |
| `.ui-badge` | 徽章 | mono 字体，等宽显示 |
| `.ui-scrollbar` | 滚动条 | 统一滚动条样式 |

**使用规范：**
- 页面主操作按钮使用 `.ui-btn .ui-btn-primary`
- 工具栏/卡片内操作使用 `.ui-btn .ui-btn-small`
- 不允许在视图组件中覆盖 `.ui-btn` 的 padding、border-radius 等基础样式
- 图标按钮使用 `.ui-btn-icon`
- Element Plus 的 `el-button--text` 已全局统一样式为青色

**页面头部结构规范：**
```html
<div class="page-header">
  <div class="header-info">
    <h2>页面标题</h2>
    <span class="subtitle">副标题说明</span>
  </div>
  <button class="ui-btn ui-btn-primary">操作</button>
</div>
```

```scss
.page-header {
  @apply flex justify-between items-center gap-4;
  flex-shrink: 0;
}
.header-info {
  @apply flex items-baseline;
}
.header-info h2 {
  @apply text-2xl font-semibold;
  background: linear-gradient(90deg, var(--text-primary), var(--accent-cyan));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
.header-info .subtitle {
  @apply text-sm text-[var(--text-muted)] ml-3;
}
```

- 根容器使用 `gap-4`（16px）与子元素间距
- 页面标题统一使用渐变色文字（text → accent-cyan）
- 副标题使用 `text-muted`，左侧 `ml-3` 与标题保持间距
- 右侧操作按钮统一使用 `ui-btn-primary`

### 7.5 UnoCSS 样式规范

UnoCSS 是原子化 CSS 引擎，提供即时按需编译。所有原子化样式直接使用 UnoCSS/Tailwind 工具类，scoped SCSS 仅用于复杂结构样式。

**前缀规范：`cf-`（CogniFlow）**

所有项目级快捷方式统一使用 `cf-` 前缀，定义在 `uno.config.ts` 的 `shortcuts` 中。

**快捷方式完整列表：**

| 名称 | 用途 | 实际样式 |
|------|------|----------|
| `cf-btn` | 默认按钮 | 胶囊形卡片边框按钮 |
| `cf-btn-primary` | 主操作按钮 | 黑色胶囊背景 |
| `cf-btn-brand` | 品牌强调按钮 | 青色渐变背景 |
| `cf-btn-small` | 紧凑按钮 | 小尺寸胶囊 |
| `cf-btn-icon` | 图标按钮 | 40×40 圆形透明 |
| `cf-card` | 卡片容器 | 背景+边框+圆角 |
| `cf-card-header` | 卡片头部 | flex+分隔线 |
| `cf-card-content` | 卡片内容区 | p-6 |
| `cf-flex` | flex 容器 | `flex` |
| `cf-flex-col` | 纵向 flex | `flex flex-col` |
| `cf-items-center` | 垂直居中 | `items-center` |
| `cf-justify-center` | 水平居中 | `justify-center` |
| `cf-justify-between` | 两端对齐 | `justify-between` |
| `cf-gap-2` ~ `cf-gap-6` | 间距 | `gap-2` ~ `gap-6` |
| `cf-text-xs` ~ `cf-text-lg` | 文字层级 | 14~20px 不同字重 |
| `cf-text-muted` | 次要文字 | `text-[var(--text-muted)]` |
| `cf-text-secondary` | 辅助文字 | `text-[var(--text-secondary)]` |
| `cf-font-mono` | 等宽字体 | JetBrains Mono |
| `cf-font-bold` | 加粗 | `font-bold` |
| `cf-badge` | 徽章 | mono+边框+大写 |
| `cf-input` | 输入框 | 全宽+边框+聚焦态 |
| `cf-animate-fade-in` | 淡入动画 | fadeIn keyframes |
| `cf-transition` | 通用过渡 | `transition-all duration-200` |
| `cf-page-header` | 页面头部 | flex+间隙+不缩放 |
| `cf-dialog-overlay` | 对话框遮罩 | 固定定位+模糊 |
| `cf-dialog-panel` | 对话框面板 | 最大宽度 450px |
| `cf-table-wrapper` | 表格容器 | 横向滚动 |
| `cf-toolbar` | 工具栏 | flex+两端对齐 |
| `cf-content-area` | 内容区 | flex-1+溢出隐藏 |
| `cf-panel` | 侧边面板 | 固定宽度+背景 |
| `cf-loading` | 加载状态 | 绝对定位居中 |
| `cf-empty` | 空状态 | 居中+内边距 |
| `cf-scroll-y` | 纵向滚动 | `overflow-y-auto` |
| `cf-scrollbar` | 滚动条样式 | 1.5px 宽度 |

**使用示例：**
```html
<button class="cf-btn">默认按钮</button>
<button class="cf-btn-primary">主要按钮</button>
<div class="cf-card">卡片内容</div>
```

**样式迁移原则：**
- 简单结构样式（flex、gap、颜色、边框、圆角）→ UnoCSS 模板类
- 复杂结构样式（动画 keyframes、复杂选择器、嵌套规则）→ scoped SCSS
- 动态值（:style 绑定）→ 直接写 CSS 变量或内联样式
- 组件私有样式（局部使用）→ scoped SCSS
- 通用样式（多处复用）→ uno.config.ts 添加 cf- 快捷方式

### 7.4 代码规范

**Vue 组件规范：**
- 使用 `<script setup lang="ts">` 语法
- 组件文件使用 PascalCase 命名（如 `UserProfile.vue`）
- Props 使用 TypeScript 类型定义
- 事件使用 `defineEmits` 声明

**命名规范：**
- 组件名：PascalCase（如 `UserCard`）
- 事件名：camelCase（如 `update:modelValue`）
- CSS 类名：kebab-case（如 `user-card`）

**TypeScript 严格规范：**

**tsconfig.json 严格模式（已启用）：**
```json
{
  "strict": true,
  "strictNullChecks": true,
  "noUnusedLocals": true,
  "noUnusedParameters": true,
  "noFallthroughCasesInSwitch": true
}
```

**ESLint 强制规则：**
| 规则 | 级别 | 说明 |
|------|------|------|
| `no-explicit-any` | warn | 禁止 `any`，用 `unknown` 代替 |
| `@typescript-eslint/consistent-type-definitions` | error | 对象类型用 `interface` |
| `@typescript-eslint/consistent-type-imports` | error | 类型导入必须用 `import type` |
| `@typescript-eslint/no-unused-vars` | error | 未使用变量报错（下划线前缀例外） |
| `@typescript-eslint/prefer-nullish-coalescing` | error | 优先用 `??` 而非 `\|\|` |
| `@typescript-eslint/prefer-optional-chain` | error | 优先用 `?.` 而非 `&&` 链 |
| `prefer-const` | error | 变量初始化后不变则用 `const` |
| `prefer-template` | error | 字符串拼接用模板字面量 |
| `object-shorthand` | error | 对象方法用简写形式 |
| `quote-props`: as-needed | error | 仅在必要时引述属性名 |

**类型定义规范：**
```typescript
// ✅ 对象类型用 interface
interface UserProfile {
  id: number
  name: string
  email: string
  created_at?: string
}

// ✅ 联合类型和原始类型别名用 type
type Status = 'pending' | 'running' | 'completed' | 'failed'
type ID = number | string

// ✅ 类型导入
import type { TrainingJobResponse } from '@/types/api'

// ✅ 字面量断言
const statusMap = {
  pending: '等待中',
  running: '进行中',
} as const

// ✅ unknown 代替 any（需要类型守卫）
function processData(data: unknown) {
  if (typeof data === 'string') {
    // data 在这里被收窄为 string
    console.log(data.toUpperCase())
  }
}
```

**模板中动态索引的类型处理：**

Vue 模板中 `Record<string, T>[key]` 会产生类型错误，应提取为辅助函数：
```typescript
// ❌ 模板中直接访问会产生 TS 错误
// {{ nodeConfig[key] }}

// ✅ 在 script 中定义辅助函数
function getNodeValue(key: string): string | number | boolean | null {
  return nodeConfig[key] ?? null
}

// 模板中
// {{ getNodeValue(key) }}
```

**reactive 对象的类型推断：**

显式声明 reactive 对象的类型，避免隐式 `{}`：
```typescript
// ❌ 隐式空对象类型
const contextMenu = reactive({
  show: false,
  target: null as unknown,
})

// ✅ 显式声明字段类型
const contextMenu = reactive({
  show: false,
  x: 0,
  y: 0,
  target: null as unknown,
  targetType: null as 'node' | 'edge' | 'pane' | null
})
```

**组件 Props 和 Emit 类型：**

```typescript
// ✅ Props 使用 defineProps 泛型
const props = defineProps<{
  title: string
  count?: number
}>()

// ✅ Emit 使用 defineEmits 泛型
const emit = defineEmits<{
  (e: 'update', value: string): void
  (e: 'delete', id: number): void
}>()
```

**axios 响应数据类型的处理：**

API 响应数据在运行前类型不确定，应对 `res.data` 做显式类型断言：
```typescript
// ✅ 从 @/types/api 导入接口
import type { TrainingJobResponse } from '@/types/api'

const res = await trainingApi.listJobs()
const jobs = res.data as TrainingJobResponse[]
```

**样式规范：**
- 使用 UnoCSS 原子化类名编写样式
- 使用 CSS 变量管理主题颜色
- 组件样式使用 `scoped`
- 避免行内样式（除了动态值）

### 7.4.1 Element Plus 表单组件规范

**禁止使用原生 HTML 表单标签，所有表单输入必须使用 Element Plus 组件：**

| 原生标签 | Element Plus 组件 | 说明 |
|---------|------------------|------|
| `<input type="text">` | `<el-input>` | 文本输入 |
| `<input type="number">` | `<el-input-number>` | 数字输入 |
| `<input type="range">` | `<el-slider>` | 范围滑块 |
| `<input type="checkbox">` | `<el-checkbox>` | 复选框 |
| `<input type="file">` | `<el-upload>` | 文件上传 |
| `<select>` + `<option>` | `<el-select>` + `<el-option>` | 下拉选择 |
| `<textarea>` | `<el-input type="textarea">` | 多行文本 |

**深色主题适配（CSS 变量方式）：**

在 `src/style/_element-plus-vars.scss` 中覆盖 Element Plus 设计令牌（推荐方式，比 scoped `:deep()` 更优雅）：

```scss
:root {
  // CogniFlow 品牌主色替换 EP 默认蓝色
  --el-color-primary: #00f0ff;
  --el-text-color-primary: #ffffff;
  --el-text-color-regular: #d0d0e0;
  --el-text-color-secondary: #8888aa;
  --el-text-color-placeholder: #555566;
  --el-border-color: #2a2a3a;
  --el-border-color-light: #222230;
  --el-fill-color-blank: #0a0a0f;
  --el-bg-color: #0a0a0f;
  --el-bg-color-page: #0a0a0f;
  --el-bg-color-overlay: #1a1a24;
}
```

全局 `:deep()` 样式覆盖（背景/边框/下拉面板，放在 `src/style/_element-plus.scss` 中）：

```scss
// el-input / el-select 背景边框适配
.el-input__wrapper,
.el-select__wrapper {
  background: var(--bg-primary) !important;
  box-shadow: none !important;
  border: 1px solid var(--border-color) !important;
}
// 下拉面板（Teleport 渲染，必须全局）
.el-select-dropdown {
  background: var(--bg-card) !important;
  border: 1px solid var(--border-color) !important;
}
// el-button link 类型（AtlasList 等操作按钮）
.el-button.is-link {
  color: var(--accent-cyan) !important;
}
```

**说明：** Element Plus 的 el-select / el-dropdown 下拉面板使用 `<Teleport to="body">` 渲染到 DOM 末尾，Vue scoped 样式无法穿透，必须在全局 `index.scss` 中覆盖。

**例外：`type="file"` 隐藏输入**

`display: none` 的 `<input type="file">` 用于程序化触发文件对话框（如按钮触发），保持原生实现，无需替换为 `el-upload`。

### 7.6 ESLint 规则

```javascript
// eslint.config.ts 核心规则
{
  '@typescript-eslint/no-explicit-any': 'warn',
  '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
  '@typescript-eslint/consistent-type-imports': ['error', { prefer: 'type-imports' }],
  'prefer-const': 'error',
  'prefer-template': 'error',
}
```

### 7.7 Git 提交规范（前端）

提交前端代码时，scope 使用以下值：
- `webui`: WebUI 通用修改
- `webui/api`: API 相关
- `webui/components`: 组件相关
- `webui/views`: 页面相关

### 7.8 常用命令

```bash
cd webui
pnpm install          # 安装依赖
pnpm dev            # 开发服务器
pnpm build          # 生产构建
pnpm build:type     # TypeScript 类型检查
pnpm lint           # ESLint 检查
pnpm lint:fix       # ESLint 自动修复
```

## 8. 文档规范

### 8.1 文档类型

项目文档按用途分为五类，每类有明确的定位和编写要求：

| 类型 | 目录 | 用途 | 示例 |
|------|------|------|------|
| **用户文档** | `docs/guides/` | 面向最终用户的操作手册 | 功能使用、配置说明 |
| **开发文档** | `docs/dev/` | 面向开发者的技术参考 | API 文档、架构说明 |
| **计划文档** | `docs/plans/` | 迭代计划和待办清单 | 规则引擎迭代计划、待办清单 |
| **研究文档** | `docs/research/` | 探索性文档 | 技术调研、方案对比 |
| **归档文档** | `docs/archives/` | 历史版本保留 | 旧版本说明 |

**README.md 除外**，所有文档一律使用 **HTML** 编写，禁止使用 Markdown。

**原因：** Markdown 在复杂布局、样式控制和嵌入交互内容时能力有限，HTML 可提供更精细的控制和一致性。

### 8.2 HTML 文档编写规范

**文件组织：**
```
docs/
├── css/
│   └── main.css          # 文档全局样式（必须）
├── guides/               # 用户文档
├── dev/                  # 开发文档
├── plans/                # 计划文档
├── research/             # 研究文档
├── archives/            # 归档文档
└── 文档中心.html        # 文档首页入口
```

**文件命名：**
- 使用 kebab-case 小写字母 + 连字符（例：`user-guide.html`、`api-reference.html`）
- 避免使用中文文件名
- 每个文档目录下应有 `index.html` 作为入口

**HTML 文档头部结构：**
```html
<!-- -*- coding: utf-8 -*- -->
<!--
  功能名称 - 功能简述

  文档用途说明，包含适用读者、前置条件。
-->
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>功能名称 - CogniFlow 文档</title>
  <link rel="stylesheet" href="../css/main.css">
</head>
<body>
  <div class="doc-container">
    <!-- 文档内容 -->
  </div>
</body>
</html>
```

**内容结构规范：**

每个 HTML 文档应按以下层级组织内容：

1. **文档标题**（`.doc-title`）— 文档主标题，仅一个
2. **文档副标题**（`.doc-subtitle`）— 文档目的和范围说明
3. **章节**（`.doc-section`）— 按逻辑划分的内容区块
4. **章节标题**（`.doc-section-title`）— 章节小标题
5. **段落、列表、表格、代码块**— 具体内容

**禁止事项：**
- 禁止使用内联 `style` 属性，所有样式必须在 `docs/css/main.css` 中定义
- 禁止使用 `<font>`、`<center>` 等废弃标签
- 禁止使用表格做布局（仅用于展示结构化数据）
- 禁止在文档中硬编码颜色值，统一使用 CSS 变量

**可复用样式类（定义在 `docs/css/main.css`）：**

| 类名 | 用途 |
|------|------|
| `.doc-container` | 文档主体容器，居中，最大宽度 900px |
| `.doc-title` | 文档主标题，渐变色文字 |
| `.doc-subtitle` | 文档副标题，次要文字色 |
| `.doc-section` | 内容章节区块，margin-bottom: 32px |
| `.doc-section-title` | 章节标题，青色下划线分隔 |
| `.doc-table` | 表格，全宽，深色主题 |
| `.doc-code` / `.doc-code-block` | 代码块，等宽字体，深色背景 |
| `.doc-list` | 无序列表，青色圆点前缀 |
| `.doc-badge` | 徽章，mono 字体，青色边框 |
| `.doc-divider` | 水平分割线 |

### 8.3 样式编写规范

**文件：`docs/css/main.css`**

- 文件头部包含中文注释说明文件用途
- 所有颜色使用 CSS 变量，禁止硬编码十六进制值
- 选择器尽量简短，避免三层以上的嵌套
- 响应式布局使用相对单位（em、rem、%），避免固定像素值

**CSS 变量命名约定（docs 专用）：**
```css
/* 文档专用变量放在 [data-doc] 作用域下 */
[data-doc] {
  --doc-bg-primary: #0a0a0f;
  --doc-text-primary: #ffffff;
  --doc-accent: #00f0ff;
}
```

### 8.4 编写流程

1. **规划** — 确定文档属于哪类（用户/开发/设计/研究），决定放在哪个目录
2. **编写** — 按 8.2 的头部结构创建 HTML 文件，引用 `docs/css/main.css`
3. **自审** — 检查是否有内联样式、硬编码颜色、废弃标签
4. **更新入口** — 如有必要，更新对应目录的 `index.html` 添加链接
5. **提交** — Git commit message 使用 `docs:` 前缀

### 8.5 评审清单

提交文档前逐项检查：

- [ ] 文件放在正确目录（guides/dev/plans/research/archives）
- [ ] 使用 `.html` 扩展名，非 `.md`
- [ ] 头部包含中文注释说明文档用途
- [ ] 引用了 `docs/css/main.css`
- [ ] 无内联 `style` 属性
- [ ] 无硬编码十六进制颜色值
- [ ] 无废弃 HTML 标签
- [ ] 有对应的 `index.html` 入口链接（若是子文档）

## 9. 许可证

MIT License

<!-- rtk-instructions v2 -->
# RTK (Rust Token Killer) - Token-Optimized Commands

## Golden Rule

**Always prefix commands with `rtk`**. If RTK has a dedicated filter, it uses it. If not, it passes through unchanged. This means RTK is always safe to use.

**Important**: Even in command chains with `&&`, use `rtk`:
```bash
# ❌ Wrong
git add . && git commit -m "msg" && git push

# ✅ Correct
rtk git add . && rtk git commit -m "msg" && rtk git push
```

## RTK Commands by Workflow

### Build & Compile (80-90% savings)
```bash
rtk cargo build         # Cargo build output
rtk cargo check         # Cargo check output
rtk cargo clippy        # Clippy warnings grouped by file (80%)
rtk tsc                 # TypeScript errors grouped by file/code (83%)
rtk lint                # ESLint/Biome violations grouped (84%)
rtk prettier --check    # Files needing format only (70%)
rtk next build          # Next.js build with route metrics (87%)
```

### Test (60-99% savings)
```bash
rtk cargo test          # Cargo test failures only (90%)
rtk go test             # Go test failures only (90%)
rtk jest                # Jest failures only (99.5%)
rtk vitest              # Vitest failures only (99.5%)
rtk playwright test     # Playwright failures only (94%)
rtk pytest              # Python test failures only (90%)
rtk rake test           # Ruby test failures only (90%)
rtk rspec               # RSpec test failures only (60%)
rtk test <cmd>          # Generic test wrapper - failures only
```

### Git (59-80% savings)
```bash
rtk git status          # Compact status
rtk git log             # Compact log (works with all git flags)
rtk git diff            # Compact diff (80%)
rtk git show            # Compact show (80%)
rtk git add             # Ultra-compact confirmations (59%)
rtk git commit          # Ultra-compact confirmations (59%)
rtk git push            # Ultra-compact confirmations
rtk git pull            # Ultra-compact confirmations
rtk git branch          # Compact branch list
rtk git fetch           # Compact fetch
rtk git stash           # Compact stash
rtk git worktree        # Compact worktree
```

Note: Git passthrough works for ALL subcommands, even those not explicitly listed.

### GitHub (26-87% savings)
```bash
rtk gh pr view <num>    # Compact PR view (87%)
rtk gh pr checks        # Compact PR checks (79%)
rtk gh run list         # Compact workflow runs (82%)
rtk gh issue list       # Compact issue list (80%)
rtk gh api              # Compact API responses (26%)
```

### JavaScript/TypeScript Tooling (70-90% savings)
```bash
rtk pnpm list           # Compact dependency tree (70%)
rtk pnpm outdated       # Compact outdated packages (80%)
rtk pnpm install        # Compact install output (90%)
rtk npm run <script>    # Compact npm script output
rtk npx <cmd>           # Compact npx command output
rtk prisma              # Prisma without ASCII art (88%)
```

### Files & Search (60-75% savings)
```bash
rtk ls <path>           # Tree format, compact (65%)
rtk read <file>         # Code reading with filtering (60%)
rtk grep <pattern>      # Search grouped by file (75%). Format flags (-c, -l, -L, -o, -Z) run raw.
rtk find <pattern>      # Find grouped by directory (70%)
```

### Analysis & Debug (70-90% savings)
```bash
rtk err <cmd>           # Filter errors only from any command
rtk log <file>          # Deduplicated logs with counts
rtk json <file>         # JSON structure without values
rtk deps                # Dependency overview
rtk env                 # Environment variables compact
rtk summary <cmd>       # Smart summary of command output
rtk diff                # Ultra-compact diffs
```

### Infrastructure (85% savings)
```bash
rtk docker ps           # Compact container list
rtk docker images       # Compact image list
rtk docker logs <c>     # Deduplicated logs
rtk kubectl get         # Compact resource list
rtk kubectl logs        # Deduplicated pod logs
```

### Network (65-70% savings)
```bash
rtk curl <url>          # Compact HTTP responses (70%)
rtk wget <url>          # Compact download output (65%)
```

### Meta Commands
```bash
rtk gain                # View token savings statistics
rtk gain --history      # View command history with savings
rtk discover            # Analyze Claude Code sessions for missed RTK usage
rtk proxy <cmd>         # Run command without filtering (for debugging)
rtk init                # Add RTK instructions to CLAUDE.md
rtk init --global       # Add RTK to ~/.claude/CLAUDE.md
```

## Token Savings Overview

| Category | Commands | Typical Savings |
|----------|----------|-----------------|
| Tests | vitest, playwright, cargo test | 90-99% |
| Build | next, tsc, lint, prettier | 70-87% |
| Git | status, log, diff, add, commit | 59-80% |
| GitHub | gh pr, gh run, gh issue | 26-87% |
| Package Managers | pnpm, npm, npx | 70-90% |
| Files | ls, read, grep, find | 60-75% |
| Infrastructure | docker, kubectl | 85% |
| Network | curl, wget | 65-70% |

Overall average: **60-90% token reduction** on common development operations.
<!-- /rtk-instructions -->