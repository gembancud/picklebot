import sys
from pathlib import Path

import pytest
import torch

from picklebot_mj import ball
from picklebot_mj.ball_sim import BallParams, BallSim, BallState, energy, sphere_impulse

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from calibrate_analytic_cor import drop_apex_top  # noqa: E402

P = BallParams()
R = P.radius


def state(pos, vel=None, spin=None, dtype=torch.float64, device="cpu"):
    pos = torch.as_tensor(pos, dtype=dtype, device=device).reshape(-1, 3)
    z = torch.zeros_like(pos)
    vel = z.clone() if vel is None else torch.as_tensor(vel, dtype=dtype, device=device).reshape(-1, 3)
    spin = z.clone() if spin is None else torch.as_tensor(spin, dtype=dtype, device=device).reshape(-1, 3)
    return BallState(pos.clone(), vel.clone(), spin.clone())


def first_bounce(s, dt=0.005, substeps=10, max_t=2.0):
    """Run until each ball's first court contact; return (state just before, state just after)."""
    sim = BallSim(P)
    before = s.clone()
    for _ in range(int(max_t / dt)):
        prev = s.clone()
        s, ev = sim.step(s, dt, substeps)
        if bool(ev.court_contact.all()):
            return prev, s
    raise AssertionError("no bounce")


def test_official_drop_in_band():
    top = drop_apex_top(P.court_cor).item()
    assert 0.762 <= top <= 0.864 and top == pytest.approx(0.813, abs=1e-3)


@pytest.mark.parametrize("substeps", [1, 4, 10])
def test_drop_is_phase_independent(substeps):
    # The exact sweep that native MuJoCo contacts failed (COR 0.1-2.9), plus random sub-mm phases.
    heights = torch.cat([torch.linspace(1.95, 2.05, 21, dtype=torch.float64),
                         1.981 + torch.rand(32, dtype=torch.float64, generator=torch.Generator().manual_seed(0)) * 0.01])
    tops = drop_apex_top(P.court_cor, heights, substeps=substeps)
    # Apex scales with drop height; normalise by the height to compare phases.
    ratio = (tops - 2 * R) / heights
    spread = (ratio.max() - ratio.min()).item()
    assert spread < 2e-3, spread
    assert ((tops >= 0.735) & (tops <= 0.90)).all()  # heights differ by +-5 cm


def test_official_drop_insensitive_to_step_size():
    tops = [drop_apex_top(P.court_cor, substeps=k, dt=dt).item()
            for dt, k in [(0.005, 10), (0.005, 2), (0.002, 1), (0.02, 20)]]
    assert max(tops) - min(tops) < 2e-3, tops


@pytest.mark.parametrize("height", [0.3, 1.0, 2.0, 3.0])
def test_cor_constant_across_heights(height):
    # Velocities at the 1 ms step ends straddling the contact.
    s = state([-3.0, 1.0, height + R])
    sim = BallSim(P)
    vin = vout = None
    for _ in range(4000):
        prev = s.clone()
        s, ev = sim.step(s, 0.001, 1)
        if bool(ev.court_contact.all()):
            vin, vout = prev.vel[0, 2].item(), s.vel[0, 2].item()
            break
    assert vout / -vin == pytest.approx(P.court_cor, abs=0.01)


def test_no_energy_gain_random_impacts():
    g = torch.Generator().manual_seed(1)
    n = 4096
    v = (torch.rand(n, 3, generator=g, dtype=torch.float64) - 0.5) * torch.tensor([30.0, 30.0, 0.0], dtype=torch.float64)
    v[:, 2] = -torch.rand(n, generator=g, dtype=torch.float64) * 15 - 0.1
    w = (torch.rand(n, 3, generator=g, dtype=torch.float64) - 0.5) * 600
    n_hat = torch.tensor([0.0, 0.0, 1.0], dtype=torch.float64).expand(n, 3)
    v2, w2, j = sphere_impulse(v, w, n_hat, torch.zeros_like(v), P.court_cor, P.court_friction, P)
    e0 = 0.5 * P.mass * (v**2).sum(-1) + 0.5 * P.inertia * (w**2).sum(-1)
    e1 = 0.5 * P.mass * (v2**2).sum(-1) + 0.5 * P.inertia * (w2**2).sum(-1)
    assert (e1 <= e0 + 1e-9).all()
    assert (v2[:, 2] > 0).all()
    assert (j[:, 2] > 0).all()
    # Friction impulse never exceeds the Coulomb cone.
    assert (j[:, :2].norm(dim=-1) <= P.court_friction * j[:, 2] + 1e-12).all()


def test_full_flight_energy_never_increases_through_bounces():
    sim = BallSim(P)
    s = state([-6.0, 0, 1.5 + R], [6.0, 1.0, 2.0], [10.0, -80.0, 30.0])
    e_prev = energy(s, P)
    for _ in range(600):
        s, _ = sim.step(s, 0.005, 10)
        e = energy(s, P)
        assert (e <= e_prev + 1e-9).all()
        e_prev = e


