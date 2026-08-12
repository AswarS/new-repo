"""决策路径分析模块 — 基于 SessionTrace 计算路径指标"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field
from typing import List

from history_parser import SessionTrace


@dataclass
class PathMetrics:
    """单次运行的路径指标"""
    session_id: str = ""
    # B1: 无效探索
    total_steps: int = 0
    total_tool_calls: int = 0
    error_retries: int = 0  # 报错/回退次数
    irrelevant_tool_ratio: float = 0.0  # 无关工具调用占比（需结合最终结果判断）
    # B2: 路径信息
    tool_sequence: list = field(default_factory=list)  # 工具调用序列
    # C: 效率成本
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0
    latency_ms: float = 0.0


@dataclass
class PathComparisonResult:
    """Baseline vs Treatment 路径对比结果"""
    skill_id: str = ""
    # B1: 无效探索减少
    baseline_avg_steps: float = 0.0
    treatment_avg_steps: float = 0.0
    delta_steps: float = 0.0
    baseline_avg_errors: float = 0.0
    treatment_avg_errors: float = 0.0
    delta_errors: float = 0.0
    baseline_avg_tool_calls: float = 0.0
    treatment_avg_tool_calls: float = 0.0
    delta_tool_calls: float = 0.0
    # B2: 决策熵
    baseline_decision_entropy: float = 0.0
    treatment_decision_entropy: float = 0.0
    delta_entropy: float = 0.0  # H_baseline - H_treatment，正值=收敛
    # C: 效率成本
    baseline_avg_tokens: float = 0.0
    treatment_avg_tokens: float = 0.0
    delta_tokens: float = 0.0
    baseline_avg_latency: float = 0.0
    treatment_avg_latency: float = 0.0
    delta_latency: float = 0.0


def extract_path_metrics(trace: SessionTrace, latency_ms: float = 0.0) -> PathMetrics:
    """从 SessionTrace 提取路径指标"""
    return PathMetrics(
        session_id=trace.session_id,
        total_steps=trace.total_steps,
        total_tool_calls=trace.total_tool_calls,
        error_retries=trace.error_count,
        tool_sequence=trace.tool_call_sequence,
        total_input_tokens=trace.total_input_tokens,
        total_output_tokens=trace.total_output_tokens,
        total_tokens=trace.total_tokens,
        latency_ms=latency_ms,
    )


def compute_group_decision_entropy(tool_sequences: List[List[str]]) -> float:
    """
    计算一组运行的决策熵。

    将每次运行的工具调用序列对齐到相同步骤位置，
    计算每个位置上选择的香农熵，然后求平均。

    如果序列长度不同，短序列在该位置视为 "<no_action>"。
    """
    if not tool_sequences:
        return 0.0

    # 过滤空序列
    non_empty = [seq for seq in tool_sequences if seq]
    if not non_empty:
        return 0.0

    max_len = max(len(seq) for seq in tool_sequences)
    if max_len == 0:
        return 0.0

    n_runs = len(tool_sequences)
    entropies = []

    for pos in range(max_len):
        choices = []
        for seq in tool_sequences:
            if pos < len(seq):
                choices.append(seq[pos])
            else:
                choices.append("<no_action>")

        # 计算该位置的香农熵
        counts = Counter(choices)
        entropy = 0.0
        for count in counts.values():
            p = count / n_runs
            if p > 0:
                entropy -= p * math.log2(p)
        entropies.append(entropy)

    return sum(entropies) / len(entropies) if entropies else 0.0


def compare_paths(
    baseline_metrics: List[PathMetrics],
    treatment_metrics: List[PathMetrics],
    skill_id: str = "",
) -> PathComparisonResult:
    """对比 Baseline 与 Treatment 的路径指标"""

    def _avg(values: list) -> float:
        return sum(values) / len(values) if values else 0.0

    # B1: 无效探索
    b_steps = [m.total_steps for m in baseline_metrics]
    t_steps = [m.total_steps for m in treatment_metrics]
    b_errors = [m.error_retries for m in baseline_metrics]
    t_errors = [m.error_retries for m in treatment_metrics]
    b_tools = [m.total_tool_calls for m in baseline_metrics]
    t_tools = [m.total_tool_calls for m in treatment_metrics]

    # B2: 决策熵
    b_sequences = [m.tool_sequence for m in baseline_metrics]
    t_sequences = [m.tool_sequence for m in treatment_metrics]
    b_entropy = compute_group_decision_entropy(b_sequences)
    t_entropy = compute_group_decision_entropy(t_sequences)

    # C: 效率成本
    b_tokens = [m.total_tokens for m in baseline_metrics]
    t_tokens = [m.total_tokens for m in treatment_metrics]
    b_latency = [m.latency_ms for m in baseline_metrics]
    t_latency = [m.latency_ms for m in treatment_metrics]

    return PathComparisonResult(
        skill_id=skill_id,
        baseline_avg_steps=_avg(b_steps),
        treatment_avg_steps=_avg(t_steps),
        delta_steps=_avg(t_steps) - _avg(b_steps),
        baseline_avg_errors=_avg(b_errors),
        treatment_avg_errors=_avg(t_errors),
        delta_errors=_avg(t_errors) - _avg(b_errors),
        baseline_avg_tool_calls=_avg(b_tools),
        treatment_avg_tool_calls=_avg(t_tools),
        delta_tool_calls=_avg(t_tools) - _avg(b_tools),
        baseline_decision_entropy=b_entropy,
        treatment_decision_entropy=t_entropy,
        delta_entropy=b_entropy - t_entropy,  # 正值=Treatment 更收敛
        baseline_avg_tokens=_avg(b_tokens),
        treatment_avg_tokens=_avg(t_tokens),
        delta_tokens=_avg(t_tokens) - _avg(b_tokens),
        baseline_avg_latency=_avg(b_latency),
        treatment_avg_latency=_avg(t_latency),
        delta_latency=_avg(t_latency) - _avg(b_latency),
    )
