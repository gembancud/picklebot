import math

import pytest
import torch

from picklebot_mj.ball import AeroParams
from picklebot_mj.ball_sim import (PADDLE_COR, PADDLE_HALF, BallParams, BallSim, BallState, PaddleState,
                                   _rotvec_to_matrix)

# Aerodynamics off isolates the contact model; gravity remains.
NOAERO = BallParams(aero=AeroParams(drag_coefficient=0.0, lift_coefficient_slope=0.0, angular_decay_rate=0.0))
R = NOAERO.radius
D = torch.float64


def t(x):
    return torch.as_tensor(x, dtype=D)


def paddle(pos, rotvec=(0.0, 0.0, 0.0), vel=(0.0, 0.0, 0.0), ang=(0.0, 0.0, 0.0), n=1):
    rot = _rotvec_to_matrix(t(rotvec).reshape(1, 3)).expand(n, 3, 3).clone()
    return PaddleState(t(pos).reshape(1, 3).expand(n, 3).clone(), rot,
                       t(vel).reshape(1, 3).expand(n, 3).clone(), t(ang).reshape(1, 3).expand(n, 3).clone())


def ball(pos, vel, spin=None):
    pos = t(pos).reshape(-1, 3)
    return BallState(pos.clone(), t(vel).reshape(-1, 3).clone(),
                     torch.zeros_like(pos) if spin is None else t(spin).reshape(-1, 3).clone())


def run(s, pd, steps, dt=0.005, substeps=1, params=NOAERO):
    sim = BallSim(params)
    hit = torch.zeros(s.pos.shape[0], dtype=torch.bool)
    J = torch.zeros_like(s.pos)
    for _ in range(steps):
        s, ev = sim.step(s, dt, substeps, pd)
        hit |= ev.paddle_contact
        J += ev.paddle_impulse
        # Advance the paddle pose with its constant velocity.
        pos, rot = pd.pos + pd.lin_vel * dt, _rotvec_to_matrix(pd.ang_vel * dt) @ pd.rot
        pd = PaddleState(pos, rot, pd.lin_vel, pd.ang_vel)
    return s, hit, J


@pytest.mark.parametrize("speed", [5.0, 10.0, 20.0, 30.0])
def test_pbcor_surrogate_on_fixed_paddle(speed):
    # Face-up fixed paddle; ball fired straight down onto the face centre.
    pd = paddle([0, 0, 1.0])
    sim, dt = BallSim(NOAERO), 0.001
    s = ball([0, 0, 1.0 + 0.1], [0, 0, -speed])
    for _ in range(200):
        prev = s
        s, ev = sim.step(s, dt, 1, pd)
        if ev.paddle_contact.all():
            break
    assert ev.paddle_contact.all()
    # Velocities at the 1 ms step ends straddling the impact; gravity contributes < 0.01 m/s.
    ratio = s.vel[0, 2].item() / -prev.vel[0, 2].item()
    assert ratio == pytest.approx(PADDLE_COR, abs=0.02)
    assert ratio <= 0.43


@pytest.mark.parametrize("dt", [0.005, 0.02])
def test_no_tunnelling_fast_swing(dt):
    # Ball nearly at rest; paddle (normal +x) swings through it at 30 m/s. Sweep 40 phases.
    n = 40
    offsets = torch.linspace(0.0, 30.0 * dt, n, dtype=D)
    s = BallState(torch.stack([0.3 + offsets, torch.zeros(n, dtype=D), torch.full((n,), 1.0, dtype=D)], -1),
                  torch.zeros(n, 3, dtype=D), torch.zeros(n, 3, dtype=D))
    pd = paddle([0.0, 0, 1.0], rotvec=(0.0, math.pi / 2, 0.0), vel=(30.0, 0, 0), n=n)  # face normal -> +x
    s, hit, _ = run(s, pd, steps=int(0.04 / dt) + 2, dt=dt)
    assert hit.all()
    # Kinematic paddle: ball leaves at (1 + e) * 30 m/s along +x.
    assert torch.allclose(s.vel[:, 0], torch.full((n,), (1 + PADDLE_COR) * 30.0, dtype=D), atol=0.2)


