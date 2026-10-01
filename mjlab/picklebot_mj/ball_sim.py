"""Analytic, batched ball simulation (decision D-039).

The ball is not a MuJoCo contact body. Its state (position, velocity, world
angular velocity) lives in torch tensors, batched over environments, and is
advanced here:

* flight: RK4 sub-steps of gravity + `ball.aero_force` + spin decay;
* court: swept sphere-vs-plane (z = 0) test inside each sub-step. At the time of
  impact an impulse is applied, then the rest of the sub-step continues with
  the new velocity. The result is independent of where the impact falls in
  the step, which native MuJoCo contacts were not (results/stage1-bounce.md).

Impulse model (rigid sphere, Coulomb friction):
  normal:     v_n' = -e * v_n          (e only applied above REST_SPEED)
  tangential: the impulse that would stop contact-point slip is
              J_t* = -m u / (1 + 1/k_I)   with k_I = I / (m r^2),
              capped at mu * J_n (sliding) — this gives the slip/roll transition.
  spin:       d_omega = (r_c x J_t) / I  with r_c = -r n.
"""

from __future__ import annotations

from dataclasses import dataclass

import torch

from picklebot_mj import ball
from picklebot_mj.ball import AeroParams, aero_force

# Normal COR for the court, calibrated with aerodynamics on so the official drop test
# (1.981 m, ball-bottom datum) peaks at the band centre (ball top 0.813 m; band
# 0.762-0.864). This is a provisional bound; no acrylic-court reference exists yet.
COURT_COR = 0.6381  # scripts/calibrate_analytic_cor.py, 2026-10-02
COURT_FRICTION = 0.2  # Unity average of ball 0.1 / court 0.3
REST_SPEED = 0.05  # m/s: below this normal approach speed the bounce is fully inelastic


@dataclass
class BallParams:
    mass: float = ball.BALL_MASS
    radius: float = ball.BALL_RADIUS
    inertia: float = ball.BALL_INERTIA
    gravity: float = ball.GRAVITY
    court_cor: float = COURT_COR
    court_friction: float = COURT_FRICTION
    aero: AeroParams = AeroParams()


@dataclass
class BallState:
    pos: torch.Tensor  # (N, 3)
    vel: torch.Tensor  # (N, 3)
    spin: torch.Tensor  # (N, 3) world-frame angular velocity

    def clone(self) -> "BallState":
        return BallState(self.pos.clone(), self.vel.clone(), self.spin.clone())


def _deriv(v, w, p: BallParams):
    g = torch.zeros_like(v)
    g[..., 2] = -p.gravity
    return v, g + aero_force(v, w, p.aero) / p.mass, -p.aero.angular_decay_rate * w


def flight_rk4(x, v, w, h, p: BallParams):
    """One RK4 step of length h (scalar or (N, 1) tensor) without contacts."""
    k1 = _deriv(v, w, p)
    k2 = _deriv(v + 0.5 * h * k1[1], w + 0.5 * h * k1[2], p)
    k3 = _deriv(v + 0.5 * h * k2[1], w + 0.5 * h * k2[2], p)
    k4 = _deriv(v + h * k3[1], w + h * k3[2], p)
    x = x + h / 6 * (k1[0] + 2 * k2[0] + 2 * k3[0] + k4[0])
    v = v + h / 6 * (k1[1] + 2 * k2[1] + 2 * k3[1] + k4[1])
    w = w + h / 6 * (k1[2] + 2 * k2[2] + 2 * k3[2] + k4[2])
    return x, v, w


