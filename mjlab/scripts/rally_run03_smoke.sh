#!/usr/bin/env bash
# D-139 smoke (architecture): rally run 3 resumes rally-02-coop/model_6400 with its optimizer and no critic warm-up. Three
# PPO iterations at 1,024 envs (training seed 77; the checkpoints are never a parent): the iteration count continues
# from 6400 and the learning rate is the checkpoint's.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab
PICKLEBOT_CRITIC_WARMUP=0 PICKLEBOT_ENVS=1024 PICKLEBOT_WALL_CAP=900 bash scripts/train_run.sh rally-03-smoke Picklebot-Latent-Court-V2-Res-PPO-Clean-Mix-KeepAlive-Pairs-Coop-G1 \
  --agent.seed 77 --agent.max-iterations 3 --agent.resume True --agent.load-run 2026-10-21_20-50-34_rally-02-coop \
  --agent.load-checkpoint model_6400.pt
cat artifacts/train/rally-03-smoke.exit.json
grep -a -E "Learning iteration|Learning rate|Episode_Reward/partner_return|Traceback|Error" artifacts/train/rally-03-smoke.log | tail -9
grep -a -E "Learning rate" artifacts/train/rally-02-coop.log | tail -1
