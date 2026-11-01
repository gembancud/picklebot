"""Rally target checks (D-134 / D-135; mjlab/results/rally-target.md).

Usage:
  rally_check.py early PREFIX   the early-kill read: PREFIX-{early,parent-early}-{v2,move,court,pairs}.json; exit 1 = kill
  rally_check.py m1 PREFIX TAG      milestone M1 (rally-milestones.md) on PREFIX-target.json; exit 1 = not met
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


def early_continuation(prefix: str) -> bool:
    """Rally run 3 (D-139, a continuation): the early-kill read against the parent's reads on the same seeds."""
    ld = lambda k: json.load(open(f"{prefix}-{k}.json"))  # noqa: E731
    v0, v1 = ld("parent-early-v2")["drill_v2"]["per_shot_p"], ld("early-v2")["drill_v2"]["per_shot_p"]
    pc, ec = ld("parent-early-court"), ld("early-court")
    c0, c1 = pc["legal_return_rate"], ec["legal_return_rate"]
    fk, fn = ec["robot_falls"], ec["robot_episodes"]
    f1, flo = fk / max(fn, 1), wilson(fk, fn)[0]
    arr = lambda d: min(s["arrival_rate"] for s in d["move_drill"]["sectors"]  # noqa: E731
                        if s["sector"] < 8 and s.get("arrival_rate") is not None)
    a0, a1 = arr(ld("parent-early-move")), arr(ld("early-move"))
    p0, p1 = ld("parent-early-pairs")["pairs"], ld("early-pairs")["pairs"]
    own0, own0_lo = boot_low(p0["court_counts"], 1, 0)
    own1, own1_lo = boot_low(p1["court_counts"], 1, 0)
    fed0, _ = boot_low(p0["court_counts"], 3, 2)
    fed1, fed1_lo = boot_low(p1["court_counts"], 3, 2)
    print(f"early: partner-ball legal {own0:.4f} (low {own0_lo:.4f}) -> {own1:.4f} (low {own1_lo:.4f}) (kill below "
          f"{own0_lo - 0.02:.4f}); feeder-ball legal {fed0:.4f} -> {fed1:.4f} (low {fed1_lo:.4f}) (kill below {fed0 - 0.03:.4f}); "
          f"P(5+) {p0['p_len_ge_5']} -> {p1['p_len_ge_5']}")
    print(f"early: court main {c0} -> {c1} ({100 * (c1 - c0):+.1f}; kill below -5); drill v2 {v0} -> {v1} "
          f"({100 * (v1 - v0):+.1f}; kill below -5); move arrival min {a0} -> {a1} ({100 * (a1 - a0):+.1f}; kill below -5); "
          f"court falls/episode {f1:.4f} (low {flo}; kill if low > 0.04 or point > 0.074)")
    return (own1 >= own0_lo - 0.02 and fed1 >= fed0 - 0.03 and c1 >= c0 - 0.05 and v1 >= v0 - 0.05 and a1 >= a0 - 0.05
            and flo <= 0.04 and f1 <= 0.074)


DOWN_WEIGHTED = ("short", "high", "reach_forehand")  # D-141: the families run 5 feeds less often


def early_weak(prefix: str) -> bool:
    """Rally run 5 (D-141): the early-kill read against the parent's reads on the same seeds."""
    ld = lambda k: json.load(open(f"{prefix}-{k}.json"))  # noqa: E731
    v0, v1 = ld("parent-early-v2")["drill_v2"]["per_shot_p"], ld("early-v2")["drill_v2"]["per_shot_p"]
    pc, ec = ld("parent-early-court"), ld("early-court")
    c0, c1 = pc["legal_return_rate"], ec["legal_return_rate"]
    fk, fn = ec["robot_falls"], ec["robot_episodes"]
    f1, flo = fk / max(fn, 1), wilson(fk, fn)[0]
    arr = lambda d: min(s["arrival_rate"] for s in d["move_drill"]["sectors"]  # noqa: E731
                        if s["sector"] < 8 and s.get("arrival_rate") is not None)
    a0, a1 = arr(ld("parent-early-move")), arr(ld("early-move"))
    j0, j1 = ld("parent-early-pairs"), ld("early-pairs")
    own0, _ = boot_low(j0["pairs"]["court_counts"], 1, 0)
    own1, own1_lo = boot_low(j1["pairs"]["court_counts"], 1, 0)
    fed0, _ = boot_low(j0["pairs"]["court_counts"], 3, 2)
    fed1, fed1_lo = boot_low(j1["pairs"]["court_counts"], 3, 2)
    fam = {k: (j0["per_family"][k]["legal_return"], j1["per_family"][k]["legal_return"]) for k in j0["per_family"]}
    print(f"early: partner-ball legal {own0:.4f} -> {own1:.4f} (low {own1_lo:.4f}; kill below {max(0.50, own0 - 0.03):.4f}); "
          f"feeder-ball legal {fed0:.4f} -> {fed1:.4f} (low {fed1_lo:.4f}; kill below {fed0 - 0.02:.4f}); "
          f"P(5+) {j0['pairs']['p_len_ge_5']} -> {j1['pairs']['p_len_ge_5']}")
    print("early: feeder families " + "; ".join(f"{k} {a:.3f} -> {b:.3f}" + (" (guard: kill below -5)" if k in DOWN_WEIGHTED else "")
                                               for k, (a, b) in fam.items()))
    print(f"early: court main {c0} -> {c1} ({100 * (c1 - c0):+.1f}; kill below -5); drill v2 {v0} -> {v1} "
          f"({100 * (v1 - v0):+.1f}; kill below -5); move arrival min {a0} -> {a1} ({100 * (a1 - a0):+.1f}; kill below -5); "
          f"court falls/episode {f1:.4f} (low {flo}; kill if low > 0.04 or point > 0.074)")
    guard = all(fam[k][1] >= fam[k][0] - 0.05 for k in DOWN_WEIGHTED)
    return (own1 >= max(0.50, own0 - 0.03) and fed1 >= fed0 - 0.02 and guard and c1 >= c0 - 0.05 and v1 >= v0 - 0.05
            and a1 >= a0 - 0.05 and flo <= 0.04 and f1 <= 0.074)


