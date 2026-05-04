#!/bin/bash
# CogniFlow 构建脚本 - Linux/macOS
# 用法: ./scripts/build.sh [backend|frontend|binary|all|docker|clean]
#
# 环境变量:
#   USE_VENV=1           - 使用虚拟环境
#   CYTHONIZE=1         - 使用 Cython 编译 engine/ 为 .so（保护源码）
#   TARGET=cpu|gpu       - Docker 构建目标（默认 cpu）
#   VERSION=xxx          - Docker 镜像版本

set -e

# ========== 配置 ==========
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
WEBUI_DIR="$PROJECT_ROOT/webui"
ENGINE_DIR="$PROJECT_ROOT/engine"
PYTHON_BIN="${PYTHON_BIN:-python3}"
PIP_BIN="${PIP_BIN:-pip3}"

# 颜色
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; NC='\033[0m'

log() { echo -e "${BLUE}[INFO]${NC} $1"; }
ok()  { echo -e "${GREEN}[OK]${NC} $1"; }
warn(){ echo -e "${YELLOW}[WARN]${NC} $1"; }
err() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# ========== 前置检查 ==========
need() {
    if ! command -v $1 &> /dev/null; then
        err "缺少命令: $1"
    fi
}

# ========== 后端构建 ==========
build_backend() {
    log "========== 构建后端 =========="

    cd "$PROJECT_ROOT"

    need $PIP_BIN

    if [[ "${USE_VENV:-0}" == "1" ]]; then
        log "使用虚拟环境..."
        [[ ! -d "venv" ]] && $PYTHON_BIN -m venv venv
        source venv/bin/activate
        PYTHON_BIN="python"; PIP_BIN="pip"
    fi

    # 安装依赖
    log "安装 Python 依赖..."
    $PIP_BIN install --upgrade pip
    $PIP_BIN install -r requirements.txt

    # Cython 编译 engine/（可选，保护源码）
    if [[ "${CYTHONIZE:-0}" == "1" ]]; then
        $PIP_BIN install cython
        build_cython
    fi

    ok "后端构建完成！"
    log "运行: cd backend && uvicorn app:app --host 0.0.0.0 --port 8000"
}

# ========== Cython 编译 engine/ ==========
build_cython() {
    log "使用 Cython 编译 engine/ 为 .so（源码保护）..."

    cd "$PROJECT_ROOT"

    # Cython 编译
    $PYTHON_BIN -c "
import sys
from Cython.Build import cythonize
from setuptools import find_packages, Distribution

# 找出所有 .pyx 文件
import glob
pyxs = glob.glob('engine/**/*.pyx', recursive=True)
if not pyxs:
    print('No .pyx files found in engine/, skipping Cython')
    sys.exit(0)

print(f'Found .pyx files: {pyxs}')
"

    # 如果有 .pyx 文件才编译
    if compylable=$(find engine -name "*.pyx" 2>/dev/null | head -1); then
        log "编译 $compylable ..."
        $PYTHON_BIN -c "
from Cython.Build import cythonize
from setuptools import Extension
import numpy as np

extensions = [
    Extension('engine.' + f.replace('engine/', '').replace('/', '.').replace('.pyx', ''),
              [f])
    for f in find_cython_files()
]

if extensions:
    from distutils.core import Distribution
    from distutils.core import setup
    setup(ext_modules=cythonize(extensions, language_level=3))
" 2>/dev/null || warn "Cython 编译跳过（无 .pyx 或编译失败）"
    fi

    ok "Cython 编译完成"
}

find_cython_files() {
    find engine -name "*.pyx" 2>/dev/null
}

# ========== 前端构建 ==========
build_frontend() {
    log "========== 构建前端 =========="

    cd "$WEBUI_DIR"

    need node

    # 选择包管理器
    PKG="pnpm"
    for p in pnpm yarn npm; do
        if command -v $p &> /dev/null; then PKG=$p; break; fi
    done
    [[ "$PKG" == "npm" ]] && warn "未检测到 pnpm，使用 npm（推荐: npm install -g pnpm）"
    log "使用: $PKG"

    log "安装前端依赖..."
    $PKG install

    log "构建生产版本..."
    $PKG run build

    ok "前端构建完成: $WEBUI_DIR/dist/"
}

# ========== Docker 构建 ==========
build_docker() {
    log "========== 构建 Docker 镜像 =========="

    need docker

    cd "$PROJECT_ROOT"

    local TARGET="${TARGET:-cpu}"
    local VERSION="${VERSION:-latest}"
    local IMAGE="${IMAGE_NAME:-cogniflow/cogniflow}"

    log "目标: $IMAGE:$VERSION (TARGET=$TARGET)"

    [[ ! -f Dockerfile ]] && err "未找到 Dockerfile"

    docker build \
        --build-arg TARGET="$TARGET" \
        --build-arg PYTHON_VERSION=3.10 \
        -t "$IMAGE:$VERSION" \
        -t "$IMAGE:${TARGET}-latest" \
        -t "$IMAGE:latest" \
        .

    ok "Docker 镜像构建完成！"
    log "运行: docker run -p 8000:8000 $IMAGE:$VERSION"
}

