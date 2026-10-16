"""Stage 5D consolidation (D-092): the composite teacher reads a residual executor in the lambda-3 action space."""

import importlib.util
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("consolidate", ROOT / "scripts" / "consolidate.py")
cs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cs)


class Fixed:
    """A stand-in actor returning a fixed action and recording the last-action slice it was shown."""

    def __init__(self, a):
        self.a, self.seen = a, None

    def __call__(self, td):
        self.seen = td["actor"][:, 4:7].clone()
        return self.a.clone()


def test_composite_matches_the_residual_action_term_and_keeps_own_last_actions():
    torch.manual_seed(0)
    n, dim, L, lam, lam_r, wr, wr_r = 8, 7, 4, 3.0, 1.0, 0.3, 0.1
    sl = slice(4, 7)  # pretend the last-action slice is 3 wide here; the teacher writes its own lasts into it
    a_b, a_r = torch.randn(n, 3) * 0.5, torch.randn(n, 3) * 0.5
    # dims: 2 latent + 1 wrist in the slice-sized actions (dim of actions = 3 for this toy)
    base, res = Fixed(a_b), Fixed(a_r)
    t = cs.CompositeTeacher(base, res, n, 3, 2, lam, lam_r, wr, wr_r, sl, "cpu")
    x = torch.zeros(n, dim)
    y = t(x)
    # latent dims: lam tanh(a) = lam tanh(a_b) + lam_r tanh(a_r)
    assert torch.allclose(lam * y[:, :2], (lam * torch.tanh(a_b[:, :2]) + lam_r * torch.tanh(a_r[:, :2])).clamp(-lam * 0.999, lam * 0.999), atol=1e-5)
    # wrist dims: wr tanh(a) = wr tanh(a_b) + wr_r tanh(a_r)
    assert torch.allclose(wr * y[:, 2:], (wr * torch.tanh(a_b[:, 2:]) + wr_r * torch.tanh(a_r[:, 2:])).clamp(-wr * 0.999, wr * 0.999), atol=1e-5)
    # second call: each part sees its own last action
    t(x)
    assert torch.allclose(base.seen, a_b) and torch.allclose(res.seen, a_r)
    t.reset(torch.ones(n, dtype=torch.bool))
    t(x)
    assert torch.count_nonzero(base.seen) == 0 and torch.count_nonzero(res.seen) == 0