def early_pace(prefix: str) -> bool:
    """Rally run 7 (D-144, experiment design's lines): the early-kill read against the parent's reads on the same seeds."""
    ld = lambda k: json.load(open(f"{prefix}-{k}.json"))  # noqa: E731
    v0, v1 = ld("parent-early-v2")["drill_v2"]["per_shot_p"], ld("early-v2")["drill_v2"]["per_shot_p"]
    pc, ec = ld("parent-early-court"), ld("early-court")
    c0, c1 = pc["legal_return_rate"], ec["legal_return_rate"]
    lc0 = pc["legal_return_rate"] / max(pc["contact_rate"], 1e-9)
    lc1 = ec["legal_return_rate"] / max(ec["contact_rate"], 1e-9)
    fk, fn = ec["robot_falls"], ec["robot_episodes"]
    f1, flo = fk / max(fn, 1), wilson(fk, fn)[0]
    arr = lambda d: min(s["arrival_rate"] for s in d["move_drill"]["sectors"]  # noqa: E731
                        if s["sector"] < 8 and s.get("arrival_rate") is not None)
    a0, a1 = arr(ld("parent-early-move")), arr(ld("early-move"))
    j0, j1 = ld("parent-early-pairs"), ld("early-pairs")
    own0, _ = boot_low(j0["pairs"]["court_counts"], 1, 0)
    own1, own1_lo = boot_low(j1["pairs"]["court_counts"], 1, 0)
    fed0, _ = boot_low(j0["pairs"]["court_counts"], 3, 2)
    fed1, fed1_lo = boot_low(j1["pairs"]["court_counts"], 3, 2)
    d0, d1 = j0["contact_diagnostics"], j1["contact_diagnostics"]
    box0, box1 = d0["keep_alive_box_share_of_legal_landings"], d1["keep_alive_box_share_of_legal_landings"]
    fl0, fl1 = d0["flight_time_mean_s"], d1["flight_time_mean_s"]
    print(f"early: manipulation: keep-alive-box share {box0} -> {box1}; flight {fl0} -> {fl1} s; ball out "
          f"{d0['ball_speed_out_mean']} -> {d1['ball_speed_out_mean']} m/s (kill if box < 0.27 and flight < 1.28)")
    print(f"early: partner-ball legal {own0:.4f} -> {own1:.4f} (low {own1_lo:.4f}; kill below {max(0.50, own0 - 0.03):.4f}); "
          f"feeder-ball legal {fed0:.4f} -> {fed1:.4f} (low {fed1_lo:.4f}; kill below {fed0 - 0.02:.4f}); "
          f"P(5+) {j0['pairs']['p_len_ge_5']} -> {j1['pairs']['p_len_ge_5']}")
    print(f"early: court legal given contact {lc0:.4f} -> {lc1:.4f} (kill below {lc0 - 0.03:.4f}); court main {c0} -> {c1} "
          f"({100 * (c1 - c0):+.1f}; kill below -5); drill v2 {v0} -> {v1} ({100 * (v1 - v0):+.1f}; kill below -5); "
          f"move arrival min {a0} -> {a1} ({100 * (a1 - a0):+.1f}; kill below -5); court falls/episode {f1:.4f} "
          f"(low {flo}; kill if low > 0.04 or point > 0.074)")
    engaged = not (box1 < 0.27 and fl1 < 1.28)
    return (engaged and own1 >= max(0.50, own0 - 0.03) and fed1 >= fed0 - 0.02 and lc1 >= lc0 - 0.03
            and c1 >= c0 - 0.05 and v1 >= v0 - 0.05 and a1 >= a0 - 0.05 and flo <= 0.04 and f1 <= 0.074)


