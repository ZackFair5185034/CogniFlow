# -*- coding: utf-8 -*-
"""WebSocket 管理器 - 处理实时通信。

支持训练状态、模型执行状态和系统状态的实时推送。
"""
import asyncio
import logging
import subprocess
import sys
import psutil
from typing import Dict, Set
from fastapi import WebSocket

logger = logging.getLogger("cogniflow")


class WebSocketManager:
    """WebSocket 连接管理器。"""

    def __init__(self):
        # 训练状态连接: job_id -> set of websockets
        self._training_connections: Dict[int, Set[WebSocket]] = {}
        # 模型执行状态连接
        self._launch_connections: Set[WebSocket] = set()
        # 系统状态连接
        self._system_connections: Set[WebSocket] = set()
        # 系统状态推送任务
        self._system_push_task: asyncio.Task | None = None
        # 导出状态连接: export_id -> set of websockets
        self._export_connections: Dict[str, Set[WebSocket]] = {}

    async def connect_training(self, websocket: WebSocket, job_id: int):
        """连接训练状态 WebSocket。"""
        await websocket.accept()
        if job_id not in self._training_connections:
            self._training_connections[job_id] = set()
        self._training_connections[job_id].add(websocket)

    def disconnect_training(self, websocket: WebSocket, job_id: int):
        """断开训练状态 WebSocket。"""
        if job_id in self._training_connections:
            self._training_connections[job_id].discard(websocket)

    async def send_training_update(self, job_id: int, data: dict):
        """向所有连接的客户端发送训练更新。"""
        # 发送给特定 job_id 的连接
        if job_id in self._training_connections:
            disconnected = set()
            for websocket in self._training_connections[job_id]:
                try:
                    await websocket.send_json({
                        "type": "training_update",
                        "data": data
                    })
                except Exception:
                    disconnected.add(websocket)
            # 清理断开的连接
            for ws in disconnected:
                self._training_connections[job_id].discard(ws)

        # 同时发送给全局频道（job_id=0）的连接
        if 0 in self._training_connections:
            disconnected = set()
            for websocket in self._training_connections[0]:
                try:
                    await websocket.send_json({
                        "type": "training_update",
                        "data": data
                    })
                except Exception:
                    disconnected.add(websocket)
            for ws in disconnected:
                self._training_connections[0].discard(ws)

    async def connect_launch(self, websocket: WebSocket):
        """连接模型执行状态 WebSocket。"""
        await websocket.accept()
        self._launch_connections.add(websocket)

    def disconnect_launch(self, websocket: WebSocket):
        """断开模型执行状态 WebSocket。"""
        self._launch_connections.discard(websocket)

    async def send_launch_update(self, data: dict):
        """向所有连接的客户端发送执行状态更新。"""
        disconnected = set()
        for websocket in self._launch_connections:
            try:
                await websocket.send_json({
                    "type": "launch_update",
                    "data": data
                })
            except Exception:
                disconnected.add(websocket)
        for ws in disconnected:
            self._launch_connections.discard(ws)

    # ===== 导出进度 WebSocket =====
    async def connect_export(self, websocket: WebSocket, export_id: str):
        """连接导出进度 WebSocket。"""
        await websocket.accept()
        if export_id not in self._export_connections:
            self._export_connections[export_id] = set()
        self._export_connections[export_id].add(websocket)

    def disconnect_export(self, websocket: WebSocket, export_id: str):
        """断开导出进度 WebSocket。"""
        if export_id in self._export_connections:
            self._export_connections[export_id].discard(websocket)

    async def send_export_update(self, export_id: str, data: dict):
        """向导出任务连接的客户端发送进度更新。"""
        if export_id not in self._export_connections:
            return
        disconnected = set()
        for websocket in self._export_connections[export_id]:
            try:
                await websocket.send_json({
                    "type": "export_update",
                    "data": data
                })
            except Exception:
                disconnected.add(websocket)
        for ws in disconnected:
            self._export_connections[export_id].discard(ws)

    async def connect_system(self, websocket: WebSocket):
        """连接系统状态 WebSocket。"""
        await websocket.accept()
        self._system_connections.add(websocket)
        # 启动推送任务（如果还没启动）
        if self._system_push_task is None or self._system_push_task.done():
            self._system_push_task = asyncio.create_task(self._push_system_stats())

    def disconnect_system(self, websocket: WebSocket):
        """断开系统状态 WebSocket。"""
        self._system_connections.discard(websocket)

    async def _push_system_stats(self):
        """定期推送系统状态。"""
        while self._system_connections:
            try:
                stats = self._get_system_stats()
                disconnected = set()
                for websocket in self._system_connections:
                    try:
                        await websocket.send_json({
                            "type": "system_stats",
                            "data": stats
                        })
                    except Exception:
                        disconnected.add(websocket)
                for ws in disconnected:
                    self._system_connections.discard(ws)
                await asyncio.sleep(2)  # 每2秒推送一次
            except Exception:
                await asyncio.sleep(2)

    def _get_system_stats(self) -> dict:
        """获取系统状态。"""
        # CPU 使用率
        cpu_percent = psutil.cpu_percent(interval=None)

        # 内存信息
        memory = psutil.virtual_memory()
        memory_total = memory.total
        memory_used = memory.used
        memory_percent = memory.percent

        # 磁盘信息
        disk = psutil.disk_usage('/')
        disk_total = disk.total
        disk_used = disk.used
        disk_percent = disk.percent

        # GPU 使用率（支持 NVIDIA/AMD/Intel 全系显卡）
        gpu_percent = 0
        gpu_memory_used = 0
        gpu_memory_total = 0
        gpu_available = False
        gpu_name = None

        try:
            # 方法1: nvidia-smi（NVIDIA 显卡）
            nvidia_result = subprocess.run(
                ['nvidia-smi', '--query-gpu=utilization.gpu,memory.used,memory.total,name', '--format=csv,noheader,nounits'],
                capture_output=True, text=True, timeout=5
            )
            if nvidia_result.returncode == 0:
                parts = nvidia_result.stdout.strip().split(',')
                if len(parts) >= 4:
                    gpu_percent = float(parts[0].strip())
                    gpu_memory_used = int(parts[1].strip()) * 1024 * 1024
                    gpu_memory_total = int(parts[2].strip()) * 1024 * 1024
                    gpu_name = parts[3].strip()
                    gpu_available = True
                    logger.info(f"GPU 检测(nvidia-smi): {gpu_name}, 使用率 {gpu_percent}%")
            else:
                logger.warning(f"nvidia-smi 返回非零: {nvidia_result.stderr.strip()}")
        except FileNotFoundError:
            logger.warning("nvidia-smi 不可用（未安装 NVIDIA 驱动或不在 PATH 中）")
        except Exception as e:
            logger.warning(f"nvidia-smi 执行异常: {e}")

        # 方法2: Windows PowerShell 性能计数器（通用，任务管理器数据源）
        if not gpu_available:
            try:
                # 先列出可用的 GPU 计数器集
                list_cmd = '(Get-Counter -ListSet "GPU *" -ErrorAction SilentlyContinue).Counter | Out-String'
                try:
                    result = subprocess.run(
                        ['powershell', '-NoProfile', '-Command', list_cmd],
                        capture_output=True, text=True, timeout=5
                    )
                    if result.returncode == 0 and result.stdout.strip():
                        logger.info(f"PowerShell GPU 计数器列表: {result.stdout.strip()[:200]}")
                except Exception as e:
                    logger.debug(f"列出 GPU 计数器失败: {e}")

                ps_commands = [
                    # 方案A: % GPU Usage (Windows 10 17063+, 任务管理器数据源)
                    # 使用 -Maximum 而非 -Average，与任务管理器计算方式一致
                    ('$c = (Get-Counter "\\GPU(*)\\% GPU Usage" -ErrorAction SilentlyContinue).CounterSamples; '
                     'if ($c) { $u = ($c | Measure-Object -Property CookedValue -Maximum).Maximum } else { '
                     '$c = (Get-Counter "\\GPU Engine(*)\\Utilization Percentage" -ErrorAction SilentlyContinue).CounterSamples; '
                     'if (-not $c) { exit 1 }; '
                     '$u = ($c | Measure-Object -Property CookedValue -Maximum).Maximum }; '
                     '$m = (Get-Counter "\\GPU(*)\\Dedicated Memory Used" -ErrorAction SilentlyContinue).CounterSamples; '
                     '$mu = 0; if ($m) { $mu = ($m | Measure-Object -Property CookedValue -Sum).Sum * 1024 * 1024 }; '
                     '$ml = (Get-Counter "\\GPU(*)\\Dedicated Memory Limit" -ErrorAction SilentlyContinue).CounterSamples; '
                     '$mt = 0; if ($ml) { $mt = ($ml | Measure-Object -Property CookedValue -Maximum).Maximum * 1024 * 1024 }; '
                     'Write-Output "$u,$mu,$mt"'),
                ]

                for exe_name in ['powershell', 'pwsh']:
                    for ps_cmd in ps_commands:
                        try:
                            result = subprocess.run(
                                [exe_name, '-NoProfile', '-Command', ps_cmd],
                                capture_output=True, text=True, timeout=5
                            )
                            if result.returncode == 0:
                                out = result.stdout.strip()
                                if out and out not in ('', '0', '0,0,0', '0,0'):
                                    parts = out.split(',')
                                    if len(parts) >= 3:
                                        gpu_percent = float(parts[0].strip())
                                        gpu_memory_used = int(parts[1].strip())
                                        gpu_memory_total = int(parts[2].strip())
                                        if gpu_percent > 0 or gpu_memory_total > 0:
                                            gpu_available = True
                                            logger.info(f"GPU 检测(PowerShell): 使用率 {gpu_percent}%")
                                            break
                            else:
                                logger.debug(f"PowerShell({exe_name}) 退出码 {result.returncode}")
                        except FileNotFoundError:
                            continue
                        except Exception as e:
                            logger.debug(f"PowerShell({exe_name}) 异常: {e}")
                    if gpu_available:
                        break

                if not gpu_available:
                    # 失败时打印原始输出以便诊断
                    logger.warning("PowerShell GPU 计数器不可用，尝试诊断模式...")
                    try:
                        diag = subprocess.run(
                            ['powershell', '-NoProfile', '-Command',
                             'Get-Counter -ListSet "GPU*" -ErrorAction SilentlyContinue | Format-Table -AutoSize | Out-String'],
                            capture_output=True, text=True, timeout=5
                        )
                        if diag.stdout.strip():
                            logger.info(f"可用 GPU 计数器集: {diag.stdout.strip()[:300]}")
                        else:
                            logger.warning(f"无 GPU 计数器集，stderr: {diag.stderr.strip()[:200]}")
                    except Exception as e:
                        logger.debug(f"GPU 计数器诊断失败: {e}")
            except Exception as e:
                logger.warning(f"PowerShell GPU 检测异常: {e}")

        # 方法3: torch.cuda（PyTorch 环境备选）
        if not gpu_available:
            try:
                import torch
                if torch.cuda.is_available():
                    device = torch.cuda.current_device()
                    gpu_memory_used = torch.cuda.memory_allocated(device)
                    gpu_memory_total = torch.cuda.get_device_properties(device).total_memory
                    gpu_name = torch.cuda.get_device_name(device)
                    if gpu_memory_total > 0:
                        gpu_percent = (gpu_memory_used / gpu_memory_total) * 100
                    gpu_available = True
                    logger.info(f"GPU 检测(torch): {gpu_name}, 使用率 {gpu_percent}%")
            except ImportError:
                logger.warning("torch 不可用")
            except Exception as e:
                logger.warning(f"torch GPU 检测异常: {e}")

        if not gpu_available:
            logger.info("GPU 检测: 所有方法均未检测到 GPU")

        return {
            "cpu": {
                "percent": cpu_percent,
                "status": "warning" if cpu_percent > 80 else "normal"
            },
            "memory": {
                "total": memory_total,
                "used": memory_used,
                "percent": memory_percent,
                "status": "warning" if memory_percent > 80 else "normal"
            },
            "disk": {
                "total": disk_total,
                "used": disk_used,
                "percent": disk_percent,
                "status": "warning" if disk_percent > 90 else "normal"
            },
            "gpu": {
                "percent": gpu_percent,
                "memory_used": gpu_memory_used,
                "memory_total": gpu_memory_total,
                "name": gpu_name,
                "status": "warning" if gpu_percent > 80 else "normal"
            }
        }


# 全局单例
ws_manager = WebSocketManager()
