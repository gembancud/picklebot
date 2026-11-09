"""D-252: the call-and-set target's lines (mjlab/results/footwork-target.md), from CallSetDrill's counters (pure python).

Headline: pass share over judged calls (falls count as failures; censored calls are out), Wilson 95 % interval; the
target needs pass >= 0.80, Wilson low >= 0.78, every call type >= 0.70 and at least MIN_REPS judged reps. Reported: SET /
READY / REACH shares, the pace ladder, start time, per type / side / early, the reversed share.
"""
from __future__ import annotations

import math

TARGET, TARGET_LOW, TYPE_FLOOR, MIN_REPS, MIN_CHAINS = 0.80, 0.78, 0.70, 4000, 600
CALL_TYPES = ("wide_forehand", "wide_backhand", "deep", "short")


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return float("nan"), float("nan")
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return c - h, c + h


def _sum(c: dict, key: str, cells) -> int:
    return sum(c[key][i] for i in cells)


def type_cells(t: int) -> list[int]:
    return [t * 4 + j for j in range(4)]


def read(c: dict) -> dict:
    """Summary numbers from one or more pooled counter dicts (CallSetDrill.counters)."""
    allc = range(len(c["judged"]))
    n, k = _sum(c, "judged", allc), _sum(c, "passed", allc)
    lo, hi = wilson(k, n)
    out = {"judged": n, "passed": k, "pass": k / n if n else float("nan"), "wilson": (lo, hi),
           "issued": _sum(c, "issued", allc), "censored": _sum(c, "censored", allc), "fell": _sum(c, "fell", allc),
           "chains": c["chains"]}
    for key in ("set", "ready", "reach"):
        out[key] = _sum(c, key, allc) / n if n else float("nan")
    out["types"] = {}
    for t, name in enumerate(CALL_TYPES):
        cells = type_cells(t)
        nt, kt = _sum(c, "judged", cells), _sum(c, "passed", cells)
        out["types"][name] = {"judged": nt, "pass": kt / nt if nt else float("nan")}
    for name, cells in (("forehand", [i for i in allc if (i // 2) % 2 == 0]), ("backhand", [i for i in allc if (i // 2) % 2 == 1]),
                        ("normal", [i for i in allc if i % 2 == 0]), ("early", [i for i in allc if i % 2 == 1])):
        nt, kt = _sum(c, "judged", cells), _sum(c, "passed", cells)
        out[name] = {"judged": nt, "pass": kt / nt if nt else float("nan")}
    ln = sum(c["ladder_n"])
    out["ladder"] = {p: (sum(row) / ln if ln else float("nan")) for p, row in zip(c["meta"]["paces"], c["ladder"])}
    out["ladder_n"] = ln
    sn = _sum(c, "start_n", allc)
    out["start_s"] = sum(c["start_sum"]) / sn if sn else float("nan")
    out["reversed"] = _sum(c, "reversed", allc) / max(out["issued"], 1)
    out["early_share"] = out["early"]["judged"] / n if n else float("nan")
    if "diag" in c:  # reported: the parts of SET / READY, the pelvis at the stance spot, means at T
        out["diag"] = {k: sum(v) / n if n else float("nan") for k, v in c["diag"].items()}
        out["diag_mean"] = {k: sum(v) / n if n else float("nan") for k, v in c["diag_sum"].items()}
    return out


def pool(counters: list[dict]) -> dict:
    keys = [k for k in counters[0] if k not in ("meta", "ladder", "chains", "diag", "diag_sum")]
    out = {k: [sum(x) for x in zip(*(c[k] for c in counters))] for k in keys}
    for d in ("diag", "diag_sum"):
        if d in counters[0]:
            out[d] = {k: [sum(x) for x in zip(*(c[d][k] for c in counters))] for k in counters[0][d]}
    out["ladder"] = [[sum(x) for x in zip(*(c["ladder"][i] for c in counters))] for i in range(len(counters[0]["ladder"]))]
    out["chains"] = [sum(x) for x in zip(*(c["chains"] for c in counters))]
    out["meta"] = counters[0]["meta"]
    return out


def target_lines(r: dict) -> tuple[bool, list[str]]:
    lo = r["wilson"][0]
    worst = min(v["pass"] for v in r["types"].values())
    ok_n = r["judged"] >= MIN_REPS and r["chains"][0] >= MIN_CHAINS
    ok = ok_n and r["pass"] >= TARGET and lo >= TARGET_LOW and worst >= TYPE_FLOOR
    lines = [f"CALL-AND-SET: pass {r['pass']:.4f} (Wilson {lo:.3f}-{r['wilson'][1]:.3f}) on {r['judged']} judged calls "
             f"({r['chains'][0]} chains; >= {MIN_REPS} / {MIN_CHAINS}); target >= {TARGET} with low >= {TARGET_LOW}",
             "per call type: " + ", ".join(f"{k} {v['pass']:.3f} (n {v['judged']})" for k, v in r["types"].items())
             + f" (each >= {TYPE_FLOOR})",
             f"(reported) SET {r['set']:.3f}, READY {r['ready']:.3f}, REACH {r['reach']:.3f}; falls {r['fell']}, censored "
             f"{r['censored']}; start {r['start_s']:.2f} s; reversed {r['reversed']:.3f}; early share {r['early_share']:.3f}",
             "(reported) pace ladder: " + ", ".join(f"{p} m/s {v:.3f}" for p, v in r["ladder"].items()) + f" (n {r['ladder_n']})",
             f"(reported) forehand {r['forehand']['pass']:.3f}, backhand {r['backhand']['pass']:.3f}, normal "
             f"{r['normal']['pass']:.3f}, early {r['early']['pass']:.3f}",
             f"TARGET-LINES {'MET' if ok else 'NOT MET'}"]
    if "diag" in r:
        dg, dm = r["diag"], r["diag_mean"]
        lines.insert(-1, "(reported) at T: " + ", ".join(f"{k} {v:.3f}" for k, v in dg.items())
                     + f"; means: pelvis-to-spot {dm['d_s']:.2f} m, paddle fwd {dm['p_fwd']:.2f} m, toward side "
                     f"{dm['p_side']:.2f} m, height {dm['p_z']:.2f} m")
    return ok, lines