def early_ceiling(prefix: str, engage_check: bool = True) -> bool:
    """Rally run 8 (D-145, experiment design's lines): the early-kill read against the parent's reads on the same seeds."""
    ld = lambda k: json.load(open(f"{prefix}-{k}.json"))  # noqa: E731
    v0, v1 = ld("parent-early-v2")["drill_v2"]["per_shot_p"], ld("early-v2")["drill_v2"]["per_shot_p"]
    pc, ec = ld("parent-early-court"), ld("early-court")
    c0, c1 = pc["legal_return_rate"], ec["legal_return_rate"]
    k0, k1 = pc["contact_rate"], ec["contact_rate"]
    lc0, lc1 = c0 / max(k0, 1e-9), c1 / max(k1, 1e-9)
    fk, fn = ec["robot_falls"], ec["robot_episodes"]
    f1, flo = fk / max(fn, 1), wilson(fk, fn)[0]
    arr = lambda d: min(s["arrival_rate"] for s in d["move_drill"]["sectors"]  # noqa: E731
                        if s["sector"] < 8 and s.get("arrival_rate") is not None)
    a0, a1 = arr(ld("parent-early-move")), arr(ld("early-move"))
    j0, j1 = ld("parent-early-pairs"), ld("early-pairs")
    own0, _ = boot_low(j0["pairs"]["court_counts"], 1, 0)
    own1, own1_lo = boot_low(j1["pairs"]["court_counts"], 1, 0)
    fed0, _ = boot_low(j0["pairs"]["court_counts"], 3, 2)
    fed1, fed1_lo = boot_low(j1["pairs"]["court_counts"], 3, 2)
    d0, d1 = j0["contact_diagnostics"], j1["contact_diagnostics"]
    # pair contact rate: first contacts over finished feeds (both ball types)
    pk = lambda j: j["contact_diagnostics"]["first_contacts"] / max(sum(r[0] + r[2] for r in j["pairs"]["court_counts"]), 1)  # noqa: E731
    pk0, pk1 = pk(j0), pk(j1)
    s0, s1 = d0["ball_speed_out_mean"], d1["ball_speed_out_mean"]
    h0, h1 = d0["ball_out_share_above_11"], d1["ball_out_share_above_11"]
    print(f"early: manipulation: pair ball out {s0} -> {s1} m/s (needs <= {s0 - 0.4:.3f}); share above 11 m/s {h0} -> {h1} "
          f"(needs <= {h0 - 0.08:.4f}); kill if neither")
    print(f"early: partner-ball legal {own0:.4f} -> {own1:.4f} (low {own1_lo:.4f}; kill below {max(0.50, own0 - 0.03):.4f}); "
          f"feeder-ball legal {fed0:.4f} -> {fed1:.4f} (low {fed1_lo:.4f}; kill below {fed0 - 0.02:.4f}); "
          f"P(5+) {j0['pairs']['p_len_ge_5']} -> {j1['pairs']['p_len_ge_5']}")
    print(f"early: court legal given contact {lc0:.4f} -> {lc1:.4f} (kill below {lc0 - 0.03:.4f}); court contact {k0} -> {k1} "
          f"(kill below {k0 - 0.03:.4f}); pair contact {pk0:.4f} -> {pk1:.4f} (kill below {pk0 - 0.03:.4f}); court main "
          f"{c0} -> {c1} ({100 * (c1 - c0):+.1f}; kill below -5); drill v2 {v0} -> {v1} ({100 * (v1 - v0):+.1f}; kill below "
          f"-5); move arrival min {a0} -> {a1} ({100 * (a1 - a0):+.1f}; kill below -5); court falls/episode {f1:.4f} "
          f"(low {flo}; kill if low > 0.04 or point > 0.074)")
    engaged = s1 <= s0 - 0.4 or h1 <= h0 - 0.08 or not engage_check
    return (engaged and own1 >= max(0.50, own0 - 0.03) and fed1 >= fed0 - 0.02 and lc1 >= lc0 - 0.03
            and k1 >= k0 - 0.03 and pk1 >= pk0 - 0.03 and c1 >= c0 - 0.05 and v1 >= v0 - 0.05 and a1 >= a0 - 0.05
            and flo <= 0.04 and f1 <= 0.074)


def early_ceiling_own(prefix: str) -> bool:
    """Rally run 9 (D-148): early_ceiling's lines unchanged, plus experiment design's guard: no feeder-ball family in
    the pairs read loses more than 5 points of contact against the parent."""
    ok = early_ceiling(prefix)
    f0 = json.load(open(f"{prefix}-parent-early-pairs.json"))["per_family"]
    f1 = json.load(open(f"{prefix}-early-pairs.json"))["per_family"]
    worst = min(((f1[k]["contact"] - f0[k]["contact"], k) for k in f0 if k in f1), default=(0.0, None))
    print(f"early: worst feeder-family contact change {100 * worst[0]:+.1f} points ({worst[1]}; kill below -5)")
    return ok and worst[0] >= -0.05


FEEDER_BONUS_FAMILIES = ("reach_deep", "cross_backhand", "fast", "reach_backhand", "backhand")


def early_feedbonus(prefix: str) -> bool:
    """Rally run 11 (D-150): early_ceiling's lines without its pace engagement check (the parent already has the
    ceiling), D-148's family-contact guard, and the new engagement check (architecture): the five bonus families'
    combined feeder-ball legal in the pairs read is up on the parent."""
    ok = early_ceiling(prefix, engage_check=False)
    f0 = json.load(open(f"{prefix}-parent-early-pairs.json"))["per_family"]
    f1 = json.load(open(f"{prefix}-early-pairs.json"))["per_family"]
    worst = min(((f1[k]["contact"] - f0[k]["contact"], k) for k in f0 if k in f1), default=(0.0, None))
    legal = lambda f: sum(f[k]["legal_return"] * f[k]["episodes"] for k in FEEDER_BONUS_FAMILIES) / max(  # noqa: E731
        sum(f[k]["episodes"] for k in FEEDER_BONUS_FAMILIES), 1)
    g0, g1 = legal(f0), legal(f1)
    print(f"early: worst feeder-family contact change {100 * worst[0]:+.1f} points ({worst[1]}; kill below -5)")
    print(f"early: bonus families' feeder-ball legal {g0:.4f} -> {g1:.4f} ({100 * (g1 - g0):+.1f}; kill if not up)")
    return ok and worst[0] >= -0.05 and g1 > g0


