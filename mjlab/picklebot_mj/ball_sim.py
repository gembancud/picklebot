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

import math
from dataclasses import dataclass

import torch

from picklebot_mj import ball, court
from picklebot_mj.ball import AeroParams, aero_force

# Normal COR for the court, calibrated with aerodynamics on so the official drop test
# (1.981 m, ball-bottom datum) peaks at the band centre (ball top 0.813 m; band
# 0.762-0.864). This is a provisional bound; no acrylic-court reference exists yet.
COURT_COR = 0.6381  # scripts/calibrate_analytic_cor.py, 2026-10-02
COURT_FRICTION = 0.2  # Unity average of ball 0.1 / court 0.3
REST_SPEED = 0.05  # m/s: below this normal approach speed the bounce is fully inelastic
NET_COR = 0.10  # Unity NetRestitution
NET_FRICTION = 0.4  # Unity NetDynamicFriction
MAX_TRAVEL = 0.5  # max ball travel per sub-step, in radii (prevents tunnelling through the net)
# Paddle face: Unity CourtGeometryV1 width 0.2032 m, face length 0.4064 - 0.127 m, thickness 0.016 m.
PADDLE_HALF = (0.2032 / 2, (0.4064 - 0.127) / 2, 0.016 / 2)
# Normal COR against a rigid, kinematic paddle; this is the PBCoR surrogate (limit 0.43).
PADDLE_COR = 0.40  # Unity PaddleRestitution
PADDLE_FRICTION = 0.2  # Unity PaddleDynamicFriction
PADDLE_CORNER_RADIUS = 0.0254  # 1 in rounded face corners (Unity PaddleCornerRadius; drawn by g1_paddle)


@dataclass
class BallParams:
    mass: float = ball.BALL_MASS
    radius: float = ball.BALL_RADIUS
    inertia: float = ball.BALL_INERTIA
    gravity: float = ball.GRAVITY
    court_cor: float = COURT_COR
    court_friction: float = COURT_FRICTION
    net_cor: float = NET_COR
    net_friction: float = NET_FRICTION
    paddle_cor: float = PADDLE_COR
    paddle_friction: float = PADDLE_FRICTION
    paddle_corner_radius: float = 0.0  # 0 = square box face; tasks set PADDLE_CORNER_RADIUS
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


def net_closest(x: torch.Tensor):
    """Closest points on the net slab and the two posts to ball centres x.

    The net is a slab |x| <= t/2, |y| <= half post span, 0 <= z <= court.net_height_at(y).
    The tilt of its top edge (slope 0.017) is ignored for the normal. Posts are
    vertical cylinders. Returns (closest point (N, 3), is_post (N,) bool), taking
    whichever of net and post is nearer.
    """
    t2 = court.NET_THICKNESS / 2
    span = court.HALF_NET_POST_SPAN
    yq = x[..., 1].clamp(-span, span)
    top = court.NET_CENTER_HEIGHT + (court.NET_SIDELINE_HEIGHT - court.NET_CENTER_HEIGHT) / court.HALF_WIDTH * yq.abs()
    q_net = torch.stack([x[..., 0].clamp(-t2, t2), yq, x[..., 2].clamp(0.0, None).minimum(top)], dim=-1)
    # Posts at y = +-(span + r_post), on the near post side.
    side = torch.where(x[..., 1] >= 0, 1.0, -1.0).to(x.dtype)
    axis = torch.stack([torch.zeros_like(side), side * (span + court.NET_POST_RADIUS)], dim=-1)
    rel = x[..., :2] - axis
    rel_n = rel.norm(dim=-1, keepdim=True)
    radial = axis + rel * (court.NET_POST_RADIUS / rel_n.clamp_min(1e-12)).clamp(max=1.0)
    q_post = torch.cat([radial, x[..., 2:3].clamp(0.0, court.NET_SIDELINE_HEIGHT)], dim=-1)
    d_net = (x - q_net).norm(dim=-1)
    d_post = (x - q_post).norm(dim=-1)
    is_post = d_post < d_net
    return torch.where(is_post.unsqueeze(-1), q_post, q_net), is_post


@dataclass
class PaddleState:
    """Paddle face pose and velocity at the start of a step, per environment.

    pos: face-centre position (N, 3). rot: (N, 3, 3) world-from-paddle rotation; its
    columns are the face width axis, the length axis (toward the tip) and the face
    normal. lin_vel / ang_vel: world-frame velocity of the face centre and angular velocity.
    """

    pos: torch.Tensor
    rot: torch.Tensor
    lin_vel: torch.Tensor
    ang_vel: torch.Tensor


