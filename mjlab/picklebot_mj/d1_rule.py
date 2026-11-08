"""D-192 d1 coded lines (panel round 59, mjlab/results/footwork-review.md): the base rebuilt by the s5c-18 kickstart
recipe with fw1b-S model_16600 as the move-episode teacher (the one change), keeping latent-07.

1. teacher_check (experiment design): the teacher and the old walking teacher (model_15900) on the kickstart's own move
   geometry (Picklebot-Footwork-Measure60-Court-G1: MoveDrill spots 0.5-3 m in the half court), mean actions. TEACHER-OK
   if, in both left (2) and back (4), the teacher's sustained p50 >= 1.6 m/s and >= the walker's + 0.3; else
   TEACHER-SLOW (the kickstart drill never asks for speed: stop and re-ask the panel; the drill is not swapped quietly).
2. kick_kill (RL + motion, mse_hit per RL): mean over kickstart log rows 300-360 (about 30 % of 6,900 s at s5c-18's pace):
   mse_move > 0.142 (twice the floor test's all-joint 0.071 at lam 3) -> KILL-NO-FIT; mse_hit > 0.0017 (twice s5c-18's
   0.00085 over the same rows) -> KILL-HIT-INTERFERE; else CONTINUE.
3. base_gate (experiment design), paired against RES_BASE model_32874:
   agility on Picklebot-Footwork-Measure60-L3Base-G1 (mean actions): D-188 validity first (falls <= 2 x parent, worst
   untimed arrival >= 0.80, (fallen + censored) / spots <= 0.15) else INVALID; R_LB = mean over left / back of sustained
   p50 / the specialist's (fw1d-C); AGILE if R_LB >= 0.85 and the first-step p50 in left and back <= the parent's;
   CAP-HELD if R_LB <= 0.70; else MIXED.
   hitting on the D-086 battery (h5c_eval.sh, Court-L3 / Drill3-Prior5-L3): RETAINS only if main >= parent - 0.02,
   passing cells >= parent - 2, no drill5b family more than 0.05 below the parent, style <= parent + 0.15, move-drill
   falls <= max(0.01, parent), court falls <= parent + 0.01; else REJECTED. PROTOCOL-DRIFT is flagged (reported) if the
   parent's main differs from its archived 0.7993 by more than 0.03.
   Base verdict: INVALID / CAP-HELD / REJECTED -> stop and re-ask the panel; AGILE or MIXED with RETAINS -> BASE-PASS
   (the residual re-climb, its own pre-registered lines).
"""

from __future__ import annotations

import json

from picklebot_mj import bodyspeed_rule as bsr
from picklebot_mj.ballidx_rule import quantile

LEFT, BACK = 2, 4
TEACHER_MIN, TEACHER_GAIN = 1.6, 0.3
KILL_ROWS = (300, 360)
MSE_MOVE_MAX, MSE_HIT_MAX = 0.142, 0.0017
R_LB_AGILE, R_LB_CAP = 0.85, 0.70
ARCHIVED_MAIN = 0.7993  # results/stage5c-s5c-18-court.json (dev 4200790)


def agility(d: dict) -> dict:
    """One footwork_eval / stage2_eval JSON -> falls, validity inputs, per-sector speeds and first-step p50."""
    c = d["move_drill"]["footwork"]
    s = bsr.sectors(c)
    fin = [x["arrived"] + x["timed_out"] + x["fell"] for x in s]
    return {"falls": 1000.0 * d["robot_falls"] / (d["envs"] * d["sim_seconds"]),
            "worst_arrival": min(x["arrival"] for x in s if x["arrival"] is not None),
            "fallen_censored_share": (sum(c["fell"]) + sum(c["censored"])) / max(1, sum(x["spots"] for x in s)),
            "sustained_p50": [x["sustained_p50"] for x in s], "peak_p50": [x["peak_p50"] for x in s],
            "first_step_p50": [quantile(c["first_step_hist"][i], 0.5, c["first_step_bin_s"]) for i in range(len(s))],
            "settled": [round(c["settled"][i] / max(1, f), 3) for i, f in enumerate(fin)]}


def teacher_check(teacher: dict, walker: dict) -> tuple[str, list[str]]:
    t, w = agility(teacher), agility(walker)
    lines, ok = [], True
    for i, name in ((LEFT, "left"), (BACK, "back")):
        ts, ws = t["sustained_p50"][i], w["sustained_p50"][i]
        good = ts is not None and ts >= TEACHER_MIN and (ws is None or ts >= ws + TEACHER_GAIN)
        ok &= good
        lines.append(f"{name}: teacher {ts} vs walker {ws} m/s (need >= {TEACHER_MIN} and >= walker + {TEACHER_GAIN}) "
                     f"-> {'ok' if good else 'SLOW'}")
    return ("TEACHER-OK" if ok else "TEACHER-SLOW"), lines


def kick_rows(log_path: str) -> list[dict]:
    rows = []
    for line in open(log_path, errors="ignore"):
        if line.startswith('{"it"'):
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return rows


def kick_kill(rows: list[dict]) -> tuple[str, str] | None:
    """None until row KILL_ROWS[1] exists; then (verdict, line)."""
    lo, hi = KILL_ROWS
    if len(rows) < hi:
        return None
    w = rows[lo:hi]
    mv = sum(r["mse_move"] for r in w) / len(w)
    mh = sum(r["mse_hit"] for r in w) / len(w)
    v = "KILL-NO-FIT" if mv > MSE_MOVE_MAX else "KILL-HIT-INTERFERE" if mh > MSE_HIT_MAX else "CONTINUE"
    return v, (f"rows {lo + 1}-{hi}: mse_move {mv:.4f} (kill > {MSE_MOVE_MAX}), mse_hit {mh:.5f} (kill > {MSE_HIT_MAX}); "
               f"first-20 mse_move {sum(r['mse_move'] for r in rows[:20]) / 20:.4f} (reported) -> {v}")


def agility_verdict(child: dict, parent: dict, spec_sectors: list[dict]) -> tuple[str, dict]:
    c, p = agility(child), agility(parent)
    for a in (c, p):
        a["R_LB"] = sum(a["sustained_p50"][i] / spec_sectors[i]["sustained_p50"] for i in (LEFT, BACK)) / 2
    valid = (c["falls"] <= 2 * p["falls"] and c["worst_arrival"] >= 0.80 and c["fallen_censored_share"] <= 0.15)
    fs_ok = all(c["first_step_p50"][i] is not None and p["first_step_p50"][i] is not None
                and c["first_step_p50"][i] <= p["first_step_p50"][i] for i in (LEFT, BACK))
    v = ("INVALID" if not valid else "AGILE" if c["R_LB"] >= R_LB_AGILE and fs_ok
         else "CAP-HELD" if c["R_LB"] <= R_LB_CAP else "MIXED")
    return v, {"child": c, "parent": p, "valid": valid, "first_step_ok": fs_ok}


def _cells_pass(court: dict) -> int:
    cells = court.get("per_zone_family", {})
    return sum(1 for v in cells.values() if v["episodes"] >= 30 and v["legal_return"] >= 0.75)


def hitting(tag: str) -> dict:
    R = f"results/stage5c-{tag}"
    court, move = json.load(open(f"{R}-court.json")), json.load(open(f"{R}-move.json"))
    d5b = json.load(open(f"{R}-drill5b.json"))
    return {"main": court["legal_return_rate"], "cells": _cells_pass(court), "n_cells": len(court.get("per_zone_family", {})),
            "families": {f: v["legal_return"] for f, v in d5b["per_family"].items()},
            "style": json.load(open(f"{R}-style.json"))["nearest_clip_distance_median"],
            "falls_court": court["robot_fall_rate_per_episode"],
            "falls_move": move.get("robot_fall_rate_per_episode", 0.0)}


def retention(c: dict, p: dict) -> tuple[str, list[str], bool]:
    worst = min(((c["families"][f] - p["families"][f], f) for f in p["families"] if f in c["families"]), default=(0.0, ""))
    checks = [
        (c["main"] >= p["main"] - 0.02, f"main {c['main']:.4f} >= parent {p['main']:.4f} - 0.02"),
        (c["cells"] >= p["cells"] - 2, f"passing cells {c['cells']} >= parent {p['cells']} - 2"),
        (worst[0] >= -0.05, f"worst drill5b family {worst[1]} {worst[0]:+.3f} >= -0.05"),
        (c["style"] <= p["style"] + 0.15, f"style {c['style']:.3f} <= parent {p['style']:.3f} + 0.15"),
        (c["falls_move"] <= max(0.01, p["falls_move"]), f"move falls {c['falls_move']:.4f} <= max(0.01, {p['falls_move']:.4f})"),
        (c["falls_court"] <= p["falls_court"] + 0.01, f"court falls {c['falls_court']:.4f} <= parent {p['falls_court']:.4f} + 0.01"),
    ]
    lines = [f"[{'pass' if ok else 'FAIL'}] {t}" for ok, t in checks]
    drift = abs(p["main"] - ARCHIVED_MAIN) > 0.03
    return ("RETAINS" if all(ok for ok, _ in checks) else "REJECTED"), lines, drift


def base_verdict(agility_v: str, retention_v: str) -> str:
    if agility_v in ("INVALID", "CAP-HELD"):
        return agility_v
    if retention_v != "RETAINS":
        return "REJECTED"
    return "BASE-PASS"


# D-193 (panel round 60, coach / motion / RL; experiment design voted A): the teacher check's 1.6 m/s line was
# mis-calibrated for 0.5-3 m spots (the sustained window is capped by spot length); TEACHER-SLOW stays recorded as failed.
# A fresh-seed premise check on the metric the three C votes share, plus D-188's existing validity numbers (no new
# threshold beyond the shared one, which was set after the 0.35-0.41 s gap had been seen; recorded as such).
PREMISE_FIRST_STEP_GAIN = 0.25  # s


def premise_check(teacher: dict, walker: dict) -> tuple[str, list[str]]:
    t, w = agility(teacher), agility(walker)
    lines, ok = [], True
    for i, name in ((LEFT, "left"), (BACK, "back")):
        tf, wf = t["first_step_p50"][i], w["first_step_p50"][i]
        good = tf is not None and wf is not None and tf <= wf - PREMISE_FIRST_STEP_GAIN
        ok &= good
        lines.append(f"{name}: first-step p50 teacher {tf} vs walker {wf} s (need <= walker - {PREMISE_FIRST_STEP_GAIN}) "
                     f"-> {'ok' if good else 'FAIL'}")
    valid = t["worst_arrival"] >= 0.80 and t["fallen_censored_share"] <= 0.15
    ok &= valid
    lines.append(f"teacher validity (D-188): worst untimed arrival {t['worst_arrival']:.3f} >= 0.80, fallen + censored "
                 f"{t['fallen_censored_share']:.3f} <= 0.15 -> {'ok' if valid else 'FAIL'}")
    lines.append(f"reported: peak p50 L/B teacher {t['peak_p50'][LEFT]}/{t['peak_p50'][BACK]} vs walker "
                 f"{w['peak_p50'][LEFT]}/{w['peak_p50'][BACK]}; settled L/B {t['settled'][LEFT]}/{t['settled'][BACK]} vs "
                 f"{w['settled'][LEFT]}/{w['settled'][BACK]}; falls {t['falls']:.3f} vs {w['falls']:.3f} per 1,000 env-s")
    return ("PREMISE-OK" if ok else "PREMISE-FAIL"), lines


# ---------------------------------------------------------------------------------------------------------------------
# Stage 2 (D-194: D-193 rulings, experiment design round 59, amended in round 61): 22b's residual (model_30200)
# re-climbed on the d1 base. Kill at +360, from the training log, against 22b's last 100 iterations before model_30200
# (30100-30199; falls 1.574, legal_return 0.7549 per 1,000 env-s / per ended episode): falls per 1,000 env-s over
# +341-360 > 2 x reference -> KILL-UNSTABLE; mean Episode_Reward/legal_return over +341-360 < reference - 0.05 ->
# KILL-NO-HIT. Round 61 rejected a same-age reference (22b's +341-360 after its resume from model_29000): 22b's rise from
# 0.60 to 0.755 was learning, not a log artefact, and its own continuation from model_30200 (30201-30600) stays inside the
# literal line in every 20-iteration window. From the +360 checkpoint's Measure60-RallyLamR2 read (PICKLEBOT_RES_BASE =
# the d1 base), D-188 validity against 22b's read on its own base (same task, same seed): falls > 2 x parent, worst
# untimed arrival < 0.80 or (fallen + censored) / spots > 0.15 -> KILL-NO-ARRIVE.
import re as _re  # noqa: E402

S2_KILL_ITERS = (341, 360)
S2_REF_ITERS = range(30100, 30200)


def log_blocks(path: str) -> dict[int, str]:
    """rsl_rl training log -> {iteration: block text}."""
    t = open(path, errors="ignore").read()
    parts = _re.split(r"Learning iteration (\d+)/\d+", t)
    return {int(parts[i]): parts[i + 1] for i in range(1, len(parts) - 1, 2)}


def window_stats(blocks: dict[int, str], its, envs: int) -> tuple[float, float]:
    """(falls per 1,000 env-s, mean Episode_Reward/legal_return) over the given iterations."""
    import os
    import sys
    import tempfile
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts", "diag"))
    from falls_by_length import falls_per_1000_env_s
    text = "".join(f"Learning iteration {i}/0\n{blocks[i]}" for i in its if i in blocks)
    with tempfile.NamedTemporaryFile("w", suffix=".log", delete=False) as f:
        f.write(text)
    try:
        falls = falls_per_1000_env_s(f.name, envs=envs)[0]
    finally:
        os.unlink(f.name)
    lr = [float(x) for x in _re.findall(r"Episode_Reward/legal_return: ([-0-9.]+)", text)]
    return falls, (sum(lr) / len(lr) if lr else float("nan"))


def s2_window_verdict(f1: float, l1: float, f0: float, l0: float) -> str:
    return "KILL-UNSTABLE" if f1 > 2 * f0 else "KILL-NO-HIT" if not l1 >= l0 - 0.05 else "CONTINUE"


def s2_train_kill(child_log: str, start_it: int, ref_log: str, envs: int, ref_its=S2_REF_ITERS) -> tuple[str, str] | None:
    """None until iteration start_it + 361 has begun (so +360's block is complete); then (verdict, line)."""
    b = log_blocks(child_log)
    lo, hi = S2_KILL_ITERS
    if start_it + hi + 1 not in b:
        return None
    f1, l1 = window_stats(b, range(start_it + lo, start_it + hi + 1), envs)
    f0, l0 = window_stats(log_blocks(ref_log), ref_its, envs)
    v = s2_window_verdict(f1, l1, f0, l0)
    fr, lrr = window_stats(b, range(start_it + 241, start_it + 261), envs)
    return v, (f"+{lo}-{hi}: falls per 1,000 env-s {f1:.2f} (kill > 2 x 22b {f0:.2f}); legal_return {l1:.4f} "
               f"(kill < 22b {l0:.4f} - 0.05) -> {v}; reported +241-260: falls {fr:.2f}, legal_return {lrr:.4f}")


def s2_arrive_kill(read: dict, parent_read: dict) -> tuple[str, str]:
    a, p = agility(read), agility(parent_read)
    ok = a["falls"] <= 2 * p["falls"] and a["worst_arrival"] >= 0.80 and a["fallen_censored_share"] <= 0.15
    v = "CONTINUE" if ok else "KILL-NO-ARRIVE"
    return v, (f"Measure60 read: falls {a['falls']:.2f} (kill > 2 x 22b {p['falls']:.2f}); worst untimed arrival "
               f"{a['worst_arrival']:.3f} (kill < 0.80); fallen + censored {a['fallen_censored_share']:.3f} (kill > 0.15) -> {v}")


def s2_verdict(rally_pass: bool, agility_v: str) -> str:
    """D1-PASS / ADOPT-AGILITY-NOT-MET mean adopt the child; they show the base caused a rally gain only if the child
    also beats the 22b model_30600 read (reported, D-194)."""
    if rally_pass and agility_v == "AGILE":
        return "D1-PASS"
    if rally_pass and agility_v == "MIXED":
        return "ADOPT-AGILITY-NOT-MET"
    return "PANEL"


