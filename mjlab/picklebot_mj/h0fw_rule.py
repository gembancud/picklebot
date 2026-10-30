"""H0 fine-tune h0-fw-01 kill and endpoint rule (D-185, panel round 54). Reads are tracking_eval.py --per-stroke JSONs
with the travel instrument; every child read is paired with the parent (s5c-03b model_63300) on the same dev seed.

  fw = footwork-fast read; tl = tennis-lafan3 read (tennis strokes + LAFAN1 + mirrored LAFAN1 windows).
  D_fw / D_lafan / S_fw / TR: travel_rule.read_stats (FAST windows; LAFAN1 falls back to all windows if < 30 envs).
Kill at +900 (single seed pair): KILL if D_fw < 0.70 or D_lafan < 0.80 or fw FAST success < 0.90 or any stroke type
  > 10 points below the parent or S_fw > S_parent + 0.05 or falls > 2 x parent (floor 0.005); INSTRUMENT if any travel
  read fails travel_rule's instrument check.
Endpoint (fw one pair, tl two pairs; stroke and LAFAN success as the mean of the two tl seeds):
  H0F-PASS iff D_fw >= 0.90, D_lafan >= 0.90, D_fw <= 1.10, fw FAST success >= 0.95, tennis r_mpkpe <= parent + 0.010,
  each stroke type >= parent - 0.03, LAFAN1 and mirrored-LAFAN1 success >= parent - 0.03, S_fw <= S_parent + 0.03,
  tennis |robot - reference displacement| p50 <= 0.18 m, tennis ee_pos_error <= parent + 0.01, instrument OK;
  H0F-FAIL if D_lafan < 0.90 (the objective change did not work: O2 next, as its own run);
  H0F-RETENTION if the travel lines (D_fw >= 0.90, D_lafan >= 0.90, D_fw <= 1.10) pass and another line fails;
  H0F-PARTIAL otherwise (D_lafan passes, D_fw does not): re-ask the panel.
h0-fw-02 (D-186, panel round 55) calls the same functions with stricter options: kill(d_lafan_min=0.82,
  lafan_succ_drop=0.05) adds the anti-lunge line (LAFAN1 and mirrored-LAFAN1 success >= parent - 0.05); endpoint(ho=...)
  adds the held-out footwork gate (D_fwHO >= 0.90 and <= 1.10 on clips never trained on), counted with the travel lines.
"""

from __future__ import annotations

import numpy as np

from picklebot_mj import travel_rule as tr

STROKES = ("serve", "smash", "forehand_volley", "backhand_volley", "forehand", "backhand")
KILL_D_FW, KILL_D_LAFAN, KILL_FAST_SUCC, KILL_STROKE, KILL_SLIP, KILL_FALLS = 0.70, 0.80, 0.90, 0.10, 0.05, 2.0
OK, D_MAX, FAST_SUCC, RMPKPE, STROKE, SLIP, DISP_TENNIS, EE = 0.90, 1.10, 0.95, 0.010, 0.03, 0.03, 0.18, 0.01


def lafan_stats(d: dict) -> dict:
    s = tr.read_stats(d, tr.is_lafan)
    return s if s.get("envs", 0) >= tr.MIN_LAFAN_FAST else tr.read_stats(d, tr.is_lafan, fast=False)


def fast_success(d: dict) -> float:
    u = [p for p in d["per_clip"] if p["ref_pelvis_speed"] >= tr.FAST]
    return float(np.mean([p["success"] for p in u])) if u else float("nan")


def _tennis(p: dict) -> bool:
    return "subject" not in p["clip"] and not p["clip"].startswith(("fwfast_", "footwork_"))


def tennis_stats(d: dict) -> dict:
    units = [k for k, p in enumerate(d["per_clip"]) if _tennis(p)]
    pu = [d["per_clip"][k] for k in units]
    envs = [e for e in d["per_env"] if e["unit"] in set(units)]
    return {"r_mpkpe": float(np.mean([p["r_mpkpe"] for p in pu])), "ee": float(np.mean([p["ee_pos_error"] for p in pu])),
            "disp_err_p50": float(np.median([abs(e["disp_robot"] - e["disp_ref"]) for e in envs]))}


def strokes(d: dict) -> dict:
    return {s: d["by_stroke"][s]["success"] for s in STROKES if s in d["by_stroke"]}


def lafan_success(d: dict) -> dict:
    return {k: d["by_source"].get(k) for k in ("lafan", "lafan_mirror")}


