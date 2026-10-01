"""Tune feed ranges with the analytic ball alone (no robot).

For each candidate FeedCfg, sample feeds and simulate. Report the fraction that
bounce exactly once before the contact plane x = ROBOT_X + 0.2 (in front of the
pelvis), and the height and lateral offset there. Target: height 0.55-1.15 m
(forehand strike zone from the Stage 2 envelope).
Usage: python scripts/tune_feed.py
"""

from __future__ import annotations

import itertools

import torch

from picklebot_mj.ball_sim import BallSim, BallState
from picklebot_mj.tasks.return_stand import ROBOT_START, BallPhysicsAction, FeedCfg

PLANE_X = ROBOT_START[0] + 0.2


class _FakeTerm:
    """Reuse BallPhysicsAction._feed/_u without an env."""
    def __init__(self, feed, n, device="cpu"):
        self.cfg = type("C", (), {"feed": feed})()
        self.device = device
        self.gen = torch.Generator(device=device).manual_seed(0)
        z = torch.zeros(n, 3)
        self.ball = BallState(z.clone(), z.clone(), z.clone())

    _u = BallPhysicsAction._u
    _feed = BallPhysicsAction._feed


def evaluate(feed: FeedCfg, n=2048):
    t = _FakeTerm(feed, n)
    t._feed(torch.arange(n))
    s, sim = t.ball, BallSim()
    bounces = torch.zeros(n, dtype=torch.long)
    h = torch.full((n,), float("nan"))
    lat = torch.full((n,), float("nan"))
    for _ in range(int(2.5 / 0.005)):
        prev = s.pos[:, 0].clone()
        s, ev = sim.step(s, 0.005, 1)
        before = torch.isnan(h)
        bounces += (ev.court_contact & before).long()
        cross = before & (prev > PLANE_X) & (s.pos[:, 0] <= PLANE_X)
        h = torch.where(cross, s.pos[:, 2], h)
        lat = torch.where(cross, s.pos[:, 1] - ROBOT_START[1], lat)
    ok = (bounces == 1) & ~torch.isnan(h)
    good = ok & (h >= 0.55) & (h <= 1.15)
    return {"one_bounce": float(ok.float().mean()), "in_zone": float(good.float().mean()),
            "h_p10": float(h[ok].quantile(0.1)) if ok.any() else None,
            "h_p50": float(h[ok].median()) if ok.any() else None,
            "h_p90": float(h[ok].quantile(0.9)) if ok.any() else None,
            "lat_min": float(lat[ok].min()) if ok.any() else None, "lat_max": float(lat[ok].max()) if ok.any() else None}


if __name__ == "__main__":
    print("current", FeedCfg(), evaluate(FeedCfg()))
    best = []
    for bx, ft, z0 in itertools.product(
            [(-4.6, -4.2), (-4.4, -4.0), (-4.2, -3.8), (-4.0, -3.6)],
            [(0.8, 0.95), (0.9, 1.05), (1.0, 1.15)],
            [(0.9, 1.3), (1.2, 1.6)]):
        f = FeedCfg(bounce_x=bx, flight_time=ft, start_z=z0)
        r = evaluate(f, n=1024)
        best.append((r["in_zone"], bx, ft, z0, r))
    best.sort(key=lambda b: -b[0])
    for b in best[:6]:
        print(f"in_zone={b[0]:.3f} bounce_x={b[1]} flight_time={b[2]} start_z={b[3]} {b[4]}")
