"""D-186 diagnostic: travel ratio D by clip family (LAFAN1 walk / run / sprint / fightAndSports, original vs mirrored,
footwork-fast) for an h0-fw read pair, FAST windows (travel_rule definitions). Reported, never a verdict.
Usage: python scripts/diag/h0fw_breakdown.py results/h0fw01-killtl-child.json results/h0fw01-killtl-parent.json ...
"""

import json
import sys
from collections import defaultdict

import numpy as np

from picklebot_mj import travel_rule as tr


def family(clip: str) -> str:
    if clip.startswith("fwfast_"):
        return "footwork_fast"
    if "subject" in clip:
        base = clip.split("_")[0].rstrip("0123456789")
        return ("mirror_" if clip.endswith("_mirror") else "") + base
    return "tennis"


for path in sys.argv[1:]:
    d = json.load(open(path))
    fast = {k for k, u in enumerate(d["per_clip"]) if u["ref_pelvis_speed"] >= tr.FAST}
    out = defaultdict(list)
    for e in d["per_env"]:
        if e["disp_ref"] >= tr.MIN_REF_M:
            out[(family(e["clip"]), e["unit"] in fast)].append(e["disp_robot"] / e["disp_ref"])
    print(path)
    for (f, is_fast), r in sorted(out.items()):
        print(f"  {f:22s} {'FAST' if is_fast else 'slow':4s} n={len(r):5d} D={np.median(r):.3f}")
