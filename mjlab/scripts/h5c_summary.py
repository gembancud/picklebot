"""Stage 5C gate summary for an h5c_eval.sh run (D-075).

Gate:
- every family in every court zone where it is fed >= 75 % legal (volleys included);
- move-to-spot arrival >= 90 % in every direction;
- recovery median <= 0.5 m (court-wide random spots);
- falls <= 1 % per robot episode, taken as the worse of the court drill and the move-to-spot drill (D-086);
- style <= 3.86;
- no Stage 5B drill family more than 5 points below h4-25b (its paired final evaluation, stage5b-h4-gate2-cand).

Main metric (plateau rule): the court drill's pooled no-hint legal rate.
Usage: python scripts/h5c_summary.py TAG [--json OUT]
"""
import argparse
import json

ap = argparse.ArgumentParser()
ap.add_argument("tag")
ap.add_argument("--json", default=None)
a = ap.parse_args()
R = f"results/stage5c-{a.tag}"
court, move = json.load(open(f"{R}-court.json")), json.load(open(f"{R}-move.json"))
d5b, base5b = json.load(open(f"{R}-drill5b.json")), json.load(open("results/stage5b-h4-gate2-cand-nohint-A.json"))
style = json.load(open(f"{R}-style.json"))["nearest_clip_distance_median"]
checks = {}
cells = court.get("per_zone_family", {})
low = {k: v["legal_return"] for k, v in cells.items() if v["episodes"] >= 30 and v["legal_return"] < 0.75}
thin = {k: v["episodes"] for k, v in cells.items() if v["episodes"] < 30}  # unresolved: never counted as passing (D-086)
n_pass = len(cells) - len(low) - len(thin)
checks["court cells >= 75 %"] = (not low and not thin, f"{n_pass}/{len(cells)} cells pass" + (f"; fail: {low}" if low else "")
                                 + (f"; under 30 episodes: {thin}" if thin else ""))
SECTOR_NAMES = ("fwd", "fwd-left", "left", "back-left", "back", "back-right", "right", "fwd-right")  # 0 = toward the net, ccw
sectors = move.get("move_drill", {}).get("sectors", [])
arr = {SECTOR_NAMES[v["sector"]]: v.get("arrival_rate") for v in sectors}
bad = {k: r for k, r in arr.items() if r is None or r < 0.9}
checks["move arrival >= 90 % per direction"] = (not bad and bool(arr), f"{arr}")
rec = court.get("recovery", {}).get("error_median_m")
try:  # D-086: the gate reads the time-model score; the at-next-feed score and the stand-still gap are reported with it
    rr = json.load(open(f"{R}-recovery.json"))["recovery"]
    rec_tm = rr.get("time_model_error_median_m")
    checks["recovery <= 0.5 m"] = (rec_tm is not None and rec_tm <= 0.5,
                                   f"time model {rec_tm} (stand-still gap {rr.get('stand_still_gap_median_m')}, "
                                   f"scored {rr.get('time_model_scored')}, unscored {rr.get('time_model_unscored_next_feed_first')}); "
                                   f"at next feed {rec}")
except FileNotFoundError:
    checks["recovery <= 0.5 m"] = (rec is not None and rec <= 0.5, f"at next feed {rec} (no time-model evaluation)")
falls_court, falls_move = court["robot_fall_rate_per_episode"], move.get("robot_fall_rate_per_episode", 0.0)
falls = max(falls_court, falls_move)
checks["falls <= 1 %"] = (falls <= 0.01, f"court {falls_court}, move drill {falls_move}")
checks["style <= 3.86"] = (style <= 3.86, f"{style:.3f}")
reg = {f: round(d5b["per_family"][f]["legal_return"] - base5b["per_family"][f]["legal_return"], 3)
       for f in base5b["per_family"] if f in d5b["per_family"]}
worse = {f: x for f, x in reg.items() if x < -0.05}
checks["5B families within 5 points of h4-25b"] = (not worse, f"diffs {reg}")
main = court["legal_return_rate"]
print(f"{a.tag}: main metric (court drill, pooled no-hint legal) {main:.4f}; falls {falls}; recovery {rec}; style {style:.3f}")
try:  # D-086 north-star, reported, not gated
    ra = json.load(open(f"{R}-rally.json"))["rally"]
    print(f"  rally (court-anchored feeds): P(rally >= {ra['n']}) {ra['p_reach_n']} {ra['p_reach_n_ci95']}; "
          f"mean length of ended rallies {ra['mean_length_of_ended_rallies']} (n {ra['ended_rallies']})")
except FileNotFoundError:
    pass
for k, (ok, why) in checks.items():
    print(f"  [{'pass' if ok else 'FAIL'}] {k}: {why}")
zones = {}
for k, v in cells.items():
    f, z = k.split("@")
    zones.setdefault(f, {})[z] = round(v["legal_return"], 3)
print("  per family x zone (legal):")
for f, zz in zones.items():
    print(f"    {f:16s} " + "  ".join(f"{z}:{zz.get(z, '-')}" for z in ("back", "mid", "front")))
if a.json:
    json.dump({"main": main, "checks": {k: [ok, why] for k, (ok, why) in checks.items()}, "zones": zones},
              open(a.json, "w"), indent=1)
