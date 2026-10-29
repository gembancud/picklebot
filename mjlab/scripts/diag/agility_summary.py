"""Agility screen summary (docs/research/footwork-route-2026-10-29.md section 6): per-arm, per-sector deadline arrival
(DA), untimed arrival, falls, peak speed and residual saturation from the training-log counters, the ball-side
direction split, and the pre-registered PASS / FAIL route (picklebot_mj/agility_rule.py), every line with its sign and
threshold. Source tags: A0 and the ball-side arm [train-diag], A / F / B [train-log].

Windows: A0 (learning rate 0) and the ball-side arm use the second half of their logged steps; A, F and B use their
last 1/8 (about iterations 350-400 of 400) as "at 400", and their first 1/8 is printed for reference.

--gates (D-172, the second screen, scripts/diag/agility_screen2.sh): the rule is applied behind the validity gates
(agility_rule.route_gated): A0 outside 10 <= DA(FR) <= 90 or below 90 % untimed arrival in any sector prints
"VOID: A0 outside validity gates" and no route; F with a censored share above 10 % voids any route that needs F.
Without the flag the output is the first screen's, unchanged.

Usage: python scripts/diag/agility_summary.py [--prefix results/agility] [--json results/agility-summary.json] [--gates]
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from picklebot_mj import agility_rule as ar  # noqa: E402

END = (0.875, 1.0)
START = (0.0, 0.125)
HALF = (0.5, 1.0)


def fmt(x, pct=True):
    if x is None:
        return "  n/a"
    return f"{100 * x:5.1f}" if pct else f"{x:5.2f}"


def table(tag: str, st: dict) -> None:
    print(f"{tag}: sector            issued resolved  DA %  untimed %  falls %  peak p50/p90 m/s  sat %  censored")
    for s in st["sectors"]:
        print(f"  {s['sector']} {s['name']:<14} {s['issued']:7d} {s['resolved']:8d} {fmt(s['da'])} {fmt(s['untimed']):>9} "
              f"{fmt(s['falls']):>8}   {fmt(s['peak_p50'], False)}/{fmt(s['peak_p90'], False)}      {fmt(s['sat_share'])} {s['censored']:8d}")
    print(f"  LB (2,3,4): DA {fmt(st['da_LB'])}  untimed {fmt(st['untimed_LB'])}  falls {fmt(st['falls_LB'])}  "
          f"sat {fmt(st['sat_share_LB'])}")
    print(f"  FR (0,6,7): DA {fmt(st['da_FR'])}  untimed {fmt(st['untimed_FR'])}  falls {fmt(st['falls_FR'])}  "
          f"sat {fmt(st['sat_share_FR'])}")
    print(f"  lowest untimed arrival over sectors: {fmt(st['untimed_min'])}")


def load(prefix: str, tag: str):
    p = f"{prefix}-{tag}.jsonl"
    if not os.path.exists(p):
        return None
    rows = [r for r in ar.read_rows(p)]
    return rows or None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prefix", default="results/agility")
    ap.add_argument("--json", default="results/agility-summary.json")
    ap.add_argument("--gates", action="store_true", help="apply the D-172 validity gates (second screen)")
    args = ap.parse_args()
    out = {"arms": {}}
    arms = {}
    for tag, win, src in (("A0", HALF, "train-diag"), ("A", END, "train-log"), ("F", END, "train-log"),
                          ("B", END, "train-log")):
        rows = load(args.prefix, tag)
        if rows is None or not any("move" in r for r in rows):
            print(f"{tag}: not run")
            continue
        rows = [r for r in rows if "move" in r]
        st = ar.arm_stats(ar.window(rows, "move", *win))
        arms[tag] = st
        out["arms"][tag] = {"window": win, "source": src, "last_step": rows[-1]["step"], **st}
        table(f"{tag} [{src}] window {win[0]:.3f}-{win[1]:.3f} of {rows[-1]['step']} env steps", st)
        if tag != "A0":
            s0 = ar.arm_stats(ar.window(rows, "move", *START))
            out["arms"][tag]["start"] = s0
            print(f"  {tag} first 1/8: DA(LB) {fmt(s0['da_LB'])}  DA(FR) {fmt(s0['da_FR'])}")
        print()
    rows = load(args.prefix, "BALL")
    ball = None
    if rows is not None and any("dir" in r for r in rows):
        rows = [r for r in rows if "dir" in r]
        ball = ar.ball_side(ar.window(rows, "dir", *HALF))
        out["ball_side"] = ball
        print("BALL [train-diag] feeder balls by direction (second half):")
        for dn, d in ball["directions"].items():
            print(f"  {dn:<8} feeds {d['feeds']:6d}  legal {fmt(d['legal'])}  contact {fmt(d['contact'])}  onset p50/p90 "
                  f"{fmt(d['onset_p50_s'], False)}/{fmt(d['onset_p90_s'], False)} s  never {fmt(d['onset_never_share'])}  "
                  f"sat {fmt(d['sat_share'])}  peak mean {fmt(d['peak_mean'], False)} m/s")
        print("\n".join(ball["lines"]))
        print()
    else:
        print("BALL: not run\n")
    if "A0" not in arms:
        print("ROUTE: none (A0 not run)")
        return
    rule = ar.route_gated if args.gates else ar.route
    r = rule(arms["A0"], arms.get("A"), arms.get("F"), arms.get("B"))
    out["route"] = r
    if args.gates:
        out["gates"] = True
    print("Pre-registered rule (section 6)" + (" behind the D-172 validity gates:" if args.gates else ":"))
    print("\n".join(r["lines"]))
    print(f"route: {r['route']}  (B triggered: {r['b_triggered']})")
    if args.json:
        with open(args.json, "w") as f:
            json.dump(out, f, indent=1)


if __name__ == "__main__":
    main()
