"""维度二：Utility（效用）实验

子维度:
  A. 结果质量 — LLM-as-Judge 评分
  B. 决策路径评估 — 从历史文件解析 agent 决策步骤
     B1. 无效探索减少（步数、报错/回退、无关工具调用）
     B2. 路径收敛度（决策熵，需与成功率联合解读）
  C. 效率成本 — token 消耗、延迟
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

from models import SkillDefinition, RunResult, JudgeResult, UtilityResult
from task_runner import run_experiment_batch
from judge import judge_batch
from history_parser import find_session_history, parse_session_history
from path_analysis import (
    PathMetrics, PathComparisonResult,
    extract_path_metrics, compare_paths,
)
from analysis.statistics import (
    mean_std, paired_significance_test, confidence_interval_mean
)


async def run_utility_experiment(
    skill: SkillDefinition,
    model: str,
    n_repeats: int,
    history_dir: Optional[Path] = None,
) -> tuple[UtilityResult, PathComparisonResult, dict]:
    """
    对单个 skill 运行 Utility 实验。

    流程:
    1. Baseline: 对正样本不注入 skill，运行 N 次
    2. Treatment: 对正样本注入 skill，运行 N 次
    3. 使用 Judge 对两组输出分别评分（子维度 A）
    4. 从历史文件解析决策路径（子维度 B）
    5. 对比效率成本（子维度 C）

    参数:
      history_dir: claude-code-backend 历史目录路径
                   (如 project_root/claude-code-backend/history)
    """
    positive_cases = skill.positive_cases
    if not positive_cases:
        print(f"  [SKIP] {skill.skill_id}: 无正样本用于 Utility 测试")
        return (
            UtilityResult(skill_id=skill.skill_id, model=model),
            PathComparisonResult(skill_id=skill.skill_id),
            {},
        )

    cases_map = {c.id: c for c in positive_cases}

    # === 运行任务 ===
    print(f"  Baseline 运行 ({len(positive_cases)} cases × {n_repeats} repeats)...")
    baseline_results = await run_experiment_batch(
        skill, positive_cases, model, "without_skill", n_repeats
    )

    print(f"  Treatment 运行 ({len(positive_cases)} cases × {n_repeats} repeats)...")
    treatment_results = await run_experiment_batch(
        skill, positive_cases, model, "with_skill", n_repeats
    )

    # === 子维度 A: 结果质量（LLM-as-Judge）===
    print(f"  Judge 评分 Baseline...")
    baseline_judgments = await judge_batch(skill, cases_map, baseline_results, "utility")

    print(f"  Judge 评分 Treatment...")
    treatment_judgments = await judge_batch(skill, cases_map, treatment_results, "utility")

    baseline_scores = [j.quality_score for j in baseline_judgments]
    treatment_scores = [j.quality_score for j in treatment_judgments]

    baseline_success = [1.0 if j.task_success else 0.0 for j in baseline_judgments]
    treatment_success = [1.0 if j.task_success else 0.0 for j in treatment_judgments]

    b_quality_mean, b_quality_std = mean_std(baseline_scores)
    t_quality_mean, t_quality_std = mean_std(treatment_scores)

    b_success_rate = sum(baseline_success) / len(baseline_success) if baseline_success else 0.0
    t_success_rate = sum(treatment_success) / len(treatment_success) if treatment_success else 0.0

    p_value = paired_significance_test(baseline_scores, treatment_scores)

    # === 子维度 B & C: 决策路径 + 效率成本（从历史文件解析）===
    print(f"  解析决策路径...")
    baseline_path_metrics = _extract_all_path_metrics(baseline_results, history_dir)
    treatment_path_metrics = _extract_all_path_metrics(treatment_results, history_dir)

    path_comparison = compare_paths(
        baseline_path_metrics, treatment_path_metrics, skill_id=skill.skill_id
    )

    # 用历史文件中的 token 数据补充（如果可用）
    b_tokens = [m.total_tokens for m in baseline_path_metrics if m.total_tokens > 0]
    t_tokens = [m.total_tokens for m in treatment_path_metrics if m.total_tokens > 0]

    # 如果历史中没有 token 信息，回退到 latency 作为效率代理
    if not b_tokens:
        b_tokens = [r.latency_ms for r in baseline_results if not r.error]
    if not t_tokens:
        t_tokens = [r.latency_ms for r in treatment_results if not r.error]

    b_tokens_mean, _ = mean_std(b_tokens)
    t_tokens_mean, _ = mean_std(t_tokens)

    # === 汇总 ===
    result = UtilityResult(
        skill_id=skill.skill_id,
        model=model,
        baseline_success_rate=b_success_rate,
        treatment_success_rate=t_success_rate,
        baseline_quality_mean=b_quality_mean,
        baseline_quality_std=b_quality_std,
        treatment_quality_mean=t_quality_mean,
        treatment_quality_std=t_quality_std,
        quality_p_value=p_value,
        baseline_tokens_mean=b_tokens_mean,
        treatment_tokens_mean=t_tokens_mean,
        token_delta=t_tokens_mean - b_tokens_mean,
    )

    details = {
        "baseline_results": baseline_results,
        "treatment_results": treatment_results,
        "baseline_judgments": baseline_judgments,
        "treatment_judgments": treatment_judgments,
        "baseline_path_metrics": baseline_path_metrics,
        "treatment_path_metrics": treatment_path_metrics,
        "path_comparison": path_comparison,
    }

    # 打印路径分析摘要
    _print_path_summary(path_comparison, t_success_rate, b_success_rate)

    return result, path_comparison, details


def _extract_all_path_metrics(
    run_results: list[RunResult],
    history_dir: Optional[Path],
) -> list[PathMetrics]:
    """从运行结果中提取所有路径指标"""
    metrics = []
    for r in run_results:
        if r.error:
            continue

        pm = PathMetrics(session_id=r.session_id, latency_ms=r.latency_ms)

        # 尝试从历史文件获取详细路径信息
        if history_dir and r.session_id:
            jsonl_path = find_session_history(r.session_id, history_dir)
            if jsonl_path:
                trace = parse_session_history(jsonl_path)
                pm = extract_path_metrics(trace, latency_ms=r.latency_ms)

        metrics.append(pm)
    return metrics


def _print_path_summary(
    pc: PathComparisonResult,
    treatment_success: float,
    baseline_success: float,
):
    """打印路径分析摘要（含决策熵联合解读）"""
    print(f"  --- 路径分析 ---")
    print(f"  平均步数: Baseline={pc.baseline_avg_steps:.1f}, "
          f"Treatment={pc.treatment_avg_steps:.1f} (Δ={pc.delta_steps:+.1f})")
    print(f"  报错/回退: Baseline={pc.baseline_avg_errors:.1f}, "
          f"Treatment={pc.treatment_avg_errors:.1f} (Δ={pc.delta_errors:+.1f})")
    print(f"  工具调用: Baseline={pc.baseline_avg_tool_calls:.1f}, "
          f"Treatment={pc.treatment_avg_tool_calls:.1f} (Δ={pc.delta_tool_calls:+.1f})")
    print(f"  决策熵: Baseline={pc.baseline_decision_entropy:.3f}, "
          f"Treatment={pc.treatment_decision_entropy:.3f} (ΔH={pc.delta_entropy:+.3f})")
    print(f"  Token: Baseline={pc.baseline_avg_tokens:.0f}, "
          f"Treatment={pc.treatment_avg_tokens:.0f} (Δ={pc.delta_tokens:+.0f})")

    # 决策熵联合解读
    delta_success = treatment_success - baseline_success
    if pc.delta_entropy > 0 and delta_success >= 0:
        print(f"  [解读] ΔH>0 且成功率提升/持平 → Skill 提供了有效先验，收敛是正向的")
    elif pc.delta_entropy > 0 and delta_success < -0.05:
        print(f"  [警告] ΔH>0 但成功率下降 → Skill 可能引导到错误方向，需人工排查")
    elif abs(pc.delta_entropy) < 0.05 and delta_success > 0.05:
        print(f"  [解读] ΔH≈0 但成功率提升 → Skill 通过知识内容起作用，未收窄搜索空间")
    print(f"  --- 路径分析结束 ---")
