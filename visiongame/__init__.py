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
