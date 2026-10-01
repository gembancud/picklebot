#!/usr/bin/env bash
# Stage 2 first training run, hard-capped at < 2 h wall clock (loop rule).
# Usage (WSL): bash -l mjlab/scripts/stage2_train.sh RUN_NAME [num_envs] [max_iterations] [seed]
# Runs in the foreground (blocks). From Windows, launch it as its own process so it outlives
# the calling shell, e.g.:
#   Start-Process wsl -WindowStyle Hidden -ArgumentList '-d','Ubuntu','--','bash','-l','/mnt/f/dev/picklebot-mjlab/mjlab/scripts/stage2_train.sh','RUN'
# Follow mjlab/artifacts/stage2/<RUN_NAME>.log (or scripts/stage2_status.sh RUN_NAME).
set -uo pipefail
RUN="${1:?run name}"
NUM_ENVS="${2:-4096}"
ITERS="${3:-950}"
SEED="${4:-1}"
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="$REPO/mjlab/artifacts/stage2"
mkdir -p "$OUT"
source "$HOME/envs/picklebot-mj/bin/activate"
export PYTHONWARNINGS=ignore
cd "$REPO/mjlab"
echo "{\"run\": \"$RUN\", \"num_envs\": $NUM_ENVS, \"max_iterations\": $ITERS, \"seed\": $SEED, \"started\": \"$(date -Is)\", \"wall_cap_s\": 7000}" > "$OUT/$RUN.launch.json"
timeout 7000s train Picklebot-Return-Stand-G1 \
  --env.scene.num-envs "$NUM_ENVS" --agent.max-iterations "$ITERS" --agent.seed "$SEED" \
  --agent.save-interval 50 --agent.logger tensorboard --agent.run-name "$RUN" --log-root "$OUT/logs" \
  > "$OUT/$RUN.log" 2>&1 < /dev/null
CODE=$?
echo "{\"run\": \"$RUN\", \"exit_code\": $CODE, \"finished\": \"$(date -Is)\"}" > "$OUT/$RUN.exit.json"