def sphere_impulse(v, w, n, surface_vel, cor, mu, p: BallParams):
    """Velocity change for a sphere hitting a surface with outward normal n.

    surface_vel is the velocity of the surface at the contact point. Returns
    (v', w', J): the new ball velocity, spin and the impulse on the ball.
    """
    rel = v - surface_vel
    vn = (rel * n).sum(-1, keepdim=True)  # < 0 when approaching
    e = torch.where(-vn > REST_SPEED, torch.full_like(vn, cor), torch.zeros_like(vn))
    jn = -(1.0 + e) * p.mass * vn.clamp(max=0.0)  # >= 0
    r_c = -p.radius * n
    u = rel - vn * n + torch.cross(w, r_c, dim=-1)  # contact-point slip velocity
    k_i = p.inertia / (p.mass * p.radius**2)
    jt_stick = -p.mass * u / (1.0 + 1.0 / k_i)
    jt_mag = jt_stick.norm(dim=-1, keepdim=True)
    cap = mu * jn
    jt = torch.where(jt_mag > cap, jt_stick * (cap / jt_mag.clamp_min(1e-12)), jt_stick)
    j = jn * n + jt
    return v + j / p.mass, w + torch.cross(r_c, jt, dim=-1) / p.inertia, j


@dataclass
class StepEvents:
    court_contact: torch.Tensor  # (N,) bool: any court contact this step
    court_point: torch.Tensor  # (N, 3) first court contact point this step (nan if none)


class BallSim:
    def __init__(self, params: BallParams | None = None):
        self.p = params or BallParams()

    def step(self, s: BallState, dt: float, substeps: int = 10) -> tuple[BallState, StepEvents]:
        p = self.p
        h = dt / substeps
        x, v, w = s.pos, s.vel, s.spin
        n = torch.zeros_like(x)
        n[..., 2] = 1.0
        contact = torch.zeros(x.shape[0], dtype=torch.bool, device=x.device)
        point = torch.full_like(x, float("nan"))
        for _ in range(substeps):
            x1, v1, w1 = flight_rk4(x, v, w, h, p)
            hit = (x1[..., 2] < p.radius) & (v1[..., 2] < 0)
            if bool(hit.any()):
                # Time of impact inside the sub-step by linear interpolation of height.
                z0, z1 = x[..., 2], x1[..., 2]
                frac = ((z0 - p.radius) / (z0 - z1).clamp_min(1e-12)).clamp(0.0, 1.0)
                frac = torch.where(z0 < p.radius, torch.zeros_like(frac), frac).unsqueeze(-1)
                xc, vc, wc = flight_rk4(x, v, w, frac * h, p)
                xc = xc.clone()
                xc[..., 2] = p.radius
                vb, wb, _ = sphere_impulse(vc, wc, n, torch.zeros_like(vc), p.court_cor, p.court_friction, p)
                xr, vr, wr = flight_rk4(xc, vb, wb, (1.0 - frac) * h, p)
                # Never end a sub-step below the court.
                xr = xr.clone()
                xr[..., 2] = xr[..., 2].clamp_min(p.radius)
                m3 = hit.unsqueeze(-1)
                first = hit & ~contact
                point = torch.where(first.unsqueeze(-1), xc - p.radius * n, point)
                contact = contact | hit
                x1, v1, w1 = torch.where(m3, xr, x1), torch.where(m3, vr, v1), torch.where(m3, wr, w1)
            # Resting ball: hold on the surface without sinking.
            resting = (x1[..., 2] <= p.radius + 1e-6) & (v1[..., 2].abs() <= REST_SPEED)
            if bool(resting.any()):
                x1 = x1.clone(); v1 = v1.clone()
                x1[..., 2] = torch.where(resting, torch.full_like(x1[..., 2], p.radius), x1[..., 2])
                v1[..., 2] = torch.where(resting, torch.zeros_like(v1[..., 2]), v1[..., 2])
            x, v, w = x1, v1, w1
        return BallState(x, v, w), StepEvents(contact, point)


def energy(s: BallState, p: BallParams) -> torch.Tensor:
    """Total mechanical energy per ball (translational + rotational + potential, ball centre)."""
    return (0.5 * p.mass * (s.vel**2).sum(-1) + 0.5 * p.inertia * (s.spin**2).sum(-1)
            + p.mass * p.gravity * s.pos[..., 2])
