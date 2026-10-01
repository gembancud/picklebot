import sys
from pathlib import Path

import mujoco
import numpy as np
import pytest

from picklebot_mj.ball_sim import PADDLE_HALF
from picklebot_mj.g1_paddle import FACE_CENTRE_X, PADDLE_BODY, PADDLE_MASS, WRIST_BODY, get_spec

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))


@pytest.fixture(scope="module")
def model():
    return get_spec().compile()


def test_paddle_attached_to_right_wrist(model):
    pid = model.body(PADDLE_BODY).id
    assert model.body_parentid[pid] == model.body(WRIST_BODY).id
    assert model.body_mass[pid] == pytest.approx(PADDLE_MASS)


def test_paddle_frame_axes_in_wrist(model):
    d = mujoco.MjData(model)
    mujoco.mj_kinematics(model, d)
    pid, wid = model.body(PADDLE_BODY).id, model.body(WRIST_BODY).id
    rw = d.xmat[wid].reshape(3, 3)
    rp = d.xmat[pid].reshape(3, 3)
    local = rw.T @ rp  # paddle axes in the wrist frame
    assert np.allclose(local[:, 0], [0, 0, 1], atol=1e-6)  # width   -> wrist z
    assert np.allclose(local[:, 1], [1, 0, 0], atol=1e-6)  # length  -> wrist x (along the hand)
    assert np.allclose(local[:, 2], [0, 1, 0], atol=1e-6)  # normal  -> wrist y (palm normal)
    offset = rw.T @ (d.xpos[pid] - d.xpos[wid])
    assert np.allclose(offset, [FACE_CENTRE_X, 0, 0], atol=1e-9)


def test_paddle_geoms_do_not_collide(model):
    for name in ("paddle_face", "paddle_handle"):
        g = model.geom(name).id
        assert model.geom_contype[g] == 0 and model.geom_conaffinity[g] == 0
    assert np.allclose(model.geom(model.geom("paddle_face").id).size, PADDLE_HALF)


def test_fixed_base_model_and_actuators():
    from stage2_envelope import ARM, actuator_for_joint, fixed_base_model
    m = fixed_base_model()
    act = actuator_for_joint(m)
    for j in ARM:
        assert m.joint(j).id in act
    assert m.nq == m.njnt  # no free joint: all hinges
