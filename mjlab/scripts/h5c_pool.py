"""Pool several court-drill evaluations per zone x family cell (D-086 final-evaluation rule: 4+ seeds per cell).

Usage: python scripts/h5c_pool.py OUT.json IN1.json IN2.json ...
Writes pooled per-cell episodes / legal returns with Wilson 95 % intervals, the pooled main metric, and the cells
below 75 % (or unresolved under 30 episodes).
"""
import json
import math
import sys


def wilson(k, n, z=1.96):
    if n == 0:
        return [0.0, 0.0]
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(c - h, 4), round(c + h, 4)]


out, ins = sys.argv[1], sys.argv[2:]
cells, tot_ep, tot_ret = {}, 0, 0
for f in ins:
    d = json.load(open(f))
    tot_ep += d["episodes"]
    tot_ret += d["legal_returns"]
    for k, v in d.get("per_zone_family", {}).items():
        c = cells.setdefault(k, [0, 0])
        c[0] += v["episodes"]
        c[1] += round(v["legal_return"] * v["episodes"])
pooled = {k: {"episodes": n, "legal_return": round(r / max(n, 1), 4), "ci95": wilson(r, n)} for k, (n, r) in cells.items()}
fail = {k: v["legal_return"] for k, v in pooled.items() if v["episodes"] >= 30 and v["legal_return"] < 0.75}
thin = [k for k, v in pooled.items() if v["episodes"] < 30]
res = {"inputs": ins, "main_metric": round(tot_ret / max(tot_ep, 1), 4), "main_ci95": wilson(tot_ret, tot_ep),
       "episodes": tot_ep, "cells": pooled, "cells_pass": len(pooled) - len(fail) - len(thin), "cells_total": len(pooled),
       "cells_below_75": fail, "cells_unresolved": thin}
json.dump(res, open(out, "w"), indent=1)
print(f"pooled main {res['main_metric']} {res['main_ci95']}; cells pass {res['cells_pass']}/{res['cells_total']}")
