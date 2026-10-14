"""Left-right mirroring of G1 motion rows (scripts/motion/mirror_g1_csv.py, D-077)."""
import importlib.util
from pathlib import Path

import numpy as np

spec = importlib.util.spec_from_file_location(
    "mirror_g1_csv", Path(__file__).resolve().parents[1] / "scripts" / "motion" / "mirror_g1_csv.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def _rows(n=50, seed=0):
    r = np.random.default_rng(seed)
    q = r.normal(size=(n, 36))
    q[:, 3:7] /= np.linalg.norm(q[:, 3:7], axis=1, keepdims=True)
    return q


def test_mirroring_twice_is_the_identity():
    q = _rows()
    assert np.allclose(m.mirror_rows(m.mirror_rows(q)), q)


def test_left_and_right_swap_with_roll_and_yaw_negated():
    q = _rows()
    o = m.mirror_rows(q)
    J = list(m.G1_JOINTS)
    assert np.allclose(o[:, 1], -q[:, 1]) and np.allclose(o[:, [0, 2]], q[:, [0, 2]])
    li, ri = J.index("left_hip_roll_joint"), J.index("right_hip_roll_joint")
    assert np.allclose(o[:, 7 + ri], -q[:, 7 + li])
    lk, rk = J.index("left_knee_joint"), J.index("right_knee_joint")
    assert np.allclose(o[:, 7 + rk], q[:, 7 + lk])
    wy = J.index("waist_yaw_joint")
    assert np.allclose(o[:, 7 + wy], -q[:, 7 + wy])


def test_a_yaw_rotation_is_reversed():
    # root yawed by +30 deg (about z): the mirror is yawed by -30 deg
    a = np.deg2rad(30)
    q = np.zeros((1, 36))
    q[0, 3:7] = [0, 0, np.sin(a / 2), np.cos(a / 2)]  # xyzw
    o = m.mirror_rows(q)
    assert np.allclose(o[0, 3:7], [0, 0, -np.sin(a / 2), np.cos(a / 2)])
