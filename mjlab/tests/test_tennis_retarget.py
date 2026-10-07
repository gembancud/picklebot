"""Stage 5B Tennis-MoCap -> G1 retargeting (scripts/motion/tennis_retarget.py).

Needs the GMR venv and the local Tennis-MoCap download (D-046); skipped elsewhere. Run:
    ~/envs/gmr/bin/python -m pytest tests/test_tennis_retarget.py
"""

import sys
from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("general_motion_retargeting")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "motion"))
import tennis_retarget as tr  # noqa: E402

DATA = ROOT / "artifacts" / "motion" / "Tennis-MoCap" / "data"
BVH = DATA / "astrejos_Derecha.bvh"
pytestmark = pytest.mark.skipif(not BVH.exists(), reason="Tennis-MoCap not downloaded")


def test_loader_parses_arena_bvh_in_metres_z_up():
    frames, rest, height, bones = tr.load_bvh(BVH)
    assert len(frames) == 2999  # 30 s at 100 Hz
    assert set(tr.PARENT) == set(bones)
    f = frames[0]
    assert 0.7 < f["Hips"][0][2] < 1.2  # hips around 1 m above the floor, Z up
    assert f["Head"][0][2] > f["Hips"][0][2] > f["LeftAnkle"][0][2]
    assert 1.4 < height < 2.1
    for b in bones:
        assert abs(np.linalg.norm(f[b][1]) - 1) < 1e-6


def test_rest_pose_maps_to_the_g1_t_pose(tmp_path):
    import mujoco as mj

    m, q = tr.retarget_rest(BVH, tmp_path / "cfg.json")
    for j in range(1, m.njnt):
        name = mj.mj_id2name(m, mj.mjtObj.mjOBJ_JOINT, j)
        want = tr.TPOSE.get(name, 0.0)
        tol = 10 if "wrist" in name else 3  # wrists have no target (hands are position-only), so they float a little
        assert abs(q[6 + j] - want) < np.deg2rad(tol), (name, np.degrees(q[6 + j]), np.degrees(want))


def test_clip_csv_layout_grounding_and_checks(tmp_path):
    import subprocess

    subprocess.run([sys.executable, str(ROOT / "scripts/motion/tennis_retarget.py"), str(BVH), "--max-seconds", "2",
                    "--out", str(tmp_path)], check=True, capture_output=True, cwd=ROOT)
    csv = np.loadtxt(tmp_path / "astrejos_Derecha.csv", delimiter=",")
    assert csv.shape == (100, 36)  # 2 s at 50 Hz; base xyz + quat xyzw + 29 joints
    assert np.allclose(np.linalg.norm(csv[:, 3:7], axis=1), 1, atol=1e-6)
    import json

    rep = json.loads((tmp_path / "astrejos_Derecha.json").read_text())
    assert min(rep["left_ankle_z_min_m"], rep["right_ankle_z_min_m"]) == pytest.approx(tr.STAND_ANKLE_Z, abs=1e-3)
    assert rep["human_hand"] == "right"
    for wrist in ("right_wrist_roll_joint", "right_wrist_pitch_joint", "right_wrist_yaw_joint"):
        assert wrist not in rep["joints_at_limit"]  # hands tracked by position only
    hum = np.load(tmp_path / "astrejos_Derecha_human.npz")
    assert hum["pos"].shape == (100, len(tr.MAP), 3)
