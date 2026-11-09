#!/usr/bin/env bash
# D-252 baseline diagnostic: Q zero-shot on the call-and-set test with the reported parts at T (where the pelvis and paddle are), dev 4220452, mean actions,
# 1,024 envs x 120 s. Reads only.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
unset PICKLEBOT_LAM_R PICKLEBOT_RES_BASE PICKLEBOT_LEG_R PICKLEBOT_TEACHER PICKLEBOT_TEACHER_GAIN PICKLEBOT_CONTROLLER
pgrep -f "run-name " > /dev/null && { echo "a trainer is running: not started"; exit 1; }
L=artifacts/train/logs/picklebot_return_stand; R=results/cs-diag
export PICKLEBOT_RES_BASE=/mnt/f/dev/picklebot-mjlab/mjlab/$L/2026-10-31_18-24-20_s5c-d1-fw1bS/model_32854.pt PICKLEBOT_LAM_R=2
[ -s $R-Q-4220452.json ] || python scripts/diag/callset_eval.py --task Picklebot-Footwork-CallSet-RallyLamR2-G1 \
  --checkpoint $L/2026-11-07_19-25-03_rally-d1s3cap8hr2/model_36793.pt --envs 1024 --seconds 120 --seed 4220452 \
  --move-prob 1.0 --json $R-Q-4220452.json > $R-Q-4220452.log 2>&1
grep -a -E "CALL-AND-SET|per call type|\(reported\)|TARGET-LINES" $R-Q-4220452.log | tee $R-summary.txt
echo done > artifacts/train/cs-diag.done
