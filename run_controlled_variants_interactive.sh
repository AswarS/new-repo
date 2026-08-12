#!/usr/bin/env bash
set -euo pipefail

repo_dir="/home/bwren/skill-eval"
webshop_dir="$repo_dir/benchmarks/WebShop"
backend_dir="$repo_dir/claude-code-backend"
variant_dir="$repo_dir/skills/webshop/controlled-variants"
run_tag="controlled_20260811"
output_root="$webshop_dir/output/$run_tag"
log_root="$webshop_dir/logs/$run_tag"
python_bin="/home/bwren/miniconda3/envs/webshop/bin/python"

mkdir -p "$output_root" "$log_root"
exec > >(tee -a "$log_root/queue.log") 2>&1

log() {
  printf '[%s] %s\n' "$(date '+%F %T')" "$*"
}

stop_backend() {
  local parent_pid="${1:-}"
  if [[ -n "$parent_pid" ]] && kill -0 "$parent_pid" 2>/dev/null; then
    kill -TERM "$parent_pid" 2>/dev/null || true
  fi
  sleep 2
  local listener_pid
  listener_pid="$(ss -ltnp 2>/dev/null | sed -n 's/.*:3199 .*pid=\([0-9][0-9]*\).*/\1/p' | head -1)"
  if [[ -n "$listener_pid" ]] && kill -0 "$listener_pid" 2>/dev/null; then
    kill -TERM "$listener_pid" 2>/dev/null || true
  fi
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

start_backend() {
  local variant="$1"
  local skill_path="$2"
  local backend_log="$log_root/${variant}.backend.log"
  cd "$backend_dir"
  log "Starting interactive-environment backend for $variant"
  bun run serve --port 3199 --add-dir "$skill_path" >"$backend_log" 2>&1 &
  backend_pid=$!

  local attempt
  for attempt in $(seq 1 60); do
    if "$python_bin" -c 'import urllib.request; urllib.request.urlopen("http://localhost:3199/health", timeout=2)' >/dev/null 2>&1; then
      return 0
    fi
    if ! kill -0 "$backend_pid" 2>/dev/null; then
      log "ERROR: backend exited for $variant"
      tail -n 80 "$backend_log" || true
      return 1
    fi
    sleep 2
  done
  log "ERROR: backend health timeout for $variant"
  return 1
}

probe_variant() {
  local variant="$1"
  local expected_skill="$2"
  local probe_output="$output_root/${variant}_smoke"
  local probe_log="$log_root/${variant}.smoke.log"
  rm -rf "$probe_output"
  mkdir -p "$probe_output"

  cd "$webshop_dir"
  log "Smoke testing $variant"
  "$python_bin" -u run_webshop_v2.py run --num 1 --task 0 --max-steps 30 --output "$probe_output" >"$probe_log" 2>&1

  if grep -q 'Not logged in' "$probe_log"; then
    log "ERROR: $variant backend is not logged in"
    return 1
  fi
  if ! grep -q "Skills: $expected_skill" "$probe_log"; then
    log "ERROR: expected exclusive skill $expected_skill not observed for $variant"
    grep 'Skills:' "$probe_log" || true
    return 1
  fi
  if ! grep -q 'Model:.*claude-opus-4-6' "$probe_log"; then
    log "ERROR: unexpected model for $variant"
    grep 'Model:' "$probe_log" || true
    return 1
  fi
  if [[ ! -f "$probe_output/task_0000.trajectory.json" ]]; then
    log "ERROR: smoke trajectory missing for $variant"
    return 1
  fi
  log "Smoke test passed for $variant"
}

run_repetition() {
  local variant="$1"
  local repetition="$2"
  local run_name="${variant}_rep${repetition}"
  local run_output="$output_root/$run_name"
  local run_log="$log_root/${run_name}.log"

  if [[ -f "$run_output/summary.json" ]]; then
    local existing_count
    existing_count="$(find "$run_output" -maxdepth 1 -name 'task_*.trajectory.json' -type f | wc -l)"
    if [[ "$existing_count" -eq 50 ]]; then
      log "Skipping already complete $run_name"
      return 0
    fi
  fi

  mkdir -p "$run_output"
  cd "$webshop_dir"
  log "Running $run_name"
  "$python_bin" -u run_webshop_v2.py run --num 50 --max-steps 30 --output "$run_output" >"$run_log" 2>&1

  local trajectory_count
  trajectory_count="$(find "$run_output" -maxdepth 1 -name 'task_*.trajectory.json' -type f | wc -l)"
  if [[ "$trajectory_count" -ne 50 || ! -f "$run_output/summary.json" ]]; then
    log "ERROR: incomplete $run_name trajectories=$trajectory_count"
    return 1
  fi
  if grep -q 'Not logged in' "$run_log"; then
    log "ERROR: login failure in $run_name"
    return 1
  fi
  "$python_bin" -c 'import json,sys; d=json.load(open(sys.argv[1])); print(json.dumps({k:d.get(k) for k in ("model","total_tasks","completed","errors","avg_reward","reward_eq_1.0","avg_steps")}))' "$run_output/summary.json" | tee "$log_root/${run_name}.result.json"
  log "Completed $run_name"
}

variants=(
  "v0|$variant_dir/webshop-v0-common-control|webshop-v0-common-control"
  "v1|$variant_dir/webshop-v1-constraint-ledger|webshop-v1-constraint-ledger"
  "v2|$variant_dir/webshop-v2-enforced-loop|webshop-v2-enforced-loop"
  "v3|$variant_dir/webshop-v3-explicit-state|webshop-v3-explicit-state"
  "v4|$variant_dir/webshop-v4-option-gate|webshop-v4-option-gate"
)

log "Controlled variant queue started in TTY $(tty)"
stop_backend ""

for entry in "${variants[@]}"; do
  IFS='|' read -r variant skill_path expected_skill <<<"$entry"
  start_backend "$variant" "$skill_path"
  probe_variant "$variant" "$expected_skill"
  run_repetition "$variant" 1
  run_repetition "$variant" 2
  stop_backend "$backend_pid"
done

log "ALL CONTROLLED VARIANT RUNS COMPLETED"
