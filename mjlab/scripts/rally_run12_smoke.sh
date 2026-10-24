#!/usr/bin/env bash
# D-152 smoke: rally run 12's task resumes rally-10-pace25/model_21399 with its optimizer and no critic warm-up. Forty PPO
# iterations at 1,024 envs (training seed 82; the checkpoints are never a parent); the new term must log a negative
# reward.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
PICKLEBOT_CRITIC_WARMUP=0 PICKLEBOT_ENVS=1024 PICKLEBOT_WALL_CAP=900 bash scripts/train_run.sh rally-12-smoke Picklebot-Latent-Court-V2-Res-PPO-Clean-Mix-KeepAlive-Pairs-Coop-Moves-Weak-Pace25-LegRes-G1 \
  --agent.seed 82 --agent.max-iterations 40 --agent.resume True --agent.load-run 2026-10-25_03-30-00_rally-12-legres-init \
  --agent.load-checkpoint model_21399.pt
cat artifacts/train/rally-12-smoke.exit.json
grep -a -E "Learning iteration|Episode_Reward/ball_out_over|Episode_Reward/Episode_Reward/legal_return|Episode_Reward/paddle_contact|Traceback|Error" artifacts/train/rally-12-smoke.log | tail -9
PICKLEBOT_LEG_R=0.1 bash scripts/stage2_eval.sh rally-12-legres-init model_21399.pt --task Picklebot-Latent-Court-Res-G1 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --rally --pairs --pair-handoff contact --envs 64 --seconds 10 --seed 4219402 --json /tmp/r12smoke.json > /tmp/r12s.log 2>&1; echo "eval: $?"; grep -a -E "Error|Traceback" /tmp/r12s.log | head -3
