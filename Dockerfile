# CogniFlow Dockerfile
# 支持 CPU 和 GPU (CUDA) 构建

# ========== 构建参数 ==========
# 构建时传入: docker build --build-arg TARGET=cpu ..
# TARGET: cpu | gpu
ARG TARGET=cpu

# Python 版本
ARG PYTHON_VERSION=3.10

# ========== 阶段1: 前端构建 ==========
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# 复制前端代码
COPY webui/package*.json ./

# 安装 pnpm
RUN npm install -g pnpm

# 安装依赖
RUN pnpm install

# 复制源码
COPY webui/ ./

# 构建前端
RUN pnpm run build

# ========== 阶段2: 后端构建 ==========
FROM python:${PYTHON_VERSION}-slim AS backend-builder

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
    git \
    && rm -rf /var/lib/apt/lists/*

# 复制 requirements.txt
COPY requirements.txt .

# 安装 Python 依赖（CPU 版 PyTorch）
ARG TARGET
ENV TARGET=${TARGET}

RUN pip install --no-cache-dir --upgrade pip && \
    if [ "$TARGET" = "gpu" ]; then \
        pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cu118; \
    else \
        pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu; \
    fi && \
    pip install --no-cache-dir -r requirements.txt

# engine 已通过 requirements.txt 安装，无需复制源码
# ========== 阶段3: 运行镜像 ==========
FROM python:${PYTHON_VERSION}-slim AS runtime

LABEL maintainer="CogniFlow Team"
LABEL description="CogniFlow - 通用视觉感知处理框架"

# 安装运行时依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# 创建非 root 用户
RUN groupadd -r cogniflow && useradd -r -g cogniflow cogniflow

WORKDIR /app

# 复制后端代码（仅 backend/，无源码泄露）
COPY --from=backend-builder /usr/local/lib/python${PYTHON_VERSION}/site-packages /usr/local/lib/python${PYTHON_VERSION}/site-packages
COPY --from=backend-builder /usr/local/bin /usr/local/bin
COPY backend/ ./backend/

# 上传目录（空目录，用于用户数据持久化）
COPY uploads/ ./uploads/

# 复制前端构建产物
COPY --from=frontend-builder /app/frontend/dist ./webui/dist

# 暴露端口
EXPOSE 8000 5173

# 环境变量
ENV PYTHONUNBUFFERED=1
ENV LOG_LEVEL=INFO

# 切换到非 root 用户
USER cogniflow

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/')" || exit 1

# 启动命令
# 默认启动后端（前端静态文件由后端托管）
CMD ["python", "-m", "uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000"]

# ========== 多架构支持说明 ==========
# 构建示例:
#
#   # CPU 版本
#   docker build -t cogniflow/cogniflow:latest-cpu --build-arg TARGET=cpu .
#
#   # GPU 版本 (需要 CUDA)
#   docker build -t cogniflow/cogniflow:latest-gpu --build-arg TARGET=gpu .
#
#   # 推送到 Docker Hub
#   docker push cogniflow/cogniflow:latest-cpu
#   docker push cogniflow/cogniflow:latest-gpu
#
#   # 多架构构建 (需要 docker buildx)
#   docker buildx create --use
#   docker buildx build --platform linux/amd64,linux/arm64 \
#       -t cogniflow/cogniflow:latest \
#       --build-arg TARGET=cpu \
#       --push .
