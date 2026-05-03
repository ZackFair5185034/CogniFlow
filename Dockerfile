# CogniFlow Dockerfile - 单阶段构建 + pip 缓存
# 支持 CPU / GPU (CUDA)
#
# 构建参数:
#   TARGET=cpu|gpu
#   PYTHON_VERSION=3.10
#
# 构建示例:
#   docker build -t cogniflow/cogniflow:latest-cpu --build-arg TARGET=cpu .
#   docker build -t cogniflow/cogniflow:latest-gpu --build-arg TARGET=gpu .

ARG TARGET=cpu
ARG PYTHON_VERSION=3.10

# ========== 前端构建阶段 ==========
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

COPY webui/package*.json ./
RUN npm install -g pnpm
RUN pnpm install

COPY webui/ ./
RUN pnpm run build

# ========== 运行阶段 ==========
FROM python:${PYTHON_VERSION}-slim

LABEL maintainer="CogniFlow Team"
LABEL description="CogniFlow - 通用视觉感知处理框架"

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制 requirements.txt（用于 pip install）
COPY requirements.txt .

# 安装 Python 依赖（使用 buildkit cache 加速后续构建）
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir --upgrade pip && \
    if [ "$TARGET" = "gpu" ]; then \
        pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cu118; \
    else \
        pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu; \
    fi && \
    pip install --no-cache-dir -r requirements.txt

# 创建非 root 用户
RUN groupadd -r cogniflow && useradd -r -g cogniflow cogniflow

# 复制后端代码（到 /app/backend/）
COPY backend/ ./backend/

# 复制前端构建产物（到 /app/webui/dist/）
COPY --from=frontend-builder /app/frontend/dist ./webui/dist

# 创建数据目录结构（运行时由 docker volume 持久化）
RUN mkdir -p /app/data/{data,uploads/images,uploads/videos,uploads/models,inference_output,model_cache,checkpoints,datasets,runs,logs}

# 环境变量
ENV PYTHONUNBUFFERED=1
ENV LOG_LEVEL=INFO
ENV DATA_DIR=/app/data
ENV PYTHONPATH=/app

# 切换到非 root 用户
USER cogniflow

# 暴露端口
EXPOSE 8000 5173

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/')" || exit 1

# 启动命令（WORKDIR=/app，backend/ 在 /app/backend/，uvicorn 启动目录相对于 PYTHONPATH）
CMD ["python", "-m", "uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000"]