# D-196 d1s3 (panel round 62): the speed lines are paired with the untrained composite Z (22b on the d1 base) on the
# same seed. Kill at +360: KILL-SLOWED if sustained p50 left or back < Z's - 0.15 m/s (motion); KILL-NO-ARRIVE if D-188
# validity fails against Z. Endpoint: AGILE-KEPT if R_LB >= Z's - 0.03 (RL) and first-step p50 left and back <= Z's +
# 0.05 s (motion); else SPEED-LOST.
S3_SLOW_M_S, S3_RLB_SLACK, S3_FIRST_SLACK = 0.15, 0.03, 0.05


def s3_speed_kill(read: dict, z_read: dict) -> tuple[str, str]:
    a, z = agility(read), agility(z_read)
    slow = [n for i, n in ((LEFT, "left"), (BACK, "back"))
            if not (a["sustained_p50"][i] is not None and a["sustained_p50"][i] >= z["sustained_p50"][i] - S3_SLOW_M_S)]
    valid = a["falls"] <= 2 * z["falls"] and a["worst_arrival"] >= 0.80 and a["fallen_censored_share"] <= 0.15
    v = "KILL-SLOWED" if slow else "KILL-NO-ARRIVE" if not valid else "CONTINUE"
    return v, (f"Measure60 read: sustained L/B {a['sustained_p50'][LEFT]}/{a['sustained_p50'][BACK]} vs Z "
               f"{z['sustained_p50'][LEFT]}/{z['sustained_p50'][BACK]} (kill below Z - {S3_SLOW_M_S}); falls {a['falls']:.2f} "
               f"(kill > 2 x Z {z['falls']:.2f}); worst untimed arrival {a['worst_arrival']:.3f} (kill < 0.80); fallen + "
               f"censored {a['fallen_censored_share']:.3f} (kill > 0.15) -> {v}")


def s3_agility_kept(read: dict, z_read: dict, spec_sectors: list[dict]) -> tuple[str, list[str]]:
    a, z = agility(read), agility(z_read)
    rlb = lambda x: sum(x["sustained_p50"][i] / spec_sectors[i]["sustained_p50"] for i in (LEFT, BACK)) / 2  # noqa: E731
    ra, rz = rlb(a), rlb(z)
    lines = [f"R_LB {ra:.3f} vs Z {rz:.3f} (need >= Z - {S3_RLB_SLACK})"]
    ok = ra >= rz - S3_RLB_SLACK
    for i, n in ((LEFT, "left"), (BACK, "back")):
        fa, fz = a["first_step_p50"][i], z["first_step_p50"][i]
        good = fa is not None and fz is not None and fa <= fz + S3_FIRST_SLACK
        ok &= good
        lines.append(f"first step {n} {fa} vs Z {fz} s (need <= Z + {S3_FIRST_SLACK})")
    return ("AGILE-KEPT" if ok else "SPEED-LOST"), lines


# ---------------------------------------------------------------------------------------------------------------------
# D-199 d1s4 (panel round 64): the d1s3 child + ready_at_event. Kill at +360 adds, to D-194's training-log lines and
# D-196's speed lines (now against the parent d1s3 on the same seed):
# KILL-NO-DOSE: the per-event mean ready value over +341-360 is not above the +1-20 mean by more than 2 SE of the +1-20
# window (PICKLEBOT_READY_LOG rows: cumulative [sum, events, young, sum of squares] by env step); KILL-EVENTS: feeder
# fires per env step over iterations 100-300 exceed the parent's (d1s3's own training, same iterations) by > 10 %.
# Endpoint (paired with the parent; the control = d1s3 continued without the term, run only if the child is F-UP):
# F-UP feeder legal >= ref + 0.05 with the court-bootstrap low above ref's point; ABS-F feeder legal >= 0.80 (required
# for READY-PASS, D-198); rally = d1s2-gate against the parent; AGILE-KEPT against the parent; K3-KEPT k >= 3 legal
# >= parent - 0.01 (dose read); DOSE k = 0 pelvis-speed p50 at the fire <= parent - 0.05 (matched band, dose read).
# Precedence: KILL -> INVALID -> NO-DOSE -> READY-TIME -> READY-PASS -> READY-F -> READY-FAIL.
STEPS_PER_IT = 24


def _row_from(rows: list[dict], step: int) -> dict | None:
    """D-200 addendum (the D-199 addendum-2 lesson): the first logged row at or after `step` (windows are built from rows
    that exist, never from an edge no row covers)."""
    after = [r for r in rows if r["step"] >= step]
    return min(after, key=lambda r: r["step"]) if after else None


MIN_WINDOW_EVENTS = 1000


def _ready_window(rows: list[dict], it_lo: int, it_hi: int, start_it: int = 0) -> tuple[float, float, int]:
    """(mean, SE, events) of the per-event ready value between the first logged rows at or after iterations it_lo - 1 and
    it_hi after the resume at start_it (cumulative rows; the env step counter continues from start_it x STEPS_PER_IT on a
    resume). Fewer than MIN_WINDOW_EVENTS events -> (nan, nan, n): the caller reports NO-DATA, never a kill."""
    ra = _row_from(rows, (start_it + it_lo - 1) * STEPS_PER_IT)
    rb = None if ra is None else _row_from(rows, max((start_it + it_hi) * STEPS_PER_IT,
                                                      ra["step"] + (it_hi - it_lo + 1) * STEPS_PER_IT))
    if ra is None or rb is None or rb["step"] <= ra["step"]:
        return float("nan"), float("nan"), 0
    a, b = ra["ready"], rb["ready"]
    sm, n, sq = b[0] - a[0], b[1] - a[1], b[3] - a[3]
    if n < MIN_WINDOW_EVENTS:
        return float("nan"), float("nan"), int(n)
    mean = sm / n
    var = max(sq / n - mean * mean, 0.0)
    return mean, (var / n) ** 0.5, int(n)


def s4_dose_kill(rows: list[dict], start_it: int = 0) -> tuple[str, str]:
    m0, se0, n0 = _ready_window(rows, 1, 20, start_it)
    m1, _, n1 = _ready_window(rows, 341, 360, start_it)
    if n0 < MIN_WINDOW_EVENTS or n1 < MIN_WINDOW_EVENTS:
        return "NO-DATA", f"ready windows hold {n0} / {n1} events (< {MIN_WINDOW_EVENTS}): NO-DATA (not a kill)"
    ok = m1 > m0 + 2 * se0
    v = "CONTINUE" if ok else "KILL-NO-DOSE"
    return v, (f"ready per-event mean +1-20 {m0:.4f} (SE {se0:.4f}, n {n0}) -> +341-360 {m1:.4f} (n {n1}); "
               f"kill unless above +1-20 + 2 SE = {m0 + 2 * se0:.4f} -> {v}")


def _feeder_rate(pair_rows: list[dict], it_lo: int, it_hi: int, start_it: int = 0) -> float:
    a = _row_from(pair_rows, (start_it + it_lo) * STEPS_PER_IT)
    b = None if a is None else _row_from(pair_rows, max((start_it + it_hi) * STEPS_PER_IT, a["step"] + (it_hi - it_lo) * STEPS_PER_IT))
    if a is None or b is None or b["step"] <= a["step"]:
        return float("nan")
    return (b["feeder"] - a["feeder"]) / (b["step"] - a["step"])


def s4_events_kill(child_pairs: list[dict], parent_pairs: list[dict], child_start: int = 0,
                   parent_start: int = 0) -> tuple[str, str]:
    c = _feeder_rate(child_pairs, 100, 300, child_start)
    p = _feeder_rate(parent_pairs, 100, 300, parent_start)
    if c != c or p != p:
        return "NO-DATA", f"feeder-rate windows have no rows (child {c}, parent {p}): NO-DATA (not a kill)"
    ok = c <= 1.10 * p
    v = "CONTINUE" if ok else "KILL-EVENTS"
    return v, f"feeder fires per env step, iterations 100-300: child {c:.4f} vs parent {p:.4f} (kill > 1.10 x) -> {v}"


def f_up(child_pairs: dict, ref_pairs: dict) -> tuple[bool, str]:
    import sys as _sys
    _sys.path.insert(0, "scripts")
    import rally_check as rc
    fc, lo = rc.boot_low(child_pairs["court_counts"], 3, 2)
    fr, _ = rc.boot_low(ref_pairs["court_counts"], 3, 2)
    ok = fc >= fr + 0.05 and lo > fr
    return ok, f"feeder legal {fc:.4f} (low {lo:.4f}) vs {fr:.4f}: >= +0.05 and low above -> {'F-UP' if ok else 'not'}"


def s4_verdict(killed: bool, valid: bool, dose: bool, fup_parent: bool, fup_control: bool | None, abs_f: bool,
               rally: bool, agile: bool, k3: bool) -> str:
    if killed:
        return "KILL"
    if not valid:
        return "INVALID"
    if not dose:
        return "NO-DOSE"
    if fup_parent and fup_control is False:
        return "READY-TIME"
    if fup_parent and abs_f and rally and agile and k3:
        return "READY-PASS"
    if fup_parent and agile and k3:
        return "READY-F"
    return "READY-FAIL"


# ---------------------------------------------------------------------------------------------------------------------
# D-201 d1s5 (panel round 65): the d1s3 child trained with pair_rally_cap 5. Kill at +360: KILL-NO-SHARE when the feeder
# share of balls started on pair courts over iterations 100-300 is not >= the parent d1s3 run's share at the same
# iterations + 0.05 (PICKLEBOT_PAIR_LOG rows: split[0] = [pair-court feeder fires, pair-court hand-offs]). Endpoint F-BIN
# (D-172: feeder premises within launch bins): the 0-1 launch bin's feeder legal on the paired LR-0 dose runs (pair log
# "launch" outcome_feeds_legal, second half) >= parent + 0.05.
F_BIN_GAIN, SHARE_GAIN = 0.05, 0.05


def _pair_share(rows: list[dict], it_lo: int, it_hi: int, start_it: int) -> tuple[float, int]:
    a = _row_from(rows, (start_it + it_lo) * STEPS_PER_IT)
    b = None if a is None else _row_from(rows, max((start_it + it_hi) * STEPS_PER_IT, a["step"] + (it_hi - it_lo) * STEPS_PER_IT))
    if a is None or b is None or b["step"] <= a["step"]:
        return float("nan"), 0
    f = b["split"][0][0] - a["split"][0][0]
    h = b["split"][0][1] - a["split"][0][1]
    return (f / (f + h) if f + h else float("nan")), int(f + h)


def s5_share_kill(child_rows: list[dict], parent_rows: list[dict], child_start: int, parent_start: int) -> tuple[str, str]:
    c, nc = _pair_share(child_rows, 100, 300, child_start)
    p, npar = _pair_share(parent_rows, 100, 300, parent_start)
    if c != c or p != p or min(nc, npar) < MIN_WINDOW_EVENTS:
        return "NO-DATA", f"pair-court feeder share windows: child {c} (n {nc}), parent {p} (n {npar}): NO-DATA (not a kill)"
    v = "CONTINUE" if c >= p + SHARE_GAIN else "KILL-NO-SHARE"
    return v, f"pair-court feeder share, iterations 100-300: child {c:.4f} vs parent {p:.4f} (kill unless >= +{SHARE_GAIN}) -> {v}"


def _bin01(path: str) -> tuple[float, int]:
    import json
    rows = [json.loads(line) for line in open(path)]
    rows = [r for r in rows if "launch" in r]
    if len(rows) < 2:
        return float("nan"), 0
    s0, s1 = rows[0]["step"], rows[-1]["step"]
    mid = min(rows, key=lambda r: abs(r["step"] - (s0 + 0.5 * (s1 - s0))))
    a, b = mid["launch"]["outcome_feeds_legal"][0], rows[-1]["launch"]["outcome_feeds_legal"][0]
    feeds, legal = b[0] - a[0], b[1] - a[1]
    return (legal / feeds if feeds else float("nan")), int(feeds)


def f_bin(child_path: str, parent_path: str) -> tuple[bool, str]:
    c, nc = _bin01(child_path)
    p, npar = _bin01(parent_path)
    ok = c == c and p == p and min(nc, npar) >= 200 and c >= p + F_BIN_GAIN
    return ok, f"0-1 launch bin feeder legal {c:.4f} (n {nc}) vs {p:.4f} (n {npar}): >= +{F_BIN_GAIN} (n >= 200) -> {'F-BIN' if ok else 'not'}"


def s5_verdict(fup: bool, fband: bool, fup_control: bool | None, abs_f: bool, rally: bool, agile: bool, k3: bool,
               p5_kept: bool, refeed3: bool) -> str:
    """After KILL / INVALID / NO-SHARE (handled by the driver): MIX -> MORE-TIME -> CAP-PASS -> CAP-F -> CAP-FAIL."""
    if fup and not fband:
        return "MIX"
    if fup and fup_control is False:
        return "MORE-TIME"
    kept = agile and k3 and p5_kept and refeed3
    if fup and fband and kept and abs_f and rally:
        return "CAP-PASS"
    if fup and fband and kept:
        return "CAP-F"
    return "CAP-FAIL"


# ---------------------------------------------------------------------------------------------------------------------
# D-202 d1s6 (panel round 66, option (b) parked readiness, Picklebot-Rally22b-FastMove-Parked-G1). Kill at +360 adds
# KILL-FARM (RL): the mean rally length (pair log shots / rallies, all courts) over iterations 100-300 < 0.9 x the parent
# d1s3 run's at the same iterations. Endpoint DOSE (architecture): on the paired LR-0 dose runs' k = 0 feeder tally, the
# child's pelvis-speed p50 at the feeder fire <= parent - 0.05 m/s, or its recovery-distance p50 <= parent - 0.10 m.
# GUARDS: rally_check.r19_guards against the parent's reads (every family >= parent - 0.05, cross_forehand - 0.03,
# left + back feeder contact - 0.05; covers experiment design's reach_deep / backhand / fast / left + back).
FARM_RATIO, DOSE_V, DOSE_D = 0.9, 0.05, 0.10


def _rally_length(rows: list[dict], it_lo: int, it_hi: int, start_it: int) -> tuple[float, int]:
    a = _row_from(rows, (start_it + it_lo) * STEPS_PER_IT)
    b = None if a is None else _row_from(rows, max((start_it + it_hi) * STEPS_PER_IT, a["step"] + (it_hi - it_lo) * STEPS_PER_IT))
    if a is None or b is None or b["step"] <= a["step"]:
        return float("nan"), 0
    r, sh = b["rallies"] - a["rallies"], b["shots"] - a["shots"]
    return (sh / r if r else float("nan")), int(r)


def s6_farm_kill(child_rows: list[dict], parent_rows: list[dict], child_start: int, parent_start: int) -> tuple[str, str]:
    c, nc = _rally_length(child_rows, 100, 300, child_start)
    p, npar = _rally_length(parent_rows, 100, 300, parent_start)
    if c != c or p != p or min(nc, npar) < MIN_WINDOW_EVENTS:
        return "NO-DATA", f"rally-length windows: child {c} (n {nc}), parent {p} (n {npar}): NO-DATA (not a kill)"
    v = "CONTINUE" if c >= FARM_RATIO * p else "KILL-FARM"
    return v, f"mean rally length, iterations 100-300: child {c:.3f} vs parent {p:.3f} (kill below {FARM_RATIO} x) -> {v}"


def s6_dose(child_vars: dict, parent_vars: dict) -> tuple[bool, str]:
    """child_vars / parent_vars: feeder_rule.feeder_stats(...)["vars"] of the paired dose runs."""
    cv, pv = child_vars["pelvis_speed"]["p50"], parent_vars["pelvis_speed"]["p50"]
    cd, pd = child_vars["recover_dist"]["p50"], parent_vars["recover_dist"]["p50"]
    ok = None not in (cv, pv, cd, pd) and (cv <= pv - DOSE_V or cd <= pd - DOSE_D)
    return ok, (f"DOSE: pelvis speed p50 at the feeder fire {cv} vs parent {pv} (<= -{DOSE_V}) or recovery distance p50 "
                f"{cd} vs {pd} (<= -{DOSE_D}) -> {'DOSE' if ok else 'NO-DOSE'}")


def parked_paid(path: str) -> str:
    """Report only: the training dose log (parked_ready, PICKLEBOT_READY_LOG)."""
    import json
    rows = [json.loads(line) for line in open(path)] if __import__("os").path.exists(path) else []
    rows = [r for r in rows if "parked" in r]
    if not rows:
        return "parked dose log: no rows"
    s, n, dead, _ = rows[-1]["parked"]
    return (f"parked dose log (step {rows[-1]['step']}): paid steps {int(n)} of {int(dead)} dead-court env steps "
            f"({n / max(dead, 1):.3f}); mean value when paid {s / max(n, 1):.3f}")