def kill(fw_c: dict, fw_p: dict, tl_c: dict, tl_p: dict, d_lafan_min: float = KILL_D_LAFAN,
         lafan_succ_drop: float | None = None) -> tuple[str, list[str]]:
    a, ap, l, lp = tr.read_stats(fw_c), tr.read_stats(fw_p), lafan_stats(tl_c), lafan_stats(tl_p)
    lines = []
    if not all(s.get("instrument_ok") for s in (a, ap, l, lp)):
        return "INSTRUMENT", ["instrument check failed on a travel read"]
    sc, sp = strokes(tl_c), strokes(tl_p)
    worst = min(sc[s] - sp[s] for s in sc)
    fall_c = max(fw_c["fall_rate"], tl_c["fall_rate"])
    fall_p = max(fw_p["fall_rate"], tl_p["fall_rate"], 0.005)
    checks = [("D_fw", a["D"], a["D"] >= KILL_D_FW), ("D_lafan", l["D"], l["D"] >= d_lafan_min),
              ("fw FAST success", fast_success(fw_c), fast_success(fw_c) >= KILL_FAST_SUCC),
              ("worst stroke - parent", worst, worst >= -KILL_STROKE),
              ("S_fw - S_parent", a["S"] - ap["S"], a["S"] - ap["S"] <= KILL_SLIP),
              ("falls / parent", fall_c / fall_p, fall_c <= KILL_FALLS * fall_p)]
    if lafan_succ_drop is not None:
        for k in ("lafan", "lafan_mirror"):
            dv = lafan_success(tl_c)[k] - lafan_success(tl_p)[k]
            checks.append((f"{k} success - parent", dv, dv >= -lafan_succ_drop))
    for name, v, ok in checks:
        lines.append(f"{name} {v:.3f} -> {'ok' if ok else 'KILL'}")
    return ("CONTINUE" if all(ok for _, _, ok in checks) else "KILL"), lines


def endpoint(fw_c: dict, fw_p: dict, tl_c: list[dict], tl_p: list[dict], ho: dict | None = None) -> tuple[str, list[str]]:
    a, ap = tr.read_stats(fw_c), tr.read_stats(fw_p)
    h = tr.read_stats(ho) if ho is not None else None
    lc = [lafan_stats(d) for d in tl_c]
    lp = [lafan_stats(d) for d in tl_p]
    if not all(s.get("instrument_ok") for s in [a, ap] + lc + lp + ([h] if h else [])):
        return "INSTRUMENT", ["instrument check failed on a travel read"]
    d_lafan = float(np.mean([s["D"] for s in lc]))
    sc = {s: np.mean([strokes(d)[s] for d in tl_c]) for s in STROKES}
    sp = {s: np.mean([strokes(d)[s] for d in tl_p]) for s in STROKES}
    lsc = {k: np.mean([lafan_success(d)[k] for d in tl_c]) for k in ("lafan", "lafan_mirror")}
    lsp = {k: np.mean([lafan_success(d)[k] for d in tl_p]) for k in ("lafan", "lafan_mirror")}
    tc = [tennis_stats(d) for d in tl_c]
    tp = [tennis_stats(d) for d in tl_p]
    rm_c, rm_p = np.mean([t["r_mpkpe"] for t in tc]), np.mean([t["r_mpkpe"] for t in tp])
    ee_c, ee_p = np.mean([t["ee"] for t in tc]), np.mean([t["ee"] for t in tp])
    disp = np.mean([t["disp_err_p50"] for t in tc])
    travel = [("D_fw >= 0.90", a["D"], a["D"] >= OK), ("D_lafan >= 0.90", d_lafan, d_lafan >= OK),
              ("D_fw <= 1.10", a["D"], a["D"] <= D_MAX)]
    if h is not None:
        travel += [("D_fwHO >= 0.90", h["D"], h["D"] >= OK), ("D_fwHO <= 1.10", h["D"], h["D"] <= D_MAX)]
    other = [("fw FAST success", fast_success(fw_c), fast_success(fw_c) >= FAST_SUCC),
             ("tennis r_mpkpe - parent", rm_c - rm_p, rm_c - rm_p <= RMPKPE),
             *[(f"stroke {s} - parent", sc[s] - sp[s], sc[s] - sp[s] >= -STROKE) for s in STROKES],
             *[(f"{k} success - parent", lsc[k] - lsp[k], lsc[k] - lsp[k] >= -STROKE) for k in lsc],
             ("S_fw - S_parent", a["S"] - ap["S"], a["S"] - ap["S"] <= SLIP),
             ("tennis |disp err| p50", disp, disp <= DISP_TENNIS),
             ("tennis ee error - parent", ee_c - ee_p, ee_c - ee_p <= EE)]
    lines = [f"{n} {v:.3f} -> {'ok' if ok else 'FAIL'}" for n, v, ok in travel + other]
    if d_lafan < OK:
        return "H0F-FAIL", lines
    if all(ok for _, _, ok in travel):
        return ("H0F-PASS" if all(ok for _, _, ok in other) else "H0F-RETENTION"), lines
    return "H0F-PARTIAL", lines
