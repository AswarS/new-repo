"""Agent Backend 客户端 — 封装对 claude-code-backend 的 HTTP 调用"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Optional

import httpx

from config import AGENT_BASE_URL, AGENT_AUTH_TOKEN, REQUEST_TIMEOUT


def _headers() -> dict[str, str]:
    """构建请求头"""
    h = {"Content-Type": "application/json"}
    if AGENT_AUTH_TOKEN:
        h["Authorization"] = f"Bearer {AGENT_AUTH_TOKEN}"
    return h


async def agent_one_shot(prompt: str, timeout: int = REQUEST_TIMEOUT) -> dict:
    """
    One-shot 调用 agent（适合评判等单轮任务）。

    POST /api/agent
    返回: {"response": str, "latency_ms": float, "error": str}
    """
    start = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                f"{AGENT_BASE_URL}/api/agent",
                headers=_headers(),
                json={"prompt": prompt},
            )
            elapsed = (time.perf_counter() - start) * 1000
            resp.raise_for_status()
            data = resp.json()
            # agent 返回格式可能是 {"result": "..."} 或直接文本
            response_text = _extract_response_text(data)
            return {
                "response": response_text,
                "latency_ms": elapsed,
                "error": "",
                "raw_data": data,
            }
    except Exception as e:
        elapsed = (time.perf_counter() - start) * 1000
        return {
            "response": "",
            "latency_ms": elapsed,
            "error": str(e),
            "raw_data": {},
        }


async def agent_session_call(
    system_context: str,
    user_message: str,
    cwd: Optional[str] = None,
    timeout: int = REQUEST_TIMEOUT,
) -> dict:
    """
    Multi-turn session 调用（创建 session → 发送 system context → 发送用户消息）。

    适合需要注入 skill 上下文的任务执行。

    返回: {"response": str, "latency_ms": float, "error": str, "session_id": str}
    """
    start = time.perf_counter()
    session_id = ""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            # 1. 创建 session
            create_payload = {}
            if cwd:
                create_payload["cwd"] = cwd
            create_resp = await client.post(
                f"{AGENT_BASE_URL}/api/sessions",
                headers=_headers(),
                json=create_payload,
            )
            create_resp.raise_for_status()
            session_data = create_resp.json()
            session_id = session_data.get("session_id", "")

            if not session_id:
                raise ValueError(f"Failed to create session: {session_data}")

            # 2. 发送 system context（作为第一条消息注入背景）
            if system_context:
                ctx_resp = await client.post(
                    f"{AGENT_BASE_URL}/api/sessions/{session_id}/message",
                    headers=_headers(),
                    json={"content": system_context},
                )
                ctx_resp.raise_for_status()

            # 3. 发送用户消息
            msg_resp = await client.post(
                f"{AGENT_BASE_URL}/api/sessions/{session_id}/message",
                headers=_headers(),
                json={"content": user_message},
            )
            msg_resp.raise_for_status()
            msg_data = msg_resp.json()

            elapsed = (time.perf_counter() - start) * 1000
            response_text = _extract_response_text(msg_data)

            return {
                "response": response_text,
                "latency_ms": elapsed,
                "error": "",
                "session_id": session_id,
                "raw_data": msg_data,
            }
    except Exception as e:
        elapsed = (time.perf_counter() - start) * 1000
        return {
            "response": "",
            "latency_ms": elapsed,
            "error": str(e),
            "session_id": session_id,
            "raw_data": {},
        }


async def agent_streaming_call(prompt: str, timeout: int = REQUEST_TIMEOUT) -> dict:
    """
    Streaming 调用（收集所有 chunk 拼接为完整响应）。

    POST /api/agent/stream
    适合需要实时监测输出的场景。
    """
    start = time.perf_counter()
    chunks = []
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream(
                "POST",
                f"{AGENT_BASE_URL}/api/agent/stream",
                headers=_headers(),
                json={"prompt": prompt},
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line.strip():
                        chunks.append(line)

        elapsed = (time.perf_counter() - start) * 1000
        full_response = "\n".join(chunks)
        return {
            "response": full_response,
            "latency_ms": elapsed,
            "error": "",
        }
    except Exception as e:
        elapsed = (time.perf_counter() - start) * 1000
        return {
            "response": "\n".join(chunks),
            "latency_ms": elapsed,
            "error": str(e),
        }


def _extract_response_text(data) -> str:
    """从 agent 返回数据中提取文本响应"""
    if isinstance(data, str):
        return data
    if isinstance(data, dict):
        # 常见字段名
        for key in ("result", "response", "content", "message", "output", "text"):
            if key in data:
                val = data[key]
                if isinstance(val, str):
                    return val
                if isinstance(val, list):
                    # 可能是消息列表
                    return "\n".join(
                        item.get("content", item.get("text", str(item)))
                        for item in val
                        if isinstance(item, dict)
                    )
        # 如果有 messages 数组，取最后一条 assistant 消息
        if "messages" in data:
            msgs = data["messages"]
            for msg in reversed(msgs):
                if isinstance(msg, dict) and msg.get("role") == "assistant":
                    return msg.get("content", "")
        return json.dumps(data, ensure_ascii=False)
    if isinstance(data, list):
        return "\n".join(str(item) for item in data)
    return str(data)
