#!/usr/bin/env python3
"""Run WebShop tasks using Claude Code HTTP API with trajectory tracking.

Drives Claude Code agent to complete WebShop shopping tasks, using the same
infrastructure as run_swe.py: HTTP API streaming, tool restrictions, skill
injection, and sandbox enforcement.

Usage:
    # Run 50 tasks
    python run_webshop.py run --num 50

    # Run with specific port and skill
    python run_webshop.py run --num 10 --port 3199

    # Resume a previous run (skips completed tasks)
    python run_webshop.py run --num 50 --output output/run_20260805_123456
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
SANDBOX_HOOK_SCRIPT = SCRIPT_DIR.parent / "SWE" / "sandbox_hook.py"
OUTPUT_DIR = SCRIPT_DIR / "output"

# Default server port (same as SWE runner)
DEFAULT_PORT = 3199

# Add WebShop to path for env imports
sys.path.insert(0, str(SCRIPT_DIR))


# ── WebShop Environment ───────────────────────────────────────────────────────


def load_tasks(env, num_tasks: int = 0) -> list[dict]:
    """Load WebShop tasks from an existing environment.

    Returns a list of task dicts with task_idx and goal.
    """
    total = env.total_tasks if hasattr(env, 'total_tasks') else env.num_tasks if hasattr(env, 'num_tasks') else 0
    if total == 0:
        # Fallback: try resetting to discover total
        total = num_tasks if num_tasks > 0 else 500
    count = min(num_tasks, total) if num_tasks > 0 else total

    tasks = []
    for i in range(count):
        obs, info = env.reset(task_idx=i)
        tasks.append({
            "task_idx": i,
            "goal": info["goal"],
            "initial_obs": obs,
            "available_actions": info.get("available_actions"),
        })

    return tasks


def create_env():
    """Create a WebShop environment instance."""
    from webshop_env import WebShopEnv
    env = WebShopEnv()
    env.total_tasks = env.setup()
    return env


# ── Task Prompt Construction ──────────────────────────────────────────────────


SYSTEM_PROMPT = """You are a shopping assistant agent interacting with a web shopping environment.
At each step, you receive an observation (the current page content) and must output an action.

Valid actions:
- search[query]: Search for products with the given query
- click[element]: Click on an element on the page (product link, option, button)

Action rules:
- Your response MUST end with exactly ONE action line: search[...] or click[...]
- First search for relevant products based on the instruction
- Then click on a product that matches the requirements
- Select required options (color, size, etc.) before clicking Buy Now
- Click [Buy Now] when you've found and configured the right product
- Match ALL attributes mentioned in the instruction (color, size, price, etc.)
"""

SKILL_INSTRUCTION = """You have the following skills available via the Skill tool: {skills}

IMPORTANT: You MUST use the Skill tool to invoke a relevant skill BEFORE you start working on the task. Skills contain specialized strategies and domain knowledge that significantly improve your success rate.

"""

FIRST_TURN_TEMPLATE = """{system_prompt}

{skill_instruction}Here is your task:

Instruction: {goal}

