#!/usr/bin/env bash
# scripts/train_run.sh for the agility screen tasks: identical, except that it starts scripts/diag/agility_train.py (which
# registers picklebot_mj/tasks/agility.py, then calls mjlab's train entry point) instead of the `train` console script.
# Usage: agility_train_run.sh RUN_NAME TASK_ID [extra train args...]
# Writes artifacts/train/RUN.{launch.json,env,log,exit.json}; checkpoints under artifacts/train/logs/.
set -uo pipefail
RUN="${1:?run name}"; TASK="${2:?task id}"; shift 2
REPO="$(cd "$(dirname "$0")/../../.." && pwd)"
OUT="$REPO/mjlab/artifacts/train"
mkdir -p "$OUT"
source "$HOME/envs/picklebot-mj/bin/activate"
export PYTHONWARNINGS=ignore
export TORCH_ALLOW_TF32_CUBLAS_OVERRIDE=1  # TF32 matmuls (D-086)
cd "$REPO/mjlab"
echo "{\"run\": \"$RUN\", \"task\": \"$TASK\", \"envs\": \"${PICKLEBOT_ENVS:-4096}\", \"extra\": \"$*\", \"started\": \"$(date -Is)\", \"wall_cap_s\": ${PICKLEBOT_WALL_CAP:-7000}, \"entry\": \"scripts/diag/agility_train.py\"}" > "$OUT/$RUN.launch.json"
env | grep "^PICKLEBOT_" | sort > "$OUT/$RUN.env"
timeout "${PICKLEBOT_WALL_CAP:-7000}s" python scripts/diag/agility_train.py "$TASK" --env.scene.num-envs "${PICKLEBOT_ENVS:-4096}" \
  --agent.save-interval 100 --agent.logger tensorboard --agent.run-name "$RUN" --log-root "$OUT/logs" "$@" > "$OUT/$RUN.log" 2>&1 < /dev/null
CODE=$?
echo "{\"run\": \"$RUN\", \"exit_code\": $CODE, \"finished\": \"$(date -Is)\"}" > "$OUT/$RUN.exit.json"
