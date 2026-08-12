"""WebShop 评估指标计算"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from webshop_agent import EpisodeResult


@dataclass
class BenchmarkReport:
    """WebShop benchmark 汇总报告"""
    mode: str  # "baseline" or "with_skill"
    total_tasks: int = 0
    total_success: int = 0
    overall_success_rate: float = 0.0
    avg_reward: float = 0.0
    std_reward: float = 0.0
    avg_steps: float = 0.0
    std_steps: float = 0.0
    reward_threshold_10: float = 0.0  # reward >= 0.1 的比例
    reward_threshold_50: float = 0.0  # reward >= 0.5 的比例
    reward_threshold_100: float = 0.0  # reward == 1.0 的比例
    errors: int = 0
    total_episodes: int = 0


def compute_metrics(results: list[EpisodeResult], mode: str = "baseline") -> BenchmarkReport:
    """从一组 episode 结果计算评估指标"""
    if not results:
        return BenchmarkReport(mode=mode)

    total = len(results)
    rewards = [r.reward for r in results]
    successes = [r for r in results if r.reward == 1]
    errors = [r for r in results if r.error]
    steps_all = [r.steps for r in results if not r.error]

    # 更严格的成功定义：只有 reward == 1 才算成功
    success_rate = len(successes) / total if total > 0 else 0.0
    avg_reward = float(np.mean(rewards)) if rewards else 0.0
    std_reward = float(np.std(rewards)) if rewards else 0.0
    avg_steps = float(np.mean(steps_all)) if steps_all else 0.0
    std_steps = float(np.std(steps_all)) if steps_all else 0.0

    # 不同 reward 阈值的达标率
    r10 = sum(1 for r in rewards if r >= 0.1) / total if total > 0 else 0.0
    r50 = sum(1 for r in rewards if r >= 0.5) / total if total > 0 else 0.0
    r100 = sum(1 for r in rewards if r >= 1.0) / total if total > 0 else 0.0

    return BenchmarkReport(
        mode=mode,
        total_tasks=total,
        total_success=len(successes),
        overall_success_rate=success_rate,
        avg_reward=avg_reward,
        std_reward=std_reward,
        avg_steps=avg_steps,
        std_steps=std_steps,
        reward_threshold_10=r10,
        reward_threshold_50=r50,
        reward_threshold_100=r100,
        errors=len(errors),
        total_episodes=total,
    )


def compare_reports(baseline: BenchmarkReport, treatment: BenchmarkReport) -> dict:
    """对比 Baseline 与 Treatment 的结果"""
    return {
        "overall_delta_sr": treatment.overall_success_rate - baseline.overall_success_rate,
        "overall_delta_reward": treatment.avg_reward - baseline.avg_reward,
        "overall_delta_steps": treatment.avg_steps - baseline.avg_steps,
        "baseline_sr": baseline.overall_success_rate,
        "treatment_sr": treatment.overall_success_rate,
        "baseline_avg_reward": baseline.avg_reward,
        "treatment_avg_reward": treatment.avg_reward,
        "baseline_r50": baseline.reward_threshold_50,
        "treatment_r50": treatment.reward_threshold_50,
        "baseline_r100": baseline.reward_threshold_100,
        "treatment_r100": treatment.reward_threshold_100,
    }


def format_report(report: BenchmarkReport) -> str:
    """格式化输出报告"""
    lines = [
        f"{'='*60}",
        f"  WebShop Benchmark Report ({report.mode})",
        f"{'='*60}",
        f"",
        f"  总任务数:       {report.total_tasks}",
        f"  成功数 (r=1):    {report.total_success}",
        f"  成功率:         {report.overall_success_rate:.1%}",
        f"  平均 Reward:    {report.avg_reward:.3f} +/- {report.std_reward:.3f}",
        f"  平均步数:       {report.avg_steps:.1f} +/- {report.std_steps:.1f}",
        f"  R>=0.1 比例:    {report.reward_threshold_10:.1%}",
        f"  R>=0.5 比例:    {report.reward_threshold_50:.1%}",
        f"  R=1.0 比例:     {report.reward_threshold_100:.1%}",
        f"  错误数:         {report.errors}",
        f"{'='*60}",
    ]
    return "\n".join(lines)


def save_results(
    results: list[EpisodeResult],
    report: BenchmarkReport,
    output_dir: Path,
    mode: str,
):
    """保存详细结果和报告到文件"""
    output_dir.mkdir(parents=True, exist_ok=True)

    # 保存详细结果
    results_data = []
    for r in results:
        results_data.append({
            "task_idx": r.task_idx,
            "goal": r.goal,
            "success": r.success,
            "reward": r.reward,
            "steps": r.steps,
            "total_steps_attempted": r.total_steps_attempted,
            "max_steps": r.max_steps,
            "error": r.error,
            "session_id": r.session_id,
            "steps_log": [
                {
                    "step_idx": s.step_idx,
                    "observation": s.observation[:300],
                    "action": s.action,
                    "latency_ms": s.latency_ms,
                }
                for s in r.steps_log
            ],
        })

    results_file = output_dir / f"results_{mode}.json"
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(results_data, f, ensure_ascii=False, indent=2)

    # 保存报告
    report_file = output_dir / f"report_{mode}.txt"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(format_report(report))

    return results_file, report_file
