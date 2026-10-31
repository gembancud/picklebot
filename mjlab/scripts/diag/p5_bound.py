"""D-189: a CPU-only upper bound on open-rally P(5+) from removing late left / back feeder-ball arrivals (experiment
design, D-188 / round 58). A MODEL, not a measurement: it assumes P(5+) scales with the feeder ball's legal rate and
that nothing else about the rally changes. It covers the feeder ball only (no existing log records direction for
handed balls).

  F      = feeder-ball legal over all directions: sum_dir feeds x legal / sum feeds   (the *-early-dir.json read)
  P5     = pairs p_len_ge_5_with_open                                                 (the *-early-pairs.json read)
  B_LB   = P5 x F' / F with left and back set to legal 1.0 (the most generous case)
  B_LBf  = P5 x F'' / F with left and back set to forward's legal
  B_max  = P5 / F (every feeder ball returned)
Line (D-188, unchanged): B_LB >= 0.50 -> footwork can plausibly lift P(5+) to about half; reported against it.
Usage: python scripts/diag/p5_bound.py
"""

import json

PAIRS = {"22b model_30200": ("results/rally-22b-early-dir.json", "results/rally-22b-early-pairs.json"),
         "23 model_31400": ("results/rally-23-early-dir.json", "results/rally-23-early-pairs.json")}
LINE = 0.50


def p5(pairs_json: dict) -> float:
    for k in ("pairs", "summary"):
        if isinstance(pairs_json.get(k), dict) and "p_len_ge_5_with_open" in pairs_json[k]:
            return float(pairs_json[k]["p_len_ge_5_with_open"])
    return float(pairs_json["p_len_ge_5_with_open"])


def bound(dirs: dict, p: float) -> dict:
    n = sum(v["feeds"] for v in dirs.values())
    F = sum(v["feeds"] * v["legal"] for v in dirs.values()) / n
    fl = lambda lb: sum(v["feeds"] * (lb if k in ("left", "back") else v["legal"]) for k, v in dirs.items()) / n  # noqa: E731
    return {"F": F, "P5": p, "B_LB": p * fl(1.0) / F, "B_LBf": p * fl(dirs["forward"]["legal"]) / F, "B_max": p / F}


if __name__ == "__main__":
    out = {}
    for name, (dj, pj) in PAIRS.items():
        b = bound(json.load(open(dj))["directions"], p5(json.load(open(pj))))
        out[name] = b
        print(f"{name}: " + ", ".join(f"{k} {v:.3f}" for k, v in b.items())
              + f" -> B_LB {'>=' if b['B_LB'] >= LINE else '<'} {LINE}")
    json.dump(out, open("results/p5-bound.json", "w"), indent=1)