def test_angled_bounce_slows_and_gains_topspin():
    prev, after = first_bounce(state([-5, 0, R + 0.05], [8.0, 0.0, -6.0]))
    assert 0 < after.vel[0, 0] < prev.vel[0, 0]
    assert after.vel[0, 2] > 0
    assert after.spin[0, 1] > 0  # moving +x -> topspin is +y


def _bounce(v, w):
    v = torch.tensor([v], dtype=torch.float64)
    w = torch.tensor([w], dtype=torch.float64)
    n = torch.tensor([[0.0, 0.0, 1.0]], dtype=torch.float64)
    return sphere_impulse(v, w, n, torch.zeros_like(v), P.court_cor, P.court_friction, P)


def test_spin_changes_bounce():
    # Fast skid: plain and backspin both slide throughout, so friction removes the same speed;
    # topspin has little slip and keeps its pace.
    plain, _, _ = _bounce([6.0, 0.0, -5.0], [0.0, 0.0, 0.0])
    back, _, _ = _bounce([6.0, 0.0, -5.0], [0.0, -150.0, 0.0])
    top, _, _ = _bounce([6.0, 0.0, -5.0], [0.0, 150.0, 0.0])
    assert back[0, 0] == pytest.approx(plain[0, 0]) and top[0, 0] > plain[0, 0] + 1.0
    # Slow approach with heavy backspin: the ball checks up and comes back.
    plain, _, _ = _bounce([1.5, 0.0, -5.0], [0.0, 0.0, 0.0])
    back, w_back, _ = _bounce([1.5, 0.0, -5.0], [0.0, -150.0, 0.0])
    assert back[0, 0] < 0 < plain[0, 0]
    assert -150.0 < w_back[0, 1] < 0  # friction reduces the backspin


def test_rolling_ball_keeps_rolling_without_slip_change():
    # A ball already rolling (u = 0) receives no tangential impulse.
    v = torch.tensor([[3.0, 0.0, -2.0]], dtype=torch.float64)
    w = torch.tensor([[0.0, 3.0 / R, 0.0]], dtype=torch.float64)  # rolling in +x
    n = torch.tensor([[0.0, 0.0, 1.0]], dtype=torch.float64)
    v2, w2, j = sphere_impulse(v, w, n, torch.zeros_like(v), P.court_cor, P.court_friction, P)
    assert j[0, :2].abs().max() < 1e-12 and v2[0, 0] == pytest.approx(3.0)


def test_ball_comes_to_rest_without_sinking():
    sim = BallSim(P)
    s = state([-3.0, 1.0, 1.0 + R])
    zmin = 1.0
    for _ in range(int(6.0 / 0.005)):
        s, _ = sim.step(s, 0.005, 10)
        zmin = min(zmin, s.pos[0, 2].item())
    assert zmin >= R - 1e-9
    assert s.pos[0, 2].item() == pytest.approx(R, abs=1e-6) and abs(s.vel[0, 2].item()) < 1e-6


def test_flight_between_bounces_matches_reference():
    s = state([-6.0, 0, 1.0], [15.0, 0.0, 3.0], [0.0, 150.0, 0.0])
    sim = BallSim(P)
    for _ in range(int(0.3 / 0.005)):
        s, ev = sim.step(s, 0.005, 10)
        assert not ev.court_contact.any()
    rx, rv, rw = ball.reference_flight([-6.0, 0, 1.0], [15.0, 0.0, 3.0], [0.0, 150.0, 0.0], 0.3)
    assert torch.allclose(s.pos[0], rx, atol=1e-6) and torch.allclose(s.vel[0], rv, atol=1e-5)


def test_batched_equals_single_and_deterministic():
    g = torch.Generator().manual_seed(2)
    n = 64
    pos = torch.rand(n, 3, generator=g, dtype=torch.float64) * torch.tensor([10, 6, 2], dtype=torch.float64) + torch.tensor([-5, -3, 0.2], dtype=torch.float64)
    vel = (torch.rand(n, 3, generator=g, dtype=torch.float64) - 0.5) * 20
    spin = (torch.rand(n, 3, generator=g, dtype=torch.float64) - 0.5) * 300
    sim = BallSim(P)
    a = BallState(pos.clone(), vel.clone(), spin.clone())
    b = BallState(pos.clone(), vel.clone(), spin.clone())
    for _ in range(200):
        a, _ = sim.step(a, 0.005, 10)
        b, _ = sim.step(b, 0.005, 10)
    assert torch.equal(a.pos, b.pos)
    for i in (0, 17, 63):
        c = BallState(pos[i:i + 1].clone(), vel[i:i + 1].clone(), spin[i:i + 1].clone())
        for _ in range(200):
            c, _ = sim.step(c, 0.005, 10)
        assert torch.allclose(a.pos[i], c.pos[0], atol=1e-12)


@pytest.mark.skipif(not torch.cuda.is_available(), reason="no CUDA")
def test_cuda_float32_matches_cpu_float64():
    heights = torch.linspace(1.95, 2.05, 64)
    gpu = drop_apex_top(P.court_cor, heights.cuda(), dtype=torch.float32, device="cuda").cpu().double()
    cpu = drop_apex_top(P.court_cor, heights.double())
    assert (gpu - cpu).abs().max() < 2e-3
