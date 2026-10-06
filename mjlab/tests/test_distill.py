"""Stage 5 distillation (D-042): a tiny DAgger run routes both episode types, lowers the loss, saves a big student."""

import json
import subprocess
import sys
from pathlib import Path

import pytest
import torch

ROOT = Path(__file__).resolve().parents[1]
LOGS = ROOT / "artifacts/train/logs/picklebot_return_stand"
MOVE = LOGS / "2026-10-06_04-16-06_drill-move-d01/model_13900.pt"
HIT = LOGS / "2026-10-06_01-09-48_footwork-f02/model_12000.pt"


@pytest.mark.skipif(not torch.cuda.is_available() or not (MOVE.exists() and HIT.exists()),
                    reason="needs CUDA and the local teacher checkpoints")
def test_tiny_distillation(tmp_path):
    cmd = [sys.executable, str(ROOT / "scripts/distill.py"), "--move-teacher", str(MOVE), "--hit-teacher", str(HIT),
           "--out", str(tmp_path), "--envs", "64", "--iterations", "4", "--batch", "512", "--save-every", "4",
           "--no-compile", "--hidden", "1024,512,256"]
    subprocess.run(cmd, check=True, cwd=ROOT, capture_output=True)
    log = json.load(open(tmp_path / "distill_log.json"))["log"]
    assert log[-1]["loss"] < log[0]["loss"]
    assert all(r["mse_move"] == r["mse_move"] and r["mse_hit"] == r["mse_hit"] for r in log)  # both types seen
    ck = torch.load(tmp_path / "model_4.pt", map_location="cpu", weights_only=False)
    a = ck["actor_state_dict"]
    assert a["mlp.0.weight"].shape == (1024, 118) and a["mlp.6.weight"].shape == (29, 256)
