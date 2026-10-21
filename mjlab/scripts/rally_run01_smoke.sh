#!/usr/bin/env bash
# D-135 smoke (architecture): the contact hand-off has only run in tests. The tests, then three PPO iterations of rally
# run 1's task at 1,024 envs from the parent (training seed 77; the checkpoints are never a parent), with the realised
# feed shares.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab
bash -l scripts/test.sh tests/test_stage5f.py -k "d132 or d135 or pair_courts" -p no:logging 2>&1 | grep -v DEBUG | grep -E "passed|failed|^E " | head
PICKLEBOT_ENVS=1024 PICKLEBOT_WALL_CAP=900 bash scripts/train_run.sh rally-01-smoke Picklebot-Latent-Court-V2-Res-PPO-Clean-Mix-KeepAlive-Pairs-Contact-G1 \
  --agent.seed 77 --agent.max-iterations 3 --agent.resume True --agent.load-run 2026-10-21_09-25-54_s5h-04-pairs \
  --agent.load-checkpoint model_3398.pt
cat artifacts/train/rally-01-smoke.exit.json
grep -a -E "Iteration time|Episode_Reward/legal_return|feed|Traceback|Error" artifacts/train/rally-01-smoke.log | tail -12
