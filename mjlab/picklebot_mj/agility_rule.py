"""Agility screen (docs/research/footwork-route-2026-10-29.md section 6): rates from the training-log counters and the
pre-registered PASS / FAIL routing rule. Pure Python (no torch, no mjlab), so the summary step and its tests run
anywhere.

Counter rows are the cumulative JSON lines written by `picklebot_mj.tasks.agility` (PICKLEBOT_AGILITY_LOG):
    {"step": env steps, "move": {issued, arrived, deadline, timed_out, fell, censored, time_sum, peak_sum, peak_hist,
                                 sat_steps, move_steps}, "dir": {...}}
A window is the difference of two rows. Per sector, a spot is *resolved* when it ends in an arrival (any time within
the untimed limit), an untimed time-out or a fall; spots cut by the episode's time limit are censored and left out.
    DA = arrivals before the deadline / resolved, untimed = arrivals / resolved, falls = falls / resolved.
Group rates are the mean of their sectors' rates (sectors are drawn uniformly; the box-wall reversal makes counts
unequal, and the mean keeps every direction's weight equal).
"""

from __future__ import annotations

import json

N_SECTORS = 8
SECTOR_NAMES = ("forward", "forward-left", "left", "back-left", "back", "back-right", "right", "forward-right")
LB = (2, 3, 4)  # left, back-left, back
FR = (0, 6, 7)  # forward, right, forward-right
DIRS = ("forward", "left", "back", "right")  # feeder-ball direction classes (scripts/diag/feeder_speed_envelope.py)
SPEED_BIN = 0.1  # m/s, peak pelvis speed histogram

# Pre-registered thresholds (section 6), in points of deadline arrival unless stated.
D0_MIN = 10.0  # rule 1: a direction-specific deficit at the start
GAIN_MIN = 15.0  # rule 2: DA(LB) gain within 400 iterations
GAP_FRAC = 0.5  # rule 2: remaining deficit at most 0.5 x D0
F_MARGIN = 10.0  # rules 3-4: F's DA(LB) >= F's DA(FR) - 10
B_SAT_MIN = 0.25  # B only if A fails and A's LB saturation share >= 25 %
BALL_LB_MAX, BALL_FR_MIN = 0.55, 0.80  # ball-side line: train left + back legal <= 55 %, forward + right >= 80 %


def read_rows(path: str) -> list[dict]:
    """Cumulative rows, one per logged env step (duplicates dropped)."""
    rows, seen = [], set()
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            if r["step"] not in seen:
                seen.add(r["step"])
                rows.append(r)
    rows.sort(key=lambda r: r["step"])
    return rows


CONSTANT_KEYS = ("onset_bin_s",)  # settings carried in the rows, not counters


def _sub(b, a):
    if isinstance(b, dict):
        return {k: (b[k] if k in CONSTANT_KEYS else _sub(b[k], a[k])) for k in b}
    if isinstance(b, list):
        return [_sub(x, y) for x, y in zip(b, a)]
    return b - a


def diff(a: dict | None, b: dict, key: str) -> dict:
    """Counters accumulated between rows a and b (a None: since the start)."""
    if a is None:
        return b[key]
    return _sub(b[key], a[key])


def window(rows: list[dict], key: str, lo: float, hi: float = 1.0) -> dict:
    """Counters between the rows at fractions lo and hi of the logged steps (0.5-1.0: the second half)."""
    assert rows, "no rows logged"
    s0, s1 = rows[0]["step"], rows[-1]["step"]
    pick = lambda f: min(rows, key=lambda r: abs(r["step"] - (s0 + f * (s1 - s0))))
    a = None if lo <= 0 else pick(lo)
    b = pick(hi)
    if a is not None and a["step"] >= b["step"]:
        a = None
    return diff(a, b, key)


def _q(hist: list[int], p: float, bin_w: float):
    n = sum(hist)
    if n == 0:
        return None
    acc = 0
    for i, c in enumerate(hist):
        acc += c
        if acc >= p * n:
            return round((i + 0.5) * bin_w, 3)
    return round((len(hist) - 0.5) * bin_w, 3)


