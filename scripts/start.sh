#!/bin/bash
# CogniFlow 启动脚本 - Linux/macOS
# 用法: ./scripts/start.sh [dev|production]
#
# 环境变量:
#   DATA_DIR     - 数据目录（默认 ~/.cogniflow/data）
#   API_PORT     - 后端端口（默认 8000）
#   WEB_PORT     - 前端端口（默认 5173）

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
WEBUI_DIR="$SCRIPT_DIR/webui"

# 端口
API_PORT="${API_PORT:-8000}"
WEB_PORT="${WEB_PORT:-5173}"

# 数据目录（统一存储所有运行时数据）
DATA_DIR="${DATA_DIR:-$HOME/.cogniflow/data}"
export DATA_DIR

# 创建数据目录结构
setup_data_dir() {
    echo "[INFO] 数据目录: $DATA_DIR"
    mkdir -p "$DATA_DIR"/{data,uploads/images,uploads/videos,uploads/models,inference_output,model_cache,checkpoints,datasets,runs,logs}
    echo "[INFO] 数据目录结构已创建"
}

start_backend() {
    echo "[INFO] 启动后端 :$API_PORT ..."
    cd "$BACKEND_DIR"
    python -m uvicorn app:app --host 0.0.0.0 --port $API_PORT "$@"
}

start_frontend() {
    echo "[INFO] 启动前端 :$WEB_PORT ..."
    cd "$WEBUI_DIR"
    if command -v pnpm &> /dev/null; then
        pnpm dev --host 0.0.0.0 --port $WEB_PORT
    else
        npm run dev -- --host 0.0.0.0 --port $WEB_PORT
    fi
}

case "${1:-production}" in
    dev)
        echo "开发模式: 后端热重载 + 前端开发服务器"
        setup_data_dir
        start_backend --reload &
        start_frontend
        ;;
    production|*)
        echo "生产模式: 仅后端（前端已嵌入）"
        echo "访问: http://localhost:$API_PORT"
        setup_data_dir
        start_backend
        ;;
esac
