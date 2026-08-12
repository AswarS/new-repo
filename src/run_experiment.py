"""
Skill 质量评估实验主入口

用法:
    python run_experiment.py --skills-dir ../skills --output-dir ../output --phases all
    python run_experiment.py --phases applicability --repeats 5
    python run_experiment.py --phases utility --history-dir ../claude-code-backend/history
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# 将 src 加入路径
sys.path.insert(0, str(Path(__file__).parent))

from config import SKILLS_DIR, OUTPUT_DIR, STRONG_MODEL, WEAK_MODEL, DEFAULT_REPEATS
from skill_loader import load_all_skills
from experiments.applicability import run_applicability_experiment
from experiments.utility import run_utility_experiment
from experiments.transferability import run_transferability_experiment
from analysis.report import generate_report
from models import ApplicabilityResult, UtilityResult, TransferabilityResult
from path_analysis import PathComparisonResult


def parse_args():
    parser = argparse.ArgumentParser(description="Skill 质量定量评估实验")
    parser.add_argument(
        "--skills-dir", type=str, default=str(SKILLS_DIR),
        help="skills 目录路径"
    )
    parser.add_argument(
        "--output-dir", type=str, default=str(OUTPUT_DIR),
        help="结果输出目录"
    )
    parser.add_argument(
        "--strong-model", type=str, default=STRONG_MODEL,
        help="强模型 ID"
    )
    parser.add_argument(
        "--weak-model", type=str, default=WEAK_MODEL,
        help="弱模型 ID"
    )
    parser.add_argument(
        "--repeats", type=int, default=DEFAULT_REPEATS,
        help="每个 case 的重复运行次数"
    )
    parser.add_argument(
        "--phases", type=str, default="all",
        help="运行哪些实验维度: applicability,utility,transferability,all"
    )
    parser.add_argument(
        "--skill-ids", type=str, default=None,
        help="逗号分隔的 skill_id，只评估指定 skill（默认全部）"
    )
    parser.add_argument(
        "--history-dir", type=str, default=None,
        help="claude-code-backend 历史目录路径（用于解析 agent 决策路径）"
    )
    return parser.parse_args()


async def main():
    args = parse_args()

    skills_dir = Path(args.skills_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    phases = args.phases.split(",") if args.phases != "all" else ["applicability", "utility", "transferability"]
    strong_model = args.strong_model
    weak_model = args.weak_model
    n_repeats = args.repeats

    # 历史目录（用于路径分析）
    history_dir = Path(args.history_dir) if args.history_dir else _detect_history_dir(skills_dir)

    # 加载 skills
    print(f"加载 skills 从: {skills_dir}")
    skills = load_all_skills(skills_dir)
    if not skills:
        print("未找到任何 skill，退出")
        return

    # 过滤指定 skill
    if args.skill_ids:
        target_ids = set(args.skill_ids.split(","))
        skills = [s for s in skills if s.skill_id in target_ids]

    print(f"待评估 skills: {[s.skill_id for s in skills]}")
    print(f"实验维度: {phases}")
    print(f"重复次数: {n_repeats}")
    print(f"强模型: {strong_model}, 弱模型: {weak_model}")
    print(f"历史目录: {history_dir or '未指定（路径分析不可用）'}")
    print("=" * 60)

    applicability_results: list[ApplicabilityResult] = []
    utility_results: list[UtilityResult] = []
    path_comparisons: list[PathComparisonResult] = []
    transferability_results: list[TransferabilityResult] = []

    for skill in skills:
        print(f"\n{'='*60}")
        print(f"评估 Skill: {skill.skill_id} ({skill.name})")
        print(f"{'='*60}")

        # 维度一：Applicability
        if "applicability" in phases:
            print(f"\n[维度一] Applicability 测试")
            app_result, _, _ = await run_applicability_experiment(
                skill, strong_model, n_repeats
            )
            applicability_results.append(app_result)
            print(f"  结果: Recall={app_result.recall:.3f}, "
                  f"Precision={app_result.precision:.3f}, "
                  f"FTR={app_result.false_trigger_rate:.3f}")

        # 维度二：Utility（含路径分析）
        if "utility" in phases:
            print(f"\n[维度二] Utility 测试")
            util_result, path_comp, _ = await run_utility_experiment(
                skill, strong_model, n_repeats, history_dir=history_dir
            )
            utility_results.append(util_result)
            path_comparisons.append(path_comp)
            print(f"  结果: Baseline质量={util_result.baseline_quality_mean:.2f}, "
                  f"Treatment质量={util_result.treatment_quality_mean:.2f}, "
                  f"p={util_result.quality_p_value:.4f}")

        # 维度三：Transferability
        if "transferability" in phases:
            print(f"\n[维度三] Transferability 测试")
            trans_result = await run_transferability_experiment(
                skill, strong_model, weak_model, n_repeats
            )
            transferability_results.append(trans_result)
            print(f"  结果: 强模型增益={trans_result.strong_model_utility:+.3f}, "
                  f"弱模型增益={trans_result.weak_model_utility:+.3f}, "
                  f"敏感度={trans_result.model_sensitivity:.3f}")

    # 生成报告
    print(f"\n{'='*60}")
    print("生成实验报告...")
    config_summary = {
        "skills_dir": str(skills_dir),
        "strong_model": strong_model,
        "weak_model": weak_model,
        "repeats": n_repeats,
        "phases": phases,
        "n_skills": len(skills),
        "history_dir": str(history_dir) if history_dir else "N/A",
    }
    report_path = generate_report(
        applicability_results, utility_results, transferability_results,
        output_dir, config_summary, path_comparisons
    )
    print(f"报告已生成: {report_path}")
    print("实验完成！")


def _detect_history_dir(skills_dir: Path):
    """尝试自动检测 history 目录"""
    # 尝试 project_root/claude-code-backend/history
    project_root = skills_dir.parent
    candidate = project_root / "claude-code-backend" / "history"
    if candidate.exists():
        return candidate
    return None


if __name__ == "__main__":
    asyncio.run(main())
