# -*- coding: utf-8 -*-
"""动作类节点 - 外部操作执行节点。

按 Phase 1 设计文档实现 BaseExecutor 模式。

节点分类: action (#FF7F4C)
"""
import asyncio
from typing import Any, Dict, List, Literal, Optional, Tuple

from backend.services.rule_engine.models import (
    NodeConfigSchema, NodeDefinition, NodeCategory, PortDefinition,
    PortType, ConfigSchemaProperty,
)
from pydantic import Field
from typing import Dict
from .base import BaseExecutor


# P0-A (2026-09-11): 节点配置 schema（Pydantic 强类型校验）。
class KeyboardActionConfig(NodeConfigSchema):
    """KeyboardActionNode 配置 schema。"""
    keys: List[str] = Field(default_factory=list, description="要模拟按下的键列表")
    hold_duration: float = Field(default=0.1, ge=0.01, le=5.0, description="按住时长（秒）")
    interval: float = Field(default=0, ge=0, le=10.0, description="按键间隔（秒）")


class MouseActionConfig(NodeConfigSchema):
    """MouseActionNode 配置 schema。"""
    action: Literal["click", "move", "scroll", "double_click", "right_click"] = Field(
        default="click", description="鼠标动作类型"
    )
    x: float = Field(default=0, ge=0, le=9999, description="鼠标 X 坐标")
    y: float = Field(default=0, ge=0, le=9999, description="鼠标 Y 坐标")
    button: Literal["left", "right", "middle"] = Field(
        default="left", description="使用的鼠标按钮"
    )


class WaitActionConfig(NodeConfigSchema):
    """WaitActionNode 配置 schema。"""
    duration: float = Field(default=1.0, ge=0.1, le=300.0, description="等待时长（秒）")


class HttpRequestActionConfig(NodeConfigSchema):
    """HttpRequestActionNode 配置 schema。"""
    url: str = Field(default="", description="HTTP 请求的目标 URL")
    method: Literal["GET", "POST", "PUT", "DELETE", "PATCH"] = Field(
        default="GET", description="HTTP 请求方法"
    )
    headers: str = Field(default="{}", description="HTTP 请求头（JSON 格式）")
    body: str = Field(default="{}", description="HTTP 请求体（JSON 格式）")
    timeout: int = Field(default=30, ge=1, le=300, description="请求超时时间（秒）")


class LogActionConfig(NodeConfigSchema):
    """LogActionNode 配置 schema。"""
    message: str = Field(default="", description="要记录的日志消息, 支持 {变量名} 插值")
    level: Literal["debug", "info", "warning", "error"] = Field(
        default="info", description="日志输出级别"
    )


