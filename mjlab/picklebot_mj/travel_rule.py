"""Travel check (D-184, panel round 53, 5 of 5 for "check first"): does the motion prior cover the ground its reference
covers? Read from scripts/motion/tracking_eval.py's per-env travel instrument (per_env: net pelvis displacement, robot
and reference, at 1 s and at the window end; stance slip; foot friction).

Per read: FAST envs = envs of units whose reference pelvis speed >= FAST (1.0 m/s, as D-183) with a reference
displacement >= MIN_REF_M. D = median over FAST envs of disp_robot / disp_ref; D1 the same at 1 s (reference >= 0.25 m);
TR = sum disp_robot / sum disp_ref with a cluster (unit) bootstrap 95 % interval; S = median stance slip; D_hi = D
over envs with foot friction >= HI_FRICTION.
Instrument check (experiment design): |TR - median per-unit speed ratio| <= 0.05, else INSTRUMENT.
Routing (thresholds: the panel median of the five proposals; 0.90 is D-183's own "expresses" floor):
  INSTRUMENT  if either footwork-fast read fails the instrument check -> report, re-ask the panel;
  CONTACT     if D_H0 < 0.80 and S_H0 > 0.15 (amass_g1_import SKATE_MAX) and D_H0_hi >= 0.90 -> fix contact first;
  TRAVEL-OK   if D_H0 >= 0.90 and D_lat >= 0.90 -> route (a) (selection);
  DECODER-GAP if D_H0 >= 0.90 and D_lat < 0.80 -> decoder-only re-distil;
  TRAVEL-GAP  if D_H0 < 0.80 -> route D, sub-route by the control (H0 on its own LAFAN1 training windows):
              D_lafan >= 0.90 -> COVERAGE (fine-tune H0 with footwork-fast added, objective unchanged),
              else OBJECTIVE (the objective must reward travel; which change is panel round 54's);
  MIXED       otherwise -> re-ask the panel.
"""

from __future__ import annotations

import numpy as np

FAST, MIN_REF_M, MIN_REF_1S_M = 1.0, 0.5, 0.25
OK, GAP, SKATE_MAX, HI_FRICTION, INSTR_TOL = 0.90, 0.80, 0.15, 0.6, 0.05
BOOT, BOOT_SEED, MIN_LAFAN_FAST = 1000, 0, 30


def _fast_units(d: dict, select=None) -> set[int]:
    return {k for k, u in enumerate(d["per_clip"]) if u["ref_pelvis_speed"] >= FAST and (select is None or select(u))}


def read_stats(d: dict, select=None, fast: bool = True) -> dict:
    """Travel statistics of one tracking_eval JSON. select(per_clip entry) -> bool restricts the units (e.g. LAFAN)."""
    units = _fast_units(d, select) if fast else {k for k, u in enumerate(d["per_clip"]) if select is None or select(u)}
    envs = [e for e in d["per_env"] if e["unit"] in units and e["disp_ref"] >= MIN_REF_M]
    if not envs:
        return {"envs": 0}
    r = np.array([e["disp_robot"] / e["disp_ref"] for e in envs])
    e1 = [e for e in envs if e["disp_ref_1s"] == e["disp_ref_1s"] and e["disp_ref_1s"] >= MIN_REF_1S_M]
    r1 = np.array([e["disp_robot_1s"] / e["disp_ref_1s"] for e in e1]) if e1 else np.array([np.nan])
    rob, ref = np.array([e["disp_robot"] for e in envs]), np.array([e["disp_ref"] for e in envs])
    uid = np.array([e["unit"] for e in envs])
    uu = np.unique(uid)
    rng = np.random.default_rng(BOOT_SEED)
    idx = {u: np.where(uid == u)[0] for u in uu}
    boots = []
    for _ in range(BOOT):
        pick = np.concatenate([idx[u] for u in rng.choice(uu, size=len(uu), replace=True)])
        boots.append(rob[pick].sum() / ref[pick].sum())
    pu = [d["per_clip"][k] for k in units]
    vel = float(np.median([u["pelvis_speed"] / u["ref_pelvis_speed"] for u in pu])) if pu else None
    fr = np.array([e["foot_friction"] for e in envs])
    hi = r[fr >= HI_FRICTION] if np.isfinite(fr).all() else np.array([])
    tr = float(rob.sum() / ref.sum())
    return {"envs": len(envs), "units": len(uu), "D": float(np.median(r)), "D1": float(np.nanmedian(r1)), "TR": tr,
            "TR_ci95": [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))],
            "vel_ratio_median": vel, "instrument_ok": vel is not None and abs(tr - vel) <= INSTR_TOL,
            "S": float(np.median([e["stance_slip_mps"] for e in envs])),
            "D_hi": float(np.median(hi)) if len(hi) else None, "hi_envs": int(len(hi))}


def is_lafan(u: dict) -> bool:
    return "subject" in u["clip"]


def route(h0: dict, lat: dict, lafan: dict | None) -> tuple[str, str | None, list[str]]:
    """h0 / lat: read_stats of the footwork-fast reads; lafan: read_stats of H0 on its LAFAN1 windows."""
    lines = []
    if not (h0.get("instrument_ok") and lat.get("instrument_ok")):
        return "INSTRUMENT", None, [f"instrument check failed: H0 {h0.get('TR')} vs {h0.get('vel_ratio_median')}, "
                                    f"latent {lat.get('TR')} vs {lat.get('vel_ratio_median')}"]
    dh, dl = h0["D"], lat["D"]
    lines.append(f"D_H0 {dh:.3f}, D_lat {dl:.3f}, S_H0 {h0['S']:.3f}, D_H0_hi {h0['D_hi']}")
    if dh < GAP and h0["S"] > SKATE_MAX and h0["D_hi"] is not None and h0["D_hi"] >= OK:
        return "CONTACT", None, lines
    if dh >= OK and dl >= OK:
        return "TRAVEL-OK", None, lines
    if dh >= OK and dl < GAP:
        return "DECODER-GAP", None, lines
    if dh < GAP:
        sub = None
        if lafan and lafan.get("envs"):
            sub = "COVERAGE" if lafan["D"] >= OK else "OBJECTIVE"
            lines.append(f"control D_lafan {lafan['D']:.3f} over {lafan['envs']} envs -> {sub}")
        return "TRAVEL-GAP", sub, lines
    return "MIXED", None, lines
