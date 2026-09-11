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
- **已知遗留失败（2026-06-06 更新）**：
  - `test_node_executors.py::TestImagePreprocessorNode::test_fallback_when_cv2_missing` — 假设 cv2 不可用，但环境 cv2 已装，走正常错误路径。与 phase 无关。
  - 注：原 docs 提到的 5 个 test_api/test_atlas.py 测试文件已不存在（`backend/tests/test_api/` 目录被清理），不再计入遗留失败。
- **测试基线**（2026-06-06）：236 passed（`tests/test_rule_engine/`），1 pre-existing 失败。Phase 14 修复 + test_padding_expansion 修复后从 41 → 236 通过。

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
└── index.scss              # 主入口，@use 导入所有模块
```

> **ENG 修正 (2026-09-12)**：原文档列的 `_common.scss` **已不存在**（2026-06-18 其内容全部迁到 `uno.config.ts` 的 shortcut）。
> 按钮/卡片/标签等组件类现在**只**定义在 `uno.config.ts`，不在 SCSS 文件里。

#### 按钮体系

全局按钮类定义在 **`uno.config.ts` 的 `shortcuts`**（不是 SCSS）：

| 类名 | 用途 | 实际实现 |
|------|------|----------|
| `ui-btn` | 默认按钮 | 13px / `px-4 py-2` / 6px 圆角 / 卡片底+边框 |
| `ui-btn-primary` | 主操作按钮 | 品牌青底 + **深墨字**（`--on-vibrant`） |
| `ui-btn-success` / `ui-btn-danger` | 语义操作 | 语义色底 + 深墨字 |
| `ui-btn-small` / `ui-btn-xs` / `ui-btn-sm` | 紧凑尺寸 | `ui-btn-sm` 是**修饰符**，与基础类组合用 |
| `ui-btn-secondary` | 次要按钮 | 低对比底色，hover 点亮品牌青（修饰符） |
| `ui-btn-icon` | 图标按钮 | 34×34 方形，透明底 |
| `ui-card` / `ui-card-header` / `ui-card-content` | 卡片 | 背景+边框+圆角 |
| `ui-tag` / `ui-tag-blue|green|yellow|red` | 标签 | 语义底 + 语义字 |
| `ui-input` / `ui-badge` / `ui-scrollbar` | 输入/徽章/滚动条 | — |

**使用规范：**
- 页面主操作按钮使用 `ui-btn ui-btn-primary`
- 工具栏/卡片内操作使用 `ui-btn ui-btn-small`
- 修饰符必须与基础类组合：`class="ui-btn ui-btn-primary ui-btn-sm"`
  （`ui-btn-sm` / `ui-btn-secondary` 内部用 `!` 强制覆盖，避免 UnoCSS 生成顺序影响结果）
- **亮色底（品牌青/语义色）上一律用 `text-[var(--on-vibrant)]`，禁止 `text-white`**
  —— 白字在 `#22d3ee` 上仅 1.81:1，在 v1 蓝 `#5898ff` 上也仅 2.86:1，均不可读
- 不允许在视图组件中覆盖基础类的 padding、border-radius

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
  background: linear-gradient(90deg, var(--text-primary), var(--accent));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
.header-info .subtitle {
  @apply text-sm text-[var(--text-muted)] ml-3;
}
```

> 实际写法更简单：直接用 `cf-gradient-text` shortcut（`uno.config.ts` 已定义，6 个视图在用），无需手写 SCSS 块。

- 根容器使用 `gap-4`（16px）与子元素间距
- 页面标题统一使用渐变色文字：`class="cf-gradient-text text-2xl font-semibold"`
- 副标题使用 `text-muted`，左侧 `ml-3` 与标题保持间距
- 右侧操作按钮统一使用 `ui-btn-primary`

### 7.5 UnoCSS 样式规范

UnoCSS 是原子化 CSS 引擎，提供即时按需编译。所有原子化样式直接使用 UnoCSS/Tailwind 工具类，scoped SCSS 仅用于复杂结构样式。

**前缀规范：`ui-`（组件类）与 `cf-`（框架类）**

> **ENG 修正 (2026-09-12)**：原文档声称"所有项目级快捷方式统一使用 `cf-` 前缀"，
> 并列出 34 个 `cf-*`。**实测其中 31 个不存在，且全项目 0 处使用**。
> 实际生效的是 `ui-*` 系列（`ui-btn` 70 处 / `ui-card` 28 处…）。
> 文档与实现对齐后如下；**新代码请按此表写**。

**一、`ui-*` 组件类（`uno.config.ts` 定义，实际在用）**

| 名称 | 用途 |
|------|------|
| `ui-btn` | 按钮基类（13px / `px-4 py-2` / 6px 圆角 / 卡片底） |
| `ui-btn-primary` / `ui-btn-success` / `ui-btn-danger` | 语义按钮，亮底 + 深墨字 |
| `ui-btn-secondary` | 次要按钮（修饰符，hover 点亮品牌青） |
| `ui-btn-small` / `ui-btn-xs` / `ui-btn-sm` | 紧凑尺寸（后两者为修饰符，`ui-btn-sm` 用 `!` 强制覆盖） |
| `ui-btn-icon` | 图标按钮（34×34） |
| `ui-card` / `ui-card-header` / `ui-card-content` | 卡片容器 / 头部 / 内容区 |
| `ui-tag` + `ui-tag-blue` / `-green` / `-yellow` / `-red` | 标签及语义变体 |
| `ui-input` | 输入框（全宽，深色底，聚焦青边） |
| `ui-badge` | 徽章（mono 字体） |
| `ui-scrollbar` | 滚动条样式 |

**二、`cf-*` 框架类（仅这两个体系在用，共 6 个）**

| 名称 | 用途 |
|------|------|
| `cf-gradient-text` | 页面标题渐变文字（6 个视图在用） |
| `cf-loading` / `cf-loading--overlay` / `cf-loading__container` / `cf-loading__ring` / `cf-loading__text` | LoadingSpinner 子元素 |

**三、`--cat-*` 节点分类色板（规则引擎专用，定义在 `_variables.scss`）**

6 类各三个令牌：`--cat-<name>`（主色）/ `--cat-<name>-bg`（18% 底）/ `--cat-<name>-fg`（chip 文字）。

| 分类 | 主色 |
|------|------|
| `input` / `detection` / `processing` | `#58e49e` / `#58bae4` / `#e4c158` |
| `action` / `logic` / `output` | `#e48b58` / `#b158e4` / `#e4586b` |

