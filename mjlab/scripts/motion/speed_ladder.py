"""Supervised speed ladder (D-175, panel round 49): where does tracking fail as footwork gets faster?

On-disk 100STYLE G1 retargets (artifacts/motion/style100-g1: Neutral FW / BW / SW, accepted; Neutral SR, on disk but
rejected by the D-101 retarget rule) are time-scaled by csv_to_npz_local.py --input-fps (30 fps source played at
30 * k fps -> k times faster; cadence rises by k too). SW and SR are also mirrored left <-> right
(mirror_g1_csv.py). All rungs go into one motion file (new directory artifacts/motion/speed-ladder/), clip names
suffixed _x<k>, every clip source 1, so tracking_eval.py --per-stroke scores 4 s windows (task
Picklebot-Tracking-SpeedLadder-G1). Each window is binned by its reference pelvis speed (window p50 of the horizontal
speed) and its heading-frame direction (the sector most of its moving frames fall in).

Pure helpers (CPU-tested in tests/test_speed_ladder.py) plus two subcommands (picklebot-mj venv, from mjlab/):
    python scripts/motion/speed_ladder.py merge OUT.npz PART_x1.npz:1 PART_x1.5.npz:1.5 ...
    python scripts/motion/speed_ladder.py summarize --motion NPZ --h0 H0.json --lat LAT.json --barrier BAR.json
        --json results/speed-ladder.json --txt results/speed-ladder-summary.txt [--seeds ...]
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

SPEED_BINS = ((0.0, 1.0, "<=1.0"), (1.0, 1.5, "1.0-1.5"), (1.5, 2.0, "1.5-2.0"), (2.0, float("inf"), ">=2.0"))
DIRECTIONS = ("forward", "left", "back", "right")
MOVING_MPS = 0.1  # frames slower than this carry no direction

# D-175 coded rule (thresholds as registered; not to be changed).
FAST_MPS = 2.0
VOID_X1 = 0.95
SEL_LAT, SEL_COV5 = 0.90, 0.80
DEC_LAT, DEC_H0 = 0.70, 0.90
BODY_H0 = 0.70


def speed_bin(v: float) -> str:
    """D-175 bins: <= 1.0, (1.0, 1.5), [1.5, 2.0), >= 2.0 m/s."""
    if v <= 1.0:
        return SPEED_BINS[0][2]
    if v < 1.5:
        return SPEED_BINS[1][2]
    return SPEED_BINS[2][2] if v < FAST_MPS else SPEED_BINS[3][2]


def yaw_of(quat_wxyz: np.ndarray) -> np.ndarray:
    w, x, y, z = (quat_wxyz[..., i] for i in range(4))
    return np.arctan2(2.0 * (w * z + x * y), 1.0 - 2.0 * (y * y + z * z))


def heading_velocity(lin_vel_w: np.ndarray, quat_wxyz: np.ndarray) -> np.ndarray:
    """World horizontal velocity [T, 3+] -> heading (yaw) frame [T, 2]: x forward, y left."""
    yaw = yaw_of(quat_wxyz)
    c, s = np.cos(yaw), np.sin(yaw)
    vx, vy = lin_vel_w[..., 0], lin_vel_w[..., 1]
    return np.stack([c * vx + s * vy, -s * vx + c * vy], axis=-1)


def sector(vh: np.ndarray) -> np.ndarray:
    """Heading-frame velocity [T, 2] -> sector index into DIRECTIONS (forward |a| < 45, left 45-135, back, right)."""
    a = np.degrees(np.arctan2(vh[..., 1], vh[..., 0]))
    out = np.full(a.shape, 2)  # back
    out[(a >= -45) & (a < 45)] = 0
    out[(a >= 45) & (a < 135)] = 1
    out[(a >= -135) & (a < -45)] = 3
    return out


def window_stats(lin_vel_w: np.ndarray, quat_wxyz: np.ndarray) -> dict:
    """Reference pelvis stats over one window's frames: speed p50 / p90, dominant direction and its frame share."""
    sp = np.linalg.norm(lin_vel_w[:, :2], axis=-1)
    vh = heading_velocity(lin_vel_w, quat_wxyz)
    moving = sp > MOVING_MPS
    sec = sector(vh)[moving]
    counts = np.bincount(sec, minlength=4) if len(sec) else np.zeros(4, dtype=int)
    d = int(np.argmax(counts))
    return {"ref_p50": float(np.median(sp)), "ref_p90": float(np.quantile(sp, 0.9)),
            "direction": DIRECTIONS[d], "purity": float(counts[d] / max(1, counts.sum())),
            "bin": speed_bin(float(np.median(sp)))}


