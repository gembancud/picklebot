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


@pytest.mark.skipif(not tr.CAPSULES_JSON.exists(), reason="run scripts/motion/export_collision_geoms.py first")
def test_ik_uses_the_paddle_g1_capsules_and_avoids_self_collision(tmp_path):
    import subprocess

    import mujoco as mj

    xml = tr.capsule_model_xml(tmp_path / "g1_capsules.xml")
    m = mj.MjModel.from_xml_path(str(xml))
    caps = [g for g in range(m.ngeom) if m.geom_contype[g]]
    assert caps and all((mj.mj_id2name(m, mj.mjtObj.mjOBJ_GEOM, g) or "").startswith("cap_") for g in caps)
    assert m.body("paddle").id > 0
    subprocess.run([sys.executable, str(ROOT / "scripts/motion/tennis_retarget.py"), str(BVH), "--max-seconds", "6",
                    "--out", str(tmp_path)], check=True, capture_output=True, cwd=ROOT)
    csv = np.loadtxt(tmp_path / "astrejos_Derecha.csv", delimiter=",")
    d = mj.MjData(m)
    arm = {m.body(b).id for b in tr.ARM_L + tr.ARM_R + ["paddle"]}
    held = {m.body("paddle").id} | {m.body(b).id for b in tr.ARM_R}  # the paddle sits in the right hand
    deep = 0
    for row in csv:
        d.qpos[:3], d.qpos[3:7], d.qpos[7:] = row[:3], row[[6, 3, 4, 5]], row[7:]
        mj.mj_kinematics(m, d)
        mj.mj_collision(m, d)
        for c in d.contact[: d.ncon]:
            b1, b2 = m.geom_bodyid[c.geom1], m.geom_bodyid[c.geom2]
            if {b1, b2} <= held:
                continue
            if (b1 in arm or b2 in arm) and -c.dist > 0.02:
                deep += 1
                break
    # Frames with an arm/paddle overlap deeper than 2 cm: 0.3 % before the paddle orientation target, 2.3 % with it
    # (the paddle face brushing the thigh in fast swings; stage5b-paddle-orientation.md). Regression bound, not a gate.
    assert deep / len(csv) < 0.03


@pytest.mark.skipif(not tr.CAPSULES_JSON.exists(), reason="run scripts/motion/export_collision_geoms.py first")
def test_paddle_face_follows_the_swing_on_a_backhand(tmp_path):
    import json
    import subprocess

    bvh = DATA / "jgacosta_Reves.bvh"
    if not bvh.exists():
        pytest.skip("clip missing")
    subprocess.run([sys.executable, str(ROOT / "scripts/motion/tennis_retarget.py"), str(bvh), "--max-seconds", "10",
                    "--out", str(tmp_path)], check=True, capture_output=True, cwd=ROOT)
    rep = json.loads((tmp_path / "jgacosta_Reves.json").read_text())
    assert rep["swing_frames"] > 20
    assert rep["paddle_normal_err_swing_median_deg"] < 10  # face normal along the hand's travel during swings
    assert rep["pos_err_median_m"] < 0.05  # body tracking not traded away
