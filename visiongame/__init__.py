"""VisionGame - 通用视觉控制游戏框架.

支持功能：
- 屏幕/视频采集
- 视觉特征提取
- 强化学习训练 (PPO/SAC)
- 游戏控制输入模拟
- 数据标注工具

安装：
    pip install -e .

使用示例：
    from visiongame import ScreenCapture, VideoReader, CNNEncoder, GameEnv, GameController

    # 屏幕采集
    with ScreenCapture(fps=30) as capture:
        frame = capture.capture()

    # 视频读取
    with VideoReader("video.mp4") as reader:
        for frame in reader:
            print(frame.shape)

    # RL训练
    from visiongame.examples import train_example
    train_example.main()
"""

__version__ = "0.1.0"
__author__ = "VisionGame Team"

# 数据输入模块
from visiongame.core.data_input import (
    ScreenCapture,
    VideoReader,
    FrameBuffer,
    DatasetManager,
)

# 视觉处理模块
from visiongame.core.vision import (
    ImagePreprocessor,
    CNNEncoder,
    UIDetector,
)

# 强化学习模块
from visiongame.core.rl import (
    PPO,
    SAC,
    GameEnv,
    GameAdapter,
    Trainer,
)

# 控制模块
from visiongame.core.control import (
    KeyboardEmulator,
    MouseEmulator,
    GameController,
)

# 标注工具
from visiongame.annotation import (
    BoundingBox,
    BoundingBoxAnnotator,
    LabelTool,
)

# 配置
from visiongame.config import (
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
