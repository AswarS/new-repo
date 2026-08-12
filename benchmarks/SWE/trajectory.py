#!/usr/bin/env python3
"""Trajectory collection: build a step-by-step trace from agent messages.

Each step = one tool_use call + its tool_result, forming a replayable trajectory tree.
Fork from any step by restoring git state + replaying messages up to that point.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional


@dataclass
class Step:
    """A single tool invocation step in the trajectory."""
    step: int                       # 1-indexed step number
    tool_name: str                  # e.g. "Edit", "Bash", "Read", "Grep"
    tool_input: dict                # tool_use input parameters
    tool_result: str                # tool_result content (may be truncated)
    tool_use_id: str = ""           # tool_use_id for correlation
    assistant_message: dict = field(default_factory=dict)  # full assistant msg with this tool_use
    user_message: dict = field(default_factory=dict)       # full user msg with tool_result
    commit_hash: str = ""           # git commit at this step (if hook produced one)
    diff: str = ""                  # diff for this step (if any)


@dataclass
class Trajectory:
    instance_id: str
    branch: str
    task: str
    steps: list[Step] = field(default_factory=list)
    messages: list[dict] = field(default_factory=list)  # filtered history-style messages
    total_steps: int = 0
    final_diff: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


# ── Git Helpers ───────────────────────────────────────────────────────────────


def run_git(args: list[str], cwd: str) -> str:
    """Run a git command and return stdout."""
    result = subprocess.run(
        ["git"] + args,
        capture_output=True, text=True, cwd=cwd,
        encoding="utf-8", errors="replace"
    )
    return result.stdout.strip()


# ── Message Filtering ─────────────────────────────────────────────────────────


def filter_messages_to_history(messages: list) -> list:
    """Filter raw SDK messages to history-like turn records.

    Keeps only high-level turn messages (assistant with tool_use/text/thinking,
    user with tool_result, and result), discarding low-level stream_event noise.

    Handles both formats:
      - Blocking API: {"type": "assistant", "message": {"role": "assistant", "content": [...]}}
      - SSE stream:   {"type": "assistant", "message": {"type": "assistant", "message": {"role": "assistant", "content": [...]}}}
    """
    history = []
    for m in messages:
        mtype = m.get("type", "")
        if mtype == "assistant":
            msg = m.get("message", {})
            # Check if this is SSE nested format (msg has "type" + inner "message")
            if "message" in msg and isinstance(msg.get("message"), dict):
                inner = msg["message"]
                inner_type = msg.get("type", "")
                if inner_type in ("assistant", "user") and inner.get("role") in ("assistant", "user"):
                    history.append(inner)
                elif inner_type == "result":
                    history.append(msg)
            # Blocking API format (msg has "role" directly)
            elif msg.get("role") in ("assistant", "user"):
                history.append(msg)
        elif mtype == "user":
            msg = m.get("message", {})
            if msg.get("role") == "user":
                history.append(msg)
        elif mtype == "result":
            history.append(m)
    return history


# ── Step Building ─────────────────────────────────────────────────────────────


def build_steps_from_messages(filtered_messages: list) -> list[Step]:
    """Build step list from filtered messages. Each tool_use = 1 step.

    Walks through messages pairing assistant tool_use blocks with their
    corresponding user tool_result blocks.
    """
    steps: list[Step] = []
    step_counter = 0

    # Build a map of tool_use_id -> tool_result
    tool_results: dict[str, str] = {}
    tool_result_messages: dict[str, dict] = {}
    for m in filtered_messages:
        if m.get("role") == "user":
            content = m.get("content", [])
            if isinstance(content, list):
                for block in content:
                    if block.get("type") == "tool_result":
                        tuid = block.get("tool_use_id", "")
                        result_content = block.get("content", "")
                        if isinstance(result_content, list):
                            # Extract text from content blocks
                            parts = []
                            for part in result_content:
                                if isinstance(part, dict) and part.get("type") == "text":
                                    parts.append(part.get("text", ""))
                                elif isinstance(part, str):
                                    parts.append(part)
                            result_content = "\n".join(parts)
                        tool_results[tuid] = str(result_content)
                        tool_result_messages[tuid] = m

    # Walk assistant messages, extract tool_use blocks
    for m in filtered_messages:
        if m.get("role") != "assistant":
            continue
        content = m.get("content", [])
        if not isinstance(content, list):
            continue
        for block in content:
            if block.get("type") != "tool_use":
                continue
            step_counter += 1
            tuid = block.get("id", "")
            tool_name = block.get("name", "")
            tool_input = block.get("input", {})
            tool_result = tool_results.get(tuid, "")
            user_msg = tool_result_messages.get(tuid, {})

            steps.append(Step(
                step=step_counter,
                tool_name=tool_name,
                tool_input=tool_input,
                tool_result=tool_result,
                tool_use_id=tuid,
                assistant_message=m,
                user_message=user_msg,
            ))

    return steps


def get_messages_up_to_step(steps: list[Step], step_num: int) -> list[dict]:
    """Reconstruct the message history up to (and including) step N.

    Returns a list of messages in conversation order that can be used
    as context when forking from this step.
    """
    seen_messages = []
    seen_ids = set()

    for s in steps[:step_num]:
        # Add assistant message (if not already added — multiple tool_use
        # in one assistant message share the same msg)
        a_id = id(s.assistant_message)  # use object identity
        if a_id not in seen_ids and s.assistant_message:
            seen_ids.add(a_id)
            seen_messages.append(s.assistant_message)

        # Add user message (tool_result)
        u_id = id(s.user_message)
        if u_id not in seen_ids and s.user_message:
            seen_ids.add(u_id)
            seen_messages.append(s.user_message)

    return seen_messages


# ── Trajectory Building ───────────────────────────────────────────────────────


def build_trajectory(
    repo_path: str,
    branch: str,
    base_ref: str,
    instance_id: str,
    task: str,
    messages: Optional[list] = None,
) -> Trajectory:
    """Build a complete trajectory from agent messages."""
    # Filter to history-style messages
    filtered = filter_messages_to_history(messages or [])

    # Build steps from tool_use calls
    steps = build_steps_from_messages(filtered)

    # Get final cumulative diff
    final_diff = run_git(["diff", f"{base_ref}..{branch}"], cwd=repo_path)

    traj = Trajectory(
        instance_id=instance_id,
        branch=branch,
        task=task,
        steps=steps,
        messages=filtered,
        total_steps=len(steps),
        final_diff=final_diff,
    )
    return traj


def save_trajectory(traj: Trajectory, output_path: Path):
    """Save trajectory to JSON file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(traj.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
