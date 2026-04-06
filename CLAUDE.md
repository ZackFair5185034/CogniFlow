# VisionGame 项目规范

## 1. 项目概述

VisionGame 是一个基于强化学习的通用视觉控制游戏框架，支持屏幕/视频采集、视觉特征提取、RL训练和游戏控制输入模拟。

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
visiongame/
├── visiongame/                    # 主包
│   ├── __init__.py               # 包初始化
│   ├── config/                    # 配置模块
│   │   ├── schema.py             # 配置数据类
│   │   ├── default.yaml          # 默认配置
│   │   └── __init__.py
│   ├── core/                     # 核心模块
│   │   ├── data_input/           # 数据输入
│   │   │   ├── capture/          # 屏幕捕获
│   │   │   └── storage/          # 数据存储
│   │   ├── vision/               # 视觉处理
│   │   │   ├── features/         # 特征提取
│   │   │   ├── detector/         # 目标检测
│   │   │   └── preprocessor/     # 图像预处理
│   │   ├── rl/                   # 强化学习
│   │   │   ├── algorithms/       # RL算法
│   │   │   ├── environment/      # 环境封装
│   │   │   └── trainer/          # 训练器
│   │   └── control/              # 控制接口
│   │       ├── input_emulator/   # 输入模拟
│   │       └── controller/       # 控制器
│   └── annotation/               # 标注工具
├── examples/                     # 示例代码
├── tests/                        # 单元测试
└── docs/                         # 文档
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

### 4.3 Gitignore 规则

- Python 缓存：`__pycache__/`、`.pyc`
- 虚拟环境：`venv/`、`env/`
- IDE 配置：`.idea/`、`.vscode/`
- 日志文件：`*.log`
- 训练输出：`logs/`、`checkpoints/`、`data/`
- 模型文件：`*.pt`、`.pth`
- 敏感信息：`.env`、`*.key`

## 5. 测试规范

- 所有新功能必须包含单元测试
- 使用 `pytest` 框架
- 测试文件放在 `tests/` 目录
- 覆盖率目标：核心模块 > 80%

## 6. 依赖管理

- 使用 `requirements.txt` 管理依赖
- 开发依赖放在 `extras_require["dev"]`
- 定期更新依赖版本

## 7. 许可证

MIT License
