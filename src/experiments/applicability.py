"""维度一：Applicability（可触发性）实验"""

import asyncio
from models import SkillDefinition, RunResult, JudgeResult, ApplicabilityResult
from task_runner import run_experiment_batch
from judge import judge_batch
from analysis.statistics import confidence_interval_proportion


async def run_applicability_experiment(
    skill: SkillDefinition,
    model: str,
    n_repeats: int,
) -> tuple[ApplicabilityResult, list[RunResult], list[JudgeResult]]:
    """
    对单个 skill 运行 Applicability 实验。

    流程:
    1. 对正样本集运行 N 次（with_skill 模式），检查是否正确触发
    2. 对负样本集运行 N 次（with_skill 模式），检查是否误触发
    3. 使用 Judge 判断触发行为
    4. 计算 Recall / Precision / False Trigger Rate
    """
    positive_cases = skill.positive_cases
    negative_cases = skill.negative_cases

    if not positive_cases and not negative_cases:
        print(f"  [SKIP] {skill.skill_id}: 无正/负样本")
        return ApplicabilityResult(skill_id=skill.skill_id), [], []

    # 运行正样本
    print(f"  运行正样本 ({len(positive_cases)} cases × {n_repeats} repeats)...")
    positive_results = await run_experiment_batch(
        skill, positive_cases, model, "with_skill", n_repeats
    )

    # 运行负样本
    print(f"  运行负样本 ({len(negative_cases)} cases × {n_repeats} repeats)...")
    negative_results = await run_experiment_batch(
        skill, negative_cases, model, "with_skill", n_repeats
    )

    # 构建 case map
    all_cases = positive_cases + negative_cases
    cases_map = {c.id: c for c in all_cases}

    # Judge 评判
    print(f"  Judge 评判触发行为...")
    all_results = positive_results + negative_results
    judge_results = await judge_batch(skill, cases_map, all_results, "applicability")

    # 计算指标
    # 正样本中判断为 triggered 的
    pos_judge = [j for j in judge_results if j.case_id.startswith("pos")]
    neg_judge = [j for j in judge_results if j.case_id.startswith("neg")]

    correct_triggers = sum(1 for j in pos_judge if j.triggered)
    total_positive_runs = len(pos_judge)

    false_triggers = sum(1 for j in neg_judge if j.triggered)
    total_negative_runs = len(neg_judge)

    # 总触发次数（正+负中都 triggered 的）
    total_triggered = correct_triggers + false_triggers

    # Recall = 正样本中正确触发 / 正样本总运行数
    recall = correct_triggers / total_positive_runs if total_positive_runs > 0 else 0.0

    # Precision = 正确触发 / 总触发
    precision = correct_triggers / total_triggered if total_triggered > 0 else 0.0

    # False Trigger Rate = 负样本中误触发 / 负样本总运行数
    ftr = false_triggers / total_negative_runs if total_negative_runs > 0 else 0.0

    # 置信区间
    recall_ci = confidence_interval_proportion(correct_triggers, total_positive_runs)
    precision_ci = confidence_interval_proportion(correct_triggers, total_triggered) if total_triggered > 0 else (0.0, 0.0)
    ftr_ci = confidence_interval_proportion(false_triggers, total_negative_runs)

    result = ApplicabilityResult(
        skill_id=skill.skill_id,
        recall=recall,
        precision=precision,
        false_trigger_rate=ftr,
        recall_ci=recall_ci,
        precision_ci=precision_ci,
        false_trigger_ci=ftr_ci,
        total_positive_runs=total_positive_runs,
        total_negative_runs=total_negative_runs,
        correct_triggers=correct_triggers,
        false_triggers=false_triggers,
    )

    return result, all_results, judge_results
