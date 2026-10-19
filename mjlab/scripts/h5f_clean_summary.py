"""Stage 5F clean-instrument summary for an h5f_clean_eval.sh run (D-113). Gate items with the unchanged D-101 bars,
plus the non-gating D-101 figure and delay cells. Usage: python scripts/h5f_clean_summary.py TAG [--json OUT]"""
import argparse
import json
import os

SECTOR_NAMES = ("fwd", "fwd-left", "left", "back-left", "back", "back-right", "right", "fwd-right")
FLOORS = {"neutral": 0.92, "moderate": 0.80, "extreme": 0.55}
ap = argparse.ArgumentParser()
ap.add_argument("tag")
ap.add_argument("--json", default=None)
a = ap.parse_args()
R, C = f"results/stage5f-{a.tag}", f"results/stage5c-{a.tag}-5c"
load = lambda p: json.load(open(p)) if os.path.exists(p) else None  # noqa: E731


def v2(d):
    if not d:
        return None
    g = d["drill_v2"]
    return {"p": g["per_shot_p"], "ci95": g["per_shot_ci95"],
            "groups": {k: {"p": x["legal_return"], "wilson_low": x["ci95"][0], "feeds": x["episodes"]}
                       for k, x in g["groups"].items()},
            "p_rally5": d["rally"].get("p_reach_5"), "p_rally10": d["rally"].get("p_reach_n")}


def arrival(d):
    s = (d or {}).get("move_drill", {}).get("sectors", [])
    return {SECTOR_NAMES[v["sector"]]: v.get("arrival_rate") for v in s if v["sector"] < len(SECTOR_NAMES)}


out = {"tag": a.tag, "instrument": "D-113 clean (drill v2 cell 0/0, ball noise, noisy spot)"}
out["v2"] = v2(load(f"{R}-v2.json"))
for k in ("cleanspot", "nospot", "c10", "b40c20"):
    out[f"v2_{k}"] = v2(load(f"{R}-v2-{k}.json"))
out["d101_reported"] = v2(load(f"{R}-d101.json"))
court, move, style = load(f"{C}-court.json"), load(f"{C}-move.json"), load(f"{C}-style.json")
mc10 = load(f"{R}-move-c10.json")
out["court_main"] = court and court["legal_return_rate"]
out["falls"] = court and max(court["robot_fall_rate_per_episode"], (move or {}).get("robot_fall_rate_per_episode", 0.0))
out["falls_court"] = court and court["robot_fall_rate_per_episode"]
out["arrival"] = arrival(move)
out["style_new"] = style and (style.get("new_reference") or {}).get("nearest_clip_distance_median")
out["style_old"] = style and style.get("nearest_clip_distance_median")
out["move_c10_reported"] = mc10 and {"arrival_min": min(arrival(mc10).values()) if arrival(mc10) else None,
                                     "falls": mc10["robot_fall_rate_per_episode"]}
ra = load(f"{C}-rally.json")
out["rally5d_p10"] = ra and ra["rally"]["p_reach_n"]
g = {}
if out["v2"]:
    g["per-shot p >= 0.80"] = out["v2"]["p"] >= 0.80
    for k, fl in FLOORS.items():
        g[f"{k} Wilson low >= {fl}"] = out["v2"]["groups"][k]["wilson_low"] >= fl
if court:
    g["court main >= 76.8 %"] = out["court_main"] >= 0.768
    g["falls <= 1 %"] = out["falls"] <= 0.01
if out["arrival"]:
    g["arrival >= 90 % every direction"] = min(out["arrival"].values()) >= 0.90
if out["style_new"] is not None:
    g["style (new) <= 3.86"] = out["style_new"] <= 3.86
out["gate"] = g
out["gate_items_met"] = f"{sum(g.values())}/{len(g)}"
print(json.dumps(out, indent=1))
if a.json:
    json.dump(out, open(a.json, "w"), indent=1)
