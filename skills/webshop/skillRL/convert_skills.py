"""
将 claude_style_skills_webshop.json 中的每条 skill 转换为标准目录格式。
每个 skill 生成一个目录（以 skill_id 命名），内含 SKILL.MD 文件。

SKILL.MD 格式：
---
name: <title>
description: <when_to_apply（触发条件）>
---

# <Title>

<principle（具体内容）>
"""

import json
import os
import re

# 路径配置
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_PATH = os.path.join(SCRIPT_DIR, "claude_style_skills_webshop.json")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "skills_output")


def slugify(text: str) -> str:
    """将标题转换为 kebab-case 目录名"""
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


def write_skill(skill: dict, category: str = "general"):
    """将单条 skill 写入目录"""
    skill_id = skill["skill_id"]
    title = skill["title"]
    principle = skill["principle"]
    when_to_apply = skill["when_to_apply"]

    # 目录名：title 全小写，slugify 处理
    skill_name = slugify(title)
    dir_name = skill_name
    skill_dir = os.path.join(OUTPUT_DIR, dir_name)
    os.makedirs(skill_dir, exist_ok=True)

    # 生成 SKILL.MD
    content = f"""---
name: {skill_name}
description: {when_to_apply}
---

# {title}

{principle}
"""

    md_path = os.path.join(skill_dir, "SKILL.MD")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"  [OK] {dir_name} -> {title}")


def main():
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    count = 0

    # 处理 general_skills
    print("=== General Skills ===")
    for skill in data.get("general_skills", []):
        write_skill(skill, category="general")
        count += 1

    # 处理 task_specific_skills（按类别）
    for category, skills in data.get("task_specific_skills", {}).items():
        print(f"\n=== Task Specific: {category} ===")
        for skill in skills:
            write_skill(skill, category=category)
            count += 1

    print(f"\n完成！共处理 {count} 条 skill，输出目录: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