def s6_verdict(dose: bool, guards: bool, fup: bool, fband: bool, fup_control: bool | None, abs_f: bool, rally: bool,
               agile: bool, k3: bool, p5_kept: bool, refeed3: bool) -> str:
    """After KILL / INVALID (the driver): NO-DOSE -> GUARD-BREACH -> MIX -> MORE-TIME -> PARK-PASS -> PARK-F -> PARK-FAIL."""
    if not dose:
        return "NO-DOSE"
    if not guards:
        return "GUARD-BREACH"
    if fup and not fband:
        return "MIX"
    if fup and fup_control is False:
        return "MORE-TIME"
    kept = agile and k3 and p5_kept and refeed3
    if fup and fband and kept and abs_f and rally:
        return "PARK-PASS"
    if fup and fband and kept:
        return "PARK-F"
    return "PARK-FAIL"


# ---------------------------------------------------------------------------------------------------------------------
# D-203 d1s7 (panel round 67, 5 of 5: (d) alone): the d1s3 child with return_stand.restart_obs as a trailing actor and
# critic input (zero columns), on d1s3's own task. NO-USE (experiment design; applies only after DOSE passes): on the
# paired dose read with the new inputs frozen at live-court values (PICKLEBOT_RESTART_OBS_FREEZE), the ablated child
# takes back at least half of the DOSE gain on a DOSE dimension that passed; otherwise the inputs are not what moved it.
USE_FRACTION = 0.5


def s7_use(child_vars: dict, parent_vars: dict, ablated_vars: dict) -> tuple[bool, str]:
    lines, used = [], False
    for k, line in (("pelvis_speed", DOSE_V), ("recover_dist", DOSE_D)):
        c, p, a = child_vars[k]["p50"], parent_vars[k]["p50"], ablated_vars[k]["p50"]
        if None in (c, p, a) or not c <= p - line:
            lines.append(f"{k}: child {c} vs parent {p} (no DOSE on this dimension)")
            continue
        back = (a - c) / (p - c)
        used |= back >= USE_FRACTION
        lines.append(f"{k}: child {c} vs parent {p}, frozen inputs {a}: takes back {back:.2f} of the gain (USED if >= {USE_FRACTION})")
    return used, "USE: " + "; ".join(lines) + f" -> {'USED' if used else 'NO-USE'}"


def s7_verdict(dose: bool, used: bool, guards: bool, fup: bool, fband: bool, fup_control: bool | None, abs_f: bool,
               rally: bool, agile: bool, k3: bool, p5_kept: bool, refeed3: bool) -> str:
    """After KILL / INVALID (the driver): NO-DOSE -> NO-USE -> GUARD-BREACH -> MIX -> MORE-TIME -> OBS-PASS -> OBS-F -> OBS-FAIL.
    Stop rule (round 67): NO-DOSE or NO-USE ends the feeder premise (no fourth feeder lever)."""
    if not dose:
        return "NO-DOSE"
    if not used:
        return "NO-USE"
    v = s6_verdict(True, guards, fup, fband, fup_control, abs_f, rally, agile, k3, p5_kept, refeed3)
    return v.replace("PARK-", "OBS-")


def open_hazards(p: dict, kmax: int = 4) -> list[float]:
    """Report only (round 67 diagnosis): the share of rallies that reach shot position k (open rallies counted) and end
    there, for k = 0 (the feeder ball) .. kmax. The opening exchange, not the steady per-ball rate, holds P(5+) down."""
    h, oh = p["len_hist"], p["open_len_hist"]
    out = []
    for k in range(kmax + 1):
        reached = sum(h[k:]) + sum(oh[k:])
        out.append(h[k] / reached if reached else float("nan"))
    return out


# ---------------------------------------------------------------------------------------------------------------------
# D-204 diag68 (panel round 68, 3 of 5 for (i) first, all 5 for (i) and (iii) before any lever): the first handed ball.
# Parent d1s3 model_31399, two LR-0 reads with the ball-index split tally (the TF task), refeed 0.5 s (dev 4220332) and
# 3.0 s (dev 4220333); pair courts, the matched distance band, second half. Lines (0.5-s read):
#   INVALID if fewer than 1,000 k = 1 balls in the band.
#   STATE (motion): for pelvis_speed or recover_dist, k = 1 failure top tercile - bottom tercile >= 0.10 while the
#     same gap at k >= 3 is <= 0.05.
#   BALL (coach, as a share): for a shot variable (bounce_depth, net_clear, angle, spin), k = 1 failure reweighted to
#     the k >= 3 balls' bin shares removes >= half of the k = 1 excess over k >= 3.
#   Route: STATE only -> recovery to ready at rally start / after misses; BALL only -> the returner's feed-return
#   quality or the pair-court mix; BOTH -> panel; NEITHER -> the falls lever (RL). RESTART (reported): k = 1 failure
#   at 3.0 s vs 0.5 s.
DIAG_MIN_K1, STATE_GAP, STATE_FLAT, BALL_SHARE = 1000, 0.10, 0.05, 0.5
DIAG_STATE_VARS = ("pelvis_speed", "recover_dist")
DIAG_SHOT_VARS = ("bounce_depth", "net_clear", "angle", "spin")


def matched_failure(h1: list[int], l1: list[int], h3: list[int]) -> float | None:
    """k = 1 failure with its bins reweighted to the k >= 3 balls' shares (bins without k = 1 balls dropped)."""
    pairs = [(1 - a / b, c) for b, a, c in zip(h1, l1, h3) if b > 0 and c > 0]
    w = sum(c for _, c in pairs)
    return sum(f * c for f, c in pairs) / w if w else None


def diag68_route(c: dict, g: int = 0) -> tuple[str, list[str]]:
    from picklebot_mj import ballidx_rule as br
    from picklebot_mj.tasks.ball_index import SPLIT_VARS
    spec = {name: (lo, w, nb) for name, lo, w, nb in SPLIT_VARS}
    lines = []
    h1_any, _ = br.band_hist(c, g, 0, "pelvis_speed")
    n1 = sum(h1_any)
    if n1 < DIAG_MIN_K1:
        return "INVALID", [f"k=1 balls in the band {n1} < {DIAG_MIN_K1}"]
    state = []
    for name in DIAG_STATE_VARS:
        nb = spec[name][2]
        g1 = br.var_stats(*br.band_hist(c, g, 0, name), *spec[name])
        g3 = br.var_stats(*br.band_hist(c, g, 2, name), *spec[name])
        t1, t3 = g1["terciles"], g3["terciles"]
        d1 = None if None in (t1[2]["failure"], t1[0]["failure"]) else t1[2]["failure"] - t1[0]["failure"]
        d3 = None if None in (t3[2]["failure"], t3[0]["failure"]) else t3[2]["failure"] - t3[0]["failure"]
        ok = d1 is not None and d3 is not None and d1 >= STATE_GAP and d3 <= STATE_FLAT
        if ok:
            state.append(name)
        lines.append(f"STATE {name}: k=1 top - bottom tercile failure {d1} (>= {STATE_GAP}), k>=3 {d3} (<= {STATE_FLAT}) -> {ok}")
    ball = []
    for name in DIAG_SHOT_VARS:
        nb = spec[name][2]
        h1, l1 = br.band_hist(c, g, 0, name)
        h3, l3 = br.band_hist(c, g, 2, name)
        h1, l1, h3, l3 = h1[:nb], l1[:nb], h3[:nb], l3[:nb]
        f1 = 1 - sum(l1) / sum(h1) if sum(h1) else None
        f3 = 1 - sum(l3) / sum(h3) if sum(h3) else None
        m1 = matched_failure(h1, l1, h3)
        share = None if None in (f1, f3, m1) or f1 <= f3 else (f1 - m1) / (f1 - f3)
        ok = share is not None and share >= BALL_SHARE
        if ok:
            ball.append(name)
        lines.append(f"BALL {name}: k=1 failure {f1 and round(f1, 4)}, matched to k>=3 balls {m1 and round(m1, 4)}, k>=3 "
                     f"{f3 and round(f3, 4)}: share of the excess removed {share and round(share, 3)} (>= {BALL_SHARE}) -> {ok}")
    v = "BOTH" if state and ball else ("STATE" if state else ("BALL" if ball else "NEITHER"))
    return v, lines


# D-204 control (panel round 68, experiment design): the pure d1s3 continuation rally-d1s3ctl (no change, training seed
# 197) as the drift reference. Guard reads pooled over 4 seeds per checkpoint (family contact weighted by episodes,
# direction contact by feeds). GUARD-N: the parent's single-seed read (4220306) breaches r19_guards against its own pooled
# read -> later guard reads use >= 4 seeds. DRIFT: the control breaches r19_guards against the pooled parent, or its mean
# family contact shift is <= -2.0 points -> later children are also reported against the control. Thresholds unchanged.
DRIFT_MEAN = -0.02


def pool_reads(pairs_paths: list[str], dir_paths: list[str]) -> tuple[dict, dict]:
    import json
    fam, dirs = {}, {}
    for p in pairs_paths:
        for k, v in json.load(open(p))["per_family"].items():
            a = fam.setdefault(k, [0.0, 0])
            a[0] += v["contact"] * v["episodes"]
            a[1] += v["episodes"]
    for p in dir_paths:
        for k, v in json.load(open(p))["directions"].items():
            a = dirs.setdefault(k, [0.0, 0])
            a[0] += v["contact"] * v["feeds"]
            a[1] += v["feeds"]
    pf = {k: {"contact": a[0] / a[1] if a[1] else 0.0, "episodes": a[1]} for k, a in fam.items()}
    pd = {k: {"contact": a[0] / a[1] if a[1] else 0.0, "feeds": a[1]} for k, a in dirs.items()}
    return {"per_family": pf}, {"directions": pd}


def mean_family_shift(child_fam: dict, ref_fam: dict) -> float:
    ks = [k for k in ref_fam if k in child_fam]
    return sum(child_fam[k]["contact"] - ref_fam[k]["contact"] for k in ks) / max(len(ks), 1)


def sum_counters(a, b):
    """D-204 addendum: element-wise sum of two windowed ball-index counter trees (dicts / lists of numbers)."""
    if isinstance(a, dict):
        return {k: sum_counters(a[k], b[k]) if k in b else a[k] for k in a}
    if isinstance(a, list):
        return [sum_counters(x, y) for x, y in zip(a, b)]
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool):
        return a + b
    return a


# ---------------------------------------------------------------------------------------------------------------------
# D-205 d1s8 (panel round 69): recovery pay while parked (Picklebot-Rally22b-FastMove-IdleRec-G1). Training seed 199,
# smoke 200; rally-d1s3ctlb (seed 197, same parent / task family / length / settings) is the unconditional control.
# Kill at +360: D-194's lines; KILL-FARM (s6_farm_kill); KILL-NO-CLIMB (experiment design): the windowed mean value of
# the newly paid branch over iterations 300-360 must be >= its iterations 0-60 value + 0.05 (NO-DATA under 1,000 steps).
# Endpoint, LR-0 split reads at 0.5 s on dev 4220332 + 4220337 summed (paired with the parent's diag68 reads), pair
# courts, second half:
#   INVALID: < 1,000 k = 1 balls in the matched band in any arm (parent, control, child).
#   DOSE: k = 1 recover_dist p50 at the hand-off (all distance bands) <= parent - 0.10 m and <= control - 0.10 m.
#   HAZARD (primary): matched-band k = 1 failure <= parent - 0.03 and <= control - 0.03; k >= 3 failure <= parent + 0.01.
#   GUARDS: r19_guards on pooled 4-seed reads against the static parent (the control's breaches reported, attribution).
#   P5-KEPT: P(5+) open on 4220306 >= parent - 0.01. F-UP reported.
# Verdicts: KILL -> INVALID -> NO-DOSE -> NO-HAZARD -> GUARD-BREACH -> P5-LOSS -> REC-PASS. NO-DOSE -> panel (std 0.5 or
# end readiness rewards); NO-HAZARD (dose without the hazard) falsifies STATE -> the falls lever.
CLIMB_GAIN, S8_DOSE_D, S8_HAZ, S8_K3 = 0.05, 0.10, 0.03, 0.01
ALL_BANDS = (0, 40)


def k1_state(c: dict, g: int = 0) -> dict:
    from picklebot_mj import ballidx_rule as br
    from picklebot_mj.tasks.ball_index import SPLIT_VARS
    spec = {name: (lo, w, nb) for name, lo, w, nb in SPLIT_VARS}
    out = {}
    for name in ("recover_dist", "pelvis_speed"):
        out[name] = br.var_stats(*br.band_hist(c, g, 0, name, band=ALL_BANDS), *spec[name])["p50"]
    m1 = br.var_stats(*br.band_hist(c, g, 0, "pelvis_speed"), *spec["pelvis_speed"])
    m3 = br.var_stats(*br.band_hist(c, g, 2, "pelvis_speed"), *spec["pelvis_speed"])
    out.update({"k1_n": m1["balls"], "k1_fail": m1["failure"], "k3_fail": m3["failure"]})
    return out


def _idlerec_window(rows: list[dict], it_lo: int, it_hi: int, start_it: int) -> tuple[float, int]:
    rows = [r for r in rows if "idlerec" in r]
    a = _row_from(rows, (start_it + it_lo) * STEPS_PER_IT)
    b = None if a is None else _row_from(rows, max((start_it + it_hi) * STEPS_PER_IT, a["step"] + (it_hi - it_lo) * STEPS_PER_IT))
    if a is None or b is None or b["step"] <= a["step"]:
        return float("nan"), 0
    s, n = b["idlerec"][0] - a["idlerec"][0], b["idlerec"][1] - a["idlerec"][1]
    return (s / n if n else float("nan")), int(n)


def s8_climb_kill(rows: list[dict], start_it: int) -> tuple[str, str]:
    lo, nlo = _idlerec_window(rows, 0, 60, start_it)
    hi, nhi = _idlerec_window(rows, 300, 360, start_it)
    if lo != lo or hi != hi or min(nlo, nhi) < MIN_WINDOW_EVENTS:
        return "NO-DATA", f"newly paid recovery windows: {lo} (n {nlo}), {hi} (n {nhi}): NO-DATA (not a kill)"
    v = "CONTINUE" if hi >= lo + CLIMB_GAIN else "KILL-NO-CLIMB"
    return v, f"newly paid recovery value, iterations 0-60 {lo:.4f} -> 300-360 {hi:.4f} (kill below +{CLIMB_GAIN}) -> {v}"


def s8_lines(child: dict, parent: dict, control: dict) -> dict:
    inv = min(child["k1_n"], parent["k1_n"], control["k1_n"]) < DIAG_MIN_K1
    dose = (None not in (child["recover_dist"], parent["recover_dist"], control["recover_dist"])
            and child["recover_dist"] <= parent["recover_dist"] - S8_DOSE_D and child["recover_dist"] <= control["recover_dist"] - S8_DOSE_D)
    haz = (None not in (child["k1_fail"], parent["k1_fail"], control["k1_fail"], child["k3_fail"], parent["k3_fail"])
           and child["k1_fail"] <= parent["k1_fail"] - S8_HAZ and child["k1_fail"] <= control["k1_fail"] - S8_HAZ
           and child["k3_fail"] <= parent["k3_fail"] + S8_K3)
    return {"invalid": inv, "dose": dose, "hazard": haz}


def s8_verdict(invalid: bool, dose: bool, hazard: bool, guards: bool, p5_kept: bool) -> str:
    """After KILL (the driver): INVALID -> NO-DOSE -> NO-HAZARD -> GUARD-BREACH -> P5-LOSS -> REC-PASS."""
    if invalid:
        return "INVALID"
    if not dose:
        return "NO-DOSE"
    if not hazard:
        return "NO-HAZARD"
    if not guards:
        return "GUARD-BREACH"
    if not p5_kept:
        return "P5-LOSS"
    return "REC-PASS"


