"""实验配置模块"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Agent Backend 配置
AGENT_BASE_URL = os.getenv("AGENT_BASE_URL", "http://localhost:3000")
AGENT_AUTH_TOKEN = os.getenv("AGENT_AUTH_TOKEN", "")

# 实验参数
DEFAULT_REPEATS = int(os.getenv("DEFAULT_REPEATS", "5"))
MAX_CONCURRENCY = int(os.getenv("MAX_CONCURRENCY", "3"))
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "180"))

# Agent 工作目录（session 创建时指定）
AGENT_CWD = os.getenv("AGENT_CWD", str(Path(__file__).parent.parent))

# 路径
PROJECT_ROOT = Path(__file__).parent.parent
SKILLS_DIR = PROJECT_ROOT / "skills"
OUTPUT_DIR = PROJECT_ROOT / "output"

# 模型标识（用于报告中区分，实际模型由 agent backend 决定）
# 通过不同的 system prompt 或 session 配置来模拟"强/弱模型"差异
STRONG_MODEL = os.getenv("STRONG_MODEL", "claude-agent-default")
WEAK_MODEL = os.getenv("WEAK_MODEL", "claude-agent-default")
