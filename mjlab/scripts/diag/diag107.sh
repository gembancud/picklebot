#!/usr/bin/env bash
# Panel round 107 (a): a diagnostic read of the killed D-246 checkpoint (rally-d1s3q8w2b model_37040) against Q
# (rally-d1s3cap8hr2 model_36793) on the read mix. Reads only; no promotion, no training. Frozen set-start pairs for both
# on dev 4220438; the child's direction read on dev 4220435 (paired with Q's stage-0 read there, results/lc107-dirQ-4220435.json).
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
pgrep -f "run-name |stage2_eval|feeder_speed" > /dev/null && { echo "GPU busy: not started"; exit 1; }
L=artifacts/train/logs/picklebot_return_stand
BASE=/mnt/f/dev/picklebot-mjlab/mjlab/$L/2026-10-31_18-24-20_s5c-d1-fw1bS/model_32854.pt
Q=$(ls -d $L/*_rally-d1s3cap8hr2)/model_36793.pt
K=$(ls -d $L/*_rally-d1s3q8w2b)/model_37040.pt
for f in $BASE $Q $K; do [ -f $f ] || { echo "missing $f"; exit 1; }; done
PA="--task Picklebot-Latent-Court-Res-G1 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --rally --pairs --pair-handoff contact --envs 2048 --seconds 120 --pair-drill-reset"
R=results/diag107
onbase() { PICKLEBOT_RES_BASE=$BASE PICKLEBOT_LAM_R=2 "$@"; }
[ -s $R-K-pairs-4220438.json ] || onbase python scripts/stage2_eval.py --checkpoint $K $PA --seed 4220438 --json $R-K-pairs-4220438.json >> $R-reads.log 2>&1
[ -s $R-Q-pairs-4220438.json ] || onbase python scripts/stage2_eval.py --checkpoint $Q $PA --seed 4220438 --json $R-Q-pairs-4220438.json >> $R-reads.log 2>&1
[ -s $R-K-dir-4220435.json ] || onbase python scripts/diag/feeder_speed_envelope.py --checkpoint $K --seed 4220435 --json $R-K-dir-4220435.json >> $R-reads.log 2>&1
echo done > artifacts/train/diag107.done
