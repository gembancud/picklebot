#!/usr/bin/env bash
# D-132 smoke (architecture): pair mode has only run in evaluation. Two PPO iterations of the run 4 task at 1,024 envs
# from run 1's endpoint (training seed 77; the checkpoints are never a parent), then the tests.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab
bash -l scripts/test.sh tests/test_stage5f.py -k "d132 or pair_courts" -p no:logging 2>&1 | grep -v DEBUG | grep -E "passed|failed|^E " | head
PICKLEBOT_ENVS=1024 PICKLEBOT_WALL_CAP=900 bash scripts/train_run.sh s5h-04-smoke Picklebot-Latent-Court-V2-Res-PPO-Clean-Mix-KeepAlive-Pairs-G1 \
  --agent.seed 77 --agent.max-iterations 3 --agent.resume True --agent.load-run 2026-10-21_00-50-33_s5h-01-keepalive \
  --agent.load-checkpoint model_2599.pt
cat artifacts/train/s5h-04-smoke.exit.json
grep -a -E "Iteration time|Episode_Reward/legal_return|Traceback|Error" artifacts/train/s5h-04-smoke.log | tail -6
