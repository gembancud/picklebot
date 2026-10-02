"""Paired A/B aiming summary from two stage2_eval.py runs on identical feeds (same seed),
one with target forced to A and one to B.

assignment gain = 1/2 [ (P(land in A | target A) - P(land in A | target B))
                      + (P(land in B | target B) - P(land in B | target A)) ]
per feed (all feeds, misses count as not landing in either). The 95 % interval is a normal
approximation treating the conditions as independent proportions (conservative for paired feeds).

Usage: python scripts/aim_gain.py EVAL_A.json EVAL_B.json
"""

import json
import math
import sys

a, b = (json.load(open(p)) for p in sys.argv[1:3])
na, nb = a["episodes"], b["episodes"]
inA_A, inB_A = a["contact_diagnostics"]["landings_in_A"] / na, a["contact_diagnostics"]["landings_in_B"] / na
inA_B, inB_B = b["contact_diagnostics"]["landings_in_A"] / nb, b["contact_diagnostics"]["landings_in_B"] / nb
gain = 0.5 * ((inA_A - inA_B) + (inB_B - inB_A))
var = 0.25 * (inA_A * (1 - inA_A) / na + inA_B * (1 - inA_B) / nb + inB_B * (1 - inB_B) / nb + inB_A * (1 - inB_A) / na)
se = math.sqrt(var)
out = {"feeds_A": na, "feeds_B": nb,
       "hit_rate_target_A": round(a["contact_diagnostics"]["target_hits"] / na, 4),
       "hit_rate_target_B": round(b["contact_diagnostics"]["target_hits"] / nb, 4),
       "land_in_A": {"target_A": round(inA_A, 4), "target_B": round(inA_B, 4)},
       "land_in_B": {"target_A": round(inB_A, 4), "target_B": round(inB_B, 4)},
       "legal_return": {"target_A": a["legal_return_rate"], "target_B": b["legal_return_rate"]},
       "assignment_gain": round(gain, 4), "assignment_gain_ci95": [round(gain - 1.96 * se, 4), round(gain + 1.96 * se, 4)]}
print(json.dumps(out, indent=1))
