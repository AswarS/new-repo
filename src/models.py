"""数据模型定义"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class EvalCase:
    """单个评估用例"""
    id: str
    case_type: str  # positive / negative / ambiguous / handoff / regression
    user_query: str
    available_context: dict[str, str] = field(default_factory=dict)
    expected_behavior: str = ""
    must_include: list[str] = field(default_factory=list)
    must_not_include: list[str] = field(default_factory=list)
    reason_should_not_trigger: str = ""
    better_skill: str = ""
    expected_next_skill: str = ""
    handoff_condition: str = ""
    must_not_regress: str = ""


@dataclass
class SkillDefinition:
    """加载后的 Skill 完整定义"""
    skill_id: str
    name: str
    description: str
    skill_content: str  # SKILL.md 全文
    metadata: dict[str, Any] = field(default_factory=dict)
    output_contract: str = ""
    verifier: str = ""
    examples: str = ""
    handoff_policy: str = ""
    eval_cases: list[EvalCase] = field(default_factory=list)

    @property
    def positive_cases(self) -> list[EvalCase]:
        return [c for c in self.eval_cases if c.case_type == "positive"]

    @property
    def negative_cases(self) -> list[EvalCase]:
        return [c for c in self.eval_cases if c.case_type == "negative"]

    @property
    def ambiguous_cases(self) -> list[EvalCase]:
        return [c for c in self.eval_cases if c.case_type == "ambiguous"]

    @property
    def handoff_cases(self) -> list[EvalCase]:
        return [c for c in self.eval_cases if c.case_type == "handoff"]

    @property
    def regression_cases(self) -> list[EvalCase]:
        return [c for c in self.eval_cases if c.case_type == "regression"]


@dataclass
class RunResult:
    """单次 LLM 调用结果"""
    skill_id: str
    case_id: str
    model: str
    run_index: int
    mode: str  # "with_skill" / "without_skill"
    response: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_ms: float = 0.0
    error: str = ""
    session_id: str = ""  # agent session ID，用于关联历史文件


@dataclass
class JudgeResult:
    """LLM-as-Judge 评分结果"""
    skill_id: str
    case_id: str
    run_index: int
    mode: str
    # Applicability 判断
    triggered: bool = False
    trigger_correct: bool = False
    # Utility 评分
    task_success: bool = False
    quality_score: float = 0.0  # 0-10
    quality_rationale: str = ""
    # 输出合规性
    output_fields_present: list[str] = field(default_factory=list)
    output_fields_missing: list[str] = field(default_factory=list)
    # Verifier 结果
    verdict: str = ""  # PASS / PASS_WITH_MINOR_ISSUES / FAIL
    failed_checks: list[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class ApplicabilityResult:
    """Applicability 维度汇总"""
    skill_id: str
    recall: float = 0.0
    precision: float = 0.0
    false_trigger_rate: float = 0.0
    recall_ci: tuple[float, float] = (0.0, 0.0)
    precision_ci: tuple[float, float] = (0.0, 0.0)
    false_trigger_ci: tuple[float, float] = (0.0, 0.0)
    total_positive_runs: int = 0
    total_negative_runs: int = 0
    correct_triggers: int = 0
    false_triggers: int = 0


@dataclass
class UtilityResult:
    """Utility 维度汇总"""
    skill_id: str
    model: str
    # 结果质量
    baseline_success_rate: float = 0.0
    treatment_success_rate: float = 0.0
    baseline_quality_mean: float = 0.0
    baseline_quality_std: float = 0.0
    treatment_quality_mean: float = 0.0
    treatment_quality_std: float = 0.0
    quality_p_value: float = 1.0
    # 效率
    baseline_tokens_mean: float = 0.0
    treatment_tokens_mean: float = 0.0
    token_delta: float = 0.0
    # 知识正确性
    knowledge_accuracy: float = 0.0


@dataclass
class TransferabilityResult:
    """Transferability 维度汇总"""
    skill_id: str
    strong_model_utility: float = 0.0
    weak_model_utility: float = 0.0
    model_sensitivity: float = 0.0
    cross_task_variance: float = 0.0
    worst_case_success_rate: float = 0.0
