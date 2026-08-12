"""
ALFWorld Benchmark 运行脚本

通过 claude-code-backend WebSocket 驱动 agent 完成 ALFWorld 文本交互任务，
支持 Baseline / Treatment（注入 Skill）对比实验。

用法:
    python run_alfworld.py
    python run_alfworld.py --with-skill --skill-file path/to/skill.md
    python run_alfworld.py --num-tasks 20 --repeats 3 --max-steps 50
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

# 确保当前目录在 path 中
sys.path.insert(0, str(Path(__file__).parent))

from alfworld_config import (
    AGENT_WS_URL, MAX_STEPS, MAX_TASKS,
    REPEATS, OUTPUT_DIR, MAX_CONCURRENCY,
)
from alfworld_env import ALFWorldEnv
from alfworld_agent import ALFWorldAgent, EpisodeResult, SKILL_INJECT_SLASH_COMMAND, SKILL_INJECT_PROMPT
from alfworld_eval import (
    compute_metrics, compare_reports,
    format_report, save_results,
)


def parse_args():
    parser = argparse.ArgumentParser(description="ALFWorld Benchmark Runner")
    parser.add_argument(
        "--num-tasks", type=int, default=MAX_TASKS,
        help="运行的任务数量 (0=全部)"
    )
    parser.add_argument(
        "--repeats", type=int, default=REPEATS,
        help="每个任务重复次数"
    )
    parser.add_argument(
        "--max-steps", type=int, default=MAX_STEPS,
        help="每个任务最大步数"
    )
    parser.add_argument(
        "--with-skill", action="store_true",
        help="是否注入 Skill（Treatment 组）"
    )
    parser.add_argument(
        "--skill-name", type=str, default=None,
        help="Skill 名称（通过 claude-code-backend Skill Tool 调用，如 alfworld-planner）"
    )
    parser.add_argument(
        "--skill-args", type=str, default="",
        help="传给 Skill Tool 的参数"
    )
    parser.add_argument(
        "--skill-file", type=str, default=None,
        help="Skill 文件路径（仅 --inject-mode=prompt 时使用）"
    )
    parser.add_argument(
        "--skill-content", type=str, default=None,
        help="直接传入 Skill 内容（仅 --inject-mode=prompt 时使用）"
    )
    parser.add_argument(
        "--inject-mode", type=str, default="slash_command",
        choices=["slash_command", "prompt"],
        help="Skill 注入方式: slash_command（通过 Skill Tool）或 prompt（嵌入提示）"
    )
    parser.add_argument(
        "--baseline-only", action="store_true",
        help="仅运行 Baseline"
    )
    parser.add_argument(
        "--treatment-only", action="store_true",
        help="仅运行 Treatment（需指定 --skill-file）"
    )
    parser.add_argument(
        "--ws-url", type=str, default=AGENT_WS_URL,
        help="claude-code-backend WebSocket URL"
    )
    parser.add_argument(
        "--output-dir", type=str, default=str(OUTPUT_DIR),
        help="输出目录"
    )
    parser.add_argument(
        "--task-types", type=str, default=None,
        help="逗号分隔的任务类型过滤 (如 pick_and_place,pick_clean_then_place)"
    )
    parser.add_argument(
        "--alfworld-config", type=str, default=None,
        help="ALFWorld 配置文件路径"
    )
    parser.add_argument(
        "--concurrency", type=int, default=MAX_CONCURRENCY,
        help="最大并发数（注意 ALFWorld 环境非线程安全，建议设为 1）"
    )
    return parser.parse_args()


def load_skill_content(args) -> str:
    """加载 Skill 内容（仅 inject_mode=prompt 时需要）"""
    if args.skill_file:
        path = Path(args.skill_file)
        if not path.exists():
            print(f"[ERROR] Skill 文件不存在: {path}")
            sys.exit(1)
        return path.read_text(encoding="utf-8")
    if args.skill_content:
        return args.skill_content
    return ""


async def run_batch(
    env: ALFWorldEnv,
    task_indices: list[int],
    ws_url: str,
    skill_name: str,
    skill_args: str,
    skill_content: str,
    inject_mode: str,
    max_steps: int,
    repeats: int,
    mode: str,
) -> list[EpisodeResult]:
    """运行一批任务"""
    all_results = []
    total = len(task_indices) * repeats
    completed = 0

    for task_idx in task_indices:
        for rep in range(repeats):
            completed += 1
            # 重置环境到指定任务
            obs, info = env.reset(task_idx)
            task_type = info["task_type"]
            game_file = info["game_file"]

            print(
                f"  [{completed}/{total}] Task {task_idx} "
                f"({task_type}) rep={rep+1}/{repeats}...",
                end="",
                flush=True,
            )

            # 创建 agent 并运行 episode
            agent = ALFWorldAgent(
                ws_url=ws_url,
                skill_name=skill_name,
                skill_args=skill_args,
                skill_content=skill_content,
                inject_mode=inject_mode,
            )

            result = await agent.run_episode(
                first_observation=obs,
                step_fn=env.step,
                max_steps=max_steps,
                task_idx=task_idx,
                task_type=task_type,
                game_file=game_file,
                admissible_commands=info.get("admissible_commands", []),
            )

            status = "OK" if result.success else "FAIL"
            if result.error:
                status = f"ERR({result.error[:30]})"
            print(f" {status} (steps={result.steps})")

            all_results.append(result)

    return all_results


async def main():
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("  ALFWorld Benchmark")
    print("=" * 60)
    print(f"  WebSocket URL:  {args.ws_url}")
    print(f"  Max steps:      {args.max_steps}")
    print(f"  Repeats:        {args.repeats}")
    print(f"  Output dir:     {output_dir}")

    # 初始化 ALFWorld 环境
    print("\n[1/4] 初始化 ALFWorld 环境...")
    env = ALFWorldEnv(config_path=args.alfworld_config)

    try:
        num_available = env.setup()
    except Exception as e:
        print(f"[ERROR] ALFWorld 初始化失败: {e}")
        print("  请确保已安装 alfworld: pip install alfworld[full]")
        print("  并下载数据: alfworld-download")
        sys.exit(1)

    print(f"  可用任务: {num_available}")

    # 确定要运行的任务索引
    task_indices = list(range(num_available))

    # 按类型过滤
    if args.task_types:
        target_types = set(args.task_types.split(","))
        task_indices = [
            i for i in task_indices
            if env.get_task_type(env._game_files[i]) in target_types
        ]
        print(f"  过滤后任务数: {len(task_indices)} (types: {args.task_types})")

    # 数量限制
    if args.num_tasks > 0:
        task_indices = task_indices[:args.num_tasks]
    print(f"  运行任务数: {len(task_indices)}")

    # 加载 Skill 配置
    skill_name = args.skill_name or ""
    skill_args = args.skill_args or ""
    skill_content = ""
    inject_mode = args.inject_mode

    if args.with_skill or args.treatment_only:
        if inject_mode == "slash_command":
            if not skill_name:
                print("[ERROR] slash_command 模式需要指定 --skill-name")
                sys.exit(1)
            print(f"  Skill 注入: /{skill_name} (via Skill Tool)")
        else:
            skill_content = load_skill_content(args)
            if not skill_content:
                print("[ERROR] prompt 模式需要指定 --skill-file 或 --skill-content")
                sys.exit(1)
            print(f"  Skill 注入: prompt 模式 ({len(skill_content)} chars)")

    # 确定运行模式
    run_baseline = not args.treatment_only
    run_treatment = args.with_skill or args.treatment_only

    baseline_results = []
    treatment_results = []

    # [2/4] Baseline
    if run_baseline:
        print(f"\n[2/4] 运行 Baseline ({len(task_indices)} tasks × {args.repeats} reps)...")
        t0 = time.time()
        baseline_results = await run_batch(
            env, task_indices, args.ws_url,
            skill_name="", skill_args="",
            skill_content="", inject_mode=inject_mode,
            max_steps=args.max_steps,
            repeats=args.repeats, mode="baseline",
        )
        elapsed = time.time() - t0
        print(f"  Baseline 完成 ({elapsed:.1f}s)")
    else:
        print("\n[2/4] 跳过 Baseline")

    # [3/4] Treatment
    if run_treatment:
        print(f"\n[3/4] 运行 Treatment ({len(task_indices)} tasks × {args.repeats} reps)...")
        t0 = time.time()
        treatment_results = await run_batch(
            env, task_indices, args.ws_url,
            skill_name=skill_name, skill_args=skill_args,
            skill_content=skill_content, inject_mode=inject_mode,
            max_steps=args.max_steps,
            repeats=args.repeats, mode="with_skill",
        )
        elapsed = time.time() - t0
        print(f"  Treatment 完成 ({elapsed:.1f}s)")
    else:
        print("\n[3/4] 跳过 Treatment")

    # [4/4] 评估
    print(f"\n[4/4] 计算评估指标...")

    if baseline_results:
        baseline_report = compute_metrics(baseline_results, "baseline")
        print(f"\n{format_report(baseline_report)}")
        save_results(baseline_results, baseline_report, output_dir, "baseline")

    if treatment_results:
        treatment_report = compute_metrics(treatment_results, "with_skill")
        print(f"\n{format_report(treatment_report)}")
        save_results(treatment_results, treatment_report, output_dir, "with_skill")

    # 对比
    if baseline_results and treatment_results:
        comparison = compare_reports(baseline_report, treatment_report)
        print(f"\n{'='*60}")
        print(f"  对比 (Treatment - Baseline)")
        print(f"{'='*60}")
        print(f"  成功率 Δ:  {comparison['overall_delta_sr']:+.1%}")
        print(f"  步数 Δ:    {comparison['overall_delta_steps']:+.1f}")
        print(f"  --- 按类型 ---")
        for item in comparison["per_type"]:
            print(
                f"  {item['task_type']:30s}  "
                f"ΔSR={item['delta_sr']:+.1%}"
            )

        # 保存对比结果
        comp_file = output_dir / "comparison.json"
        with open(comp_file, "w", encoding="utf-8") as f:
            json.dump(comparison, f, ensure_ascii=False, indent=2)
        print(f"\n  对比结果已保存: {comp_file}")

    env.close()
    print(f"\n[DONE] 结果输出到: {output_dir}")


if __name__ == "__main__":
    asyncio.run(main())
