#!/usr/bin/env bash
# D-252 baseline: Q (rally-d1s3cap8hr2 model_36793) zero-shot on the call-and-set test, dev 4220451, mean actions,
# 1,024 envs x 120 s. Reads only.
# PREDICTION (written 2026-11-09, before the read; the agent's, reported against the outcome):
#   headline pass (2.5 m/s) <= 0.05: Q needs 1.36 s for its first 1.5 m and the 2 m deadline is 1.3 s;
#   pace ladder 1.5 m/s 0.05-0.30, 2.0 m/s <= 0.15;
#   SET 0.3-0.7 (Q settles but not on a clock), READY <= 0.3 (the sided ready box was never trained),
#   REACH 0.3-0.7 (Q steers to the spot input, the stance spot); falls <= 2x Q's Measure60 3.55 per 1,000 env-s.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
unset PICKLEBOT_LAM_R PICKLEBOT_RES_BASE PICKLEBOT_LEG_R PICKLEBOT_TEACHER PICKLEBOT_TEACHER_GAIN PICKLEBOT_CONTROLLER
pgrep -f "run-name " > /dev/null && { echo "a trainer is running: not started"; exit 1; }
L=artifacts/train/logs/picklebot_return_stand; R=results/cs-base
export PICKLEBOT_RES_BASE=/mnt/f/dev/picklebot-mjlab/mjlab/$L/2026-10-31_18-24-20_s5c-d1-fw1bS/model_32854.pt PICKLEBOT_LAM_R=2
[ -s $R-Q-4220451.json ] || python scripts/diag/callset_eval.py --task Picklebot-Footwork-CallSet-RallyLamR2-G1 \
  --checkpoint $L/2026-11-07_19-25-03_rally-d1s3cap8hr2/model_36793.pt --envs 1024 --seconds 120 --seed 4220451 \
  --move-prob 1.0 --json $R-Q-4220451.json > $R-Q-4220451.log 2>&1
grep -a -E "CALL-AND-SET|per call type|\(reported\)|TARGET-LINES" $R-Q-4220451.log | tee $R-summary.txt
echo done > artifacts/train/cs-base.done
