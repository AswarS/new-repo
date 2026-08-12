#!/usr/bin/env python3
"""Run SWE tasks locally using Claude Code CLI with git trajectory tracking.

Reads instances from a SWE-bench JSONL file, auto-locates the corresponding
repo under a repos/ directory, and drives Claude Code to solve each task.
Every code modification is automatically committed for trajectory fork trees.

Usage:
    # Run all instances from JSONL
    python run_swe.py run -d swe-bench-lite_test.jsonl --repos-dir ./repos

    # Run a specific instance
    python run_swe.py run -d swe-bench-lite_test.jsonl --repos-dir ./repos -i django__django-12345

    # Fork from step 3, create 5 branches
    python run_swe.py fork -t output/django__django-12345.trajectory.json --fork-at 3 --forks 5
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from trajectory import build_trajectory, save_trajectory, get_messages_up_to_step

SCRIPT_DIR = Path(__file__).parent.resolve()
HOOK_SCRIPT = SCRIPT_DIR / "auto_commit_hook.py"
SANDBOX_HOOK_SCRIPT = SCRIPT_DIR / "sandbox_hook.py"
OUTPUT_DIR = SCRIPT_DIR / "output"

# Local Claude Code project directory (run via bun)
# Set CLAUDE_CODE_DIR env var to override, otherwise defaults to swe-runner's parent dir
CLAUDE_PROJECT_DIR = Path(os.environ.get("CLAUDE_CODE_DIR", str(SCRIPT_DIR / ".."))).resolve()
# Default server port
DEFAULT_PORT = 3199

# Conda environment instruction prepended to task prompt
CONDA_INSTRUCTION = """IMPORTANT: A conda environment named `{conda_env}` has been created for this task with Python {python_version}.
Before running ANY Python or pip commands, you MUST first activate it:
conda activate {conda_env}

Do this at the start of every Bash tool call that involves Python.

"""

# Patch output instruction appended to every task prompt
PATCH_INSTRUCTION = """

IMPORTANT: After you have finished making all code changes to fix the issue, you MUST run the following command as your final step to save the patch:
git diff {base_commit} > {patch_path}
Do not skip this step.
"""

# Skill usage instruction prepended to task prompt when skills are available
SKILL_INSTRUCTION = """You have the following skills available via the Skill tool: {skills}

IMPORTANT: You MUST use the Skill tool to invoke a relevant skill BEFORE you start working on the task. Skills contain specialized strategies and domain knowledge that significantly improve your success rate.Skipping skills leads to worse outcomes. Call the Skill tool first, then follow its guidance.

