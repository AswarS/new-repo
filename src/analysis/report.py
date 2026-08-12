"""实验报告生成模块"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from dataclasses import asdict
from typing import List, Optional

from models import (
    ApplicabilityResult, UtilityResult, TransferabilityResult,
)
from path_analysis import PathComparisonResult


def generate_report(
    applicability_results: List[ApplicabilityResult],
    utility_results: List[UtilityResult],
    transferability_results: List[TransferabilityResult],
    output_dir: Path,
    config_summary: dict,
    path_comparisons: Optional[List[PathComparisonResult]] = None,
) -> str:
    """生成完整实验报告（Markdown + JSON）"""
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if path_comparisons is None:
        path_comparisons = []

    # 生成 JSON 原始数据
    raw_data = {
        "timestamp": timestamp,
        "config": config_summary,
        "applicability": [asdict(r) for r in applicability_results],
        "utility": [asdict(r) for r in utility_results],
        "path_analysis": [asdict(r) for r in path_comparisons],
        "transferability": [asdict(r) for r in transferability_results],
    }
    json_path = output_dir / f"results_{timestamp}.json"
    json_path.write_text(json.dumps(raw_data, ensure_ascii=False, indent=2), encoding="utf-8")

    # 生成 Markdown 报告
    md = _build_markdown_report(
        applicability_results, utility_results, transferability_results,
        config_summary, path_comparisons
    )
    md_path = output_dir / f"report_{timestamp}.md"
    md_path.write_text(md, encoding="utf-8")

    return str(md_path)


def _build_markdown_report(
    app_results: List[ApplicabilityResult],
    util_results: List[UtilityResult],
    trans_results: List[TransferabilityResult],
    config: dict,
    path_comparisons: List[PathComparisonResult],
) -> str:
    lines = []
    lines.append("# Skill 质量评估实验报告\n")
    lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # 配置摘要
    lines.append("## 实验配置\n")
    for k, v in config.items():
        lines.append(f"- **{k}**: {v}")
    lines.append("")

    # 维度一：Applicability
    if app_results:
        lines.append("## 维度一：Applicability（可触发性）\n")
        lines.append("| Skill | Recall | Precision | False Trigger Rate | Recall 95%CI | Precision 95%CI |")
        lines.append("|---|---|---|---|---|---|")
        for r in app_results:
            lines.append(
                f"| {r.skill_id} "
                f"| {r.recall:.3f} "
                f"| {r.precision:.3f} "
                f"| {r.false_trigger_rate:.3f} "
                f"| [{r.recall_ci[0]:.3f}, {r.recall_ci[1]:.3f}] "
                f"| [{r.precision_ci[0]:.3f}, {r.precision_ci[1]:.3f}] |"
            )
        lines.append("")

    # 维度二：Utility — 结果质量
    if util_results:
        lines.append("## 维度二：Utility（效用）\n")
        lines.append("### 子维度 A：结果质量\n")
        lines.append("| Skill | Model | Baseline 成功率 | Treatment 成功率 | Baseline 质量(μ±σ) | Treatment 质量(μ±σ) | p值 |")
        lines.append("|---|---|---|---|---|---|---|")
        for r in util_results:
            lines.append(
                f"| {r.skill_id} "
                f"| {r.model} "
                f"| {r.baseline_success_rate:.3f} "
                f"| {r.treatment_success_rate:.3f} "
                f"| {r.baseline_quality_mean:.2f}±{r.baseline_quality_std:.2f} "
                f"| {r.treatment_quality_mean:.2f}±{r.treatment_quality_std:.2f} "
                f"| {r.quality_p_value:.4f} |"
            )
        lines.append("")

    # 维度二 — 路径分析
    if path_comparisons:
        lines.append("### 子维度 B：Agent 决策路径评估\n")
        lines.append("#### B1. 无效探索减少\n")
        lines.append("| Skill | Baseline步数 | Treatment步数 | Δ步数 | Baseline报错 | Treatment报错 | Δ报错 | Baseline工具调用 | Treatment工具调用 | Δ工具调用 |")
        lines.append("|---|---|---|---|---|---|---|---|---|---|")
        for pc in path_comparisons:
            lines.append(
                f"| {pc.skill_id} "
                f"| {pc.baseline_avg_steps:.1f} "
                f"| {pc.treatment_avg_steps:.1f} "
                f"| {pc.delta_steps:+.1f} "
                f"| {pc.baseline_avg_errors:.1f} "
                f"| {pc.treatment_avg_errors:.1f} "
                f"| {pc.delta_errors:+.1f} "
                f"| {pc.baseline_avg_tool_calls:.1f} "
                f"| {pc.treatment_avg_tool_calls:.1f} "
                f"| {pc.delta_tool_calls:+.1f} |"
            )
        lines.append("")

        lines.append("#### B2. 路径收敛度（决策熵）\n")
        lines.append("| Skill | Baseline H | Treatment H | ΔH (B-T) | 成功率变化 | 联合解读 |")
        lines.append("|---|---|---|---|---|---|")
        for i, pc in enumerate(path_comparisons):
            # 联合解读需要成功率数据
            delta_success = 0.0
            interpretation = "—"
            if i < len(util_results):
                delta_success = util_results[i].treatment_success_rate - util_results[i].baseline_success_rate
                if pc.delta_entropy > 0.05 and delta_success >= 0:
                    interpretation = "✅ 有效收敛"
                elif pc.delta_entropy > 0.05 and delta_success < -0.05:
                    interpretation = "⚠️ 收敛到错误方向"
                elif abs(pc.delta_entropy) <= 0.05 and delta_success > 0.05:
                    interpretation = "ℹ️ 知识内容起作用，非收窄搜索"
                else:
                    interpretation = "— 效果不显著"

            lines.append(
                f"| {pc.skill_id} "
                f"| {pc.baseline_decision_entropy:.3f} "
                f"| {pc.treatment_decision_entropy:.3f} "
                f"| {pc.delta_entropy:+.3f} "
                f"| {delta_success:+.3f} "
                f"| {interpretation} |"
            )
        lines.append("")

        lines.append("### 子维度 C：效率成本（ROI）\n")
        lines.append("| Skill | Baseline Token | Treatment Token | ΔToken | Baseline延迟(ms) | Treatment延迟(ms) | Δ延迟 |")
        lines.append("|---|---|---|---|---|---|---|")
        for pc in path_comparisons:
            lines.append(
                f"| {pc.skill_id} "
                f"| {pc.baseline_avg_tokens:.0f} "
                f"| {pc.treatment_avg_tokens:.0f} "
                f"| {pc.delta_tokens:+.0f} "
                f"| {pc.baseline_avg_latency:.0f} "
                f"| {pc.treatment_avg_latency:.0f} "
                f"| {pc.delta_latency:+.0f} |"
            )
        lines.append("")

    # 维度三：Transferability
    if trans_results:
        lines.append("## 维度三：Transferability（可迁移性）\n")
        lines.append("| Skill | 强模型 Utility | 弱模型 Utility | 模型敏感度 | 跨任务方差 | 最差案例成功率 |")
        lines.append("|---|---|---|---|---|---|")
        for r in trans_results:
            lines.append(
                f"| {r.skill_id} "
                f"| {r.strong_model_utility:+.3f} "
                f"| {r.weak_model_utility:+.3f} "
                f"| {r.model_sensitivity:.3f} "
                f"| {r.cross_task_variance:.4f} "
                f"| {r.worst_case_success_rate:.3f} |"
            )
        lines.append("")

    # 分析要点
    lines.append("## 分析要点\n")
    lines.append("- Applicability 和 Utility 指标不应合并为单一总分")
    lines.append("- **路径收敛（决策熵下降）须与成功率联合解读**：ΔH>0 + 成功率下降 = 引导错误方向")
    lines.append("- 模型敏感度高说明 Skill 对弱模型收益更大（或反之），需分开报告")
    lines.append("- 跨任务方差过大提示 Skill 可能过拟合特定案例")
    lines.append("- Token 增量为正是预期的（注入了额外上下文），关键看 净收益比 = 质量提升 / 成本增量")
    lines.append("")

    return "\n".join(lines)