# ---------------------------------------------------------------------------------------------------------------------
# D-206 (panel round 70, 5 of 5 for (iii): fix the drift first). Stage A (reads only): the drift control's model_31800
# (+400) and model_32200 (+800) on D-204's pooled guard seeds. EARLY-DRIFT (experiment design's rule): +400 breaches
# r19_guards against the pooled parent or its mean family shift <= -2.0 -> a lower LR or a shorter run cannot fix it; the
# anchored recipe (new code) goes to the panel. Otherwise LATE -> stage B: rally-d1s3lr, the parent on d1s3's task with
# one change, LR_PEAK 1e-4 -> 3e-5, 1,200 iterations, training seed 201, read on the same pooled seeds. FIXED: no
# r19_guards breach, mean shift >= -1.0, pooled feeder legal and pooled P(5+) >= parent - 0.01; STILL-DRIFT: a breach or
# mean shift <= -2.0; otherwise PARTIAL -> panel.
FIXED_MEAN, POOL_SLACK = -0.01, 0.01


def pooled_pairs(paths: list[str]) -> dict:
    """Pooled feeder legal (court_counts columns 3 / 2) and P(5+) with open rallies (summed histograms)."""
    import json
    cc = [0, 0, 0, 0]
    h, oh = None, None
    for p in paths:
        q = json.load(open(p))["pairs"]
        for row in q["court_counts"]:
            for i in range(4):
                cc[i] += row[i]
        h = list(q["len_hist"]) if h is None else [a + b for a, b in zip(h, q["len_hist"])]
        oh = list(q["open_len_hist"]) if oh is None else [a + b for a, b in zip(oh, q["open_len_hist"])]
    k, n = sum(h[5:]) + sum(oh[5:]), sum(h) + sum(oh[5:])
    return {"feeder": cc[3] / cc[2] if cc[2] else float("nan"), "p5": k / n if n else float("nan"), "rallies": n}


def drift_verdict(guards_ok: bool, mean_shift: float, feeder: float, feeder_ref: float, p5: float, p5_ref: float) -> str:
    if not guards_ok or mean_shift <= DRIFT_MEAN:
        return "STILL-DRIFT"
    if mean_shift >= FIXED_MEAN and feeder >= feeder_ref - POOL_SLACK and p5 >= p5_ref - POOL_SLACK:
        return "FIXED"
    return "PARTIAL"


# ---------------------------------------------------------------------------------------------------------------------
# D-208 (panel round 72, 5 of 5 for (i)): the anchor at coef 0.3 (3 of 5; RL 0.1, architecture probe / 0.5). FIXED stays
# as D-206 (unchanged) and a GAIN line is added (experiment design): pooled P(5+) >= parent + 0.01 and the lower 95 % CI
# (t, 3 df) of the per-seed paired P(5+) difference above 0. Routes: FIXED + GAIN -> confirmation; FIXED without GAIN ->
# HELD-NO-GAIN; STILL-DRIFT + GAIN -> TRADE-OFF; otherwise the drift verdict -> panel. Confirmation pooled over 4 fresh
# seeds with the parent re-read on them; CONFIRM-FAIL on a breach or child P(5+) < parent (as D-207).
GAIN_MIN, T3_975 = 0.01, 3.182


def gain_line(child_paths: list[str], parent_paths: list[str]) -> tuple[bool, str]:
    import json
    import statistics
    import sys
    sys.path.insert(0, "scripts")
    import rally_check as rc
    d = [rc.p5_open(json.load(open(c))["pairs"])[0] - rc.p5_open(json.load(open(p))["pairs"])[0]
         for c, p in zip(child_paths, parent_paths)]
    pooled = pooled_pairs(child_paths)["p5"] - pooled_pairs(parent_paths)["p5"]
    lo = statistics.mean(d) - T3_975 * statistics.stdev(d) / len(d) ** 0.5 if len(d) > 1 else float("nan")
    ok = pooled >= GAIN_MIN and lo > 0
    return ok, (f"GAIN: pooled P(5+) {100 * pooled:+.2f} points (>= +{100 * GAIN_MIN:.0f}); per-seed "
                f"{', '.join(f'{100 * x:+.2f}' for x in d)}; lower 95 % CI {100 * lo:+.2f} (> 0) -> {'GAIN' if ok else 'no gain'}")


def mechanism(paths: list[str]) -> dict:
    """Reported (motion, round 72): pooled ready stance, falls per hit, WRONG_SIDE share of endings, recovery median."""
    import json
    js = [json.load(open(p)) for p in paths]
    w = sum(j["ready"]["feeds_scored"] for j in js)
    ends = sum(sum(j["rally_endings"].values()) for j in js)
    return {"ready": sum(j["ready"]["ready"] * j["ready"]["feeds_scored"] for j in js) / max(w, 1),
            "falls_per_1000_hits": 1000 * sum(j["falls"] for j in js) / max(sum(j["hits"] for j in js), 1),
            "wrong_side_share": sum(j["rally_endings"].get("WRONG_SIDE", 0) for j in js) / max(ends, 1),
            "recovery_median_m": sum(j["recovery"]["error_median_m"] for j in js) / len(js)}


def anchor_route(drift: str, gain: bool) -> str:
    if drift == "FIXED":
        return "CONFIRM" if gain else "HELD-NO-GAIN"
    if drift == "STILL-DRIFT" and gain:
        return "TRADE-OFF"
    return drift


# D-209 (panel round 73; no majority: (iv) 2, (i) 2, (iii) 1; the least-new-code options (iv) and (iii) tie at none, so
# experiment design's position decides: (iv)). rally-d1s3lr2 replicates rally-d1s3lr with one change, training seed
# 201 -> 205. REPLICATED (experiment design) = GAIN and the mechanism moved as in d1s3lr: pooled ready stance >= 0.25
# and falls per 1,000 hits <= 1.3. Not replicated -> the d1s3lr gain was a seed effect; the anchor line closes (panel).
REP_READY, REP_FALLS = 0.25, 1.3


def replicated(gain: bool, mech: dict) -> bool:
    return bool(gain) and mech["ready"] >= REP_READY and mech["falls_per_1000_hits"] <= REP_FALLS


# ---------------------------------------------------------------------------------------------------------------------
# D-210 (panel round 74, 5 of 5 for (ii): LR 3e-5 as the recipe base, no promotion). Two runs on training seed 206:
# C = rally-d1s3lr3 (d1s3lr's recipe) and L = rally-d1s3bh (C + backhand-family feeder weights 2.0, coach; 3 of 5 for the
# lever, 3 of 5 for a fresh matched control). New GAIN statistic (experiment design, prospective only): pooled P(5+)
# difference >= +1 point and diff - 1.96 x max(binomial SE, empirical per-seed SE) > 0. RECIPE (C vs parent): GAIN2 plus
# ready >= 0.25 and falls <= 1.3 (confirmatory on seed-206 data only). LEVER (L vs C): GAIN2, r19_guards against the
# parent unchanged. LEVER pass + guards -> CONFIRM; else panel. The 3-training-seed estimate is reported, never a verdict.
def gain2(child_paths: list[str], ref_paths: list[str]) -> tuple[bool, float, float, str]:
    import json
    import statistics
    import sys
    sys.path.insert(0, "scripts")
    import rally_check as rc
    qc, qr = pooled_pairs(child_paths), pooled_pairs(ref_paths)
    diff = qc["p5"] - qr["p5"]
    se_b = (qc["p5"] * (1 - qc["p5"]) / qc["rallies"] + qr["p5"] * (1 - qr["p5"]) / qr["rallies"]) ** 0.5
    d = [rc.p5_open(json.load(open(c))["pairs"])[0] - rc.p5_open(json.load(open(r))["pairs"])[0] for c, r in zip(child_paths, ref_paths)]
    se_e = statistics.stdev(d) / len(d) ** 0.5 if len(d) > 1 else float("inf")
    lo = diff - 1.96 * max(se_b, se_e)
    ok = diff >= GAIN_MIN and lo > 0
    return ok, diff, lo, (f"GAIN2: pooled P(5+) {100 * diff:+.2f} points (>= +{100 * GAIN_MIN:.0f}); binomial SE {100 * se_b:.2f}, "
                          f"per-seed SE {100 * se_e:.2f}; lower bound {100 * lo:+.2f} (> 0); per-seed "
                          f"{', '.join(f'{100 * x:+.2f}' for x in d)} -> {'GAIN' if ok else 'no gain'}")


def seed_estimate(diffs: list[float]) -> str:
    """Reported only: the mean of per-training-seed pooled differences with a t interval (n - 1 df)."""
    import statistics
    t = {1: 12.706, 2: 4.303, 3: 3.182}
    m = statistics.mean(diffs)
    if len(diffs) < 2:
        return f"training-seed estimate {100 * m:+.2f} (one seed)"
    h = t.get(len(diffs) - 1, 2.0) * statistics.stdev(diffs) / len(diffs) ** 0.5
    return f"training-seed estimate (reported) {100 * m:+.2f} points, 95 % CI {100 * (m - h):+.2f} to {100 * (m + h):+.2f} over {len(diffs)} training seeds"


# ---------------------------------------------------------------------------------------------------------------------
# D-212 (panel round 76; (ii) 3 of 5 - motion, coach, RL; (i) 2). C = rally-d1s3lr3 model_32598 (the parent since D-211).
# Two runs on training seed 207: C2 = rally-d1s3lr4 (C + 1,200 iterations, LR 3e-5) and K = rally-d1s3cap (C2's recipe +
# the training-only pair_rally_cap 5; smoke seed 208). The lever had no majority (approach_far pre-bounce 1, the cap 1,
# IdleRec 1); least new code: the cap (coded since D-161). COMPOUND (C2 vs C, D-204 seeds): gain2 against lev74-C,
# r19_guards against the original parent's pooled reads on the same seeds, ready >= 0.25, falls <= 1.3. LEVER (K vs C2):
# the same lines plus coach's OPEN ((1 - h0)(1 - h1) >= C2's + 0.02), K3-KEPT (late-rally failure share <= C2's + 0.005)
# and FEEDER (pooled feeder legal >= C2's - 0.01). Hazards pool the rally histograms, then use open_hazards.
OPEN_GAIN, K3_SLACK, FEEDER_SLACK = 0.02, 0.005, 0.01


def pooled_hazards(paths: list[str], kmax: int = 4) -> dict:
    import json
    h, oh = None, None
    for p in paths:
        q = json.load(open(p))["pairs"]
        h = list(q["len_hist"]) if h is None else [a + b for a, b in zip(h, q["len_hist"])]
        oh = list(q["open_len_hist"]) if oh is None else [a + b for a, b in zip(oh, q["open_len_hist"])]
    hz = open_hazards({"len_hist": h, "open_len_hist": oh}, kmax)
    late = sum(h[3:]) / max(sum(h[3:]) + sum(oh[3:]), 1)
    return {"h": hz, "open2": (1 - hz[0]) * (1 - hz[1]), "late": late}


def lever_lines(child_paths: list[str], ref_paths: list[str]) -> tuple[bool, list[str]]:
    c, r = pooled_hazards(child_paths), pooled_hazards(ref_paths)
    fc, fr = pooled_pairs(child_paths)["feeder"], pooled_pairs(ref_paths)["feeder"]
    o = c["open2"] >= r["open2"] + OPEN_GAIN
    k3 = c["late"] <= r["late"] + K3_SLACK
    fd = fc >= fr - FEEDER_SLACK
    lines = [f"OPEN: (1-h0)(1-h1) {c['open2']:.4f} vs {r['open2']:.4f} (>= +{OPEN_GAIN}) -> {o}",
             f"K3-KEPT: late failure share {c['late']:.4f} vs {r['late']:.4f} (<= +{K3_SLACK}) -> {k3}",
             f"FEEDER: feeder legal {fc:.4f} vs {fr:.4f} (>= -{FEEDER_SLACK}) -> {fd}",
             "hazards h0-h4 child " + " / ".join(f"{x:.3f}" for x in c["h"]) + "; ref " + " / ".join(f"{x:.3f}" for x in r["h"])]
    return o and k3 and fd, lines


def lev76_candidate(compound: bool, lever: bool) -> str:
    """The checkpoint taken to the fresh confirmation: K if LEVER, else C2 if COMPOUND, else none (panel)."""
    return "K" if lever else ("C2" if compound else "none")


# ---------------------------------------------------------------------------------------------------------------------
# D-213 (panel round 77; (ii) 4 of 5, (iii) IdleRec 1). Stage A, reads only: Fast4 (fw-fast4-01 model_18099) against
# d1's teacher fw1b-S model_16600 on Picklebot-Footwork-Measure60-Court-G1 (the kickstart's 0.5-3 m geometry), mean
# actions, paired on dev 4220357. Lines by majority (experiment design's wording where the forms differed):
#   VALID (D-188): falls <= 2 x fw1b-S's, worst arrival >= 0.80, (fallen + censored) / spots <= 0.15;
#   ARRIVE: worst-sector untimed arrival >= 0.95 and >= fw1b-S's - 0.02;
#   SETTLE (5 of 5; no slack 3 of 5): settled share in left and back each >= fw1b-S's;
#   FIRST-STEP (3 of 5; no slack 2 of 3): first-step p50 in left and back each <= fw1b-S's;
#   FASTER (3 of 5): sustained p50 in left and back each >= fw1b-S's + 0.10 m/s, and falls <= fw1b-S's.
# All pass -> D1B-OK (the D-192 kickstart with the teacher swapped to Fast4); else TEACHER-NOT-READY (panel).
F4_ARRIVE, F4_ARRIVE_SLACK, F4_FASTER = 0.95, 0.02, 0.10


def fast4_check(t: dict, w: dict) -> tuple[str, list[str]]:
    """t, w: agility() of Fast4 and fw1b-S on the same seed."""
    lr = (LEFT, BACK)
    valid = t["falls"] <= 2 * w["falls"] and t["worst_arrival"] >= 0.80 and t["fallen_censored_share"] <= 0.15
    arrive = t["worst_arrival"] >= F4_ARRIVE and t["worst_arrival"] >= w["worst_arrival"] - F4_ARRIVE_SLACK
    settle = all(t["settled"][i] >= w["settled"][i] for i in lr)
    fs = all(t["first_step_p50"][i] is not None and w["first_step_p50"][i] is not None
             and t["first_step_p50"][i] <= w["first_step_p50"][i] for i in lr)
    faster = all(t["sustained_p50"][i] is not None and w["sustained_p50"][i] is not None
                 and t["sustained_p50"][i] >= w["sustained_p50"][i] + F4_FASTER for i in lr) and t["falls"] <= w["falls"]
    g = lambda k: f"L/B {t[k][LEFT]}/{t[k][BACK]} vs {w[k][LEFT]}/{w[k][BACK]}"  # noqa: E731
    lines = [f"VALID: falls {t['falls']:.3f} vs {w['falls']:.3f} (<= 2x), worst arrival {t['worst_arrival']:.3f} (>= 0.80), "
             f"fallen+censored {t['fallen_censored_share']:.3f} (<= 0.15) -> {valid}",
             f"ARRIVE: worst arrival {t['worst_arrival']:.3f} vs {w['worst_arrival']:.3f} (>= {F4_ARRIVE} and >= -{F4_ARRIVE_SLACK}) -> {arrive}",
             f"SETTLE: settled {g('settled')} (each >=) -> {settle}",
             f"FIRST-STEP: p50 {g('first_step_p50')} s (each <=) -> {fs}",
             f"FASTER: sustained p50 {g('sustained_p50')} m/s (each >= +{F4_FASTER}), falls <= -> {faster}"]
    return ("D1B-OK" if valid and arrive and settle and fs and faster else "TEACHER-NOT-READY"), lines


# ---------------------------------------------------------------------------------------------------------------------
# D-214 (panel round 78; (i) 4 of 5, (iii) pre-bounce approach_far 1). R = rally-d1s3idle: C model_32598 on
# Picklebot-Rally22b-FastMove-IdleRec-G1 (D-205's recovery pay while parked), LR 3e-5. Endpoint lines against C (lev74-C)
# on D-204's pooled seeds, besides gain2 / r19_guards / the mechanism bars: H1 (pooled k = 1 hazard <= C's - S8_HAZ),
# FEEDER (pooled feeder legal >= C's - FEEDER_SLACK), K3-KEPT (late failure share <= C's + K3_SLACK, as D-212).
# Reported (round 77): the late split into endings at shots 3-4 over reached 3, and endings at 5+ over reached 5.
def late_splits(paths: list[str]) -> tuple[float, float]:
    import json
    h, oh = None, None
    for p in paths:
        q = json.load(open(p))["pairs"]
        h = list(q["len_hist"]) if h is None else [a + b for a, b in zip(h, q["len_hist"])]
        oh = list(q["open_len_hist"]) if oh is None else [a + b for a, b in zip(oh, q["open_len_hist"])]
    s34 = sum(h[3:5]) / max(sum(h[3:]) + sum(oh[3:]), 1)
    s5 = sum(h[5:]) / max(sum(h[5:]) + sum(oh[5:]), 1)
    return s34, s5


