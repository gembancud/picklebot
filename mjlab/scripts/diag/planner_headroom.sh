#!/usr/bin/env bash
# Round 38 (coach, architecture): zero-code headroom read for the e4 teacher. Run 14's model_27798 (PICKLEBOT_LAM_R=2)
# in the M1 pair read (contact hand-off, 2,048 envs, 120 s) with the stance-spot planner as trained (task), clean (true
# state and spin, no delay) and off, all on seed 4219801; then the direction split with the planner as trained and
# clean on seed 4219802. Reported only; nothing is selected on it.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
export PICKLEBOT_LAM_R=2
R=results/planner-headroom; CK=artifacts/train/logs/picklebot_return_stand/2026-10-25_15-06-49_rally-14-lamr2/model_27798.pt
A="--task Picklebot-Latent-Court-Res-G1 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --rally --pairs --pair-handoff contact --envs 2048 --seconds 120 --seed 4219801"
for p in task clean off; do
  python scripts/stage2_eval.py --checkpoint $CK $A --planner $p --json $R-pairs-$p.json > /tmp/ph-$p.log 2>&1; echo "pairs $p: $?"
done
for p in task clean; do
  python scripts/diag/feeder_speed_envelope.py --checkpoint $CK --seed 4219802 --planner $p --json $R-dir-$p.json > /tmp/phd-$p.log 2>&1; echo "dir $p: $?"
done
