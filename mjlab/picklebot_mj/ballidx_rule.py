"""Ball-index diagnostic: summary and the pre-registered routing rule (scripts/diag/ballidx51.sh).

Input: windowed counters of picklebot_mj/tasks/ball_index.py (agility_rule.window(rows, "ballidx", 0.5)). Cells are
(group * 3 + k_bin) * 5 + direction; group 0 = pair courts (the read-like courts), k bins 1 / 2 / 3+, directions forward
/ left / back / right / none (no predicted interception).

Rule (pre-registered; failure = 1 - legal over counted balls; terciles by count over the k = 1 histogram's bins):
- PACE if k=1 incoming speed p50 >= (k>=3 p50) + 1.0 m/s AND k=1 failure in its top speed tercile >= 2 x its bottom
  tercile -> a pace ceiling on feeder-ball returns.
- REACH if k=1 distance-to-interception p50 >= (k>=3 p50) + 0.5 m AND k=1 failure in its top distance tercile >= 2 x its
  bottom tercile -> placement shaping of feeder returns toward the partner.
- DIRECTION if k=1 left + back share >= 2 x the k>=3 left + back share AND k=1 left + back failure >= 2 x k=1 forward +
  right failure -> footwork again (body-limited).
- otherwise OTHER. Several may fire: all are printed, ordered PACE, REACH, DIRECTION.
"""

from __future__ import annotations

N_KBINS, N_DIRS = 3, 5
K_NAMES = ("1", "2", "3+")
DIR_NAMES = ("forward", "left", "back", "right", "none")
SPEED_BIN, DIST_BIN = 0.5, 0.25
PACE_DP50, REACH_DP50, RATIO = 1.0, 0.5, 2.0


def _cell(g: int, k: int, d: int) -> int:
    return (g * N_KBINS + k) * N_DIRS + d


def _rate(a, b):
    return a / b if b else None


def _addv(rows):
    return [sum(x) for x in zip(*rows)] if rows else []


def quantile(hist: list[int], p: float, bin_w: float):
    """p-quantile of a histogram, linear within the bin (None if empty)."""
    n = sum(hist)
    if n == 0:
        return None
    acc, target = 0.0, p * n
    for i, c in enumerate(hist):
        if c and acc + c >= target:
            return round((i + (target - acc) / c) * bin_w, 4)
        acc += c
    return round(len(hist) * bin_w, 4)


def terciles(hist: list[int], legal: list[int]) -> dict:
    """Failure in the bottom and top terciles by count: the fewest lowest (highest) bins holding >= 1/3 of the balls."""
    n = sum(hist)
    out = {"n": n}
    if n == 0:
        return {**out, "bottom": None, "top": None}

    def take(order):
        bins, acc = [], 0
        for i in order:
            if acc >= n / 3:
                break
            bins.append(i)
            acc += hist[i]
        b = sum(hist[i] for i in bins)
        lg = sum(legal[i] for i in bins)
        return {"bins": [min(bins), max(bins)], "balls": b, "failure": round(1 - lg / b, 4) if b else None}

    out["bottom"] = take(range(len(hist)))
    out["top"] = take(range(len(hist) - 1, -1, -1))
    out["overlap"] = out["bottom"]["bins"][1] >= out["top"]["bins"][0]
    return out


def k_stats(c: dict, g: int, k: int) -> dict:
    """One (group, k bin): counts, rates, speed / distance quantiles, direction shares and legal by direction."""
    cells = [_cell(g, k, d) for d in range(N_DIRS)]
    pred = cells[:4]
    get = lambda key, cs: sum(c[key][i] for i in cs)  # noqa: E731
    balls, legal, contact = get("balls", cells), get("legal", cells), get("contact", cells)
    gk = g * N_KBINS + k
    sp = _addv([c["speed"][i] for i in cells])
    sp_l = _addv([c["speed_legal"][i] for i in cells])
    hs = _addv([c["hspeed"][i] for i in cells])
    di = _addv([c["dist"][i] for i in pred])  # predicted interceptions only
    di_l = _addv([c["dist_legal"][i] for i in pred])
    npred = get("balls", pred)
    dirs = {}
    for d, name in enumerate(DIR_NAMES):
        b, lg = c["balls"][cells[d]], c["legal"][cells[d]]
        dirs[name] = {"balls": b, "share": round(b / npred, 4) if (npred and d < 4) else None,
                      "share_all": round(b / balls, 4) if balls else None,
                      "legal": round(lg / b, 4) if b else None,
                      "contact": round(c["contact"][cells[d]] / b, 4) if b else None}
    lb_b = sum(c["balls"][cells[d]] for d in (1, 2))
    lb_l = sum(c["legal"][cells[d]] for d in (1, 2))
    fr_b = sum(c["balls"][cells[d]] for d in (0, 3))
    fr_l = sum(c["legal"][cells[d]] for d in (0, 3))
    return {
        "k": K_NAMES[k], "balls": balls, "received": c["received"][gk], "void": c["void"][gk],
        "censored": c["censored"][gk], "fell": get("fell", cells), "early": get("early", cells),
        "legal": round(legal / balls, 4) if balls else None, "contact": round(contact / balls, 4) if balls else None,
        "legal_given_contact": round(legal / contact, 4) if contact else None,
        "speed_p50": quantile(sp, 0.5, SPEED_BIN), "speed_p90": quantile(sp, 0.9, SPEED_BIN),
        "hspeed_p50": quantile(hs, 0.5, SPEED_BIN), "hspeed_mean": round(get("hspd_sum", cells) / balls, 4) if balls else None,
        "dist_p50": quantile(di, 0.5, DIST_BIN), "dist_p90": quantile(di, 0.9, DIST_BIN), "predicted": npred,
        "directions": dirs,
        "lb_share": round(lb_b / npred, 4) if npred else None, "lb_failure": round(1 - lb_l / lb_b, 4) if lb_b else None,
        "fr_failure": round(1 - fr_l / fr_b, 4) if fr_b else None,
        "speed_hist": sp, "speed_legal_hist": sp_l, "dist_hist": di, "dist_legal_hist": di_l,
        "speed_terciles": terciles(sp, sp_l), "dist_terciles": terciles(di, di_l),
    }


