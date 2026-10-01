#!/usr/bin/env bash
# Stage 0: short G1 flat-velocity training run to confirm mjlab trains on this machine.
# Usage (WSL): bash -l mjlab/scripts/stage0_velocity_smoke.sh [num_envs] [iterations]
set -euo pipefail
NUM_ENVS="${1:-4096}"
ITERS="${2:-300}"
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="$REPO/mjlab/artifacts/stage0"
mkdir -p "$OUT"
source "$HOME/envs/picklebot-mj/bin/activate"
export PYTHONWARNINGS=ignore
cd "$REPO/mjlab"
nvidia-smi --query-gpu=name,memory.used,memory.total --format=csv > "$OUT/gpu-before-$NUM_ENVS.csv"
START=$(date +%s)
train Mjlab-Velocity-Flat-Unitree-G1 \
  --env.scene.num-envs "$NUM_ENVS" \
  --agent.max-iterations "$ITERS" \
  --agent.logger tensorboard \
  --agent.seed 1 \
  --agent.run-name "smoke-$NUM_ENVS" \
  --log-root "$OUT/logs" \
  2>&1 | tee "$OUT/train-$NUM_ENVS.log"
END=$(date +%s)
echo "wall_seconds=$((END-START)) num_envs=$NUM_ENVS iterations=$ITERS" | tee "$OUT/summary-$NUM_ENVS.txt"
