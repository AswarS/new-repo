"""ALFWorld ReAct prompt 模板与动作解析"""

from __future__ import annotations

import re


# ===== Few-shot examples (来自 ALFWorld ReAct 论文) =====

REACT_EXAMPLES = """Here are two examples.

----- Example 1 -----
You are in the middle of a room. Looking quickly around you, you see a cabinet 6, a cabinet 5, a cabinet 4, a cabinet 3, a cabinet 2, a cabinet 1, a coffeemachine 1, a countertop 3, a countertop 2, a countertop 1, a drawer 3, a drawer 2, a drawer 1, a fridge 1, a garbagecan 1, a microwave 1, a shelf 3, a shelf 2, a shelf 1, a sinkbasin 1, a stoveburner 4, a stoveburner 3, a stoveburner 2, a stoveburner 1, a toaster 1.
Your task is to: put a clean lettuce in diningtable.

> think: To solve the task, I need to find and take a lettuce, then clean it with sinkbasin, then put it in diningtable.
OK.
> think: First I need to find a lettuce. A lettuce is more likely to appear in fridge 1, countertop 1, countertop 2, countertop 3. I'll check them one by one.
OK.
> go to fridge 1
You open the fridge 1. The fridge 1 is open. In it, you see a cup 1, a egg 2, a potato 3, a potato 2.
> go to countertop 1
On the countertop 1, you see a bread 1, a fork 1, a lettuce 1.
> take lettuce 1 from countertop 1
You pick up the lettuce 1 from the countertop 1.
> go to sinkbasin 1
On the sinkbasin 1, you see a apple 1, a ladle 2, a spoon 1.
> clean lettuce 1 with sinkbasin 1
You clean the lettuce 1 using the sinkbasin 1.
> go to diningtable 1
On the diningtable 1, you see a apple 3, a bread 2, a butterknife 2, a cup 2, a fork 2, a knife 2, a ladle 1, a mug 2, a peppershaker 1, a plate 1, a soapbottle 2, a spatula 3, a spoon 3, a tomato 1, a winebottle 1.
> put lettuce 1 in/on diningtable 1
You put the lettuce 1 in/on the diningtable 1.

----- Example 2 -----
You are in the middle of a room. Looking quickly around you, you see a bed 1, a desk 2, a desk 1, a drawer 6, a drawer 5, a drawer 4, a drawer 3, a drawer 2, a drawer 1, a garbagecan 1, a laundryhamper 1, a safe 1, a shelf 6, a shelf 5, a shelf 4, a shelf 3, a shelf 2, a shelf 1, a sidetable 1.
Your task is to: look at bowl under the desklamp.

> think: To solve the task, I need to find and take a bowl, then find a desklamp and use it.
OK.
> think: First I need to find a bowl. A bowl is more likely to appear in drawer 1-6, desk 1-2, shelf 1-6, sidetable 1. I'll check them one by one.
OK.
> go to desk 1
On the desk 1, you see a book 1, a cellphone 3, a pen 2.
> go to desk 2
On the desk 2, you see a alarmclock 2, a bowl 2, a cd 1, a cellphone 1, a creditcard 1, a desklamp 1, a keychain 2, a pen 1.
> think: Now I find a bowl 2 and a desklamp 1. I need to take the bowl and use the desklamp.
OK.
> take bowl 2 from desk 2
You pick up the bowl 2 from the desk 2.
> use desklamp 1
You turn on the desklamp 1.

"""


def build_system_prompt(skill_content: str = "") -> str:
    """
    构建 ALFWorld agent 的 system prompt。

    Args:
        skill_content: 可选的 Skill 内容注入
    """
    base = (
        "Interact with a household to solve a task. "
        "At each step, you will receive an observation from the environment "
        "along with a list of admissible commands you can execute. "
        "You must choose exactly ONE action from the admissible commands, "
        "or use 'think: {reasoning}' for internal reasoning before acting.\n\n"
        "Rules:\n"
        "- Respond with ONLY the action, prefixed with '> '.\n"
        "- Only use actions from the provided admissible commands list.\n"
        "- Use 'think: ...' for internal reasoning before acting.\n"
        "- Do not repeat failed actions.\n"
        "- Be efficient — minimize unnecessary exploration.\n"
    )

    if skill_content:
        base += (
            "\n---\n"
            "## Additional Knowledge (Skill)\n\n"
            f"{skill_content}\n"
            "---\n"
        )

    return base


def build_first_message(task_observation: str, admissible_commands: list[str] = None) -> str:
    """构建发给 agent 的第一条消息（包含 few-shot + 首次观察）"""
    msg = (
        f"{REACT_EXAMPLES}\n"
        f"Now here is your task. Good luck!\n\n"
        f"{task_observation}\n"
    )
    if admissible_commands:
        msg += f"\nAdmissible commands: {', '.join(admissible_commands)}\n"
    return msg


def build_step_message(observation: str, admissible_commands: list[str] = None) -> str:
    """构建后续步骤的环境反馈消息"""
    if admissible_commands:
        return f"{observation}\nAdmissible commands: {', '.join(admissible_commands)}"
    return observation


def parse_action(agent_response: str) -> str:
    """
    从 agent 回复中解析出动作。

    agent 回复可能包含思考过程和动作，需要提取最终动作。
    格式预期: "> action" 或 "action" 或混合文本中包含动作行。

    Returns:
        解析后的动作字符串，或空字符串表示解析失败
    """
    if not agent_response:
        return ""

    text = agent_response.strip()

    # 尝试匹配 "> action" 格式的行
    lines = text.split("\n")

    # 从后往前找最后一个以 > 开头的行（排除 think:）
    action_lines = []
    for line in reversed(lines):
        stripped = line.strip()
        if stripped.startswith(">"):
            action = stripped[1:].strip()
            if not action.startswith("think:"):
                return action
            action_lines.append(action)

    # 如果只有 think 行，返回最后一个 think
    if action_lines:
        return action_lines[0]

    # 没有 > 前缀，尝试直接匹配动作模式
    action_patterns = [
        r"^(go to .+)$",
        r"^(take .+ from .+)$",
        r"^(put .+ (?:in|on) .+)$",
        r"^(open .+)$",
        r"^(close .+)$",
        r"^(use .+)$",
        r"^(clean .+ with .+)$",
        r"^(heat .+ with .+)$",
        r"^(cool .+ with .+)$",
        r"^(examine .+)$",
        r"^(look)$",
        r"^(inventory)$",
        r"^(think: .+)$",
    ]

    for line in reversed(lines):
        stripped = line.strip().lower()
        for pattern in action_patterns:
            m = re.match(pattern, stripped, re.IGNORECASE)
            if m:
                return line.strip()

    # 兜底：返回最后一个非空行
    for line in reversed(lines):
        if line.strip():
            return line.strip()

    return text
