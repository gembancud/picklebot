import pytest
import torch

from picklebot_mj import court
from picklebot_mj.ball_sim import BallParams, BallSim, BallState, energy

P = BallParams()
R = P.radius
T2 = court.NET_THICKNESS / 2


def state(pos, vel, spin=None):
    pos = torch.tensor(pos, dtype=torch.float64).reshape(-1, 3)
    vel = torch.tensor(vel, dtype=torch.float64).reshape(-1, 3)
    spin = torch.zeros_like(pos) if spin is None else torch.tensor(spin, dtype=torch.float64).reshape(-1, 3)
    return BallState(pos, vel, spin)


def run(s, duration, dt=0.005, substeps=1):
    sim = BallSim(P)
    xs, any_net, any_post = [s.pos.clone()], torch.zeros(s.pos.shape[0], dtype=torch.bool), torch.zeros(s.pos.shape[0], dtype=torch.bool)
    for _ in range(int(round(duration / dt))):
        s, ev = sim.step(s, dt, substeps)
        xs.append(s.pos.clone())
        any_net |= ev.net_contact
        any_post |= ev.post_contact
    return s, torch.stack(xs), any_net, any_post


@pytest.mark.parametrize("dt", [0.005, 0.02])
@pytest.mark.parametrize("speed", [12.0, 30.0])
def test_ball_into_net_is_stopped_at_any_step_size(dt, speed):
    ys = [0.0, 1.5, -2.9, 3.2]
    zs = [0.2, 0.5, 0.7]
    pos = [[-1.0, y, z] for y in ys for z in zs]
    s, xs, net, _ = run(state(pos, [[speed, 0.0, 0.0]] * len(pos)), duration=0.2, dt=dt)
    assert net.all()
    assert (xs[..., 0] <= -(T2 + R) + 1e-9).all(), xs[..., 0].max()
    assert (s.vel[:, 0] <= 0.0).all()
    assert (s.vel[:, 0].abs() < 0.3 * speed).all()


def test_ball_over_net_is_untouched():
    for y in (0.0, 2.0):
        top = court.net_height_at(y)
        s, xs, net, _ = run(state([-1.0, y, top + R + 0.10], [15.0, 0.0, 0.0]), duration=0.15)
        assert not net.any() and s.pos[0, 0] > 0.5


def test_net_cord_touch_deflects_without_energy_gain():
    # Ball whose bottom is 1 cm below the top of the net at the centre.
    z = court.NET_CENTER_HEIGHT + R - 0.01
    s0 = state([-0.5, 0.0, z], [8.0, 0.0, 0.0])
    e0 = energy(s0, P)
    sim = BallSim(P)
    s, hit_seen = s0, False
    for _ in range(40):
        s, ev = sim.step(s, 0.005, 1)
        hit_seen |= bool(ev.net_contact.any())
        if hit_seen:
            break
    assert hit_seen
    assert s.vel[0, 2] > 0  # pushed upward by the cord
    assert s.vel[0, 0] < 8.0
    assert energy(s, P) <= e0 + 1e-9


def test_ball_beyond_posts_is_untouched():
    y = court.HALF_NET_POST_SPAN + 2 * court.NET_POST_RADIUS + R + 0.02
    s, xs, net, post = run(state([-1.0, y, 0.5], [12.0, 0.0, 0.0]), duration=0.2)
    assert not net.any() and s.pos[0, 0] > 1.0


def test_ball_into_post_bounces_back():
    y = court.HALF_NET_POST_SPAN + court.NET_POST_RADIUS
    s, xs, net, post = run(state([-1.0, y, 0.5], [12.0, 0.0, 0.0]), duration=0.2)
    assert post.all()
    assert s.vel[0, 0] < 0
    assert (xs[:, 0, 0] <= -(court.NET_POST_RADIUS + R) + 1e-9).all()


def test_no_energy_gain_on_random_net_impacts():
    g = torch.Generator().manual_seed(3)
    n = 2048
    pos = torch.stack([torch.full((n,), -0.3, dtype=torch.float64),
                       (torch.rand(n, generator=g, dtype=torch.float64) - 0.5) * 7.0,
                       torch.rand(n, generator=g, dtype=torch.float64) * 1.0 + 0.05], dim=-1)
    vel = torch.stack([torch.rand(n, generator=g, dtype=torch.float64) * 25 + 2,
                       (torch.rand(n, generator=g, dtype=torch.float64) - 0.5) * 6,
                       (torch.rand(n, generator=g, dtype=torch.float64) - 0.5) * 6], dim=-1)
    spin = (torch.rand(n, 3, generator=g, dtype=torch.float64) - 0.5) * 400
    s = BallState(pos, vel, spin)
    sim = BallSim(P)
    e_prev = energy(s, P)
    for _ in range(40):
        s, _ = sim.step(s, 0.005, 1)
        e = energy(s, P)
        assert (e <= e_prev + 1e-9).all()
        e_prev = e


def test_adaptive_substeps():
    sim = BallSim(P)
    s = state([0, 0, 1], [30.0, 0, 0])
    k = sim.substeps_for(s, 0.005, 1)
    assert 30.0 * 0.005 / k <= 0.5 * R + 1e-12
