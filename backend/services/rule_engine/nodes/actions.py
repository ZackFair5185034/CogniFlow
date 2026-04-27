# -*- coding: utf-8 -*-
"""动作节点 - 执行各种操作动作。"""
import asyncio
from typing import Optional
from .base import (
    BaseNode, NodeCategory, NodeResult, NodeStatus, ExecutionContext
)


class KeyboardActionNode(BaseNode):
    """键盘动作 - 模拟键盘按键。

    配置项:
        keys: list[str] - 要按下的键列表
        hold_duration: float - 按住时长(秒)
        interval: float - 按键间隔(秒)
    """
    node_type = "keyboard_action"
    category = NodeCategory.ACTION
    label = "键盘动作"
    description = "模拟键盘按键"
    icon = "mdi:keyboard"

    inputs = [
        {"name": "trigger", "type": "flow", "label": "触发"},
    ]
    outputs = [
        {"name": "next", "type": "flow", "label": "完成"},
    ]

    config_schema = {
        "type": "object",
        "properties": {
            "keys": {
                "type": "array",
                "items": {"type": "string"},
                "default": []
            },
            "hold_duration": {
                "type": "number",
                "minimum": 0,
                "default": 0.1
            },
            "interval": {
                "type": "number",
                "minimum": 0,
                "default": 0
            },
        }
    }

    async def _execute(self, context: ExecutionContext, input_data: dict) -> NodeResult:
        """执行键盘动作。"""
        keys = self.config.get("keys", [])
        hold_duration = self.config.get("hold_duration", 0.1)
        interval = self.config.get("interval", 0)

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

            context.logs.append(f"按键: {key}")

        return NodeResult(
            status=NodeStatus.COMPLETED,
            output_data={
                "executed_keys": executed_keys,
                "success": True,
            }
        )


class MouseActionNode(BaseNode):
    """鼠标动作 - 模拟鼠标操作。

    配置项:
        action: str - 动作类型 (click/move/scroll)
        x: int - X坐标
        y: int - Y坐标
        button: str - 鼠标按钮 (left/right/middle)
    """
    node_type = "mouse_action"
    category = NodeCategory.ACTION
    label = "鼠标动作"
    description = "模拟鼠标操作"
    icon = "mdi:mouse"

    inputs = [
        {"name": "trigger", "type": "flow", "label": "触发"},
    ]
    outputs = [
        {"name": "next", "type": "flow", "label": "完成"},
    ]

    config_schema = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["click", "move", "scroll", "double_click", "right_click"],
                "default": "click"
            },
            "x": {
                "type": "integer",
                "default": 0
            },
            "y": {
                "type": "integer",
                "default": 0
            },
            "button": {
                "type": "string",
                "enum": ["left", "right", "middle"],
                "default": "left"
            },
            "scroll_amount": {
                "type": "integer",
                "default": 0
            },
        }
    }

    async def _execute(self, context: ExecutionContext, input_data: dict) -> NodeResult:
        """执行鼠标动作。"""
        action = self.config.get("action", "click")
        x = self.config.get("x", 0)
        y = self.config.get("y", 0)
        button = self.config.get("button", "left")

        # TODO: 对接鼠标模拟
        # from engine.core.control.input_emulator import MouseEmulator
        # mouse = MouseEmulator()
        # if action == "click":
        #     mouse.click(x, y, button)
        # elif action == "move":
        #     mouse.move(x, y)

        return NodeResult(
            status=NodeStatus.COMPLETED,
            output_data={
                "action": action,
                "position": {"x": x, "y": y},
                "success": True,
            }
        )