Here is the task:
"""


# ── JSONL & Repo Discovery ──────────────────────────────────────────────────


def load_instances(jsonl_path: Path) -> list[dict]:
    """Load instances from a SWE-bench JSONL file."""
    instances = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                instances.append(json.loads(line))
    return instances


def instance_to_repo_dir_name(instance: dict) -> str:
    """Derive the repo directory name from an instance.

    SWE-bench instance_id format: "astropy__astropy-12907"
    repo field format: "astropy/astropy"

    The repo directory under repos/ is expected to be named as:
      - "astropy__astropy" (double-underscore joined owner__name), OR
      - "astropy/astropy" (nested owner/name)

    We try both conventions.
    """
    # Primary: derive from instance_id (strip the issue number)
    # e.g. "django__django-12345" -> "django__django"
    instance_id = instance["instance_id"]
    # Split on last hyphen followed by digits
    parts = instance_id.rsplit("-", 1)
    if len(parts) == 2 and parts[1].isdigit():
        return parts[0]
    return instance_id


def find_repo_path(repos_dir: Path, instance: dict) -> Path | None:
    """Find the local repo path for an instance under repos_dir.

    Tries multiple naming conventions:
      1. repos/<owner>__<name>        (e.g. repos/django__django)
      2. repos/<owner>/<name>         (e.g. repos/django/django)
      3. repos/<owner>-<name>         (e.g. repos/django-django)
    """
    # From instance_id
    dir_name = instance_to_repo_dir_name(instance)
    candidate = repos_dir / dir_name
    if candidate.exists():
        return candidate

    # From repo field (e.g. "astropy/astropy")
    repo_field = instance.get("repo", "")
    if "/" in repo_field:
        # Try nested: repos/astropy/astropy
        nested = repos_dir / repo_field
        if nested.exists():
            return nested
        # Try flattened with double underscore: repos/astropy__astropy
        flat = repos_dir / repo_field.replace("/", "__")
        if flat.exists():
            return flat
        # Try flattened with single dash
        dashed = repos_dir / repo_field.replace("/", "-")
        if dashed.exists():
            return dashed

    return None


# ── Git Setup ────────────────────────────────────────────────────────────────


def checkout_base_commit(repo_path: str, base_commit: str):
    """Reset repo to the base commit for this instance."""
    # Clean any leftover state
    subprocess.run(
        ["git", "checkout", "--", "."],
        capture_output=True, text=True, cwd=repo_path
    )
    subprocess.run(
        ["git", "clean", "-fd"],
        capture_output=True, text=True, cwd=repo_path
    )
    # Checkout the base commit
    result = subprocess.run(
        ["git", "checkout", base_commit],
        capture_output=True, text=True, cwd=repo_path
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Failed to checkout {base_commit}: {result.stderr.strip()}"
        )


def setup_branch(repo_path: str, branch_prefix: str, instance_id: str) -> tuple:
    """Create a new branch for this run. Returns (branch_name, base_ref)."""
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        capture_output=True, text=True, cwd=repo_path
    )
    base_ref = result.stdout.strip()

    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    branch_name = f"{branch_prefix}/{instance_id}-{timestamp}"

    subprocess.run(
        ["git", "checkout", "-b", branch_name],
        capture_output=True, text=True, cwd=repo_path, check=True
    )
    print(f"  Branch: {branch_name}")
    print(f"  Base: {base_ref[:8]}")
    return branch_name, base_ref


# ── Hook Setup ───────────────────────────────────────────────────────────────


def setup_hook(repo_path: str, output_dir: Path | None = None) -> Path:
    """Write .claude/settings.local.json with PostToolUse and PreToolUse hooks."""
    claude_dir = Path(repo_path) / ".claude"
    claude_dir.mkdir(exist_ok=True)

    settings_path = claude_dir / "settings.local.json"
    hook_path = str(HOOK_SCRIPT).replace("\\", "/")
    sandbox_hook_path = str(SANDBOX_HOOK_SCRIPT).replace("\\", "/")
    python_exe = sys.executable.replace("\\", "/")

    # Set SWE_SANDBOX_DIR so the sandbox hook knows the allowed directory
    # Set SWE_SANDBOX_ALLOW for additional allowed paths (e.g. output dir)
    sandbox_env = f"SWE_SANDBOX_DIR={repo_path}"
    if output_dir:
        sandbox_env += f" SWE_SANDBOX_ALLOW={str(output_dir.resolve())}"

    settings = {
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "Bash|Edit|Write|Read|Glob|Grep|NotebookEdit",
                    "hooks": [
                        {
                            "type": "command",
                            "command": f"{sandbox_env} {python_exe} {sandbox_hook_path}"
                        }
                    ]
                }
            ],
            "PostToolUse": [
                {
                    "matcher": "Edit|Write|NotebookEdit",
                    "hooks": [
                        {
                            "type": "command",
                            "command": f"{python_exe} {hook_path}"
                        }
                    ]
                }
            ]
        }
    }

    settings_path.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    return settings_path


def setup_gitignore_for_runner(repo_path: str):
    """Ensure .swe-runner-* files are in .gitignore."""
    gitignore_path = Path(repo_path) / ".gitignore"
    marker = ".swe-runner-"

    if gitignore_path.exists():
        content = gitignore_path.read_text(encoding="utf-8")
        if marker in content:
            return
        content = content.rstrip() + "\n"
    else:
        content = ""

    content += f"\n# SWE Runner temp files\n{marker}*\n.claude/settings.local.json\n"
    gitignore_path.write_text(content, encoding="utf-8")


# ── Conda Environment Management ───────────────────────────────────────────


def create_conda_env(env_name: str, python_version: str, repo_path: str) -> bool:
    """Create a conda environment and install repo dependencies.

    Returns True if the environment was created successfully.
    """
    print(f"  Conda: creating env '{env_name}' (python={python_version})...")

    # Create environment
    result = subprocess.run(
        ["conda", "create", "-n", env_name, f"python={python_version}", "-y", "--quiet"],
        capture_output=True, text=True, timeout=300
    )
    if result.returncode != 0:
        print(f"  [WARN] conda create failed: {result.stderr.strip()[:200]}")
        return False

    # Install repo dependencies if possible
    repo = Path(repo_path)
    installed = False

    # Try setup.py / pyproject.toml editable install
    if (repo / "setup.py").exists() or (repo / "pyproject.toml").exists():
        print(f"  Conda: installing repo in editable mode...")
        res = subprocess.run(
            ["conda", "run", "-n", env_name,
             "pip", "install", "-e", ".", "--quiet", "--no-build-isolation"],
            capture_output=True, text=True, cwd=repo_path, timeout=600
        )
        if res.returncode == 0:
            installed = True
        else:
            # Fallback: try without --no-build-isolation
            res = subprocess.run(
                ["conda", "run", "-n", env_name,
                 "pip", "install", "-e", ".", "--quiet"],
                capture_output=True, text=True, cwd=repo_path, timeout=600
            )
            if res.returncode == 0:
                installed = True
            else:
                print(f"  [WARN] pip install -e . failed: {res.stderr.strip()[:200]}")

    # Try requirements.txt if editable install didn't work
    if not installed and (repo / "requirements.txt").exists():
        print(f"  Conda: installing requirements.txt...")
        subprocess.run(
            ["conda", "run", "-n", env_name,
             "pip", "install", "-r", "requirements.txt", "--quiet"],
            capture_output=True, text=True, cwd=repo_path, timeout=600
        )

    # Also try requirements-dev.txt or test requirements
    for req_file in ["requirements-dev.txt", "requirements_dev.txt",
                     "test-requirements.txt", "test_requirements.txt"]:
        if (repo / req_file).exists():
            subprocess.run(
                ["conda", "run", "-n", env_name,
                 "pip", "install", "-r", req_file, "--quiet"],
                capture_output=True, text=True, cwd=repo_path, timeout=600
            )

    print(f"  Conda: env ready")
    return True


def remove_conda_env(env_name: str):
    """Remove a conda environment."""
    print(f"  Conda: removing env '{env_name}'...")
    subprocess.run(
        ["conda", "env", "remove", "-n", env_name, "-y", "--quiet"],
        capture_output=True, text=True, timeout=120
    )


def get_conda_env_name(instance_id: str) -> str:
    """Generate a conda environment name for an instance."""
    # Keep it short but unique — conda env names have length limits
    return f"swe-{instance_id}"


# ── Claude Code Execution via HTTP API ───────────────────────────────────────


def check_server_health(port: int) -> bool:
    """Check if the API server is running and healthy."""
    import urllib.request
    url = f"http://localhost:{port}/health"
    try:
        resp = urllib.request.urlopen(url, timeout=2)
        return resp.status == 200
    except Exception:
        return False


def check_agent_skills(port: int) -> dict:
    """Query the agent to retrieve available skills and tools.

    Sends a minimal request and reads the system init message to extract
    the skills/tools list. Returns a dict with 'skills' and 'tools' lists.
    """
    import urllib.request

    url = f"http://localhost:{port}/api/agent/stream"
    payload = json.dumps({"prompt": "hi", "cwd": "/tmp"}).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    info = {"skills": [], "tools": [], "model": ""}
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            for raw_line in resp:
                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line.startswith("data: "):
                    continue
                event = json.loads(line[6:])
                msg = event.get("message", {})
                if msg.get("type") == "system" and msg.get("subtype") == "init":
                    info["skills"] = msg.get("skills", [])
                    info["tools"] = msg.get("tools", [])
                    info["model"] = msg.get("model", "")
                    break
    except Exception:
        pass
    return info


def run_claude_code(
    repo_path: str,
    task: str,
    allowed_tools: str,
    model: str = "",
    max_turns: int = 0,
    quiet: bool = False,
    system_prompt: str = "",
    port: int = DEFAULT_PORT,
) -> list:
    """Run Claude Code via HTTP API with real-time progress display.

    Uses SSE streaming for live output, with a fallback to blocking mode
    if the stream connection fails.
    """
    import urllib.request
    import urllib.error

    url = f"http://localhost:{port}/api/agent/stream"
    request_body = {"prompt": task, "cwd": repo_path}
    if allowed_tools:
        request_body["allowedTools"] = allowed_tools
    payload = json.dumps(request_body).encode("utf-8")

    if not quiet:
        print(f"  API: POST {url}")
        print(f"  CWD: {repo_path}")
        print(f"  Task: {task[:120]}{'...' if len(task) > 120 else ''}")
        print()

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    messages = []
    step_count = 0
    try:
        with urllib.request.urlopen(req, timeout=1800) as resp:
            # Read line-by-line from the SSE stream
            for raw_line in resp:
                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line:
                    continue
                if line.startswith("data: "):
                    data_str = line[6:]
                    try:
                        event = json.loads(data_str)
                        messages.append(event)
                        if not quiet:
                            step_count = _print_progress(event, step_count)
                    except json.JSONDecodeError:
                        pass
    except KeyboardInterrupt:
        print("\n  Interrupted.")
    except Exception as e:
        if messages:
            # Got some data before failure — use what we have
            if not quiet:
                print(f"  [WARN] Stream ended early ({len(messages)} events collected): {e}")
        else:
            # SSE completely failed — fall back to blocking mode
            if not quiet:
                print(f"  [WARN] SSE failed ({e}), falling back to blocking API...")
            messages = _run_blocking_fallback(repo_path, task, allowed_tools, port, quiet)

    return messages


def _run_blocking_fallback(repo_path: str, task: str, allowed_tools: str, port: int, quiet: bool) -> list:
    """Fallback: use blocking /api/agent endpoint."""
    import urllib.request

    url = f"http://localhost:{port}/api/agent"
    request_body = {"prompt": task, "cwd": repo_path}
    if allowed_tools:
        request_body["allowedTools"] = allowed_tools
    payload = json.dumps(request_body).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=1800) as resp:
            data = resp.read()
            result = json.loads(data)
            if "error" in result:
                print(f"  [ERROR] {result['error']}", file=sys.stderr)
            messages = result.get("messages", [])
            if not quiet:
                print(f"  [done] Received {len(messages)} messages (blocking)")
            return messages
    except Exception as e2:
        print(f"  [ERROR] Blocking fallback also failed: {e2}", file=sys.stderr)
        return []


def _print_progress(event: dict, step_count: int) -> int:
    """Print real-time progress for a streaming event."""
    etype = event.get("type", "")

    if etype == "assistant":
        msg = event.get("message", {})
        msg_type = msg.get("type", "")

        # Nested structure: event.message.message.content
        inner = msg.get("message", {})
        content = inner.get("content", msg.get("content", ""))

        if msg_type == "assistant" and isinstance(content, list):
            for block in content:
                if block.get("type") == "tool_use":
                    step_count += 1
                    name = block.get("name", "?")
                    inp = block.get("input", {})
                    if name in ("Edit", "Write", "Read"):
                        detail = inp.get("file_path", "")
                    elif name == "Bash":
                        cmd = inp.get("command", "")
                        detail = cmd[:80] + ("..." if len(cmd) > 80 else "")
                    elif name == "Grep":
                        detail = f'"{inp.get("pattern", "")}"'
                    elif name == "Glob":
                        detail = inp.get("pattern", "")
                    else:
                        detail = str(inp)[:60]
                    print(f"  \033[33m[step {step_count}]\033[0m {name}: {detail}")
                elif block.get("type") == "text":
                    text = block.get("text", "").strip()
                    if text:
                        display = text[:200] + ("..." if len(text) > 200 else "")
                        print(f"  \033[36m[text]\033[0m {display}")

        elif msg_type == "result":
            duration = msg.get("duration_ms", 0)
            subtype = msg.get("subtype", "success")
            print(f"\n  \033[32m[done]\033[0m {subtype} ({duration/1000:.1f}s, {step_count} steps)")

    elif etype == "result":
        pass  # handled above via assistant->result

    elif etype == "error":
        print(f"  \033[31m[error]\033[0m {event.get('error', '?')}")

    sys.stdout.flush()
    return step_count




# ── Cleanup ──────────────────────────────────────────────────────────────────


def cleanup(repo_path: str, settings_path: Path | None):
    """Remove temporary files created during the run."""
    if settings_path and settings_path.exists():
        settings_path.unlink()
    counter_path = Path(repo_path) / ".swe-runner-step"
    if counter_path.exists():
        counter_path.unlink()


# ── Instance Processing ──────────────────────────────────────────────────────


# ── History JSONL Copy ─────────────────────────────────────────────────────────


# Backend history directory (keyed by sanitized cwd)
HISTORY_BASE = CLAUDE_PROJECT_DIR / "history"


def _copy_session_history(session_id: str, instance_id: str, output_dir: Path):
    """Copy the session history JSONL from backend history dir to output."""
    # The history dir is keyed by sanitized cwd path
    # Search all subdirs for matching session_id.jsonl
    jsonl_name = f"{session_id}.jsonl"
    for history_dir in HISTORY_BASE.iterdir():
        if not history_dir.is_dir():
            continue
        src = history_dir / jsonl_name
        if src.exists():
            dst = output_dir / f"{instance_id}.history.jsonl"
            shutil.copy2(src, dst)
            print(f"  History: {dst.name}")
            return
    # Not found — not an error, just skip
    pass


# ── Instance Processing ──────────────────────────────────────────────────────


def process_instance(
    instance: dict,
    repos_dir: Path,
    output_dir: Path,
    args,
) -> dict:
    """Process a single SWE-bench instance."""
    instance_id = instance["instance_id"]
    task = instance["problem_statement"]
    base_commit = instance.get("base_commit", "")

    # Find repo
    repo_path = find_repo_path(repos_dir, instance)
    if repo_path is None:
        dir_name = instance_to_repo_dir_name(instance)
        print(f"  [SKIP] Repo not found: {dir_name}")
        return {"instance_id": instance_id, "status": "repo_not_found"}

    repo_path_str = str(repo_path.resolve())
    print(f"  Repo: {repo_path_str}")

    # Checkout base commit
    if base_commit:
        try:
            checkout_base_commit(repo_path_str, base_commit)
            print(f"  Checked out: {base_commit[:8]}")
        except RuntimeError as e:
            print(f"  [ERROR] {e}")
            return {"instance_id": instance_id, "status": "checkout_failed"}

    # Setup branch
    branch_name, base_ref = setup_branch(
        repo_path_str, args.branch_prefix, instance_id
    )

    # Setup hook & gitignore
    setup_gitignore_for_runner(repo_path_str)
    settings_path = setup_hook(repo_path_str, output_dir)

    # Create conda environment if enabled
    conda_env_name = None
    if not args.no_conda:
        conda_env_name = get_conda_env_name(instance_id)
        if not create_conda_env(conda_env_name, args.python_version, repo_path_str):
            print(f"  [WARN] Conda env creation failed, proceeding without it")
            conda_env_name = None

    # Check server is running
    if not check_server_health(args.port):
        print(f"  [ERROR] API server not running on port {args.port}", file=sys.stderr)
        print(f"  Please start the server first: bun run serve --port {args.port}", file=sys.stderr)
        if conda_env_name:
            remove_conda_env(conda_env_name)
        return {"instance_id": instance_id, "status": "server_not_running"}

    # Append patch output instruction to task
    patch_path = str((output_dir / f"{instance_id}.patch.txt").resolve())
    full_task = task + PATCH_INSTRUCTION.format(
        base_commit=base_commit, patch_path=patch_path
    )

    # Prepend conda activation instruction
    if conda_env_name:
        full_task = CONDA_INSTRUCTION.format(
            conda_env=conda_env_name, python_version=args.python_version
        ) + full_task

    # Prepend skill instruction if skills are available
    skills = getattr(args, "_agent_skills", [])
    if skills:
        full_task = SKILL_INSTRUCTION.format(skills=", ".join(skills)) + full_task

    # Run Claude Code
    t0 = time.time()
    messages = run_claude_code(
        repo_path_str,
        task=full_task,
        allowed_tools=args.allowed_tools,
        model=args.model,
        max_turns=args.max_turns,
        quiet=args.quiet,
        system_prompt=args.system_prompt,
        port=args.port,
    )
    elapsed = time.time() - t0

    # Cleanup hook
    if not args.no_cleanup:
        cleanup(repo_path_str, settings_path)

    # Remove conda environment
    if conda_env_name and not args.no_cleanup:
        remove_conda_env(conda_env_name)

    # Extract session_id for history lookup
    session_id = None
    for m in messages:
        if m.get("type") == "system" and m.get("session_id"):
            session_id = m["session_id"]
            break

    # Collect trajectory
    traj = build_trajectory(
        repo_path=repo_path_str,
        branch=branch_name,
        base_ref=base_ref,
        instance_id=instance_id,
        task=task,
        messages=messages,
    )

    # Save trajectory
    traj_path = output_dir / f"{instance_id}.trajectory.json"
    save_trajectory(traj, traj_path)

    # Copy history JSONL from backend if available
    if session_id:
        _copy_session_history(session_id, instance_id, output_dir)

    # Clean log
    log_path = Path(repo_path_str) / ".swe-runner-log.jsonl"
    if log_path.exists():
        log_path.unlink()

    print(f"  Done: {traj.total_steps} steps, {len(traj.messages)} turns, {elapsed:.1f}s -> {traj_path.name}")
    return {
        "instance_id": instance_id,
        "status": "completed",
        "steps": traj.total_steps,
        "elapsed": elapsed,
        "branch": branch_name,
    }


# ── Fork Logic ────────────────────────────────────────────────────────────────


def set_step_counter(repo_path: str, step: int):
    """Set the step counter file so hook continues numbering from step+1."""
    counter_path = Path(repo_path) / ".swe-runner-step"
    counter_path.write_text(str(step))


def run_fork(args):
    """Fork from a specific step in an existing trajectory.

    Restores both git state AND conversation history up to the fork point,
    then continues the agent from there.
    """
    traj_path = Path(args.trajectory)
    if not traj_path.exists():
        print(f"Error: trajectory file not found: {traj_path}", file=sys.stderr)
        sys.exit(1)

    traj_data = json.loads(traj_path.read_text(encoding="utf-8"))
    instance_id = traj_data["instance_id"]
    task = traj_data["task"]
    steps = traj_data["steps"]
    fork_at = args.fork_at
    num_forks = args.forks

    if fork_at < 1 or fork_at > len(steps):
        print(f"Error: --fork-at must be between 1 and {len(steps)} "
              f"(trajectory has {len(steps)} steps)", file=sys.stderr)
        sys.exit(1)

    # Build conversation history up to fork point using step messages
    history_messages = get_messages_up_to_step(
        [type('S', (), s)() if isinstance(s, dict) else s for s in steps],  # won't work with raw dicts
        fork_at
    )
    # Actually rebuild from the raw step dicts
    history_messages = []
    for s in steps[:fork_at]:
        if isinstance(s, dict):
            if s.get("assistant_message"):
                history_messages.append(s["assistant_message"])
            if s.get("user_message"):
                history_messages.append(s["user_message"])

    # Deduplicate (multiple tool_use in one assistant message)
    deduped = []
    seen = set()
    for m in history_messages:
        m_id = m.get("id", id(m))
        if m_id not in seen:
            seen.add(m_id)
            deduped.append(m)
    history_messages = deduped

    # Format history as context prefix for the prompt
    history_summary = _format_history_for_prompt(history_messages)

    # Get the fork commit (use git state from the step if available, else use branch)
    fork_step = steps[fork_at - 1]
    fork_commit = fork_step.get("commit_hash", "")

    # If no commit_hash in new format, we need to recover git state differently
    # Fall back: just use the current branch state (agent changes are in the worktree)
    if not fork_commit:
        # Use git log to find the state — the branch should still exist
        branch = traj_data.get("branch", "")
        if branch:
            fork_commit = branch
        else:
            print("  [WARN] No commit_hash in steps, using HEAD")
            fork_commit = "HEAD"

    # The user must provide --repos-dir so we can locate the repo
    if not args.repos_dir:
        print("Error: --repos-dir is required for fork command", file=sys.stderr)
        sys.exit(1)

    repos_dir = Path(args.repos_dir).resolve()

    # Derive repo dir from instance_id
    parts = instance_id.rsplit("-", 1)
    repo_dir_name = parts[0] if len(parts) == 2 and parts[1].isdigit() else instance_id

    repo_path = None
    for candidate in [
        repos_dir / repo_dir_name,
        repos_dir / repo_dir_name.replace("__", "/"),
    ]:
        if candidate.exists():
            repo_path = candidate
            break

    if repo_path is None:
        print(f"Error: cannot find repo for '{instance_id}' under {repos_dir}", file=sys.stderr)
        sys.exit(1)

    repo_path_str = str(repo_path.resolve())

    # Each run gets its own output directory
    if args.output:
        output_dir = Path(args.output)
    else:
        run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = OUTPUT_DIR / f"run_{run_timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"{'='*60}")
    print(f"SWE Runner - Fork from Step {fork_at}")
    print(f"{'='*60}")
    print(f"  Instance: {instance_id}")
    print(f"  Repo: {repo_path_str}")
    print(f"  Fork at: step {fork_at}/{len(steps)}")
    print(f"  History context: {len(history_messages)} messages")
    print(f"  Forks: {num_forks}")
    print()

    # Check server is running
    if not check_server_health(args.port):
        print(f"Error: API server not running on port {args.port}", file=sys.stderr)
        print(f"Please start the server first: bun run serve --port {args.port}", file=sys.stderr)
        sys.exit(1)

    results = []
    for fork_idx in range(1, num_forks + 1):
            print(f"\n--- Fork {fork_idx}/{num_forks} ---")

            # 1. Checkout the fork point (restore git state)
            if fork_commit and fork_commit != "HEAD":
                subprocess.run(
                    ["git", "checkout", fork_commit],
                    capture_output=True, text=True, cwd=repo_path_str, check=True
                )

            # 2. Create fork branch
            timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
            branch_name = f"swe-run/{instance_id}-fork{fork_idx}-step{fork_at}-{timestamp}"
            subprocess.run(
                ["git", "checkout", "-b", branch_name],
                capture_output=True, text=True, cwd=repo_path_str, check=True
            )
            print(f"  Branch: {branch_name}")

            # 3. Setup hook & gitignore
            setup_gitignore_for_runner(repo_path_str)
            settings_path = setup_hook(repo_path_str, output_dir)

            # 4. Build prompt with history context + original task + patch instruction
            patch_path = str((output_dir / f"{instance_id}-fork{fork_idx}-step{fork_at}.patch.txt").resolve())
            fork_prompt = _build_fork_prompt(task, history_summary, fork_commit, patch_path)

            # 5. Run Claude Code
            t0 = time.time()
            messages = run_claude_code(
                repo_path_str,
                task=fork_prompt,
                allowed_tools=args.allowed_tools,
                model=args.model,
                max_turns=args.max_turns,
                quiet=args.quiet,
                system_prompt=args.system_prompt,
                port=args.port,
            )
            elapsed = time.time() - t0

            # 6. Cleanup
            if not args.no_cleanup:
                cleanup(repo_path_str, settings_path)

            # 7. Collect trajectory
            fork_id = f"{instance_id}-fork{fork_idx}-step{fork_at}"
            traj = build_trajectory(
                repo_path=repo_path_str,
                branch=branch_name,
                base_ref=fork_commit if fork_commit != "HEAD" else branch_name,
                instance_id=fork_id,
                task=task,
                messages=messages,
            )

            # 8. Save
            traj_out = output_dir / f"{fork_id}.trajectory.json"
            save_trajectory(traj, traj_out)

            # Clean log
            log_path = Path(repo_path_str) / ".swe-runner-log.jsonl"
            if log_path.exists():
                log_path.unlink()

            print(f"  Done: {traj.total_steps} steps, {elapsed:.1f}s -> {traj_out.name}")
            results.append({
                "fork": fork_idx,
                "branch": branch_name,
                "steps": traj.total_steps,
                "elapsed": elapsed,
            })

    # Generate preds.json for fork output
    generate_preds_json(output_dir, model_name=args.model or "mco-4")

    # Summary
    print(f"\n{'='*60}")
    print(f"Fork complete: {len(results)} branches from step {fork_at}")
    for r in results:
        print(f"  Fork {r['fork']}: {r['steps']} steps, {r['elapsed']:.1f}s ({r['branch']})")
    print(f"{'='*60}")


def _format_history_for_prompt(history_messages: list) -> str:
    """Format conversation history messages into a readable text summary."""
    lines = []
    for m in history_messages:
        role = m.get("role", "?")
        content = m.get("content", [])
        if isinstance(content, list):
            for block in content:
                btype = block.get("type", "")
                if btype == "tool_use":
                    name = block.get("name", "?")
                    inp = block.get("input", {})
                    # Summarize input
                    if name in ("Edit", "Write", "Read"):
                        detail = inp.get("file_path", "")
                    elif name == "Bash":
                        detail = inp.get("command", "")[:200]
                    elif name == "Grep":
                        detail = f'pattern="{inp.get("pattern", "")}"'
                    elif name == "Glob":
                        detail = inp.get("pattern", "")
                    else:
                        detail = json.dumps(inp)[:150]
                    lines.append(f"[{role}] tool_use: {name}({detail})")
                elif btype == "tool_result":
                    result_text = block.get("content", "")
                    if isinstance(result_text, str):
                        result_text = result_text[:300]
                    lines.append(f"[{role}] tool_result: {result_text}")
                elif btype == "text":
                    text = block.get("text", "")[:200]
                    lines.append(f"[{role}] {text}")
                elif btype == "thinking":
                    lines.append(f"[{role}] (thinking...)")
        elif isinstance(content, str) and content:
            lines.append(f"[{role}] {content[:200]}")
    return "\n".join(lines)


def _build_fork_prompt(task: str, history_summary: str, base_commit: str, patch_path: str) -> str:
    """Build the prompt for a fork run, including history context."""
    prompt = f"""You are continuing work on a task. Here is what has been done so far:

