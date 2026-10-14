"""Offline checks of the Stage 5C court-wide feeds (D-076): every family from every court zone, analytic ball only.

For each (family, zone): feeds are sampled with the task's own sampler, anchored at a pelvis spot in the zone
(back x = -5.8, mid x = -4.2, front x = -2.8; y = 0, and y = +-1.8 for the lateral families), and simulated.
Reported:
- in: the first bounce lands inside the robot's court (and, for volleys, behind the robot);
- hittable: the ball enters the hitting window, i.e. after its first bounce and before a second one at 0.35-1.2 m
  high, or for volley families before any bounce at 0.4-1.6 m high and no more than 0.5 m in front of the pelvis;
- travel p50/p95: horizontal distance from the pelvis to the nearest window point minus a 0.7 m arm reach;
- speed p95: travel / time to that point.

Usage: python scripts/tune_court_feeds.py [--n 1024] [--families drop,lob,...] [--json OUT]
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import torch

from picklebot_mj import court
from picklebot_mj.ball_sim import BallSim
from picklebot_mj.feeds import COURT_FAMILIES, COURT_ZONES, FAMILY_NAMES, VOLLEY_FAMILIES, only

spec = importlib.util.spec_from_file_location("tune_feed", Path(__file__).with_name("tune_feed.py"))
tf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tf)

ZONE_ANCHOR_X = {"back": -5.8, "mid": -4.2, "front": -2.8}
LATERAL = {"cross_forehand", "cross_backhand", "reach_forehand", "reach_backhand"}
HIT_Z, VOLLEY_Z, REACH_M = (0.35, 1.2), (0.4, 1.6), 0.7


def check(name: str, anchor, n: int, seed: int = 0):
    t = tf._FakeTerm(only(name), n, seed=seed)
    t.anchor_xy = anchor
    t._feed(torch.arange(n))
    s, sim = t.ball, BallSim()
    a = torch.tensor(anchor, dtype=torch.float32)
    volley = name in VOLLEY_FAMILIES
    bounces = torch.zeros(n, dtype=torch.long)
    land = torch.full((n, 2), float("nan"))
    best = torch.full((n,), float("inf"))
    t_best = torch.full((n,), float("nan"))
    dt = 0.005
    for i in range(int(3.0 / dt)):
        s, ev = sim.step(s, dt, 1)
        first = ev.court_contact & (bounces == 0)
        land = torch.where(first.unsqueeze(-1), s.pos[:, :2], land)
        bounces += ev.court_contact.long()
        z = s.pos[:, 2]
        if volley:
            window = (bounces == 0) & (z >= VOLLEY_Z[0]) & (z <= VOLLEY_Z[1]) & (s.pos[:, 0] <= a[0] + 0.5)
        else:
            window = (bounces == 1) & (z >= HIT_Z[0]) & (z <= HIT_Z[1])
        d = (s.pos[:, :2] - a).norm(dim=-1)
        better = window & (d < best)
        best = torch.where(better, d, best)
        t_best = torch.where(better, torch.full_like(d, (i + 1) * dt), t_best)
    ok = torch.isfinite(best)
    lands_in = (land[:, 0] > -court.HALF_LENGTH) & (land[:, 0] < 0) & (land[:, 1].abs() < court.HALF_WIDTH)
    if volley:
        lands_in = lands_in & (land[:, 0] < a[0])  # a missed volley bounces behind the robot
    travel = (best - REACH_M).clamp(min=0.0)
    q = lambda x, p: round(float(x[ok].quantile(p)), 2) if ok.any() else None
    return {"in": round(float(lands_in.float().mean()), 3), "hittable": round(float(ok.float().mean()), 3),
            "travel_p50": q(travel, 0.5), "travel_p95": q(travel, 0.95),
            "speed_p95": q(travel / t_best, 0.95)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=1024)
    ap.add_argument("--families", default=None, help="comma-separated (default: all families)")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    fams = a.families.split(",") if a.families else list(FAMILY_NAMES)
    out = {}
    for f in fams:
        ys = (-1.8, 0.0, 1.8) if f in LATERAL else (0.0,)
        for z in COURT_ZONES:
            for y in ys:
                r = check(f, (ZONE_ANCHOR_X[z], y), a.n)
                key = f"{f}@{z}" + (f"/y{y:+.1f}" if len(ys) > 1 else "")
                out[key] = r
                print(f"{key:28s} {r}", flush=True)
    if a.json:
        json.dump(out, open(a.json, "w"), indent=1)


if __name__ == "__main__":
    main()