def parse_clip(name: str) -> tuple[str, float]:
    """'Neutral_SW_train_mirror_x2.5' -> ('SW_train_mirror', 2.5)."""
    base, k = name.rsplit("_x", 1)
    return base.split("_", 1)[1], float(k)


def gait_of(clip: str) -> str:
    return clip.split("_", 1)[0]  # 'SW_train_mirror' -> 'SW'


def _mean(xs):
    xs = [x for x in xs if x is not None and not np.isnan(x)]
    return float(np.mean(xs)) if xs else float("nan")


def coded_rule(h0_x1: float, lat_x1: float, h0_fast: float, lat_fast: float, cov5_fast: float,
               n_fast: int) -> tuple[list[str], str]:
    """D-175 coded rule, in its registered order. Returns (printed lines, verdict)."""
    def line(name, v, op, thr):
        met = (v < thr) if op == "<" else (v >= thr)
        return f"  {name:<44} {v * 100:6.1f} %  {op:>2} {thr * 100:5.1f} %  -> {'met' if met else 'not met'}", met

    lines = [f"  left/back windows at ref p50 >= {FAST_MPS:.1f} m/s: {n_fast}"]
    l1, v1 = line("VOID: H0 success at x1", h0_x1, "<", VOID_X1)
    l2, v2 = line("VOID: latent-07 success at x1", lat_x1, "<", VOID_X1)
    lines += [l1, l2]
    if n_fast == 0:
        return lines + ["  no left/back windows at the fast speed: the rule cannot be applied"], "UNDEFINED"
    l3, s1 = line("SELECTION: latent-07 success (fast L/B)", lat_fast, ">=", SEL_LAT)
    l4, s2 = line("SELECTION: lam-5 coverage (fast L/B)", cov5_fast, ">=", SEL_COV5)
    l5, d1 = line("DECODER: latent-07 success (fast L/B)", lat_fast, "<", DEC_LAT)
    l6, d2 = line("DECODER: H0 success (fast L/B)", h0_fast, ">=", DEC_H0)
    l7, b1 = line("BODY?: H0 success (fast L/B)", h0_fast, "<", BODY_H0)
    lines += [l3, l4, l5, l6, l7]
    if v1 or v2:
        return lines, "VOID"
    if s1 and s2:
        return lines, "SELECTION"
    if d1 and d2:
        return lines, "DECODER"
    if b1:
        return lines, "BODY?"
    return lines, "OTHER"


def rows_from_evals(motion: dict, pelvis: int, h0: dict, lat: dict, bar: dict) -> list[dict]:
    """One row per window: reference stats from the motion file plus the three evaluations' per-window numbers."""
    key = lambda p: (p["clip"], p["start"])  # noqa: E731
    L, B = {key(p): p for p in lat["per_clip"]}, {key(p): p for p in bar["per_clip"]}
    rows = []
    for p in h0["per_clip"]:
        a, b = p["start"], p["end"]
        clip, k = parse_clip(p["clip"])
        st = window_stats(motion["body_lin_vel_w"][a:b, pelvis], motion["body_quat_w"][a:b, pelvis])
        q, r = L[key(p)], B[key(p)]
        rows.append({"clip": clip, "gait": gait_of(clip), "factor": k, "start": a, "end": b, **st,
                     "accepted": gait_of(clip) != "SR",
                     "h0_success": p["success"], "lat_success": q["success"],
                     "h0_speed": p.get("pelvis_speed"), "lat_speed": q.get("pelvis_speed"),
                     "h0_ref_speed_played": p.get("ref_pelvis_speed"), "lat_ref_speed_played": q.get("ref_pelvis_speed"),
                     "bar_success": r["success"], "cov2": r["in2"], "cov5": r["in5"]})
    return rows


def rule_inputs(rows: list[dict]) -> dict:
    x1 = [r for r in rows if r["factor"] == 1.0]
    fast = [r for r in rows if r["direction"] in ("left", "back") and r["ref_p50"] >= FAST_MPS]
    return {"h0_x1": _mean([r["h0_success"] for r in x1]), "lat_x1": _mean([r["lat_success"] for r in x1]),
            "h0_fast": _mean([r["h0_success"] for r in fast]), "lat_fast": _mean([r["lat_success"] for r in fast]),
            "cov5_fast": _mean([r["cov5"] for r in fast]), "cov2_fast": _mean([r["cov2"] for r in fast]),
            "n_fast": len(fast), "n_x1": len(x1)}


