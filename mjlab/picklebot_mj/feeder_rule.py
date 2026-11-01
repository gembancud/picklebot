"""D-198 feeder-ball split rule (panel round 63; experiment design's lines). The rally target's first good shot is the
return of the feeder ball, so P(5+) <= feeder-ball legal (about 0.65 for every player); 76 % of feeder failures are
missed contacts, even on easy feeds. This read (scripts/diag/ballidx63.sh) asks why.

Arms (LR 0, ballidx52's overrides, pair courts, second half): C = the d1s3 child (dev 4220303), P = 22b model_30200
(dev 4220303, paired), C2 = the d1s3 child again (dev 4220304, the noise arm). On C, in the matched band (predicted
interception 0.75-1.5 m), every gap also exceeding 2 x its |C - C2| difference:
- FEED-STATE if k = 0 contact <= k >= 3 contact - 0.10, and a receiver-state variable at the feeder fire passes
  route_split (b) at k = 0 (worst-tercile failure >= 2 x the best);
- FEED-SHOT if k = 0 contact is within 0.05 of k >= 3 contact;
- FEED-OTHER otherwise (timing or perception of a ball that is not a robot's).
INVALID if any arm's config check fails or it has fewer than 800 feeder balls in the matched band.
"""

from __future__ import annotations

from picklebot_mj import ballidx_rule as br

MIN_BAND_BALLS = 800
STATE_GAP, SHOT_WITHIN, NOISE_X = 0.10, 0.05, 2.0
K3 = 2  # k bin "3+"


def _band_rows(base: int, band) -> list[int]:
    return [base * br.DIST_BINS + d for d in range(*band)]


def _sumrows(hist: list[list[int]], cells: list[int], band) -> int:
    return sum(hist[c][d] for c in cells for d in range(*band))


def feeder_stats(c: dict, g: int = 0, band=br.MATCHED_BAND) -> dict:
    from picklebot_mj.tasks.ball_index import SPLIT_VARS, STATE_VARS
    f = c["feeder"]
    cells = [g * br.N_DIRS + d for d in range(br.N_DIRS)]
    pred = cells[:4]
    balls = sum(f["balls"][i] for i in cells)
    bb = _sumrows(f["dist"], pred, band)
    out = {"balls": balls, "received": f["received"][g], "void": f["void"][g], "censored": f["censored"][g],
           "legal": round(sum(f["legal"][i] for i in cells) / balls, 4) if balls else None,
           "contact": round(sum(f["contact"][i] for i in cells) / balls, 4) if balls else None,
           "band_balls": bb,
           "band_contact": round(_sumrows(f["dist_contact"], pred, band) / bb, 4) if bb else None,
           "band_legal": round(_sumrows(f["dist_legal"], pred, band) / bb, 4) if bb else None, "vars": {}}
    rows = _band_rows(g, band)
    par = {name: (lo, w, nb) for name, lo, w, nb in SPLIT_VARS}
    for name in STATE_VARS:
        h = br._addv([f["split"][name][r] for r in rows])
        lg = br._addv([f["split_legal"][name][r] for r in rows])
        out["vars"][name] = br.var_stats(h, lg, *par[name])
    return out


def k3_band_contact(c: dict, g: int = 0, band=br.MATCHED_BAND) -> dict:
    cells = [br._cell(g, K3, d) for d in range(4)]
    bb = _sumrows(c["dist"], cells, band)
    return {"band_balls": bb, "band_contact": round(_sumrows(c["dist_contact"], cells, band) / bb, 4) if bb else None}


def route(c: dict, c2: dict, valid: bool = True) -> dict:
    """c, c2: the C and C2 arms' windowed counters."""
    from picklebot_mj.tasks.ball_index import STATE_VARS
    f, f2 = feeder_stats(c), feeder_stats(c2)
    k, k2 = k3_band_contact(c), k3_band_contact(c2)
    lines = []
    if not valid or min(f["band_balls"], f2["band_balls"]) < MIN_BAND_BALLS:
        lines.append(f"INVALID: config ok {valid}; feeder balls in the matched band C {f['band_balls']}, C2 {f2['band_balls']} "
                     f"(need >= {MIN_BAND_BALLS})")
        return {"verdict": "INVALID", "lines": lines, "C": f, "C2": f2, "k3": k, "k3_C2": k2}
    gap, gap2 = k["band_contact"] - f["band_contact"], k2["band_contact"] - f2["band_contact"]
    noise = NOISE_X * abs(gap - gap2)
    big = gap >= STATE_GAP - 1e-12 and gap > noise
    lines.append(f"contact (matched band): k>=3 {k['band_contact']:.4f} - k=0 {f['band_contact']:.4f} = {gap:+.4f} "
                 f"(C2 {gap2:+.4f}; noise 2 x |C - C2| = {noise:.4f}); >= {STATE_GAP} and > noise -> {'yes' if big else 'no'}")
    fired = []
    for name in STATE_VARS:
        v, v2 = f["vars"][name], f2["vars"][name]
        w, b = v["worst"], v["best"]
        ok = w is not None and b is not None and w >= br.RATIO * b - 1e-12
        if ok and v2["worst"] is not None and v2["best"] is not None:
            d, d2 = w - b, v2["worst"] - v2["best"]
            ok = d > NOISE_X * abs(d - d2)
        lines.append(f"state {name} (b) at k=0: worst-tercile failure {br._f(w)} >= 2 x best {br._f(b)}, spread above "
                     f"2 x |C - C2| -> {'PASS' if ok else 'FAIL'}")
        if ok:
            fired.append(name)
    within = abs(gap) <= SHOT_WITHIN + 1e-12
    v = "FEED-STATE" if (big and fired) else "FEED-SHOT" if within else "FEED-OTHER"
    lines.append(f"state variables fired: {fired}; |gap| <= {SHOT_WITHIN}: {within} -> {v}")
    return {"verdict": v, "lines": lines, "fired": fired, "C": f, "C2": f2, "k3": k, "k3_C2": k2}
