"""ALFWorld benchmark 配置"""

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

# ALFWorld 配置
ALFWORLD_DATA_DIR = os.getenv("ALFWORLD_DATA_DIR", "")  # 留空则使用 alfworld 默认路径
MAX_STEPS = int(os.getenv("ALFWORLD_MAX_STEPS", "50"))
MAX_TASKS = int(os.getenv("ALFWORLD_MAX_TASKS", "0"))  # 0 = 全部
REPEATS = int(os.getenv("ALFWORLD_REPEATS", "3"))

# 并发控制
MAX_CONCURRENCY = int(os.getenv("MAX_CONCURRENCY", "3"))

# 超时（秒）
STEP_TIMEOUT = int(os.getenv("ALFWORLD_STEP_TIMEOUT", "60"))
SESSION_TIMEOUT = int(os.getenv("ALFWORLD_SESSION_TIMEOUT", "600"))

# 输出
OUTPUT_DIR = Path(os.getenv("ALFWORLD_OUTPUT_DIR", str(_project_root / "output" / "alfworld")))

# ALFWorld 任务类型
TASK_TYPES = [
    "pick_and_place",
    "pick_clean_then_place",
    "pick_heat_then_place",
    "pick_cool_then_place",
    "look_at_obj_in_light",
    "pick_two_obj_and_place",
]