# ---------------------------------------------------------------------------------------------------------------------
def cmd_merge(a):
    fields = ("joint_pos", "joint_vel", "body_pos_w", "body_quat_w", "body_lin_vel_w", "body_ang_vel_w")
    parts, starts, names, off = [], [], [], 0
    for spec in a.parts:
        path, k = spec.rsplit(":", 1)
        d = np.load(path)
        assert float(d["fps"][0]) == 50.0
        parts.append(d)
        starts.append(d["clip_starts"] + off)
        names += [f"{n}_x{k}" for n in d["clip_names"]]
        off += len(d["joint_pos"])
    out = {f: np.concatenate([p[f] for p in parts]) for f in fields}
    out.update(fps=parts[0]["fps"], clip_starts=np.concatenate(starts), clip_names=np.array(names),
               clip_source=np.ones(len(names), dtype=int))  # all source 1: per-stroke mode scores fixed windows
    assert not Path(a.out).exists(), f"{a.out} exists: never overwrite"
    np.savez(a.out, **out)
    print(f"{len(names)} clips, {off} frames -> {a.out}")


def _fmt(v, pct=True):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "   -  "
    return f"{v * 100:5.1f}%" if pct else f"{v:5.2f}"


def cmd_summarize(a):
    motion = dict(np.load(a.motion))
    h0, lat, bar = (json.load(open(p)) for p in (a.h0, a.lat, a.barrier))
    rows = rows_from_evals(motion, a.pelvis_index, h0, lat, bar)
    # Per clip x speed (whole-clip reference speed from the motion file; window means of the evaluation numbers).
    names = [str(s) for s in motion["clip_names"]]
    ends = np.r_[motion["clip_starts"][1:], len(motion["joint_pos"])]
    per_clip = []
    for i, n in enumerate(names):
        clip, k = parse_clip(n)
        s0, s1 = int(motion["clip_starts"][i]), int(ends[i])
        sp = np.linalg.norm(motion["body_lin_vel_w"][s0:s1, a.pelvis_index, :2], axis=-1)
        w = [r for r in rows if r["clip"] == clip and r["factor"] == k]
        per_clip.append({"clip": clip, "factor": k, "seconds": (s1 - s0) / 50.0, "windows": len(w),
                         "ref_p50": float(np.median(sp)), "ref_p90": float(np.quantile(sp, 0.9)),
                         **{q: _mean([r[q] for r in w]) for q in
                            ("h0_success", "lat_success", "h0_speed", "lat_speed", "h0_ref_speed_played", "cov2",
                             "cov5")}})
    per_clip.sort(key=lambda c: (c["clip"], c["factor"]))
    # Bins: direction x speed.
    bins = defaultdict(list)
    for r in rows:
        bins[(r["accepted"], r["direction"], r["bin"])].append(r)
    bin_rows = [{"accepted_only": acc, "direction": d, "bin": b, "windows": len(g),
                 **{q: _mean([r[q] for r in g]) for q in ("ref_p50", "h0_success", "lat_success", "h0_speed",
                                                          "lat_speed", "cov2", "cov5")}}
                for (acc, d, b), g in sorted(bins.items(), key=lambda x: (not x[0][0], DIRECTIONS.index(x[0][1]),
                                                                          [s[2] for s in SPEED_BINS].index(x[0][2])))]
    # The coded rule: primary = accepted retargets, every rung; sensitivities printed alongside.
    variants = {
        "primary (accepted FW/BW/SW + SW mirror, all rungs)": [r for r in rows if r["accepted"]],
        "sensitivity: + Neutral_SR (rejected retarget)": rows,
        "sensitivity: brief rungs x1-x2.5 only, accepted": [r for r in rows if r["accepted"] and r["factor"] <= 2.5],
    }
    rules = {}
    for name, rs in variants.items():
        inp = rule_inputs(rs)
        lines, verdict = coded_rule(inp["h0_x1"], inp["lat_x1"], inp["h0_fast"], inp["lat_fast"], inp["cov5_fast"],
                                    inp["n_fast"])
        rules[name] = {"inputs": inp, "lines": lines, "verdict": verdict}
    out = {"decision": "D-175", "motion": a.motion, "h0_checkpoint": h0["checkpoint"],
           "latent_checkpoint": lat["checkpoint"], "seeds": {"h0": h0["seed"], "latent": lat["seed"],
                                                             "barrier": bar["seed"]},
           "window_s": a.window_s, "speed_measure": "window p50 of reference pelvis horizontal speed",
           "direction_measure": "dominant heading-frame sector of reference pelvis velocity (moving frames)",
           "per_clip": per_clip, "bins": bin_rows, "rule": rules, "windows": rows}
    Path(a.json).write_text(json.dumps(out, indent=1))
    # Readable summary.
    L = ["Supervised speed ladder (D-175, panel round 49). Evaluation only; no training.",
         f"H0: {h0['checkpoint']} (seed {h0['seed']})",
         f"latent-07 encoder: {lat['checkpoint']} (tracking seed {lat['seed']}, barrier seed {bar['seed']})",
         f"Motion: {a.motion}; {a.window_s:.0f} s windows (tracking_eval.py --per-stroke), success = window reached "
         "without a tracking termination.",
         "Reference speed = horizontal pelvis speed of the reference; achieved = robot pelvis, mean over frames played.",
         "Coverage lamN = share of steps whose encoder latent is within N prior std of the prior mean in every dim.",
         "CAVEAT: time-warping a clip by k raises speed AND cadence (step frequency) by k; a fast rung is a fast-"
         "cadence walk, not a run. Failures at high k can reflect cadence or swing-leg speed, not ground speed.",
         "CAVEAT: Neutral_SR (sidestep run) is on disk but was rejected by the D-101 retarget rule (ankle roll at its"
         " limit in 33-45 % of frames, foot slide > 0.10 m/s); it is reported, and only in a sensitivity line.",
         "", "Per clip x speed (ref p50/p90 over the whole clip; other columns are window means):",
         f"{'clip':<18}{'xk':>5}{'win':>5}{'ref50':>7}{'ref90':>7}{'refPl':>7}{'achH0':>7}{'achLat':>7}"
         f"{'H0':>8}{'Lat07':>8}{'cov2':>8}{'cov5':>8}"]
    for c in per_clip:
        L.append(f"{c['clip']:<18}{c['factor']:>5.1f}{c['windows']:>5d}{c['ref_p50']:>7.2f}{c['ref_p90']:>7.2f}"
                 f"{_fmt(c['h0_ref_speed_played'], False):>7}{_fmt(c['h0_speed'], False):>7}"
                 f"{_fmt(c['lat_speed'], False):>7}{_fmt(c['h0_success']):>8}{_fmt(c['lat_success']):>8}"
                 f"{_fmt(c['cov2']):>8}{_fmt(c['cov5']):>8}")
    L += ["", "Windows by heading-frame direction x reference speed bin (window p50):",
          f"{'set':<10}{'dir':<9}{'bin':<9}{'win':>5}{'ref50':>7}{'achH0':>7}{'achLat':>7}{'H0':>8}{'Lat07':>8}"
          f"{'cov2':>8}{'cov5':>8}"]
    for b in bin_rows:
        L.append(f"{'accepted' if b['accepted_only'] else 'SR':<10}{b['direction']:<9}{b['bin']:<9}{b['windows']:>5d}"
                 f"{b['ref_p50']:>7.2f}{_fmt(b['h0_speed'], False):>7}{_fmt(b['lat_speed'], False):>7}"
                 f"{_fmt(b['h0_success']):>8}{_fmt(b['lat_success']):>8}{_fmt(b['cov2']):>8}{_fmt(b['cov5']):>8}")
    L += ["", "Coded rule (D-175): metric = success on left/back windows with reference p50 >= 2.0 m/s.",
          "Order: VOID (either checkpoint < 95 % at x1) > SELECTION (latent >= 90 % and lam-5 coverage >= 80 %) >"
          " DECODER (latent < 70 % and H0 >= 90 %) > BODY? (H0 < 70 %) > OTHER."]
    for name, r in rules.items():
        L += ["", f"[{name}]"] + r["lines"] + [f"  lam-2 coverage (fast L/B, reported): {_fmt(r['inputs']['cov2_fast'])}",
                                               f"  VERDICT: {r['verdict']}"]
    L += ["", f"VERDICT (primary): {rules[next(iter(rules))]['verdict']}"]
    Path(a.txt).write_text("\n".join(L) + "\n")
    print("\n".join(L))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("merge")
    m.add_argument("out")
    m.add_argument("parts", nargs="+", help="PATH:FACTOR")
    s = sub.add_parser("summarize")
    for f in ("motion", "h0", "lat", "barrier", "json", "txt"):
        s.add_argument(f"--{f}", required=True)
    s.add_argument("--pelvis-index", type=int, default=0)
    s.add_argument("--window-s", type=float, default=4.0)
    a = ap.parse_args()
    {"merge": cmd_merge, "summarize": cmd_summarize}[a.cmd](a)


if __name__ == "__main__":
    main()
