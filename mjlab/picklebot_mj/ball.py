"""Pickleball ball body and aerodynamics (drag, Magnus lift, spin decay).

The force model is a port of Unity AerodynamicModelV1 with SimulationConfigV1
defaults. It is written in torch, batched over environments, so a task can
apply it every physics step through `xfrc_applied`. `reference_flight` is an
RK4 port of FlightReferenceIntegratorV1, used only to validate simulated flight.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import mujoco
import torch

BALL_MASS = 0.024  # kg (Unity CourtGeometryV1)
BALL_RADIUS = 0.037  # m
# A pickleball is a thin plastic shell, so use a hollow-sphere inertia: (2/3) m r^2.
BALL_INERTIA = (2.0 / 3.0) * BALL_MASS * BALL_RADIUS**2
GRAVITY = 9.81


@dataclass(frozen=True)
class AeroParams:
    """Unity SimulationConfigV1 defaults."""

    air_density: float = 1.204
    drag_coefficient: float = 0.30
    lift_coefficient_slope: float = 0.195
    max_lift_coefficient: float = 0.25
    min_speed: float = 0.01
    angular_decay_rate: float = 0.05  # 1/s
    radius: float = BALL_RADIUS


def aero_force(vel: torch.Tensor, angvel: torch.Tensor, p: AeroParams = AeroParams(),
               wind: torch.Tensor | None = None) -> torch.Tensor:
    """Drag + Magnus lift force (N), shape (..., 3). Inputs in world frame."""
    rel = vel if wind is None else vel - wind
    speed = rel.norm(dim=-1, keepdim=True)
    active = speed > p.min_speed
    safe_speed = speed.clamp_min(p.min_speed)
    direction = rel / safe_speed
    q = 0.5 * p.air_density * math.pi * p.radius**2 * safe_speed**2
    drag = -q * p.drag_coefficient * direction

    w_perp = angvel - (angvel * direction).sum(-1, keepdim=True) * direction
    w_perp_mag = w_perp.norm(dim=-1, keepdim=True)
    spin_param = p.radius * w_perp_mag / safe_speed
    cl = torch.clamp(p.lift_coefficient_slope * spin_param, max=p.max_lift_coefficient)
    lift_dir = torch.cross(w_perp, rel, dim=-1)
    lift_dir = lift_dir / lift_dir.norm(dim=-1, keepdim=True).clamp_min(1e-12)
    has_spin = w_perp_mag > 1e-9
    lift = torch.where(has_spin, q * cl * lift_dir, torch.zeros_like(lift_dir))
    return torch.where(active, drag + lift, torch.zeros_like(drag))


def spin_decay_torque(angvel: torch.Tensor, p: AeroParams = AeroParams(),
                      inertia: float = BALL_INERTIA) -> torch.Tensor:
    """Torque giving d(omega)/dt = -k * omega for a sphere with scalar inertia."""
    return -p.angular_decay_rate * inertia * angvel


def ball_wrench(vel: torch.Tensor, angvel: torch.Tensor, p: AeroParams = AeroParams()) -> torch.Tensor:
    """(..., 6) force+torque for MuJoCo `xfrc_applied` (applied at the body CoM)."""
    return torch.cat([aero_force(vel, angvel, p), spin_decay_torque(angvel, p)], dim=-1)


def reference_flight(pos, vel, angvel, duration: float, max_step: float = 1e-4,
                     p: AeroParams = AeroParams(), mass: float = BALL_MASS):
    """RK4 flight (no contacts) in float64. Returns (pos, vel, angvel) tensors."""
    x = torch.as_tensor(pos, dtype=torch.float64).clone()
    v = torch.as_tensor(vel, dtype=torch.float64).clone()
    w = torch.as_tensor(angvel, dtype=torch.float64).clone()
    g = torch.tensor([0.0, 0.0, -GRAVITY], dtype=torch.float64)

    def deriv(x, v, w):
        return v, g + aero_force(v, w, p) / mass, -p.angular_decay_rate * w

    t = 0.0
    while t < duration - 1e-12:
        h = min(max_step, duration - t)
        k1 = deriv(x, v, w)
        k2 = deriv(x + 0.5 * h * k1[0], v + 0.5 * h * k1[1], w + 0.5 * h * k1[2])
        k3 = deriv(x + 0.5 * h * k2[0], v + 0.5 * h * k2[1], w + 0.5 * h * k2[2])
        k4 = deriv(x + h * k3[0], v + h * k3[1], w + h * k3[2])
        x = x + h / 6 * (k1[0] + 2 * k2[0] + 2 * k3[0] + k4[0])
        v = v + h / 6 * (k1[1] + 2 * k2[1] + 2 * k3[1] + k4[1])
        w = w + h / 6 * (k1[2] + 2 * k2[2] + 2 * k3[2] + k4[2])
        t += h
    return x, v, w


def add_ball(parent: mujoco.MjsBody, name: str = "ball", pos=(0.0, 0.0, 1.0)) -> mujoco.MjsBody:
    """Free ball body with explicit hollow-sphere inertia."""
    body = parent.add_body(name=name, pos=list(pos))
    body.add_freejoint(name=f"{name}_free")
    body.explicitinertial = True
    # Set the CoM frame explicitly: left unset, MjSpec gave ipos = body pos here,
    # putting the centre of mass a body-offset away from the sphere.
    body.ipos = [0.0, 0.0, 0.0]
    body.iquat = [1.0, 0.0, 0.0, 0.0]
    body.mass = BALL_MASS
    body.inertia = [BALL_INERTIA] * 3
    body.add_geom(
        name=f"{name}_geom",
        type=mujoco.mjtGeom.mjGEOM_SPHERE,
        size=[BALL_RADIUS, 0.0, 0.0],
        rgba=[0.95, 0.85, 0.1, 1.0],
    )
    return body
