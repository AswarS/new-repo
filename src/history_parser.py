"""对话历史解析模块 — 从 claude-code-backend 的 JSONL 历史文件中提取决策路径信息"""

from __future__ import annotations

import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ToolCall:
    """一次工具调用记录"""
    tool_name: str
    tool_input: str = ""
    tool_result: str = ""
    is_error: bool = False


@dataclass
class DecisionStep:
    """Agent 的一次决策步骤"""
    step_index: int
    role: str  # "user" / "assistant" / "tool_result"
    thinking: str = ""
    text_output: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0


@dataclass
class SessionTrace:
    """一个 session 的完整决策路径"""
    session_id: str
    steps: list[DecisionStep] = field(default_factory=list)

    @property
    def total_steps(self) -> int:
        """Agent 响应总步数（仅计 assistant 消息）"""
        return sum(1 for s in self.steps if s.role == "assistant")

    @property
    def total_tool_calls(self) -> int:
        """总工具调用次数"""
        return sum(len(s.tool_calls) for s in self.steps)

    @property
    def error_count(self) -> int:
        """工具调用报错/失败次数"""
        count = 0
        for step in self.steps:
            for tc in step.tool_calls:
                if tc.is_error:
                    count += 1
        return count

    @property
    def total_input_tokens(self) -> int:
        return sum(s.input_tokens for s in self.steps)

    @property
    def total_output_tokens(self) -> int:
        return sum(s.output_tokens for s in self.steps)

    @property
    def total_tokens(self) -> int:
        return self.total_input_tokens + self.total_output_tokens

    @property
    def tool_call_sequence(self) -> list[str]:
        """按顺序提取所有工具调用名称（用于决策熵计算）"""
        seq = []
        for step in self.steps:
            for tc in step.tool_calls:
                seq.append(tc.tool_name)
        return seq

    @property
    def unique_tools_used(self) -> set[str]:
        return set(self.tool_call_sequence)


def parse_session_history(jsonl_path: Path) -> SessionTrace:
    """
    解析一个 session 的 JSONL 历史文件。

    JSONL 格式（每行一个 JSON 对象）：
    - type=user: 用户消息
    - type=assistant: agent 响应（可能含 thinking、text、tool_use）
    - type=tool_result: 工具执行结果
    - type=file-history-snapshot: 文件快照（忽略）
    - type=last-prompt: 会话结束标记（忽略）
    """
    if not jsonl_path.exists():
        return SessionTrace(session_id="")

    session_id = jsonl_path.stem
    trace = SessionTrace(session_id=session_id)
    step_idx = 0

    lines = jsonl_path.read_text(encoding="utf-8").splitlines()

    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue

        record_type = record.get("type", "")

        if record_type == "user":
            step = DecisionStep(step_index=step_idx, role="user")
            msg = record.get("message", {})
            content = msg.get("content", "")
            if isinstance(content, str):
                step.text_output = content
            elif isinstance(content, list):
                step.text_output = _extract_text_from_content_blocks(content)
            trace.steps.append(step)
            step_idx += 1

        elif record_type == "assistant":
            step = DecisionStep(step_index=step_idx, role="assistant")
            msg = record.get("message", {})
            content_blocks = msg.get("content", [])

            if isinstance(content_blocks, list):
                for block in content_blocks:
                    block_type = block.get("type", "")
                    if block_type == "thinking":
                        step.thinking += block.get("thinking", "") + "\n"
                    elif block_type == "text":
                        step.text_output += block.get("text", "") + "\n"
                    elif block_type == "tool_use":
                        tc = ToolCall(
                            tool_name=block.get("name", ""),
                            tool_input=json.dumps(
                                block.get("input", {}), ensure_ascii=False
                            )[:500],
                        )
                        step.tool_calls.append(tc)

            # 提取 usage
            usage = msg.get("usage", {})
            step.input_tokens = usage.get("input_tokens", 0)
            step.output_tokens = usage.get("output_tokens", 0)
            step.cache_read_tokens = usage.get("cache_read_input_tokens", 0)
            # cache_creation 可能在不同位置
            step.cache_creation_tokens = usage.get(
                "cache_creation_input_tokens",
                usage.get("cache_creation", {}).get("ephemeral_5m_input_tokens", 0)
            )

            trace.steps.append(step)
            step_idx += 1

        elif record_type == "tool_result":
            # 工具返回结果，关联到上一个 assistant step 的最后一个 tool_call
            msg = record.get("message", {})
            content = msg.get("content", "")
            is_error = msg.get("is_error", False) or record.get("is_error", False)

            # 向前找到最后一个有 tool_calls 的 assistant step
            for prev_step in reversed(trace.steps):
                if prev_step.role == "assistant" and prev_step.tool_calls:
                    # 找到第一个还没有 result 的 tool_call
                    for tc in prev_step.tool_calls:
                        if not tc.tool_result:
                            tc.tool_result = content[:500] if isinstance(content, str) else str(content)[:500]
                            tc.is_error = is_error
                            break
                    break

    return trace


def find_session_history(
    session_id: str,
    history_base_dir: Path,
) -> Optional[Path]:
    """
    根据 session_id 在历史目录中查找对应的 JSONL 文件。

    历史目录结构: history/{cwd-path-encoded}/{session_id}.jsonl
    """
    if not history_base_dir.exists():
        return None

    # 搜索所有子目录
    for jsonl_file in history_base_dir.rglob(f"{session_id}.jsonl"):
        return jsonl_file

    return None


def _extract_text_from_content_blocks(blocks: list) -> str:
    """从 content blocks 列表中提取纯文本"""
    parts = []
    for block in blocks:
        if isinstance(block, str):
            parts.append(block)
        elif isinstance(block, dict):
            if block.get("type") == "text":
                parts.append(block.get("text", ""))
    return "\n".join(parts)
