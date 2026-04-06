"""Configuration module for VisionGame."""

from visiongame.config.schema import (
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
