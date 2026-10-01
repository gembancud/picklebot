#!/usr/bin/env bash
# Verify the Stage 2 task trains end to end through mjlab's own CLI (a few PPO iterations).
set -uo pipefail
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="$REPO/mjlab/artifacts/stage2"
mkdir -p "$OUT"
source "$HOME/envs/picklebot-mj/bin/activate"
export PYTHONWARNINGS=ignore
cd "$REPO/mjlab"
train Picklebot-Return-Stand-G1 --env.scene.num-envs "${1:-1024}" --agent.max-iterations "${2:-5}" \
  --agent.logger tensorboard --agent.seed 1 --agent.run-name train-smoke --log-root "$OUT/logs" \
  > "$OUT/train-smoke.log" 2>&1
echo "exit=$?"
grep -E "Learning iteration|Mean reward|Mean episode length|Iteration time|Episode_Reward/(paddle_contact|legal_return|approach_ball)|Episode_Termination|Traceback|Error" "$OUT/train-smoke.log" | tail -40