def _rotvec_to_matrix(rv: torch.Tensor) -> torch.Tensor:
    """Rodrigues: rotation vectors (N, 3) -> rotation matrices (N, 3, 3)."""
    theta = rv.norm(dim=-1, keepdim=True)
    k = rv / theta.clamp_min(1e-12)
    kx, ky, kz = k.unbind(-1)
    zero = torch.zeros_like(kx)
    K = torch.stack([zero, -kz, ky, kz, zero, -kx, -ky, kx, zero], dim=-1).reshape(-1, 3, 3)
    s, c = torch.sin(theta)[..., None], torch.cos(theta)[..., None]
    eye = torch.eye(3, dtype=rv.dtype, device=rv.device).expand_as(K)
    return eye + s * K + (1 - c) * (K @ K)


def paddle_at(pd: PaddleState, t: float | torch.Tensor):
    """Paddle pose after time t, assuming constant velocity over the step."""
    pos = pd.pos + pd.lin_vel * t
    rot = _rotvec_to_matrix(pd.ang_vel * t) @ pd.rot
    return pos, rot


@dataclass
class StepEvents:
    court_contact: torch.Tensor  # (N,) bool: any court contact this step
    court_point: torch.Tensor  # (N, 3) first court contact point this step (nan if none)
    net_contact: torch.Tensor  # (N,) bool: any net or post contact this step
    post_contact: torch.Tensor  # (N,) bool: any post contact this step
    paddle_contact: torch.Tensor | None = None  # (N,) bool
    paddle_point: torch.Tensor | None = None  # (N, 3) first paddle contact point (world)
    paddle_impulse: torch.Tensor | None = None  # (N, 3) total impulse ON THE PADDLE this step (reaction)
    paddle_angular_impulse: torch.Tensor | None = None  # (N, 3) about the paddle face centre, on the paddle


