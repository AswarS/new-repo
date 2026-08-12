"""WebShop ReAct prompt 模板与动作解析"""

from __future__ import annotations

import re


# ===== Few-shot examples (WebShop ReAct 风格) =====

REACT_EXAMPLES = """Here are two examples of how to interact with WebShop.

----- Example 1 -----
Observation:
[Search]

Instruction:
i need a long clip-in hair extension which is natural looking

Action: search[natural looking long clip-in hair extension]

Observation:
[Back to Search]
Page 1 (Total results: 80)
[Next >]
[B078FWBPJL]
Natural Long Clip-In Hair Extensions, Synthetic Straight 24 inch
$14.99
[B09BVRT6K2]
Premium Clip-In Hair Extensions, Natural Look, 22 inch
$29.99
[B07D9SX3J8]
Thick Double Weft Clip-In Hair Extensions Set Natural Color 20 inch
$18.99

Action: click[B078FWBPJL]

Observation:
[Back to Search]
[< Prev]
Natural Long Clip-In Hair Extensions, Synthetic Straight 24 inch
Price: $14.99
Rating: N.A.
[Description]
[Features]
[Reviews]
[Attributes]
Color: Natural Black | Blonde | Dark Brown | Light Brown
Length: 20 inch | 22 inch | 24 inch
[Buy Now]

Action: click[Natural Black]

Observation:
You have clicked Natural Black.

Action: click[24 inch]

Observation:
You have clicked 24 inch.

Action: click[Buy Now]

----- Example 2 -----
Observation:
[Search]

Instruction:
i am looking for a grey sectional sofa for my living room

Action: search[grey sectional sofa living room]

Observation:
[Back to Search]
Page 1 (Total results: 50)
[Next >]
[B09KZL7FGR]
Modern Sectional Sofa, L-Shaped Couch, Grey Linen Fabric
$599.99
[B08PJ24BLS]
Reversible Sectional Sofa with Ottoman, Grey
$459.00

Action: click[B09KZL7FGR]

Observation:
[Back to Search]
[< Prev]
Modern Sectional Sofa, L-Shaped Couch, Grey Linen Fabric
Price: $599.99
Rating: 4.2 out of 5
[Description]
[Features]
[Reviews]
[Attributes]
Color: Dark Grey | Light Grey | Charcoal
Size: Standard | Large
[Buy Now]

Action: click[Light Grey]

Observation:
You have clicked Light Grey.

Action: click[Buy Now]

"""


def build_system_prompt() -> str:
    """构建 WebShop agent 的 system prompt。"""
    return (
        "You are a shopping assistant agent interacting with a web shopping environment. "
        "At each step, you will receive an observation (the current page content) and "
        "the task instruction. You must follow a strict Think → Skill → Verify → Act workflow.\n\n"
        "Valid actions:\n"
        "- search[query]: Search for products with the given query\n"
        "- click[element]: Click on an element on the page (product link, option, button)\n\n"
        "## Step-by-Step Workflow (MUST follow for every step)\n\n"
        "Each time you receive an observation, you MUST follow these steps IN ORDER:\n\n"
        "### Step 1: Think\n"
        "Analyze the current observation. What page are you on? What information is available? "
        "What does the task instruction require? What should you do next?\n\n"
        "### Step 2: Invoke Skill (if applicable)\n"
        "If you have an available skill that is relevant to the current step, invoke it via "
        "tool call. Skills provide expert guidance on how to handle specific situations "
        "(e.g., how to search, how to select options, how to verify prices).\n\n"
        "### Step 3: Verify Skill Compliance\n"
        "If you invoked a skill, you MUST read the skill's output carefully and verify that "
        "your planned action follows the skill's recommendations. Specifically:\n"
        "- What did the skill recommend?\n"
        "- Does my planned action match that recommendation?\n"
        "- If not, adjust my action to comply with the skill's guidance.\n\n"
        "**CRITICAL: If a skill tells you to do X, you MUST do X. The skill's output is "
        "authoritative guidance that overrides your default behavior. Do NOT ignore skill output.**\n\n"
        "### Step 4: Act\n"
        "Output exactly ONE action in the format: action[argument]\n\n"
        "## Skill Awareness\n\n"
        "Before starting the task, review your available skills and understand what each one "
        "is useful for (e.g., parsing the query, searching, evaluating results, inspecting a "
        "product page, selecting options, or purchasing). As you work through the task, use "
        "your judgment to identify the single point at which invoking a skill would provide "
        "the most value. You may invoke at most ONE skill for the entire task — choose the "
        "step where it matters most. If no skill is clearly useful at any point, complete the "
        "task without invoking one.\n\n"
        "## Action Rules\n"
        "- Your final output line MUST be ONLY the action: action[argument]\n"
        "- First search for relevant products based on the instruction\n"
        "- Then click on a product that matches the requirements\n"
        "- Select required options (color, size, etc.) before clicking Buy Now\n"
        "- Click [Buy Now] when you've found and configured the right product\n"
        "- Be efficient — find the best matching product quickly\n"
        "- Match ALL attributes mentioned in the instruction (color, size, price, etc.)\n"
    )


