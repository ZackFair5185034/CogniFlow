#!/bin/bash
# CogniFlow 构建脚本 - Linux/macOS
# 用法: ./scripts/build.sh [backend|frontend|all|docker|clean]

set -e  # 遇到错误立即退出

# ========== 配置 ==========
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
WEBUI_DIR="$PROJECT_ROOT/webui"
PYTHON_BIN="${PYTHON_BIN:-python3}"
PIP_BIN="${PIP_BIN:-pip3}"
NODE_VERSION="${NODE_VERSION:-18}"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# ========== 前置检查 ==========
check_command() {
    if ! command -v $1 &> /dev/null; then
        log_error "命令 '$1' 未找到，请先安装。"
        exit 1
    fi
}

check_python_version() {
    local py_ver=$($PYTHON_BIN -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    if [[ $(echo "$py_ver < 3.8" | bc -l 2>/dev/null || echo "0") == "1" ]]; then
        log_error "Python 版本需要 >= 3.8，当前: $py_ver"
        exit 1
    fi
    log_info "Python 版本: $py_ver"
}

# ========== 后端构建 ==========
build_backend() {
    log_info "========== 构建后端 =========="

    cd "$PROJECT_ROOT"

    # 创建虚拟环境（可选）
    if [[ "${USE_VENV:-0}" == "1" ]]; then
        log_info "使用虚拟环境..."
        if [ ! -d "venv" ]; then
            $PYTHON_BIN -m venv venv
        fi
        source venv/bin/activate
        PYTHON_BIN="python"
        PIP_BIN="pip"
    fi

    # 检查 pip
    check_command $PIP_BIN

    # 安装 Python 依赖
    log_info "安装后端依赖..."
    $PIP_BIN install --upgrade pip
    $PIP_BIN install -r requirements.txt

    # 注意：不安装 engine 源码包，只安装运行时依赖

    log_success "后端构建完成！"
}

# ========== 前端构建 ==========
build_frontend() {
    log_info "========== 构建前端 =========="

    cd "$WEBUI_DIR"

    # 检查 node
    check_command node

    # 检查 pnpm 或 npm
    if command -v pnpm &> /dev/null; then
        PKG_MANAGER="pnpm"
    else
        PKG_MANAGER="npm"
        log_warn "未检测到 pnpm，使用 npm（推荐安装 pnpm: npm install -g pnpm）"
    fi
    log_info "使用包管理器: $PKG_MANAGER"

    # 安装依赖
    log_info "安装前端依赖（这可能需要几分钟）..."
    $PKG_MANAGER install

    # 构建
    log_info "构建生产版本..."
    $PKG_MANAGER run build

    log_success "前端构建完成！输出: $WEBUI_DIR/dist/"
}

# ========== Docker 构建 ==========
build_docker() {
    log_info "========== 构建 Docker 镜像 =========="

    check_command docker

    cd "$PROJECT_ROOT"

    # 获取版本号
    VERSION=${VERSION:-$(git describe --tags --always 2>/dev/null || echo "latest")}
    IMAGE_NAME="${IMAGE_NAME:-cogniflow/cogniflow}"

    log_info "构建镜像: $IMAGE_NAME:$VERSION"

    # 检查是否有 Dockerfile
    if [ ! -f "$PROJECT_ROOT/Dockerfile" ]; then
        log_error "未找到 Dockerfile，请先创建！"
        exit 1
    fi

    # 构建
    docker build \
        --build-arg VERSION="$VERSION" \
        --build-arg PYTHON_VERSION=3.10 \
        -t "$IMAGE_NAME:$VERSION" \
        -t "$IMAGE_NAME:latest" \
        .

    log_success "Docker 镜像构建完成！"
    log_info "运行容器: docker run -p 8000:8000 -p 5173:5173 $IMAGE_NAME:$VERSION"
}

# ========== 清理 ==========
clean() {
    log_info "========== 清理构建产物 =========="

    # Python
    find "$PROJECT_ROOT" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find "$PROJECT_ROOT" -type f -name "*.pyc" -delete 2>/dev/null || true
    find "$PROJECT_ROOT" -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
    rm -rf "$PROJECT_ROOT/build" "$PROJECT_ROOT/dist" "$PROJECT_ROOT/venv" 2>/dev/null || true

    # 前端
    rm -rf "$WEBUI_DIR/node_modules" "$WEBUI_DIR/dist" 2>/dev/null || true

    # Docker
    if command -v docker &> /dev/null; then
        docker images | grep cogniflow | awk '{print $3}' | xargs -r docker rmi -f 2>/dev/null || true
    fi

    log_success "清理完成！"
}

# ========== 帮助信息 ==========
show_help() {
    echo -e "${GREEN}CogniFlow 构建脚本${NC}"
    echo ""
    echo "用法: $0 [命令]"
    echo ""
    echo "命令:"
    echo "  backend   - 仅构建后端"
    echo "  frontend  - 仅构建前端"
    echo "  all      - 构建前后端（默认）"
    echo "  docker   - 构建 Docker 镜像"
    echo "  clean    - 清理构建产物"
    echo "  help     - 显示此帮助"
    echo ""
    echo "环境变量:"
    echo "  PYTHON_BIN    - Python 解释器路径（默认: python3）"
    echo "  PIP_BIN       - pip 路径（默认: pip3）"
    echo "  USE_VENV      - 是否使用虚拟环境（0或1，默认: 0）"
    echo "  VERSION       - Docker 镜像版本"
    echo "  IMAGE_NAME    - Docker 镜像名称"
    echo ""
}

# ========== 主入口 ==========
main() {
    local cmd="${1:-all}"

    log_info "CogniFlow 构建脚本"
    log_info "项目目录: $PROJECT_ROOT"

    case "$cmd" in
        backend)
            check_python_version
            build_backend
            ;;
        frontend)
            build_frontend
            ;;
        all)
            check_python_version
            build_backend
            build_frontend
            ;;
        docker)
            build_docker
            ;;
        clean)
            clean
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            log_error "未知命令: $cmd"
            show_help
            exit 1
            ;;
    esac
}

main "$@"