class BallSim:
    def __init__(self, params: BallParams | None = None):
        self.p = params or BallParams()
        self._consts: dict = {}

    def _const(self, name, values, like: torch.Tensor) -> torch.Tensor:
        """Small constant tensors cached per (device, dtype): no host-to-device copy per sub-step."""
        key = (name, like.device, like.dtype)
        if key not in self._consts:
            self._consts[key] = torch.tensor(values, dtype=like.dtype, device=like.device)
        return self._consts[key]

    def substeps_for(self, s: BallState, dt: float, substeps: int, paddle: PaddleState | None = None) -> int:
        """Raise the sub-step count so no ball moves more than MAX_TRAVEL * radius per sub-step,
        relative to the world or to the paddle (including paddle rotation at the face tip)."""
        if not s.vel.numel():
            return substeps
        speed = s.vel.norm(dim=-1)
        if paddle is not None:
            tip = math.hypot(PADDLE_HALF[0], PADDLE_HALF[1])
            speed = speed + paddle.lin_vel.norm(dim=-1) + paddle.ang_vel.norm(dim=-1) * tip
        return max(substeps, math.ceil(float(speed.max()) * dt / (MAX_TRAVEL * self.p.radius)))

    def _paddle(self, x, v, w, ppos, prot, pvel, pang):
        """Sphere vs oriented box (paddle face). Returns updated (x, v, w), hit mask, impulse on ball, point."""
        p = self.p
        half = self._const("paddle_half", PADDLE_HALF, x)
        local = ((x - ppos).unsqueeze(-2) @ prot).squeeze(-2)  # R^T (x - c)
        q_local = torch.maximum(torch.minimum(local, half), -half)
        rc = p.paddle_corner_radius
        if rc > 0.0:
            # Rounded-corner face: in the face plane, the closest point of a rectangle with
            # corner radius rc is the inner (rc-shrunk) rectangle's closest point pushed out by rc.
            inner = self._const("paddle_inner", [PADDLE_HALF[0] - rc, PADDLE_HALF[1] - rc], x)
            lxy = local[..., :2]
            qxy = torch.maximum(torch.minimum(lxy, inner), -inner)
            dxy = lxy - qxy
            dn = dxy.norm(dim=-1, keepdim=True)
            qxy = qxy + dxy * torch.clamp(rc / dn.clamp_min(1e-12), max=1.0)
            q_local = torch.cat([qxy, q_local[..., 2:]], -1)
        d_local = local - q_local
        dist = d_local.norm(dim=-1, keepdim=True)
        inside = dist.squeeze(-1) < 1e-9
        # Inside the box: leave through the face the ball is approaching from (relative velocity).
        q_world = ppos + (prot @ q_local.unsqueeze(-1)).squeeze(-1)
        surf_vel = pvel + torch.cross(pang, q_world - ppos, dim=-1)
        rel_local = ((v - surf_vel).unsqueeze(-2) @ prot).squeeze(-2)
        face_sign = torch.where(rel_local[..., 2] > 0, -1.0, 1.0).to(x.dtype)
        n_inside = prot[..., :, 2] * face_sign.unsqueeze(-1)
        n_out = (prot @ (d_local / dist.clamp_min(1e-12)).unsqueeze(-1)).squeeze(-1)
        n = torch.where(inside.unsqueeze(-1), n_inside, n_out)
        overlap = dist.squeeze(-1) < p.radius
        approaching = ((v - surf_vel) * n).sum(-1) < 0
        hit = overlap & approaching
        vb, wb, j = sphere_impulse(v, w, n, surf_vel, p.paddle_cor, p.paddle_friction, p)
        q_surface = torch.where(inside.unsqueeze(-1),
                                ppos + (prot @ (local * self._const("xy_mask", [1.0, 1.0, 0.0], x)).unsqueeze(-1)).squeeze(-1)
                                + n_inside * half[2], q_world)
        x_out = q_surface + n * p.radius
        o3, h3 = overlap.unsqueeze(-1), hit.unsqueeze(-1)
        return (torch.where(o3, x_out, x), torch.where(h3, vb, v), torch.where(h3, wb, w),
                hit, torch.where(h3, j, torch.zeros_like(j)), q_surface)

    def _net(self, x, v, w):
        p = self.p
        q, is_post = net_closest(x)
        d = x - q
        dist = d.norm(dim=-1, keepdim=True)
        inside = dist.squeeze(-1) < 1e-9  # centre inside the slab: push out along +-x
        n = torch.where(inside.unsqueeze(-1),
                        torch.stack([torch.where(v[..., 0] > 0, -1.0, 1.0).to(x.dtype),
                                     torch.zeros_like(x[..., 0]), torch.zeros_like(x[..., 0])], dim=-1),
                        d / dist.clamp_min(1e-12))
        overlap = dist.squeeze(-1) < p.radius
        approaching = (v * n).sum(-1) < 0
        hit = overlap & approaching
        vb, wb, _ = sphere_impulse(v, w, n, torch.zeros_like(v), p.net_cor, p.net_friction, p)
        q_out = q + n * p.radius  # depenetrate to the surface
        m3 = overlap.unsqueeze(-1)
        x = torch.where(m3, q_out, x)
        h3 = hit.unsqueeze(-1)
        return x, torch.where(h3, vb, v), torch.where(h3, wb, w), hit, hit & is_post

    def step(self, s: BallState, dt: float, substeps: int = 10,
             paddle: PaddleState | None = None, adaptive: bool = True) -> tuple[BallState, StepEvents]:
        """Advance all balls by dt.

        adaptive=True raises `substeps` from the batch's fastest ball/paddle (one host sync per
        call; convenient for tests and tools). adaptive=False uses exactly `substeps` and makes
        no host syncs. Training uses it with a count sized for the design speed (see the task).
        The sub-step body is branch-free: every contact test is computed and masked.
        """
        p = self.p
        if adaptive:
            substeps = self.substeps_for(s, dt, substeps, paddle)
        h = dt / substeps
        if paddle is not None:
            pad_hit = torch.zeros(s.pos.shape[0], dtype=torch.bool, device=s.pos.device)
            pad_point = torch.full_like(s.pos, float("nan"))
            pad_j = torch.zeros_like(s.pos)
            pad_l = torch.zeros_like(s.pos)
        k = 0
        x, v, w = s.pos, s.vel, s.spin
        n = torch.zeros_like(x)
        n[..., 2] = 1.0
        zero3 = torch.zeros_like(x)
        contact = torch.zeros(x.shape[0], dtype=torch.bool, device=x.device)
        net_hit = torch.zeros_like(contact)
        post_hit = torch.zeros_like(contact)
        point = torch.full_like(x, float("nan"))
        R = p.radius
        reach = max(court.NET_THICKNESS / 2, court.NET_POST_RADIUS) + R
        for _ in range(substeps):
            x1, v1, w1 = flight_rk4(x, v, w, h, p)
            # Court: time of impact by linear interpolation inside the sub-step, impulse at the
            # contact state, then the rest of the sub-step with the sub-step's mean acceleration.
            z0, z1 = x[..., 2], x1[..., 2]
            hit = (z1 < R) & (v1[..., 2] < 0)
            frac = ((z0 - R) / (z0 - z1).clamp_min(1e-12)).clamp(0.0, 1.0)
            frac = torch.where(z0 < R, torch.zeros_like(frac), frac).unsqueeze(-1)
            xc = x + frac * (x1 - x)
            xc = torch.cat([xc[..., :2], torch.full_like(xc[..., 2:], R)], -1)
            vc = v + frac * (v1 - v)
            wc = w + frac * (w1 - w)
            vb, wb, _ = sphere_impulse(vc, wc, n, zero3, p.court_cor, p.court_friction, p)
            rem = (1.0 - frac) * h
            acc = (v1 - v) / h
            xr = xc + vb * rem + 0.5 * acc * rem * rem
            vr = vb + acc * rem
            xr = torch.cat([xr[..., :2], xr[..., 2:].clamp_min(R)], -1)
            m3 = hit.unsqueeze(-1)
            point = torch.where((hit & ~contact).unsqueeze(-1), xc - R * n, point)
            contact = contact | hit
            x1, v1, w1 = torch.where(m3, xr, x1), torch.where(m3, vr, v1), torch.where(m3, wb, w1)
            # Resting ball: hold on the surface without sinking.
            resting = (x1[..., 2] <= R + 1e-6) & (v1[..., 2].abs() <= REST_SPEED)
            rz = resting.unsqueeze(-1)
            x1 = torch.where(rz, torch.cat([x1[..., :2], torch.full_like(x1[..., 2:], R)], -1), x1)
            v1 = torch.where(rz, torch.cat([v1[..., :2], torch.zeros_like(v1[..., 2:])], -1), v1)
            # Net and posts (masked to balls near the net plane).
            near_net = (x1[..., 0].abs() < reach) & (x1[..., 2] < court.NET_SIDELINE_HEIGHT + R)
            xn, vn, wn, hn, hp = self._net(x1, v1, w1)
            mn = near_net.unsqueeze(-1)
            x1, v1, w1 = torch.where(mn, xn, x1), torch.where(mn, vn, v1), torch.where(mn, wn, w1)
            net_hit |= hn & near_net
            post_hit |= hp & near_net
            if paddle is not None:
                k += 1
                ppos, prot = paddle_at(paddle, k * h)
                x1, v1, w1, ph, j, q = self._paddle(x1, v1, w1, ppos, prot, paddle.lin_vel, paddle.ang_vel)
                first = ph & ~pad_hit
                pad_point = torch.where(first.unsqueeze(-1), q, pad_point)
                pad_hit |= ph
                pad_j = pad_j - j  # reaction on the paddle
                pad_l = pad_l + torch.cross(q - ppos, -j, dim=-1)
            x, v, w = x1, v1, w1
        ev = StepEvents(contact, point, net_hit, post_hit)
        if paddle is not None:
            ev.paddle_contact, ev.paddle_point, ev.paddle_impulse, ev.paddle_angular_impulse = pad_hit, pad_point, pad_j, pad_l
        return BallState(x, v, w), ev


