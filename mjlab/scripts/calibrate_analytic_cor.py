"""Bisect the analytic court COR so the official drop (1.981 m, ball-bottom datum) peaks at 0.813 m (ball top).

Usage: python scripts/calibrate_analytic_cor.py
"""

import torch

from picklebot_mj.ball_sim import BallParams, BallSim, BallState

TARGET_TOP = 0.813


def drop_apex_top(cor: float, height_bottom: float = 1.981, dt: float = 0.005, substeps: int = 10,
                  dtype=torch.float64, device="cpu") -> torch.Tensor:
    p = BallParams(court_cor=cor)
    sim = BallSim(p)
    h = torch.as_tensor(height_bottom, dtype=dtype, device=device).reshape(-1)
    n = h.shape[0]
    s = BallState(torch.zeros(n, 3, dtype=dtype, device=device), torch.zeros(n, 3, dtype=dtype, device=device),
                  torch.zeros(n, 3, dtype=dtype, device=device))
    s.pos[:, 2] = h + p.radius
    bounced = torch.zeros(n, dtype=torch.bool, device=device)
    apex = torch.zeros(n, dtype=dtype, device=device)
    for _ in range(int(1.8 / dt)):
        s, ev = sim.step(s, dt, substeps)
        bounced |= ev.court_contact
        rising = bounced & (s.vel[:, 2] > 0)
        apex = torch.where(rising | (bounced & (apex > 0)), torch.maximum(apex, s.pos[:, 2]), apex)
        # stop tracking after the ball falls back to the court a second time: apex max is captured anyway
    return apex + p.radius


if __name__ == "__main__":
    lo, hi = 0.55, 0.75
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        if drop_apex_top(mid).item() > TARGET_TOP:
            hi = mid
        else:
            lo = mid
    cor = 0.5 * (lo + hi)
    print(f"COURT_COR = {cor:.4f}  apex_top = {drop_apex_top(cor).item():.4f}")