--- PREVIOUS ACTIONS ---
{history_summary}
--- END PREVIOUS ACTIONS ---

The original task is:
{task}

Continue from where the previous actions left off. Do NOT repeat work that was already done.
Review the current state of the code and continue fixing the issue.

IMPORTANT: After you have finished making all code changes to fix the issue, you MUST run:
git diff {base_commit} > {patch_path}
"""
    return prompt


# ── Preds JSON Generation ─────────────────────────────────────────────────────


def generate_preds_json(output_dir: Path, model_name: str = "mco-4"):
    """Generate preds.json from patch files and trajectory data.

    For each instance:
      1. If <instance_id>.patch.txt exists, use its content as model_patch
      2. Otherwise, fall back to final_diff from <instance_id>.trajectory.json
    """
    preds = {}

    # Collect from patch files
    for patch_file in output_dir.glob("*.patch.txt"):
        instance_id = patch_file.stem.replace(".patch", "")
        patch_content = patch_file.read_text(encoding="utf-8", errors="replace")
        preds[instance_id] = {
            "instance_id": instance_id,
            "model_name_or_path": model_name,
            "model_patch": patch_content,
        }

    # Fill in from trajectory files for any that don't have a patch
    for traj_file in output_dir.glob("*.trajectory.json"):
        instance_id = traj_file.stem.replace(".trajectory", "")
        if instance_id in preds:
            continue
        try:
            traj_data = json.loads(traj_file.read_text(encoding="utf-8"))
            final_diff = traj_data.get("final_diff", "")
            if final_diff:
                preds[instance_id] = {
                    "instance_id": instance_id,
                    "model_name_or_path": model_name,
                    "model_patch": final_diff,
                }
        except (json.JSONDecodeError, OSError):
            pass

    if preds:
        preds_path = output_dir / "preds.json"
        preds_path.write_text(
            json.dumps(preds, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        print(f"  preds.json: {len(preds)} entries -> {preds_path}")

    return preds


# ── Main ─────────────────────────────────────────────────────────────────────


def add_common_args(parser):
    """Add arguments shared between run and fork subcommands."""
    parser.add_argument("--output", "-o", default="", help="Output directory for trajectories (default: auto-generated per run)")
    parser.add_argument(
        "--allowed-tools", default="Edit,Write,Read,Bash,Glob,Grep,Skill,NotebookEdit",
        help="Comma-separated list of allowed tools for Claude Code"
    )
    parser.add_argument("--model", "-m", default="", help="Model to use (e.g. sonnet, opus)")
    parser.add_argument("--max-turns", type=int, default=0, help="Max conversation turns (0=unlimited)")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Server port (default: {DEFAULT_PORT})")
    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress real-time agent output")
    parser.add_argument("--no-cleanup", action="store_true", help="Don't remove hook settings after run")
    parser.add_argument("--system-prompt", "-s", default="", help="Additional system prompt")
    parser.add_argument("--no-conda", action="store_true", help="Skip conda environment creation")
    parser.add_argument("--python-version", default="3.9", help="Python version for conda env (default: 3.9)")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run SWE tasks locally with Claude Code + git trajectory tracking"
    )
    subparsers = parser.add_subparsers(dest="command")

    # ── run subcommand ──
    run_parser = subparsers.add_parser("run", help="Run SWE instances from JSONL")
    run_parser.add_argument("--data", "-d", required=True, help="Path to SWE-bench JSONL file")
    run_parser.add_argument("--repos-dir", required=True, help="Directory containing cloned repos")
    run_parser.add_argument("--instance", "-i", default="", help="Run only this instance ID")
    run_parser.add_argument("--num", "-n", type=int, default=0, help="Number of instances (0=all)")
    run_parser.add_argument("--branch-prefix", default="swe-run", help="Branch name prefix")
    add_common_args(run_parser)

    # ── fork subcommand ──
    fork_parser = subparsers.add_parser("fork", help="Fork from a step in an existing trajectory")
    fork_parser.add_argument(
        "--trajectory", "-t", required=True,
        help="Path to existing trajectory JSON file"
    )
    fork_parser.add_argument(
        "--fork-at", "-k", type=int, required=True,
        help="Step number to fork from (1-indexed)"
    )
    fork_parser.add_argument(
        "--forks", "-n", type=int, default=3,
        help="Number of fork branches to create (default: 3)"
    )
    fork_parser.add_argument("--repos-dir", default="", help="Directory containing cloned repos")
    add_common_args(fork_parser)

    args = parser.parse_args()

    # Default to 'run' if no subcommand (backward compat)
    if args.command is None:
        parser.print_help()
        sys.exit(1)

    return args


def main():
    args = parse_args()

    if args.command == "fork":
        run_fork(args)
        return

    # ── run command ──
    data_path = Path(args.data)
    if not data_path.exists():
        print(f"Error: JSONL file not found: {data_path}", file=sys.stderr)
        sys.exit(1)

    repos_dir = Path(args.repos_dir).resolve()
    if not repos_dir.exists():
        print(f"Error: repos directory not found: {repos_dir}", file=sys.stderr)
        sys.exit(1)

    if shutil.which("bun") is None:
        print("Error: 'bun' not found in PATH.", file=sys.stderr)
        sys.exit(1)

    if not args.no_conda and shutil.which("conda") is None:
        print("Error: 'conda' not found in PATH. Use --no-conda to skip.", file=sys.stderr)
        sys.exit(1)

    # Each run gets its own output directory
    if args.output:
        output_dir = Path(args.output)
    else:
        run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = OUTPUT_DIR / f"run_{run_timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load instances
    print(f"Loading instances from {data_path.name}")
    instances = load_instances(data_path)
    print(f"  Total: {len(instances)} instances")

    # Filter
    if args.instance:
        instances = [i for i in instances if i["instance_id"] == args.instance]
        if not instances:
            print(f"Error: instance '{args.instance}' not found in dataset", file=sys.stderr)
            sys.exit(1)

    # Skip already completed
    completed = set()
    for f in output_dir.glob("*.trajectory.json"):
        completed.add(f.stem.replace(".trajectory", ""))
    if completed:
        before = len(instances)
        instances = [i for i in instances if i["instance_id"] not in completed]
        if before != len(instances):
            print(f"  Skipping {before - len(instances)} already completed")

    # Limit
    if args.num > 0:
        instances = instances[:args.num]

    print(f"  Running: {len(instances)} instances")
    if not instances:
        print("Nothing to run.")
        return

    # Check server is running
    if not check_server_health(args.port):
        print(f"Error: API server not running on port {args.port}", file=sys.stderr)
        print(f"Please start the server first: bun run serve --port {args.port}", file=sys.stderr)
        sys.exit(1)

    # Check agent skills before running
    agent_info = check_agent_skills(args.port)
    print(f"\n  Model: {agent_info['model'] or '?'}")
    print(f"  Tools: {', '.join(agent_info['tools'][:20])}{'...' if len(agent_info['tools']) > 10 else ''}")
    if agent_info["skills"]:
        print(f"  Skills: {', '.join(agent_info['skills'])}")
    else:
        print(f"  Skills: (none)")
    print()

    # Store skills in args so process_instance can use them
    args._agent_skills = agent_info["skills"]

    # Process
    results = []
    for idx, instance in enumerate(instances):
            iid = instance["instance_id"]
            print(f"\n{'='*60}")
            print(f"[{idx+1}/{len(instances)}] {iid}")
            print(f"  repo: {instance.get('repo', '?')}  "
                  f"commit: {instance.get('base_commit', '?')[:8]}")
            print(f"{'='*60}")

            result = process_instance(instance, repos_dir, output_dir, args)
            results.append(result)

    # Summary
    print(f"\n{'='*60}")
    done = sum(1 for r in results if r["status"] == "completed")
    print(f"Done: {done}/{len(results)} completed, output: {output_dir}")

    # Generate preds.json
    generate_preds_json(output_dir, model_name=args.model or "mco-4")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