def energy(s: BallState, p: BallParams) -> torch.Tensor:
    """Total mechanical energy per ball (translational + rotational + potential, ball centre)."""
    return (0.5 * p.mass * (s.vel**2).sum(-1) + 0.5 * p.inertia * (s.spin**2).sum(-1)
            + p.mass * p.gravity * s.pos[..., 2])


def _step_tensors(sim: "BallSim", x, v, w, ppos, prot, pvel, pang, dt: float, substeps: int):
    """Pure-tensor fixed-sub-step step (adaptive=False) for torch.compile."""
    s, ev = BallSim.step(sim, BallState(x, v, w), dt, substeps, PaddleState(ppos, prot, pvel, pang), adaptive=False)
    return (s.pos, s.vel, s.spin, ev.court_contact, ev.court_point, ev.net_contact, ev.post_contact,
            ev.paddle_contact, ev.paddle_point, ev.paddle_impulse, ev.paddle_angular_impulse)


class CompiledBallSim(BallSim):
    """BallSim whose fixed-sub-step paddle step runs through torch.compile.

    mode "default" fuses element-wise kernels; "reduce-overhead" also captures CUDA graphs.
    Results match the eager step to float32 rounding (see tests/test_ball_compile.py).
    """

    def __init__(self, params: BallParams | None = None, mode: str = "default"):
        super().__init__(params)
        self.mode = mode
        self._fn = torch.compile(lambda *a: _step_tensors(self, *a), mode=mode, dynamic=False, fullgraph=True)

    def step(self, s, dt, substeps=10, paddle=None, adaptive=True):
        if adaptive or paddle is None:
            return super().step(s, dt, substeps, paddle, adaptive)
        out = self._fn(s.pos, s.vel, s.spin, paddle.pos, paddle.rot, paddle.lin_vel, paddle.ang_vel, dt, substeps)
        if self.mode == "reduce-overhead":  # CUDA-graph outputs are overwritten on the next replay
            out = tuple(o.clone() for o in out)
        x, v, w, cc, cp, nc, pc, padc, padp, padj, padl = out
        return BallState(x, v, w), StepEvents(cc, cp, nc, pc, padc, padp, padj, padl)
