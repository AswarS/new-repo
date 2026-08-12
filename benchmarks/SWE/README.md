# SWE Runner — 本地 SWE 任务执行器

使用 Claude Code CLI 在本地 repo 上解决 SWE-bench 任务，每次代码修改自动 git commit，构建可追溯的 agent 轨迹分叉树。

## 前置条件

1. **Claude Code CLI** 已安装且在 PATH 中
   ```bash
   npm install -g @anthropic-ai/claude-code
   ```

2. **Python 3.9+**

3. 本地已 clone 好目标 repo（放在 `repos/` 目录下）

## 目录结构

```
repos/
├── django__django/          # 以 instance_id 前缀命名
├── astropy__astropy/
├── requests__requests/
└── ...

swe-runner/
├── run_swe.py               # 主入口
├── auto_commit_hook.py      # PostToolUse hook
├── trajectory.py            # 轨迹收集
└── output/                  # 输出目录（自动创建）
```

Repo 目录命名支持多种约定：
- `repos/django__django` （推荐，双下划线）
- `repos/django/django` （嵌套目录）
- `repos/django-django` （短横线）

## 快速开始

```bash
# 运行单个 instance
python swe-runner/run_swe.py \
  -d swe_data/swe-bench-lite_test.jsonl \
  --repos-dir ./repos \
  -i django__django-12345

# 运行前 5 个 instance
python swe-runner/run_swe.py \
  -d swe_data/swe-bench-lite_test.jsonl \
  --repos-dir ./repos \
  -n 5 --verbose

# 运行全部
python swe-runner/run_swe.py \
  -d swe_data/swe-bench-lite_test.jsonl \
  --repos-dir ./repos
```

## 参数说明

| 参数 | 简写 | 说明 |
|------|------|------|
| `--data` | `-d` | SWE-bench JSONL 文件路径（必填） |
| `--repos-dir` | | 存放 clone 好的 repo 的目录（必填） |
| `--instance` | `-i` | 只运行指定 instance ID |
| `--num` | `-n` | 运行前 N 个实例（0=全部） |
| `--output` | `-o` | 输出目录（默认 `swe-runner/output/`） |
| `--model` | `-m` | 指定模型（如 sonnet, opus） |
| `--max-turns` | | 最大对话轮次（0=不限） |
| `--allowed-tools` | | 允许的工具（默认 Edit,Write,Read,Bash,Glob,Grep） |
| `--system-prompt` | `-s` | 附加 system prompt |
| `--verbose` | `-v` | 实时显示 Claude Code 输出 |
| `--no-cleanup` | | 运行后不清理临时 hook 配置 |

## 工作流程

```
run_swe.py 对每个 instance:

1. 从 JSONL 读取 instance（含 problem_statement, base_commit, repo）
2. 在 repos/ 目录下定位对应 repo
3. git checkout <base_commit>
4. git checkout -b swe-run/<instance-id>-<timestamp>
5. 写入 .claude/settings.local.json（PostToolUse hook）
6. 启动 claude -p，发送 problem_statement
7. Claude Code 每次 Edit/Write → hook 自动 git commit
8. 完成后收集 git log → trajectory JSON
9. 清理临时文件
```

## 轨迹分叉树

运行后，每一步修改都是独立 commit：

```bash
# 查看某个 instance 的所有步骤
git -C repos/django__django log --oneline swe-run/django__django-12345-*

# 从第 3 步分叉
git -C repos/django__django checkout <step3-commit>
git -C repos/django__django checkout -b swe-run/django__django-12345-fork-1

# 在分叉点重新尝试
python swe-runner/run_swe.py \
  -d swe_data/swe-bench-lite_test.jsonl \
  --repos-dir ./repos \
  -i django__django-12345
```

## 输出格式

`output/<instance-id>.trajectory.json`:

```json
{
  "instance_id": "django__django-12345",
  "branch": "swe-run/django__django-12345-20260803T120000",
  "task": "problem statement...",
  "steps": [
    {
      "step": 1,
      "commit_hash": "abc1234...",
      "message": "swe-step-001: Edit django/db/models.py",
      "diff": "...",
      "files_changed": ["django/db/models.py"],
      "timestamp": "2026-08-03T12:00:05+08:00"
    }
  ],
  "messages": [...],
  "total_steps": 5,
  "final_diff": "..."
}
```

## 准备 Repos

可以用脚本批量 clone：

```bash
# 从 JSONL 提取所有 repo，去重后 clone
python -c "
import json
repos = set()
for line in open('swe_data/swe-bench-lite_test.jsonl'):
    d = json.loads(line)
    repos.add(d['repo'])
for r in sorted(repos):
    owner, name = r.split('/')
    print(f'git clone https://github.com/{r} repos/{owner}__{name}')
" | bash
```
