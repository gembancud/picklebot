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
    lines = [f"legal(d <= 0.3) {pn:.4f} (n {near[0]}, Wilson {nlo:.3f}-{nhi:.3f}); legal(d > 1.2) {pf:.4f} (n {far[0]}, Wilson "
             f"{flo:.3f}-{fhi:.3f}); gap {pn - pf:+.4f}",
             f"RESTART-BINDS: near >= {D216_NEAR} and gap >= {D216_GAP} and intervals apart -> {restart}; "
             f"SHOT-BINDS: near < {D216_SHOT} -> {shot}",
             f"(reported) coach's route: legal(d <= 1.2) {pw:.4f} >= 0.70 and far <= near - 0.10 -> {coach}",
             "(reported) legal by bin: " + ", ".join(f"{x[1] / max(x[0], 1):.3f} (n {x[0]})" for x in out_by_d)]
    return v, lines
