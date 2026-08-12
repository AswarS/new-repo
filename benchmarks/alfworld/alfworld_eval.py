"""ALFWorld 评估指标计算"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np

from alfworld_agent import EpisodeResult


@dataclass
class TaskTypeMetrics:
    """单个任务类型的汇总指标"""
    task_type: str
    total: int = 0
    success: int = 0
    success_rate: float = 0.0
    avg_steps: float = 0.0
    std_steps: float = 0.0
    min_steps: int = 0
    max_steps: int = 0


@dataclass
class BenchmarkReport:
    """ALFWorld benchmark 汇总报告"""
    mode: str  # "baseline" or "with_skill"
    total_tasks: int = 0
    total_success: int = 0
    overall_success_rate: float = 0.0
    avg_steps_success: float = 0.0
    std_steps_success: float = 0.0
    per_type: list[TaskTypeMetrics] = field(default_factory=list)
    errors: int = 0
    total_episodes: int = 0


def compute_metrics(results: list[EpisodeResult], mode: str = "baseline") -> BenchmarkReport:
    """
    从一组 episode 结果计算评估指标。

    Args:
        results: EpisodeResult 列表
        mode: "baseline" 或 "with_skill"
    """
    if not results:
        return BenchmarkReport(mode=mode)

    total = len(results)
    successes = [r for r in results if r.success]
    errors = [r for r in results if r.error]

    # 总体成功率
    success_rate = len(successes) / total if total > 0 else 0.0

    # 成功任务的步数统计
    success_steps = [r.steps for r in successes]
    avg_steps = float(np.mean(success_steps)) if success_steps else 0.0
    std_steps = float(np.std(success_steps)) if success_steps else 0.0

    # 按任务类型分组
    by_type = defaultdict(list)
    for r in results:
        by_type[r.task_type].append(r)

    per_type = []
    for task_type, type_results in sorted(by_type.items()):
        type_successes = [r for r in type_results if r.success]
        type_steps = [r.steps for r in type_successes]
        per_type.append(TaskTypeMetrics(
            task_type=task_type,
            total=len(type_results),
            success=len(type_successes),
            success_rate=len(type_successes) / len(type_results) if type_results else 0.0,
            avg_steps=float(np.mean(type_steps)) if type_steps else 0.0,
            std_steps=float(np.std(type_steps)) if type_steps else 0.0,
            min_steps=min(type_steps) if type_steps else 0,
            max_steps=max(type_steps) if type_steps else 0,
        ))

    return BenchmarkReport(
        mode=mode,
        total_tasks=total,
        total_success=len(successes),
        overall_success_rate=success_rate,
        avg_steps_success=avg_steps,
        std_steps_success=std_steps,
        per_type=per_type,
        errors=len(errors),
        total_episodes=total,
    )


def compare_reports(
    baseline: BenchmarkReport,
    treatment: BenchmarkReport,
) -> dict:
    """对比 Baseline 与 Treatment 的结果"""
    delta_sr = treatment.overall_success_rate - baseline.overall_success_rate
    delta_steps = treatment.avg_steps_success - baseline.avg_steps_success

    per_type_comparison = []
    baseline_types = {t.task_type: t for t in baseline.per_type}
    treatment_types = {t.task_type: t for t in treatment.per_type}

    all_types = sorted(set(baseline_types.keys()) | set(treatment_types.keys()))
    for tt in all_types:
        b = baseline_types.get(tt)
        t = treatment_types.get(tt)
        per_type_comparison.append({
            "task_type": tt,
            "baseline_sr": b.success_rate if b else 0.0,
            "treatment_sr": t.success_rate if t else 0.0,
            "delta_sr": (t.success_rate if t else 0.0) - (b.success_rate if b else 0.0),
        })

    return {
        "overall_delta_sr": delta_sr,
        "overall_delta_steps": delta_steps,
        "baseline_sr": baseline.overall_success_rate,
        "treatment_sr": treatment.overall_success_rate,
        "per_type": per_type_comparison,
    }


def format_report(report: BenchmarkReport) -> str:
    """格式化输出报告"""
    lines = [
        f"{'='*60}",
        f"  ALFWorld Benchmark Report ({report.mode})",
        f"{'='*60}",
        f"",
        f"  总任务数:     {report.total_tasks}",
        f"  成功数:       {report.total_success}",
        f"  成功率:       {report.overall_success_rate:.1%}",
        f"  平均步数(成功): {report.avg_steps_success:.1f} ± {report.std_steps_success:.1f}",
        f"  错误数:       {report.errors}",
        f"",
        f"  --- 按任务类型 ---",
    ]

    for t in report.per_type:
        lines.append(
            f"  {t.task_type:30s}  SR={t.success_rate:.1%}  "
            f"({t.success}/{t.total})  "
            f"steps={t.avg_steps:.1f}±{t.std_steps:.1f}"
        )

    lines.append(f"{'='*60}")
    return "\n".join(lines)


def save_results(
    results: list[EpisodeResult],
    report: BenchmarkReport,
    output_dir: Path,
    mode: str,
):
    """保存详细结果和报告到文件"""
    output_dir.mkdir(parents=True, exist_ok=True)

    # 保存详细结果 (JSON)
    results_data = []
    for r in results:
        results_data.append({
            "task_idx": r.task_idx,
            "task_type": r.task_type,
            "game_file": r.game_file,
            "success": r.success,
            "steps": r.steps,
            "total_steps_attempted": r.total_steps_attempted,
            "max_steps": r.max_steps,
            "reward": r.reward,
            "error": r.error,
            "session_id": r.session_id,
            "steps_log": [
                {
                    "step_idx": s.step_idx,
                    "observation": s.observation,
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
