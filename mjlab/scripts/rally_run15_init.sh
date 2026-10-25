#!/usr/bin/env bash
# D-155: rally run 15's parent: rally-14 model_27798 with the latent output rows and std scaled by 2/3 (lam_r 2 -> 3).
set -euo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate
L=artifacts/train/logs/picklebot_return_stand; D=$L/2026-10-26_06-00-00_rally-15-lamr3-init
mkdir -p $D
python scripts/lam_r_init.py --src $L/2026-10-25_15-06-49_rally-14-lamr2/model_27798.pt --dst $D/model_27798.pt --factor 0.6666667
