# -*- coding: utf-8 -*-
"""规则引擎异常定义。"""
from typing import List, Optional


class RuleEngineError(Exception):
    """规则引擎基础异常。"""
    pass


class CycleError(RuleEngineError):
    """循环依赖错误 - 规则图存在环回。"""

    def __init__(self, message: str, cycle_nodes: List[str] = None):
        super().__init__(message)
        self.cycle_nodes = cycle_nodes or []


class ValidationError(RuleEngineError):
    """规则图校验错误。"""
    pass


class ExecutorError(RuleEngineError):
    """节点执行错误。"""

    def __init__(
        self,
        message: str,
        node_id: str = None,
        node_type: str = None,
        cause: Exception = None
    ):
        super().__init__(message)
        self.node_id = node_id
        self.node_type = node_type
        self.cause = cause
