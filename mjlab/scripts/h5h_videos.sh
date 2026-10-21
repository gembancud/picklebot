#!/usr/bin/env bash
# Stage 5H interim videos (D-132, panel round 20): one court, both robots (picklebot_mj/pair_video.py), R4 protocol,
# 8 envs (4 courts), 60 s, development seeds (64 envs rendered too slowly). Clips, chosen before rendering:
#   PREFIX-first.mp4    court 0, every rally in order (not picked);
#   PREFIX-longest.mp4  the longest rally among courts 0-3 (picked: labelled as the longest of 4 courts).
# Policies: run 1 (s5h-01-keepalive/model_2599, the best Stage 5H policy that passes every stage rule; seed 4217401) and
# run 4 (s5h-04-pairs/model_3398, pair-mode self-play, killed by the court-main rule by 0.5 points; seed 4217402).
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
O=artifacts/videos/s5h; mkdir -p $O
A="--task Picklebot-Latent-Court-Res-G1 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --rally --pairs --envs 8 --seconds 60 --pair-video-courts 4"
bash scripts/stage2_eval.sh s5h-01-keepalive model_2599.pt $A --seed 4217401 --pair-video $O/run1 \
  --pair-video-caption "Stage 5H run 1 (passes every stage rule). Two-robot rallies of 4+ legal shots: 0.04 % (video bar 10 %)" \
  --json $O/run1.json > /tmp/v1.log 2>&1; echo "run 1: $?"
bash scripts/stage2_eval.sh s5h-04-pairs model_3398.pt $A --seed 4217402 --pair-video $O/run4 \
  --pair-video-caption "Stage 5H run 4 (trained by self-play; court rule missed by 0.5 pt). Rallies of 4+ legal shots: 0.65 % (bar 10 %)" \
  --json $O/run4.json > /tmp/v4.log 2>&1; echo "run 4: $?"
python - <<'PY'
import json, imageio_ffmpeg, mediapy
mediapy.set_ffmpeg(imageio_ffmpeg.get_ffmpeg_exe())
for tag in ("run1", "run4"):
    d = json.load(open(f"artifacts/videos/s5h/{tag}.json"))
    print(tag, d.get("pair_video"), "P(4+)", d["pairs"]["p_len_ge_4"], "rallies", d["pairs"]["rallies"])
PY
ls -la $O
