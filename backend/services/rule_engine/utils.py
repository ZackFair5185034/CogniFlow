# -*- coding: utf-8 -*-
"""规则引擎工具函数。
"""
import os
import uuid
from pathlib import Path


def get_temp_image_path(node_id: str, source_path: str) -> str:
    """生成预处理图片的临时保存路径。

    Args:
        node_id: 节点实例 ID
        source_path: 源图片路径

    Returns:
        临时图片保存路径
    """
    data_dir = os.environ.get("COGNIFLOW_DATA_DIR", "data")
    suffix = Path(source_path).suffix or ".jpg"

    output_dir = os.path.join(data_dir, "inference_output", "preprocessed")
    os.makedirs(output_dir, exist_ok=True)

    filename = f"pre_{node_id}_{uuid.uuid4().hex[:8]}{suffix}"
    return os.path.join(output_dir, filename)
