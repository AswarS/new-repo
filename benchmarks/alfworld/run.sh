#!/usr/bin/env bash
# ============================================
# ALFWorld Benchmark - 启动脚本
# ============================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# 检查 Python
if ! command -v python &>/dev/null; then
    echo "[ERROR] Python 未安装或不在 PATH 中"
    exit 1
fi

# 检查 alfworld
if ! python -c "import alfworld" 2>/dev/null; then
    echo "[ERROR] alfworld 未安装"
    echo "  请运行: pip install alfworld[full]"
    echo "  然后运行: alfworld-download"
    exit 1
fi

# 检查 websockets
if ! python -c "import websockets" 2>/dev/null; then
    echo "[INFO] 安装依赖..."
    pip install -r requirements.txt
fi

# 检查 agent backend
if ! curl -s -o /dev/null http://localhost:3000/health 2>/dev/null; then
    echo "[WARN] claude-code-backend 可能未启动 (localhost:3000)"
    echo "[WARN] 请确认 agent 服务正在运行"
fi

echo ""
echo "============================================"
echo "  ALFWorld Benchmark"
echo "============================================"
echo ""

python run_alfworld.py "$@"
