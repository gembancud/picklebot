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
