#!/usr/bin/env bash
set -euo pipefail

repo_dir="/home/bwren/skill-eval"
webshop_dir="$repo_dir/benchmarks/WebShop"
backend_dir="$repo_dir/claude-code-backend"
skills_dir="$repo_dir/skills/webshop"
python_bin="/home/bwren/miniconda3/envs/webshop/bin/python"
bun_bin="/home/bwren/.bun/bin/bun"
queue_stamp="$(date +%Y%m%d_%H%M%S)"
queue_log_dir="$webshop_dir/logs/queue_$queue_stamp"
queue_output_dir="$webshop_dir/output/queue_$queue_stamp"
current_runner_pid="${1:-1922166}"
current_backend_parent_pid="${2:-1920923}"
current_output_dir="${3:-$webshop_dir/output/run_20260811_150957}"

mkdir -p "$queue_log_dir" "$queue_output_dir"
exec > >(tee -a "$queue_log_dir/queue.log") 2>&1

log() {
  printf '[%s] %s\n' "$(date '+%F %T')" "$*"
}

wait_for_pid() {
  local target_pid="$1"
  while kill -0 "$target_pid" 2>/dev/null; do
    sleep 30
  done
}

wait_for_port_free() {
  local attempt
  for attempt in $(seq 1 30); do
    if ! ss -ltn | grep -q ':3199 '; then
      return 0
    fi
    sleep 1
  done
  log "ERROR: port 3199 did not become free"
  return 1
}

stop_backend() {
  local parent_pid="${1:-}"
  if [[ -n "$parent_pid" ]] && kill -0 "$parent_pid" 2>/dev/null; then
    log "Stopping backend parent PID $parent_pid"
    kill -TERM "$parent_pid" 2>/dev/null || true
  fi

  local listener_pid
  listener_pid="$(ss -ltnp 2>/dev/null | sed -n 's/.*:3199 .*pid=\([0-9][0-9]*\).*/\1/p' | head -1)"
  if [[ -n "$listener_pid" ]] && kill -0 "$listener_pid" 2>/dev/null; then
    log "Stopping backend listener PID $listener_pid"
    kill -TERM "$listener_pid" 2>/dev/null || true
  fi
  wait_for_port_free
}

start_backend() {
  local condition="$1"
  local skill_path="$2"
  local backend_log="$queue_log_dir/${condition}.backend.log"

  log "Starting backend for $condition with $skill_path"
  cd "$backend_dir"
  setsid "$bun_bin" run ./src/bootstrap-entry.ts serve --port 3199 --add-dir "$skill_path" \
    >"$backend_log" 2>&1 &
  backend_pid=$!

  local attempt
  for attempt in $(seq 1 60); do
    if "$python_bin" -c 'import urllib.request; urllib.request.urlopen("http://localhost:3199/health", timeout=2)' \
      >/dev/null 2>&1; then
      log "Backend healthy for $condition (PID $backend_pid)"
      return 0
    fi
    if ! kill -0 "$backend_pid" 2>/dev/null; then
      log "ERROR: backend exited for $condition"
      tail -n 80 "$backend_log" || true
      return 1
    fi
    sleep 2
  done
  log "ERROR: backend health timeout for $condition"
  return 1
}

verify_skill() {
  local condition="$1"
  local expected_skill="$2"
  local skill_probe="$queue_log_dir/${condition}.skills.json"

  cd "$webshop_dir"
  "$python_bin" -c 'import json; from run_webshop_v2 import check_agent_skills; print(json.dumps(check_agent_skills(3199)))' \
    >"$skill_probe"
  if ! grep -q "\"$expected_skill\"" "$skill_probe"; then
    log "ERROR: expected skill $expected_skill not loaded for $condition"
    cat "$skill_probe"
    return 1
  fi
  log "Verified skill $expected_skill for $condition"
}