def early_legres(prefix: str) -> bool:
    """Rally run 12 (D-152): early_ceiling's lines without the pace engagement check, D-148's family-contact guard, and
    the engagement check (coach): reach_deep and fast feeder-ball contact in the pairs read is up on the parent."""
    ok = early_ceiling(prefix, engage_check=False)
    f0 = json.load(open(f"{prefix}-parent-early-pairs.json"))["per_family"]
    f1 = json.load(open(f"{prefix}-early-pairs.json"))["per_family"]
    worst = min(((f1[k]["contact"] - f0[k]["contact"], k) for k in f0 if k in f1), default=(0.0, None))
    fams = ("reach_deep", "fast")
    con = lambda f: sum(f[k]["contact"] * f[k]["episodes"] for k in fams) / max(sum(f[k]["episodes"] for k in fams), 1)  # noqa: E731
    g0, g1 = con(f0), con(f1)
    print(f"early: worst feeder-family contact change {100 * worst[0]:+.1f} points ({worst[1]}; kill below -5)")
    print(f"early: reach_deep + fast feeder-ball contact {g0:.4f} -> {g1:.4f} ({100 * (g1 - g0):+.1f}; kill if not up)")
    return ok and worst[0] >= -0.05 and g1 > g0


def early_legres30(prefix: str) -> bool:
    """Rally run 13 (D-153): run 12's early-legres lines unchanged, plus (coach, experiment design, RL) feeder-ball
    contact on balls that need a move to the left or back (scripts/diag/feeder_speed_envelope.py) up on the parent."""
    ok = early_legres(prefix)
    d0 = json.load(open(f"{prefix}-parent-early-dir.json"))["directions"]
    d1 = json.load(open(f"{prefix}-early-dir.json"))["directions"]
    con = lambda d: sum(d[k]["contact"] * d[k]["feeds"] for k in ("left", "back")) / max(d["left"]["feeds"] + d["back"]["feeds"], 1)  # noqa: E731
    g0, g1 = con(d0), con(d1)
    print(f"early: left + back feeder-ball contact {g0:.4f} -> {g1:.4f} ({100 * (g1 - g0):+.1f}; kill if not up); left legal "
          f"{d0['left']['legal']} -> {d1['left']['legal']}, back legal {d0['back']['legal']} -> {d1['back']['legal']}")
    return ok and g1 > g0


def early_lamr2(prefix: str) -> bool:
    """Rally run 14 (D-154): run 12's early-legres lines unchanged, plus left + back feeder-ball contact (the direction
    split) up on the parent by at least 2 points (round 36: an engagement line needs a margin, not just "up")."""
    ok = early_legres(prefix)
    d0 = json.load(open(f"{prefix}-parent-early-dir.json"))["directions"]
    d1 = json.load(open(f"{prefix}-early-dir.json"))["directions"]
    con = lambda d: sum(d[k]["contact"] * d[k]["feeds"] for k in ("left", "back")) / max(d["left"]["feeds"] + d["back"]["feeds"], 1)  # noqa: E731
    g0, g1 = con(d0), con(d1)
    print(f"early: left + back feeder-ball contact {g0:.4f} -> {g1:.4f} ({100 * (g1 - g0):+.1f}; kill below +2.0); left legal "
          f"{d0['left']['legal']} -> {d1['left']['legal']}, back legal {d0['back']['legal']} -> {d1['back']['legal']}")
    return ok and g1 >= g0 + 0.02


def early_teacher30(prefix: str) -> bool:
    """Rally run 17 (D-157): run 14's early lines (early_lamr2) unchanged, plus the used line (round 39: experiment design,
    architecture): the same checkpoint and seed with the teacher input zeroed (PICKLEBOT_TEACHER_GAIN=0) must lose at
    least 3 points of left + back feeder-ball contact."""
    ok = early_lamr2(prefix)
    d1 = json.load(open(f"{prefix}-early-dir.json"))["directions"]
    dz = json.load(open(f"{prefix}-early-dir-zero.json"))["directions"]
    con = lambda d: sum(d[k]["contact"] * d[k]["feeds"] for k in ("left", "back")) / max(d["left"]["feeds"] + d["back"]["feeds"], 1)  # noqa: E731
    g1, gz = con(d1), con(dz)
    print(f"early: used line: left + back feeder-ball contact with the input {g1:.4f}, zeroed {gz:.4f} "
          f"({100 * (g1 - gz):+.1f}; kill below +3.0)")
    return ok and g1 >= gz + 0.03


R14 = "results/rally-18b-parent-early"  # run 14 model_27798's read on 4219967-4219971: the D-160 cumulative reference
CROSS_FH_29000 = "results/rally-18b-early-pairs.json"  # run 18b model_29000's read: the accepted cross_forehand regression


