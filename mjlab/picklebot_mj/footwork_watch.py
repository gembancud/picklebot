"""Coded kill lines for footwork specialist runs (D-181, panel round 51), enforced while the run trains.

Round 51 found D-180's kill line was written in a script comment and checked by hand only. This watcher reads the
drill's cumulative counters (PICKLEBOT_AGILITY_LOG rows, one every 10 iterations) and the training log, and kills the
trainer the first time a line trips. Iterations are counted in this run (24 env steps per iteration) from its first logged row: the env step counter
continues from the parent checkpoint.
  K-unstable: falls > 8.314 per 1,000 env-s (2 x 4.157) pooled over the last 100 iterations, after iteration 100
              -> VOID-unstable;
  K-settle (D-180's line): training untimed arrival < 50 % pooled over a 100-iteration window starting at
              iteration >= 200 -> KILL-no-settle;
  K-speed:    training min(left, back, right) sustained p50 < 1.3 m/s over the same window -> KILL-speed-traded
              (a result, reported as such).
A NaN exit kills the run by itself (rsl_rl check_nan). Usage:
    python -m picklebot_mj.footwork_watch RUN_NAME COUNTERS.jsonl TRAIN.log OUT.json
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time

from picklebot_mj import agility_rule as ar
from picklebot_mj import bodyspeed_rule as bsr

STEPS_PER_IT = 24
WINDOW_IT = 100
SETTLE_FROM_IT, UNSTABLE_FROM_IT = 200, 100
SETTLE_MIN, SPEED_MIN, FALLS_MAX = 0.50, 1.3, 2 * 4.157
LRB = (2, 4, 6)


def _diff(a: dict, b: dict) -> dict:
    out = {}
    for k, v in b.items():
        if isinstance(v, list) and v and isinstance(v[0], list):
            out[k] = [[y - (a[k][i][j] if a else 0) for j, y in enumerate(r)] for i, r in enumerate(v)]
        elif isinstance(v, list):
            out[k] = [y - (a[k][i] if a else 0) for i, y in enumerate(v)]
    return out


def window_lines(rows: list[dict]) -> dict | None:
    """K-settle and K-speed on the latest complete 100-iteration window starting at iteration >= 200 (None: none yet)."""
    if not rows:
        return None
    end, base = rows[-1], rows[0]["step"]  # the env step counter continues from the parent checkpoint
    start_step = end["step"] - WINDOW_IT * STEPS_PER_IT
    if start_step - base < SETTLE_FROM_IT * STEPS_PER_IT:
        return None
    first = min(rows, key=lambda r: abs(r["step"] - start_step))
    c = _diff(first["move"], end["move"])
    fin = sum(c["arrived"]) + sum(c["timed_out"]) + sum(c["fell"])
    arrival = sum(c["arrived"]) / fin if fin else None
    sp = [bsr.quantile(c["best_hist"][i], 0.5, bsr.SPEED_BIN) for i in LRB]
    speed = None if any(x is None for x in sp) else min(sp)
    out = {"from_it": (first["step"] - base) // STEPS_PER_IT, "to_it": (end["step"] - base) // STEPS_PER_IT, "untimed_arrival": arrival,
           "lrb_sustained_min": speed, "kill": None}
    if arrival is not None and arrival < SETTLE_MIN:
        out["kill"] = "KILL-no-settle"
    elif speed is not None and speed < SPEED_MIN:
        out["kill"] = "KILL-speed-traded"
    return out


def falls_line(log_text: str, envs: int) -> dict | None:
    """K-unstable on the last 100 logged iterations, once past iteration 100."""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts", "diag"))
    from falls_by_length import falls_per_1000_env_s
    blocks = log_text.split("Learning iteration")
    if len(blocks) - 1 < UNSTABLE_FROM_IT + WINDOW_IT:
        return None
    with tempfile.NamedTemporaryFile("w", suffix=".log", delete=False) as f:
        f.write("Learning iteration".join(blocks[-WINDOW_IT:]))
    try:
        falls = falls_per_1000_env_s(f.name, envs=envs)[0]
    finally:
        os.unlink(f.name)
    return {"iterations": len(blocks) - 1, "falls_per_1000_env_s": falls,
            "kill": "VOID-unstable" if falls > FALLS_MAX else None}


def main(argv=None) -> int:
    run, counters, log, out = (argv or sys.argv[1:])[:4]
    envs = int(os.environ.get("PICKLEBOT_ENVS", "4096"))
    exit_json = os.path.join(os.path.dirname(log), f"{run}.exit.json")
    while not os.path.exists(exit_json):
        time.sleep(120)
        try:
            rows = ar.read_rows(counters)
            text = open(log, errors="ignore").read()
        except FileNotFoundError:
            continue
        checks = {"window": window_lines(rows), "falls": falls_line(text, envs)}
        kill = next((c["kill"] for c in checks.values() if c and c["kill"]), None)
        with open(out + ".last", "w") as f:
            json.dump(checks, f)
        if kill:
            json.dump({"run": run, "kill": kill, "checks": checks, "time": time.strftime("%Y-%m-%dT%H:%M:%S")},
                      open(out, "w"), indent=1)
            subprocess.run(["pkill", "-f", f"run-name {run} "], check=False)
            return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
