"""WebShop benchmark 配置"""

import os
from pathlib import Path
from dotenv import load_dotenv

# 加载项目根目录 .env
_project_root = Path(__file__).parent.parent.parent
load_dotenv(_project_root / ".env")

# Agent backend 配置
AGENT_WS_URL = os.getenv("AGENT_WS_URL", "ws://localhost:3000/ws")
AGENT_BASE_URL = os.getenv("AGENT_BASE_URL", "http://localhost:3000")
AGENT_AUTH_TOKEN = os.getenv("AGENT_AUTH_TOKEN", "")

# WebShop 环境配置
WEBSHOP_URL = os.getenv("WEBSHOP_URL", "http://localhost:3000")  # WebShop Flask server
WEBSHOP_NUM_PRODUCTS = int(os.getenv("WEBSHOP_NUM_PRODUCTS", "0"))  # 0 = None (use all)
WEBSHOP_HUMAN_GOALS = os.getenv("WEBSHOP_HUMAN_GOALS", "true").lower() == "true"

# 任务配置
MAX_STEPS = int(os.getenv("WEBSHOP_MAX_STEPS", "30"))
MAX_TASKS = int(os.getenv("WEBSHOP_MAX_TASKS", "50"))  # 0 = 全部
REPEATS = int(os.getenv("WEBSHOP_REPEATS", "3"))

# 并发控制
MAX_CONCURRENCY = int(os.getenv("MAX_CONCURRENCY", "3"))

# 超时（秒）
STEP_TIMEOUT = int(os.getenv("WEBSHOP_STEP_TIMEOUT", "60"))
SESSION_TIMEOUT = int(os.getenv("WEBSHOP_SESSION_TIMEOUT", "300"))

# 输出
OUTPUT_DIR = Path(os.getenv("WEBSHOP_OUTPUT_DIR", str(_project_root / "output" / "webshop")))

# WebShop 数据路径
WEBSHOP_DATA_DIR = Path(__file__).parent.parent / "WebShop"
HUMAN_GOALS_FILE = WEBSHOP_DATA_DIR / "baseline_models" / "data" / "human_goals.json"