def p5_open(p: dict) -> tuple[float, list[float]]:
    """D-160: P(5+) counting a rally still running at the end of the read that already has 5 or more shots."""
    if "open_len_hist" not in p:
        raise KeyError("read has no open_len_hist (made before the audit fixes); re-read it")
    h, oh = p["len_hist"], p["open_len_hist"]
    k, n = sum(h[5:]) + sum(oh[5:]), sum(h) + sum(oh[5:])
    return k / max(n, 1), wilson(k, n)


def r19_guards(fam: dict, d: dict, ref: str = R14, cross_ref: str = CROSS_FH_29000, name: str = "run 14",
               cross_name: str = "model_29000") -> bool:
    """D-160's cumulative guards: no feeder family's contact more than 5 points below run 14 (cross_forehand: no more
    than 3 below run 18b model_29000's read), left + back feeder contact no more than 5 below run 14.
    D-193: `ref` / `cross_ref` change the reference reads (same slacks); the defaults replay the D-160 guards unchanged."""
    f14 = json.load(open(f"{ref}-pairs.json"))["per_family"]
    f29 = json.load(open(cross_ref))["per_family"]
    ok = True
    for k in f14:
        if k not in fam:
            continue
        r, slack, base = (f29[k]["contact"], 0.03, cross_name) if k == "cross_forehand" else (f14[k]["contact"], 0.05, name)
        if fam[k]["contact"] < r - slack:
            print(f"guard: {k} contact {fam[k]['contact']:.4f} < {base} {r:.4f} - {slack} (KILL)")
            ok = False
    worst = min(((fam[k]["contact"] - f14[k]["contact"], k) for k in f14 if k in fam and k != "cross_forehand"), default=(0.0, None))
    print(f"guard: worst family contact vs {name} {100 * worst[0]:+.1f} ({worst[1]}; kill below -5); cross_forehand "
          f"{fam['cross_forehand']['contact']:.4f} vs {cross_name} {f29['cross_forehand']['contact']:.4f} (kill below -3)")
    d14 = json.load(open(f"{ref}-dir.json"))["directions"]
    con = lambda x: sum(x[k]["contact"] * x[k]["feeds"] for k in ("left", "back")) / max(x["left"]["feeds"] + x["back"]["feeds"], 1)  # noqa: E731
    g14, g1 = con(d14), con(d)
    print(f"guard: left + back feeder contact {g1:.4f} vs {name} {g14:.4f} ({100 * (g1 - g14):+.1f}; kill below -5)")
    return ok and g1 >= g14 - 0.05


def early_r19(prefix: str) -> bool:
    """Rally run 19 (D-160, panel round 41: run 18b continued from model_29000; experiment design's lines, sized from
    measured read noise): against the parent re-read on the same seeds, P(5+) (open rallies counted) up >= 1.0 point;
    partner-ball legal >= parent - 1.5; feeder-ball legal >= parent - 1.0 and >= run 14 - 2; D-160's cumulative family
    and left + back guards; run 18b's court / drill / move / falls lines unchanged."""
    ok = early_ceiling(prefix, engage_check=False)  # partner / feeder legal at run 18b's lines, court, drill, move, falls
    j0, j1 = json.load(open(f"{prefix}-parent-early-pairs.json")), json.load(open(f"{prefix}-early-pairs.json"))
    q0, _ = p5_open(j0["pairs"])
    q1, q1ci = p5_open(j1["pairs"])
    own0, _ = boot_low(j0["pairs"]["court_counts"], 1, 0)
    own1, _ = boot_low(j1["pairs"]["court_counts"], 1, 0)
    fed0, _ = boot_low(j0["pairs"]["court_counts"], 3, 2)
    fed1, _ = boot_low(j1["pairs"]["court_counts"], 3, 2)
    fed14, _ = boot_low(json.load(open(f"{R14}-pairs.json"))["pairs"]["court_counts"], 3, 2)
    print(f"early: P(5+) open {q0:.4f} -> {q1:.4f} {q1ci} ({100 * (q1 - q0):+.1f}; kill below +1.0); partner legal "
          f"{own0:.4f} -> {own1:.4f} (kill below {own0 - 0.015:.4f}); feeder legal {fed0:.4f} -> {fed1:.4f} (kill below "
          f"{max(fed0 - 0.01, fed14 - 0.02):.4f}: parent - 1, run 14 - 2)")
    g = r19_guards(j1["per_family"], json.load(open(f"{prefix}-early-dir.json"))["directions"])
    return ok and g and q1 >= q0 + 0.01 and own1 >= own0 - 0.015 and fed1 >= fed0 - 0.01 and fed1 >= fed14 - 0.02


def early_r21(prefix: str) -> bool:
    """Rally run 21 (D-162): early-r19's lines unchanged, plus experiment design's parallel line: feeder-ball legal in
    the pairs read with the feeder ball delayed 3 s (PREFIX-{parent-early,early}-pairs3.json) >= parent - 1.0."""
    ok = early_r19(prefix)
    p0 = json.load(open(f"{prefix}-parent-early-pairs3.json"))["pairs"]
    p1 = json.load(open(f"{prefix}-early-pairs3.json"))["pairs"]
    f0, _ = boot_low(p0["court_counts"], 3, 2)
    f1, _ = boot_low(p1["court_counts"], 3, 2)
    print(f"early: feeder-ball legal at a 3 s refeed delay {f0:.4f} -> {f1:.4f} (kill below {f0 - 0.01:.4f}); P(5+) open "
          f"{p5_open(p0)[0]:.4f} -> {p5_open(p1)[0]:.4f} (reported)")
    return ok and f1 >= f0 - 0.01


