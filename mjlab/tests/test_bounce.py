"""Ball-court and ball-net contact on the full court spec (CPU MuJoCo, aerodynamics on)."""

import mujoco
import numpy as np
import pytest
import torch

from picklebot_mj import ball, court

DTS = sorted(court.COURT_DAMPRATIO_BY_DT)
R = ball.BALL_RADIUS


def make(dt, pos):
    spec = court.build_court_spec()
    spec.option.timestep = dt
    spec.option.integrator = mujoco.mjtIntegrator.mjINT_IMPLICITFAST
    spec.option.cone = mujoco.mjtCone.mjCONE_PYRAMIDAL
    ball.add_ball(spec.worldbody, pos=pos)
    court.add_ball_contacts(spec)
    m = spec.compile()
    return m, mujoco.MjData(m), m.body("ball").id


def run(dt, pos, vel=(0, 0, 0), spin=(0, 0, 0), duration=1.5):
    """Simulate; return per-step arrays of time, pos, linvel, angvel(world), ncon."""
    m, d, bid = make(dt, pos)
    d.qvel[0:3], d.qvel[3:6] = vel, spin
    res = np.zeros(6)
    out = {k: [] for k in ("t", "x", "v", "w", "ncon")}
    for _ in range(int(round(duration / dt))):
        mujoco.mj_forward(m, d)
        mujoco.mj_objectVelocity(m, d, mujoco.mjtObj.mjOBJ_BODY, bid, res, 0)
        out["t"].append(d.time); out["x"].append(d.qpos[:3].copy()); out["v"].append(res[3:].copy())
        out["w"].append(res[:3].copy()); out["ncon"].append(d.ncon)
        d.xfrc_applied[bid] = ball.ball_wrench(torch.tensor(res[3:].copy()), torch.tensor(res[:3].copy())).numpy()
        mujoco.mj_step(m, d)
    return {k: np.array(v) for k, v in out.items()}


def first_contact_window(tr):
    c = np.flatnonzero(tr["ncon"] > 0)
    start = c[0]
    end = start + np.argmax(tr["ncon"][start:] == 0)  # first free step after contact
    return start, end


def energy(tr, i):
    return 0.5 * ball.BALL_MASS * tr["v"][i] @ tr["v"][i] + ball.BALL_MASS * 9.81 * tr["x"][i][2]


@pytest.mark.parametrize("dt", DTS)
def test_official_drop_test(dt):
    tr = run(dt, [0.5, 0.5, 1.981 + R], duration=1.6)
    start, end = first_contact_window(tr)
    after = tr["x"][end:, 2]
    apex_i = end + np.argmax(after[: np.argmax(np.diff(after) < 0) + 1])
    apex_top = tr["x"][apex_i][2] + R
    assert 0.762 <= apex_top <= 0.864, apex_top
    # Impact time vs gravity-only free fall of the ball bottom (spec: within 0.01 s).
    assert abs(tr["t"][start] - np.sqrt(2 * 1.981 / 9.81)) < 0.01
    assert np.linalg.norm(tr["x"][apex_i][:2] - [0.5, 0.5]) <= 0.01
    assert energy(tr, apex_i) < energy(tr, start)


@pytest.mark.xfail(strict=True, reason=(
    "Known failure (mjlab/results/stage1-bounce.md): native MuJoCo soft-contact restitution "
    "depends on penetration depth at first detection (impact phase vs timestep grid); "
    "COR ranges 0.1-2.9 at dt 1-2 ms"))
@pytest.mark.parametrize("dt", DTS)
@pytest.mark.parametrize("height", [0.5, 1.0, 2.0, 3.0])
def test_cor_stable_across_drop_heights(dt, height):
    tr = run(dt, [-3.0, 1.0, height + R], duration=np.sqrt(2 * height / 9.81) + 0.2)
    start, end = first_contact_window(tr)
    cor = tr["v"][end][2] / -tr["v"][start - 1][2]
    assert 0.58 <= cor <= 0.70, (height, cor)
    assert tr["v"][end][2] < -tr["v"][start - 1][2]  # never gains energy


@pytest.mark.parametrize("dt", DTS)
def test_angled_bounce_loses_energy_and_gains_topspin(dt):
    vin = np.array([8.0, 0.0, -6.0])
    tr = run(dt, [-5.0, 0.0, R + 0.03], vel=vin, duration=0.25)
    start, end = first_contact_window(tr)
    v_out, w_out = tr["v"][end], tr["w"][end]
    assert v_out[2] > 0
    assert 0 < v_out[0] < tr["v"][start - 1][0]  # friction slows the tangential speed
    assert w_out[1] > 0  # moving +x: friction at the bottom induces topspin (+y)
    assert energy(tr, end) < energy(tr, start - 1)


@pytest.mark.parametrize("dt", DTS)
def test_backspin_checks_up(dt):
    vin = np.array([6.0, 0.0, -5.0])
    plain = run(dt, [-5.0, 0.0, R + 0.03], vel=vin, duration=0.2)
    back = run(dt, [-5.0, 0.0, R + 0.03], vel=vin, spin=[0.0, -150.0, 0.0], duration=0.2)
    _, e1 = first_contact_window(plain)
    _, e2 = first_contact_window(back)
    assert back["v"][e2][0] < plain["v"][e1][0]


@pytest.mark.parametrize("dt", [
    pytest.param(0.005, marks=pytest.mark.xfail(
        strict=True, reason="5 ms: 2*dt soft contact cannot stop a 12 m/s ball within the net; it tunnels")),
    0.002, 0.001])
def test_ball_into_net_is_stopped(dt):
    tr = run(dt, [-1.0, 0.5, 0.5], vel=[12.0, 0.0, 0.0], duration=0.4)
    assert tr["x"][:, 0].max() < R + court.NET_THICKNESS  # never passes the net plane
    hit = np.flatnonzero(tr["ncon"] > 0)[0]
    end = hit + np.argmax(tr["ncon"][hit:] == 0)
    assert abs(tr["v"][end][0]) < 0.3 * 12.0  # Unity net restitution is 0.10


@pytest.mark.parametrize("dt", DTS)
def test_ball_over_net_clears(dt):
    # A ball passing 10 cm above the centre of the net does not touch it.
    tr = run(dt, [-1.0, 0.0, court.NET_CENTER_HEIGHT + R + 0.10 + 0.05], vel=[12.0, 0.0, 0.5], duration=0.15)
    assert tr["ncon"].max() == 0 and tr["x"][-1][0] > 0.5


def test_floor_contact_pair_is_used_not_default_collision():
    m, d, bid = make(0.002, [-3.0, 1.0, R - 0.001])
    mujoco.mj_forward(m, d)
    assert d.ncon == 1 and d.contact[0].exclude == 0
    # The contact comes from the explicit pair (its solref differs from the floor default).
    assert np.allclose(d.contact[0].solref, court.court_solref(0.002))


def test_uncalibrated_dt_is_rejected():
    with pytest.raises(ValueError):
        court.court_solref(0.003)
