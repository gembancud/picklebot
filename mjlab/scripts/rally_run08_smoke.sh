#!/usr/bin/env bash
# D-145 smoke: rally run 8's task resumes rally-05-weak/model_15000 with its optimizer and no critic warm-up. Three PPO
# iterations at 1,024 envs (training seed 78; the checkpoints are never a parent); the new term must log a negative
# reward. Then a short pairs read (64 envs, 10 s, development seed 4218815) must print the new fast-share diagnostic.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
PICKLEBOT_CRITIC_WARMUP=0 PICKLEBOT_ENVS=1024 PICKLEBOT_WALL_CAP=900 bash scripts/train_run.sh rally-08-smoke Picklebot-Latent-Court-V2-Res-PPO-Clean-Mix-KeepAlive-Pairs-Coop-Moves-Weak-Pace-G1 \
  --agent.seed 78 --agent.max-iterations 3 --agent.resume True --agent.load-run 2026-10-22_23-28-36_rally-05-weak \
  --agent.load-checkpoint model_15000.pt
cat artifacts/train/rally-08-smoke.exit.json
grep -a -E "Learning iteration|Episode_Reward/ball_out_over|Episode_Reward/legal_return|Episode_Reward/paddle_contact|Traceback|Error" artifacts/train/rally-08-smoke.log | tail -12
bash scripts/stage2_eval.sh rally-05-weak model_15000.pt --task Picklebot-Latent-Court-Res-G1 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --rally --pairs --pair-handoff contact --envs 64 --seconds 10 --seed 4218815 --json /tmp/r08smoke.json > /tmp/r08s.log 2>&1; echo "eval: $?"
python -c "import json; d=json.load(open('/tmp/r08smoke.json'))['contact_diagnostics']; print(d['ball_speed_out_mean'], d['ball_out_share_above_11'], d['first_contacts'])"
