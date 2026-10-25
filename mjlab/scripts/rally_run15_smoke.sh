#!/usr/bin/env bash
# D-155 smoke: rally run 15's task resumes rally-14-lamr2/model_27798 with its optimizer and no critic warm-up. Forty PPO
# iterations at 1,024 envs (training seed 85; the checkpoints are never a parent); no new term; mean fell_over over the
# 40 iterations must be <= 1.5 x run 14 smoke's 0.106 (architecture, round 37).
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
PICKLEBOT_CRITIC_WARMUP=0 PICKLEBOT_ENVS=1024 PICKLEBOT_WALL_CAP=900 bash scripts/train_run.sh rally-15-smoke Picklebot-Latent-Court-V2-Res-PPO-Clean-Mix-KeepAlive-Pairs-Coop-Moves-Weak-Pace25-LamR3-G1 \
  --agent.seed 85 --agent.max-iterations 40 --agent.resume True --agent.load-run 2026-10-26_06-00-00_rally-15-lamr3-init \
  --agent.load-checkpoint model_27798.pt
cat artifacts/train/rally-15-smoke.exit.json
grep -a -E "Learning iteration|Episode_Reward/ball_out_over|Episode_Reward/Episode_Reward/legal_return|Episode_Reward/paddle_contact|Traceback|Error" artifacts/train/rally-15-smoke.log | tail -9
PICKLEBOT_LAM_R=3 bash scripts/stage2_eval.sh rally-15-lamr3-init model_27798.pt --task Picklebot-Latent-Court-Res-G1 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --rally --pairs --pair-handoff contact --envs 64 --seconds 10 --seed 4219702 --json /tmp/r15smoke.json > /tmp/r15s.log 2>&1; echo "eval: $?"; grep -a -E "Error|Traceback" /tmp/r15s.log | head -3
grep -a -o "Episode_Termination/fell_over: [0-9.]*" artifacts/train/rally-15-smoke.log | awk '{s+=$2;n++} END{m=s/n; print "fell_over mean", m, "over", n, (m <= 0.159 ? "ok" : "STOP")}'
