"""Soft volley on-ramp geometry: height and speed as the ball passes the pelvis (offline, CPU)."""
import importlib.util, itertools
from dataclasses import replace
from pathlib import Path
import torch
from picklebot_mj.ball_sim import BallSim
from picklebot_mj.feeds import FAMILIES, only
spec = importlib.util.spec_from_file_location("tune_feed", Path("scripts/tune_feed.py"))
tf = importlib.util.module_from_spec(spec); spec.loader.exec_module(tf)
base = FAMILIES["volley_forehand"]
def run(cfg, ax, n=256):
    FAMILIES["volley_forehand"] = cfg
    t = tf._FakeTerm(only("volley_forehand"), n, seed=0); t.anchor_xy = (ax, 0.0)
    t._feed(torch.arange(n)); s, sim = t.ball, BallSim()
    z_at = torch.full((n,), float("nan")); v_at = z_at.clone(); bounced = torch.zeros(n, dtype=torch.bool)
    for i in range(600):
        prev = s.pos[:, 0].clone(); s, ev = sim.step(s, 0.005, 1)
        p = (prev > ax) & (s.pos[:, 0] <= ax) & torch.isnan(z_at)
        z_at = torch.where(p, torch.where(bounced, torch.full_like(z_at, -1.0), s.pos[:, 2]), z_at)
        v_at = torch.where(p, s.vel.norm(dim=-1), v_at); bounced |= ev.court_contact
    return round(float(z_at.nanmedian()), 2), round(float(v_at.nanmedian()), 2)
for bx, sz, ft in itertools.product((-7.4, -7.9, -8.4), (1.0, 1.3), (1.0, 1.15, 1.3)):
    cfg = replace(base, bounce_x=(bx - 0.1, bx + 0.1), start_z=(sz - 0.05, sz + 0.05), flight_time=(ft - 0.02, ft + 0.02))
    print(bx, sz, ft, {x: run(cfg, x) for x in (-4.9, -4.2, -3.4, -2.6)}, flush=True)