def _format_available_actions(available_actions: dict | None) -> str:
    """将 available_actions 格式化为提示文本"""
    if not available_actions:
        return ""
    parts = []
    if available_actions.get("has_search_bar"):
        parts.append("- search[query]: Search for products with the given query")
    clickables = available_actions.get("clickables", [])
    if clickables:
        items_str = ", ".join(clickables)
        parts.append(f"- click[element]: Click on a clickable element. Available elements: [{items_str}]")
    if not parts:
        return ""
    return "\n\nAvailable actions:\n" + "\n".join(parts) + "\n"


def build_first_message(observation: str, instruction: str, available_actions: dict | None = None) -> str:
    """构建发给 agent 的第一条消息（包含 few-shot + 首次观察 + 任务指令）"""
    actions_text = _format_available_actions(available_actions)
    return (
        # f"{REACT_EXAMPLES}\n"
        f"IMPORTANT REMINDER: The examples above are simplified demonstrations of the action format only. "
        f"In your actual execution, you MUST invoke the relevant skill (via tool call) before outputting each action. "
        f"Do NOT skip skill invocation.\n\n"
        f"CRITICAL: After invoking a skill, you MUST read and follow the skill's output. "
        f"The skill provides expert guidance — your action must comply with what the skill recommends. "
        f"If the skill says to search with specific keywords, use those keywords. "
        f"If the skill says to click a specific item, click that item. "
        f"Do NOT invoke a skill and then ignore its recommendation.\n\n"
        f"Now here is your task. Good luck!\n\n"
        f"Observation:\n{observation}\n"
        f"{actions_text}\n"
        f"Instruction:\n{instruction}\n"
    )


def build_step_message(observation: str, available_actions: dict | None = None) -> str:
    """构建后续步骤的环境反馈消息"""
    actions_text = _format_available_actions(available_actions)
    return (
        f"Observation:\n{observation}\n{actions_text}\n"
        f"Remember: Think first about what this observation tells you. "
        f"If you invoke a skill, you MUST follow its output — read the skill's recommendation "
        f"carefully and ensure your action complies with it. Then output your action."
    )


def parse_action(agent_response: str) -> str:
    """
    从 agent 回复中解析出动作。

    WebShop 动作格式: search[query] 或 click[element]

    Returns:
        解析后的动作字符串，或空字符串表示解析失败
    """
    if not agent_response:
        return ""

    text = agent_response.strip()

    # 匹配 action[argument] 格式
    # 支持 "Action: search[...]" 或直接 "search[...]"
    patterns = [
        r"(?:Action:\s*)?(?:action:\s*)?(search\[.+?\])",
        r"(?:Action:\s*)?(?:action:\s*)?(click\[.+?\])",
    ]

    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)
        if matches:
            # 返回最后一个匹配（agent 可能先 think 再给 action）
            return matches[-1]

    # 尝试从多行中逐行匹配
    lines = text.split("\n")
    for line in reversed(lines):
        stripped = line.strip()
        for pattern in patterns:
            m = re.search(pattern, stripped, re.IGNORECASE)
            if m:
                return m.group(1)

    # 兜底：检查是否整行就是 action 格式
    for line in reversed(lines):
        stripped = line.strip()
        if re.match(r"^(search|click)\[.+\]$", stripped, re.IGNORECASE):
            return stripped

    return ""
