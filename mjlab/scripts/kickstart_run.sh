#!/usr/bin/env bash
# Capped kickstart run (loop rule: < 2 h). Usage: kickstart_run.sh RUN [kickstart_h4.py args...]
# Writes artifacts/train/RUN.{launch.json,log,exit.json}; checkpoints under artifacts/train/logs/picklebot_return_stand.
set -uo pipefail
RUN="${1:?run name}"; shift
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="$REPO/mjlab/artifacts/train"
source "$HOME/envs/picklebot-mj/bin/activate"
export PYTHONWARNINGS=ignore
cd "$REPO/mjlab"
echo "{\"run\": \"$RUN\", \"extra\": \"$*\", \"started\": \"$(date -Is)\", \"wall_cap_s\": 7100}" > "$OUT/$RUN.launch.json"
timeout 7100s python scripts/kickstart_h4.py --run-name "$RUN" --log-root "$OUT/logs/picklebot_return_stand" "$@" > "$OUT/$RUN.log" 2>&1 < /dev/null
CODE=$?
echo "{\"run\": \"$RUN\", \"exit_code\": $CODE, \"finished\": \"$(date -Is)\"}" > "$OUT/$RUN.exit.json"
