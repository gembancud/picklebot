#!/usr/bin/env bash
# AMASS-G1 footwork clips -> artifacts/motion/tracking/amass-footwork.npz, the AMASS part of the footwork specialist's
# style (AMP) expert set (tasks/footwork_specialist.py, D-179). Selection rule (frozen before conversion): accepted clips
# (scripts/motion/amass_g1_import.py) moving in >= 30 % of frames, with >= 50 % of moving frames to the left, back or
# right of the pelvis heading. 30 fps CSVs -> 50 fps npz (the control rate, as the LAFAN1 expert files).
# The npz stays in git-ignored artifacts/ (AMASS licence); the clip list is results/amass-footwork-clips.json.
set -euo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
SRC=artifacts/motion/amass-g1; OUT=artifacts/motion/tracking/amass-footwork.npz; LIST=results/amass-footwork-clips.json
[ -s $OUT ] && { echo "$OUT exists: not rebuilt"; exit 0; }
python -I - "$SRC" "$LIST" <<'PY'
import json, sys
src, out = sys.argv[1], sys.argv[2]
pick = []
for n in json.load(open(f"{src}/accepted.json")):
    r = json.load(open(f"{src}/{n}.json"))
    d = r["dir_frac"]
    if r["moving_frames_frac"] >= 0.3 and d["left"] + d["back"] + d["right"] >= 0.5:
        pick.append(n)
json.dump(sorted(pick), open(out, "w"), indent=1)
print(f"{len(pick)} clips -> {out}")
PY
python scripts/motion/csv_to_npz_local.py $SRC $OUT --clips-json $LIST --input-fps 30 --output-fps 50
python -I - "$OUT" <<'PY'
import sys, numpy as np
d = np.load(sys.argv[1])
for f in ("lafan-g1.npz", "lafan-g1-mirror.npz"):
    e = np.load(f"artifacts/motion/tracking/{f}")
    assert float(e["fps"][0]) == float(d["fps"][0]) == 50.0, (f, e["fps"], d["fps"])
    assert e["body_pos_w"].shape[1:] == d["body_pos_w"].shape[1:], f
print(f"{len(d['clip_starts'])} clips, {len(d['joint_pos'])} frames at {float(d['fps'][0])} fps; matches the LAFAN1 files")
PY
