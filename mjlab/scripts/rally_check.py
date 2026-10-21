"""Rally target checks (D-134 / D-135; mjlab/results/rally-target.md).

Usage:
  rally_check.py early PREFIX   the early-kill read: PREFIX-{early,parent-early}-{v2,move,court,pairs}.json; exit 1 = kill
  rally_check.py target PREFIX TAG  the target read: PREFIX-target.json (contact hand-off), PREFIX-target-crossing.json
                                (reported) and court falls from the endpoint summary (results/stage5f-TAG-summary.json)
"""

from __future__ import annotations

import json
import math
import sys


def wilson(k: int, n: int, z: float = 1.96) -> list[float]:
    if n == 0:
        return [0.0, 0.0]
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(c - h, 4), round(c + h, 4)]


def pair_stats(p: dict) -> dict:
    """Own-ball (the partner's shots) and feeder-ball legal counts, P(5+) with its count."""
    so, sd = p["sides_own_ball"], p["sides"]
    k_own = sum(round(v["legal"] * v["feeds"]) for v in so.values())
    n_own = sum(v["feeds"] for v in so.values())
    k_all = sum(round(v["legal"] * v["feeds"]) for v in sd.values())
    n_all = sum(v["feeds"] for v in sd.values())
    hist, n = p["len_hist"], p["rallies"]
    k5 = sum(hist[5:])
    return {"own": k_own / max(n_own, 1), "own_k": k_own, "own_n": n_own, "own_ci": wilson(k_own, n_own),
            "feeder": (k_all - k_own) / max(n_all - n_own, 1), "feeder_n": n_all - n_own,
            "feeder_ci": wilson(k_all - k_own, n_all - n_own),
            "p5": k5 / max(n, 1), "p5_ci": wilson(k5, n), "rallies": n, "p4": p["p_len_ge_4"], "mean": p["mean_len"],
            "sides": {s: v["legal"] for s, v in sd.items()}}


def early(prefix: str) -> bool:
    ld = lambda k: json.load(open(f"{prefix}-{k}.json"))  # noqa: E731
    v0, v1 = ld("parent-early-v2")["drill_v2"]["per_shot_p"], ld("early-v2")["drill_v2"]["per_shot_p"]
    pc, ec = ld("parent-early-court"), ld("early-court")
    c0, c1 = pc["legal_return_rate"], ec["legal_return_rate"]
    fk, fn = ec["robot_falls"], ec["robot_episodes"]
    f1, flo = fk / max(fn, 1), wilson(fk, fn)[0]
    arr = lambda d: min(s["arrival_rate"] for s in d["move_drill"]["sectors"]  # noqa: E731
                        if s["sector"] < 8 and s.get("arrival_rate") is not None)
    a0, a1 = arr(ld("parent-early-move")), arr(ld("early-move"))
    P0, P1 = pair_stats(ld("parent-early-pairs")["pairs"]), pair_stats(ld("early-pairs")["pairs"])
    print(f"early: pairs own-ball legal {P0['own']:.4f} {P0['own_ci']} -> {P1['own']:.4f} {P1['own_ci']} of {P1['own_n']} "
          f"(kill if not above {P0['own_ci'][1]}); P(5+) {P0['p5']:.4f} -> {P1['p5']:.4f} {P1['p5_ci']}; "
          f"P(4+) {P0['p4']} -> {P1['p4']}; rallies {P1['rallies']}")
    print(f"early: feeder-ball legal {P0['feeder']:.4f} -> {P1['feeder']:.4f} ({100 * (P1['feeder'] - P0['feeder']):+.1f}; "
          f"kill below -5); court main {c0} -> {c1} ({100 * (c1 - c0):+.1f}; kill below -5); drill v2 {v0} -> {v1} "
          f"({100 * (v1 - v0):+.1f}; kill below -5); move arrival min {a0} -> {a1} ({100 * (a1 - a0):+.1f}; kill below -5)")
    print(f"early: court falls/episode {f1:.4f} [{flo}, ...] of {fn} (kill if Wilson low > 0.04 or point > 0.074)")
    ok = (P1["own"] > P0["own_ci"][1] and P1["feeder"] >= P0["feeder"] - 0.05 and c1 >= c0 - 0.05 and v1 >= v0 - 0.05
          and a1 >= a0 - 0.05 and flo <= 0.04 and f1 <= 0.074)
    return ok


def target(prefix: str, tag: str) -> bool:
    P = pair_stats(json.load(open(f"{prefix}-target.json"))["pairs"])
    try:
        X = pair_stats(json.load(open(f"{prefix}-target-crossing.json"))["pairs"])
        print(f"crossing hand-off (reported): P(5+) {X['p5']:.4f} {X['p5_ci']}; own-ball {X['own']:.4f}; P(4+) {X['p4']}")
    except FileNotFoundError:
        pass
    falls = json.load(open(f"results/stage5f-{tag}-summary.json"))["falls_court"]
    gap = abs(P["sides"]["A"] - P["sides"]["B"])
    print(f"target (contact hand-off): rallies {P['rallies']}; P(5+) {P['p5']:.4f} {P['p5_ci']} (pass: >= 0.80, low >= 0.78); "
          f"P(4+) {P['p4']}; mean {P['mean']}; own-ball legal {P['own']:.4f} {P['own_ci']}; feeder-ball legal "
          f"{P['feeder']:.4f} {P['feeder_ci']}; sides {P['sides']} (gap {100 * gap:.1f} points, <= 3); court falls {falls} (<= 0.04)")
    met = P["rallies"] >= 1000 and P["p5"] >= 0.80 and P["p5_ci"][0] >= 0.78 and gap <= 0.03 and falls <= 0.04
    print("TARGET MET" if met else "target not met")
    return met


if __name__ == "__main__":
    mode, prefix = sys.argv[1], sys.argv[2]
    if mode == "early":
        sys.exit(0 if early(prefix) else 1)
    target(prefix, sys.argv[3])
