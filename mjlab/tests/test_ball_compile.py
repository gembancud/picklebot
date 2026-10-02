"""The compiled training ball step matches the eager step (float32 rounding) on a mixed batch."""

import sys
from pathlib import Path

import pytest
import torch

pytestmark = pytest.mark.skipif(not torch.cuda.is_available(), reason="needs CUDA")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))


def test_compiled_step_matches_eager_over_many_steps():
    from bench_ball_compile import make

    from picklebot_mj.ball_sim import BallSim, CompiledBallSim, PaddleState

    s_e, pd = make(2048, seed=3)
    s_c = type(s_e)(s_e.pos.clone(), s_e.vel.clone(), s_e.spin.clone())
    eager, comp = BallSim(), CompiledBallSim(mode="default")
    hits_e = hits_c = 0
    for _ in range(40):
        s_e, ev_e = eager.step(s_e, 0.005, 6, pd, adaptive=False)
        s_c, ev_c = comp.step(s_c, 0.005, 6, pd, adaptive=False)
        hits_e += int(ev_e.paddle_contact.sum())
        hits_c += int(ev_c.paddle_contact.sum())
        pd = PaddleState(pd.pos + pd.lin_vel * 0.005, pd.rot, pd.lin_vel, pd.ang_vel)
    # Chaotic contacts can diverge for a few balls after rounding differences; the bulk must agree.
    close = ((s_e.pos - s_c.pos).norm(dim=-1) < 1e-3).float().mean()
    assert close > 0.99, float(close)
    assert abs(hits_e - hits_c) <= max(2, 0.01 * hits_e)
