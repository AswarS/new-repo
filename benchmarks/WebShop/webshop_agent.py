"""WebShop Agent 交互层 — 通过 WebSocket 驱动 claude-code-backend

脚本只负责发送任务观察并接收 agent 的最终 action。
Skill 的有无由后端启动参数（--add-dir）决定，脚本不感知。
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Callable, Optional

import websockets

from webshop_config import AGENT_WS_URL, STEP_TIMEOUT, SESSION_TIMEOUT
from webshop_prompts import (
    build_system_prompt,
    build_first_message,
    build_step_message,
    parse_action,
)


@dataclass
class StepRecord:
    """单步记录"""
    step_idx: int
    observation: str
    action: str
    raw_response: str
    latency_ms: float = 0.0
    skill_calls: list[str] = field(default_factory=list)


@dataclass
class EpisodeResult:
    """单次任务运行结果"""
    task_idx: int
    goal: str
    success: bool
    reward: float
    steps: int
    total_steps_attempted: int
    max_steps: int
    steps_log: list[StepRecord] = field(default_factory=list)
    error: str = ""
    session_id: str = ""
    skill_invoked: bool = False
    skill_calls_total: list[str] = field(default_factory=list)


class WebShopAgent:
    """通过 WebSocket 连接 claude-code-backend 的 WebShop agent

    每个 episode 使用一个持久 WebSocket 连接（多轮对话）。
    Agent 自主决定是否调用 Skill tool，脚本只关心最终返回的 action。
    """

    def __init__(
        self,
        ws_url: str = AGENT_WS_URL,
        step_timeout: int = STEP_TIMEOUT,
        session_timeout: int = SESSION_TIMEOUT,
    ):
        self._ws_url = ws_url
        self._step_timeout = step_timeout
        self._session_timeout = session_timeout
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._session_id: str = ""

    async def connect(self) -> str:
        """建立 WebSocket 连接，返回 session_id。每次调用都会强制关闭旧连接。"""
        # 强制关闭旧连接，确保不会复用会话
        await self.close()

        self._ws = await websockets.connect(
            self._ws_url, max_size=10 * 1024 * 1024, close_timeout=5,
        )
        raw = await asyncio.wait_for(self._ws.recv(), timeout=30)
        data = json.loads(raw)
        msg = data.get("message", {})
        if msg.get("type") == "session_started":
            self._session_id = msg.get("sessionId", str(uuid.uuid4()))
        else:
            self._session_id = str(uuid.uuid4())
        return self._session_id

    async def close(self):
        """关闭 WebSocket 连接，确保后端释放会话"""
        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass
            self._ws = None
            self._session_id = ""
            # 等待后端处理断开，避免新连接复用旧会话
            await asyncio.sleep(0.1)

    async def send_message(self, content: str) -> tuple[str, list[str]]:
        """发送消息并等待 agent 完成整轮交互，返回 (最终文本, skill调用列表)

        只在收到顶层 {type: "result"} 时才认为 turn 结束。
        中间的 assistant 消息（包括 tool call 和子任务 result）都不提前退出。
        """
        if not self._ws:
            raise RuntimeError("Not connected")

        msg = json.dumps({"type": "user_message", "content": content})
        await self._ws.send(msg)

        response_parts = []
        result_text = ""
        skill_calls = []
        try:
            while True:
                raw = await asyncio.wait_for(
                    self._ws.recv(), timeout=self._step_timeout
                )
                data = json.loads(raw)
                msg_type = data.get("type", "")

                if msg_type == "assistant":
                    message = data.get("message", {})
                    inner_type = message.get("type", "")

                    if inner_type == "assistant":
                        inner_msg = message.get("message", {})
                        content_blocks = inner_msg.get("content", [])
                        if isinstance(content_blocks, list):
                            for block in content_blocks:
                                if isinstance(block, dict):
                                    if block.get("type") == "text":
                                        response_parts.append(block["text"])
                                    elif block.get("type") == "tool_use":
                                        name = block.get("name", "")
                                        if name.startswith("webshop-") or "skill" in name.lower():
                                            skill_calls.append(name)
                    elif inner_type == "result":
                        result_text = message.get("result", "")

                elif msg_type == "result":
                    subtype = data.get("subtype", "")
                    if subtype == "error_during_execution" or data.get("is_error"):
                        errors = data.get("errors", [])
                        err_msg = errors[0] if errors else f"Backend error (subtype={subtype})"
                        raise RuntimeError(f"Backend execution error: {err_msg}")
                    break
                elif msg_type == "error":
                    raise RuntimeError(f"Agent error: {data.get('error')}")
        except asyncio.TimeoutError:
            raise TimeoutError(f"Step timeout ({self._step_timeout}s)")

        if not response_parts and result_text:
            response_parts.append(result_text)

        return "\n".join(response_parts), skill_calls

    async def run_episode(
        self,
        task_idx: int,
        goal: str,
        initial_obs: str,
        env_step_fn: Callable[[str], tuple[str, float, bool, dict]],
        max_steps: int,
        initial_available_actions: dict | None = None,
    ) -> EpisodeResult:
        """
        运行单个 episode。

        使用持久 WebSocket 连接，每步发送 observation，等待 agent 返回 action。
        Agent 内部可能调用 Skill tool 等工具，脚本只关心最终输出的 action。

        Args:
            task_idx: 任务索引
            goal: 任务目标文本
            initial_obs: 初始观察
            env_step_fn: 环境 step 函数 (action) -> (obs, reward, done, info)
            max_steps: 最大步数
            initial_available_actions: 初始页面可用动作
        """
        steps_log: list[StepRecord] = []
        success = False
        reward = 0.0
        total_steps = 0
        error = ""
        all_skill_calls: list[str] = []

        try:
            await self.connect()

            # 第一条消息：system prompt + few-shot + 初始观察 + 目标
            system_prompt = build_system_prompt()
            first_msg = f"{system_prompt}\n\n{build_first_message(initial_obs, goal, initial_available_actions)}"

            t0 = time.perf_counter()
            response, skill_calls = await self.send_message(first_msg)
            latency = (time.perf_counter() - t0) * 1000
            all_skill_calls.extend(skill_calls)

            action = parse_action(response)
            steps_log.append(StepRecord(
                step_idx=0, observation=initial_obs,
                action=action, raw_response=response,
                latency_ms=latency, skill_calls=skill_calls,
            ))

            if not action:
                error = "Failed to parse action at step 0"
            else:
                # 交互循环
                for step_i in range(1, max_steps):
                    total_steps = step_i

                    # 执行动作
                    obs, step_reward, done, info = env_step_fn(action)
                    reward = step_reward

                    if done:
                        success = reward > 0
                        steps_log.append(StepRecord(
                            step_idx=step_i, observation=obs,
                            action="[DONE]", raw_response="", latency_ms=0,
                        ))
                        break

                    # 发送观察，等待 agent 返回 action
                    step_msg = build_step_message(obs, info.get("available_actions") if info else None)

                    t0 = time.perf_counter()
                    response, skill_calls = await self.send_message(step_msg)
                    latency = (time.perf_counter() - t0) * 1000
                    all_skill_calls.extend(skill_calls)

                    action = parse_action(response)
                    steps_log.append(StepRecord(
                        step_idx=step_i, observation=obs,
                        action=action, raw_response=response,
                        latency_ms=latency, skill_calls=skill_calls,
                    ))

                    if not action:
                        print(f"    [DEBUG] step {step_i} raw_response:\n{response[:500]}")
                        error = f"Failed to parse action at step {step_i}"
                        break

        except Exception as e:
            error = str(e)
        finally:
            # 任务结束后发送 /new 创建新会话，再关闭连接
            if self._ws:
                try:
                    await self.send_message("/new")
                except Exception:
                    pass
            await self.close()

        return EpisodeResult(
            task_idx=task_idx,
            goal=goal,
            success=success,
            reward=reward,
            steps=total_steps,
            total_steps_attempted=total_steps,
            max_steps=max_steps,
            steps_log=steps_log,
            error=error,
            session_id=self._session_id,
            skill_invoked=len(all_skill_calls) > 0,
            skill_calls_total=all_skill_calls,
        )
