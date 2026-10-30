#!/usr/bin/env bash
# D-182 diagnostic (before panel round 52): deterministic (mean-action) reads of the footwork checkpoints on
# Picklebot-Footwork-Measure60-G1 through scripts/stage2_eval.py, to separate action noise from skill in held arrival.
# 1,024 envs, 120 s, development seeds 4220210 (fw1b-S model_16600) and 4220211 (fw1c-A last checkpoint). Diagnostic only:
# the pre-registered reads stay stochastic.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
unset PICKLEBOT_LAM_R PICKLEBOT_RES_BASE PICKLEBOT_LEG_R PICKLEBOT_TEACHER PICKLEBOT_TEACHER_GAIN PICKLEBOT_CONTROLLER
pgrep -f "run-name " > /dev/null && { echo "a trainer is running: not started"; exit 1; }
L=artifacts/train/logs/picklebot_return_stand
A=$(ls -d $L/*_fw1c-A | tail -1); ACK=$(ls $A/model_*.pt | sort -V | tail -1)
for pair in "4220210 $L/2026-10-31_01-16-15_fw1b-S/model_16600.pt B0" "4220211 $ACK A"; do
  set -- $pair
  python scripts/diag/footwork_eval.py --task Picklebot-Footwork-Measure60-G1 --checkpoint $2 --envs 1024 --seconds 120 \
    --seed $1 --move-prob 1.0 --json results/fw1c-det-$3.json 2>&1 | grep -v "^\[INFO\]\|^|\|^+" | tail -14
  echo "== $3 ($2) done"
done
echo done > artifacts/train/fw1c-det.done
