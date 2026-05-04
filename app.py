# -*- coding: utf-8 -*-
"""CogniFlow WebUI - FastAPI 主入口。

提供：
- REST API
- WebSocket 实时通信
- Vue3 前端静态文件托管
- Windows 系统托盘支持
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import os
import sys
import threading
import ctypes

from backend.database import init_db
from backend.routers import atlas, image, annotation, category, model, training, launch, websocket, inference, rule_engine, ws_stream

# 系统托盘支持
from system_tray import TrayManager, open_browser

# ===== 控制台管理（仅 Windows）=====
_console_handler_cb = None  # 保持回调引用，防止被 GC

def _init_console():
    """初始化控制台：阻止关闭窗口时退出。

    console=False 时 PyInstaller 使用 pythonw 启动，无控制台窗口。
    后续可通过托盘菜单 AllocConsole() 创建新控制台。
    关闭该控制台窗口时，SetConsoleCtrlHandler 拦截信号，
    调用 FreeConsole() 断开连接，程序不退出。
    """
    global _console_handler_cb
    try:
        kernel32 = ctypes.windll.kernel32

        # 注册控制台事件处理器
        HandlerRoutine = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_uint)
        def _ctrl_handler(dwCtrlType):
            if dwCtrlType == 0:  # CTRL_CLOSE_EVENT
                kernel32.FreeConsole()
                return True
            return False

        cb = HandlerRoutine(_ctrl_handler)
        _console_handler_cb = cb
        kernel32.SetConsoleCtrlHandler(cb, 1)
    except Exception:
        pass


def show_console_window():
    """打开控制台窗口（供托盘菜单调用）。"""
    try:
        kernel32 = ctypes.windll.kernel32
        # 如果已有控制台则显示，否则创建新控制台
        kernel32.AllocConsole()
        sys.stdout = open('CONOUT$', 'w')
        sys.stderr = open('CONOUT$', 'w')
        print("[CogniFlow] 控制台已打开，关闭窗口不会退出程序")
    except Exception:
        pass

# 统一数据目录（所有持久化数据都放这里）
# 本地开发: ./data, Docker: /app/data
_DEFAULT_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
DATA_DIR = os.environ.get("DATA_DIR", _DEFAULT_DATA_DIR)

# 上传文件存储目录
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
MODEL_DIR = os.path.join(UPLOAD_DIR, "models")

# 推理输出目录
INFERENCE_OUTPUT_DIR = os.path.join(DATA_DIR, "inference_output")

# 日志目录
LOGS_DIR = os.path.join(DATA_DIR, "logs")

# YOLO 训练输出目录（YOLO 默认 runs/detect/，我们统一放这里）
YOLO_RUNS_DIR = os.path.join(DATA_DIR, "runs")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理。"""
    # 确保所有数据目录存在
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(os.path.join(UPLOAD_DIR, "images"), exist_ok=True)
    os.makedirs(os.path.join(UPLOAD_DIR, "videos"), exist_ok=True)
    os.makedirs(MODEL_DIR, exist_ok=True)
    os.makedirs(INFERENCE_OUTPUT_DIR, exist_ok=True)
    os.makedirs(LOGS_DIR, exist_ok=True)
    os.makedirs(YOLO_RUNS_DIR, exist_ok=True)

    init_db()
    # 设置事件循环给流式推理 WebSocket 管理器
    import asyncio
    try:
        loop = asyncio.get_running_loop()
        ws_stream.stream_conn_manager.set_loop(loop)
    except RuntimeError:
        pass
    yield


# 创建 FastAPI 应用
app = FastAPI(
    title="CogniFlow WebUI",
    description="CogniFlow 训练图集管理、模型管理、数据标注、规则引擎",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(atlas.router, prefix="/api/atlas", tags=["图集管理"])
app.include_router(image.router, prefix="/api/images", tags=["图片管理"])
app.include_router(annotation.router, prefix="/api/annotations", tags=["标注管理"])
app.include_router(category.router, prefix="/api/categories", tags=["类别管理"])
app.include_router(model.router, prefix="/api/models", tags=["模型管理"])
app.include_router(training.router, prefix="/api/training", tags=["训练管理"])
app.include_router(launch.router, prefix="/api/launch", tags=["模型启动"])
app.include_router(inference.router, prefix="/api/inference", tags=["模型测试"])
app.include_router(rule_engine.router, tags=["规则引擎"])
app.include_router(websocket.router, prefix="/ws", tags=["WebSocket"])
app.include_router(ws_stream.router, prefix="/ws", tags=["流式推理WebSocket"])

# 挂载上传文件目录为静态文件服务
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(os.path.join(UPLOAD_DIR, "images"), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_DIR, "videos"), exist_ok=True)
os.makedirs(MODEL_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# 挂载推理输出目录为静态文件服务
os.makedirs(INFERENCE_OUTPUT_DIR, exist_ok=True)
app.mount("/inference_output", StaticFiles(directory=INFERENCE_OUTPUT_DIR), name="inference_output")

# 挂载 Vue 前端静态文件（开发时若无 dist 目录则跳过）
# Docker 环境: WEBUI_DIST=/app/webui/dist
_WEBUI_DIST = os.environ.get("WEBUI_DIST", os.path.join(os.path.dirname(os.path.abspath(__file__)), "webui", "dist"))
if os.path.exists(_WEBUI_DIST):
    app.mount("/", StaticFiles(directory=_WEBUI_DIST, html=True), name="frontend")


@app.get("/")
async def root():
    """根路径重定向到前端。"""
    if os.path.exists(_WEBUI_DIST):
        return RedirectResponse(url="/index.html")
    return {"message": "CogniFlow API running", "docs": "/docs"}


@app.get("/api/health")
async def health_check():
    """健康检查端点。"""
    return {"status": "ok"}


def start_with_tray() -> None:
    """启动应用并集成系统托盘（仅 Windows）。"""
    import uvicorn

    # 判断是否为 Windows 平台
    is_windows = sys.platform.startswith("win")

    # 注册控制台事件处理器（console=False 时无窗口，用于后续 AllocConsole 的窗口关闭处理）
    if is_windows:
        _init_console()

    # 用于存储 uvicorn 服务器实例
    server_config = {"server": None}

    def stop_server() -> None:
        """停止 uvicorn 服务器。"""
        if server_config["server"]:
            server_config["server"].should_exit = True

    if is_windows:
        # Windows 平台：启动托盘 + 自动打开浏览器
        tray_manager = TrayManager(
            on_quit_callback=stop_server,
            on_show_console_callback=show_console_window,
        )

        # 在独立线程中启动托盘
        tray_thread = threading.Thread(target=tray_manager.start, daemon=True)
        tray_thread.start()

        # 等待一小段时间确保托盘启动
        import time
        time.sleep(0.5)

        # 自动打开浏览器
        print("[CogniFlow] 正在打开浏览器...")
        open_browser()

        # 启动 FastAPI 应用
        print("[CogniFlow] 启动 WebUI 服务...")
        config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info")
        server_config["server"] = uvicorn.Server(config)
        server_config["server"].run()
    else:
        # 非 Windows 平台：直接打开浏览器
        open_browser()
        print("[CogniFlow] 启动 WebUI 服务...")
        uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    start_with_tray()