def rec78_lines(child_paths: list[str], ref_paths: list[str]) -> tuple[bool, list[str]]:
    c, r = pooled_hazards(child_paths), pooled_hazards(ref_paths)
    fc, fr = pooled_pairs(child_paths)["feeder"], pooled_pairs(ref_paths)["feeder"]
    h1 = c["h"][1] <= r["h"][1] - S8_HAZ
    fd = fc >= fr - FEEDER_SLACK
    k3 = c["late"] <= r["late"] + K3_SLACK
    (c34, c5), (r34, r5) = late_splits(child_paths), late_splits(ref_paths)
    lines = [f"H1: k = 1 hazard {c['h'][1]:.4f} vs {r['h'][1]:.4f} (<= -{S8_HAZ}) -> {h1}",
             f"FEEDER: feeder legal {fc:.4f} vs {fr:.4f} (>= -{FEEDER_SLACK}) -> {fd}",
             f"K3-KEPT: late failure share {c['late']:.4f} vs {r['late']:.4f} (<= +{K3_SLACK}) -> {k3}",
             f"(reported) late splits: shots 3-4 {c34:.4f} vs {r34:.4f}; 5+ ended {c5:.4f} vs {r5:.4f}",
             "(reported) hazards h0-h4 child " + " / ".join(f"{x:.3f}" for x in c["h"]) + "; ref " + " / ".join(f"{x:.3f}" for x in r["h"])]
    return h1 and fd and k3, lines


# ---------------------------------------------------------------------------------------------------------------------
# D-215 (panel round 79; no majority: (i) pre-bounce approach_far 2, the stance-target fix 2, the cap on half the courts
# 1; least new code: the stance-target fix, architecture's form). F = rally-d1s3cfs: C on d1s3's task with
# court_feed_stance + court_feed_stance_unplanned (launcher feeds' stance_xy retargeted to their own stance spot with the
# planner off; before, stance_progress paid speed toward (0, 0), the net centre). Lines against C (lev74-C), besides
# gain2 / r19_guards / the mechanism bars: H0 (pooled feeder-ball hazard <= C's - S8_HAZ), FEEDER and K3-KEPT as D-214.
def cfs79_lines(child_paths: list[str], ref_paths: list[str]) -> tuple[bool, list[str]]:
    c, r = pooled_hazards(child_paths), pooled_hazards(ref_paths)
    h0 = c["h"][0] <= r["h"][0] - S8_HAZ
    ok, lines = rec78_lines(child_paths, ref_paths)
    fd_k3 = lines[1].endswith("True") and lines[2].endswith("True")
    return h0 and fd_k3, [f"H0: feeder-ball hazard {c['h'][0]:.4f} vs {r['h'][0]:.4f} (<= -{S8_HAZ}) -> {h0}"] + lines[1:]


