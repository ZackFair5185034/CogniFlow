"""VisionGame 配置模块 - 定义所有配置数据类。"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from pathlib import Path


@dataclass
class DataInputConfig:
    """数据输入配置。"""
    capture_fps: int = 30
    buffer_size: int = 100
    screenshot_format: str = "png"
    capture_region: Optional[List[int]] = None  # [x, y, width, height]
    video_decoder: str = "ffmpeg"  # ffmpeg 或 opencv


@dataclass
class VisionConfig:
    """视觉处理配置。"""
    image_size: tuple = (224, 224)
    normalization_mean: List[float] = field(default_factory=lambda: [0.485, 0.456, 0.406])
    normalization_std: List[float] = field(default_factory=lambda: [0.229, 0.224, 0.225])
    backbone: str = "resnet18"
    feature_dim: int = 512
    use_pretrained: bool = True


@dataclass
class RLConfig:
    """强化学习训练配置。"""
    algorithm: str = "ppo"
    gamma: float = 0.99
    lam: float = 0.95  # GAE lambda 参数
    learning_rate: float = 3e-4
    clip_eps: float = 0.2  # PPO 裁剪 epsilon
    ent_coef: float = 0.01  # 熵系数
    vf_coef: float = 0.5  # 价值函数系数
    max_grad_norm: float = 0.5
    ppo_epochs: int = 10
    batch_size: int = 64
    buffer_size: int = 2048
    sac_alpha: float = 0.2  # SAC 熵温度参数


@dataclass
class ControlConfig:
    """游戏控制配置。"""
    action_delay: float = 0.1  # 操作间隔时间（秒）
    key_press_duration: float = 0.05
    mouse_move_duration: float = 0.1
    safety_check: bool = True
    emergency_stop_key: str = "f12"


@dataclass
class AnnotationConfig:
    """标注工具配置。"""
    label_format: str = "coco"  # coco 或 yolo
    export_dir: Path = Path("./datasets")
    auto_save: bool = True
    auto_save_interval: int = 60  # 秒


@dataclass
class StorageConfig:
    """数据存储配置。"""
    root_dir: Path = Path("./data")
    db_type: str = "sqlite"  # sqlite 或 postgres
    db_path: Path = Path("./data/visiongame.db")
    max_storage_gb: int = 100


@dataclass
class TrainingConfig:
    """训练配置。"""
    total_timesteps: int = 1_000_000
    eval_freq: int = 10000
    save_freq: int = 50000
    log_freq: int = 1000
    num_eval_episodes: int = 10
    checkpoint_dir: Path = Path("./checkpoints")
    log_dir: Path = Path("./logs")
    device: str = "cuda"
    distributed: bool = False
    world_size: int = 1


@dataclass
class Config:
    """VisionGame 主配置类。"""
    data_input: DataInputConfig = field(default_factory=DataInputConfig)
    vision: VisionConfig = field(default_factory=VisionConfig)
    rl: RLConfig = field(default_factory=RLConfig)
    control: ControlConfig = field(default_factory=ControlConfig)
    annotation: AnnotationConfig = field(default_factory=AnnotationConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    training: TrainingConfig = field(default_factory=TrainingConfig)

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "Config":
        """从字典创建配置。"""
        def _dict_to_config(d, cfg_class):
            if d is None:
                return cfg_class()
            field_values = {}
            for field_name in cfg_class.__dataclass_fields__:
                if field_name in d:
                    field_value = d[field_name]
                    field_type = cfg_class.__dataclass_fields__[field_name].type
                    if hasattr(field_type, "__dataclass_fields__"):
                        field_values[field_name] = _dict_to_config(field_value, field_type)
                    else:
                        field_values[field_name] = field_value
            return cfg_class(**field_values)

        return _dict_to_config(config_dict, cls)

    @classmethod
    def from_yaml(cls, path: Path) -> "Config":
        """从 YAML 文件加载配置。"""
        import yaml
        with open(path, "r") as f:
            config_dict = yaml.safe_load(f)
        return cls.from_dict(config_dict)

    def to_dict(self) -> Dict[str, Any]:
        """将配置转换为字典。"""
        result = {}
        for field_name in self.__dataclass_fields__:
            value = getattr(self, field_name)
            if hasattr(value, "__dataclass_fields__"):
                result[field_name] = value.to_dict()
            else:
                result[field_name] = value
        return result

    def save_yaml(self, path: Path):
        """保存配置到 YAML 文件。"""
        import yaml
        with open(path, "w") as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False)


# 全局配置实例
_config: Optional[Config] = None


def get_config() -> Config:
    """获取全局配置实例。"""
    global _config
    if _config is None:
        _config = Config()
    return _config


def set_config(config: Config):
    """设置全局配置实例。"""
    global _config
    _config = config