def failure_by_bin(hist: list[int], legal: list[int], bin_w: float, min_balls: int = 1) -> list[dict]:
    return [{"lo": round(i * bin_w, 3), "balls": b, "failure": round(1 - lg / b, 4)}
            for i, (b, lg) in enumerate(zip(hist, legal)) if b >= min_balls]


def summarize(c: dict, g: int = 0) -> dict:
    ks = [k_stats(c, g, k) for k in range(N_KBINS)]
    return {"group": g, "k": ks,
            "fail_by_speed": {"1": failure_by_bin(ks[0]["speed_hist"], ks[0]["speed_legal_hist"], SPEED_BIN),
                              "3+": failure_by_bin(ks[2]["speed_hist"], ks[2]["speed_legal_hist"], SPEED_BIN)},
            "fail_by_dist": {"1": failure_by_bin(ks[0]["dist_hist"], ks[0]["dist_legal_hist"], DIST_BIN),
                             "3+": failure_by_bin(ks[2]["dist_hist"], ks[2]["dist_legal_hist"], DIST_BIN)}}


def _f(x, nd=3):
    return "n/a" if x is None else f"{x:.{nd}f}"


def _ge(a, b):
    return a is not None and b is not None and a >= b - 1e-12


def route(s: dict) -> dict:
    """The coded rule on a summarize() result. Returns {"fired": [...], "verdict": str, "lines": [...]}."""
    k1, k3 = s["k"][0], s["k"][2]
    lines, fired = [], []

    def line(name, value, op, thr, unit):
        ok = _ge(value, thr)
        lines.append(f"{name}: {_f(value)}{unit} {op} {_f(thr)}{unit} -> {'PASS' if ok else 'FAIL'}")
        return ok

    thr = None if k3["speed_p50"] is None else k3["speed_p50"] + PACE_DP50
    a = line("PACE  (a) k=1 speed p50 vs k>=3 p50 + 1.0", k1["speed_p50"], ">=", thr, " m/s")
    st = k1["speed_terciles"]
    bot, top = (st["bottom"] or {}).get("failure"), (st["top"] or {}).get("failure")
    b = line("PACE  (b) k=1 failure, top speed tercile vs 2 x bottom", top, ">=", None if bot is None else RATIO * bot, "")
    if a and b:
        fired.append("PACE")
    thr = None if k3["dist_p50"] is None else k3["dist_p50"] + REACH_DP50
    a = line("REACH (a) k=1 distance p50 vs k>=3 p50 + 0.5", k1["dist_p50"], ">=", thr, " m")
    dt = k1["dist_terciles"]
    bot, top = (dt["bottom"] or {}).get("failure"), (dt["top"] or {}).get("failure")
    b = line("REACH (b) k=1 failure, top distance tercile vs 2 x bottom", top, ">=", None if bot is None else RATIO * bot, "")
    if a and b:
        fired.append("REACH")
    a = line("DIRECTION (a) k=1 left + back share vs 2 x k>=3 share", k1["lb_share"], ">=",
             None if k3["lb_share"] is None else RATIO * k3["lb_share"], "")
    b = line("DIRECTION (b) k=1 left + back failure vs 2 x k=1 forward + right failure", k1["lb_failure"], ">=",
             None if k1["fr_failure"] is None else RATIO * k1["fr_failure"], "")
    if a and b:
        fired.append("DIRECTION")
    return {"fired": fired, "verdict": " + ".join(fired) if fired else "OTHER", "lines": lines}
