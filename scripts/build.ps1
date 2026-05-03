#!/usr/bin/env pwsh
# CogniFlow 构建脚本 - Windows (PowerShell)
# 用法: .\scripts\build.ps1 [backend|frontend|all|docker|clean]

# ========== 配置 ==========
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$BackendDir = Join-Path $ProjectRoot "backend"
$WebuiDir = Join-Path $ProjectRoot "webui"

# 颜色（PowerShell 控制台）
function Log-Info { Write-Host "[INFO] $args" -ForegroundColor Cyan }
function Log-Success { Write-Host "[SUCCESS] $args" -ForegroundColor Green }
function Log-Warn { Write-Host "[WARN] $args" -ForegroundColor Yellow }
function Log-Error { Write-Host "[ERROR] $args" -ForegroundColor Red }

# ========== 前置检查 ==========
function Test-Command {
    param([string]$cmd)
    $null -ne (Get-Command $cmd -ErrorAction SilentlyContinue)
}

function Test-Python {
    try {
        $ver = python --version 2>&1
        if ($LASTEXITCODE -ne 0) { throw "Python not found" }
        Log-Info "Python: $ver"
        return $true
    } catch {
        Log-Error "Python 未找到，请先安装 Python 3.8+"
        return $false
    }
}

# ========== 后端构建 ==========
function Build-Backend {
    Log-Info "========== 构建后端 =========="

    Set-Location $ProjectRoot

    # 创建虚拟环境（可选）
    if ($env:USE_VENV -eq "1") {
        Log-Info "使用虚拟环境..."
        if (-not (Test-Path "venv")) {
            python -m venv venv
        }
        & ".\venv\Scripts\Activate.ps1"
        $PyCmd = "python"
        $PipCmd = "pip"
    } else {
        $PyCmd = "python"
        $PipCmd = "pip"
    }

    # 检查 pip
    if (-not (Test-Command "pip")) {
        Log-Error "pip 未找到"
        exit 1
    }

    # 安装依赖
    Log-Info "安装后端依赖..."
    & pip install --upgrade pip
    & pip install -r requirements.txt

    # 安装 engine 包
    Log-Info "安装 CogniFlow engine 包..."
    & pip install -e .

    Log-Success "后端构建完成！"
}

# ========== 前端构建 ==========
function Build-Frontend {
    Log-Info "========== 构建前端 =========="

    Set-Location $WebuiDir

    # 检查 node
    if (-not (Test-Command "node")) {
        Log-Error "Node.js 未找到，请先安装 https://nodejs.org/"
        exit 1
    }
    Log-Info "Node: $(node --version)"

    # 选择包管理器
    if (Test-Command "pnpm") {
        $PkgMgr = "pnpm"
    } elseif (Test-Command "yarn") {
        $PkgMgr = "yarn"
    } else {
        $PkgMgr = "npm"
        Log-Warn "未检测到 pnpm，使用 npm（推荐安装 pnpm: npm install -g pnpm）"
    }
    Log-Info "使用包管理器: $PkgMgr"

    # 安装依赖
    Log-Info "安装前端依赖（这可能需要几分钟）..."
    & $PkgMgr install

    # 构建
    Log-Info "构建生产版本..."
    & $PkgMgr run build

    Log-Success "前端构建完成！输出: $WebuiDir\dist"
}

# ========== Docker 构建 ==========
function Build-Docker {
    Log-Info "========== 构建 Docker 镜像 =========="

    if (-not (Test-Command "docker")) {
        Log-Error "Docker 未找到，请先安装 https://docker.com/"
        exit 1
    }

    Set-Location $ProjectRoot

    # 检查 Dockerfile
    $dockerfile = Join-Path $ProjectRoot "Dockerfile"
    if (-not (Test-Path $dockerfile)) {
        Log-Error "未找到 Dockerfile，请先创建！"
        exit 1
    }

    $version = if ($env:VERSION) { $env:VERSION } else { "latest" }
    $imageName = if ($env:IMAGE_NAME) { $env:IMAGE_NAME } else { "cogniflow/cogniflow" }

    Log-Info "构建镜像: $imageName`:$version"

    docker build `
        --build-arg VERSION="$version" `
        --build-arg PYTHON_VERSION=3.10 `
        -t "$imageName`:$version" `
        -t "$imageName`:latest" `
        .

    if ($LASTEXITCODE -eq 0) {
        Log-Success "Docker 镜像构建完成！"
        Log-Info "运行容器: docker run -p 8000:8000 -p 5173:5173 $imageName`:$version"
    } else {
        Log-Error "Docker 构建失败"
        exit 1
    }
}

# ========== 清理 ==========
function Clear-Build {
    Log-Info "========== 清理构建产物 =========="

    # Python
    Get-ChildItem -Path $ProjectRoot -Directory -Filter "__pycache__" -Recurse -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force
    Get-ChildItem -Path $ProjectRoot -Filter "*.pyc" -Recurse -ErrorAction SilentlyContinue | Remove-Item -Force
    Get-ChildItem -Path $ProjectRoot -Directory -Filter "*.egg-info" -Recurse -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force
    @("build", "dist", "venv") | ForEach-Object {
        $p = Join-Path $ProjectRoot $_
        if (Test-Path $p) { Remove-Item -Path $p -Recurse -Force }
    }

    # 前端
    @("node_modules", "dist") | ForEach-Object {
        $p = Join-Path $WebuiDir $_
        if (Test-Path $p) { Remove-Item -Path $p -Recurse -Force }
    }

    # Docker 镜像
    if (Test-Command "docker") {
        docker images | Where-Object { $_.Repository -like "*cogniflow*" } | ForEach-Object {
            docker rmi -f $_.ID
        }
    }

    Log-Success "清理完成！"
}

# ========== 帮助 ==========
function Show-Help {
    Write-Host @"
CogniFlow 构建脚本 (Windows PowerShell)

用法: .\scripts\build.ps1 [命令]

命令:
  backend   - 仅构建后端
  frontend  - 仅构建前端
  all       - 构建前后端（默认）
  docker    - 构建 Docker 镜像
  clean     - 清理构建产物
  help      - 显示此帮助

环境变量:
  USE_VENV     - 是否使用虚拟环境（0或1，默认: 0）
  VERSION      - Docker 镜像版本
  IMAGE_NAME   - Docker 镜像名称

示例:
  .\scripts\build.ps1 all           # 构建全部
  .\scripts\build.ps1 backend       # 仅后端
  .\scripts\build.ps1 docker        # Docker 镜像
  .\scripts\build.ps1 clean         # 清理

"@
}

# ========== 主入口 ==========
$cmd = if ($args[0]) { $args[0] } else { "all" }

Log-Info "CogniFlow 构建脚本"
Log-Info "项目目录: $ProjectRoot"

switch ($cmd) {
    "backend" {
        if (-not (Test-Python)) { exit 1 }
        Build-Backend
    }
    "frontend" {
        Build-Frontend
    }
    "all" {
        if (-not (Test-Python)) { exit 1 }
        Build-Backend
        Build-Frontend
    }
    "docker" {
        Build-Docker
    }
    "clean" {
        Clear-Build
    }
    { $_ -in "help", "--help", "-h" } {
        Show-Help
    }
    default {
        Log-Error "未知命令: $cmd"
        Show-Help
        exit 1
    }
}
