#!/usr/bin/env pwsh
# CogniFlow Build Script - Windows
# Usage: .\scripts\build.ps1 <command>
#
# Environment variables:
#   USE_VENV=1         - Use virtual environment (not needed if already in venv)
#   PYINSTALLER_OPTS=  - PyInstaller extra options

param(
    [string]$Command = "help"
)

# ========== Config ==========
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$BackendDir  = Join-Path $ProjectRoot "backend"
$WebuiDir   = Join-Path $ProjectRoot "webui"
$EngineDir  = Join-Path $ProjectRoot "engine"
$OutputDir  = Join-Path $ProjectRoot "dist"

# Store original location and switch to project root
# This ensures we use the correct Python and venv
$OriginalDir = Get-Location
Set-Location $ProjectRoot

# Find Python in current project venv first
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$VenvPip = Join-Path $ProjectRoot ".venv\Scripts\pip.exe"
$VenvPyInstaller = Join-Path $ProjectRoot ".venv\Scripts\pyinstaller.exe"

# Colors
function Log { param($m) Write-Host "[INFO] $m" -ForegroundColor Cyan }
function Ok  { param($m) Write-Host "[OK] $m" -ForegroundColor Green }
function Warn{ param($m) Write-Host "[WARN] $m" -ForegroundColor Yellow }
function Err { param($m) Write-Host "[ERROR] $m" -ForegroundColor Red; Set-Location $OriginalDir; exit 1 }

# ========== Pre-check ==========
function Test-Command {
    param([string]$cmd)
    $null -ne (Get-Command $cmd -ErrorAction SilentlyContinue)
}

# ========== Backend Build + PyInstaller ==========
function Build-Backend {
    Log "========== Build Backend (Windows) =========="

    # Check Python in venv first
    if (Test-Path $VenvPython) {
        $PythonExe = $VenvPython
        $PipExe = $VenvPip
        Log "Using venv Python: $PythonExe"
    } elseif (Test-Command "python") {
        $PythonExe = "python"
        $PipExe = "pip"
        Log "Using system Python"
    } else {
        Err "Python not found. Install Python 3.8+ https://python.org"
    }

    $pyVer = & $PythonExe --version 2>&1
    Log "Python: $pyVer"

    # Check pip
    if (-not (Test-Path $PipExe) -and -not (Test-Command "pip")) {
        Err "pip not found"
    }

    # Install PyInstaller if not exists
    $PyInstallerExists = Test-Path $VenvPyInstaller
    if (-not $PyInstallerExists) {
        Log "Installing PyInstaller..."
        if ($PipExe) {
            & $PipExe install pyinstaller pyinstaller-hooks-contrib
        } else {
            & $PythonExe -m pip install pyinstaller pyinstaller-hooks-contrib
        }
    }

    # Create spec file (if not exists)
    $specFile = Join-Path $ProjectRoot "cogniflow.spec"
    if (-not (Test-Path $specFile)) {
        Log "Generating PyInstaller spec file..."
        New-Item -ItemType File -Path $specFile -Force
        # Create a basic spec file
        @"
# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, collect_submodules

datas = [('webui/dist', 'webui/dist')]
binaries = []
hiddenimports = [
    'fastapi', 'starlette', 'uvicorn', 'sqlalchemy', 'PIL', 'cv2', 'ultralytics',
    'backend.database', 'backend.schemas', 'backend.websocket_manager',
    'backend.routers.atlas', 'backend.routers.image', 'backend.routers.annotation',
    'backend.routers.category', 'backend.routers.model', 'backend.routers.training',
    'backend.routers.launch', 'backend.routers.inference', 'backend.routers.websocket',
    'backend.routers.ws_stream', 'backend.routers.rule_engine',
    'system_tray', 'system_tray.tray_manager', 'system_tray.browser',
    'pystray', 'PIL.Image', 'PIL.ImageDraw',
]

for pkg in ['fastapi', 'starlette', 'uvicorn', 'sqlalchemy', 'PIL', 'cv2', 'ultralytics']:
    try:
        submods = collect_submodules(pkg)
        hiddenimports.extend(submods)
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
"@ | Set-Content -Path $specFile -Encoding UTF8
    }

    # Package
    Log "PyInstaller packaging (may take 5-10 minutes)..."

    if (Test-Path $VenvPyInstaller) {
        & $VenvPyInstaller cogniflow.spec --clean --noconfirm
    } else {
        & $PythonExe -m PyInstaller cogniflow.spec --clean --noconfirm
    }

    if ($LASTEXITCODE -ne 0) {
        Err "PyInstaller packaging failed"
    }

    # Copy frontend build output to dist
    $distBackend = Join-Path $ProjectRoot "dist\cogniflow"
    $webuiDist = Join-Path $WebuiDir "dist"
    if (Test-Path $webuiDist) {
        $targetWebui = Join-Path $distBackend "webui\dist"
        Log "Copying frontend build output to dist..."
        Copy-Item -Path $webuiDist -Destination $targetWebui -Recurse -Force
    }

    Ok "Backend build complete!"
    Log "Output dir: $OutputDir\cogniflow\cogniflow.exe"
}