def r19_gate(prefix: str, tag: str) -> bool:
    """Rally run 19's endpoint success (D-160, read once): P(5+) (open rallies counted) >= parent + 2.0 points with a
    Wilson low above the parent's point; partner-ball legal >= parent - 1.5; feeder-ball legal >= run 14 - 2; sides
    within 3 points; court falls <= 4 %; D-160's cumulative family and left + back guards on the endpoint reads."""
    j, j0 = json.load(open(f"{prefix}-target.json")), json.load(open(f"{prefix}-parent-early-pairs.json"))
    p = j["pairs"]
    q0, _ = p5_open(j0["pairs"])
    q1, q1ci = p5_open(p)
    own0, _ = boot_low(j0["pairs"]["court_counts"], 1, 0)
    own, _ = boot_low(p["court_counts"], 1, 0)
    fed, _ = boot_low(p["court_counts"], 3, 2)
    fed14, _ = boot_low(json.load(open(f"{R14}-pairs.json"))["pairs"]["court_counts"], 3, 2)
    P = pair_stats(p)
    gap = abs(P["sides"]["A"] - P["sides"]["B"])
    falls = json.load(open(f"results/stage5f-{tag}-summary.json"))["falls_court"]
    g = r19_guards(j["per_family"], json.load(open(f"{prefix}-endpoint-dir.json"))["directions"])
    ok = (q1 >= q0 + 0.02 and q1ci[0] > q0 and own >= own0 - 0.015 and fed >= fed14 - 0.02 and gap <= 0.03
          and falls <= 0.04 and g)
    print(f"run 19 gate: P(5+) open {q1:.4f} {q1ci} (>= parent {q0:.4f} + 0.02, low above {q0:.4f}); partner legal {own:.4f} "
          f"(>= {own0 - 0.015:.4f}); feeder legal {fed:.4f} (>= {fed14 - 0.02:.4f}); gap {100 * gap:.1f} (<= 3); falls "
          f"{falls} (<= 0.04): {'PASS' if ok else 'not met'}")
    return ok


def d1s2_gate(prefix: str, tag: str, ref_name: str = "22b") -> bool:
    """D-193 stage-2 run verdict (22b's residual re-climbed on the d1 base): paired against the parent 22b model_30200 read
    on the same seeds (PREFIX-parent-early-{pairs,dir}.json, its own base): P(5+) open >= parent + 2.0 with a Wilson low
    above the parent's point; partner-ball legal >= parent - 1.5; feeder-ball legal >= parent - 1.0; sides within 3; court
    falls <= 4 % (the h5f battery); D-160's guards with the same slacks against the parent's reads. The promotion gate
    (r19-gate against run 14) is computed and reported separately and unchanged."""
    j, j0 = json.load(open(f"{prefix}-target.json")), json.load(open(f"{prefix}-parent-early-pairs.json"))
    p = j["pairs"]
    q0, _ = p5_open(j0["pairs"])
    q1, q1ci = p5_open(p)
    own0, _ = boot_low(j0["pairs"]["court_counts"], 1, 0)
    own, _ = boot_low(p["court_counts"], 1, 0)
    fed0, _ = boot_low(j0["pairs"]["court_counts"], 3, 2)
    fed, _ = boot_low(p["court_counts"], 3, 2)
    P = pair_stats(p)
    gap = abs(P["sides"]["A"] - P["sides"]["B"])
    falls = json.load(open(f"results/stage5f-{tag}-summary.json"))["falls_court"]
    g = r19_guards(j["per_family"], json.load(open(f"{prefix}-endpoint-dir.json"))["directions"],
                   ref=f"{prefix}-parent-early", cross_ref=f"{prefix}-parent-early-pairs.json", name=ref_name, cross_name=ref_name)
    ok = (q1 >= q0 + 0.02 and q1ci[0] > q0 and own >= own0 - 0.015 and fed >= fed0 - 0.01 and gap <= 0.03
          and falls <= 0.04 and g)
    print(f"d1 stage-2 run verdict: P(5+) open {q1:.4f} {q1ci} (>= {ref_name} {q0:.4f} + 0.02, low above {q0:.4f}); partner legal "
          f"{own:.4f} (>= {own0 - 0.015:.4f}); feeder legal {fed:.4f} (>= {fed0 - 0.01:.4f}); gap {100 * gap:.1f} (<= 3); "
          f"falls {falls} (<= 0.04): {'PASS' if ok else 'not met'}")
    return ok


