"""S-D2b footwork hint: the fast interception estimate is close to the simulated ball (all families)."""

import sys
from pathlib import Path

import pytest
import torch

from picklebot_mj.ball_sim import BallSim
from picklebot_mj.feeds import FAMILY_NAMES, only
from picklebot_mj.tasks.shadow_swing import HINT_Z, predict_intercept

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from tune_feed import _FakeTerm  # noqa: E402


def _actual(t, n):
    """Simulated point where the ball descends through HINT_Z after its first bounce (or its apex)."""
    s, sim = t.ball, BallSim()
    bounced = torch.zeros(n, dtype=torch.bool)
    hit = torch.full((n, 2), float("nan"))
    prev_z = s.pos[:, 2].clone()
    apex = torch.full((n, 3), float("nan"))
    for _ in range(int(4.0 / 0.005)):
        s, ev = sim.step(s, 0.005, 1)
        newly = ev.court_contact & ~bounced
        bounced |= ev.court_contact
        z = s.pos[:, 2]
        after = bounced & ~newly
        desc = after & (prev_z >= HINT_Z) & (z < HINT_Z) & torch.isnan(hit[:, 0])
        hit = torch.where(desc.unsqueeze(-1), s.pos[:, :2], hit)
        top = after & (z < prev_z) & torch.isnan(apex[:, 0])
        apex = torch.where(top.unsqueeze(-1), s.pos, apex)
        prev_z = z
    return torch.where(torch.isnan(hit[:, :1]), apex[:, :2], hit)


@pytest.mark.parametrize("name", FAMILY_NAMES)
def test_hint_close_to_simulated_interception(name):
    n = 256
    t = _FakeTerm(only(name), n, seed=11)  # a different seed than the calibration
    t._feed(torch.arange(n))
    xi, yi = predict_intercept(t.ball.pos.clone(), t.ball.vel.clone(), t.family)
    act = _actual(t, n)
    err = ((torch.stack([xi, yi], -1) - act).norm(dim=-1))
    ok = torch.isfinite(err)
    assert ok.float().mean() > 0.95
    print(name, round(float(err[ok].median()), 3), round(float(err[ok].quantile(0.9)), 3))
    assert float(err[ok].median()) < 0.3, (name, float(err[ok].median()))
