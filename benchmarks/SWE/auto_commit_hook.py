#!/usr/bin/env python3
"""PostToolUse hook for Claude Code: auto-commits after file modifications.

This script is called by Claude Code's hook system after each tool use.
It reads the tool event from stdin and commits if the tool modified files.

Usage in .claude/settings.local.json:
{
  "hooks": {
    "PostToolUse": [{
      "matcher": "Edit|Write|Bash",
      "hooks": [{"type": "command", "command": "python /path/to/auto_commit_hook.py"}]
    }]
  }
}
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

# Tools that modify files and should trigger a commit
COMMIT_TOOLS = {"Edit", "Write", "NotebookEdit"}

# Bash commands that likely modify files (heuristic)
BASH_MODIFY_PATTERNS = [
    "sed ", "awk ", "mv ", "cp ", "rm ", "mkdir ",
    "touch ", "chmod ", "cat >", "cat >>", "echo >", "echo >>",
    "tee ", "patch ", "git apply", "pip install", "npm install",
]


def get_step_counter_path() -> Path:
    """Get path to the step counter file."""
    counter_dir = os.environ.get("SWE_RUNNER_WORKDIR", os.getcwd())
    return Path(counter_dir) / ".swe-runner-step"


def increment_step() -> int:
    """Increment and return the current step number."""
    counter_path = get_step_counter_path()
    step = 1
    if counter_path.exists():
        try:
            step = int(counter_path.read_text().strip()) + 1
        except (ValueError, OSError):
            step = 1
    counter_path.write_text(str(step))
    return step


def has_changes(cwd: str) -> bool:
    """Check if there are uncommitted changes in the repo."""
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True, text=True, cwd=cwd
    )
    return bool(result.stdout.strip())


def git_commit(message: str, cwd: str) -> Optional[str]:
    """Stage all changes and commit. Returns commit hash or None."""
    subprocess.run(
        ["git", "add", "-A"],
        capture_output=True, text=True, cwd=cwd
    )
    result = subprocess.run(
        ["git", "commit", "-m", message, "--no-verify"],
        capture_output=True, text=True, cwd=cwd
    )
    if result.returncode == 0:
        # Extract commit hash
        hash_result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, cwd=cwd
        )
        return hash_result.stdout.strip()
    return None


def should_commit_bash(command: str) -> bool:
    """Heuristic: does this bash command likely modify files?"""
    cmd_lower = command.lower()
    return any(pat in cmd_lower for pat in BASH_MODIFY_PATTERNS)


def main():
    # Read hook event from stdin
    try:
        event_data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        # No valid input, skip
        sys.exit(0)

    tool_name = event_data.get("tool_name", "") or event_data.get("tool", {}).get("name", "")
    tool_input = event_data.get("tool_input", {}) or event_data.get("input", {})

    # Determine working directory
    cwd = os.environ.get("SWE_RUNNER_REPO_PATH", os.getcwd())

    # Decide whether to commit
    should_commit = False
    file_path = ""

    if tool_name in COMMIT_TOOLS:
        should_commit = True
        file_path = tool_input.get("file_path", "") or tool_input.get("path", "")
    elif tool_name == "Bash":
        command = tool_input.get("command", "")
        if should_commit_bash(command):
            should_commit = True
            file_path = f"bash: {command[:50]}"

    if not should_commit:
        sys.exit(0)

    # Check if there are actual changes
    if not has_changes(cwd):
        sys.exit(0)

    # Commit
    step = increment_step()
    short_path = Path(file_path).name if file_path and not file_path.startswith("bash:") else file_path
    message = f"swe-step-{step:03d}: {tool_name} {short_path}".strip()

    commit_hash = git_commit(message, cwd)
    if commit_hash:
        # Write step info to log file for trajectory collection
        log_path = Path(cwd) / ".swe-runner-log.jsonl"
        log_entry = {
            "step": step,
            "tool": tool_name,
            "file": file_path,
            "commit": commit_hash,
        }
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")


if __name__ == "__main__":
    main()
