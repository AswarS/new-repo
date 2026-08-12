#!/usr/bin/env python3
"""PreToolUse hook: restricts file/command access to the repo directory.

Blocks tool calls that attempt to read, write, or execute commands
referencing paths outside the allowed repo directory.

The repo path is read from the SWE_SANDBOX_DIR environment variable.

Output format (JSON to stdout):
  - permissionDecision: "allow" | "deny"
  - permissionDecisionReason: explanation string (shown to model when denied)
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path


def get_sandbox_dir() -> Path | None:
    """Get the sandbox directory from environment."""
    sandbox = os.environ.get("SWE_SANDBOX_DIR", "")
    if sandbox:
        return Path(sandbox).resolve()
    return None


def get_allowed_paths() -> list[Path]:
    """Get additional allowed paths from environment (colon-separated)."""
    raw = os.environ.get("SWE_SANDBOX_ALLOW", "")
    if not raw:
        return []
    return [Path(p).resolve() for p in raw.split(":") if p.strip()]


def is_within_sandbox(path_str: str, sandbox: Path, extra_allowed: list[Path] | None = None) -> bool:
    """Check if a path is within the sandbox directory or extra allowed paths."""
    if not path_str or not path_str.strip():
        return True  # Empty path — let the tool handle it

    try:
        # Resolve relative paths against sandbox
        p = Path(path_str)
        if not p.is_absolute():
            p = sandbox / p
        resolved = p.resolve()
        # Check sandbox
        if str(resolved).startswith(str(sandbox)):
            return True
        # Check extra allowed paths
        if extra_allowed:
            for allowed in extra_allowed:
                if str(resolved).startswith(str(allowed)):
                    return True
        return False
    except (OSError, ValueError):
        return True  # Can't resolve — let it through, tool will error


def check_bash_command(command: str, sandbox: Path, extra_allowed: list[Path]) -> str | None:
    """Check a bash command for sandbox violations.

    Returns a reason string if blocked, None if allowed.
    """
    if not command:
        return None

    # Patterns that change directory outside sandbox
    # Match: cd /some/path, cd ~/something, cd ../ (going above sandbox)
    cd_patterns = re.findall(r'\bcd\s+([^\s;&|]+)', command)
    for cd_target in cd_patterns:
        cd_target = cd_target.strip("'\"")
        if not cd_target:
            continue
        # Skip relative paths that stay inside (simple heuristic)
        if cd_target in (".", "./"):
            continue
        if not is_within_sandbox(cd_target, sandbox, extra_allowed):
            return f"Command contains 'cd {cd_target}' which is outside the allowed directory: {sandbox}"

    # Check for absolute paths in the command that are outside sandbox
    # Match absolute paths like /home/user/other-project/file.py
    abs_paths = re.findall(r'(?<![a-zA-Z0-9_=])(/[a-zA-Z0-9_./-]{3,})', command)
    for abs_path in abs_paths:
        # Skip common system paths that are typically read-only / harmless
        safe_prefixes = (
            "/dev/", "/proc/", "/sys/", "/tmp/", "/usr/", "/bin/",
            "/sbin/", "/lib/", "/etc/", "/opt/", "/var/",
            str(sandbox),
        )
        if any(abs_path.startswith(sp) for sp in safe_prefixes):
            continue
        # Check against sandbox + extra allowed
        if not is_within_sandbox(abs_path, sandbox, extra_allowed):
            return (
                f"Command references path '{abs_path}' which is outside the allowed directory. "
                f"You must work within: {sandbox}"
            )

    # Check for explicit writes to paths via redirection
    redirect_targets = re.findall(r'[12]?>+\s*([^\s;&|]+)', command)
    for target in redirect_targets:
        target = target.strip("'\"")
        if target and not is_within_sandbox(target, sandbox, extra_allowed):
            return f"Redirect target '{target}' is outside the allowed directory: {sandbox}"

    return None


def check_file_path(file_path: str, sandbox: Path, tool_name: str, extra_allowed: list[Path]) -> str | None:
    """Check if a file_path parameter is within sandbox.

    Returns a reason string if blocked, None if allowed.
    """
    if not file_path:
        return None
    if not is_within_sandbox(file_path, sandbox, extra_allowed):
        return (
            f"{tool_name} target '{file_path}' is outside the allowed directory. "
            f"You must work within: {sandbox}"
        )
    return None


def main():
    sandbox = get_sandbox_dir()
    if sandbox is None:
        # No sandbox configured — allow everything
        print(json.dumps({"permissionDecision": "allow"}))
        return

    extra_allowed = get_allowed_paths()

    # Read hook event from stdin
    try:
        event_data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        print(json.dumps({"permissionDecision": "allow"}))
        return

    tool_name = event_data.get("tool_name", "")
    tool_input = event_data.get("tool_input", {})
    if not isinstance(tool_input, dict):
        tool_input = {}

    reason = None

    if tool_name == "Bash":
        command = tool_input.get("command", "")
        reason = check_bash_command(command, sandbox, extra_allowed)

    elif tool_name in ("Edit", "Write", "Read", "NotebookEdit"):
        file_path = tool_input.get("file_path", "")
        reason = check_file_path(file_path, sandbox, tool_name, extra_allowed)

    elif tool_name in ("Glob", "Grep"):
        search_path = tool_input.get("path", "")
        if search_path:
            reason = check_file_path(search_path, sandbox, tool_name, extra_allowed)

    if reason:
        output = {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": (
                f"[SANDBOX VIOLATION] {reason}\n"
                f"All file operations must stay within the repository directory."
            ),
        }
    else:
        output = {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
        }

    print(json.dumps(output))


if __name__ == "__main__":
    main()