def sector_rates(c: dict) -> list[dict]:
    out = []
    for i in range(N_SECTORS):
        res = c["arrived"][i] + c["timed_out"][i] + c["fell"][i]
        fin = c["arrived"][i] + c["timed_out"][i]
        r = lambda k: (c[k][i] / res) if res else None
        out.append({
            "sector": i, "name": SECTOR_NAMES[i], "issued": c["issued"][i], "resolved": res,
            "censored": c["censored"][i],
            "da": r("deadline"), "untimed": r("arrived"), "falls": r("fell"),
            "mean_time_s": (c["time_sum"][i] / c["arrived"][i]) if c["arrived"][i] else None,
            "peak_mean": (c["peak_sum"][i] / fin) if fin else None,
            "peak_p50": _q(c["peak_hist"][i], 0.5, SPEED_BIN), "peak_p90": _q(c["peak_hist"][i], 0.9, SPEED_BIN),
            "sat_share": (c["sat_steps"][i] / c["move_steps"][i]) if c["move_steps"][i] else None,
        })
    return out


def group(rates: list[dict], key: str, sectors) -> float | None:
    v = [rates[i][key] for i in sectors]
    if any(x is None for x in v):
        return None
    return sum(v) / len(v)


def arm_stats(c: dict) -> dict:
    s = sector_rates(c)
    return {"sectors": s, **{f"{k}_{g}": group(s, k, sec) for k in ("da", "untimed", "falls", "sat_share")
                             for g, sec in (("LB", LB), ("FR", FR))},
            "untimed_min": min((x["untimed"] for x in s if x["untimed"] is not None), default=None)}


def _pt(x):
    return None if x is None else round(100.0 * x, 6)  # points; rounded so a boundary value compares as written


def _line(name: str, value, op: str, thr, unit: str = " pt") -> tuple[bool, str]:
    if value is None or thr is None:
        return False, f"  {name}: n/a {op} {thr} -> FAIL (missing data)"
    ok = value >= thr if op == ">=" else value <= thr if op == "<=" else value < thr
    return ok, f"  {name}: {value:+.2f}{unit} {op} {thr:+.2f}{unit} -> {'PASS' if ok else 'FAIL'}"


def rule2(a0: dict, arm: dict, d0: float, tag: str) -> tuple[bool, list[str]]:
    """Rule 2 for an arm at its endpoint: DA(LB) >= A0's DA(LB) + 15 and DA(FR) - DA(LB) <= 0.5 x D0."""
    lb0, lb, fr = _pt(a0["da_LB"]), _pt(arm["da_LB"]), _pt(arm["da_FR"])
    ok1, l1 = _line(f"{tag} DA(LB) at end", lb, ">=", None if lb0 is None else lb0 + GAIN_MIN)
    gap = None if lb is None or fr is None else fr - lb
    ok2, l2 = _line(f"{tag} deficit DA(FR) - DA(LB) at end", gap, "<=", GAP_FRAC * d0)
    return ok1 and ok2, [l1 + f"  (A0 DA(LB) {lb0:.2f} + {GAIN_MIN:.0f})" if lb0 is not None else l1,
                         l2 + f"  ({GAP_FRAC} x D0 {d0:.2f})"]


