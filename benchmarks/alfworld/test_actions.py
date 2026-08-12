# test_admissible_commands.py

import sys
import yaml

from alfworld.agents.environment import get_environment


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(
            "用法: python test_admissible_commands.py <base_config.yaml>"
        )

    config_path = sys.argv[1]

    with open(config_path, "r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    # 强制使用支持 admissible_commands 的 TextWorld 环境
    config["env"]["type"] = "AlfredTWEnv"

    env_class = get_environment("AlfredTWEnv")
    env = env_class(config, train_eval="train")
    env = env.init_env(batch_size=1)

    observation, info = env.reset()

    print("Observation:")
    print(observation[0])

    print("\nInfo keys:")
    print(sorted(info.keys()))

    if "admissible_commands" not in info:
        raise RuntimeError(
            "测试失败：info 中没有 admissible_commands"
        )

    commands = list(info["admissible_commands"][0])

    print(f"\n测试成功，共有 {len(commands)} 条可执行命令：")
    for command in commands:
        print(f"- {command}")

    # 验证其中一条命令确实可以执行
    action = commands[0]
    print(f"\n执行第一条命令: {action!r}")

    next_observation, scores, dones, next_info = env.step([action])

    print("执行结果:")
    print(next_observation[0])

    assert "admissible_commands" in next_info
    print(
        "\n下一状态可执行命令数:",
        len(next_info["admissible_commands"][0]),
    )


if __name__ == "__main__":
    main()
