#!/usr/bin/env bash
# README video for the user (2026-11-09): Q = rally-d1s3cap8hr2 model_36793 (D-243, CONFIRMED P(5+) 0.776 on the frozen
# set-start read). One court with both robots (picklebot_mj/pair_video.py), the set-start read protocol (contact hand-off,
# target A, mean actions, --pair-drill-reset), 8 envs (4 courts), 90 s, development seed 4220450. Clips chosen before
# rendering: q-first.mp4 (court 0, every rally in order, not picked) and q-longest.mp4 (the longest rally of the 4
# courts, picked and labelled so). No gate statistic.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
O=artifacts/videos/rallyQ; mkdir -p $O; L=artifacts/train/logs/picklebot_return_stand
export PICKLEBOT_RES_BASE=/mnt/f/dev/picklebot-mjlab/mjlab/$L/2026-10-31_18-24-20_s5c-d1-fw1bS/model_32854.pt PICKLEBOT_LAM_R=2
A="--task Picklebot-Latent-Court-Res-G1 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --rally --pairs --pair-handoff contact --envs 8 --seconds 90 --pair-video-courts 4 --pair-drill-reset"
python scripts/stage2_eval.py --checkpoint $L/2026-11-07_19-25-03_rally-d1s3cap8hr2/model_36793.pt $A --seed 4220450 --pair-video $O/q \
  --pair-video-caption "Rally model Q (current best): 77.6 % of rallies reach 5 good shots (target 80 %)" --json $O/q.json > $O/q.log 2>&1
echo "exit $?"; ls -la $O
