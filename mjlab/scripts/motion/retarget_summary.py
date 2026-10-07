"""Summarise tennis_retarget.py checks per stroke type (Stage 5B).

A clip is accepted when the robot follows the scaled human closely: median position error <= ACCEPT_MEDIAN_M and
95th percentile <= ACCEPT_P95_M over the position-tracked bodies. Writes OUT/accepted.json.

Usage: python scripts/motion/retarget_summary.py artifacts/motion/retargeted artifacts/motion/Tennis-MoCap/labels.csv
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ACCEPT_MEDIAN_M, ACCEPT_P95_M = 0.08, 0.20
STROKES = {"0": "serve", "1": "smash", "2": "forehand", "3": "forehand_volley", "4": "backhand", "5": "backhand_volley"}

out, labels = Path(sys.argv[1]), Path(sys.argv[2])
meta = {}
for line in labels.read_text().splitlines()[1:]:
    f, perf, _, _, stroke = line.strip().split(";")
    meta[Path(f).stem] = (STROKES[stroke], "high" if perf == "1" else "regular")
groups = defaultdict(list)
for j in sorted(out.glob("*.json")):
    if j.stem not in meta:
        continue
    r = json.loads(j.read_text())
    if "pos_err_median_m" not in r:
        continue
    r["accepted"] = r["pos_err_median_m"] <= ACCEPT_MEDIAN_M and r["pos_err_p95_m"] <= ACCEPT_P95_M
    r["stroke"], r["level"] = meta[j.stem]
    groups[r["stroke"]].append(r)
accepted = sorted(Path(r["source"]).stem for g in groups.values() for r in g if r["accepted"])
(out / "accepted.json").write_text(json.dumps(accepted, indent=1))
print(f"{'stroke':16s} clips accepted  min(acc) pos-err-med  right-handed  any-limit  skate(m/s)  wrist-p99(m/s)  "
      "joints often at limit (accepted)")
total = 0
for s in STROKES.values():
    g = groups.get(s, [])
    if not g:
        continue
    total += len(g)
    acc = [r for r in g if r["accepted"]]
    secs = sum(r["seconds"] for r in acc) / 60
    pe = np.median([r["pos_err_median_m"] for r in g])
    rh = sum(r["human_hand"] == "right" for r in g)
    lim = np.mean([r["joint_limit_frac_frames"] for r in g])
    sk = np.median([max(r["left_skate_median_mps"], r["right_skate_median_mps"]) for r in g])
    ws = np.median([r["right_wrist_speed_p99_mps"] for r in g])
    jl = defaultdict(float)
    for r in acc:
        for k, v in r["joints_at_limit"].items():
            jl[k] += v / len(acc)
    top = ", ".join(f"{k.replace('_joint', '')} {v:.0%}" for k, v in sorted(jl.items(), key=lambda x: -x[1])[:3])
    print(f"{s:16s} {len(g):5d} {len(acc):8d} {secs:8.1f}   {pe:9.3f}   {rh:5d}/{len(g):<3d}    {lim:7.1%}   {sk:8.3f}  "
          f"{ws:12.2f}    {top}")
print("clips:", total, "accepted:", len(accepted))
