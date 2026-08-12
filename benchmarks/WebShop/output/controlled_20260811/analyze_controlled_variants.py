import json
import math
import random
import re
import statistics
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "benchmarks" / "WebShop" / "result" / "controlled_20260811"
OUT_JSON = DATA / "controlled_variants_analysis.json"
OUT_MD = DATA / "controlled_variants_analysis.md"
GOLD = DATA / "ground_truth_top50.json"

RUNS = [f"v{v}_rep{r}" for v in range(5) for r in (1, 2)]
ASIN_RE = re.compile(r"^click\[([a-z0-9]{10})\]$", re.I)
SEARCH_RE = re.compile(r"^search\[(.*)\]$", re.I | re.S)
CLICK_RE = re.compile(r"^click\[(.*)\]$", re.I | re.S)
NAV = {
    "buy now", "description", "features", "reviews", "< prev", "prev", "next >",
    "back to search", "search", "< previous", "previous", "next",
}


def mean(xs):
    return sum(xs) / len(xs) if xs else 0.0


def pstdev(xs):
    return statistics.pstdev(xs) if len(xs) > 1 else 0.0


def norm(s):
    return " ".join(s.lower().strip().split())


def tokenize(s):
    return set(re.findall(r"[a-z0-9]+", s.lower()))


def near_duplicate_queries(queries):
    total = 0
    for a, b in zip(queries, queries[1:]):
        aa, bb = tokenize(a), tokenize(b)
        if aa and bb and len(aa & bb) / len(aa | bb) >= 0.8:
            total += 1
    return total


def load_run(name):
    run_dir = DATA / name
    tasks = []
    for path in sorted(run_dir.glob("task_*.trajectory.json")):
        d = json.loads(path.read_text(encoding="utf-8"))
        actions = [x.get("action", "") for x in d.get("steps_log", [])]
        actions = [a for a in actions if a and a != "[DONE]"]
        queries = []
        asins = []
        option_clicks = []
        detail_checks = 0
        back_nav = 0
        purchase_idx = None
        for i, action in enumerate(actions):
            sm = SEARCH_RE.match(action)
            cm = CLICK_RE.match(action)
            if sm:
                queries.append(norm(sm.group(1)))
                continue
            if not cm:
                continue
            value = norm(cm.group(1))
            am = ASIN_RE.match(action)
            if am:
                asins.append(am.group(1).lower())
            elif value in {"description", "features", "reviews"}:
                detail_checks += 1
            elif value in {"< prev", "prev", "next >", "back to search", "search", "< previous", "previous", "next"}:
                back_nav += 1
            elif value == "buy now":
                purchase_idx = i
            else:
                option_clicks.append((i, value))

        q_counts = Counter(queries)
        a_counts = Counter(asins)
        repeated_actions = sum(1 for a, b in zip(actions, actions[1:]) if norm(a) == norm(b))
        tasks.append({
            "task_idx": d["task_idx"],
            "reward": float(d.get("reward", 0)),
            "steps": int(d.get("steps", 0)),
            "done": bool(d.get("done", False)),
            "error": d.get("error", ""),
            "max_steps_hit": int(d.get("steps", 0)) >= int(d.get("max_steps", 30)) and not d.get("done", False),
            "searches": len(queries),
            "exact_duplicate_queries": sum(c - 1 for c in q_counts.values() if c > 1),
            "near_duplicate_queries": near_duplicate_queries(queries),
            "candidate_opens": len(asins),
            "candidate_revisits": sum(c - 1 for c in a_counts.values() if c > 1),
            "consecutive_repeat_actions": repeated_actions,
            "detail_checks": detail_checks,
            "back_navigation": back_nav,
            "option_clicks": len(option_clicks),
            "option_before_purchase": int(purchase_idx is not None and any(i < purchase_idx for i, _ in option_clicks)),
            "purchased": int(purchase_idx is not None),
            "actions": actions,
        })
    return tasks


