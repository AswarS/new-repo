@echo off
chcp 65001 >nul
REM ============================================
REM ALFWorld Benchmark - 启动脚本
REM ============================================

setlocal

set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%..\..

cd /d "%SCRIPT_DIR%"

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python 未安装或不在 PATH 中
    exit /b 1
)

REM 检查 alfworld
python -c "import alfworld" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] alfworld 未安装
    echo   请运行: pip install alfworld[full]
    echo   然后运行: alfworld-download
    exit /b 1
)

REM 检查 websockets
python -c "import websockets" >nul 2>&1
if errorlevel 1 (
    echo [INFO] 安装依赖...
    pip install -r requirements.txt
)

REM 检查 agent backend
curl -s -o nul http://localhost:3000/health >nul 2>&1
if errorlevel 1 (
    echo [WARN] claude-code-backend 可能未启动 (localhost:3000)
    echo [WARN] 请确认 agent 服务正在运行
)

echo.
echo ============================================
echo   ALFWorld Benchmark
echo ============================================
echo.

python run_alfworld.py %*

if errorlevel 1 (
    echo.
    echo [ERROR] 运行失败
    exit /b 1
)
exit /b 0