def test_face_angle_steers_outgoing_direction():
    for tilt, sign in ((0.3, +1), (-0.3, -1)):
        pd = paddle([0, 0, 1.0], rotvec=(0.0, tilt, 0.0))  # normal tilted toward +-x
        s, hit, _ = run(ball([0, 0, 1.3], [0, 0, -10.0]), pd, steps=12)
        assert hit.all()
        assert sign * s.vel[0, 0] > 1.0


def test_momentum_conserved_with_reaction_impulse():
    pd = paddle([0, 0, 1.0], rotvec=(0.2, -0.1, 0.0), vel=(0.0, 0.0, 3.0))
    s0 = ball([0.01, 0.02, 1.25], [0.5, -0.3, -12.0], [20.0, -40.0, 5.0])
    dt, steps = 0.005, 8
    s, hit, J_paddle = run(s0, pd, steps=steps, dt=dt)
    assert hit.all()
    dp_ball = NOAERO.mass * (s.vel - s0.vel)
    gravity = torch.tensor([0, 0, -NOAERO.mass * NOAERO.gravity * dt * steps], dtype=D)
    assert torch.allclose(dp_ball - gravity, -J_paddle, atol=1e-9)


def test_ball_beside_paddle_misses():
    pd = paddle([0, 0, 1.0])
    x_off = PADDLE_HALF[0] + R + 0.005
    s, hit, _ = run(ball([x_off, 0, 1.2], [0, 0, -10.0]), pd, steps=10)
    assert not hit.any()


def test_brushing_up_creates_topspin():
    # Face normal +x, paddle moving up (+z) and toward the ball (+x); ball arriving along -x.
    pd = paddle([0, 0, 1.0], rotvec=(0.0, math.pi / 2, 0.0), vel=(5.0, 0.0, 6.0))
    s, hit, _ = run(ball([0.25, 0, 1.0], [-10.0, 0, 0]), pd, steps=8)
    assert hit.all()
    assert s.vel[0, 0] > 0 and s.vel[0, 2] > 0
    assert s.spin[0, 1] > 50.0  # moving +x with +y spin = topspin


def test_no_energy_gain_in_paddle_frame_random():
    g = torch.Generator().manual_seed(5)
    n = 2048
    rv = (torch.rand(n, 3, generator=g, dtype=D) - 0.5) * 2.0
    rot = _rotvec_to_matrix(rv)
    normal = rot[..., :, 2]
    # Paddle at rest; ball starts 0.1 m off the face along the normal, moving toward it.
    centre = torch.zeros(n, 3, dtype=D)
    centre[:, 2] = 1.0
    inplane = (rot @ ((torch.rand(n, 3, generator=g, dtype=D) - 0.5) * torch.tensor([0.15, 0.2, 0.0], dtype=D)).unsqueeze(-1)).squeeze(-1)
    pos = centre + inplane + 0.1 * normal
    speed = torch.rand(n, 1, generator=g, dtype=D) * 25 + 1
    tang = (torch.rand(n, 3, generator=g, dtype=D) - 0.5) * 6
    vel = -speed * normal + tang - (tang * normal).sum(-1, keepdim=True) * normal
    spin = (torch.rand(n, 3, generator=g, dtype=D) - 0.5) * 600
    s0 = BallState(pos, vel, spin)
    pd = PaddleState(centre, rot, torch.zeros(n, 3, dtype=D), torch.zeros(n, 3, dtype=D))
    s, hit, _ = run(s0, pd, steps=10)
    ke = lambda st: 0.5 * NOAERO.mass * (st.vel**2).sum(-1) + 0.5 * NOAERO.inertia * (st.spin**2).sum(-1)
    pe = lambda st: NOAERO.mass * NOAERO.gravity * st.pos[:, 2]
    assert hit.float().mean() > 0.95
    # Depenetration can only move the ball out along the normal by < 0.5 r per sub-step; allow that PE.
    slack = NOAERO.mass * NOAERO.gravity * 0.5 * R
    assert (ke(s) + pe(s) <= ke(s0) + pe(s0) + slack).all()