def summarize(tasks):
    numeric = [
        "reward", "steps", "searches", "exact_duplicate_queries", "near_duplicate_queries",
        "candidate_opens", "candidate_revisits", "consecutive_repeat_actions", "detail_checks",
        "back_navigation", "option_clicks", "option_before_purchase",
    ]
    out = {k: mean([t[k] for t in tasks]) for k in numeric}
    out.update({
        "n": len(tasks),
        "reward_eq_1": mean([t["reward"] == 1 for t in tasks]),
        "reward_ge_0_5": mean([t["reward"] >= 0.5 for t in tasks]),
        "done_rate": mean([t["done"] for t in tasks]),
        "error_rate": mean([bool(t["error"]) for t in tasks]),
        "max_steps_rate": mean([t["max_steps_hit"] for t in tasks]),
        "option_before_purchase_given_purchase": (
            sum(t["option_before_purchase"] for t in tasks) / sum(t["purchased"] for t in tasks)
            if sum(t["purchased"] for t in tasks) else 0
        ),
    })
    return out


def variant_summary(two_runs):
    pooled = two_runs[0] + two_runs[1]
    s = summarize(pooled)
    r1, r2 = summarize(two_runs[0]), summarize(two_runs[1])
    by1 = {x["task_idx"]: x for x in two_runs[0]}
    by2 = {x["task_idx"]: x for x in two_runs[1]}
    common = sorted(set(by1) & set(by2))
    s.update({
        "run_reward_gap": abs(r1["reward"] - r2["reward"]),
        "run_steps_gap": abs(r1["steps"] - r2["steps"]),
        "paired_reward_mad": mean([abs(by1[i]["reward"] - by2[i]["reward"]) for i in common]),
        "paired_steps_mad": mean([abs(by1[i]["steps"] - by2[i]["steps"]) for i in common]),
        "perfect_reward_agreement": mean([(by1[i]["reward"] == 1) == (by2[i]["reward"] == 1) for i in common]),
        "rep1": r1,
        "rep2": r2,
    })
    return s


def bootstrap_delta(base_runs, test_runs, key, seed=7, rounds=10000):
    rng = random.Random(seed)
    base_by = [{x["task_idx"]: x for x in run} for run in base_runs]
    test_by = [{x["task_idx"]: x for x in run} for run in test_runs]
    ids = sorted(set(base_by[0]) & set(base_by[1]) & set(test_by[0]) & set(test_by[1]))
    deltas = []
    per_task = {
        i: mean([test_by[0][i][key], test_by[1][i][key]]) - mean([base_by[0][i][key], base_by[1][i][key]])
        for i in ids
    }
    for _ in range(rounds):
        sample = [ids[rng.randrange(len(ids))] for _ in ids]
        deltas.append(mean([per_task[i] for i in sample]))
    deltas.sort()
    return {
        "delta": mean(list(per_task.values())),
        "ci95": [deltas[int(0.025 * rounds)], deltas[int(0.975 * rounds)]],
    }


runs = {name: load_run(name) for name in RUNS}
variants = {}
for v in range(5):
    variants[f"v{v}"] = variant_summary([runs[f"v{v}_rep1"], runs[f"v{v}_rep2"]])

effects = {}
for v in range(1, 5):
    effects[f"v{v}"] = {
        key: bootstrap_delta([runs["v0_rep1"], runs["v0_rep2"]], [runs[f"v{v}_rep1"], runs[f"v{v}_rep2"]], key)
        for key in ["reward", "steps", "exact_duplicate_queries", "near_duplicate_queries", "candidate_revisits", "option_clicks", "option_before_purchase"]
    }

gold = {x["task_idx"]: x for x in json.loads(GOLD.read_text(encoding="utf-8"))}
option_task_ids = sorted(i for i, x in gold.items() if x.get("goal_options"))
non_option_task_ids = sorted(i for i, x in gold.items() if not x.get("goal_options"))


def task_mean(run_a, run_b, task_idx, key):
    aa = {x["task_idx"]: x for x in run_a}
    bb = {x["task_idx"]: x for x in run_b}
    return mean([aa[task_idx][key], bb[task_idx][key]])


def subgroup_effect(variant, ids, key):
    vals = []
    for i in ids:
        base = task_mean(runs["v0_rep1"], runs["v0_rep2"], i, key)
        test = task_mean(runs[f"{variant}_rep1"], runs[f"{variant}_rep2"], i, key)
        vals.append(test - base)
    return mean(vals)


