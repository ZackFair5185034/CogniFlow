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
├── backend/                      # FastAPI 后端
│   ├── app.py                   # 应用入口
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
│   └── services/
│       └── rule_engine/         # 规则引擎核心
│           ├── executor.py      # Kahn 拓扑排序 + 层内并行
│           ├── graph_manager.py # 图 CRUD + 验证
│           ├── registry.py      # 节点注册表
│           ├── scheduler.py     # Cron 定时调度
│           ├── websocket_manager.py # 规则 WS 推送
│           └── nodes/          # 节点实现
│               ├── triggers.py    # 触发器
│               ├── conditions.py  # 条件
│               ├── actions.py     # 动作
│               ├── logic.py      # 逻辑
│               └── ...
├── engine/                     # 核心视觉感知包
│   ├── __init__.py            # 包初始化，27 个公开接口
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
│   └── annotation/             # 标注工具
├── webui/                      # Vue3 前端
│   ├── src/
│   │   ├── api/              # API 调用封装
│   │   ├── components/       # 公共组件
│   │   ├── router/           # 路由配置（9 条路由）
│   │   ├── stores/           # Pinia 状态管理
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

## 6. 依赖管理

- 使用 `requirements.txt` 管理依赖
- 开发依赖放在 `extras_require["dev"]`
- 定期更新依赖版本

## 7. WebUI 前端规范

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
│   ├── router/            # 路由配置
│   ├── stores/            # Pinia 状态管理
│   ├── utils/             # 工具函数
│   ├── views/             # 页面组件
│   ├── App.vue            # 根组件
│   └── main.ts            # 入口文件
├── public/                # 静态资源
├── uno.config.ts          # UnoCSS 配置
├── eslint.config.mjs      # ESLint 9 配置
├── vite.config.ts         # Vite 配置
├── tsconfig.json          # TypeScript 配置
└── package.json
```

### 7.3 按钮体系

CogniFlow WebUI 使用全局统一的 `.ui-btn` 按钮体系，定义在 `webui/src/style/_common.scss` 和 `webui/src/style/index.scss`。

**按钮层级：**

| 类名 | 用途 | 尺寸 |
|------|------|------|
| `.ui-btn` | 默认按钮 | `padding: 8px 16px`，`font-size: 14px`，`border-radius: 8px` |
| `.ui-btn-primary` | 主操作按钮（青色渐变） | 继承默认尺寸 |
| `.ui-btn-secondary` | 次级按钮（透明背景） | 继承默认尺寸 |
| `.ui-btn-sm` | 紧凑按钮（工具栏等） | `padding: 6px 14px`，`font-size: 13px`，`border-radius: 6px` |
| `.ui-btn-small` | 与 `.ui-btn-sm` 等效 | 同上 |
| `.ui-btn-danger` | 危险操作（红色渐变） | 继承默认尺寸 |
| `.ui-btn-icon` | 图标按钮（36×36） | `width/height: 36px`，`padding: 0` |

**使用规范：**
- 页面主操作按钮使用 `.ui-btn .ui-btn-primary`
- 工具栏/卡片内操作使用 `.ui-btn .ui-btn-sm`
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

### 7.6 代码规范

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

### 7.6.1 Element Plus 表单组件规范

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

**深色主题适配：**

Element Plus 默认样式在深色主题下可能与项目主题不一致。在文件 scoped `<style>` 末尾添加 `:deep()` 覆盖：

```scss
// el-input / el-select 背景边框适配
:deep(.el-input__wrapper),
:deep(.el-select__wrapper) {
  background: var(--bg-primary) !important;
  box-shadow: none !important;
  border: 1px solid var(--border-color);
}
:deep(.el-input__wrapper:hover),
:deep(.el-select__wrapper:hover) {
  border-color: var(--accent-cyan);
}
:deep(.el-input__wrapper.is-focus),
:deep(.el-select__wrapper.is-focus) {
  border-color: var(--accent-cyan);
  box-shadow: 0 0 0 1px var(--accent-cyan) inset !important;
}
:deep(.el-input__inner),
:deep(.el-select__placeholder) {
  color: var(--text-primary);
}

// el-select 下拉菜单
:deep(.el-select-dropdown) {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
}
:deep(.el-select-dropdown__item) {
  color: var(--text-primary);
}
:deep(.el-select-dropdown__item.hover),
:deep(.el-select-dropdown__item:hover) {
  background: var(--bg-hover);
}
:deep(.el-select-dropdown__item.is-selected) {
  color: var(--accent-cyan);
}

// el-checkbox / el-slider 主题色
:deep(.el-checkbox__input.is-checked .el-checkbox__inner),
:deep(.el-slider__bar) {
  background: var(--accent-cyan);
  border-color: var(--accent-cyan);
}
```

**例外：`type="file"` 隐藏输入**

`display: none` 的 `<input type="file">` 用于程序化触发文件对话框（如按钮触发），保持原生实现，无需替换为 `el-upload`。

### 7.7 ESLint 规则

```javascript
// eslint.config.mjs 核心规则
{
  '@typescript-eslint/no-explicit-any': 'warn',
  '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
  '@typescript-eslint/consistent-type-imports': ['error', { prefer: 'type-imports' }],
  'prefer-const': 'error',
  'prefer-template': 'error',
}
```

### 7.8 Git 提交规范（前端）

提交前端代码时，scope 使用以下值：
- `webui`: WebUI 通用修改
- `webui/api`: API 相关
- `webui/components`: 组件相关
- `webui/views`: 页面相关

### 7.9 常用命令

```bash
cd webui
pnpm install          # 安装依赖
pnpm dev            # 开发服务器
pnpm build          # 生产构建
pnpm build:type     # TypeScript 类型检查
pnpm lint           # ESLint 检查
pnpm lint:fix       # ESLint 自动修复
```

## 8. 许可证

MIT License
