"""ALFWorld 环境封装

封装 alfworld TextWorld 环境，提供简洁的 reset/step 接口。
"""

from __future__ import annotations

import os
import yaml
from pathlib import Path
from typing import Optional

from alfworld.agents.environment import get_environment as _get_environment


class ALFWorldEnv:
    """ALFWorld TextWorld 环境封装"""

    def __init__(self, config_path: Optional[str] = None, data_dir: Optional[str] = None):
        """
        初始化 ALFWorld 环境。

        Args:
            config_path: alfworld 配置文件路径，留空使用默认
            data_dir: alfworld 数据目录，留空使用默认
        """
        self._config_path = config_path
        self._data_dir = data_dir
        self._env = None
        self._game_files: list[str] = []
        self._current_idx = 0
        self._current_task_type = ""
        self._setup_done = False

    def setup(self) -> int:
        """
        加载环境配置，返回可用任务总数。
        """
        if self._setup_done:
            return len(self._game_files)

        # 加载 alfworld 配置
        config = self._load_config()

        # 设置环境变量（alfworld 依赖这个）
        if self._data_dir:
            os.environ["ALFWORLD_DATA"] = self._data_dir

        # 获取 split（使用 eval_out_of_distribution 作为测试集）
        env_type = config.get("env", {}).get("type", "AlfredTWEnv")
        env_cls = _get_environment(env_type)
        self._env = env_cls(config, train_eval="eval_out_of_distribution")
        self._env = self._env.init_env(batch_size=1)

        # 收集所有游戏文件
        self._game_files = self._env.gamefiles
        self._setup_done = True

        return len(self._game_files)

    def _load_config(self) -> dict:
        """加载 ALFWorld YAML 配置"""
        if self._config_path and Path(self._config_path).exists():
            with open(self._config_path, "r") as f:
                return yaml.safe_load(f)

        # 尝试从 ALFWORLD_DATA 环境变量的同级 configs 目录加载
        alfworld_data = os.environ.get("ALFWORLD_DATA", "")
        if alfworld_data:
            # ALFWORLD_DATA 通常指向 data/data，配置在 data/configs
            data_parent = Path(alfworld_data).parent
            candidate = data_parent / "configs" / "base_config.yaml"
            if candidate.exists():
                with open(candidate, "r") as f:
                    return yaml.safe_load(f)

        # 尝试从当前脚本目录的 data/configs 加载
        script_dir = Path(__file__).parent
        local_config = script_dir / "data" / "configs" / "base_config.yaml"
        if local_config.exists():
            with open(local_config, "r") as f:
                return yaml.safe_load(f)

        # 使用 alfworld 默认配置
        import alfworld.agents.environment as _env_mod
        alfworld_base = Path(_env_mod.__file__).parent.parent
        default_config = alfworld_base / "configs" / "base_config.yaml"

        if default_config.exists():
            with open(default_config, "r") as f:
                return yaml.safe_load(f)

        # 最小化配置
        return {
            "env": {"type": "AlfredTWEnv"},
            "logic": {"domain": "alfred", "grammar": "alfred"},
        }

    def get_task_count(self) -> int:
        """返回可用任务数"""
        return len(self._game_files)

    def get_task_type(self, game_file: str) -> str:
        """从游戏文件路径推断任务类型"""
        path = game_file.lower()
        if "pick_and_place" in path:
            return "pick_and_place"
        elif "pick_clean_then_place" in path:
            return "pick_clean_then_place"
        elif "pick_heat_then_place" in path:
            return "pick_heat_then_place"
        elif "pick_cool_then_place" in path:
            return "pick_cool_then_place"
        elif "look_at_obj_in_light" in path:
            return "look_at_obj_in_light"
        elif "pick_two_obj" in path:
            return "pick_two_obj_and_place"
        return "unknown"

    def reset(self, task_idx: Optional[int] = None) -> tuple[str, dict]:
        """
        重置环境到指定任务。

        Args:
            task_idx: 任务索引，None 则按顺序取下一个

        Returns:
            (observation, info) 其中 info 包含 task_type, game_file, admissible_commands
        """
        if not self._setup_done:
            self.setup()

        if task_idx is not None:
            self._current_idx = task_idx

        # 设置游戏文件
        self._env.game_file = self._game_files[self._current_idx]
        game_file = self._game_files[self._current_idx]
        self._current_task_type = self.get_task_type(game_file)

        # 重置环境
        obs, infos = self._env.reset()

        # obs 是 list 或 tuple（batch_size=1），取第一个
        observation = obs[0] if isinstance(obs, (list, tuple)) else obs
        admissible = infos.get("admissible_commands", [[]])[0]

        info = {
            "task_type": self._current_task_type,
            "game_file": game_file,
            "admissible_commands": admissible,
            "task_idx": self._current_idx,
        }

        self._current_idx += 1
        return observation, info

    def step(self, action: str) -> tuple[str, float, bool, dict]:
        """
        执行一步动作。

        Args:
            action: 文本动作

        Returns:
            (observation, reward, done, info)
        """
        obs, scores, dones, infos = self._env.step([action])

        observation = obs[0] if isinstance(obs, (list, tuple)) else obs
        reward = scores[0] if isinstance(scores, (list, tuple)) else scores
        done = dones[0] if isinstance(dones, (list, tuple)) else dones
        admissible = infos.get("admissible_commands", [[]])[0]

        info = {
            "admissible_commands": admissible,
            "won": bool(reward > 0 and done),
        }

        return observation, float(reward), bool(done), info

    def close(self):
        """关闭环境"""
        if self._env:
            try:
                self._env.close()
            except Exception:
                pass
