import math

import mujoco
import numpy as np
import pytest

from picklebot_mj import court


@pytest.fixture(scope="module")
def model_data():
    m = court.build_court_spec().compile()
    return m, mujoco.MjData(m)


def test_constants_match_unity_reference():
    # Assets/Picklebot/Core/CourtGeometryV0.cs and V1.cs
    assert court.COURT_LENGTH == pytest.approx(13.4112)
    assert court.COURT_WIDTH == pytest.approx(6.0960)
    assert court.KITCHEN_DEPTH == pytest.approx(2.1336)
    assert court.NET_SIDELINE_HEIGHT == pytest.approx(0.9144)
    assert court.NET_CENTER_HEIGHT == pytest.approx(0.8636)
    assert court.NET_POST_SPAN == pytest.approx(6.7056)


def test_net_height_function():
    assert court.net_height_at(0.0) == pytest.approx(court.NET_CENTER_HEIGHT)
    assert court.net_height_at(court.HALF_WIDTH) == pytest.approx(court.NET_SIDELINE_HEIGHT)
    assert court.net_height_at(-court.HALF_WIDTH) == pytest.approx(court.NET_SIDELINE_HEIGHT)
    assert court.net_height_at(court.HALF_NET_POST_SPAN + 0.01) == 0.0


def _ray_down(m, d, x, y, groups=(1, 0, 0, 0, 0, 0)):
    geomid = np.zeros(1, dtype=np.int32)
    dist = mujoco.mj_ray(m, d, np.array([x, y, 3.0]), np.array([0.0, 0.0, -1.0]),
                         np.array(groups, dtype=np.uint8), 1, -1, geomid)
    return 3.0 - dist, mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_GEOM, int(geomid[0]))


@pytest.mark.parametrize("y", [0.0, 0.5, 1.5, 2.5, 3.048, -1.0, -3.048, 3.3])
def test_physical_net_top_follows_regulation_height(model_data, y):
    m, d = model_data
    mujoco.mj_forward(m, d)
    top, name = _ray_down(m, d, 0.0, y)
    assert name.startswith("net_")
    # Net box has finite thickness; ray down the net mid-plane hits the top face.
    assert top == pytest.approx(court.net_height_at(y), abs=1e-3)


def test_net_has_no_gap_at_center(model_data):
    m, d = model_data
    mujoco.mj_forward(m, d)
    # A horizontal ray along +x through the bottom of the net at the centre must hit the net.
    for z in (0.05, 0.4, 0.8):
        geomid = np.zeros(1, dtype=np.int32)
        dist = mujoco.mj_ray(m, d, np.array([-1.0, 0.0, z]), np.array([1.0, 0.0, 0.0]),
                             np.array([1, 0, 0, 0, 0, 0], dtype=np.uint8), 1, -1, geomid)
        assert dist == pytest.approx(1.0 - court.NET_THICKNESS / 2, abs=1e-6)


def test_markings_are_visual_only(model_data):
    m, _ = model_data
    for i in range(m.ngeom):
        name = mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_GEOM, i)
        if m.geom_group[i] == court.MARKING_GROUP:
            assert m.geom_contype[i] == 0 and m.geom_conaffinity[i] == 0, name


def test_lines_cover_court_outline(model_data):
    m, d = model_data
    mujoco.mj_forward(m, d)
    marks = (0, 0, 0, 1, 0, 0)
    hl, hw, w = court.HALF_LENGTH, court.HALF_WIDTH, court.LINE_WIDTH
    for x, y in [(-hl + w / 2, 0.0), (hl - w / 2, 1.0), (0.0 + 3.0, hw - w / 2),
                 (-court.KITCHEN_DEPTH + w / 2, 1.0), (-4.0, 0.0)]:
        _, name = _ray_down(m, d, x, y, marks)
        assert name is not None, (x, y)
    # Inside the kitchen near the centre there is no line.
    geomid = np.zeros(1, dtype=np.int32)
    dist = mujoco.mj_ray(m, d, np.array([-1.0, 0.0, 3.0]), np.array([0.0, 0.0, -1.0]),
                         np.array(marks, dtype=np.uint8), 1, -1, geomid)
    assert dist == -1


def test_ball_dropped_on_court_comes_to_rest_on_floor(model_data):
    spec = court.build_court_spec()
    body = spec.worldbody.add_body(name="probe", pos=[-3.0, 1.0, 0.5])
    body.add_freejoint()
    body.add_geom(type=mujoco.mjtGeom.mjGEOM_SPHERE, size=[0.037, 0, 0], mass=0.024)
    m = spec.compile()
    d = mujoco.MjData(m)
    mujoco.mj_step(m, d, nstep=int(3.0 / m.opt.timestep))
    assert d.qpos[2] == pytest.approx(0.037, abs=2e-3)
    assert math.isfinite(d.qpos[0])
