"""Offline checks of feed families with the analytic ball alone (no robot).

For each family: sample feeds with the task's own sampler, simulate, and report the
fraction that bounce exactly once before the contact plane x = ROBOT_X + 0.2 (in front
of the pelvis), plus height and lateral offset (from the pelvis) when crossing it.
Usage: python scripts/tune_feed.py [--families] [--n 2048]
"""

from __future__ import annotations

import argparse
import json

import torch

from picklebot_mj.ball_sim import BallSim, BallState
from picklebot_mj.feeds import FAMILIES, FAMILY_NAMES, FeedMix, only
from picklebot_mj.tasks.return_stand import ROBOT_START, BallPhysicsAction

PLANE_X = ROBOT_START[0] + 0.2


class _FakeTerm:
    """Reuse BallPhysicsAction's feed sampler without an env."""

    def __init__(self, mix: FeedMix, n: int, device="cpu", seed=0):
        self.device = device
        self.gen = torch.Generator(device=device).manual_seed(seed)
        z = torch.zeros(n, 3)
        self.ball = BallState(z.clone(), z.clone(), z.clone())
        self._mix = torch.tensor(mix.vector())
        self._ranges = {a: torch.tensor([getattr(FAMILIES[f], a) for f in FAMILY_NAMES])
                        for a in ("start_x", "start_z", "bounce_x", "lateral_y", "flight_time", "spin_y")}
        self.family = torch.zeros(n, dtype=torch.long)
        self.cfg = type("Cfg", (), {"target_mode": "random"})()
        self.gen_target = torch.Generator(device=device).manual_seed(seed + 1)
        self.target = torch.zeros(n, dtype=torch.long)

    _range = BallPhysicsAction._range
    _u = BallPhysicsAction._u
    _feed = BallPhysicsAction._feed


def evaluate(mix: FeedMix, n=2048, seed=0):
    t = _FakeTerm(mix, n, seed=seed)
    t._feed(torch.arange(n))
    s, sim = t.ball, BallSim()
    bounces = torch.zeros(n, dtype=torch.long)
    h = torch.full((n,), float("nan"))
    lat = torch.full((n,), float("nan"))
    speed = torch.full((n,), float("nan"))
    for _ in range(int(2.5 / 0.005)):
        prev = s.pos[:, 0].clone()
        s, ev = sim.step(s, 0.005, 1)
        before = torch.isnan(h)
        bounces += (ev.court_contact & before).long()
        cross = before & (prev > PLANE_X) & (s.pos[:, 0] <= PLANE_X)
        h = torch.where(cross, s.pos[:, 2], h)
        lat = torch.where(cross, s.pos[:, 1] - ROBOT_START[1], lat)
        speed = torch.where(cross, s.vel.norm(dim=-1), speed)
    ok = (bounces == 1) & ~torch.isnan(h)
    q = lambda x, p: round(float(x[ok].quantile(p)), 3) if ok.any() else None
    return {"one_bounce": round(float(ok.float().mean()), 4),
            "height_p05": q(h, 0.05), "height_p50": q(h, 0.5), "height_p95": q(h, 0.95),
            "lateral_min": round(float(lat[ok].min()), 3) if ok.any() else None,
            "lateral_max": round(float(lat[ok].max()), 3) if ok.any() else None,
            "speed_p50": q(speed, 0.5)}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--families", action="store_true", help="report every named family")
    ap.add_argument("--n", type=int, default=2048)
    a = ap.parse_args()
    names = FAMILY_NAMES if a.families else ("easy_forehand",)
    out = {name: evaluate(only(name), a.n) for name in names}
    for k, v in out.items():
        print(f"{k:14s} {v}")
    print(json.dumps(out))
