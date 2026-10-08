"""scripts/widen_checkpoint.py: widening hidden layers keeps the network's outputs exactly."""

import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from widen_checkpoint import pad, widen_mlp  # noqa: E402


def _forward(sd, x, n_layers):
    for i in range(n_layers):
        x = x @ sd[f"mlp.{2 * i}.weight"].T + sd[f"mlp.{2 * i}.bias"]
        if i < n_layers - 1:
            x = torch.nn.functional.elu(x)
    return x


def test_widening_is_function_preserving_and_pads_optimizer_state():
    torch.manual_seed(0)
    dims = [160, 512, 256, 128, 29]
    sd = {}
    for i in range(4):
        sd[f"mlp.{2 * i}.weight"] = torch.randn(dims[i + 1], dims[i]) * 0.1
        sd[f"mlp.{2 * i}.bias"] = torch.randn(dims[i + 1]) * 0.1
    x = torch.randn(64, 160)
    before = _forward(sd, x, 4)
    shapes = widen_mlp(sd, [1024, 512, 256], torch.Generator().manual_seed(1))
    assert sd["mlp.0.weight"].shape == (1024, 160) and sd["mlp.6.weight"].shape == (29, 256)
    assert torch.allclose(_forward(sd, x, 4), before, atol=1e-5)  # float32 summation order only
    assert shapes[(256, 512)] == (512, 1024)
    m = torch.ones(256, 512)
    assert pad(m, (512, 1024)).sum() == m.sum()
