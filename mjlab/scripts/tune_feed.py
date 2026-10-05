"""Offline checks of feed families with the analytic ball alone (no robot).

For each family: sample feeds with the task's own sampler, simulate, and report the
fraction that bounce exactly once before the contact plane x = ROBOT_X + 0.2 (in front
of the pelvis), plus height and lateral offset (from the pelvis) when crossing it.
Reach families (--reach): the hittable window is every ball position after the first bounce and
before a second one with height 0.35-1.2 m. Travel = horizontal distance from the anchor (pelvis)
to the nearest window point, minus a comfortable arm reach of 0.7 m; speed = travel / time to it.
Usage: python scripts/tune_feed.py [--families | --reach] [--n 2048]
"""

from __future__ import annotations

import argparse
import json

import torch

from picklebot_mj import court
from picklebot_mj.ball_sim import BallSim, BallState
from picklebot_mj.feeds import FAMILIES, FAMILY_NAMES, REACH_FAMILIES, STAGE4_FAMILIES, FeedMix, only
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
        self.cfg = type("Cfg", (), {"target_mode": "random", "recovery_mode": "random"})()
        self.gen_recover = torch.Generator(device=device).manual_seed(seed + 2)
        self.recover_xy = torch.zeros(n, 2)
        self.gen_target = torch.Generator(device=device).manual_seed(seed + 1)
        self.target = torch.zeros(n, dtype=torch.long)
        self.anchor_xy = ROBOT_START  # fixed anchor offline; tests may move it

    def _anchor(self, env_ids):
        k = len(env_ids)
        return torch.full((k,), float(self.anchor_xy[0])), torch.full((k,), float(self.anchor_xy[1]))

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


REACH_M = 0.7
HIT_Z = (0.35, 1.2)


def evaluate_reach(mix: FeedMix, n=2048, seed=0, anchor=ROBOT_START):
    t = _FakeTerm(mix, n, seed=seed)
    t.anchor_xy = anchor
    t._feed(torch.arange(n))
    s, sim = t.ball, BallSim()
    a = torch.tensor(anchor, dtype=torch.float32)
    bounces = torch.zeros(n, dtype=torch.long)
    land = torch.full((n, 2), float("nan"))
    best = torch.full((n,), float("inf"))
    t_best = torch.full((n,), float("nan"))
    lateral = torch.full((n,), float("nan"))
    dt = 0.005
    for i in range(int(3.0 / dt)):
        s, ev = sim.step(s, dt, 1)
        first = ev.court_contact & (bounces == 0)
        land = torch.where(first.unsqueeze(-1), s.pos[:, :2], land)
        bounces += ev.court_contact.long()
        z = s.pos[:, 2]
        window = (bounces == 1) & (z >= HIT_Z[0]) & (z <= HIT_Z[1])
        d = (s.pos[:, :2] - a).norm(dim=-1)
        better = window & (d < best)
        best = torch.where(better, d, best)
        t_best = torch.where(better, torch.full_like(d, (i + 1) * dt), t_best)
        lateral = torch.where(better, s.pos[:, 1] - a[1], lateral)
    ok = torch.isfinite(best)
    travel = (best - REACH_M).clamp(min=0.0)
    speed = travel / t_best
    q = lambda x, p: round(float(x[ok].quantile(p)), 3) if ok.any() else None
    lands_in = (land[:, 0] > -court.HALF_LENGTH) & (land[:, 0] < 0) & (land[:, 1].abs() < court.HALF_WIDTH)
    return {"hittable": round(float(ok.float().mean()), 4), "lands_in": round(float(lands_in.float().mean()), 4),
            "travel_p05": q(travel, 0.05), "travel_p50": q(travel, 0.5), "travel_p95": q(travel, 0.95),
            "time_p50": q(t_best, 0.5), "speed_p95": q(speed, 0.95),
            "lateral_p05": q(lateral, 0.05), "lateral_p95": q(lateral, 0.95)}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--families", action="store_true", help="report every named family")
    ap.add_argument("--reach", action="store_true", help="travel needed per family (all families)")
    ap.add_argument("--n", type=int, default=2048)
    a = ap.parse_args()
    if a.reach:  # from the default spot plus the deep and forward corners of the start box
        out = {}
        for ax in (ROBOT_START[0], ROBOT_START[0] - 0.7, ROBOT_START[0] + 0.7):
            for name in FAMILY_NAMES:
                out[f"{name}@x{ax:+.1f}"] = evaluate_reach(only(name), a.n, anchor=(ax, ROBOT_START[1]))
    else:
        names = STAGE4_FAMILIES if a.families else ("easy_forehand",)
        out = {name: evaluate(only(name), a.n) for name in names}
    for k, v in out.items():
        print(f"{k:14s} {v}")
    print(json.dumps(out))