task_specific = {}
for v in ["v1", "v2", "v3", "v4"]:
    task_specific[v] = {
        "reward_delta_option_tasks": subgroup_effect(v, option_task_ids, "reward"),
        "reward_delta_non_option_tasks": subgroup_effect(v, non_option_task_ids, "reward"),
        "steps_delta_option_tasks": subgroup_effect(v, option_task_ids, "steps"),
        "steps_delta_non_option_tasks": subgroup_effect(v, non_option_task_ids, "steps"),
        "option_click_delta_option_tasks": subgroup_effect(v, option_task_ids, "option_clicks"),
        "option_before_purchase_delta_option_tasks": subgroup_effect(v, option_task_ids, "option_before_purchase"),
    }

win_loss = {}
for v in ["v1", "v2", "v3", "v4"]:
    ds = []
    for i in range(50):
        ds.append(task_mean(runs[f"{v}_rep1"], runs[f"{v}_rep2"], i, "reward") - task_mean(runs["v0_rep1"], runs["v0_rep2"], i, "reward"))
    win_loss[v] = {
        "better_tasks": sum(x > 1e-12 for x in ds),
        "same_tasks": sum(abs(x) <= 1e-12 for x in ds),
        "worse_tasks": sum(x < -1e-12 for x in ds),
    }

result = {"data_dir": str(DATA), "runs": {k: summarize(v) for k, v in runs.items()}, "variants": variants, "effects_vs_v0": effects, "option_task_ids": option_task_ids, "task_specific": task_specific, "win_loss_vs_v0": win_loss}
OUT_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

labels = {
    "v0": "共同流程（对照）", "v1": "约束账本", "v2": "强制循环控制",
    "v3": "显式状态", "v4": "选项门控",
}

lines = [
    "# WebShop v0–v4 控制变量实验分析",
    "",
    "## 实验完整性",
    "",
    "- 5 个条件，每个条件 2 次独立运行，每次 50 个相同任务，共 500 条正式轨迹。",
    "- 所有运行均使用 `claude-opus-4-6`，每个条件只注入对应的单一 Skill。",
    "- 以下分析不判断商品语义是否合理；reward 直接采用环境输出，行为指标直接从 action 序列计算。",
    "",
    "## 总体结果",
    "",
    "| 条件 | 维度 | Avg reward | Reward=1 | Avg steps | Done | Error | 两遍 reward 差 | 配对 reward MAD |",
    "|---|---|---:|---:|---:|---:|---:|---:|---:|",
]
for v in [f"v{i}" for i in range(5)]:
    s = variants[v]
    lines.append(f"| {v} | {labels[v]} | {s['reward']:.4f} | {s['reward_eq_1']:.1%} | {s['steps']:.2f} | {s['done_rate']:.1%} | {s['error_rate']:.1%} | {s['run_reward_gap']:.4f} | {s['paired_reward_mad']:.4f} |")

lines += [
    "",
    "## 行为结果",
    "",
    "| 条件 | 搜索数 | 完全重复查询 | 相邻近重复查询 | 候选重访 | 连续重复动作 | 详情检查 | 选项点击 | 购买前有选项点击 | 达到步数上限 |",
    "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
]
for v in [f"v{i}" for i in range(5)]:
    s = variants[v]
    lines.append(f"| {v} | {s['searches']:.2f} | {s['exact_duplicate_queries']:.2f} | {s['near_duplicate_queries']:.2f} | {s['candidate_revisits']:.2f} | {s['consecutive_repeat_actions']:.2f} | {s['detail_checks']:.2f} | {s['option_clicks']:.2f} | {s['option_before_purchase_given_purchase']:.1%} | {s['max_steps_rate']:.1%} |")

lines += ["", "## 相对 v0 的配对效应（两遍先按 task 求均值）", "", "| 条件 | Δ reward [95% CI] | Δ steps [95% CI] | Δ重复查询 | Δ候选重访 | Δ选项点击 |", "|---|---:|---:|---:|---:|---:|"]
for v in ["v1", "v2", "v3", "v4"]:
    e = effects[v]
    def fmt(k):
        z=e[k]; return f"{z['delta']:+.3f} [{z['ci95'][0]:+.3f}, {z['ci95'][1]:+.3f}]"
    lines.append(f"| {v} | {fmt('reward')} | {fmt('steps')} | {e['exact_duplicate_queries']['delta']:+.3f} | {e['candidate_revisits']['delta']:+.3f} | {e['option_clicks']['delta']:+.3f} |")

