# -*- coding: utf-8 -*-
"""安全路径工具 - 统一的路径穿越防护。

2026-10-24 安全审计发现 5 处写入点直接拼接用户路径片段
(atlas.py / model.py / inference.py), 存在路径穿越风险。
本模块提供唯一的 `safe_join` 实现, 供所有写入点调用。
"""
import os


def safe_join(base_dir: str, *parts: str) -> str:
    """在 base_dir 之内安全地拼接路径。

    Args:
        base_dir: 基准目录(必须是绝对路径)
        *parts: 路径片段, 允许相对路径

    Returns:
        规范化后的绝对路径

    Raises:
        ValueError: 拼接结果越出 base_dir 时抛出
    """
    if not base_dir:
        raise ValueError("基准目录不能为空")

    base = os.path.abspath(base_dir)
    # 过滤掉空片段与 None
    cleaned = [str(p) for p in parts if p not in (None, "")]
    target = os.path.abspath(os.path.join(base, *cleaned))

    # 目标必须在 base 之内(含 base 本身)
    if target != base and not target.startswith(base + os.sep):
        raise ValueError(f"路径越界: {target} 不在 {base} 之内")

    return target