def early_sched(prefix: str) -> bool:
    """Rally run 18 (the optimizer restart after the KL check; the user approved judging on the rally numbers): run 12's
    early-legres guard lines without its reach_deep + fast engagement line, D-148's family-contact guard, left + back
    feeder-ball contact no more than 5 points below the parent, and the engagement line: P(5+) in the pairs read up on
    the parent by at least 2 points (the 1e-4 sweep arm gained 3.8 in 400 iterations)."""
    ok = early_ceiling(prefix, engage_check=False)
    f0 = json.load(open(f"{prefix}-parent-early-pairs.json"))["per_family"]
    f1 = json.load(open(f"{prefix}-early-pairs.json"))["per_family"]
    worst = min(((f1[k]["contact"] - f0[k]["contact"], k) for k in f0 if k in f1), default=(0.0, None))
    d0 = json.load(open(f"{prefix}-parent-early-dir.json"))["directions"]
    d1 = json.load(open(f"{prefix}-early-dir.json"))["directions"]
    con = lambda d: sum(d[k]["contact"] * d[k]["feeds"] for k in ("left", "back")) / max(d["left"]["feeds"] + d["back"]["feeds"], 1)  # noqa: E731
    g0, g1 = con(d0), con(d1)
    P0 = pair_stats(json.load(open(f"{prefix}-parent-early-pairs.json"))["pairs"])
    P1 = pair_stats(json.load(open(f"{prefix}-early-pairs.json"))["pairs"])
    print(f"early: worst feeder-family contact change {100 * worst[0]:+.1f} points ({worst[1]}; kill below -5)")
    print(f"early: left + back feeder-ball contact {g0:.4f} -> {g1:.4f} ({100 * (g1 - g0):+.1f}; kill below -5)")
    print(f"early: engagement: P(5+) {P0['p5']:.4f} -> {P1['p5']:.4f} {P1['p5_ci']} ({100 * (P1['p5'] - P0['p5']):+.1f}; "
          f"kill below +2.0)")
    return ok and worst[0] >= -0.05 and g1 >= g0 - 0.05 and P1["p5"] >= P0["p5"] + 0.02


def sched_gate(prefix: str, tag: str) -> bool:
    """Rally run 18's endpoint success (pre-registered, read once): P(5+) Wilson low above rally run 14's endpoint P(5+)
    (results/rally-14-target.json), partner-ball legal >= run 14 - 3 points, feeder-ball legal >= run 14 - 2 points,
    sides within 3 points, court falls <= 4 %. M1 and the target are read as usual."""
    p, q = json.load(open(f"{prefix}-target.json"))["pairs"], json.load(open("results/rally-14-target.json"))["pairs"]
    P, Q = pair_stats(p), pair_stats(q)
    own, _ = boot_low(p["court_counts"], 1, 0)
    fed, _ = boot_low(p["court_counts"], 3, 2)
    own14, _ = boot_low(q["court_counts"], 1, 0)
    fed14, _ = boot_low(q["court_counts"], 3, 2)
    falls = json.load(open(f"results/stage5f-{tag}-summary.json"))["falls_court"]
    gap = abs(P["sides"]["A"] - P["sides"]["B"])
    ok = P["p5_ci"][0] > Q["p5"] and own >= own14 - 0.03 and fed >= fed14 - 0.02 and gap <= 0.03 and falls <= 0.04
    print(f"run 18 gate: P(5+) {P['p5']:.4f} {P['p5_ci']} (low above run 14's {Q['p5']:.4f}); partner-ball legal {own:.4f} "
          f"(>= {own14 - 0.03:.4f}); feeder-ball legal {fed:.4f} (>= {fed14 - 0.02:.4f}); gap {100 * gap:.1f} (<= 3); falls "
          f"{falls} (<= 0.04): {'PASS' if ok else 'not met'}")
    return ok


def teacher_gate(prefix: str, tag: str) -> bool:
    """D-156: the e4 teacher's gate to distillation (pre-registered, read once on the endpoint's M1 read): feeder-ball
    legal >= 0.85 with a court-bootstrap low >= 0.84, partner-ball legal >= 0.685, sides within 3 points, court falls
    <= 4 %. M1 is never claimed from the teacher (it sees privileged inputs)."""
    p = json.load(open(f"{prefix}-target.json"))["pairs"]
    P = pair_stats(p)
    own, _ = boot_low(p["court_counts"], 1, 0)
    fed, fed_lo = boot_low(p["court_counts"], 3, 2)
    falls = json.load(open(f"results/stage5f-{tag}-summary.json"))["falls_court"]
    gap = abs(P["sides"]["A"] - P["sides"]["B"])
    ok = fed >= 0.85 and fed_lo >= 0.84 and own >= 0.685 and gap <= 0.03 and falls <= 0.04
    print(f"teacher gate: feeder-ball legal {fed:.4f} (low {fed_lo:.4f}; >= 0.85, low >= 0.84); partner-ball legal "
          f"{own:.4f} (>= 0.685); gap {100 * gap:.1f} (<= 3); falls {falls} (<= 0.04): {'PASS' if ok else 'not met'}")
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
    p5, ci = P["p5"], P["p5_ci"]
    tp = json.load(open(f"{prefix}-target.json"))["pairs"]
    if "open_len_hist" in tp:  # D-160: the primary P(5+) counts open rallies that already have 5 shots (old one above)
        p5, ci = p5_open(tp)
        print(f"target P(5+) with open rallies counted (D-160, primary): {p5:.4f} {ci}")
    met = P["rallies"] >= 1000 and p5 >= 0.80 and ci[0] >= 0.78 and gap <= 0.03 and falls <= 0.04
    print("TARGET MET" if met else "target not met")
    return met


