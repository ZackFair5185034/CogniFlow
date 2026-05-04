#!/usr/bin/env pwsh
# CogniFlow 构建脚本 - Windows
# 用法: .\scripts\build.ps1 <命令>
#
# 环境变量:
#   USE_VENV=1         - 使用虚拟环境
#   TARGET=exe|dir     - 打包类型: exe=单文件, dir=目录（默认 exe）
#   PYINSTALLER_OPTS=  - PyInstaller 额外参数

param(
    [string]$Command = "help"
)

# ========== 配置 ==========
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$BackendDir  = Join-Path $ProjectRoot "backend"
$WebuiDir   = Join-Path $ProjectRoot "webui"
$EngineDir  = Join-Path $ProjectRoot "engine"
$OutputDir  = Join-Path $ProjectRoot "dist"

# 颜色
function Log { param($m) Write-Host "[INFO] $m" -ForegroundColor Cyan }
function Ok  { param($m) Write-Host "[OK] $m" -ForegroundColor Green }
function Warn{ param($m) Write-Host "[WARN] $m" -ForegroundColor Yellow }
function Err { param($m) Write-Host "[ERROR] $m" -ForegroundColor Red; exit 1 }

# ========== 前置检查 ==========
function Test-Command {
    param([string]$cmd)
    $null -ne (Get-Command $cmd -ErrorAction SilentlyContinue)
}

# ========== 后端构建 + PyInstaller 打包 ==========
function Build-Backend {
    Log "========== 构建后端 (Windows) =========="

    # 检查 Python
    if (-not (Test-Command "python")) {
        Err "Python 未安装，请先安装 Python 3.8+ https://python.org"
    }
    $pyVer = python --version 2>&1
    Log "Python: $pyVer"

    # 检查 pip
    if (-not (Test-Command "pip")) {
        Err "pip 未找到"
    }

    # 虚拟环境
    if ($env:USE_VENV -eq "1") {
        Log "使用虚拟环境..."
        if (-not (Test-Path "venv")) {
            python -m venv venv
        }
        & ".\venv\Scripts\Activate.ps1"
    }

    # 安装依赖
    Log "安装 Python 依赖..."
    & pip install --upgrade pip
    & pip install -r requirements.txt

    # 安装 PyInstaller
    Log "安装 PyInstaller..."
    & pip install pyinstaller pyinstaller-hooks-contrib

    # 创建 spec 文件（如果没有）
    $specFile = Join-Path $ProjectRoot "cogniflow.spec"
    if (-not (Test-Path $specFile)) {
        Log "生成 PyInstaller spec 文件..."
        New-FileContent $specFile (Make-SpecContent)
    }

    # 打包
    Log "PyInstaller 打包中（这可能需要 5-10 分钟）..."
    $env:PYINSTALLER_OPTS = if ($env:PYINSTALLER_OPTS) { $env:PYINSTALLER_OPTS } else { "" }

    & python -m PyInstaller cogniflow.spec --clean --noconfirm $env:PYINSTALLER_OPTS.Split(" ")

    if ($LASTEXITCODE -ne 0) {
        Err "PyInstaller 打包失败"
    }

    # 复制前端构建产物到输出目录
    $distBackend = Join-Path $ProjectRoot "dist\backend"
    $webuiDist = Join-Path $WebuiDir "dist"
    if (Test-Path $webuiDist) {
        $targetWebui = Join-Path $distBackend "webui\dist"
        Log "复制前端构建产物到输出目录..."
        Copy-Item -Path $webuiDist -Destination $targetWebui -Recurse -Force
    }

    Ok "后端构建完成！"
    Log "输出目录: $OutputDir\backend\"
    Log "运行: $OutputDir\backend\cogniflow.exe"
}

# ========== 生成 PyInstaller spec 内容 ==========
function Make-SpecContent {}

# ========== 前端构建 ==========
function Build-Frontend {
    Log "========== 构建前端 =========="

    if (-not (Test-Command "node")) {
        Err "Node.js 未安装，请先安装 https://nodejs.org"
    }
    Log "Node: $(node --version)"

    # 选择包管理器
    if (Test-Command "pnpm") {
        $Pkg = "pnpm"
    } elseif (Test-Command "yarn") {
        $Pkg = "yarn"
    } else {
        $Pkg = "npm"
        Warn "未检测到 pnpm，使用 npm（推荐: npm install -g pnpm）"
    }
    Log "使用: $Pkg"

    Log "安装前端依赖..."
    & $Pkg install

    Log "构建生产版本..."
    & $Pkg run build

    Ok "前端构建完成: $WebuiDir\dist"
}

# ========== 全量构建 ==========
function Build-All {
    Log "========== 全量构建 =========="
    Build-Backend
    Build-Frontend
    Ok "全部构建完成！"
    Log ""
    Log "输出:"
    Log "  后端 exe: $OutputDir\backend\cogniflow.exe"
    Log "  前端: $WebuiDir\dist"
    Log ""
    Log "启动后端: $OutputDir\backend\cogniflow.exe"
    Log "启动前端: cd $WebuiDir && pnpm dev"
}

# ========== 清理 ==========
function Clear-Build {
    Log "清理构建产物..."

    # Python
    Get-ChildItem -Path $ProjectRoot -Directory -Filter "__pycache__" -Recurse -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force
    Get-ChildItem -Path $ProjectRoot -Filter "*.pyc" -Recurse -ErrorAction SilentlyContinue | Remove-Item -Force
    Get-ChildItem -Path $ProjectRoot -Directory -Filter "*.egg-info" -Recurse -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force
    @("build", "dist", "venv") | ForEach-Object {
        $p = Join-Path $ProjectRoot $_
        if (Test-Path $p) { Remove-Item -Path $p -Recurse -Force -ErrorAction SilentlyContinue }
    }

    # PyInstaller
    @("*.spec", "*.manifest") | ForEach-Object {
        Get-ChildItem -Path $ProjectRoot -Filter $_ -ErrorAction SilentlyContinue | Remove-Item -Force
    }
    $specDir = Join-Path $ProjectRoot "dist"
    if (Test-Path $specDir) { Remove-Item -Path $specDir -Recurse -Force -ErrorAction SilentlyContinue }

    # 前端
    @("node_modules", "dist") | ForEach-Object {
        $p = Join-Path $WebuiDir $_
        if (Test-Path $p) { Remove-Item -Path $p -Recurse -Force -ErrorAction SilentlyContinue }
    }

    Ok "清理完成！"
}

# ========== 帮助 ==========
function Show-Help {
    Write-Host @"
CogniFlow 构建脚本 (Windows)

用法: .\scripts\build.ps1 <命令>

命令:
  backend   构建后端 + PyInstaller 打包为 exe
  frontend  构建前端
  all       构建后端 + 前端
  clean     清理构建产物
  help      显示帮助

环境变量:
  USE_VENV=1        使用虚拟环境
  PYINSTALLER_OPTS= PyInstaller 额外参数

示例:
  .\build.ps1 all        # 构建全部
  .\build.ps1 backend    # 后端（打包 exe）
  .\build.ps1 frontend   # 前端

输出:
  exe:  dist\cogniflow\cogniflow.exe
  前端: webui\dist

"@
}

# ========== 主入口 ==========
switch ($Command) {
    "backend"  { Build-Backend }
    "frontend" { Build-Frontend }
    "all"      { Build-All }
    "clean"    { Clear-Build }
    "help"     { Show-Help }
    default    { Show-Help }
}