def route(a0: dict, a: dict | None, f: dict | None, b: dict | None = None) -> dict:
    """The section 6 rule. Arms are arm_stats() dicts (A0: its window; A, F, B: their endpoint windows). Returns the
    printed lines, the route key and whether B is triggered."""
    lines = []
    d0 = None if a0["da_FR"] is None or a0["da_LB"] is None else _pt(a0["da_FR"]) - _pt(a0["da_LB"])
    ok, l = _line("rule 1: D0 = DA(FR) - DA(LB) at A0", d0, ">=", D0_MIN)
    lines.append(l)
    if d0 is None:
        return {"lines": lines + ["ROUTE: none (A0 has no data)"], "route": "none", "b_triggered": False, "d0": None}
    if not ok:
        lines.append("ROUTE 1: D0 < 10: no direction-specific motor deficit under time pressure. Footwork routes (a)-(e) "
                     "rejected; next the reading route (f2, the e4 re-test), then (f1).")
        return {"lines": lines, "route": "reading", "b_triggered": False, "d0": d0}
    if a is None:
        return {"lines": lines + ["ROUTE: pending (arm A not run)"], "route": "pending", "b_triggered": False, "d0": d0}
    a_ok, l2 = rule2(a0, a, d0, "rule 2: A")
    lines += l2
    if a_ok:
        lines.append("ROUTE 2: PASS: the composite can learn fast left / back stepping. Run route E (section 7).")
        return {"lines": lines, "route": "E", "b_triggered": False, "d0": d0}
    sat = a["sat_share_LB"]
    b_trig, lb_sat = _line("B trigger: A's LB saturation share (A fails rule 2)", sat, ">=", B_SAT_MIN, unit="")
    lines.append(lb_sat)
    if f is None:
        return {"lines": lines + ["ROUTE: pending (arm F not run)"], "route": "pending", "b_triggered": b_trig, "d0": d0}
    f_lb, f_fr = _pt(f["da_LB"]), _pt(f["da_FR"])
    f_ok, l3 = _line("rule 3/4: F DA(LB) at end", f_lb, ">=", None if f_fr is None else f_fr - F_MARGIN)
    lines.append(l3 + (f"  (F DA(FR) {f_fr:.2f} - {F_MARGIN:.0f})" if f_fr is not None else ""))
    if f_ok:
        if b_trig and b is None:
            lines.append("ROUTE 3 (pending B): the body can and the residual cannot; B is triggered: run arm B (lam_r 3, "
                         "exact init), then re-run the summary.")
            return {"lines": lines, "route": "pending-B", "b_triggered": True, "d0": d0}
        if b_trig and b is not None:
            b_ok, lb = rule2(a0, b, d0, "rule 3: B")
            lines += lb
            if b_ok:
                lines.append("ROUTE 3b: B passes rule 2: range binds. Run route (b), lam_r 3 with the exact init.")
                return {"lines": lines, "route": "b", "b_triggered": True, "d0": d0}
        lines.append("ROUTE 3: the body can and the residual cannot. Route C: extend F into the fast teacher, then the "
                     "floor check.")
        return {"lines": lines, "route": "C", "b_triggered": b_trig, "d0": d0}
    lines.append("ROUTE 4: F also fails: at these deadlines the limit is the body or the time budget, not the controller. "
                 "Lower the v_req band to U(1.0, 1.6), report again, run no footwork lever; earlier commitment (the "
                 "reading route) is the lever left.")
    return {"lines": lines, "route": "lower-band", "b_triggered": b_trig, "d0": d0}


# Validity gates (D-172, the second screen; opt-in through route_gated: route() above is unchanged). The rule's thresholds
# (D0_MIN, GAIN_MIN, GAP_FRAC, F_MARGIN, B_SAT_MIN) are not changed.
A0_DA_FR_MIN, A0_DA_FR_MAX = 10.0, 90.0  # points: A0's DA(FR) must leave room to see a deficit and a gain
A0_UNTIMED_MIN = 0.90  # A0's untimed arrival, in every sector
F_CENSORED_MAX = 0.10  # F's censored share (censored / issued, sectors pooled)
ROUTES_NEEDING_F = ("pending-B", "b", "C", "lower-band")  # route() keys reached only through F's rule 3/4 line


def a0_gate(a0: dict) -> tuple[bool, list[str]]:
    """A0 is VALID only if 10 <= DA(FR) <= 90 points and untimed arrival >= 90 % in every sector."""
    fr = _pt(a0["da_FR"])
    ok1, l1 = _line("gate A0: DA(FR)", fr, ">=", A0_DA_FR_MIN)
    ok2, l2 = _line("gate A0: DA(FR)", fr, "<=", A0_DA_FR_MAX)
    un = [x["untimed"] for x in a0["sectors"]]
    lo = None if not un or any(x is None for x in un) else min(un)
    ok3, l3 = _line("gate A0: lowest sector untimed arrival", lo, ">=", A0_UNTIMED_MIN, unit="")
    return ok1 and ok2 and ok3, [l1, l2, l3]