# ---------------------------------------------------------------------------------------------------------------------
# D-216 (panel round 80 / 80b; (vi) 2 of 5 (coach, experiment design), (i), (iii-RL), (iv) 1 each; least code vs fewest
# moving parts unclear, so experiment design's position: (vi)). Reads only: feeder-ball legal by launch distance
# (launch_state["outcome_by_d"], bins on LAUNCH_D_EDGES 0.1 / 0.2 / 0.3 / 0.5 / 0.8 / 1.2 m), C at mean actions.
#   RESTART-BINDS: legal(d <= 0.3) >= 0.80 and legal(d <= 0.3) - legal(d > 1.2) >= 0.20 with non-overlapping Wilson 95 %
#     intervals -> (iii-RL), random rally ends on half the live courts (coded in its own entry).
#   SHOT-BINDS: legal(d <= 0.3) < 0.75 -> STOP (D-169: to the next phase, a rally fine-tune with the d1 base unfrozen).
#   Otherwise PANEL. Coach's routes (near d <= 1.2 >= 0.70 and far <= near - 0.10) are reported.
D216_NEAR, D216_GAP, D216_SHOT = 0.80, 0.20, 0.75


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return float("nan"), float("nan")
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * (p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5 / d
    return c - h, c + h


def dist_route(out_by_d: list[list[int]]) -> tuple[str, list[str]]:
    """out_by_d: [[feeds, legal]] per launch-distance bin (7 bins)."""
    near = [sum(x[0] for x in out_by_d[:3]), sum(x[1] for x in out_by_d[:3])]
    far = out_by_d[6]
    wide = [sum(x[0] for x in out_by_d[:6]), sum(x[1] for x in out_by_d[:6])]
    pn, pf = near[1] / max(near[0], 1), far[1] / max(far[0], 1)
    (nlo, nhi), (flo, fhi) = wilson(near[1], near[0]), wilson(far[1], far[0])
    pw = wide[1] / max(wide[0], 1)
    restart = pn >= D216_NEAR and pn - pf >= D216_GAP and nlo > fhi
    shot = pn < D216_SHOT
    v = "RESTART-BINDS" if restart else "SHOT-BINDS" if shot else "PANEL"
    coach = pw >= 0.70 and pf <= pw - 0.10
    far_s = (f"{pf:.4f} (n {far[0]}, Wilson {flo:.3f}-{fhi:.3f}); gap {pn - pf:+.4f}" if far[0]
             else "not read (n 0: the set-start read places no feeder ball past 1.2 m)")  # D-249: was a nan line
    lines = [f"legal(d <= 0.3) {pn:.4f} (n {near[0]}, Wilson {nlo:.3f}-{nhi:.3f}); legal(d > 1.2) {far_s}",
             f"RESTART-BINDS: near >= {D216_NEAR} and gap >= {D216_GAP} and intervals apart -> {restart}; "
             f"SHOT-BINDS: near < {D216_SHOT} -> {shot}",
             f"(reported) coach's route: legal(d <= 1.2) {pw:.4f} >= 0.70 and far <= near - 0.10 -> {coach}",
             "(reported) legal by bin: " + ", ".join(f"{x[1] / max(x[0], 1):.3f} (n {x[0]})" for x in out_by_d)]
    return v, lines


# ---------------------------------------------------------------------------------------------------------------------
# D-217 (D-216 routed RESTART-BINDS -> (iii-RL), RL's form): random rally ends (pair_cut_prob, half the live courts).
# Kill at +360 besides D-194's lines and KILL-FARM, from the PICKLEBOT_PAIR_LOG rows (windows from rows that exist):
#   KILL-NO-SHARE: live-court feeder share over iterations 300-360 < CUT_SHARE_MIN;
#   KILL-NO-DOSE: off-spot (d > 1.2 m) share of live-court feeder-ball launches over 300-360 < CUT_DOSE_MIN;
#   KILL-EASY: feeder legal after a cut over iterations 30-90 > CUT_EASY_MAX (round 43's premise, measured in training).
CUT_SHARE_MIN, CUT_DOSE_MIN, CUT_EASY_MAX = 0.18, 0.40, 0.85


def _launch_window(rows: list[dict], it_lo: int, it_hi: int, start_it: int):
    rows = [r for r in rows if "launch" in r]
    a = _row_from(rows, (start_it + it_lo) * STEPS_PER_IT)
    b = None if a is None else _row_from(rows, max((start_it + it_hi) * STEPS_PER_IT, a["step"] + (it_hi - it_lo) * STEPS_PER_IT))
    if a is None or b is None or b["step"] <= a["step"]:
        return None
    da = [sum(r[i] for r in a["launch"]["d_hist"]) for i in range(len(a["launch"]["d_hist"][0]))]
    db = [sum(r[i] for r in b["launch"]["d_hist"]) for i in range(len(b["launch"]["d_hist"][0]))]
    d = [y - x for x, y in zip(da, db)]
    ca, cb = a["launch"].get("outcome_after_cut", [0, 0]), b["launch"].get("outcome_after_cut", [0, 0])
    return {"far": d[-1], "launches": sum(d), "cut_feeds": cb[0] - ca[0], "cut_legal": cb[1] - ca[1]}


def cut81_kills(rows: list[dict], start_it: int) -> list[tuple[str, str]]:
    out = []
    s, ns = _pair_share(rows, 300, 360, start_it)
    if s != s or ns < MIN_WINDOW_EVENTS:
        out.append(("NO-DATA", f"KILL-NO-SHARE: live-court feeder share 300-360 {s} (n {ns}): NO-DATA (not a kill)"))
    else:
        v = "CONTINUE" if s >= CUT_SHARE_MIN else "KILL-NO-SHARE"
        out.append((v, f"KILL-NO-SHARE: live-court feeder share 300-360 {s:.4f} (n {ns}; kill below {CUT_SHARE_MIN}) -> {v}"))
    w = _launch_window(rows, 300, 360, start_it)
    if w is None or w["launches"] < MIN_WINDOW_EVENTS:
        out.append(("NO-DATA", f"KILL-NO-DOSE: off-spot launch share 300-360: NO-DATA (not a kill) {w}"))
    else:
        f = w["far"] / w["launches"]
        v = "CONTINUE" if f >= CUT_DOSE_MIN else "KILL-NO-DOSE"
        out.append((v, f"KILL-NO-DOSE: off-spot (d > 1.2) launch share 300-360 {f:.4f} (n {w['launches']}; kill below {CUT_DOSE_MIN}) -> {v}"))
    e = _launch_window(rows, 30, 90, start_it)
    if e is None or e["cut_feeds"] < MIN_WINDOW_EVENTS:
        out.append(("NO-DATA", f"KILL-EASY: feeder legal after a cut 30-90: NO-DATA (not a kill) {e}"))
    else:
        g = e["cut_legal"] / e["cut_feeds"]
        v = "CONTINUE" if g <= CUT_EASY_MAX else "KILL-EASY"
        out.append((v, f"KILL-EASY: feeder legal after a cut 30-90 {g:.4f} (n {e['cut_feeds']}; kill above {CUT_EASY_MAX}) -> {v}"))
    return out


# ---------------------------------------------------------------------------------------------------------------------
# D-218 (panel round 81; no majority: (iv) reads 2 (experiment design: 120 s / 240 s split; motion: --audit-fixes re-read),
# (i) feed the furthest robot 1 (RL), (ii) episode length 24 s 1 (architecture), (iii) STOP 1 (coach); fewest moving
# parts: (iv); experiment design's form decides the route, motion's read is reported). Reads only, C model_32598.
#   SPAWN-BINDS: first-half (0-120 s) off-spot (d > 1.2 m) share of logged feeder launches >= 0.45, and second half
#     (120-240 s, the 240-s read minus the 120-s read) <= 0.35, Wilson 95 % intervals apart -> (ii) episode length.
#   MID-BINDS: second-half off-spot share >= 0.45 -> the post-bounce cut. Otherwise PANEL.
SPAWN_FIRST, SPAWN_SECOND, MID_SECOND = 0.45, 0.35, 0.45
SPAWN_MIN_N = 200


def spawn_route(first_dhist: list[int], full_dhist: list[int]) -> tuple[str, list[str]]:
    """d_hist totals (summed over the previous-rally bins): the 120-s read and the 240-s read on the same seeds."""
    second = [b - a for a, b in zip(first_dhist, full_dhist)]
    f_n, f_k = sum(first_dhist), first_dhist[-1]
    s_n, s_k = sum(second), second[-1]
    pf, ps = f_k / max(f_n, 1), s_k / max(s_n, 1)
    if s_n < SPAWN_MIN_N or s_k < 0:  # D-218 guard: the split is undefined (checked before any interval)
        return "INVALID-SPLIT", [f"off-spot share: first half {pf:.4f} (n {f_n}); second half undefined (n {s_n}, "
                                  f"off-spot {s_k}): the 240-s read logs about as many feeder launches as the 120-s read"]
    (flo, fhi), (slo, shi) = wilson(f_k, f_n), wilson(s_k, s_n)
    spawn = pf >= SPAWN_FIRST and ps <= SPAWN_SECOND and flo > shi
    mid = ps >= MID_SECOND
    # D-218 guard (added before the verdict was read): the two reads are separate simulations, so the second half is a
    # difference of counts; with fewer than SPAWN_MIN_N second-half launches (or a negative count) the split is undefined.
    v = "INVALID-SPLIT" if s_n < SPAWN_MIN_N else "SPAWN-BINDS" if spawn else "MID-BINDS" if mid else "PANEL"
    return v, [f"off-spot share: first half {pf:.4f} (n {f_n}, Wilson {flo:.3f}-{fhi:.3f}); second half {ps:.4f} (n {s_n}, "
               f"Wilson {slo:.3f}-{shi:.3f})",
               f"SPAWN-BINDS (first >= {SPAWN_FIRST}, second <= {SPAWN_SECOND}, apart) -> {spawn}; MID-BINDS (second >= "
               f"{MID_SECOND}) -> {mid}"]


# ---------------------------------------------------------------------------------------------------------------------
# D-219 (panel round 82; (ii) 3 of 5: coach, motion, architecture; (i) 2: RL, experiment design). X = rally-d1s3ep24:
# C model_32598 with the training episode length 120 -> 24 s (one knob; reads set their own length). Reported mechanism:
# per-court feeder-ball conversion from court_counts column 2 (feeder balls per court): q0 = share of courts whose first
# feeder ball started the court's final rally (column 2 == 1); q1 = later feeder balls' conversion (geometric MLE over the
# courts with >= 2 feeder balls). Smoke / +360 dose (KILL-NO-DOSE): the reset-feed bucket (outcome_by_d's last bin)
# must be >= EP_DOSE_MIN of feeder-type outcomes; its growth tracks episode starts.
EP_DOSE_MIN = 0.15


def court_conv(paths: list[str]) -> dict:
    import json
    n1 = n2 = extra = 0
    for p in paths:
        for row in json.load(open(p))["pairs"]["court_counts"]:
            f = int(row[2])
            if f == 1:
                n1 += 1
            elif f >= 2:
                n2 += 1
                extra += f - 1
    n = n1 + n2
    return {"q0": n1 / max(n, 1), "q1": n2 / max(extra, 1), "courts": n}


def ep_dose(rows: list[dict], it_lo: int, it_hi: int, start_it: int) -> tuple[float, int]:
    rows = [r for r in rows if "launch" in r and "outcome_by_d" in r["launch"]]
    a = _row_from(rows, (start_it + it_lo) * STEPS_PER_IT)
    b = None if a is None else _row_from(rows, max((start_it + it_hi) * STEPS_PER_IT, a["step"] + (it_hi - it_lo) * STEPS_PER_IT))
    if a is None or b is None or b["step"] <= a["step"]:
        return float("nan"), 0
    oa, ob = a["launch"]["outcome_by_d"], b["launch"]["outcome_by_d"]
    tot = sum(y[0] - x[0] for x, y in zip(oa, ob))
    reset = ob[-1][0] - oa[-1][0]
    return (reset / tot if tot else float("nan")), int(tot)


def ep24_dose_kill(rows: list[dict], it_lo: int, it_hi: int, start_it: int) -> tuple[str, str]:
    s, n = ep_dose(rows, it_lo, it_hi, start_it)
    if s != s or n < MIN_WINDOW_EVENTS:
        return "NO-DATA", f"KILL-NO-DOSE: reset-feed share {it_lo}-{it_hi} {s} (n {n}): NO-DATA (not a kill)"
    v = "CONTINUE" if s >= EP_DOSE_MIN else "KILL-NO-DOSE"
    return v, f"KILL-NO-DOSE: reset-feed share of feeder-type outcomes {it_lo}-{it_hi} {s:.4f} (n {n}; kill below {EP_DOSE_MIN}) -> {v}"


# ---------------------------------------------------------------------------------------------------------------------
# D-220 (panel round 83; no majority: (ii) spawn restarts 2 (RL, motion), (i) 12-s episodes 1 (experiment design),
# (iii) STOP 1 (coach), (iv) relaunch 24 s with the dose instrument fixed 1 (architecture); least new code / fewest
# moving parts: (iv)). The D-219 dose line measured the leak-ball bucket, not the spawn feeder ball. The exposure is
# already logged: rallies ended by a reset on live courts (end_reasons[0][2]) per live feeder fire (split[0][0]), and
# resets per live env-second (live envs = envs / 2; 0.02 s per env step). C2 (120 s) reads 0.2615 / 0.0086; the D-219
# smoke (24 s) 0.431 / 0.0388 on rows +22 / +142. Lines: share >= RESET_SHARE_MIN and rate >= RESET_RATE_MIN (3x C2).
RESET_SHARE_MIN, RESET_RATE_MIN = 0.35, 0.0248


def reset_dose(rows: list[dict], it_lo: int, it_hi: int, start_it: int, envs: int) -> tuple[float, float, int]:
    rows = [r for r in rows if "end_reasons" in r and "split" in r]
    a = _row_from(rows, (start_it + it_lo) * STEPS_PER_IT)
    b = None if a is None else _row_from(rows, max((start_it + it_hi) * STEPS_PER_IT, a["step"] + (it_hi - it_lo) * STEPS_PER_IT))
    if a is None or b is None or b["step"] <= a["step"]:
        return float("nan"), float("nan"), 0
    dres = b["end_reasons"][0][2] - a["end_reasons"][0][2]
    dfire = b["split"][0][0] - a["split"][0][0]
    dt = (b["step"] - a["step"]) * 0.02
    return (dres / dfire if dfire else float("nan")), dres / (envs / 2 * dt), int(dfire)


def reset_dose_kill(rows: list[dict], it_lo: int, it_hi: int, start_it: int, envs: int) -> tuple[str, str]:
    s, r, n = reset_dose(rows, it_lo, it_hi, start_it, envs)
    if s != s or n < MIN_WINDOW_EVENTS:
        return "NO-DATA", f"KILL-NO-DOSE: post-reset share {it_lo}-{it_hi} {s} (n {n}): NO-DATA (not a kill)"
    ok = s >= RESET_SHARE_MIN and r >= RESET_RATE_MIN
    v = "CONTINUE" if ok else "KILL-NO-DOSE"
    return v, (f"KILL-NO-DOSE: post-reset share of live feeder fires {it_lo}-{it_hi} {s:.4f} (>= {RESET_SHARE_MIN}); resets per "
               f"live env-s {r:.5f} (>= {RESET_RATE_MIN}; n {n}) -> {v}")


# ---------------------------------------------------------------------------------------------------------------------
# D-221 (panel round 84, (a) stage 1, 5 of 5; round 84b form F2, 5 of 5). Q = fw-quick-01: fw1b-S model_16600 on
# Picklebot-Footwork-Specialist-Quick-G1 (court spots, pay settled, plus the first-step bonus). Training log rows (one per
# 10 iterations, cumulative counters; step = global iteration x STEPS_PER_IT) carry first_step_hist per sector.
QUICK_MARGIN = 0.25    # QUICK: left / back first-step p50 each <= fw1b-S's - 0.25 s (experiment design's line; tie)
QUICK_KILL = 0.10      # KILL-NO-START: the late window not >= 0.10 s faster, left and back each (4 of 5)
QUICK_MIN_N = 200      # a window is readable with >= 200 first-step samples in each of left and back (motion)
QUICK_EARLY, QUICK_LATE = (0, 100), (400, 450)  # iterations from the start checkpoint (experiment design's windows)


def first_window(rows: list[dict], it_lo: int, it_hi: int, start_it: int):
    """Left / back first-step p50 (s) and sample counts over a training window built from rows that exist; None if no
    row covers an edge."""
    rows = [r for r in rows if "move" in r and "first_step_hist" in r["move"]]
    a = _row_from(rows, (start_it + it_lo) * STEPS_PER_IT)
    b = None if a is None else _row_from(rows, max((start_it + it_hi) * STEPS_PER_IT, a["step"] + (it_hi - it_lo) * STEPS_PER_IT))
    if a is None or b is None:
        return None
    w = b["move"].get("first_step_bin_s", 0.05)
    out = []
    for i in (LEFT, BACK):
        h = [y - x for x, y in zip(a["move"]["first_step_hist"][i], b["move"]["first_step_hist"][i])]
        out.append((quantile(h, 0.5, w), sum(h)))
    pay = [y - x for x, y in zip(a["move"].get("first_pay_sum", [0.0] * 8), b["move"].get("first_pay_sum", [0.0] * 8))]
    spots = sum(y - x for x, y in zip(a["move"]["issued"], b["move"]["issued"]))
    return {"p50": [out[0][0], out[1][0]], "n": [out[0][1], out[1][1]], "pay_per_spot": sum(pay) / max(spots, 1)}


def quick_kill(rows: list[dict], start_it: int) -> tuple[str, str]:
    e, l = first_window(rows, *QUICK_EARLY, start_it), first_window(rows, *QUICK_LATE, start_it)
    lab = "KILL-NO-START"
    if e is None or l is None or min(e["n"] + l["n"]) < QUICK_MIN_N or None in e["p50"] + l["p50"]:
        return "NO-DATA", f"{lab}: windows {QUICK_EARLY} / {QUICK_LATE} not readable -> NO-DATA"
    d = [e["p50"][k] - l["p50"][k] for k in (0, 1)]
    ok = all(x >= QUICK_KILL - 1e-9 for x in d)
    return ("CONTINUE" if ok else lab), (
        f"{lab}: first-step p50 L/B {e['p50'][0]}/{e['p50'][1]} -> {l['p50'][0]}/{l['p50'][1]} s (each >= {QUICK_KILL} faster; "
        f"n {e['n']} / {l['n']}); reported bonus per spot {e['pay_per_spot']:.4f} -> {l['pay_per_spot']:.4f} -> "
        + ("CONTINUE" if ok else lab))


def quick_check(t: dict, w: dict) -> tuple[str, list[str]]:
    """t, w: agility() of the child and fw1b-S on the same seed (Measure60-Court, mean actions)."""
    lr = (LEFT, BACK)
    valid = t["falls"] <= 2 * w["falls"] and t["worst_arrival"] >= 0.80 and t["fallen_censored_share"] <= 0.15
    arrive = t["worst_arrival"] >= F4_ARRIVE and t["worst_arrival"] >= w["worst_arrival"] - F4_ARRIVE_SLACK
    settle = all(t["settled"][i] >= w["settled"][i] for i in lr)
    falls = t["falls"] <= w["falls"]
    quick = all(t["first_step_p50"][i] is not None and w["first_step_p50"][i] is not None
                and t["first_step_p50"][i] <= w["first_step_p50"][i] - QUICK_MARGIN + 1e-9 for i in lr)
    g = lambda k: f"L/B {t[k][LEFT]}/{t[k][BACK]} vs {w[k][LEFT]}/{w[k][BACK]}"  # noqa: E731
    lines = [f"VALID: falls {t['falls']:.3f} vs {w['falls']:.3f} (<= 2x), worst arrival {t['worst_arrival']:.3f} (>= 0.80), "
             f"fallen+censored {t['fallen_censored_share']:.3f} (<= 0.15) -> {valid}",
             f"ARRIVE: worst arrival {t['worst_arrival']:.3f} vs {w['worst_arrival']:.3f} (>= {F4_ARRIVE} and >= -{F4_ARRIVE_SLACK}) -> {arrive}",
             f"SETTLE: settled {g('settled')} (each >=) -> {settle}",
             f"FALLS: {t['falls']:.3f} vs {w['falls']:.3f} (<=) -> {falls}",
             f"QUICK: first-step p50 {g('first_step_p50')} s (each <= - {QUICK_MARGIN}) -> {quick}",
             f"(reported) FASTER: sustained p50 {g('sustained_p50')} m/s"]
    v = "INVALID" if not valid else "QUICK-OK" if arrive and settle and falls and quick else "QUICK-FAIL"
    return v, lines


# ---------------------------------------------------------------------------------------------------------------------
# D-223 (panel round 86: no majority, (i) 2, (iii) 2, (ii) 1; least new code / fewest moving parts: (ii), RL's form).
# A read-only attribution of h1 (the partner's first ball) on C: pairs.handoff_by_d[class][bin] = [own-ball feeds
# finished, legal], class 0 = the rally's first hand-off, 1 = later; bins on LAUNCH_D_EDGES (receiver's distance from its
# spot at the hand-off). Near = d <= 0.3 m (bins 0-2), far = d > 1.2 m (bin 6).
H1_NEAR_BINS, H1_FAR_BIN = (0, 1, 2), 6
H1_BALL_GAP, H1_POS_GAP, H1_POS_FAR = 0.05, 0.03, 0.40
H1_RECON_TOT, H1_RECON_H1 = 0.01, 0.01


def h1_split(paths: list[str]) -> dict:
    import json
    o = [[[0, 0] for _ in range(8)] for _ in range(2)]
    own = [0, 0]
    for p in paths:
        q = json.load(open(p))["pairs"]
        for c in (0, 1):
            for b in range(8):
                o[c][b][0] += q["handoff_by_d"][c][b][0]
                o[c][b][1] += q["handoff_by_d"][c][b][1]
        for r in q["court_counts"]:
            own[0] += r[0]
            own[1] += r[1]
    near = [[sum(o[c][b][i] for b in H1_NEAR_BINS) for i in (0, 1)] for c in (0, 1)]
    tot0 = sum(x[0] for x in o[0])
    return {"o": o, "own": own, "near": near, "far0": o[0][H1_FAR_BIN], "first_n": tot0,
            "first_legal": sum(x[1] for x in o[0]) / max(tot0, 1), "far_share0": o[0][H1_FAR_BIN][0] / max(tot0, 1),
            "tot": [sum(x[0] for c in o for x in c), sum(x[1] for c in o for x in c)]}


def h1_recon(paths: list[str]) -> tuple[bool, str]:
    """Smoke validity (the D-216 lesson): the tally reconciles with court_counts' own-ball columns and 1 - h1."""
    s = h1_split(paths)
    h1 = pooled_hazards(paths)["h"][1]
    okt = all(abs(s["tot"][i] - s["own"][i]) <= H1_RECON_TOT * max(s["own"][i], 1) for i in (0, 1))
    okh = abs(s["first_legal"] - (1 - h1)) <= H1_RECON_H1
    return okt and okh, (f"H1-RECON: own feeds / legal {s['tot']} vs court_counts {s['own']} (within {H1_RECON_TOT:.0%}); "
                         f"first hand-off legal {s['first_legal']:.4f} vs 1 - h1 {1 - h1:.4f} (within {H1_RECON_H1}) -> "
                         + ("VALID" if okt and okh else "INVALID"))


def h1_route(paths: list[str]) -> tuple[str, list[str]]:
    s = h1_split(paths)
    (n0, l0), (n1, l1) = s["near"]
    if min(n0, n1) < SPAWN_MIN_N:
        return "INVALID-SPLIT", [f"near first / later hand-offs n {n0} / {n1} (each >= {SPAWN_MIN_N})"]
    r0, r1 = l0 / n0, l1 / n1
    w0, w1 = wilson(l0, n0), wilson(l1, n1)
    ball = r1 - r0 >= H1_BALL_GAP - 1e-9 and w0[1] < w1[0]
    pos = abs(r1 - r0) <= H1_POS_GAP + 1e-9 and s["far_share0"] >= H1_POS_FAR - 1e-9
    v = "BALL" if ball else "POSITION" if pos else "MIXED"
    rate = lambda c, b: f"{s['o'][c][b][1] / s['o'][c][b][0]:.3f} (n {s['o'][c][b][0]})" if s["o"][c][b][0] else "-"  # noqa: E731
    lines = [f"near (d <= 0.3 m) legal: first {r0:.4f} (n {n0}, Wilson {w0[0]:.3f}-{w0[1]:.3f}) vs later {r1:.4f} "
             f"(n {n1}, Wilson {w1[0]:.3f}-{w1[1]:.3f}); gap {r1 - r0:+.4f}",
             f"far share of first hand-offs (d > 1.2 m) {s['far_share0']:.3f} (POSITION needs >= {H1_POS_FAR})",
             f"BALL: gap >= {H1_BALL_GAP} and Wilson separated -> {ball}; POSITION: |gap| <= {H1_POS_GAP} and far share "
             f">= {H1_POS_FAR} -> {pos}",
             "(reported) legal by bin, first: " + ", ".join(rate(0, b) for b in range(7)),
             "(reported) legal by bin, later: " + ", ".join(rate(1, b) for b in range(7))]
    return v, lines


# ---------------------------------------------------------------------------------------------------------------------
# D-225 (panel round 88: (iii) 3 of 5; forms differed, least new code: architecture's). What makes the first hand-off
# hard? launch_state.ball_by_class (logging only): legal returns of a feeder ball (class 0: the ball that becomes the
# first hand-off) vs of a handed ball (class 1): keep_alive score, |velocity| and |spin| at the hitter's contact; and the
# receiver's pelvis speed at the hand-off by hand-off class. Route (written before the read):
#   BALL-STATE: feeder-return keep_alive median <= own-ball median - 0.10, or |velocity| p50 >= own + 1.0 m/s -> (ii);
#   RECEIVER: no ball line, and the first hand-off receiver's speed p50 >= later + 0.2 m/s -> panel (outside D-223);
#   NEITHER otherwise -> panel. INVALID if H1-RECON fails or fewer than 200 feeder returns / first hand-offs.
BQ_KA_GAP, BQ_V_GAP, BQ_RS_GAP, BQ_MIN_N = 0.10, 1.0, 0.2, 200


def ball_by_class(paths: list[str]) -> dict:
    import json
    out = None
    for p in paths:
        b = json.load(open(p))["launch_state"]["ball_by_class"]
        if out is None:
            out = {k: (v if not isinstance(v, list) else [list(r) for r in v]) for k, v in b.items()}
        else:
            for k in ("ka", "v", "w", "recv_speed"):
                out[k] = [[x + y for x, y in zip(r, s)] for r, s in zip(out[k], b[k])]
    return out


def ball_route(paths: list[str]) -> tuple[str, list[str]]:
    b = ball_by_class(paths)
    q = lambda k, c, p=0.5: quantile(b[k][c], p, b[k.replace("recv_speed", "rs") + "_bin"] if k != "recv_speed" else b["rs_bin"])  # noqa: E731
    n_ret = [sum(b["v"][c]) for c in (0, 1)]
    n_rs = [sum(b["recv_speed"][c]) for c in (0, 1)]
    if min(n_ret + n_rs) < BQ_MIN_N:
        return "INVALID", [f"counts: feeder / own returns {n_ret}, first / later hand-offs {n_rs} (each >= {BQ_MIN_N})"]
    # keep_alive bins are rounded to the nearest BQ_KA_BIN: the median is read on bin centres
    ka = [quantile(b["ka"][c], 0.5, b["ka_bin"]) - b["ka_bin"] / 2 for c in (0, 1)]
    v = [q("v", c) for c in (0, 1)]
    w = [q("w", c) for c in (0, 1)]
    rs = [q("recv_speed", c) for c in (0, 1)]
    ball = ka[0] <= ka[1] - BQ_KA_GAP + 1e-9 or v[0] >= v[1] + BQ_V_GAP - 1e-9
    recv = rs[0] >= rs[1] + BQ_RS_GAP - 1e-9
    verdict = "BALL-STATE" if ball else "RECEIVER" if recv else "NEITHER"
    lines = [f"keep_alive median feeder-return {ka[0]:.3f} vs own-ball {ka[1]:.3f} (BALL if <= -{BQ_KA_GAP}); n {n_ret}",
             f"|velocity| p50 feeder-return {v[0]:.2f} vs own-ball {v[1]:.2f} m/s (BALL if >= +{BQ_V_GAP}); "
             f"p90 {q('v', 0, 0.9):.2f} / {q('v', 1, 0.9):.2f}",
             f"(reported) |spin| p50 {w[0]:.1f} vs {w[1]:.1f} rad/s",
             f"receiver speed p50 at first vs later hand-offs {rs[0]:.2f} vs {rs[1]:.2f} m/s (RECEIVER if >= +{BQ_RS_GAP}); "
             f"p90 {q('recv_speed', 0, 0.9):.2f} / {q('recv_speed', 1, 0.9):.2f}; n {n_rs}"]
    return verdict, lines


# ---------------------------------------------------------------------------------------------------------------------
# D-227 (panel round 90: (b) 5 of 5, opened with its premise run; (a) first). fw-scratch-01: Q2's task from a random
# init (no model_15900 lineage). Kill at +1,800 (30 % of 6,000), training log rows (one per 10 iterations, step =
# iteration x STEPS_PER_IT, start 0), experiment design's form: VOID-unstable (falls over the last 100 iterations > 8.314,
# read from the +1,800 check on) and KILL-NO-START (first-step p50 over 1,700-1,800 slower in left or back than Q2's
# 400-450 window, or n < 200 in either).
SCRATCH_KILL_WIN = (1700, 1800)
SCRATCH_REF = (1.2733, 1.3847)  # Q2 (D-222) 400-450, left / back


def scratch_kill(rows: list[dict]) -> tuple[str, str]:
    w = first_window(rows, *SCRATCH_KILL_WIN, 0)
    lab = "KILL-NO-START"
    if w is None:
        return "NO-DATA", f"{lab}: window {SCRATCH_KILL_WIN} not readable -> NO-DATA"
    ok_n = min(w["n"]) >= QUICK_MIN_N and None not in w["p50"]
    ok = ok_n and all(w["p50"][k] <= SCRATCH_REF[k] + 1e-9 for k in (0, 1))
    return ("CONTINUE" if ok else lab), (
        f"{lab}: first-step p50 L/B over {SCRATCH_KILL_WIN} {w['p50'][0]}/{w['p50'][1]} s vs Q2's 400-450 "
        f"{SCRATCH_REF[0]}/{SCRATCH_REF[1]} (each <=; n {w['n']} >= {QUICK_MIN_N}) -> " + ("CONTINUE" if ok else lab))


def set_start_report(paths: list[str], ref_paths: list[str]) -> list[str]:
    """D-227 (reported only, not a score): C under a set start against C's standard reads."""
    out = []
    for name, f in (("set start", paths), ("standard", ref_paths)):
        pp, hz, cv = pooled_pairs(f), pooled_hazards(f), court_conv(f)
        out.append(f"(reported) {name}: P(5+) {pp['p5']:.4f} (rallies {pp['rallies']}), feeder legal {pp['feeder']:.4f}, "
                   f"hazards h0-h4 " + " / ".join(f"{x:.3f}" for x in hz["h"]) + f", q0 {cv['q0']:.3f} q1 {cv['q1']:.3f}")
    return out


# ---------------------------------------------------------------------------------------------------------------------
# D-231 (panel round 92, (d) 5 of 5; lines by experiment design's form where they differed). R = rally-d1s3dr: C on
# Picklebot-Rally22b-FastMove-DrillReset-G1 (C's task + the D-229 drill reset). Training windows from the pair log rows
# (one per 20 iterations; step = iteration x STEPS_PER_IT): the pair courts' (group 0) finished rallies by length, and the
# launch summary's placement count.
OPEN_KILL_GAIN = 0.02          # KILL-NO-OPEN: (1 - h0)(1 - h1) over 220-340 >= the run's own 20-140 window + 0.02
OPEN_MIN_RALLIES = 500         # a window is readable with >= 500 finished pair-court rallies
DR_DOSE = (1.9, 2.05)          # placements per finished pair-court rally (two robots per restart)
DR_EARLY, DR_LATE = (20, 140), (220, 340)


def train_open(rows: list[dict], it_lo: int, it_hi: int, start_it: int):
    rows = [r for r in rows if "len_hist_group" in r]
    a = _row_from(rows, (start_it + it_lo) * STEPS_PER_IT)
    b = None if a is None else _row_from(rows, max((start_it + it_hi) * STEPS_PER_IT, a["step"] + (it_hi - it_lo) * STEPS_PER_IT))
    if a is None or b is None:
        return None
    h = [y - x for x, y in zip(a["len_hist_group"][0], b["len_hist_group"][0])]
    n = sum(h)
    r0 = sum(h)
    r1 = sum(h[1:])
    h0 = h[0] / r0 if r0 else float("nan")
    h1 = h[1] / r1 if r1 else float("nan")
    pa = a.get("launch", {}).get("drill_places", 0)
    pb = b.get("launch", {}).get("drill_places", 0)
    return {"n": n, "h0": h0, "h1": h1, "open2": (1 - h0) * (1 - h1), "places_per_rally": (pb - pa) / max(n, 1),
            "skipped": b.get("launch", {}).get("drill_place_skipped", 0) - a.get("launch", {}).get("drill_place_skipped", 0)}


def dr_dose(rows: list[dict], start_it: int) -> tuple[bool, str]:
    w = train_open(rows, *DR_EARLY, start_it)
    if w is None or w["n"] < OPEN_MIN_RALLIES:
        return False, f"drill-reset dose over {DR_EARLY}: {w} (>= {OPEN_MIN_RALLIES} pair-court rallies) -> NO-DATA"
    ok = DR_DOSE[0] <= w["places_per_rally"] <= DR_DOSE[1]
    return ok, (f"drill-reset dose over {DR_EARLY}: {w['places_per_rally']:.3f} placements per pair-court rally (in {DR_DOSE}), "
                f"n {w['n']}, skipped busy {w['skipped']}, open2 {w['open2']:.4f}")


def open_kill(rows: list[dict], start_it: int) -> tuple[str, str]:
    e, l = train_open(rows, *DR_EARLY, start_it), train_open(rows, *DR_LATE, start_it)
    lab = "KILL-NO-OPEN"
    if e is None or l is None or min(e["n"], l["n"]) < OPEN_MIN_RALLIES:
        return "NO-DATA", f"{lab}: windows {DR_EARLY} / {DR_LATE} not readable -> NO-DATA"
    ok = l["open2"] >= e["open2"] + OPEN_KILL_GAIN - 1e-9
    return ("CONTINUE" if ok else lab), (
        f"{lab}: training (1-h0)(1-h1) {e['open2']:.4f} over {DR_EARLY} -> {l['open2']:.4f} over {DR_LATE} "
        f"(>= +{OPEN_KILL_GAIN}; n {e['n']} / {l['n']}; h0 {e['h0']:.3f} -> {l['h0']:.3f}, h1 {e['h1']:.3f} -> {l['h1']:.3f}) -> "
        + ("CONTINUE" if ok else lab))


# ---------------------------------------------------------------------------------------------------------------------
# D-232 (panel round 93, (i) 5 of 5): F = rally-d1s3drf, R (rally-d1s3dr model_33797, unpromoted: NO-CANDIDATE on R3) +
# D-063's fall penalty. Lines, by majority with experiment design's form where they differed:
FALL_KILL_GAP = 0.01     # KILL-NO-FALLS: the +360 checkpoint's court falls / episode <= R's on the same seed - 0.01
OPEN_KEEP = 0.02         # KILL-LOST-OPEN: training (1-h0)(1-h1) over 220-340 >= the run's own 20-140 window - 0.02
R_KEPT = 0.02            # R-KEPT (gate): pooled P(5+) >= R's - 0.02 on the same seeds
R3_MAX = 0.04            # R3 (gate): court falls / episode <= 0.04


def fall_kill(child_rate: float, r_rate: float) -> tuple[str, str]:
    ok = child_rate <= r_rate - FALL_KILL_GAP + 1e-9
    return ("CONTINUE" if ok else "KILL-NO-FALLS"), (
        f"KILL-NO-FALLS: +360 court falls per episode {child_rate:.4f} vs R {r_rate:.4f} on the same seed "
        f"(<= -{FALL_KILL_GAP}) -> " + ("CONTINUE" if ok else "KILL-NO-FALLS"))


def open_keep_kill(rows: list[dict], start_it: int) -> tuple[str, str]:
    e, l = train_open(rows, *DR_EARLY, start_it), train_open(rows, *DR_LATE, start_it)
    lab = "KILL-LOST-OPEN"
    if e is None or l is None or min(e["n"], l["n"]) < OPEN_MIN_RALLIES:
        return "NO-DATA", f"{lab}: windows {DR_EARLY} / {DR_LATE} not readable -> NO-DATA"
    ok = l["open2"] >= e["open2"] - OPEN_KEEP - 1e-9
    return ("CONTINUE" if ok else lab), (
        f"{lab}: training (1-h0)(1-h1) {e['open2']:.4f} over {DR_EARLY} -> {l['open2']:.4f} over {DR_LATE} "
        f"(>= -{OPEN_KEEP}; n {e['n']} / {l['n']}) -> " + ("CONTINUE" if ok else lab))


def r_kept(child_paths: list[str], r_paths: list[str]) -> tuple[bool, str]:
    c, r = pooled_pairs(child_paths)["p5"], pooled_pairs(r_paths)["p5"]
    ok = c >= r - R_KEPT - 1e-9
    return ok, f"R-KEPT: P(5+) {c:.4f} vs R {r:.4f} (>= -{R_KEPT}) -> {ok}"


# D-234 (panel round 95, (ii) 4 of 5): the R3 premise read. R (and C) against the d1 base read as a zero-residual
# checkpoint on R3's exact instrument, same seeds. Each read's fall_log splits robot falls into SPAWN (< 1.0 s after the
# episode start, either phase), FEED (a feed in play, >= 1.0 s) and RECOVERY (between feeds, >= 1.0 s). R's excess over
# the base, per episode, is shared out over those three; a class with >= 50 % of the excess names the route.
R3_SPAWN_S = 1.0
R3_ROUTE_SHARE = 0.5


def fall_classes(read: dict) -> dict:
    fl, eps = read["fall_log"], max(int(read["robot_episodes"]), 1)
    k = int(round(R3_SPAWN_S / fl["t_bin_s"]))
    feed, betw = fl["by_t"]
    n = {"SPAWN": sum(feed[:k]) + sum(betw[:k]), "FEED": sum(feed[k:]), "RECOVERY": sum(betw[k:])}
    return {"falls": n, "per_ep": {c: v / eps for c, v in n.items()}, "booked": sum(feed) + sum(betw),
            "robot_falls": int(read["robot_falls"]), "rate": float(read["robot_fall_rate_per_episode"])}


def r3_route(base: dict, r: dict) -> tuple[str, str]:
    b, x = fall_classes(base), fall_classes(r)
    lines = []
    for w, c in (("base", b), ("R", x)):
        if c["booked"] != c["robot_falls"]:
            return "INVALID", f"INVALID: {w} booked {c['booked']} falls vs robot_falls {c['robot_falls']}"
    if b["rate"] > R3_MAX + 1e-9:
        return "BASE-FAILS", f"BASE-FAILS: the d1 base's R3 {b['rate']:.4f} > {R3_MAX} on R3's own instrument"
    exc = {c: x["per_ep"][c] - b["per_ep"][c] for c in x["per_ep"]}
    tot = x["rate"] - b["rate"]
    lines.append(f"R3 base {b['rate']:.4f}, R {x['rate']:.4f}, excess {tot:+.4f} per episode")
    for c in exc:
        lines.append(f"  {c}: base {b['per_ep'][c]:.4f} R {x['per_ep'][c]:.4f} excess {exc[c]:+.4f}"
                     + (f" ({exc[c] / tot:.0%} of the excess)" if tot > 0 else ""))
    route = "MIXED"
    if tot > 0:
        for c in ("SPAWN", "RECOVERY", "FEED"):
            if exc[c] >= R3_ROUTE_SHARE * tot - 1e-12:
                route = c
                break
    else:
        route = "NO-EXCESS"
    return route, "\n".join(lines + [f"ROUTE: {route}"])


# D-236 (panel round 96, (ii) 3 of 5): rally-d1s3drl2 (D-235) continued from model_34160 to model_34996. D-194's
# log-based lines are replaced for launcher-court runs (an 8-s launcher episode's reward sum, and the Poisson falls
# estimator, both measure the episode mix): exact pair-court and off-launcher counts from the share log.
HIT_RATIO = 0.9          # KILL-NO-HIT (D-236): pair-court mean rally length >= 0.9 x R's at the same offsets
EXACT_FALLS_MAX = 3.14   # KILL-UNSTABLE (D-236): exact falls per 1,000 env-s off the launcher courts (D-194's value)
LAUNCH_KILL_WIN = (481, 600)


def pair_rally(rows: list[dict], it_lo: int, it_hi: int, start_it: int) -> tuple[float, int]:
    """Pair-court (len_hist_group[0]) mean rally length and rally count over the window."""
    rows = [r for r in rows if "len_hist_group" in r]
    a = _row_from(rows, (start_it + it_lo) * STEPS_PER_IT)
    b = None if a is None else _row_from(rows, (start_it + it_hi) * STEPS_PER_IT)
    if a is None or b is None or b["step"] <= a["step"]:
        return float("nan"), 0
    h = [y - x for x, y in zip(a["len_hist_group"][0], b["len_hist_group"][0])]
    n = sum(h)
    return (sum(i * c for i, c in enumerate(h)) / n if n else float("nan")), n


def exact_falls(rows: list[dict], it_lo: int, it_hi: int, start_it: int, dt: float = 0.02) -> float:
    """Falls per 1,000 env-s off the launcher courts (launch_courts.other_falls) over the window."""
    rows = [r for r in rows if "other_falls" in r.get("launch", {}).get("launch_courts", {})]
    a = _row_from(rows, (start_it + it_lo) * STEPS_PER_IT)
    b = None if a is None else _row_from(rows, (start_it + it_hi) * STEPS_PER_IT)
    if a is None or b is None or b["step"] <= a["step"]:
        return float("nan")
    la, lb = a["launch"]["launch_courts"], b["launch"]["launch_courts"]
    return 1000 * (lb["other_falls"] - la["other_falls"]) / ((b["step"] - a["step"]) * dt)


def launch_kill(rows, r_rows, start_it, r_start, envs_other, win=LAUNCH_KILL_WIN) -> list[tuple[str, str]]:
    """D-236's log lines over win (all read; the caller stops on any KILL)."""
    out = []
    c, nc = pair_rally(rows, *win, start_it)
    p, npar = pair_rally(r_rows, *win, r_start)
    if c != c or p != p or min(nc, npar) < MIN_WINDOW_EVENTS:
        out.append(("NO-DATA", f"KILL-NO-HIT: pair-court rally length {c} (n {nc}) vs R {p} (n {npar}) -> NO-DATA"))
    else:
        v = "CONTINUE" if c >= HIT_RATIO * p - 1e-9 else "KILL-NO-HIT"
        out.append((v, f"KILL-NO-HIT: pair-court mean rally length +{win[0]}-{win[1]} {c:.3f} vs R {p:.3f} "
                       f"(>= {HIT_RATIO} x; n {nc} / {npar}) -> {v}"))
    f = exact_falls(rows, *win, start_it) / envs_other if envs_other else float("nan")
    v = "NO-DATA" if f != f else ("CONTINUE" if f <= EXACT_FALLS_MAX else "KILL-UNSTABLE")
    out.append((v, f"KILL-UNSTABLE: exact falls off the launcher courts {f:.3f} per 1,000 env-s (<= {EXACT_FALLS_MAX}) -> {v}"))
    return out


# ---------------------------------------------------------------------------------------------------------------------
# D-240 (panel round 100, (i) 5 of 5; the lever by majority and the tie rule: the training-only pair_rally_cap 8, RL and
# experiment design, architecture's value): P = M (rally-d1s3drl3 model_34996) on D-235's launcher-court task (move
# weights x1) with pair_rally_cap 8 in training. Smoke: D-235's lines plus the pair-court feeder share >= 2.0 x M's 0.0667
# (prediction 0.185 from M's length histogram, recorded before the smoke). Kill at +240 over +181-240, paired with M's
# post-restart +181-240 (M resumed from 34160): KILL-LOST-OPEN, KILL-UNSTABLE, KILL-NO-FALLS (dev 4220404); the rally-length
# line is void under the cap. Training-log lines are read first and stop training at once on a KILL; the dev read follows.
# Gate: D-239's lines plus OPEN, pooled (1-h0)(1-h1) >= M's + 0.02, with R3 on dev 4220405.
CAP8 = 8
CAP8_SHARE_MIN = 0.1334        # 2.0 x M's pair-court feeder share 0.0667 (results/lc98-train-share.jsonl, last row)
CAP8_SHARE_PRED = 0.185        # predicted from M's pair-court length histogram (round 100)
CAP8_KILL_WIN = (181, 240)
M_START, M_OPEN_181_240 = 34160, 0.6519   # M's post-restart window (results/lc98-train-share.jsonl)
OPEN_GATE_GAIN = 0.02


def pair_feeder_share(rows: list[dict]) -> tuple[float, int]:
    """Pair-court feeder share of balls (split[0] = [feeder, other]) between the first and last logged rows."""
    rows = [r for r in rows if "split" in r]
    if len(rows) < 2:
        return float("nan"), 0
    a, b = rows[0]["split"][0], rows[-1]["split"][0]
    f, o = b[0] - a[0], b[1] - a[1]
    return (f / (f + o) if f + o else float("nan")), f + o


def cap8_kill(rows: list[dict], start_it: int, envs_other: int, m_rows: list[dict]) -> list[tuple[str, str]]:
    """D-240's training-log lines over CAP8_KILL_WIN, paired with M's post-restart window (all read)."""
    out = []
    e, l = train_open(m_rows, *CAP8_KILL_WIN, M_START), train_open(rows, *CAP8_KILL_WIN, start_it)
    if e is None or l is None or min(e["n"], l["n"]) < OPEN_MIN_RALLIES:
        out.append(("NO-DATA", f"KILL-LOST-OPEN: windows not readable ({e and e['n']} / {l and l['n']}) -> NO-DATA"))
    else:
        v = "CONTINUE" if l["open2"] >= e["open2"] - OPEN_KEEP - 1e-9 else "KILL-LOST-OPEN"
        out.append((v, f"KILL-LOST-OPEN: training (1-h0)(1-h1) +{CAP8_KILL_WIN[0]}-{CAP8_KILL_WIN[1]} {l['open2']:.4f} vs M's "
                       f"{e['open2']:.4f} (>= -{OPEN_KEEP}; n {l['n']} / {e['n']}) -> {v}"))
    f = exact_falls(rows, *CAP8_KILL_WIN, start_it) / envs_other if envs_other else float("nan")
    v = "NO-DATA" if f != f else ("CONTINUE" if f <= EXACT_FALLS_MAX else "KILL-UNSTABLE")
    out.append((v, f"KILL-UNSTABLE: exact falls off the launcher courts {f:.3f} per 1,000 env-s (<= {EXACT_FALLS_MAX}) -> {v}"))
    return out


def open_gate(child_paths: list[str], m_paths: list[str]) -> tuple[bool, str]:
    c, m = pooled_hazards(child_paths), pooled_hazards(m_paths)
    ok = c["open2"] >= m["open2"] + OPEN_GATE_GAIN - 1e-9
    return ok, (f"OPEN: pooled (1-h0)(1-h1) {c['open2']:.4f} vs M {m['open2']:.4f} (>= +{OPEN_GATE_GAIN}; h0 {c['h'][0]:.3f} / "
                f"{m['h'][0]:.3f}, h1 {c['h'][1]:.3f} / {m['h'][1]:.3f}) -> {ok}")


# ---------------------------------------------------------------------------------------------------------------------
# D-241 (panel round 101, 5 of 5 after the agent's facts check): P = N (rally-d1s3cap8 model_35595, unpromoted:
# CONFIRM-FAIL on the left + back guard, -5.2 vs -5) on D-235's launcher-court task with the set start on half the live
# pair courts only (pair_drill_reset_frac 0.5); pair_rally_cap 8 stays. Training-log windows split the pair courts into
# the reset half (len_hist_group[0] minus len_hist_sub) and the free half (len_hist_sub).
N_START, N_OPEN_181_240 = 34996, 0.7273   # N's +181-240 training (1-h0)(1-h1), every pair court reset (lc102 log)
HALF_KILL_WIN = (181, 240)
HALF_DOSE = (1.9, 2.05)                    # placements per reset-half rally (two robots per restart)


def train_open_half(rows: list[dict], it_lo: int, it_hi: int, start_it: int):
    """(reset half, free half) training windows; None, None when the rows do not cover the window."""
    rows = [r for r in rows if "len_hist_group" in r and r.get("launch", {}).get("len_hist_sub") is not None]
    a = _row_from(rows, (start_it + it_lo) * STEPS_PER_IT)
    b = None if a is None else _row_from(rows, max((start_it + it_hi) * STEPS_PER_IT, a["step"] + (it_hi - it_lo) * STEPS_PER_IT))
    if a is None or b is None:
        return None, None
    g = [y - x for x, y in zip(a["len_hist_group"][0], b["len_hist_group"][0])]
    f = [y - x for x, y in zip(a["launch"]["len_hist_sub"], b["launch"]["len_hist_sub"])]

    def win(h):
        n = sum(h)
        h0 = h[0] / n if n else float("nan")
        h1 = h[1] / sum(h[1:]) if sum(h[1:]) else float("nan")
        return {"n": n, "h0": h0, "h1": h1, "open2": (1 - h0) * (1 - h1)}
    rh, fh = win([x - y for x, y in zip(g, f)]), win(f)
    rh["places_per_rally"] = (b["launch"]["drill_places"] - a["launch"]["drill_places"]) / max(rh["n"], 1)
    fh["places_off"] = b["launch"].get("drill_places_off", 0) - a["launch"].get("drill_places_off", 0)
    return rh, fh


def half_dose(rows: list[dict], start_it: int) -> tuple[bool, str]:
    rh, fh = train_open_half(rows, *DR_EARLY, start_it)
    if rh is None or min(rh["n"], fh["n"]) < OPEN_MIN_RALLIES // 2:
        return False, f"half-reset dose over {DR_EARLY}: not readable ({rh and rh['n']} / {fh and fh['n']} rallies) -> NO-DATA"
    ok = HALF_DOSE[0] <= rh["places_per_rally"] <= HALF_DOSE[1] and fh["places_off"] == 0
    return ok, (f"half-reset dose over {DR_EARLY}: reset half {rh['places_per_rally']:.3f} placements per rally (in {HALF_DOSE}; "
                f"n {rh['n']}), free half {fh['places_off']} placements (== 0; n {fh['n']})")


def half_kill(rows: list[dict], start_it: int, envs_other: int, ref_open: float = N_OPEN_181_240,
              ref_name: str = "N") -> list[tuple[str, str]]:
    """D-241's training-log lines over HALF_KILL_WIN (all read): KILL-LOST-OPEN on the reset half against N's paired
    window (N reset every pair court), the free half reported; KILL-UNSTABLE."""
    out = []
    rh, fh = train_open_half(rows, *HALF_KILL_WIN, start_it)
    if rh is None or rh["n"] < OPEN_MIN_RALLIES // 2:
        out.append(("NO-DATA", f"KILL-LOST-OPEN: reset-half window not readable ({rh and rh['n']}) -> NO-DATA"))
    else:
        v = "CONTINUE" if rh["open2"] >= ref_open - OPEN_KEEP - 1e-9 else "KILL-LOST-OPEN"
        out.append((v, f"KILL-LOST-OPEN: reset-half training (1-h0)(1-h1) +{HALF_KILL_WIN[0]}-{HALF_KILL_WIN[1]} {rh['open2']:.4f} "
                       f"vs {ref_name}'s {ref_open} (>= -{OPEN_KEEP}; n {rh['n']}); (reported) free half {fh['open2']:.4f} (n {fh['n']}) -> {v}"))
    f = exact_falls(rows, *HALF_KILL_WIN, start_it) / envs_other if envs_other else float("nan")
    v = "NO-DATA" if f != f else ("CONTINUE" if f <= EXACT_FALLS_MAX else "KILL-UNSTABLE")
    out.append((v, f"KILL-UNSTABLE: exact falls off the launcher courts {f:.3f} per 1,000 env-s (<= {EXACT_FALLS_MAX}) -> {v}"))
    return out


def left_contact(path: str) -> tuple[float, int]:
    import json
    d = json.load(open(path))["directions"]["left"]
    return d["contact"], d["feeds"]


# ---------------------------------------------------------------------------------------------------------------------
# D-242 (panel round 102, the lever 3 of 5, the parent 3 of 5): P = the D-241 child (rally-d1s3cap8h model_36194,
# NO-CANDIDATE on K3-KEPT alone) with pair_rally_cap 8 on the set-start half only (pair_rally_cap_reset_only); the free
# half plays uncapped. Lines in experiment design's form.
P_START, P_OPEN_181_240 = 35595, 0.7351   # the child's +181-240 reset-half training (1-h0)(1-h1) (lc103 log)
CAPR_SHARE_PRED = None                     # set by the driver from the prediction recorded before the smoke
CAPR_BAND = 0.25                           # the smoke share must fall within +/- 25 % of the prediction


def cap_split(rows: list[dict]) -> dict:
    """Between the first and last rows: the pair-court feeder share, the reset half's longest rally and the free half's
    rallies ending at 9-15 shots (len_hist index = legal returns in the rally)."""
    rows = [r for r in rows if r.get("launch", {}).get("len_hist_sub") is not None and "split" in r]
    if len(rows) < 2:
        return {}
    a, b = rows[0], rows[-1]
    g = [y - x for x, y in zip(a["len_hist_group"][0], b["len_hist_group"][0])]
    f = [y - x for x, y in zip(a["launch"]["len_hist_sub"], b["launch"]["len_hist_sub"])]
    r = [x - y for x, y in zip(g, f)]
    share, nb = pair_feeder_share(rows)
    return {"share": share, "balls": nb, "reset_max": max([i for i, c in enumerate(r) if c > 0], default=-1),
            "reset_n": sum(r), "free_9_15": sum(f[9:16]), "free_n": sum(f), "free_over8": sum(f[9:]) / max(sum(f), 1)}


def late_split(paths: list[str]) -> dict:
    """K3's late failures split by where the rally ended (shots 3-4 / 5-7 / 8+), pooled over pairs reads."""
    import json
    h = None
    for p in paths:
        q = json.load(open(p))["pairs"]["len_hist"]
        h = list(q) if h is None else [x + y for x, y in zip(h, q)]
    return {"3-4": sum(h[3:5]), "5-7": sum(h[5:8]), "8+": sum(h[8:])}


# ---------------------------------------------------------------------------------------------------------------------
# D-244 (panel round 104; no majority: cap 5 on the set-start half (RL, experiment design), the weak-family feed-mix
# weights (coach x3, motion x2), a free-half cap 16 (architecture); the tie rule: both front options need no new code,
# so experiment design's position): P = Q (rally-d1s3cap8hr2 model_36793, CONFIRMED in D-243) with pair_rally_cap 5 on
# the set-start half only. The CONFIRM block is registered as the target read (results/rally-target.md).
Q_START, Q_OPEN_181_240 = 36194, 0.7356   # Q's +181-240 reset-half training (1-h0)(1-h1) (lc105 log)
CAP5_SHARE_PRED = 0.160                    # 0.5 / 4.46 + 0.5 / 10.47 (Q's second-half log; the formula gives 0.1306 for
                                           # cap 8 against Q's measured 0.1297)
K3_LINE = 0.0269 + 0.005                   # KILL-LATE: one pairs read's late failure share <= C's gate K3 + 0.005
TARGET_P5, TARGET_WILSON, TARGET_SIDES, TARGET_R3 = 0.80, 0.78, 0.03, 0.04


def target_read(paths: list[str], r3: float) -> tuple[bool, list[str]]:
    """The frozen rally target on a pooled pairs read: P(5+) (open rallies counted) >= 0.80 with Wilson low >= 0.78
    over >= 1,000 rallies, sides A and B within 3 points of legal returns, court falls / episode <= 0.04."""
    import json
    import math
    q = pooled_pairs(paths)
    n = q["rallies"]
    k = round(q["p5"] * n)
    z = 1.96
    p = k / max(n, 1)
    d = 1 + z * z / max(n, 1)
    lo = (p + z * z / (2 * n) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / d if n else 0.0
    sides = {}
    for pth in paths:
        for s, v in json.load(open(pth))["pairs"]["sides"].items():
            a = sides.setdefault(s, [0.0, 0])
            a[0] += v["legal"] * v["feeds"]; a[1] += v["feeds"]
    leg = {s: a[0] / max(a[1], 1) for s, a in sides.items()}
    gap = max(leg.values()) - min(leg.values()) if leg else 1.0
    ok = {"p5": p >= TARGET_P5, "wilson": lo >= TARGET_WILSON and n >= 1000, "sides": gap <= TARGET_SIDES, "r3": r3 <= TARGET_R3}
    lines = [f"TARGET P(5+) {p:.4f} (>= {TARGET_P5}; {k} of {n}) -> {ok['p5']}",
             f"TARGET Wilson low {lo:.4f} (>= {TARGET_WILSON}, n >= 1000) -> {ok['wilson']}",
             f"TARGET sides legal {', '.join(f'{s} {v:.4f}' for s, v in leg.items())}: gap {gap:.4f} (<= {TARGET_SIDES}) -> {ok['sides']}",
             f"TARGET R3 court falls / episode {r3:.4f} (<= {TARGET_R3}) -> {ok['r3']}"]
    return all(ok.values()), lines


# ---------------------------------------------------------------------------------------------------------------------
# D-245 (panel round 105, 4 of 5 for the weak-family feed dose, x2 by 3 of 5): P = Q (D-243) on Q's recipe (cap 8 on the
# set-start half) with training feed-mix weights x2 on reach_deep, cross_backhand and reach_backhand (the families
# that held 424 of Q's 616 feeder misses). Lines in experiment design's form.
FAM3 = ("reach_deep", "cross_backhand", "reach_backhand")
FAM3_SHARE_PRED = 6.0 / 23.0       # 20 families at weight 1, three at 2 (zone validity ignored); recorded before the smoke
CAP8_Q_SHARE_PRED = 0.1306         # D-244's formula on Q's second-half log at cap 8 (Q measured 0.1297)


def fam3_share(rows: list[dict]) -> tuple[float, int]:
    """Share of pair-court feeder balls in FAM3 between the first and last rows that log fam_feeder."""
    from picklebot_mj.feeds import FAMILY_NAMES
    rows = [r for r in rows if r.get("launch", {}).get("fam_feeder") is not None]
    if len(rows) < 2:
        return float("nan"), 0
    d = [y - x for x, y in zip(rows[0]["launch"]["fam_feeder"], rows[-1]["launch"]["fam_feeder"])]
    n = sum(d)
    k = sum(d[FAMILY_NAMES.index(f)] for f in FAM3)
    return (k / n if n else float("nan")), n


# D-246 (panel round 106, (a)): D-245 re-run on a fresh smoke seed. The cap-split share prediction is now a smoke read of
# the same parent and recipe (+20-140, 1,024 envs), not a training log: D-245's smoke read 0.1642.
D246_SHARE_PRED = 0.1642


# D-248 (D-247's rule -> (b)): D-246 re-run with OPEN-DEV in place of the training-log KILL-LOST-OPEN. Smoke predictions
# from D-246's smoke (same parent and recipe): pair-court feeder share 0.1626; three-family share of sampled feeds 0.303
# (D-246's counter counted every refeed's draw, which samples the same mix as feeder balls).
D248_SHARE_PRED = 0.1626
D248_FAM3_PRED = 0.303


# D-249 (panel round 108, 5 of 5; the user's direction to train with the pro videos): Q on Q's recipe with the move drill's
# spots drawn from the frozen pro-move table (tasks/pro_move.py). Smoke share predictions from a basis smoke of Q's
# unchanged recipe (same parent and recipe, recorded before the child smoke); the child smoke's issued back share (after
# MoveDrill's flips) >= half the table's (experiment design's line).
PRO_BACK_TABLE = 23 / 167
PRO_MIN_SPOTS = 200


def pro_back(rows: list[dict]) -> tuple[bool, str]:
    """From the last share-log row's cumulative move_pro counters (launch_summary)."""
    rows = [r for r in rows if r.get("launch", {}).get("move_pro")]
    if not rows:
        return False, "pro-move spots: no move_pro rows -> NO-DATA"
    m = rows[-1]["launch"]["move_pro"]
    c = m["pro_class"]
    n = sum(c)
    sh = [x / n if n else float("nan") for x in c]
    ok = n >= PRO_MIN_SPOTS and sh[2] >= PRO_BACK_TABLE / 2 - 1e-9
    return ok, (f"pro-move spots: issued back share {sh[2]:.3f} (>= {PRO_BACK_TABLE / 2:.3f}, half the table's; n {n} >= "
                f"{PRO_MIN_SPOTS}); (reported) forward / left / back / right {' / '.join(f'{x:.3f}' for x in sh)} (table "
                f"0.246 / 0.305 / 0.138 / 0.311), flipped {sum(m['flipped']) / max(n, 1):.3f}, clipped "
                f"{sum(m['clipped']) / max(n, 1):.3f}, arrived {sum(m['arrived']) / max(n, 1):.3f}")
