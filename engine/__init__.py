"""CogniFlow - 通用视觉感知处理框架.

CogniFlow 集模型训练、模型测试、模型推理、规则引擎于一体，
支持图像/视频采集、视觉特征提取、目标检测、模型训练部署和可视化规则编排。

模块说明：
- data_input: 图像/视频/屏幕数据采集
- vision: 视觉特征提取与目标检测
- rl: 强化学习训练 (PPO/SAC)
- control: 控制输入模拟
- annotation: 数据标注工具

安装：
    pip install -e .

使用示例：
    from engine import ScreenCapture, VideoReader, CNNEncoder, UIDetector

    # 屏幕采集
    with ScreenCapture(fps=30) as capture:
        frame = capture.capture()

    # 视频读取
    with VideoReader("video.mp4") as reader:
        for frame in reader:
            print(frame.shape)

    # 目标检测
    from engine import UIDetector
    detector = UIDetector()
    results = detector.detect(frame)
"""

__version__ = "0.1.0"
__author__ = "CogniFlow Team"

# 数据输入模块
from engine.core.data_input import (
    ScreenCapture,
    VideoReader,
    FrameBuffer,
    DatasetManager,
)

# 视觉处理模块
from engine.core.vision import (
    ImagePreprocessor,
    CNNEncoder,
    UIDetector,
)

# 强化学习模块
from engine.core.rl import (
    PPO,
    SAC,
    GameEnv,
    GameAdapter,
    Trainer,
)

# 控制模块
from engine.core.control import (
    KeyboardEmulator,
    MouseEmulator,
    GameController,
)

# 标注工具
from engine.annotation import (
    BoundingBox,
    BoundingBoxAnnotator,
    LabelTool,
)

# 配置
from engine.config import (
    Config,
    DataInputConfig,
    VisionConfig,
    RLConfig,
    ControlConfig,
    AnnotationConfig,
    StorageConfig,
    TrainingConfig,
    get_config,
    set_config,
)

__all__ = [
    # 版本信息
    "__version__",
    "__author__",
    # 数据输入
    "ScreenCapture",
    "VideoReader",
    "FrameBuffer",
    "DatasetManager",
    # 视觉处理
    "ImagePreprocessor",
    "CNNEncoder",
    "UIDetector",
    # 强化学习
    "PPO",
    "SAC",
    "GameEnv",
    "GameAdapter",
    "Trainer",
    # 控制
    "KeyboardEmulator",
    "MouseEmulator",
    "GameController",
    # 标注
    "BoundingBox",
    "BoundingBoxAnnotator",
    "LabelTool",
    # 配置
    "Config",
    "DataInputConfig",
    "VisionConfig",
    "RLConfig",
    "ControlConfig",
    "AnnotationConfig",
    "StorageConfig",
    "TrainingConfig",
    "get_config",
    "set_config",
]
