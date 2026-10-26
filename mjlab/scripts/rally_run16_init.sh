#!/usr/bin/env bash
# D-156: rally run 16's parent: rally-14 model_27798 with the actor's input widened 124 -> 129 (five zero columns for
# the trailing teacher_contact input, a (0, 1) normalizer prior, zero-padded Adam moments; the critic unchanged at 139).
set -euo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate
L=artifacts/train/logs/picklebot_return_stand; D=$L/2026-10-26_12-30-00_rally-16-teacher-init
mkdir -p $D
python scripts/expand_checkpoint.py $L/2026-10-25_15-06-49_rally-14-lamr2/model_27798.pt $D/model_27798.pt --actor-dim 129 --critic-dim 139
