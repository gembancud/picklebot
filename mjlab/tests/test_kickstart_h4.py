"""Stage 5C kickstart (D-082): converting an executor action to a wider latent barrier keeps its latent."""

import importlib.util
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("kickstart_h4", ROOT / "scripts" / "kickstart_h4.py")
ks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ks)


def test_convert_keeps_the_latent_and_the_wrist_part():
    torch.manual_seed(0)
    a = torch.randn(64, 35) * 2.0
    b = ks.convert(a, 32, 1.0, 3.0)
    mu, sigma = torch.randn(64, 32), torch.rand(64, 32) + 0.1
    z1 = mu + 1.0 * sigma * torch.tanh(a[:, :32])
    z3 = mu + 3.0 * sigma * torch.tanh(b[:, :32])
    assert torch.allclose(z1, z3, atol=1e-4)
    assert torch.equal(a[:, 32:], b[:, 32:])
    assert (torch.tanh(b[:, :32]).abs() <= 1.0 / 3.0 + 1e-6).all()
