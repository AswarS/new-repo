"""任务执行模块 — 通过 claude-code-backend agent 运行实验任务"""

import asyncio
from config import MAX_CONCURRENCY, AGENT_CWD
from models import SkillDefinition, EvalCase, RunResult
from agent_client import agent_session_call


def _build_system_context_with_skill(skill: SkillDefinition) -> str:
    """构建注入 Skill 的上下文（作为 session 的第一条消息）"""
    return f"""[SYSTEM CONTEXT - SKILL INJECTION]

You are a helpful career planning assistant. You have access to the following skill definition. Follow its workflow, output contract, and verification checklist closely.

---
# Skill Definition

{skill.skill_content}

---
## Output Contract

{skill.output_contract}

---
## Verification Checklist

{skill.verifier}

---

Important: When you receive the next user message, apply this skill's workflow to answer their query. Produce all required output fields."""


def _build_system_context_without_skill() -> str:
    """构建不带 Skill 的 baseline 上下文"""
    return """[SYSTEM CONTEXT]

You are a helpful career planning assistant. Answer the user's question thoroughly and provide actionable guidance. Do not reference any external skill definitions or frameworks - rely on your own knowledge and reasoning."""


def _build_user_message(case: EvalCase) -> str:
    """构建用户消息，包含查询和可用上下文"""
    parts = [case.user_query]
    if case.available_context:
        context_str = "\n".join(
            f"- {k}: {v}" for k, v in case.available_context.items()
        )
        parts.append(f"\n\n[Available Context]\n{context_str}")
    return "\n".join(parts)


async def run_single(
    system_context: str,
    user_message: str,
) -> dict:
    """执行单次 agent 调用（通过 session）"""
    result = await agent_session_call(
        system_context=system_context,
        user_message=user_message,
        cwd=AGENT_CWD,
    )
    return {
        "response": result["response"],
        "latency_ms": result["latency_ms"],
        "error": result["error"],
        "session_id": result.get("session_id", ""),
    }


async def run_case_n_times(
    skill: SkillDefinition,
    case: EvalCase,
    model: str,
    mode: str,  # "with_skill" / "without_skill"
    n: int,
    semaphore: asyncio.Semaphore,
) -> list[RunResult]:
    """对一个 case 重复运行 N 次"""
    if mode == "with_skill":
        system_context = _build_system_context_with_skill(skill)
    else:
        system_context = _build_system_context_without_skill()

    user_message = _build_user_message(case)

    async def _run_once(idx: int) -> RunResult:
        async with semaphore:
            raw = await run_single(system_context, user_message)
            return RunResult(
                skill_id=skill.skill_id,
                case_id=case.id,
                model=model,
                run_index=idx,
                mode=mode,
                response=raw["response"],
                prompt_tokens=0,  # token 从历史文件中获取
                completion_tokens=0,
                total_tokens=0,
                latency_ms=raw["latency_ms"],
                error=raw["error"],
                session_id=raw.get("session_id", ""),
            )

    tasks = [_run_once(i) for i in range(n)]
    results = await asyncio.gather(*tasks)
    return list(results)


async def run_experiment_batch(
    skill: SkillDefinition,
    cases: list[EvalCase],
    model: str,
    mode: str,
    n: int,
) -> list[RunResult]:
    """批量运行一组 cases"""
    semaphore = asyncio.Semaphore(MAX_CONCURRENCY)
    all_tasks = []
    for case in cases:
        all_tasks.append(run_case_n_times(skill, case, model, mode, n, semaphore))
    batch_results = await asyncio.gather(*all_tasks)
    # flatten
    results = []
    for case_results in batch_results:
        results.extend(case_results)
    return results
