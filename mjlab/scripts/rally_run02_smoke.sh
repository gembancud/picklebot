#!/usr/bin/env bash
# D-137 smoke (architecture): cooperative credit (partner_return) has only run in tests. The tests, then three PPO iterations of rally
# run 1's task at 1,024 envs from the parent (training seed 77; the checkpoints are never a parent), with the realised
# feed shares.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab
bash -l scripts/test.sh tests/test_stage5f.py -k "d132 or d135 or d136 or d137 or pair_courts" -p no:logging 2>&1 | grep -v DEBUG | grep -E "passed|failed|^E " | head
PICKLEBOT_ENVS=1024 PICKLEBOT_WALL_CAP=900 bash scripts/train_run.sh rally-02-smoke Picklebot-Latent-Court-V2-Res-PPO-Clean-Mix-KeepAlive-Pairs-Coop-G1 \
  --agent.seed 77 --agent.max-iterations 20 --agent.resume True --agent.load-run 2026-10-21_09-25-54_s5h-04-pairs \
  --agent.load-checkpoint model_3398.pt
cat artifacts/train/rally-02-smoke.exit.json
grep -a -E "Iteration time|Episode_Reward/(legal_return|partner_return|placement)|Traceback|Error" artifacts/train/rally-02-smoke.log | tail -12