class KeyboardActionNode(BaseExecutor):
    """键盘动作 - 模拟键盘按键。

    配置项:
        keys: list[str] - 要按下的键列表
        hold_duration: float - 按住时长(秒)
        interval: float - 按键间隔(秒)
    """

    node_type = "keyboard_action"
    category = NodeCategory.ACTION
    display_name = "键盘动作"
    description = "模拟键盘按键"
    icon = "keyboard"
    color = "#FF7F4C"

    ConfigSchema = KeyboardActionConfig

    def get_definition(self) -> NodeDefinition:
        return NodeDefinition(
            type=self.node_type,
            category=self.category.value,
            display_name=self.display_name,
            description=self.description,
            icon=self.icon,
            color=self.color,
            inputs={
                "trigger": PortDefinition(
                    name="触发",
                    type=PortType.TRIGGER.value,
                    description="触发信号"
                ),
            },
            outputs={
                "success": PortDefinition(
                    name="成功",
                    type="BOOLEAN",
                    description="是否执行成功"
                ),
                "executed_keys": PortDefinition(
                    name="按键列表",
                    type="ARRAY",
                    description="已执行的按键列表"
                ),
            },
            config_schema=self.get_config_schema(),
        )

    def get_config_schema(self) -> Dict[str, ConfigSchemaProperty]:
        return {
            "keys": ConfigSchemaProperty(
                type="array",
                title="按键列表",
                description="要模拟按下的键列表",
                default=[],
                widget="multiselect",
                enum=["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m", "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z", "enter", "escape", "space", "tab", "shift", "ctrl", "alt"],
            ),
            "hold_duration": ConfigSchemaProperty(
                type="number",
                title="按住时长",
                description="每个按键按住的时长（秒）",
                default=0.1,
                minimum=0.01,
                maximum=5.0,
                step=0.05,
                widget="number",
            ),
            "interval": ConfigSchemaProperty(
                type="number",
                title="按键间隔",
                description="按键之间的间隔时间（秒）",
                default=0,
                minimum=0,
                maximum=10.0,
                step=0.1,
                widget="number",
            ),
        }

    def validate_inputs(self, inputs: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        return True, None

    async def execute(
        self,
        inputs: Dict[str, Any],
        context
    ) -> Dict[str, Any]:
        params = self.config.get("params", {})
        keys = params.get("keys", [])
        hold_duration = params.get("hold_duration", 0.1)
        interval = params.get("interval", 0)

        executed_keys = []

        for key in keys:
            # TODO: 对接键盘模拟
            # from engine.core.control.input_emulator import KeyboardEmulator
            # keyboard = KeyboardEmulator()
            # keyboard.press(key)
            # await asyncio.sleep(hold_duration)
            # keyboard.release(key)
            executed_keys.append(key)

            if interval > 0:
                await asyncio.sleep(interval)

        return {
            "executed_keys": executed_keys,
            "success": True,
        }


class MouseActionNode(BaseExecutor):
    """鼠标动作 - 模拟鼠标操作。

    配置项:
        action: str - 动作类型 (click/move/scroll)
        x: int - X坐标
        y: int - Y坐标
        button: str - 鼠标按钮 (left/right/middle)
    """

    node_type = "mouse_action"
    category = NodeCategory.ACTION
    display_name = "鼠标动作"
    description = "模拟鼠标操作"
    icon = "mouse"
    color = "#FF7F4C"

    ConfigSchema = MouseActionConfig

    def get_definition(self) -> NodeDefinition:
        return NodeDefinition(
            type=self.node_type,
            category=self.category.value,
            display_name=self.display_name,
            description=self.description,
            icon=self.icon,
            color=self.color,
            inputs={
                "trigger": PortDefinition(
                    name="触发",
                    type=PortType.TRIGGER.value,
                    description="触发信号"
                ),
            },
            outputs={
                "success": PortDefinition(
                    name="成功",
                    type="BOOLEAN",
                    description="是否执行成功"
                ),
            },
            config_schema=self.get_config_schema(),
        )

    def get_config_schema(self) -> Dict[str, ConfigSchemaProperty]:
        return {
            "action": ConfigSchemaProperty(
                type="string",
                title="动作类型",
                description="鼠标动作类型",
                default="click",
                widget="dropdown",
                enum=["click", "move", "scroll", "double_click", "right_click"],
            ),
            "x": ConfigSchemaProperty(
                type="number",
                title="X坐标",
                description="鼠标 X 坐标",
                default=0,
                minimum=0,
                maximum=9999,
                step=1,
                widget="number",
            ),
            "y": ConfigSchemaProperty(
                type="number",
                title="Y坐标",
                description="鼠标 Y 坐标",
                default=0,
                minimum=0,
                maximum=9999,
                step=1,
                widget="number",
            ),
            "button": ConfigSchemaProperty(
                type="string",
                title="鼠标按钮",
                description="使用的鼠标按钮",
                default="left",
                widget="dropdown",
                enum=["left", "right", "middle"],
            ),
        }

    def validate_inputs(self, inputs: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        return True, None

    async def execute(
        self,
        inputs: Dict[str, Any],
        context
    ) -> Dict[str, Any]:
        params = self.config.get("params", {})
        action = params.get("action", "click")
        x = params.get("x", 0)
        y = params.get("y", 0)
        button = params.get("button", "left")

        # TODO: 对接鼠标模拟
        # from engine.core.control.input_emulator import MouseEmulator
        # mouse = MouseEmulator()
        # if action == "click":
        #     mouse.click(x, y, button)
        # elif action == "move":
        #     mouse.move(x, y)

        return {
            "action": action,
            "position": {"x": x, "y": y},
            "button": button,
            "success": True,
        }


class WaitActionNode(BaseExecutor):
    """等待动作 - 等待指定时间。

    配置项:
        duration: float - 等待时长(秒)
    """

    node_type = "wait_action"
    category = NodeCategory.ACTION
    display_name = "等待"
    description = "等待指定时间"
    icon = "clock"
    color = "#FF7F4C"

    ConfigSchema = WaitActionConfig

    def get_definition(self) -> NodeDefinition:
        return NodeDefinition(
            type=self.node_type,
            category=self.category.value,
            display_name=self.display_name,
            description=self.description,
            icon=self.icon,
            color=self.color,
            inputs={
                "trigger": PortDefinition(
                    name="触发",
                    type=PortType.TRIGGER.value,
                    description="触发信号"
                ),
            },
            outputs={
                "completed": PortDefinition(
                    name="完成",
                    type="BOOLEAN",
                    description="等待完成"
                ),
            },
            config_schema=self.get_config_schema(),
        )

    def get_config_schema(self) -> Dict[str, ConfigSchemaProperty]:
        return {
            "duration": ConfigSchemaProperty(
                type="number",
                title="等待时长",
                description="等待多少秒后继续",
                default=1.0,
                minimum=0.1,
                maximum=300.0,
                step=0.5,
                widget="slider",
            ),
        }

    def validate_inputs(self, inputs: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        return True, None

    async def execute(
        self,
        inputs: Dict[str, Any],
        context
    ) -> Dict[str, Any]:
        params = self.config.get("params", {})
        duration = params.get("duration", 1.0)

        await asyncio.sleep(duration)

        return {
            "waited_seconds": duration,
            "completed": True,
        }


class HttpRequestActionNode(BaseExecutor):
    """HTTP 请求动作 - 发送 HTTP 请求。

    配置项:
        url: str - 请求URL
        method: str - 请求方法 (GET/POST/PUT/DELETE)
        headers: dict - 请求头
        body: dict - 请求体
    """

    node_type = "http_request_action"
    category = NodeCategory.ACTION
    display_name = "HTTP 请求"
    description = "发送 HTTP 请求"
    icon = "http"
    color = "#FF7F4C"

    ConfigSchema = HttpRequestActionConfig

    def get_definition(self) -> NodeDefinition:
        return NodeDefinition(
            type=self.node_type,
            category=self.category.value,
            display_name=self.display_name,
            description=self.description,
            icon=self.icon,
            color=self.color,
            inputs={
                "trigger": PortDefinition(
                    name="触发",
                    type=PortType.TRIGGER.value,
                    description="触发信号"
                ),
            },
            outputs={
                "success": PortDefinition(
                    name="成功",
                    type="BOOLEAN",
                    description="请求是否成功"
                ),
                "status_code": PortDefinition(
                    name="状态码",
                    type="INT",
                    description="HTTP 状态码"
                ),
                "response": PortDefinition(
                    name="响应",
                    type="ANY",
                    description="响应内容"
                ),
            },
            config_schema=self.get_config_schema(),
        )

    def get_config_schema(self) -> Dict[str, ConfigSchemaProperty]:
        return {
            "url": ConfigSchemaProperty(
                type="string",
                title="请求URL",
                description="HTTP 请求的目标 URL",
                default="",
                widget="text",
            ),
            "method": ConfigSchemaProperty(
                type="string",
                title="请求方法",
                description="HTTP 请求方法",
                default="GET",
                widget="dropdown",
                enum=["GET", "POST", "PUT", "DELETE", "PATCH"],
            ),
            "headers": ConfigSchemaProperty(
                type="string",
                title="请求头",
                description="HTTP 请求头（JSON 格式）",
                default="{}",
                widget="text",
            ),
            "body": ConfigSchemaProperty(
                type="string",
                title="请求体",
                description="HTTP 请求体（JSON 格式）",
                default="{}",
                widget="textarea",
            ),
            "timeout": ConfigSchemaProperty(
                type="number",
                title="超时时间",
                description="请求超时时间（秒）",
                default=30,
                minimum=1,
                maximum=300,
                step=1,
                widget="number",
            ),
        }

    def validate_inputs(self, inputs: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        return True, None

    async def execute(
        self,
        inputs: Dict[str, Any],
        context
    ) -> Dict[str, Any]:
        import httpx

        params = self.config.get("params", {})
        url = params.get("url", "")
        method = params.get("method", "GET")
        headers = params.get("headers", {})
        body = params.get("body", {})
        timeout = params.get("timeout", 30)

        if not url:
            return {"success": False, "error": "URL 不能为空"}

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=body if body else None
                )

                return {
                    "status_code": response.status_code,
                    "response": response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text,
                    "success": response.status_code < 400,
                }
        except Exception as e:
            return {"success": False, "error": str(e)}


class LogActionNode(BaseExecutor):
    """日志动作 - 记录日志信息。

    配置项:
        message: str - 日志消息
        level: str - 日志级别 (info/warning/error)
    """

    node_type = "log_action"
    category = NodeCategory.ACTION
    display_name = "日志"
    description = "记录日志信息"
    icon = "note-text"
    color = "#FF7F4C"

    ConfigSchema = LogActionConfig

    def get_definition(self) -> NodeDefinition:
        return NodeDefinition(
            type=self.node_type,
            category=self.category.value,
            display_name=self.display_name,
            description=self.description,
            icon=self.icon,
            color=self.color,
            inputs={
                "trigger": PortDefinition(
                    name="触发",
                    type=PortType.TRIGGER.value,
                    description="触发信号"
                ),
            },
            outputs={
                "logged": PortDefinition(
                    name="已记录",
                    type="BOOLEAN",
                    description="是否记录成功"
                ),
            },
            config_schema=self.get_config_schema(),
        )

    def get_config_schema(self) -> Dict[str, ConfigSchemaProperty]:
        return {
            "message": ConfigSchemaProperty(
                type="string",
                title="日志消息",
                description="要记录的日志消息，支持 {变量名} 插值",
                default="",
                widget="textarea",
            ),
            "level": ConfigSchemaProperty(
                type="string",
                title="日志级别",
                description="日志输出级别",
                default="info",
                widget="dropdown",
                enum=["debug", "info", "warning", "error"],
            ),
        }

    def validate_inputs(self, inputs: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        return True, None

    async def execute(
        self,
        inputs: Dict[str, Any],
        context
    ) -> Dict[str, Any]:
        import logging

        params = self.config.get("params", {})
        message = params.get("message", "")
        level = params.get("level", "info")

        # 模板变量替换
        try:
            rendered_message = message.format(**context.variables)
        except (KeyError, ValueError):
            rendered_message = message

        logger = logging.getLogger("rule_engine")
        log_func = getattr(logger, level, logger.info)
        log_func(rendered_message)

        return {
            "logged": True,
            "message": rendered_message,
            "level": level,
        }