class WaitActionNode(BaseNode):
    """等待动作 - 等待指定时间。

    配置项:
        duration: float - 等待时长(秒)
    """
    node_type = "wait_action"
    category = NodeCategory.ACTION
    label = "等待"
    description = "等待指定时间"
    icon = "mdi:clock-outline"

    inputs = [
        {"name": "trigger", "type": "flow", "label": "触发"},
    ]
    outputs = [
        {"name": "next", "type": "flow", "label": "完成"},
    ]

    config_schema = {
        "type": "object",
        "properties": {
            "duration": {
                "type": "number",
                "minimum": 0,
                "default": 1.0
            },
        }
    }

    async def _execute(self, context: ExecutionContext, input_data: dict) -> NodeResult:
        """执行等待。"""
        duration = self.config.get("duration", 1.0)
        await asyncio.sleep(duration)

        return NodeResult(
            status=NodeStatus.COMPLETED,
            output_data={
                "waited_seconds": duration,
            }
        )


class HttpRequestActionNode(BaseNode):
    """HTTP 请求动作 - 发送 HTTP 请求。

    配置项:
        url: str - 请求URL
        method: str - 请求方法 (GET/POST/PUT/DELETE)
        headers: dict - 请求头
        body: dict - 请求体
    """
    node_type = "http_request_action"
    category = NodeCategory.ACTION
    label = "HTTP 请求"
    description = "发送 HTTP 请求"
    icon = "mdi:http"

    inputs = [
        {"name": "trigger", "type": "flow", "label": "触发"},
    ]
    outputs = [
        {"name": "next", "type": "flow", "label": "完成"},
        {"name": "response", "type": "object", "label": "响应"},
    ]

    config_schema = {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "format": "uri",
                "default": ""
            },
            "method": {
                "type": "string",
                "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"],
                "default": "GET"
            },
            "headers": {
                "type": "object",
                "default": {}
            },
            "body": {
                "type": "object",
                "default": {}
            },
            "timeout": {
                "type": "number",
                "minimum": 1,
                "default": 30
            },
        }
    }

    async def _execute(self, context: ExecutionContext, input_data: dict) -> NodeResult:
        """执行 HTTP 请求。"""
        import httpx

        url = self.config.get("url", "")
        method = self.config.get("method", "GET")
        headers = self.config.get("headers", {})
        body = self.config.get("body", {})
        timeout = self.config.get("timeout", 30)

        if not url:
            return NodeResult(
                status=NodeStatus.FAILED,
                error_message="URL is required"
            )

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=body if body else None
                )

                return NodeResult(
                    status=NodeStatus.COMPLETED,
                    output_data={
                        "status_code": response.status_code,
                        "response": response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text,
                        "success": True,
                    }
                )
        except Exception as e:
            return NodeResult(
                status=NodeStatus.FAILED,
                error_message=str(e)
            )


class LogActionNode(BaseNode):
    """日志动作 - 记录日志信息。

    配置项:
        message: str - 日志消息
        level: str - 日志级别 (info/warning/error)
    """
    node_type = "log_action"
    category = NodeCategory.ACTION
    label = "日志"
    description = "记录日志信息"
    icon = "mdi:note-text"

    inputs = [
        {"name": "trigger", "type": "flow", "label": "触发"},
    ]
    outputs = [
        {"name": "next", "type": "flow", "label": "完成"},
    ]

    config_schema = {
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "default": ""
            },
            "level": {
                "type": "string",
                "enum": ["info", "warning", "error"],
                "default": "info"
            },
        }
    }

    async def _execute(self, context: ExecutionContext, input_data: dict) -> NodeResult:
        """执行日志记录。"""
        import logging

        message = self.config.get("message", "")
        level = self.config.get("level", "info")

        # 模板变量替换
        try:
            rendered_message = message.format(**context.variables)
        except (KeyError, ValueError):
            rendered_message = message

        log_entry = {
            "level": level,
            "message": rendered_message,
            "timestamp": context.trigger_data.get("timestamp", None),
        }
        context.logs.append(log_entry)

        logger = logging.getLogger("rule_engine")
        log_func = getattr(logger, level, logger.info)
        log_func(rendered_message)

        return NodeResult(
            status=NodeStatus.COMPLETED,
            output_data={
                "logged": True,
                "message": rendered_message,
            }
        )