> 注意 `detection` 原为 `#00f0FF`，因品牌强调色改用青色而**让位**，改为 `#58bae4`。
> 分类色必须在 CSS 里用 `var(--cat-*)`；JS canvas 绘图（如小地图、`ctx.strokeStyle`）
> 用 hex 字面量，因为 `var()` 在 canvas API 上不解析。

**使用示例：**
```html
<button class="ui-btn ui-btn-primary">主要按钮</button>
<button class="ui-btn ui-btn-secondary ui-btn-sm">次要小按钮</button>
<h2 class="cf-gradient-text text-2xl font-semibold">页面标题</h2>
<div class="ui-card">卡片内容</div>
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
  // CogniFlow 品牌主色替换 EP 默认蓝色（v2: 品牌青 #22d3ee）
  --el-color-primary: #22d3ee;
  --el-text-color-primary: #e8e8f0;
  --el-text-color-regular: #c2c2d4;
  --el-text-color-secondary: #9a9ab2;
  --el-text-color-placeholder: #8585a0;
  --el-border-color: #2e2e3c;
  --el-border-color-light: #262632;
  --el-fill-color-blank: #0b0b10;
  --el-bg-color: #0b0b10;
  --el-bg-color-page: #0b0b10;
  --el-bg-color-overlay: #1a1a24;
}
```

> ⚠️ **亮色 primary 底上的前景必须改深墨色**：EP 默认在 primary 底放白字
> （`--el-color-white`），而品牌青是亮色，白字在上面对比度仅 **1.81:1**。
> 凡是「primary 底 + 文字/图标」的 EP 组件，前景统一用 `var(--on-vibrant)`（`#04161a`）：
>
> ```scss
> .el-checkbox__input.is-checked .el-checkbox__inner::after { border-color: var(--on-vibrant) !important; }
> .el-switch.is-checked .el-switch__action { background: var(--on-vibrant) !important; }
> ```
>
> （`el-button` 不受影响：`_element-plus.scss` 已把 `.el-button` 重置为透明底。）

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
  color: var(--accent) !important;
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

> **ENG-P0-1 修复 (2026-06-19)**: 之前 §8 要求"所有文档用 HTML"违反 §6 + 实际现状
> (全 docs/*-md/*.md). 改写为 MD 版, 与 §6 目录约定一致.

### 8.1 文档类型与目录

项目文档按用途分为五类（与 §6 一致）：

| 类型 | 目录 | 用途 | 示例 |
|------|------|------|------|
| **用户文档** | `docs/guides-md/` | 面向最终用户的操作手册 | 功能使用、配置说明 |
| **开发文档** | `docs/dev-md/` | 面向开发者的技术参考 | 节点手册、API 文档 |
| **计划文档** | `docs/plans-md/` | 迭代计划和待办清单 | 规则引擎迭代计划 |
| **研究文档** | `docs/research-md/` | 探索性文档 | 技术调研、方案对比 |
| **归档文档** | `docs/archives-md/` | 已完成阶段归档 | 旧版本说明 |

> 总览索引：`docs/research-md/rule-engine-index.md`（项目入口，含阶段规划、节点清单、状态评估）
> HTML → MD 转换器（仅历史保留）：`scripts/docs/html_to_md.py`
> 直接编辑 MD：2026-06-03 起 HTML 源已清空，新文档直接编辑 MD 文件

### 8.2 编写规范

- **格式**：所有文档使用 **Markdown** 编写（`README.md` 除外，README 仍 MD）
- **编码**：UTF-8，文件头可加 `<!-- -*- coding: utf-8 -*- -->` 注释
- **目录约定**：见 §6
- **命名**：中文标题 + 英文文件名均可，建议 kebab-case（例：`rule-engine-overview.md`）
- **语言**：技术术语保留英文，注释/说明用中文
- **commit 规范**：Git commit message 使用 `docs:` 前缀

### 8.3 评审清单

提交文档前逐项检查：

- [ ] 文件放在正确目录（`*-md/` 子目录）
- [ ] 使用 `.md` 扩展名
- [ ] 内部交叉引用使用相对路径
- [ ] 中文注释完整（不依赖代码自解释）
- [ ] commit message 用 `docs:` 前缀

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