run_condition() {
  local condition="$1"
  local skill_path="$2"
  local expected_skill="$3"
  local run_output="$queue_output_dir/$condition"
  local run_log="$queue_log_dir/${condition}.experiment.log"

  start_backend "$condition" "$skill_path"
  verify_skill "$condition" "$expected_skill"

  mkdir -p "$run_output"
  log "Running $condition"
  cd "$webshop_dir"
  set +e
  "$python_bin" run_webshop_v2.py run --num 50 --max-steps 30 --output "$run_output" \
    >"$run_log" 2>&1
  local run_status=$?
  set -e

  local trajectory_count
  trajectory_count="$(find "$run_output" -maxdepth 1 -name 'task_*.trajectory.json' -type f | wc -l)"
  if [[ "$run_status" -ne 0 || "$trajectory_count" -ne 50 || ! -f "$run_output/summary.json" ]]; then
    log "ERROR: $condition failed: status=$run_status trajectories=$trajectory_count summary=$([[ -f "$run_output/summary.json" ]] && echo yes || echo no)"
    tail -n 100 "$run_log" || true
    stop_backend "$backend_pid"
    return 1
  fi

  "$python_bin" -c 'import json,sys; p=sys.argv[1]; d=json.load(open(p)); print(json.dumps({k:d.get(k) for k in ("total_tasks","completed","errors","avg_reward","reward_eq_1.0","avg_steps")}))' \
    "$run_output/summary.json" | tee "$queue_log_dir/${condition}.result.json"
  log "Completed $condition with 50 trajectories"
  stop_backend "$backend_pid"
}

log "Queue initialized at $queue_output_dir"
if kill -0 "$current_runner_pid" 2>/dev/null; then
  log "Waiting for current Skill v2 runner PID $current_runner_pid"
  wait_for_pid "$current_runner_pid"
fi
log "Current Skill v2 runner has exited; preserving its existing output"
current_trajectory_count="$(find "$current_output_dir" -maxdepth 1 -name 'task_*.trajectory.json' -type f | wc -l)"
if [[ "$current_trajectory_count" -ne 50 || ! -f "$current_output_dir/summary.json" ]]; then
  log "ERROR: current Skill v2 did not complete cleanly: trajectories=$current_trajectory_count summary=$([[ -f "$current_output_dir/summary.json" ]] && echo yes || echo no)"
  exit 1
fi
log "Verified current Skill v2: 50 trajectories and summary.json"
stop_backend "$current_backend_parent_pid"

conditions=(
  "skillv1_rep1|$skills_dir/skillNet|webshop-action-executor"
  "v0_rep1|$skills_dir/controlled-variants/webshop-v0-common-control|webshop-v0-common-control"
  "v0_rep2|$skills_dir/controlled-variants/webshop-v0-common-control|webshop-v0-common-control"
  "v1_rep1|$skills_dir/controlled-variants/webshop-v1-constraint-ledger|webshop-v1-constraint-ledger"
  "v1_rep2|$skills_dir/controlled-variants/webshop-v1-constraint-ledger|webshop-v1-constraint-ledger"
  "v2_rep1|$skills_dir/controlled-variants/webshop-v2-enforced-loop|webshop-v2-enforced-loop"
  "v2_rep2|$skills_dir/controlled-variants/webshop-v2-enforced-loop|webshop-v2-enforced-loop"
  "v3_rep1|$skills_dir/controlled-variants/webshop-v3-explicit-state|webshop-v3-explicit-state"
  "v3_rep2|$skills_dir/controlled-variants/webshop-v3-explicit-state|webshop-v3-explicit-state"
  "v4_rep1|$skills_dir/controlled-variants/webshop-v4-option-gate|webshop-v4-option-gate"
  "v4_rep2|$skills_dir/controlled-variants/webshop-v4-option-gate|webshop-v4-option-gate"
)

for entry in "${conditions[@]}"; do
  IFS='|' read -r condition skill_path expected_skill <<<"$entry"
  run_condition "$condition" "$skill_path" "$expected_skill"
done

log "ALL QUEUED EXPERIMENTS COMPLETED"