def boot_low(cc: list, num: int, den: int, reps: int = 2000) -> tuple[float, float]:
    """D-137: (point, court-cluster bootstrap 95 % lower bound) of sum(cc[:, num]) / sum(cc[:, den]); courts resampled
    with replacement, generator seed 0 (rally-milestones.md)."""
    import numpy as np
    c = np.asarray(cc, dtype=np.float64)
    c = c[c[:, den] > 0]
    if len(c) == 0:
        return 0.0, 0.0
    rng = np.random.default_rng(0)
    idx = rng.integers(0, len(c), size=(reps, len(c)))
    r = c[idx, num].sum(1) / np.maximum(c[idx, den].sum(1), 1.0)
    return float(c[:, num].sum() / c[:, den].sum()), float(np.percentile(r, 2.5))


def milestone(prefix: str, tag: str) -> bool:
    """M1 (rally-milestones.md) on PREFIX-target.json (the endpoint's pre-registered contact read)."""
    p = json.load(open(f"{prefix}-target.json"))["pairs"]
    P = pair_stats(p)
    own, own_lo = boot_low(p["court_counts"], 1, 0)
    fed, fed_lo = boot_low(p["court_counts"], 3, 2)
    falls = json.load(open(f"results/stage5f-{tag}-summary.json"))["falls_court"]
    gap = abs(P["sides"]["A"] - P["sides"]["B"])
    hist, n = p["len_hist"], p["rallies"]
    print(f"M1: partner-ball legal {own:.4f} (bootstrap low {own_lo:.4f}; bar >= 0.50, low >= 0.49); feeder-ball legal "
          f"{fed:.4f} (low {fed_lo:.4f}; bar >= 0.85, low >= 0.84); sides {P['sides']} (gap {100 * gap:.1f}, <= 3); "
          f"court falls {falls} (<= 0.04); rallies {n}")
    print(f"M1 reported: P(3+) {sum(hist[3:]) / max(n, 1):.4f}; P(5+) {P['p5']:.4f}; falls per shot "
          f"{ {k: v['falls_per_shot'] for k, v in p['sides'].items()} }; started {p.get('started')}")
    met = n >= 1000 and own >= 0.50 and own_lo >= 0.49 and fed >= 0.85 and fed_lo >= 0.84 and gap <= 0.03 and falls <= 0.04
    print("M1 MET" if met else "M1 not met")
    return met


def _main() -> None:
    mode, prefix = sys.argv[1], sys.argv[2]
    if mode == "early":
        sys.exit(0 if early(prefix) else 1)
    if mode == "early-continuation":
        sys.exit(0 if early_continuation(prefix) else 1)
    if mode == "early-weak":
        sys.exit(0 if early_weak(prefix) else 1)
    if mode == "early-pace":
        sys.exit(0 if early_pace(prefix) else 1)
    if mode == "early-ceiling":
        sys.exit(0 if early_ceiling(prefix) else 1)
    if mode == "early-ceiling-own":
        sys.exit(0 if early_ceiling_own(prefix) else 1)
    if mode == "early-feedbonus":
        sys.exit(0 if early_feedbonus(prefix) else 1)
    if mode == "early-legres":
        sys.exit(0 if early_legres(prefix) else 1)
    if mode == "early-legres30":
        sys.exit(0 if early_legres30(prefix) else 1)
    if mode in ("early-lamr2", "early-lamr3", "early-teacher"):  # D-155/D-156: run 14's early lines unchanged
        sys.exit(0 if early_lamr2(prefix) else 1)
    if mode == "early-teacher30":
        sys.exit(0 if early_teacher30(prefix) else 1)
    if mode == "early-r21":
        sys.exit(0 if early_r21(prefix) else 1)
    if mode == "early-r19":
        sys.exit(0 if early_r19(prefix) else 1)
    if mode == "r19-gate":
        sys.exit(0 if r19_gate(prefix, sys.argv[3]) else 1)
    if mode == "d1s2-gate":
        sys.exit(0 if d1s2_gate(prefix, sys.argv[3], *(sys.argv[4:5])) else 1)  # optional 4th: the parent's label
    if mode == "early-sched":
        sys.exit(0 if early_sched(prefix) else 1)
    if mode == "sched-gate":
        sys.exit(0 if sched_gate(prefix, sys.argv[3]) else 1)
    if mode == "teacher-gate":
        sys.exit(0 if teacher_gate(prefix, sys.argv[3]) else 1)
    if mode == "m1":
        sys.exit(0 if milestone(prefix, sys.argv[3]) else 1)
    if mode == "target":
        sys.exit(0 if target(prefix, sys.argv[3]) else 1)
    print(f"rally_check: unknown mode {mode!r}")  # audit 2026-10-28: unknown modes used to run target() and exit 0
    sys.exit(3)


if __name__ == "__main__":
    # Exit codes: 0 pass / met, 1 kill / not met, 2 the check itself crashed (missing or malformed read: never read it
    # as a kill), 3 unknown mode. Drivers from run 18b on act on exit 1 only.
    try:
        _main()
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        print(f"rally_check: CHECK CRASHED ({type(e).__name__}); not a verdict")
        sys.exit(2)
