"""ALFWorld Agent 交互层 — 通过 WebSocket 驱动 claude-code-backend"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Callable, Optional

import websockets

from alfworld_config import AGENT_WS_URL, STEP_TIMEOUT, SESSION_TIMEOUT
from alfworld_prompts import (
    build_system_prompt,
    build_first_message,
    build_step_message,
    parse_action,
)

# Skill 注入模式
SKILL_INJECT_SLASH_COMMAND = "slash_command"  # 发送 /skill-name 触发 Skill Tool
SKILL_INJECT_PROMPT = "prompt"  # 直接嵌入 system prompt（兜底）


@dataclass
class StepRecord:
    """单步记录"""
    step_idx: int
    observation: str
    action: str
    raw_response: str
    latency_ms: float = 0.0


@dataclass
class EpisodeResult:
    """单次任务运行结果"""
    task_idx: int
    task_type: str
    game_file: str
    success: bool
    steps: int
    total_steps_attempted: int
    max_steps: int
    reward: float
    steps_log: list[StepRecord] = field(default_factory=list)
    error: str = ""
    session_id: str = ""


class ALFWorldAgent:
    """通过 WebSocket 连接 claude-code-backend 的 ALFWorld agent"""

    def __init__(
        self,
        ws_url: str = AGENT_WS_URL,
        skill_name: str = "",
        skill_args: str = "",
        skill_content: str = "",
        inject_mode: str = SKILL_INJECT_SLASH_COMMAND,
        step_timeout: int = STEP_TIMEOUT,
        session_timeout: int = SESSION_TIMEOUT,
    ):
        """
        Args:
            ws_url: claude-code-backend WebSocket URL
            skill_name: Skill 名称（用于 /skill-name 调用），如 "alfworld-planner"
            skill_args: 传给 Skill 的参数
            skill_content: Skill 内容（仅 inject_mode="prompt" 时使用）
            inject_mode: "slash_command"（通过 Skill Tool）或 "prompt"（嵌入提示）
            step_timeout: 单步超时秒数
            session_timeout: 整个 session 超时秒数
        """
        self._ws_url = ws_url
        self._skill_name = skill_name
        self._skill_args = skill_args
        self._skill_content = skill_content
        self._inject_mode = inject_mode
        self._step_timeout = step_timeout
        self._session_timeout = session_timeout
        self._ws = None
        self._session_id = ""
        # 如果是 prompt 模式，将 skill 内容嵌入 system prompt；否则 system prompt 不含 skill
        if inject_mode == SKILL_INJECT_PROMPT and skill_content:
            self._system_prompt = build_system_prompt(skill_content)
        else:
            self._system_prompt = build_system_prompt()

    async def connect(self) -> str:
        """建立 WebSocket 连接，返回 session_id"""
        self._ws = await websockets.connect(
            self._ws_url,
            max_size=10 * 1024 * 1024,
            close_timeout=10,
        )

        # 等待 session_started 消息
        msg = await asyncio.wait_for(self._ws.recv(), timeout=self._step_timeout)
        data = json.loads(msg)

        if data.get("type") == "result":
            inner = data.get("message", {})
            if isinstance(inner, dict) and inner.get("type") == "session_started":
                self._session_id = inner.get("sessionId", str(uuid.uuid4()))
            else:
                self._session_id = str(uuid.uuid4())
        else:
            self._session_id = str(uuid.uuid4())

        return self._session_id

    async def close(self):
        """关闭连接"""
        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass
            self._ws = None

    async def send_message(self, content: str) -> str:
        """发送消息给 agent 并等待完整回复"""
        if not self._ws:
            raise RuntimeError("WebSocket not connected")

        message = json.dumps({
            "type": "user_message",
            "content": content,
            "id": str(uuid.uuid4()),
        })
        await self._ws.send(message)

        response_parts = []
        try:
            while True:
                raw = await asyncio.wait_for(self._ws.recv(), timeout=self._step_timeout)
                data = json.loads(raw)
                msg_type = data.get("type", "")

                if msg_type == "assistant":
                    text = self._extract_text(data)
                    if text:
                        response_parts.append(text)
                elif msg_type == "result":
                    text = self._extract_text(data)
                    if text:
                        response_parts.append(text)
                    break
                elif msg_type == "error":
                    raise RuntimeError(f"Agent error: {data.get('error', 'Unknown')}")
        except asyncio.TimeoutError:
            if not response_parts:
                raise

        return "\n".join(response_parts)

    def _extract_text(self, data: dict) -> str:
        """从服务端消息中提取文本内容"""
        message = data.get("message", {})
        if isinstance(message, dict):
            inner_msg = message.get("message", message)
            if isinstance(inner_msg, dict):
                content = inner_msg.get("content", [])
                if isinstance(content, list):
                    texts = []
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            texts.append(block.get("text", ""))
                    return "\n".join(texts)
                elif isinstance(content, str):
                    return content
        if isinstance(message, str):
            return message
        return ""

    async def _invoke_skill(self):
        """
        通过发送 /skill-name 消息触发 claude-code-backend 的 Skill Tool。

        Skill Tool 会加载对应的 Skill 内容并注入到 session 上下文中，
        后续 agent 的推理将受到该 Skill 的指导。
        """
        if not self._skill_name:
            return

        # 构造 /skill-name args 格式的消息
        skill_msg = f"/{self._skill_name}"
        if self._skill_args:
            skill_msg += f" {self._skill_args}"

        # 发送 skill 调用并等待完成（不需要解析返回内容，skill 已注入上下文）
        await self.send_message(skill_msg)

    async def _single_turn(self, prompt: str) -> str:
        """每步新建连接，发送完整 prompt 并获取回复（backend 是单轮模式）"""
        try:
            await self.connect()
            response = await self.send_message(prompt)
            return response
        finally:
            await self.close()

    async def run_episode(
        self,
        first_observation: str,
        step_fn: Callable[[str], tuple[str, float, bool, dict]],
        max_steps: int = 50,
        task_idx: int = 0,
        task_type: str = "",
        game_file: str = "",
        admissible_commands: list[str] = None,
    ) -> EpisodeResult:
        """
        运行一个完整的 ALFWorld episode。
        每步新建 WebSocket 连接，将完整对话历史作为 prompt 发送。
        """
        steps_log = []
        total_steps = 0
        success = False
        reward = 0.0
        error = ""

        # 对话历史（用于多轮拼接）
        history: list[str] = []

        # 首条消息：system prompt + few-shot + 初始观察
        first_msg = f"{self._system_prompt}\n\n{build_first_message(first_observation, admissible_commands)}"
        history.append(first_msg)

        try:
            t0 = time.perf_counter()
            response = await self._single_turn(first_msg)
            latency = (time.perf_counter() - t0) * 1000

            action = parse_action(response)
            steps_log.append(StepRecord(
                step_idx=0, observation=first_observation,
                action=action, raw_response=response, latency_ms=latency,
            ))

            if not action:
                error = "Failed to parse first action"
                return self._build_result(
                    task_idx, task_type, game_file, False,
                    0, 1, max_steps, 0.0, steps_log, error,
                )

            history.append(f"Action: {action}")

            # 交互循环
            for step_i in range(1, max_steps):
                total_steps = step_i

                # 如果 action 是 think，不执行环境动作，直接回复 OK 并继续
                if action.startswith("think:"):
                    history.append("OK.")

                    full_prompt = "\n\n".join(history)
                    t0 = time.perf_counter()
                    response = await self._single_turn(full_prompt)
                    latency = (time.perf_counter() - t0) * 1000

                    action = parse_action(response)
                    steps_log.append(StepRecord(
                        step_idx=step_i, observation="OK.",
                        action=action, raw_response=response, latency_ms=latency,
                    ))

                    if not action:
                        error = f"Failed to parse action at step {step_i}"
                        break

                    history.append(f"Action: {action}")
                    continue

                # 环境执行（非 think 动作）
                obs, step_reward, done, info = step_fn(action)
                reward = step_reward
                admissible_commands = info.get("admissible_commands", [])

                if done:
                    success = step_reward > 0
                    steps_log.append(StepRecord(
                        step_idx=step_i, observation=obs,
                        action="[DONE]", raw_response="", latency_ms=0,
                    ))
                    break

                # 将观察加入历史
                step_msg = build_step_message(obs, admissible_commands)
                history.append(step_msg)

                # 拼接完整对话历史发送
                full_prompt = "\n\n".join(history)

                t0 = time.perf_counter()
                response = await self._single_turn(full_prompt)
                latency = (time.perf_counter() - t0) * 1000

                action = parse_action(response)
                steps_log.append(StepRecord(
                    step_idx=step_i, observation=obs,
                    action=action, raw_response=response, latency_ms=latency,
                ))

                if not action:
                    error = f"Failed to parse action at step {step_i}"
                    break

                history.append(f"Action: {action}")

        except Exception as e:
            error = str(e)

        return self._build_result(
            task_idx, task_type, game_file, success,
            total_steps, total_steps, max_steps, reward, steps_log, error,
        )

    def _build_result(
        self, task_idx, task_type, game_file, success,
        steps, total_steps, max_steps, reward, steps_log, error,
    ) -> EpisodeResult:
        return EpisodeResult(
            task_idx=task_idx,
            task_type=task_type,
            game_file=game_file,
            success=success,
            steps=steps,
            total_steps_attempted=total_steps,
            max_steps=max_steps,
            reward=reward,
            steps_log=steps_log,
            error=error,
            session_id=self._session_id,
        )
