#!/usr/bin/env bash
# Capped distillation run (loop rule: < 2 h). Usage: distill_run.sh RUN [distill.py args...]
# Writes artifacts/train/RUN.{launch.json,log,exit.json}; checkpoints under artifacts/train/logs/picklebot_return_stand/RUN.
set -uo pipefail
RUN="${1:?run name}"; shift
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="$REPO/mjlab/artifacts/train"
source "$HOME/envs/picklebot-mj/bin/activate"
export PYTHONWARNINGS=ignore
cd "$REPO/mjlab"
echo "{\"run\": \"$RUN\", \"extra\": \"$*\", \"started\": \"$(date -Is)\", \"wall_cap_s\": 7000}" > "$OUT/$RUN.launch.json"
timeout 7000s python scripts/distill.py --out "$OUT/logs/picklebot_return_stand/$RUN" "$@" > "$OUT/$RUN.log" 2>&1 < /dev/null
CODE=$?
echo "{\"run\": \"$RUN\", \"exit_code\": $CODE, \"finished\": \"$(date -Is)\"}" > "$OUT/$RUN.exit.json"