# ========== Frontend Build ==========
function Build-Frontend {
    Log "========== Build Frontend =========="

    if (-not (Test-Command "node")) {
        Err "Node.js not found. Install https://nodejs.org"
    }
    Log "Node: $(node --version)"

    # Select package manager
    if (Test-Command "pnpm") {
        $Pkg = "pnpm"
    } elseif (Test-Command "yarn") {
        $Pkg = "yarn"
    } else {
        $Pkg = "npm"
        Warn "pnpm not found, using npm (recommended: npm install -g pnpm)"
    }
    Log "Using: $Pkg"

    Log "Installing frontend dependencies..."
    & $Pkg install

    Log "Building production version..."
    & $Pkg run build

    Ok "Frontend build complete: $WebuiDir\dist"
}

# ========== Full Build ==========
function Build-All {
    Log "========== Full Build =========="
    Build-Backend
    Build-Frontend
    Ok "All builds complete!"
    Log ""
    Log "Output:"
    Log "  Backend exe: $OutputDir\cogniflow\cogniflow.exe"
    Log "  Frontend: $WebuiDir\dist"
    Log ""
    Log "Start backend: $OutputDir\cogniflow\cogniflow.exe"
    Log "Start frontend: cd $WebuiDir && pnpm dev"
}

# ========== Clean ==========
function Clear-Build {
    Log "Cleaning build artifacts..."

    # Python
    Get-ChildItem -Path $ProjectRoot -Directory -Filter "__pycache__" -Recurse -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force
    Get-ChildItem -Path $ProjectRoot -Filter "*.pyc" -Recurse -ErrorAction SilentlyContinue | Remove-Item -Force
    Get-ChildItem -Path $ProjectRoot -Directory -Filter "*.egg-info" -Recurse -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force

    # PyInstaller output (keep venv)
    @("build", "dist\cogniflow") | ForEach-Object {
        $p = Join-Path $ProjectRoot $_
        if (Test-Path $p) { Remove-Item -Path $p -Recurse -Force -ErrorAction SilentlyContinue }
    }

    # PyInstaller spec
    @("cogniflow.spec") | ForEach-Object {
        Get-ChildItem -Path $ProjectRoot -Filter $_ -ErrorAction SilentlyContinue | Remove-Item -Force
    }

    # Frontend
    $webuiDist = Join-Path $WebuiDir "dist"
    if (Test-Path $webuiDist) { Remove-Item -Path $webuiDist -Recurse -Force -ErrorAction SilentlyContinue }

    Ok "Clean complete!"
}

# ========== Help ==========
function Show-Help {
    Write-Host ""
    Write-Host "CogniFlow Build Script (Windows)"
    Write-Host ""
    Write-Host "Usage: .\scripts\build.ps1 <command>"
    Write-Host ""
    Write-Host "Commands:"
    Write-Host "  backend   Build backend + PyInstaller package to exe"
    Write-Host "  frontend  Build frontend"
    Write-Host "  all       Build backend + frontend"
    Write-Host "  clean     Clean build artifacts"
    Write-Host "  help      Show help"
    Write-Host ""
    Write-Host "Output:"
    Write-Host "  exe:  dist\cogniflow\cogniflow.exe"
    Write-Host "  Frontend: webui\dist"
    Write-Host ""
}

# ========== Main ==========
switch ($Command) {
    "backend"  { Build-Backend }
    "frontend" { Build-Frontend }
    "all"      { Build-All }
    "clean"    { Clear-Build }
    "help"     { Show-Help }
    default    { Show-Help }
}

# Restore original location
Set-Location $OriginalDir