Observation:
{observation}
{actions_text}
Output your action (search[...] or click[...]):"""

STEP_TEMPLATE = """Observation:
{observation}
{actions_text}
Output your action (search[...] or click[...]):"""


def format_available_actions(available_actions: dict | None) -> str:
    """Format available_actions into prompt text."""
    if not available_actions:
        return ""
    parts = []
    if available_actions.get("has_search_bar"):
        parts.append("- search[query]")
    clickables = available_actions.get("clickables", [])
    if clickables:
        items_str = ", ".join(clickables[:50])  # Limit to avoid huge prompts
        if len(clickables) > 50:
            items_str += f"... ({len(clickables)} total)"
        parts.append(f"- click[element]: Available: [{items_str}]")
    if not parts:
        return ""
    return "\nAvailable actions:\n" + "\n".join(parts) + "\n"


def build_first_prompt(goal: str, observation: str, available_actions: dict | None,
                       skills: list[str]) -> str:
    """Build the first-turn prompt for the agent."""
    skill_instruction = ""
    if skills:
        skill_instruction = SKILL_INSTRUCTION.format(skills=", ".join(skills))

    actions_text = format_available_actions(available_actions)
    return FIRST_TURN_TEMPLATE.format(
        system_prompt=SYSTEM_PROMPT,
        skill_instruction=skill_instruction,
        goal=goal,
        observation=observation,
        actions_text=actions_text,
    )


def build_step_prompt(observation: str, available_actions: dict | None) -> str:
    """Build a follow-up step prompt."""
    actions_text = format_available_actions(available_actions)
    return STEP_TEMPLATE.format(observation=observation, actions_text=actions_text)


# ── Action Parsing ────────────────────────────────────────────────────────────


import re

ACTION_PATTERNS = [
    re.compile(r"(?:Action:\s*)?(?:action:\s*)?(search\[.+?\])", re.IGNORECASE | re.DOTALL),
    re.compile(r"(?:Action:\s*)?(?:action:\s*)?(click\[.+?\])", re.IGNORECASE | re.DOTALL),
]


def parse_action(text: str) -> str:
    """Parse an action from agent response. Returns empty string on failure."""
    if not text:
        return ""

    # Try full-text match (last occurrence)
    for pattern in ACTION_PATTERNS:
        matches = pattern.findall(text)
        if matches:
            return matches[-1]

    # Try line-by-line from the end
    for line in reversed(text.strip().split("\n")):
        stripped = line.strip()
        for pattern in ACTION_PATTERNS:
            m = pattern.search(stripped)
            if m:
                return m.group(1)

    return ""


# ── Claude Code HTTP API (Session-based Multi-turn) ───────────────────────────


def check_server_health(port: int) -> bool:
    """Check if the API server is running."""
    import urllib.request
    try:
        resp = urllib.request.urlopen(f"http://localhost:{port}/health", timeout=2)
        return resp.status == 200
    except Exception:
        return False


def check_agent_skills(port: int) -> dict:
    """Query available skills from the agent."""
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


def create_session(port: int, cwd: str, allowed_tools: str = "") -> str:
    """Create a persistent session. Returns session_id."""
    import urllib.request

    url = f"http://localhost:{port}/api/sessions"
    body = {"cwd": cwd}
    if allowed_tools:
        body["allowedTools"] = allowed_tools
    payload = json.dumps(body).encode("utf-8")

    req = urllib.request.Request(
        url, data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read())
    session_id = data.get("session_id")
    if not session_id:
        raise RuntimeError(f"Failed to create session: {data}")
    return session_id


def destroy_session(port: int, session_id: str):
    """Destroy a session."""
    import urllib.request

    url = f"http://localhost:{port}/api/sessions/{session_id}"
    req = urllib.request.Request(url, method="DELETE")
    try:
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass


def send_session_message(port: int, session_id: str, content: str,
                         quiet: bool = False) -> tuple[str, list[dict], list[dict]]:
    """Send a message to an existing session (multi-turn).

    Returns (response_text, raw_messages, content_blocks).
    content_blocks includes all blocks from the assistant response:
    thinking, tool_use, text, etc.
    """
    import urllib.request

    url = f"http://localhost:{port}/api/sessions/{session_id}/message/stream"
    payload = json.dumps({"content": content}).encode("utf-8")

    req = urllib.request.Request(
        url, data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    messages = []
    response_texts = []
    all_content_blocks = []
    step_count = 0

    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            for raw_line in resp:
                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line.startswith("data: "):
                    continue
                try:
                    event = json.loads(line[6:])
                    messages.append(event)

                    # Extract content blocks from assistant messages
                    if event.get("type") == "assistant":
                        msg = event.get("message", {})
                        if msg.get("type") == "assistant":
                            inner = msg.get("message", {})
                            content_blocks = inner.get("content", msg.get("content", ""))
                            if isinstance(content_blocks, list):
                                for block in content_blocks:
                                    all_content_blocks.append(block)
                                    if block.get("type") == "text":
                                        response_texts.append(block.get("text", ""))
                                    elif block.get("type") == "tool_use" and not quiet:
                                        step_count += 1
                                        name = block.get("name", "?")
                                        inp = block.get("input", {})
                                        if name == "Skill":
                                            detail = inp.get("skill", "")
                                        else:
                                            detail = ""
                                        print(f"      [{name}{': ' + detail if detail else ''}]", end="", flush=True)
                except json.JSONDecodeError:
                    pass
    except Exception as e:
        if not quiet:
            print(f" [API error: {e}]", end="")

    return "\n".join(response_texts), messages, all_content_blocks


# ── Hook Setup ────────────────────────────────────────────────────────────────


def setup_sandbox_hook(workdir: str, output_dir: Path) -> Path | None:
    """Write .claude/settings.local.json with sandbox PreToolUse hook.

    Returns the settings path, or None if sandbox hook script not found.
    """
    if not SANDBOX_HOOK_SCRIPT.exists():
        return None

    claude_dir = Path(workdir) / ".claude"
    claude_dir.mkdir(exist_ok=True)

    settings_path = claude_dir / "settings.local.json"
    python_exe = sys.executable.replace("\\", "/")
    sandbox_hook_path = str(SANDBOX_HOOK_SCRIPT).replace("\\", "/")

    sandbox_env = f"SWE_SANDBOX_DIR={workdir}"
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
            ]
        }
    }

    settings_path.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    return settings_path


# ── Task Processing ───────────────────────────────────────────────────────────


def process_task(
    task: dict,
    env,
    output_dir: Path,
    args,
) -> dict:
    """Process a single WebShop task as a multi-turn conversation session.

    One task = one session. Each observation is sent as a user message
    within the same session, preserving full conversation history.
    """
    task_idx = task["task_idx"]
    goal = task["goal"]

    # Reset env to this task
    obs, info = env.reset(task_idx=task_idx)
    available_actions = info.get("available_actions")

    skills = getattr(args, "_agent_skills", [])

    # Working directory for sandbox
    workdir = f"/tmp/webshop-task-{task_idx}"
    os.makedirs(workdir, exist_ok=True)

    # Setup sandbox hook
    settings_path = setup_sandbox_hook(workdir, output_dir)

    # Create a persistent session for this task (multi-turn conversation)
    session_id = None
    steps_log = []
    total_reward = 0.0
    done = False
    error = ""
    total_steps = 0
    all_messages = []

    try:
        session_id = create_session(args.port, workdir, args.allowed_tools)

        # Send /new to start a fresh conversation for this task
        # This ensures each task gets its own isolated session context
        send_session_message(args.port, session_id, "/new", quiet=True)

        for step_i in range(args.max_steps):
            total_steps = step_i + 1

            if not args.quiet:
                print(f"  [step {step_i + 1}] ", end="", flush=True)

            # Build message: first turn includes system prompt + goal,
            # subsequent turns just send the new observation
            if step_i == 0:
                msg_content = build_first_prompt(goal, obs, available_actions, skills)
            else:
                msg_content = build_step_prompt(obs, available_actions)

            # Send within the session (conversation history is preserved)
            t0 = time.time()
            response_text, messages, content_blocks = send_session_message(
                args.port, session_id, msg_content, quiet=args.quiet
            )
            latency = time.time() - t0
            all_messages.extend(messages)

            # Parse action
            action = parse_action(response_text)

            if not args.quiet:
                action_display = action if action else "(no action)"
                print(f" -> {action_display} ({latency:.1f}s)")

            steps_log.append({
                "step": step_i + 1,
                "observation": obs[:500],
                "action": action,
                "response": response_text[:1000],
                "content_blocks": content_blocks,
                "latency_s": round(latency, 2),
            })

            if not action:
                error = f"Failed to parse action at step {step_i + 1}"
                break

            # Execute action in environment
            obs, reward, done, step_info = env.step(action)
            total_reward = reward
            available_actions = step_info.get("available_actions")

            if done:
                steps_log.append({
                    "step": step_i + 2,
                    "observation": obs[:500],
                    "action": "[DONE]",
                    "reward": reward,
                })
                break

    except Exception as e:
        error = str(e)
    finally:
        # Destroy session
        if session_id:
            destroy_session(args.port, session_id)
        # Cleanup sandbox settings
        if settings_path and settings_path.exists():
            settings_path.unlink()

    # Save trajectory
    trajectory = {
        "task_idx": task_idx,
        "goal": goal,
        "reward": total_reward,
        "done": done,
        "steps": total_steps,
        "max_steps": args.max_steps,
        "error": error,
        "steps_log": steps_log,
        "messages_count": len(all_messages),
    }

    traj_path = output_dir / f"task_{task_idx:04d}.trajectory.json"
    traj_path.write_text(json.dumps(trajectory, ensure_ascii=False, indent=2), encoding="utf-8")

    status = "done" if done else ("error" if error else "max_steps")
    print(f"  Result: reward={total_reward:.2f}, steps={total_steps}, status={status}")

    return {
        "task_idx": task_idx,
        "reward": total_reward,
        "steps": total_steps,
        "done": done,
        "error": error,
        "status": status,
    }


# ── Results Summary ───────────────────────────────────────────────────────────


def generate_summary(results: list[dict], output_dir: Path, model: str = ""):
    """Generate summary report from results."""
    if not results:
        return

    rewards = [r["reward"] for r in results]
    completed = [r for r in results if r["done"]]
    errors = [r for r in results if r["error"]]

    avg_reward = sum(rewards) / len(rewards) if rewards else 0
    success_rate = len(completed) / len(results) if results else 0
    r50 = sum(1 for r in rewards if r >= 0.5) / len(rewards) if rewards else 0
    r100 = sum(1 for r in rewards if r >= 1.0) / len(rewards) if rewards else 0
    avg_steps = sum(r["steps"] for r in results) / len(results) if results else 0

    summary = {
        "model": model,
        "total_tasks": len(results),
        "completed": len(completed),
        "errors": len(errors),
        "avg_reward": round(avg_reward, 4),
        "success_rate": round(success_rate, 4),
        "reward_ge_0.5": round(r50, 4),
        "reward_eq_1.0": round(r100, 4),
        "avg_steps": round(avg_steps, 2),
        "results": results,
    }

    summary_path = output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n{'='*60}")
    print(f"  WebShop Benchmark Summary")
    print(f"{'='*60}")
    print(f"  Model:          {model or '?'}")
    print(f"  Total tasks:    {len(results)}")
    print(f"  Completed:      {len(completed)}")
    print(f"  Errors:         {len(errors)}")
    print(f"  Avg reward:     {avg_reward:.3f}")
    print(f"  Success rate:   {success_rate:.1%}")
    print(f"  R >= 0.5:       {r50:.1%}")
    print(f"  R = 1.0:        {r100:.1%}")
    print(f"  Avg steps:      {avg_steps:.1f}")
    print(f"{'='*60}")
    print(f"  Output: {summary_path}")


# ── CLI ───────────────────────────────────────────────────────────────────────


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run WebShop tasks with Claude Code + trajectory tracking"
    )
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="Run WebShop tasks")
    run_parser.add_argument("--num", "-n", type=int, default=50, help="Number of tasks to run (0=all)")
    run_parser.add_argument("--max-steps", type=int, default=30, help="Max steps per task")
    run_parser.add_argument("--output", "-o", default="", help="Output directory")
    run_parser.add_argument(
        "--allowed-tools", default="Bash,Read,Glob,Grep,Skill",
        help="Comma-separated allowed tools"
    )
    run_parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Server port (default: {DEFAULT_PORT})")
    run_parser.add_argument("--quiet", "-q", action="store_true", help="Suppress step output")
    run_parser.add_argument("--model", "-m", default="", help="Model name for report")
    run_parser.add_argument("--task", "-t", type=int, default=-1, help="Run only this task index")

    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        sys.exit(1)
    return args


def main():
    args = parse_args()

    if args.command != "run":
        return

    # Output directory
    if args.output:
        output_dir = Path(args.output)
    else:
        run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = OUTPUT_DIR / f"run_{run_timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Check server
    if not check_server_health(args.port):
        print(f"Error: API server not running on port {args.port}", file=sys.stderr)
        print(f"Start it first: bun run serve --port {args.port}", file=sys.stderr)
        sys.exit(1)

    # Check agent info
    agent_info = check_agent_skills(args.port)
    print(f"\n  Model: {agent_info['model'] or '?'}")
    print(f"  Tools: {', '.join(agent_info['tools'][:15])}{'...' if len(agent_info['tools']) > 15 else ''}")
    if agent_info["skills"]:
        print(f"  Skills: {', '.join(agent_info['skills'])}")
    else:
        print(f"  Skills: (none)")
    args._agent_skills = agent_info["skills"]

    # Create environment
    print(f"\n[1/3] Initializing WebShop environment...")
    env = create_env()
    print(f"  Environment ready")

    # Load tasks
    print(f"\n[2/3] Loading WebShop tasks...")
    tasks = load_tasks(env, args.num)
    print(f"  Loaded: {len(tasks)} tasks")

    # Filter single task
    if args.task >= 0:
        tasks = [t for t in tasks if t["task_idx"] == args.task]
        if not tasks:
            print(f"Error: task {args.task} not found", file=sys.stderr)
            sys.exit(1)

    # Skip already completed
    completed = set()
    for f in output_dir.glob("task_*.trajectory.json"):
        try:
            data = json.loads(f.read_text())
            completed.add(data["task_idx"])
        except (json.JSONDecodeError, KeyError):
            pass
    if completed:
        before = len(tasks)
        tasks = [t for t in tasks if t["task_idx"] not in completed]
        if before != len(tasks):
            print(f"  Skipping {before - len(tasks)} already completed")

    print(f"  Running: {len(tasks)} tasks")
    if not tasks:
        print("Nothing to run.")
        return

    # Process tasks
    print(f"\n[3/3] Running tasks...")
    print(f"{'='*60}")

    results = []
    for idx, task in enumerate(tasks):
        print(f"\n[{idx+1}/{len(tasks)}] Task {task['task_idx']}: {task['goal']}")
        result = process_task(task, env, output_dir, args)
        results.append(result)

    # Summary
    env.close()
    generate_summary(results, output_dir, model=args.model or agent_info.get("model", ""))


if __name__ == "__main__":
    main()
