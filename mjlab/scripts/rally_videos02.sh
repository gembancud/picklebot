#!/usr/bin/env bash
# Interim rally video (panel round 25, 3/5+): rally run 2's endpoint (rally-02-coop/model_6400), M1 not met. One court
# with both robots (picklebot_mj/pair_video.py), the target protocol with the contact hand-off, 8 envs (4 courts), 90 s,
# development seed 4218240. Clips, chosen before rendering: PREFIX-first.mp4 (court 0, every rally in order, not picked)
# and PREFIX-longest.mp4 (the longest rally of the 4 courts, picked and labelled so). No gate statistic is taken from it.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
O=artifacts/videos/rally02; mkdir -p $O
A="--task Picklebot-Latent-Court-Res-G1 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --rally --pairs --pair-handoff contact --envs 8 --seconds 90 --pair-video-courts 4"
bash scripts/stage2_eval.sh rally-02-coop model_6400.pt $A --seed 4218240 --pair-video $O/run2 \
  --pair-video-caption "Rally run 2 (cooperative credit). INTERIM, milestone M1 not met. Rallies of 5+ good shots: 7.9 % (target 80 %)" \
  --json $O/run2.json > /tmp/rv2.log 2>&1; echo "run 2 video: $?"
python - <<'PY'
import json
d = json.load(open("artifacts/videos/rally02/run2.json"))
print(d.get("pair_video"), "P(5+)", d["pairs"]["p_len_ge_5"], "rallies", d["pairs"]["rallies"], "hist", d["pairs"]["len_hist"][:14])
PY
ls -la $O
