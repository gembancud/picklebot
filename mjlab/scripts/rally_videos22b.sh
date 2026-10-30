#!/usr/bin/env bash
# Rally video for the user (2026-10-30, after D-177): run 22b's best checkpoint (rally-22b-readcfg/model_30200), target NOT
# met. One court with both robots (picklebot_mj/pair_video.py), read protocol (contact hand-off, target A, mean actions),
# 8 envs (4 courts), 90 s, development seed 4220200. Clips chosen before rendering: PREFIX-first.mp4 (court 0, every rally
# in order, not picked) and PREFIX-longest.mp4 (the longest rally of the 4 courts, picked and labelled so). No gate statistic.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
O=artifacts/videos/rally22b; mkdir -p $O
A="--task Picklebot-Latent-Court-Res-G1 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --rally --pairs --pair-handoff contact --envs 8 --seconds 90 --pair-video-courts 4"
PICKLEBOT_LAM_R=2 bash scripts/stage2_eval.sh rally-22b-readcfg model_30200.pt $A --seed 4220200 --pair-video $O/run22b \
  --pair-video-caption "Rally run 22b (best so far). Target NOT met: rallies of 5+ good shots 39 % (target 80 %)" \
  --json $O/run22b.json > /tmp/rv22b.log 2>&1; echo "run 22b video: $?"
python - <<'PY'
import json
d = json.load(open("artifacts/videos/rally22b/run22b.json"))
print(d.get("pair_video"), "P(5+)", d["pairs"]["p_len_ge_5"], "rallies", d["pairs"]["rallies"], "hist", d["pairs"]["len_hist"][:14])
PY
ls -la $O
