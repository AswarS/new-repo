#!/usr/bin/env bash
# ============================================
# Skill 质量评估实验 - 启动脚本
# ============================================

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT"

# 检查 Python
if ! command -v python &>/dev/null; then
    echo "[ERROR] Python 未安装或不在 PATH 中"
    exit 1
fi

# 检查依赖
if ! python -c "import httpx" 2>/dev/null; then
    echo "[INFO] 安装依赖..."
    pip install -r src/requirements.txt
fi

# 检查 .env
if [ ! -f .env ]; then
    echo "[WARN] .env 文件不存在，从模板创建..."
    cp .env.example .env
    echo "[WARN] 请编辑 .env 填入 AGENT_AUTH_TOKEN 后重新运行"
    exit 1
fi

# 检查 agent backend
if ! curl -s -o /dev/null http://localhost:3000/api/sessions 2>/dev/null; then
    echo "[WARN] claude-code-backend 可能未启动 (localhost:3000)"
    echo "[WARN] 请确认 agent 服务正在运行"
fi

# 创建输出目录
mkdir -p output

echo ""
echo "============================================"
echo "  Skill 质量评估实验"
echo "============================================"
echo ""

# 默认参数
PHASES="all"
REPEATS=5
EXTRA_ARGS=""

# 解析参数
while [[ $# -gt 0 ]]; do
    case "$1" in
        --phases)    PHASES="$2"; shift 2;;
        --repeats)   REPEATS="$2"; shift 2;;
        --skill-ids) EXTRA_ARGS="$EXTRA_ARGS --skill-ids $2"; shift 2;;
        --help)
            echo "用法: ./run.sh [选项]"
            echo ""
            echo "选项:"
            echo "  --phases PHASES       运行维度 (applicability,utility,transferability,all)"
            echo "  --repeats N           每个 case 重复次数，默认: 5"
            echo "  --skill-ids IDS       逗号分隔的 skill_id，默认: 全部"
            echo "  --help                显示帮助"
            echo ""
            echo "示例:"
            echo "  ./run.sh                                    运行全部实验"
            echo "  ./run.sh --phases utility --repeats 3       只跑 Utility"
            echo "  ./run.sh --skill-ids career_direction_exploration"
            exit 0;;
        *) shift;;
    esac
done

echo "配置:"
echo "  Skills 目录: $PROJECT_ROOT/skills"
echo "  输出目录:    $PROJECT_ROOT/output"
echo "  历史目录:    $PROJECT_ROOT/claude-code-backend/history"
echo "  运行参数:    phases=$PHASES repeats=$REPEATS $EXTRA_ARGS"
echo ""

python src/run_experiment.py \
    --skills-dir skills \
    --output-dir output \
    --history-dir claude-code-backend/history \
    --phases "$PHASES" \
    --repeats "$REPEATS" \
    $EXTRA_ARGS

echo ""
echo "[DONE] 实验完成，结果见 output/ 目录"
