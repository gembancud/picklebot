"""Footwork specialist step-1 rule (D-179; scripts/diag/footwork_fw1.sh). Each arm's measure read is routed by
bodyspeed_rule.route unchanged (VOID / BODY-OK / BODY-LIMIT / MIXED; thresholds 1.8 / 1.3 m/s, arrival 90 %, falls
4.157 per 1,000 env-s, censored 10 %). The arm carried forward (step 2's teacher) is chosen by:
  1. verdict rank BODY-OK > MIXED > BODY-LIMIT > VOID;
  2. then the higher min(left, back, right) sustained speed;
  3. within 0.1 m/s on (2), the style arm (human-like gait is what step 2 records into the motion prior).
"""

from __future__ import annotations

from picklebot_mj import bodyspeed_rule as bsr

RANK = {"BODY-OK": 3, "MIXED": 2, "BODY-LIMIT": 1, "VOID": 0}
TIE_SPEED = 0.1
STYLE_ARM = "SA"


def lrb_min(route: dict) -> float | None:
    s = {x["name"]: x["sustained_p50"] for x in route["sectors"]}
    v = [s[k] for k in ("left", "back", "right")]
    return None if any(x is None for x in v) else min(v)


def select(routes: dict[str, dict]) -> tuple[str | None, list[str]]:
    """routes: arm -> bodyspeed_rule.route result. Returns (arm, explanation lines); None if every arm is VOID."""
    live = {a: r for a, r in routes.items() if r["verdict"] != "VOID"}
    lines = [f"{a}: {r['verdict']}, min(L, B, R) sustained {lrb_min(r)}" for a, r in routes.items()]
    if not live:
        return None, lines + ["every arm VOID: no teacher carried forward"]
    top = max(RANK[r["verdict"]] for r in live.values())
    cand = {a: r for a, r in live.items() if RANK[r["verdict"]] == top}
    sp = {a: (lrb_min(r) or 0.0) for a, r in cand.items()}
    best = max(sp.values())
    near = [a for a, v in sp.items() if v >= best - TIE_SPEED - 1e-9]
    pick = STYLE_ARM if STYLE_ARM in near else max(near, key=lambda a: sp[a])
    return pick, lines + [f"carried forward: {pick} (rank {top}, speeds {sp}, tie band {TIE_SPEED} m/s -> style arm)"]


route = bsr.route
