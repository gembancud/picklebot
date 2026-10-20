#!/usr/bin/env bash
# Stage 5G E5 throughput probe (D-124 tooling iv): 50 PPO iterations of the E5 task at 4,096 envs from E3's endpoint
# (training seed 75; the probe checkpoints are never a parent). Bar: <= 3.5 s per iteration.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab
PICKLEBOT_WALL_CAP=1500 bash scripts/train_run.sh s5g-probe-ball2 Picklebot-Latent-TimedBall-PPO-G1 --agent.seed 75 \
  --agent.max-iterations 50 --agent.resume True --agent.load-run 2026-10-20_15-12-17_s5g-e3-timed-v3 \
  --agent.load-checkpoint model_39699.pt
cat artifacts/train/s5g-probe-ball2.exit.json
grep -a -v -i warn artifacts/train/s5g-probe-ball2.log | tail -60
