#!/bin/bash
# CogniFlow 启动脚本 - Linux/macOS
# 用法: ./scripts/start.sh [dev|production]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
WEBUI_DIR="$SCRIPT_DIR/webui"

# 端口
API_PORT="${API_PORT:-8000}"
WEB_PORT="${WEB_PORT:-5173}"

start_backend() {
    echo "启动后端 :$API_PORT ..."
    cd "$BACKEND_DIR"
    python -m uvicorn app:app --host 0.0.0.0 --port $API_PORT "$@"
}

start_frontend() {
    echo "启动前端 :$WEB_PORT ..."
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
        start_backend --reload &
        start_frontend
        ;;
    production|*)
        echo "生产模式: 仅后端（前端已嵌入）"
        echo "访问: http://localhost:$API_PORT"
        start_backend
        ;;
esac
