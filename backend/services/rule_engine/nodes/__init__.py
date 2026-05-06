# -*- coding: utf-8 -*-
"""节点模块 - 内置节点类型定义。

按 Phase 1 设计文档组织节点分类：
- triggers: 触发器节点（规则入口）
- conditions: 条件节点
- actions: 动作节点
- logic: 逻辑控制节点
"""
from .base import BaseExecutor, NodeCategory, NodeResult, NodeStatus, ExecutionContext

__all__ = [
    "BaseExecutor",
    "NodeCategory",
    "NodeResult",
    "NodeStatus",
    "ExecutionContext",
]
