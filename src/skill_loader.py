"""Skill 加载模块 — 从 skills/ 目录加载所有 skill 定义"""

import json
from pathlib import Path

from models import SkillDefinition, EvalCase


def load_skill(skill_dir: Path) -> SkillDefinition:
    """加载单个 skill 目录"""
    # 读取 metadata.json
    metadata_path = skill_dir / "metadata.json"
    metadata = {}
    if metadata_path.exists():
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    compiled = metadata.get("compiled_metadata", {})
    original = metadata.get("original_metadata", {})

    # 读取 SKILL.md
    skill_content = ""
    skill_md_path = skill_dir / "SKILL.md"
    if skill_md_path.exists():
        skill_content = skill_md_path.read_text(encoding="utf-8")

    # 读取 references
    refs_dir = skill_dir / "references"
    output_contract = _read_if_exists(refs_dir / "output_contract.md")
    verifier = _read_if_exists(refs_dir / "verifier.md")
    examples = _read_if_exists(refs_dir / "examples.md")
    handoff_policy = _read_if_exists(refs_dir / "handoff_policy.md")

    # 读取 eval_cases
    eval_cases = []
    eval_cases_path = skill_dir / "tests" / "eval_cases.json"
    if eval_cases_path.exists():
        raw = json.loads(eval_cases_path.read_text(encoding="utf-8"))
        eval_cases = _parse_eval_cases(raw)

    return SkillDefinition(
        skill_id=compiled.get("skill_id", skill_dir.name),
        name=compiled.get("display_name", original.get("name", skill_dir.name)),
        description=compiled.get("summary", original.get("description", "")),
        skill_content=skill_content,
        metadata=metadata,
        output_contract=output_contract,
        verifier=verifier,
        examples=examples,
        handoff_policy=handoff_policy,
        eval_cases=eval_cases,
    )


def load_all_skills(skills_dir: Path) -> list[SkillDefinition]:
    """加载目录下所有 skill"""
    skills = []
    if not skills_dir.exists():
        return skills
    for child in sorted(skills_dir.iterdir()):
        if child.is_dir() and (child / "SKILL.md").exists():
            skills.append(load_skill(child))
    return skills


def _read_if_exists(path: Path) -> str:
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def _parse_eval_cases(raw: dict) -> list[EvalCase]:
    """解析 eval_cases.json 中的各类测试用例"""
    cases = []

    for item in raw.get("positive_cases", []):
        cases.append(EvalCase(
            id=item["id"],
            case_type="positive",
            user_query=item["user_query"],
            available_context=item.get("available_context", {}),
            expected_behavior=item.get("expected_behavior", ""),
            must_include=item.get("must_include", []),
            must_not_include=item.get("must_not_include", []),
        ))

    for item in raw.get("negative_cases", []):
        cases.append(EvalCase(
            id=item["id"],
            case_type="negative",
            user_query=item["user_query"],
            reason_should_not_trigger=item.get("reason_should_not_trigger", ""),
            better_skill=item.get("better_skill", ""),
        ))

    for item in raw.get("ambiguous_cases", []):
        cases.append(EvalCase(
            id=item["id"],
            case_type="ambiguous",
            user_query=item["user_query"],
            expected_behavior=item.get("expected_behavior", ""),
        ))

    for item in raw.get("handoff_cases", []):
        cases.append(EvalCase(
            id=item["id"],
            case_type="handoff",
            user_query=item["user_query"],
            expected_next_skill=item.get("expected_next_skill", ""),
            handoff_condition=item.get("handoff_condition", ""),
        ))

    for item in raw.get("regression_cases", []):
        cases.append(EvalCase(
            id=item["id"],
            case_type="regression",
            user_query=item["user_query"],
            must_not_regress=item.get("must_not_regress", ""),
        ))

    return cases
