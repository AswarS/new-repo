"""维度三：Transferability（可迁移性）实验"""

import asyncio
from models import SkillDefinition, TransferabilityResult
from experiments.utility import run_utility_experiment
from analysis.statistics import mean_std


async def run_transferability_experiment(
    skill: SkillDefinition,
    strong_model: str,
    weak_model: str,
    n_repeats: int,
) -> TransferabilityResult:
    """
    对单个 skill 运行 Transferability 实验。

    流程:
    1. 在强模型上运行 Utility 实验
    2. 在弱模型上运行 Utility 实验
    3. 计算跨模型的 Skill 收益敏感度
    4. 计算跨任务实例的方差
    """
    print(f"  === 强模型 ({strong_model}) ===")
    strong_result, _, strong_details = await run_utility_experiment(
        skill, strong_model, n_repeats
    )

    print(f"  === 弱模型 ({weak_model}) ===")
    weak_result, _, weak_details = await run_utility_experiment(
        skill, weak_model, n_repeats
    )

    # 计算 Skill 收益 = treatment - baseline
    strong_utility_gain = strong_result.treatment_quality_mean - strong_result.baseline_quality_mean
    weak_utility_gain = weak_result.treatment_quality_mean - weak_result.baseline_quality_mean

    # 模型敏感度 = |弱模型收益 - 强模型收益|
    model_sensitivity = abs(weak_utility_gain - strong_utility_gain)

    # 跨任务方差：以 treatment 组中按 case 分组的质量分方差衡量
    cross_task_variance = _compute_cross_task_variance(strong_details)

    # 最差案例成功率
    worst_case_rate = _compute_worst_case_success(strong_details)

    return TransferabilityResult(
        skill_id=skill.skill_id,
        strong_model_utility=strong_utility_gain,
        weak_model_utility=weak_utility_gain,
        model_sensitivity=model_sensitivity,
        cross_task_variance=cross_task_variance,
        worst_case_success_rate=worst_case_rate,
    )


def _compute_cross_task_variance(details: dict) -> float:
    """计算跨任务实例的质量分方差"""
    if not details:
        return 0.0
    judgments = details.get("treatment_judgments", [])
    if not judgments:
        return 0.0

    # 按 case_id 分组，计算每个 case 的平均得分
    case_scores: dict[str, list[float]] = {}
    for j in judgments:
        case_scores.setdefault(j.case_id, []).append(j.quality_score)

    case_means = [sum(scores) / len(scores) for scores in case_scores.values()]
    if len(case_means) < 2:
        return 0.0

    _, std = mean_std(case_means)
    return std ** 2  # 返回方差


def _compute_worst_case_success(details: dict) -> float:
    """计算最差案例的成功率"""
    if not details:
        return 0.0
    judgments = details.get("treatment_judgments", [])
    if not judgments:
        return 0.0

    # 按 case_id 分组
    case_success: dict[str, list[bool]] = {}
    for j in judgments:
        case_success.setdefault(j.case_id, []).append(j.task_success)

    if not case_success:
        return 0.0

    case_rates = [
        sum(1 for s in successes if s) / len(successes)
        for successes in case_success.values()
    ]
    return min(case_rates) if case_rates else 0.0
