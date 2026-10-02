#!/usr/bin/env bash
# TensorBoard over every mjlab training run (Stage 2 runs and artifacts/train runs).
# From Windows: Start-Process wsl -WindowStyle Hidden -ArgumentList '-d','Ubuntu','--','bash','-l',
#   '/mnt/f/dev/picklebot-mjlab/mjlab/scripts/tensorboard.sh'      then open http://localhost:6006
set -uo pipefail
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
source "$HOME/envs/picklebot-mj/bin/activate"
A="$REPO/mjlab/artifacts"
exec tensorboard --port "${1:-6006}" --host localhost --reload_interval 30 \
  --logdir_spec "stage2:$A/stage2/logs,train:$A/train/logs" > "$A/tensorboard.log" 2>&1
