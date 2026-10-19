"""Stage 5F summary for an h5f_eval.sh run (D-111): the frozen D-101 battery's gate items, the with-delay bars and the
delay grid. Descriptive: the gate decision and the kill rules are applied in results/stage5f.md against the frozen
numbers in results/stage5f-thresholds.md.
Usage: python scripts/h5f_summary.py TAG [--json OUT]
"""
import argparse
import json
import os

SECTOR_NAMES = ("fwd", "fwd-left", "left", "back-left", "back", "back-right", "right", "fwd-right")
ap = argparse.ArgumentParser()
ap.add_argument("tag")
ap.add_argument("--json", default=None)
a = ap.parse_args()
R, E = f"results/stage5f-{a.tag}", f"results/stage5e-s5f-{a.tag}"
load = lambda p: json.load(open(p)) if os.path.exists(p) else None


def arrival(d):
    s = (d or {}).get("move_drill", {}).get("sectors", [])
    return {SECTOR_NAMES[v["sector"]]: v.get("arrival_rate") for v in s if v["sector"] < len(SECTOR_NAMES)}


out = {"tag": a.tag}
v2 = load(f"{E}-v2-noisy.json")
if v2:
    g = v2["drill_v2"]
    out["frozen_v2"] = {"p": g["per_shot_p"], "ci95": g["per_shot_ci95"],
                        "groups": {k: {"p": x["legal_return"], "wilson_low": x["ci95"][0]} for k, x in g["groups"].items()}}
c5 = {k: load(f"results/stage5c-s5f-{a.tag}-5c-{k}.json") for k in ("court", "move", "style")}
if c5["court"]:
    out["clean"] = {"court_main": c5["court"]["legal_return_rate"],
                    "falls": max(c5["court"]["robot_fall_rate_per_episode"], (c5["move"] or {}).get("robot_fall_rate_per_episode", 0.0)),
                    "arrival": arrival(c5["move"])}
if c5["style"]:
    out["style"] = {"old": c5["style"].get("nearest_clip_distance_median"),
                    "new": (c5["style"].get("new_reference") or {}).get("nearest_clip_distance_median")}
grid = {}
for b in (0, 20, 40, 60):
    for c in (0, 10, 20, 30):
        v, ct = load(f"{R}-v2-b{b}-c{c}.json"), load(f"{R}-court-b{b}-c{c}.json")
        if v or ct:
            grid[f"{b}/{c}"] = {"v2_p": v and v["drill_v2"]["per_shot_p"], "court_main": ct and ct["legal_return_rate"],
                                "court_falls": ct and ct["robot_fall_rate_per_episode"]}
out["grid"] = grid
out["move"] = {}
for c in (0, 10, 20):
    m = load(f"{R}-move-c{c}.json")
    if m:
        arr = arrival(m)
        out["move"][f"cmd{c}"] = {"arrival_min": min(arr.values()) if arr else None, "arrival": arr,
                                  "falls": m["robot_fall_rate_per_episode"]}
print(json.dumps(out, indent=1))
if a.json:
    json.dump(out, open(a.json, "w"), indent=1)
