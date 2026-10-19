"""How well can a spin-blind forward prediction undo ball-observation delay? (Stage 5F step 0, D-109.)

For each drill v2 feed family, feeds are launched as BallPhysicsAction._feed builds them (court-anchored at the start
spot) and flown by the full ball simulation (no paddle in reach). At random times during the flight, a delayed
measurement is taken:
- the true state LAG ms earlier;
- plus the Stage 5E ball-state noise (3 cm, 0.15 m/s per axis).

Two estimates of the current state are scored against the truth:
- **raw:** the delayed measurement used as it is (what the executors saw in Stage 5E);
- **compensated:** the measurement rolled forward by LAG with the planner's spin-blind flight and bounce model
  (`planner._rollout_step`, spin set to zero).

The output is the median and 90th-percentile position and velocity error per family, for lags of 0, 20 and 40 ms. Lag 0
is the noise-only floor.

Usage: python scripts/diag/ball_lag_error.py [--per-family 64] [--json OUT]  (CPU)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tests"))
from test_drill_v2 import _feed_states  # noqa: E402  (the feed geometry of BallPhysicsAction._feed)

from picklebot_mj.ball_sim import BallParams, BallSim, BallState, PaddleState  # noqa: E402
from picklebot_mj.drill_v2 import DRILL_V2_GROUPS  # noqa: E402
from picklebot_mj.planner import _DEFAULT_PARAMS, _rollout_step  # noqa: E402

DT = 0.005
NOISE_P, NOISE_V = 0.03, 0.15


def flights(pos, vel, spin, seconds=1.6):
    """True (pos, vel) every DT for each feed: tensors (T, N, 3)."""
    n = pos.shape[0]
    sim = BallSim(BallParams())
    s = BallState(pos.clone(), vel.clone(), spin.clone())
    far = PaddleState(torch.tensor([50.0, 50.0, 50.0]).repeat(n, 1), torch.eye(3).repeat(n, 1, 1),
                      torch.zeros(n, 3), torch.zeros(n, 3))
    P, V = [s.pos.clone()], [s.vel.clone()]
    for _ in range(int(seconds / DT)):
        s, _ = sim.step(s, DT, 6, far, adaptive=False)
        P.append(s.pos.clone())
        V.append(s.vel.clone())
    return torch.stack(P), torch.stack(V)


def compensate(p, v, lag_s, sub=4):
    """Roll (p, v) forward by lag_s with the planner's spin-blind model (bounce included)."""
    if lag_s <= 0:
        return p, v
    w = torch.zeros_like(p)
    b = torch.zeros(p.shape[0], dtype=torch.bool)
    f = torch.zeros_like(b)
    out = p[:, :2].clone()
    for _ in range(sub):
        p, v, w, b, f, out = _rollout_step(_DEFAULT_PARAMS, lag_s / sub, p, v, w, b, f, out)
    return p, v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-family", type=int, default=64)
    ap.add_argument("--samples", type=int, default=8, help="measurement times per feed")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    g = torch.Generator().manual_seed(4210010)  # a dev seed (step-0 block), recorded in the seed ledger
    fams = [f for grp in DRILL_V2_GROUPS.values() for f in grp]
    pos, vel, spin, F = _feed_states(fams, a.per_family, seed=4210010)
    TP, TV = flights(pos, vel, spin)
    T, N = TP.shape[0], TP.shape[1]
    out = {}
    for lag_ms in (0, 20, 40):
        k = lag_ms // 5
        # measurement times: from 0.15 s into the flight to 0.9 s (well before contact), at least k steps in
        t = torch.randint(max(k, 30), 180, (N, a.samples), generator=g)
        idx = torch.arange(N).unsqueeze(-1).expand_as(t)
        p_true, v_true = TP[t, idx], TV[t, idx]
        p_meas = TP[t - k, idx] + NOISE_P * torch.randn(p_true.shape, generator=g)
        v_meas = TV[t - k, idx] + NOISE_V * torch.randn(v_true.shape, generator=g)
        pc, vc = compensate(p_meas.reshape(-1, 3), v_meas.reshape(-1, 3), lag_ms / 1000.0)
        pc, vc = pc.reshape(p_meas.shape), vc.reshape(v_meas.shape)
        row = {}
        for fam in fams:
            m = torch.tensor([x == fam for x in F])
            e = {}
            for name, (pp, vv) in (("raw", (p_meas, v_meas)), ("comp", (pc, vc))):
                ep = (pp[m] - p_true[m]).norm(dim=-1).flatten()
                ev = (vv[m] - v_true[m]).norm(dim=-1).flatten()
                e[name] = {"pos_med_cm": round(float(ep.median()) * 100, 1),
                           "pos_p90_cm": round(float(ep.quantile(0.9)) * 100, 1),
                           "vel_med": round(float(ev.median()), 3), "vel_p90": round(float(ev.quantile(0.9)), 3)}
            row[fam] = e
        out[f"lag_{lag_ms}ms"] = row
        print(f"lag {lag_ms} ms: pos error median cm (raw -> compensated)")
        for fam in fams:
            r = row[fam]
            print(f"  {fam:15s} {r['raw']['pos_med_cm']:6.1f} -> {r['comp']['pos_med_cm']:6.1f}   "
                  f"p90 {r['raw']['pos_p90_cm']:6.1f} -> {r['comp']['pos_p90_cm']:6.1f}")
    if a.json:
        json.dump(out, open(a.json, "w"), indent=1)


if __name__ == "__main__":
    main()