lines += [
    "",
    "## 任务特定评估：有 `goal_options` 的任务",
    "",
    f"标准答案中共有 {len(option_task_ids)} 个任务带 `goal_options`，其余 {len(non_option_task_ids)} 个任务不带。下表比较各变体相对 v0 的配对变化。",
    "",
    "| 条件 | 选项任务 Δreward | 非选项任务 Δreward | 选项任务 Δsteps | 非选项任务 Δsteps | 选项任务 Δ选项点击 | 选项任务 Δ购买前选项 |",
    "|---|---:|---:|---:|---:|---:|---:|",
]
for v in ["v1", "v2", "v3", "v4"]:
    x = task_specific[v]
    lines.append(f"| {v} | {x['reward_delta_option_tasks']:+.4f} | {x['reward_delta_non_option_tasks']:+.4f} | {x['steps_delta_option_tasks']:+.2f} | {x['steps_delta_non_option_tasks']:+.2f} | {x['option_click_delta_option_tasks']:+.2f} | {x['option_before_purchase_delta_option_tasks']:+.1%} |")

lines += ["", "## 相对 v0 的任务胜负数", "", "| 条件 | 改善任务 | 不变任务 | 下降任务 |", "|---|---:|---:|---:|"]
for v in ["v1", "v2", "v3", "v4"]:
    x = win_loss[v]
    lines.append(f"| {v} | {x['better_tasks']} | {x['same_tasks']} | {x['worse_tasks']} |")

ranked = sorted(variants.items(), key=lambda kv: (-kv[1]["reward"], kv[1]["steps"]))
lines += [
    "",
    "## 结论",
    "",
    f"1. **总体最佳是 {ranked[0][0]}（{labels[ranked[0][0]]}）**。相对 v0，v2 的 reward 增加 0.0537（95% CI [0.0092, 0.1028]），steps 减少 1.28（95% CI [-2.57, -0.16]）；它是唯一在两个核心指标上配对区间都不跨 0 的变体。",
    "2. v2 的机制不是简单消灭完全相同的 query——这种行为在 v0 本来就很少。更明确的变化是平均搜索数从 1.72 降至 1.36、返回/翻页动作从 1.18 降至 0.61、步数上限命中从 4% 降至 0%，说明硬边界促进了更早收敛与购买。",
    "3. v1 的 reward 小幅提高 0.0208，但区间跨 0；steps 反而增加 0.31，搜索数从 1.72 增至 2.29。约束账本可能改善部分决策内容，却同时诱发更充分甚至过度的搜索，不能作为优先优化维度。",
    "4. v3 的 reward 仅增加 0.0098，且完全重复查询、近重复查询和连续重复动作均高于 v0。显式状态不是充分条件；状态若不转化为可执行的禁止/切换规则，Agent 仍可能重复行动。",
    "5. v4 的总体 reward 增加 0.0352、Reward=1 达 42%（五组最高），且两遍 reward 差仅 0.005（最稳定）。它将购买前选项点击率从 50.0% 提高到 60.8%；在有 goal_options 的任务上减少 0.91 步，而在无选项任务上增加 0.17 步，因此应作为按任务触发的局部门控，而非全任务常驻流程。",
    "6. 维度优先级应为：**强制循环控制（通用核心） > 选项门控（任务特定核心） > 约束账本（候选辅助） > 显式状态记录（单独使用价值低）**。下一版 Skill 应以 v2 为骨架，仅在检测到 goal_options/可选规格时挂载 v4，并避免无条件加入 v1、v3 的额外认知流程。",
    "",
    "## 指标解释与限制",
    "",
    "- `完全重复查询`：同一任务内规范化后完全相同的 search query 重复次数。",
    "- `相邻近重复查询`：相邻查询 token Jaccard 相似度 ≥ 0.8 的次数。",
    "- `候选重访`：同一 ASIN 在同一任务中第二次及以后被点击的次数。",
    "- `选项点击`：排除 ASIN、导航、详情标签和 Buy Now 后的其他 click；可能包含少量非选项元素，因此用于版本间相对比较，不作为绝对真值。",
    "- 只有 50 个任务和 2 次重复。置信区间采用按 task 配对 bootstrap，用于描述不确定性，不等同于跨任务分布的最终外推。",
]
OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(OUT_JSON)
print(OUT_MD)
for v in variants:
    s=variants[v]
    print(v, round(s['reward'],4), round(s['steps'],2), round(s['exact_duplicate_queries'],2), round(s['candidate_revisits'],2), round(s['option_clicks'],2))
