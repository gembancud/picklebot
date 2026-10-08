"""Stage 5B LAFAN1 -> paddle G1 retargeting (scripts/motion/lafan_retarget.py, D-047).

Needs the GMR venv and the local LAFAN1 download; skipped elsewhere. Run:
    ~/envs/gmr/bin/python -m pytest tests/test_lafan_retarget.py
"""

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("general_motion_retargeting")
ROOT = Path(__file__).resolve().parents[1]
BVH = ROOT / "artifacts" / "motion" / "lafan1" / "bvh" / "walk1_subject1.bvh"
pytestmark = pytest.mark.skipif(not BVH.exists(), reason="LAFAN1 not downloaded")


def test_walk_clip_retargets_accurately_grounded_and_without_skating(tmp_path):
    sys.path.insert(0, str(ROOT / "scripts" / "motion"))
    import tennis_retarget as tr

    subprocess.run([sys.executable, str(ROOT / "scripts/motion/lafan_retarget.py"), str(BVH), "--max-seconds", "8",
                    "--out", str(tmp_path)], check=True, capture_output=True, cwd=ROOT)
    csv = np.loadtxt(tmp_path / "walk1_subject1.csv", delimiter=",")
    assert csv.shape == (240, 36)  # 8 s at 30 fps; base xyz + quat xyzw + 29 joints
    assert np.allclose(np.linalg.norm(csv[:, 3:7], axis=1), 1, atol=1e-6)
    rep = json.loads((tmp_path / "walk1_subject1.json").read_text())
    assert rep["accepted"] and rep["pos_err_median_m"] < 0.06
    assert min(rep["left_ankle_z_min_m"], rep["right_ankle_z_min_m"]) == pytest.approx(tr.STAND_ANKLE_Z, abs=1e-3)
    assert max(rep["left_skate_median_mps"], rep["right_skate_median_mps"]) < 0.05  # planted feet stay planted
    assert json.loads((tmp_path / "accepted.json").read_text()) == ["walk1_subject1"]
