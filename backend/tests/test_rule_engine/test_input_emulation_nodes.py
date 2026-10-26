# -*- coding: utf-8 -*-
"""输入模拟节点测试 - 键盘/鼠标动作必须真实调用底层实现。"""
from unittest.mock import MagicMock, patch

import pytest

from backend.services.rule_engine.nodes.actions import (
    KeyboardActionNode,
    MouseActionNode,
)


class TestKeyboardActionNode:
    """键盘动作节点。"""

    @pytest.mark.asyncio
    async def test_presses_each_key(self):
        """每个按键都要真实调用 key_down / key_up。"""
        keyboard = MagicMock()
        node = KeyboardActionNode(node_id="n1", config={"params": {"keys": ["a", "b"]}})

        with patch(
            "engine.core.control.input_emulator.KeyboardEmulator",
            return_value=keyboard,
        ):
            result = await node.execute({}, MagicMock())

        assert keyboard.key_down.call_count == 2
        assert keyboard.key_up.call_count == 2
        assert result["executed_keys"] == ["a", "b"]
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_raises_when_backend_unavailable(self):
        """底层实现不可用时必须显式报错, 不能谎报成功。"""
        node = KeyboardActionNode(node_id="n1", config={"params": {"keys": ["a"]}})

        with patch(
            "engine.core.control.input_emulator.KeyboardEmulator",
            side_effect=RuntimeError("pyautogui 不可用"),
        ):
            with pytest.raises(Exception) as excinfo:
                await node.execute({}, MagicMock())

        assert "pyautogui 不可用" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_empty_keys_is_noop(self):
        """没有配置按键时不调用底层实现, 返回空列表。"""
        keyboard = MagicMock()
        node = KeyboardActionNode(node_id="n1", config={"params": {"keys": []}})

        with patch(
            "engine.core.control.input_emulator.KeyboardEmulator",
            return_value=keyboard,
        ):
            result = await node.execute({}, MagicMock())

        assert result["executed_keys"] == []
        assert keyboard.key_down.call_count == 0


class TestMouseActionNode:
    """鼠标动作节点。"""

    @pytest.mark.asyncio
    async def test_click_calls_mouse(self):
        """点击动作真实调用 mouse.click。"""
        mouse = MagicMock()
        node = MouseActionNode(
            node_id="n1",
            config={"params": {"action": "click", "x": 100, "y": 200, "button": "right"}},
        )

        with patch(
            "engine.core.control.input_emulator.MouseEmulator",
            return_value=mouse,
        ):
            result = await node.execute({}, MagicMock())

        mouse.click.assert_called_once()
        assert result["position"] == {"x": 100, "y": 200}
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_unsupported_action_raises(self):
        """不支持的动作类型必须显式抛错, 不能返回 success。"""
        node = MouseActionNode(
            node_id="n1",
            config={"params": {"action": "double_click"}},
        )

        with patch(
            "engine.core.control.input_emulator.MouseEmulator",
            return_value=MagicMock(),
        ):
            with pytest.raises(Exception) as excinfo:
                await node.execute({}, MagicMock())

        assert "double_click" in str(excinfo.value)
