# -*- coding: utf-8 -*-
"""端口类型定义与兼容矩阵 - 规则引擎前后端唯一的端口类型事实源。

2026-10-24 实测: 前端 `RuleCanvas.vue` 的 `isPortCompatible` 只实现了 4 条规则
(ANY / 同型 / TRIGGER->TRIGGER|CONTROL / CONTROL->CONTROL), 而后端执行器有 14 类矩阵。
两者差集导致 `BOOLEAN -> TRIGGER` 的边被 VueFlow 在 `isValidConnection` 阶段静默丢弃,
所有动作节点(输入端口均为 TRIGGER)事实上不可达。本模块把矩阵收敛到唯一实现,
通过 `GET /api/rule-engine/port-compatibility` 下发给前端, 消除双份定义漂移。
"""
from typing import Dict, List, Set

# 全部端口类型 - 与 `backend/services/rule_engine/nodes/base.py` 的 PortType 枚举一致
PORT_TYPES: List[str] = [
    "ANY",
    "IMAGE",
    "BBOX",
    "MASK",
    "SCORES",
    "TRIGGER",
    "CONTROL",
    "MODEL",
    "INT",
    "FLOAT",
    "BOOLEAN",
    "STRING",
    "ARRAY",
    "OBJECT",
]

# 端口兼容矩阵: 源类型 -> 兼容的目标类型列表
# ANY 可连接到所有类型; 其余类型只允许同型(ANY 恒可)。
#
# 2026-10-24 补充 CONTROL -> TRIGGER:
#   branch / parallel_branch / delay 的输出是 CONTROL 控制流信号, 语义上就是
#   「可以触发后续动作」。若 CONTROL 不能接 TRIGGER, 「分支 -> 动作」这条最常见
#   的链路在画布上连不出来, 动作层在分支场景下依然不可达。
PORT_COMPATIBILITY: Dict[str, List[str]] = {
    "ANY": list(PORT_TYPES),
    "IMAGE": ["ANY", "IMAGE"],
    "BBOX": ["ANY", "BBOX"],
    "MASK": ["ANY", "MASK"],
    "SCORES": ["ANY", "SCORES"],
    "TRIGGER": ["ANY", "TRIGGER", "CONTROL", "BOOLEAN"],
    "CONTROL": ["ANY", "CONTROL", "BOOLEAN", "TRIGGER"],
    "MODEL": ["ANY", "MODEL"],
    "INT": ["ANY", "INT"],
    "FLOAT": ["ANY", "FLOAT"],
    "BOOLEAN": ["ANY", "BOOLEAN", "TRIGGER", "CONTROL"],
    "STRING": ["ANY", "STRING"],
    "ARRAY": ["ANY", "ARRAY"],
    "OBJECT": ["ANY", "OBJECT"],
}

# 预编译查表, 避免每次判定都做列表扫描
_COMPAT_SETS: Dict[str, Set[str]] = {
    key: set(value) for key, value in PORT_COMPATIBILITY.items()
}


def is_port_compatible(source_type: str, target_type: str) -> bool:
    """判断源端口类型能否连接到目标端口类型。

    Args:
        source_type: 源端口类型, 如 "BOOLEAN"
        target_type: 目标端口类型, 如 "TRIGGER"

    Returns:
        兼容返回 True; 类型缺失、未知或不兼容返回 False(不静默放行)。
    """
    if not source_type or not target_type:
        return False
    if source_type == "ANY" or target_type == "ANY":
        return True
    return target_type in _COMPAT_SETS.get(source_type, set())


def get_compatibility_matrix() -> Dict[str, List[str]]:
    """返回端口兼容矩阵的深拷贝, 供 HTTP 接口下发。

    Returns:
        {源类型: [兼容的目标类型]} 的新字典, 修改返回值不影响模块常量。
    """
    return {key: list(value) for key, value in PORT_COMPATIBILITY.items()}
