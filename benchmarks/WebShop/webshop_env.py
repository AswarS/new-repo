"""WebShop 环境封装

封装 WebShop TextEnv，提供简洁的 reset/step 接口供 agent 调用。
支持两种模式:
  1. 使用 WebShop 内置 SimServer（本地模拟，无需启动 Flask 服务）
  2. 连接远程 WebShop Flask 服务（TODO: 未来支持）
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

# 将 WebShop 根目录加入 path，以便导入其模块
WEBSHOP_ROOT = Path(__file__).parent.parent / "WebShop"
sys.path.insert(0, str(WEBSHOP_ROOT))

from web_agent_site.envs.web_agent_text_env import WebAgentTextEnv
from webshop_config import HUMAN_GOALS_FILE, WEBSHOP_NUM_PRODUCTS


class WebShopEnv:
    """WebShop Text 环境封装"""

    def __init__(
        self,
        num_products: Optional[int] = None,
        human_goals: bool = True,
        observation_mode: str = "text",
    ):
        """
        初始化 WebShop 环境。

        Args:
            num_products: 产品数量限制，None 表示使用全部
            human_goals: 是否使用人工标注的目标
            observation_mode: 'text' 或 'html'
        """
        self._num_products = num_products or (WEBSHOP_NUM_PRODUCTS or None)
        self._human_goals = human_goals
        self._observation_mode = observation_mode
        self._env: Optional[WebAgentTextEnv] = None
        self._goals: list[str] = []
        self._current_idx = 0
        self._setup_done = False

    def setup(self) -> int:
        """
        初始化环境，加载产品和目标。返回可用任务总数。
        """
        if self._setup_done:
            return len(self._goals)

        # 创建 TextEnv（使用 SimServer，无需 Flask 服务）
        # 使用全量产品文件以匹配更多 human goals
        full_file = str(WEBSHOP_ROOT / "data" / "items_shuffle.json")
        full_attr = str(WEBSHOP_ROOT / "data" / "items_ins_v2.json")
        import os
        file_path = full_file if os.path.exists(full_file) else None
        attr_path = full_attr if os.path.exists(full_attr) else None

        kwargs = dict(
            observation_mode=self._observation_mode,
            num_products=self._num_products,
            human_goals=self._human_goals,
        )
        if file_path:
            kwargs["file_path"] = file_path
        if attr_path:
            kwargs["attr_path"] = attr_path

        self._env = WebAgentTextEnv(**kwargs)

        # 加载目标列表
        self._goals = self._load_goals()
        # 使用 SimServer 内部 goals 数量作为实际可用任务数
        if hasattr(self._env, 'server') and self._env.server and hasattr(self._env.server, 'goals'):
            self._goals = self._goals or [None] * len(self._env.server.goals)
            self._num_goals = len(self._env.server.goals)
        else:
            self._num_goals = len(self._goals)
        self._setup_done = True

        return self._num_goals

    def _load_goals(self) -> list[str]:
        """加载评估用目标列表"""
        if HUMAN_GOALS_FILE.exists():
            with open(HUMAN_GOALS_FILE, "r", encoding="utf-8") as f:
                goals = json.load(f)
            return goals
        # 如果没有 human_goals 文件，从环境中获取
        return []

    def get_task_count(self) -> int:
        """返回可用任务数"""
        return self._num_goals if self._setup_done else 0

    def reset(self, task_idx: Optional[int] = None) -> tuple[str, dict]:
        """
        重置环境到指定任务。

        Args:
            task_idx: 任务索引，None 则按顺序取下一个

        Returns:
            (observation, info) 其中 info 包含 goal, task_idx, available_actions
        """
        if not self._setup_done:
            self.setup()

        if task_idx is not None:
            self._current_idx = task_idx

        idx = self._current_idx

        # 使用整数 session 来确定性地选择目标
        # 对 goals 数量取模，避免 IndexError
        num_goals = len(self._env.server.goals) if hasattr(self._env, 'server') and self._env.server else None
        session_idx = idx % num_goals if num_goals else idx
        obs, _ = self._env.reset(session=session_idx)

        # 获取任务目标（instruction_text）
        goal = self._env.instruction_text
        available_actions = self._env.get_available_actions()

        info = {
            "goal": goal,
            "task_idx": idx,
            "available_actions": available_actions,
        }

        self._current_idx += 1
        return obs, info

    def step(self, action: str) -> tuple[str, float, bool, dict]:
        """
        执行一步动作。

        Args:
            action: 文本动作，格式为 "search[query]" 或 "click[element]"

        Returns:
            (observation, reward, done, info)
        """
        obs, reward, done, info = self._env.step(action)

        available_actions = self._env.get_available_actions()
        step_info = {
            "available_actions": available_actions,
            "reward": reward,
            "done": done,
        }

        return obs, float(reward), bool(done), step_info

    def get_instruction_text(self) -> str:
        """获取当前任务的目标描述"""
        return self._env.instruction_text if self._env else ""

    def close(self):
        """关闭环境"""
        if self._env:
            try:
                self._env.close()
            except Exception:
                pass
