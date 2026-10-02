#!/usr/bin/env bash
# Generic capped training run (loop rule: < 2 h wall clock). Runs in the foreground; from Windows,
# launch as its own process: Start-Process wsl -WindowStyle Hidden -ArgumentList '-d','Ubuntu','--','bash','-l',
#   '/mnt/f/dev/picklebot-mjlab/mjlab/scripts/train_run.sh','RUN','TASK','EXTRA_ARGS...'
# Usage: train_run.sh RUN_NAME TASK_ID [extra train args...]
# Writes artifacts/train/RUN.{launch.json,log,exit.json}; checkpoints under artifacts/train/logs/.
set -uo pipefail
RUN="${1:?run name}"; TASK="${2:?task id}"; shift 2
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="$REPO/mjlab/artifacts/train"
mkdir -p "$OUT"
source "$HOME/envs/picklebot-mj/bin/activate"
export PYTHONWARNINGS=ignore
cd "$REPO/mjlab"
echo "{\"run\": \"$RUN\", \"task\": \"$TASK\", \"extra\": \"$*\", \"started\": \"$(date -Is)\", \"wall_cap_s\": 7000}" > "$OUT/$RUN.launch.json"
timeout 7000s train "$TASK" --env.scene.num-envs 4096 --agent.save-interval 100 --agent.logger tensorboard \
  --agent.run-name "$RUN" --log-root "$OUT/logs" "$@" > "$OUT/$RUN.log" 2>&1 < /dev/null
CODE=$?
echo "{\"run\": \"$RUN\", \"exit_code\": $CODE, \"finished\": \"$(date -Is)\"}" > "$OUT/$RUN.exit.json"
