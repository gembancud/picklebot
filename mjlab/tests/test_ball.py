import math

import mujoco
import numpy as np
import pytest
import torch

from picklebot_mj import ball

P = ball.AeroParams()
Q_PER_V2 = 0.5 * P.air_density * math.pi * P.radius**2


def f(v, w):
    return ball.aero_force(torch.tensor(v, dtype=torch.float64), torch.tensor(w, dtype=torch.float64)).numpy()


def test_no_force_below_min_speed():
    assert np.allclose(f([0.0, 0.0, 0.0], [0.0, 50.0, 0.0]), 0.0)
    assert np.allclose(f([0.005, 0.0, 0.0], [0.0, 50.0, 0.0]), 0.0)


def test_drag_magnitude_and_direction():
    force = f([10.0, 0.0, 0.0], [0.0, 0.0, 0.0])
    expected = -Q_PER_V2 * 100.0 * P.drag_coefficient  # ~0.0777 N
    assert force == pytest.approx([expected, 0.0, 0.0])


@pytest.mark.parametrize("spin,sign", [(+1, -1), (-1, +1)])
def test_topspin_dives_backspin_floats(spin, sign):
    # Ball moving +x; omega = +y is topspin (top surface moves forward).
    force = f([10.0, 0.0, 0.0], [0.0, spin * 100.0, 0.0])
    s = P.radius * 100.0 / 10.0
    cl = min(P.max_lift_coefficient, P.lift_coefficient_slope * s)
    assert force[2] == pytest.approx(sign * Q_PER_V2 * 100.0 * cl)
    assert force[1] == pytest.approx(0.0, abs=1e-12)


def test_sidespin_curves_and_lift_is_capped():
    force = f([10.0, 0.0, 0.0], [0.0, 0.0, 1000.0])  # spin parameter 3.7 -> capped
    assert force[1] > 0  # omega_z x v_x = +y
    assert force[1] == pytest.approx(Q_PER_V2 * 100.0 * P.max_lift_coefficient)


def test_spin_parallel_to_velocity_gives_no_lift():
    force = f([10.0, 0.0, 0.0], [300.0, 0.0, 0.0])
    assert force[1:] == pytest.approx([0.0, 0.0], abs=1e-12)


def test_batched_matches_single():
    v = torch.randn(64, 3, dtype=torch.float64) * 10
    w = torch.randn(64, 3, dtype=torch.float64) * 100
    batched = ball.aero_force(v, w)
    single = torch.stack([ball.aero_force(v[i], w[i]) for i in range(64)])
    assert torch.allclose(batched, single)


def _simulate(pos, vel, angvel, duration, dt, integrator):
    spec = mujoco.MjSpec()
    spec.option.timestep = dt
    spec.option.integrator = integrator
    b = ball.add_ball(spec.worldbody, pos=pos)
    m = spec.compile()
    d = mujoco.MjData(m)
    bid = m.body(b.name).id
    d.qvel[0:3] = vel
    # Free-joint angular velocity is expressed in the body frame (identity at start).
    d.qvel[3:6] = angvel
    res = np.zeros(6)
    for _ in range(int(round(duration / dt))):
        mujoco.mj_forward(m, d)
        mujoco.mj_objectVelocity(m, d, mujoco.mjtObj.mjOBJ_BODY, bid, res, 0)
        w_world, v_world = res[:3].copy(), res[3:].copy()
        d.xfrc_applied[bid] = ball.ball_wrench(torch.tensor(v_world), torch.tensor(w_world)).numpy()
        mujoco.mj_step(m, d)
    mujoco.mj_forward(m, d)
    mujoco.mj_objectVelocity(m, d, mujoco.mjtObj.mjOBJ_BODY, bid, res, 0)
    return d.qpos[0:3].copy(), res[3:].copy(), res[:3].copy(), m


def test_ball_com_is_at_sphere_center():
    spec = mujoco.MjSpec()
    ball.add_ball(spec.worldbody, pos=[1.0, 2.0, 3.0])
    m = spec.compile()
    bid = m.body("ball").id
    assert np.allclose(m.body_ipos[bid], 0.0)
    assert np.allclose(m.body_inertia[bid], ball.BALL_INERTIA)
    assert m.body_mass[bid] == pytest.approx(ball.BALL_MASS)


CASES = {
    "flat-drive": ([0, 0, 1.0], [15.0, 0.0, 3.0], [0.0, 0.0, 0.0]),
    "topspin-drive": ([0, 0, 1.0], [15.0, 0.0, 3.0], [0.0, 150.0, 0.0]),
    "backspin-dink": ([0, 0, 1.0], [6.0, 0.0, 4.0], [0.0, -120.0, 0.0]),
    "sidespin": ([0, 0, 1.0], [12.0, 1.0, 4.0], [0.0, 0.0, 150.0]),
    "lob": ([0, 0, 1.0], [8.0, 0.0, 9.0], [0.0, 40.0, 0.0]),
}


# MuJoCo's integrators are first order in dt here: expect ~0.5*g*dt*T plus drag terms,
# i.e. ~3 cm at 5 ms and ~6 mm at 1 ms after 1 s of flight.
@pytest.mark.parametrize("dt,tol", [(0.005, 0.04), (0.001, 0.008)])
@pytest.mark.parametrize("case", list(CASES))
def test_mujoco_flight_matches_reference(case, dt, tol):
    pos, vel, angvel = CASES[case]
    duration = 1.0
    ref_x, ref_v, ref_w = ball.reference_flight(pos, vel, angvel, duration)
    x, v, w, m = _simulate(pos, vel, angvel, duration, dt, mujoco.mjtIntegrator.mjINT_IMPLICITFAST)
    assert m.body("ball").mass[0] == pytest.approx(ball.BALL_MASS)
    err = np.linalg.norm(x - ref_x.numpy())
    assert err < tol, f"{case} dt={dt}: position error {err:.4f} m"
    assert np.linalg.norm(v - ref_v.numpy()) < 10 * tol
    assert np.allclose(w, ref_w.numpy(), rtol=1e-3, atol=1e-3)


def test_flight_error_converges_first_order():
    pos, vel, angvel = CASES["topspin-drive"]
    ref_x, _, _ = ball.reference_flight(pos, vel, angvel, 1.0)
    errs = [np.linalg.norm(_simulate(pos, vel, angvel, 1.0, dt, mujoco.mjtIntegrator.mjINT_IMPLICITFAST)[0]
                           - ref_x.numpy()) for dt in (0.004, 0.002, 0.001)]
    assert 1.6 < errs[0] / errs[1] < 2.4 and 1.6 < errs[1] / errs[2] < 2.4, errs


def test_spin_changes_trajectory_in_expected_direction():
    pos, vel = [0, 0, 1.0], [15.0, 0.0, 3.0]
    flat, _, _ = ball.reference_flight(pos, vel, [0, 0, 0], 0.6)
    top, _, _ = ball.reference_flight(pos, vel, [0, 150.0, 0], 0.6)
    back, _, _ = ball.reference_flight(pos, vel, [0, -150.0, 0], 0.6)
    assert top[2] < flat[2] < back[2]