def f_gate(f: dict) -> tuple[bool, str]:
    """F is VALID only if its censored share (censored / issued, all sectors) is <= 10 %."""
    issued = sum(x["issued"] for x in f["sectors"])
    share = (sum(x["censored"] for x in f["sectors"]) / issued) if issued else None
    return _line("gate F: censored share (censored / issued)", share, "<=", F_CENSORED_MAX, unit="")


def route_gated(a0: dict, a: dict | None, f: dict | None, b: dict | None = None) -> dict:
    """route() behind the D-172 validity gates. A0 outside its gates: VOID, no route. F outside its gate: any route that
    needs F is VOID (F invalid); routes that do not need F (reading, E, pending A / F) are routed as before."""
    a0_ok, lines = a0_gate(a0)
    if not a0_ok:
        return {"lines": lines + ["VOID: A0 outside validity gates"], "route": "void", "b_triggered": False, "d0": None,
                "a0_valid": False, "f_valid": None}
    f_ok = None
    if f is not None:
        f_ok, lf = f_gate(f)
        lines.append(lf)
    r = route(a0, a, f, b)
    out = {**r, "lines": lines + r["lines"], "a0_valid": True, "f_valid": f_ok}
    if f_ok is False and r["route"] in ROUTES_NEEDING_F:
        out.update(lines=out["lines"] + [f"VOID (F invalid): route {r['route']!r} needs F, and F is outside its "
                                         "validity gate"], route="void-F", b_triggered=False)
    return out


def ball_side(c: dict) -> dict:
    """Ball-side logging (feeder balls in training): legal, contact, onset latency and saturation by direction, and the
    route E ball-side line (left + back legal <= 55 %, forward + right >= 80 %)."""
    out = {"directions": {}}
    bw = c["onset_bin_s"]
    for j, dn in enumerate(DIRS):
        n = c["feeds"][j]
        h = c["onset_hist"][j]
        out["directions"][dn] = {
            "feeds": n, "legal": c["legal"][j] / n if n else None, "contact": c["contact"][j] / n if n else None,
            "onset_p50_s": onset_quantile(h, 0.5, bw), "onset_p90_s": onset_quantile(h, 0.9, bw),
            "onset_never_share": h[-1] / sum(h) if sum(h) else None,
            "sat_share": c["sat_steps"][j] / c["approach_steps"][j] if c["approach_steps"][j] else None,
            "peak_mean": c["peak_sum"][j] / n if n else None}
    pool = lambda js, k: (sum(c[k][j] for j in js) / sum(c["feeds"][j] for j in js)) if sum(c["feeds"][j] for j in js) else None
    lb, fr = pool((1, 2), "legal"), pool((0, 3), "legal")
    ok1, l1 = _line("ball-side: train left + back feeder legal", None if lb is None else 100 * lb, "<=", 100 * BALL_LB_MAX)
    ok2, l2 = _line("ball-side: train forward + right feeder legal", None if fr is None else 100 * fr, ">=", 100 * BALL_FR_MIN)
    sat = lambda js: (sum(c["sat_steps"][j] for j in js) / sum(c["approach_steps"][j] for j in js)) \
        if sum(c["approach_steps"][j] for j in js) else None
    s_lb, s_fr = sat((1, 2)), sat((0, 3))
    ok3, l3 = _line("(b) premise: left + back approach saturation share", s_lb, ">=",
                    None if s_fr is None else max(2 * s_fr, B_SAT_MIN), unit="")
    out.update(lb_legal=lb, fr_legal=fr, premise=ok1 and ok2, sat_lb=s_lb, sat_fr=s_fr, range_binds=ok3,
               lines=[l1, l2, "  route E ball-side premise: " + ("PASS" if ok1 and ok2 else "FAIL"),
                      l3 + (f"  (max(2 x forward + right {s_fr:.3f}, {B_SAT_MIN}); reported, not a route line)"
                            if s_fr is not None else "")])
    return out


def onset_quantile(hist: list[int], p: float, bin_w: float):
    """Quantile of the onset times that happened (the last bin, 'never', excluded)."""
    return _q(hist[:-1], p, bin_w)
