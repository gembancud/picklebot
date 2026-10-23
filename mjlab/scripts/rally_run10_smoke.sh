#!/usr/bin/env bash
# D-149 smoke: rally run 10's task resumes rally-05-weak/model_15000 with its optimizer and no critic warm-up. Forty PPO
# iterations at 1,024 envs (training seed 80; the checkpoints are never a parent); the new term must log a negative
# reward.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
PICKLEBOT_CRITIC_WARMUP=0 PICKLEBOT_ENVS=1024 PICKLEBOT_WALL_CAP=900 bash scripts/train_run.sh rally-10-smoke Picklebot-Latent-Court-V2-Res-PPO-Clean-Mix-KeepAlive-Pairs-Coop-Moves-Weak-Pace25-G1 \
  --agent.seed 80 --agent.max-iterations 40 --agent.resume True --agent.load-run 2026-10-22_23-28-36_rally-05-weak \
  --agent.load-checkpoint model_15000.pt
cat artifacts/train/rally-10-smoke.exit.json
grep -a -E "Learning iteration|Episode_Reward/ball_out_over|Episode_Reward/legal_return|Episode_Reward/paddle_contact|Traceback|Error" artifacts/train/rally-10-smoke.log | tail -9
