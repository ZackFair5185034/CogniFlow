# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, collect_submodules
try:
    from PyInstaller.hooks.hookutils import collect_data_files
except ImportError:
    from PyInstaller.utils.hooks import collect_data_files

datas = [('webui/dist', 'webui/dist')]
binaries = []
hiddenimports = [
    # FastAPI 核心
    'fastapi',
    'fastapi.applications',
    'fastapi.runtime',
    'starlette',
    'starlette.applications',
    'starlette.routing',
    'starlette.middleware',
    'starlette.responses',
    'starlette.staticfiles',
    'python_multipart',
    # Uvicorn
    'uvicorn',
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
    # SQLAlchemy
    'sqlalchemy',
    'sqlalchemy.orm',
    'sqlalchemy.ext',
    'sqlalchemy.ext.declarative',
    # OpenCV
    'cv2',
    # PIL
    'PIL',
    'PIL.Image',
    # Ultralytics
    'ultralytics',
    'ultralytics.models',
    'ultralytics.utils',
    # Torch
    'torch',
    'torch.nn',
    # 后端模块
    'backend.database',
    'backend.schemas',
    'backend.websocket_manager',
    'backend.routers.atlas',
    'backend.routers.image',
    'backend.routers.annotation',
    'backend.routers.category',
    'backend.routers.model',
    'backend.routers.training',
    'backend.routers.launch',
    'backend.routers.inference',
    'backend.routers.websocket',
    'backend.routers.ws_stream',
    'backend.routers.rule_engine',
    # 系统托盘模块
    'system_tray',
    'system_tray.tray_manager',
    'system_tray.browser',
    # 托盘依赖
    'pystray',
    'PIL',
    'PIL.Image',
    'PIL.ImageDraw',
]

# 收集子模块
for pkg in ['fastapi', 'starlette', 'uvicorn', 'sqlalchemy', 'PIL', 'cv2', 'ultralytics']:
    try:
        submods = collect_submodules(pkg)
        hiddenimports.extend(submods)
    except Exception:
        pass

# 收集数据文件
for pkg in ['fastapi', 'starlette', 'uvicorn']:
    try:
        tmp = collect_data_files(pkg)
        datas.extend(tmp)
    except Exception:
        pass


a = Analysis(
    ['app.py'],
    pathex=['.'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='cogniflow',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='cogniflow',
)