# ========== PyInstaller 原生二进制打包 ==========
build_binary() {
    log "========== PyInstaller 原生二进制打包 =========="

    need $PYTHON_BIN
    need $PIP_BIN

    cd "$PROJECT_ROOT"

    # 使用虚拟环境隔离依赖
    if [[ "${USE_VENV:-1}" == "1" ]]; then
        log "创建/更新虚拟环境..."
        [[ ! -d "venv" ]] && $PYTHON_BIN -m venv venv
        source venv/bin/activate
        PYTHON_BIN="python"; PIP_BIN="pip"
    fi

    # 构建前端（二进制需要 dist/）
    if [[ ! -d "$WEBUI_DIR/dist" ]]; then
        log "前端 dist/ 不存在，先构建前端..."
        build_frontend
    fi

    # 安装项目依赖（避免 PyInstaller 打包时缺模块）
    log "安装项目依赖到虚拟环境..."
    $PIP_BIN install --upgrade pip
    # CPU-only torch（避免下载数 GB 的 CUDA 依赖）
    $PIP_BIN install torch torchvision --index-url https://download.pytorch.org/whl/cpu
    $PIP_BIN install -r requirements.txt

    # 安装 PyInstaller 及常用隐藏导入依赖
    log "安装 PyInstaller..."
    $PIP_BIN install pyinstaller pyinstaller-hooks-contrib \
        fastapi uvicorn starlette python-multipart sqlalchemy \
        pillow numpy opencv-python-headless psutil pyyaml \
        mss pyautogui ffmpeg-python pygetwindow aiosqlite

    # 检查 spec 文件
    if [[ ! -f cogniflow.spec ]]; then
        err "未找到 cogniflow.spec，请确认项目完整性"
    fi

    # PyInstaller 打包
    log "PyInstaller 打包中（这可能需要 5-10 分钟）..."
    $PYTHON_BIN -m PyInstaller cogniflow.spec --clean --noconfirm

    ok "原生二进制打包完成！"
    log "输出: $PROJECT_ROOT/dist/cogniflow/"
}

# ========== 全量构建（后端 + 前端）==========
build_all() {
    log "========== 全量构建 =========="
    build_backend
    build_frontend
    ok "全部构建完成！"
    log ""
    log "启动服务:"
    log "  后端: cd backend && uvicorn app:app --host 0.0.0.0 --port 8000"
    log "  前端: cd webui && pnpm dev"
}

# ========== 清理 ==========
clean() {
    log "清理构建产物..."

    # Python
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true
    find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
    rm -rf build dist .eggs venv 2>/dev/null || true

    # Cython 生成文件
    find engine -name "*.so" -delete 2>/dev/null || true
    find engine -name "*.c" -delete 2>/dev/null || true

    # 前端
    rm -rf "$WEBUI_DIR/node_modules" "$WEBUI_DIR/dist" 2>/dev/null || true

    # Docker
    if command -v docker &> /dev/null; then
        docker images | grep -i cogniflow | awk '{print $3}' | xargs -r docker rmi -f 2>/dev/null || true
    fi

    ok "清理完成！"
}

# ========== 帮助 ==========
help() {
    echo -e "${GREEN}CogniFlow 构建脚本${NC}"
    echo ""
    echo "用法: $0 <命令>"
    echo ""
    echo "命令:"
    echo "  backend   构建后端（+ 可选 Cython 编译）"
    echo "  frontend  构建前端"
    echo "  binary    使用 PyInstaller 打包原生二进制（Linux/macOS 可执行文件）"
    echo "  all       构建后端 + 前端"
    echo "  docker    构建 Docker 镜像"
    echo "  clean     清理构建产物"
    echo "  help      显示帮助"
    echo ""
    echo "环境变量:"
    echo "  USE_VENV=1     使用虚拟环境"
    echo "  CYTHONIZE=1    用 Cython 编译 engine/ 为 .so（源码保护）"
    echo "  TARGET=cpu|gpu Docker 构建目标（默认 cpu）"
    echo "  VERSION=xxx     Docker 镜像版本"
    echo "  IMAGE_NAME=xxx  Docker 镜像名称"
    echo ""
    echo "示例:"
    echo "  $0 all                    # 构建全部"
    echo "  $0 backend                # 仅后端"
    echo "  CYTHONIZE=1 $0 backend    # 后端 + Cython 保护"
    echo "  $0 docker                 # Docker 镜像"
}
# ========== 主入口 ==========
CMD="${1:-help}"
case "$CMD" in
    backend)  build_backend ;;
    frontend) build_frontend ;;
    binary)   build_binary ;;
    all)      build_all ;;
    docker)   build_docker ;;
    clean)    clean ;;
    help|--help|-h) help ;;
    *)        err "未知命令: $CMD" ;;
esac
