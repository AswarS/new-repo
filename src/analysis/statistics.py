"""统计分析模块"""

import math
import numpy as np
from scipy import stats


def mean_std(values: list[float]) -> tuple[float, float]:
    """计算均值和标准差"""
    if not values:
        return 0.0, 0.0
    arr = np.array(values, dtype=float)
    return float(np.mean(arr)), float(np.std(arr, ddof=1))


def confidence_interval_mean(values: list[float], confidence: float = 0.95) -> tuple[float, float]:
    """计算均值的置信区间（t 分布）"""
    if len(values) < 2:
        m = values[0] if values else 0.0
        return (m, m)
    arr = np.array(values, dtype=float)
    n = len(arr)
    mean = np.mean(arr)
    se = stats.sem(arr)
    h = se * stats.t.ppf((1 + confidence) / 2, n - 1)
    return (float(mean - h), float(mean + h))


def confidence_interval_proportion(successes: int, total: int, confidence: float = 0.95) -> tuple[float, float]:
    """计算比例的置信区间（Wilson score interval）"""
    if total == 0:
        return (0.0, 0.0)
    p = successes / total
    z = stats.norm.ppf((1 + confidence) / 2)
    denominator = 1 + z**2 / total
    center = (p + z**2 / (2 * total)) / denominator
    margin = (z / denominator) * math.sqrt(p * (1 - p) / total + z**2 / (4 * total**2))
    return (max(0.0, float(center - margin)), min(1.0, float(center + margin)))


def paired_significance_test(group_a: list[float], group_b: list[float]) -> float:
    """
    配对显著性检验。
    样本量 >= 30 时使用配对 t 检验，否则使用 Wilcoxon 符号秩检验。
    返回 p 值。
    """
    if len(group_a) < 2 or len(group_b) < 2:
        return 1.0

    # 取两组中较短的长度对齐
    min_len = min(len(group_a), len(group_b))
    a = np.array(group_a[:min_len], dtype=float)
    b = np.array(group_b[:min_len], dtype=float)

    # 如果两组完全相同
    if np.allclose(a, b):
        return 1.0

    if min_len >= 30:
        # 配对 t 检验
        _, p = stats.ttest_rel(a, b)
    else:
        # Wilcoxon 符号秩检验
        try:
            _, p = stats.wilcoxon(a, b)
        except ValueError:
            # 差值全为零时 wilcoxon 会报错
            p = 1.0

    return float(p)


def compute_decision_entropy(choices_per_run: list[list[str]]) -> float:
    """
    计算决策熵。

    参数:
      choices_per_run: 每次运行中关键决策点的选择序列
                       e.g., [["dirA", "dirB", "dirC"], ["dirA", "dirA", "dirC"], ...]

    返回:
      平均决策熵
    """
    if not choices_per_run:
        return 0.0

    # 转置：从按运行分组变为按决策点分组
    n_runs = len(choices_per_run)
    max_steps = max(len(run) for run in choices_per_run)

    entropies = []
    for step_idx in range(max_steps):
        # 收集该步骤各运行的选择
        step_choices = []
        for run in choices_per_run:
            if step_idx < len(run):
                step_choices.append(run[step_idx])

        if not step_choices:
            continue

        # 计算该步骤的香农熵
        from collections import Counter
        counts = Counter(step_choices)
        total = len(step_choices)
        entropy = 0.0
        for count in counts.values():
            p = count / total
            if p > 0:
                entropy -= p * math.log2(p)
        entropies.append(entropy)

    return float(np.mean(entropies)) if entropies else 0.0
