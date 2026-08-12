"""LLM-as-Judge 评分模块 — 通过 claude-code-backend agent 进行评判"""

from __future__ import annotations

import json
import asyncio

from config import MAX_CONCURRENCY
from models import SkillDefinition, EvalCase, RunResult, JudgeResult
from agent_client import agent_one_shot


APPLICABILITY_JUDGE_PROMPT = """You are an expert evaluator assessing whether an AI assistant correctly triggered (followed) a specific skill.

## Skill Being Evaluated
Name: {skill_name}
Description: {skill_description}

## Skill's Expected Outputs
{output_contract}

## Task

Evaluate the assistant's response and determine:
1. **triggered**: Did the response follow the skill's workflow and produce outputs consistent with the skill's purpose? (true/false)
2. **trigger_correct**: Given the case type, was the triggering behavior correct? (true/false)
   - For positive cases: triggered=true is correct
   - For negative cases: triggered=false is correct

## Case Information
- Case type: {case_type}
- User query: {user_query}
- Reason should not trigger (if negative): {reason_not_trigger}
- Better skill (if negative): {better_skill}

## Assistant's Response
{response}

## Output Format
Return ONLY a JSON object (no markdown, no explanation outside the JSON):
{{"triggered": true, "trigger_correct": true, "reasoning": "brief explanation"}}"""


UTILITY_JUDGE_PROMPT = """You are an expert evaluator scoring the quality of an AI career planning assistant's response.

## Evaluation Criteria

### Task Success (binary)
Did the response meaningfully address the user's request?

### Quality Score (0-10)
- 0-2: Completely off-topic or harmful
- 3-4: Partially relevant but missing key elements
- 5-6: Adequate but generic, missing nuance
- 7-8: Good quality, well-structured, mostly complete
- 9-10: Excellent, comprehensive, personalized, actionable

### Output Contract Compliance
Check which required fields are present:
{required_fields}

### Verification Checks
{verifier_rubric}

## User Query
{user_query}

## Available Context
{context}

## Must Include
{must_include}

## Must Not Include
{must_not_include}

## Assistant's Response
{response}

## Output Format
Return ONLY a JSON object (no markdown, no explanation outside the JSON):
{{"task_success": true, "quality_score": 7.5, "quality_rationale": "...", "output_fields_present": [], "output_fields_missing": [], "verdict": "PASS", "failed_checks": [], "notes": ""}}"""


async def judge_applicability(
    skill: SkillDefinition,
    case: EvalCase,
    run_result: RunResult,
) -> JudgeResult:
    """评判触发行为是否正确"""
    prompt = APPLICABILITY_JUDGE_PROMPT.format(
        skill_name=skill.name,
        skill_description=skill.description,
        output_contract=skill.output_contract[:2000],
        case_type=case.case_type,
        user_query=case.user_query,
        reason_not_trigger=case.reason_should_not_trigger,
        better_skill=case.better_skill,
        response=run_result.response[:3000],
    )

    result = await agent_one_shot(prompt)
    parsed = _parse_json_response(result["response"])

    return JudgeResult(
        skill_id=skill.skill_id,
        case_id=case.id,
        run_index=run_result.run_index,
        mode=run_result.mode,
        triggered=parsed.get("triggered", False),
        trigger_correct=parsed.get("trigger_correct", False),
    )


async def judge_utility(
    skill: SkillDefinition,
    case: EvalCase,
    run_result: RunResult,
) -> JudgeResult:
    """评判输出质量"""
    original = skill.metadata.get("original_metadata", {})
    outputs = original.get("outputs", [])
    required_fields = "\n".join(f"- {f}" for f in outputs) if outputs else "N/A"

    prompt = UTILITY_JUDGE_PROMPT.format(
        required_fields=required_fields,
        verifier_rubric=skill.verifier[:2000],
        user_query=case.user_query,
        context=json.dumps(case.available_context, ensure_ascii=False),
        must_include=", ".join(case.must_include) if case.must_include else "N/A",
        must_not_include=", ".join(case.must_not_include) if case.must_not_include else "N/A",
        response=run_result.response[:4000],
    )

    result = await agent_one_shot(prompt)
    parsed = _parse_json_response(result["response"])

    return JudgeResult(
        skill_id=skill.skill_id,
        case_id=case.id,
        run_index=run_result.run_index,
        mode=run_result.mode,
        task_success=parsed.get("task_success", False),
        quality_score=float(parsed.get("quality_score", 0)),
        quality_rationale=parsed.get("quality_rationale", ""),
        output_fields_present=parsed.get("output_fields_present", []),
        output_fields_missing=parsed.get("output_fields_missing", []),
        verdict=parsed.get("verdict", "FAIL"),
        failed_checks=parsed.get("failed_checks", []),
        notes=parsed.get("notes", ""),
    )


async def judge_batch(
    skill: SkillDefinition,
    cases_map: dict[str, EvalCase],
    run_results: list[RunResult],
    judge_type: str,
) -> list[JudgeResult]:
    """批量评判"""
    semaphore = asyncio.Semaphore(MAX_CONCURRENCY)

    async def _judge_one(result: RunResult) -> JudgeResult:
        async with semaphore:
            case = cases_map[result.case_id]
            if judge_type == "applicability":
                return await judge_applicability(skill, case, result)
            else:
                return await judge_utility(skill, case, result)

    tasks = [_judge_one(r) for r in run_results if not r.error]
    return list(await asyncio.gather(*tasks))


def _parse_json_response(raw: str) -> dict:
    """从 agent 回复中解析 JSON"""
    if not raw:
        return {"error": "Empty response"}
    # 尝试直接解析
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    # 尝试从 markdown code block 中提取
    if "```json" in raw:
        try:
            start = raw.index("```json") + 7
            end = raw.index("```", start)
            return json.loads(raw[start:end].strip())
        except (json.JSONDecodeError, ValueError):
            pass
    if "```" in raw:
        try:
            start = raw.index("```") + 3
            end = raw.index("```", start)
            return json.loads(raw[start:end].strip())
        except (json.JSONDecodeError, ValueError):
            pass
    # 尝试找到第一个 { 和最后一个 }
    first_brace = raw.find("{")
    last_brace = raw.rfind("}")
    if first_brace != -1 and last_brace != -1:
        try:
            return json.loads(raw[first_brace:last_brace + 1])
        except json.JSONDecodeError:
            pass
    return {"error": "Failed to parse judge response", "raw": raw[:500]}
