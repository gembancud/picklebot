"""Stance-spot planner (Stage 5E, D-097/D-098): where the robot should stand for the ball in flight.

The Stage 5B-5D stance hint (`shadow_swing.stance_spot`) read the true launch state and a per-family calibration
table, so it knew things a real robot cannot: the exact ball state, its spin and which family was fed. This planner
works from what a camera-based estimator would give:
- **Delay:** the ball is observed for `delay_s` after the launch before a spot is produced.
- **Noise:** the estimate of position and velocity carries Gaussian noise (`pos_noise`, `vel_noise` per axis).
- **Spin:** unknown and assumed zero unless `know_spin` is set (the clean reference).

From that estimate it rolls the same flight model forward (gravity, drag and Magnus from `ball.aero_force`, RK4) with
the same court bounce impulse as `ball_sim`, without the paddle or the net. It takes the interception point as the
evaluation's "top" rule (`shadow_swing.predict_intercept` mode "top"): after the bounce, where the ball rises through
HINT_TOP_Z, or its apex if lower. The stance spot sits beside that point (forehand or backhand side, HINT_BEHIND
behind it) inside HINT_BOX_V2, as the Stage 5 hint did.

Errors therefore come from estimation noise and unknown spin, as they would on a real robot. Clean mode
(`clean=True`: true state, true spin, no noise) is the reference the noisy planner is compared against.
"""

from __future__ import annotations

from dataclasses import dataclass

import torch

from picklebot_mj.ball_sim import BallParams, flight_rk4, sphere_impulse
from picklebot_mj.tasks.shadow_swing import (HINT_BEHIND, HINT_BOX_V2, HINT_SIDE_BH, HINT_SIDE_FH, HINT_TOP_Z,
                                             _const)


@dataclass(frozen=True)
class PlannerCfg:
    delay_s: float = 0.10  # observation window after the launch before the spot appears
    pos_noise: float = 0.03  # m, per axis (stereo ball tracking at court range)
    vel_noise: float = 0.15  # m/s, per axis (velocity from a short track fit)
    know_spin: bool = False  # True only for the clean reference
    dt: float = 0.0125  # rollout step (RK4)
    horizon_s: float = 1.8  # time to the interception of the longest drill v2 feed (reach_deep), from its launch


def predict_top(pos: torch.Tensor, vel: torch.Tensor, spin: torch.Tensor, cfg: PlannerCfg = PlannerCfg(),
                params: BallParams | None = None, graphed: bool = False) -> tuple[torch.Tensor, torch.Tensor]:
    """Roll the flight model forward from (pos, vel, spin), all (N, 3) court-local.

    Returns the (N, 2) xy of the interception point (after the first bounce: rising through HINT_TOP_Z, or the apex if
    lower) and an (N,) bool that is False where none was found within the horizon (then the last rolled-out xy).
    graphed: replay the rollout from a CUDA graph per batch shape (fixed-shape in-environment planning, D-124).
    """
    p = params or _DEFAULT_PARAMS
    k = CHUNK if pos.is_cuda else 1
    step = _compiled_chunk(p, cfg.dt, k) if pos.is_cuda else (lambda *a: _rollout_step(p, cfg.dt, *a))
    chunks = -(-int(round(cfg.horizon_s / cfg.dt)) // k)

    def roll(x, v, w):
        x, v, w = x.clone(), v.clone(), w.clone()
        bounced = torch.zeros(x.shape[0], dtype=torch.bool, device=x.device)
        found = torch.zeros_like(bounced)
        out = x[:, :2].clone()
        for _ in range(chunks):
            x, v, w, bounced, found, out = step(x, v, w, bounced, found, out)
        return torch.where(found.unsqueeze(-1), out, x[:, :2]), found

    if graphed and pos.is_cuda:
        return _graphed(("top", id(p), cfg.dt, chunks, pos.shape[0]), roll, pos, vel, spin)
    return roll(pos, vel, spin)


def _rollout_step(p: BallParams, dt: float, x, v, w, bounced, found, out):
    """One rollout step: RK4 flight, the first court bounce at its interpolated time, and the interception check."""
    r = p.radius
    x0, v0 = x, v
    x, v, w = flight_rk4(x, v, w, dt, p)
    ground = (x[:, 2] <= r) & (v[:, 2] < 0) & ~bounced
    # Bounce at the interpolated impact time f * dt; the rest of the step (1 - f) * dt continues after the impulse.
    f = ((x0[:, 2] - r) / (x0[:, 2] - x[:, 2]).clamp(min=1e-9)).clamp(0.0, 1.0).unsqueeze(-1)
    xi, vi = x0 + f * (x - x0), v0 + f * (v - v0)
    up = torch.zeros_like(x)
    up[:, 2] = 1.0
    vb, wb, _ = sphere_impulse(vi, w, up, torch.zeros_like(x), p.court_cor, p.court_friction, p)
    xb = xi + (1.0 - f) * dt * vb
    g = ground.unsqueeze(-1)
    v, w = torch.where(g, vb, v), torch.where(g, wb, w)
    x = torch.where(g, torch.cat([xb[:, :2], xb[:, 2:].clamp(min=r)], -1), x)
    bounced = bounced | ground
    # Interception inside the step: the ball rises through HINT_TOP_Z, or its vertical speed crosses zero.
    rise = (x[:, 2] >= HINT_TOP_Z) & (x0[:, 2] < HINT_TOP_Z)
    apex = (v[:, 2] <= 0) & (v0[:, 2] > 0)
    hit = bounced & ~found & ~ground & (rise | apex | (v[:, 2] <= 0) | (x[:, 2] >= HINT_TOP_Z))
    fr = ((HINT_TOP_Z - x0[:, 2]) / (x[:, 2] - x0[:, 2]).abs().clamp(min=1e-9)).clamp(0.0, 1.0)
    fa = (v0[:, 2] / (v0[:, 2] - v[:, 2]).clamp(min=1e-9)).clamp(0.0, 1.0)
    fh = torch.where(rise, fr, torch.where(apex, fa, torch.ones_like(fa))).unsqueeze(-1)
    out = torch.where(hit.unsqueeze(-1), (x0 + fh * (x - x0))[:, :2], out)
    return x, v, w, bounced, found | hit, out


_COMPILED: dict = {}
_DEFAULT_PARAMS = BallParams()
CHUNK = 8  # rollout steps fused per compiled call (eager costs ~3 ms per step at 12k envs, one compiled step ~0.27 ms)


def _chunk(p: BallParams, dt: float, k: int, *a):
    for _ in range(k):
        a = _rollout_step(p, dt, *a)
    return a


def _compiled_chunk(p: BallParams, dt: float, k: int):
    """torch.compile of k rollout steps (one fused graph per call; a rollout may run a few steps past the horizon)."""
    key = (id(p), dt, k)
    if key not in _COMPILED:
        _COMPILED[key] = (p, torch.compile(lambda *a: _chunk(p, dt, k, *a), mode="default", dynamic=False,
                                           fullgraph=True))
    return _COMPILED[key][1]


COMP_DT = 0.005  # compensation sub-step (one physics step)


def compensate(pos: torch.Tensor, vel: torch.Tensor, substeps: torch.Tensor, max_substeps: int,
               params: BallParams | None = None) -> tuple[torch.Tensor, torch.Tensor]:
    """Stage 5F ball latency compensator (D-108/D-109): roll each env's delayed ball measurement forward by its own
    age, substeps[i] x COMP_DT, with the spin-blind flight and bounce model. max_substeps is a host-side bound (no sync).
    Offline (scripts/diag/ball_lag_error.py) this brings 20-40 ms of delay back to the noise floor for every family."""
    p = params or _DEFAULT_PARAMS
    x, v = pos.clone(), vel.clone()
    w = torch.zeros_like(x)
    bounced = torch.zeros(x.shape[0], dtype=torch.bool, device=x.device)
    found, out = torch.zeros_like(bounced), x[:, :2].clone()
    step = _compiled_chunk(p, COMP_DT, 1) if x.is_cuda else (lambda *a: _rollout_step(p, COMP_DT, *a))
    for i in range(int(max_substeps)):
        x1, v1, w1, b1, f1, out = step(x, v, w, bounced, found, out)
        act = (substeps > i).unsqueeze(-1)
        x, v, w = torch.where(act, x1, x), torch.where(act, v1, v), torch.where(act, w1, w)
        bounced = torch.where(act.squeeze(-1), b1, bounced)
        found = f1
    return x, v


def stance_from_intercept(xy: torch.Tensor, pelvis_xy: torch.Tensor) -> torch.Tensor:
    """Stance spot beside an interception point, as `shadow_swing.stance_spot` (v2 box)."""
    xi, yi = xy[:, 0], xy[:, 1]
    forehand = yi <= pelvis_xy[:, 1]  # ball on the robot's right (-y) -> forehand
    sy = torch.where(forehand, yi + HINT_SIDE_FH, yi - HINT_SIDE_BH)
    sx = xi - HINT_BEHIND
    lo = _const(("box_lo", True), lambda: [HINT_BOX_V2[0][0], HINT_BOX_V2[1][0]], xy.device)
    hi = _const(("box_hi", True), lambda: [HINT_BOX_V2[0][1], HINT_BOX_V2[1][1]], xy.device)
    return torch.stack([sx, sy], -1).clamp(lo, hi)


def plan_stance(pos: torch.Tensor, vel: torch.Tensor, spin: torch.Tensor, pelvis_xy: torch.Tensor,
                cfg: PlannerCfg = PlannerCfg(), gen: torch.Generator | None = None, clean: bool = False,
                params: BallParams | None = None, graphed: bool = False) -> torch.Tensor:
    """Stance spot (N, 2) from the ball state at the planning time.

    clean: true state and spin. Otherwise the state is perturbed by the estimator noise and spin is unknown (zero)
    unless cfg.know_spin.
    """
    if not clean:
        pos = pos + cfg.pos_noise * torch.randn(pos.shape, generator=gen, device=pos.device)
        vel = vel + cfg.vel_noise * torch.randn(vel.shape, generator=gen, device=vel.device)
        if not cfg.know_spin:
            spin = torch.zeros_like(spin)
    xy, _ = predict_top(pos, vel, spin, cfg, params, graphed)
    return stance_from_intercept(xy, pelvis_xy)


# --- Stage 5G (D-118): timed contact, a keep-it-alive outgoing ball and the paddle state that makes it. ---------------
# The planner owns the outgoing ball; the timed goal-conditioned controller is commanded the paddle state at contact.

KEEP_ALIVE_BOX = ((4.7, 5.7), (-1.0, 1.0))  # landing x, y (far court, court-local; the robot is at x < 0)
KEEP_ALIVE_FLIGHT_S = (1.3, 1.5)  # contact-to-landing flight time: a feeder-like, returnable rally ball
KEEP_ALIVE_BOX_TAIL_M = 1.0  # D-129: the keep-alive score falls linearly to 0 this far outside the box
KEEP_ALIVE_FLIGHT_TAIL_S = 0.5  # and this far outside the flight-time window


def keep_alive_score(landing_xy: torch.Tensor, flight_s: torch.Tensor) -> torch.Tensor:
    """D-129: score in [0, 1] of a landed return (court-local landing xy, contact-to-landing time): 1 inside
    KEEP_ALIVE_BOX with a flight time inside KEEP_ALIVE_FLIGHT_S; the product of two linear tails outside."""
    (x0, x1), (y0, y1) = KEEP_ALIVE_BOX
    f0, f1 = KEEP_ALIVE_FLIGHT_S
    x, y = landing_xy[:, 0], landing_xy[:, 1]
    dx = (x0 - x).clamp(min=0.0) + (x - x1).clamp(min=0.0)
    dy = (y0 - y).clamp(min=0.0) + (y - y1).clamp(min=0.0)
    box = (1.0 - torch.sqrt(dx * dx + dy * dy) / KEEP_ALIVE_BOX_TAIL_M).clamp(0.0, 1.0)
    dt = (f0 - flight_s).clamp(min=0.0) + (flight_s - f1).clamp(min=0.0)
    return box * (1.0 - dt / KEEP_ALIVE_FLIGHT_TAIL_S).clamp(0.0, 1.0)


def _contact_step(p: BallParams, dt: float, x, v, w, t, bounced, found, cx, cv, ct):
    """As _rollout_step, also carrying the elapsed time and capturing the 3-D state and time at the interception."""
    x0, v0, t0 = x, v, t
    x, v, w, bounced, found2, _ = _rollout_step(p, dt, x, v, w, bounced, found, x[:, :2])
    hit = found2 & ~found
    rise = (x[:, 2] >= HINT_TOP_Z) & (x0[:, 2] < HINT_TOP_Z)
    fr = ((HINT_TOP_Z - x0[:, 2]) / (x[:, 2] - x0[:, 2]).abs().clamp(min=1e-9)).clamp(0.0, 1.0)
    fa = (v0[:, 2] / (v0[:, 2] - v[:, 2]).clamp(min=1e-9)).clamp(0.0, 1.0)
    fh = torch.where(rise, fr, fa).unsqueeze(-1)
    m = hit.unsqueeze(-1)
    cx = torch.where(m, x0 + fh * (x - x0), cx)
    cv = torch.where(m, v0 + fh * (v - v0), cv)
    ct = torch.where(hit, t0 + fh.squeeze(-1) * dt, ct)
    return x, v, w, t + dt, bounced, found2, cx, cv, ct


CONTACT_DT = 0.0025  # contact rollout step: <= 2.7 cm and 10 ms against the full simulation (0.0125: 14 cm, 63 ms)


def predict_contact(pos: torch.Tensor, vel: torch.Tensor, spin: torch.Tensor, cfg: PlannerCfg = PlannerCfg(),
                    params: BallParams | None = None, dt: float = CONTACT_DT):
    """The interception of predict_top as a full contact: (point (N, 3), ball velocity there (N, 3), time from now
    (N,), found (N,) bool). Spin is used as given (pass zeros for the spin-blind planner). The rollout uses its own
    finer step `dt` (the stance planner's cfg.dt is too coarse for a paddle target); cfg gives the horizon."""
    p = params or _DEFAULT_PARAMS
    n = pos.shape[0]
    x, v, w = pos.clone(), vel.clone(), spin.clone()
    t = torch.zeros(n, device=pos.device)
    bounced = torch.zeros(n, dtype=torch.bool, device=pos.device)
    found = torch.zeros_like(bounced)
    cx, cv, ct = x.clone(), v.clone(), torch.full((n,), cfg.horizon_s, device=pos.device)
    for _ in range(int(round(cfg.horizon_s / dt))):
        x, v, w, t, bounced, found, cx, cv, ct = _contact_step(p, dt, x, v, w, t, bounced, found, cx, cv, ct)
    return cx, cv, ct, found


def aim_outgoing(contact: torch.Tensor, target_xy: torch.Tensor, flight_s: torch.Tensor, iters: int = 4,
                 steps: int = 40, params: BallParams | None = None) -> torch.Tensor:
    """Outgoing ball velocity (N, 3), spin-blind with drag, that leaves `contact` and reaches the court (z = radius)
    at `target_xy` after `flight_s` seconds: a drag-free ballistic start, then fixed-point corrections on the landing
    error of an RK4 rollout of exactly flight_s (steps sub-steps of flight_s / steps)."""
    p = params or _DEFAULT_PARAMS
    g = 9.81
    T = flight_s.unsqueeze(-1)
    v = torch.cat([(target_xy - contact[:, :2]) / T,
                   ((p.radius - contact[:, 2:3]) + 0.5 * g * T * T) / T], -1)
    h = T / steps
    w0 = torch.zeros_like(contact)
    for _ in range(iters):
        x, vv, w = contact.clone(), v.clone(), w0
        for _ in range(steps):
            x, vv, w = flight_rk4(x, vv, w, h, p)
        err = torch.cat([target_xy - x[:, :2], p.radius - x[:, 2:3]], -1)
        v = v + err / T
    return v


_GRAPHS: dict = {}


def _graphed(key, fn, *inputs):
    """fn(*inputs) replayed from a CUDA graph captured once per key (the key fixes the shapes): the inputs are copied
    into the graph's static buffers and clones of its outputs are returned. fn must have no host syncs and no random
    draws. In-environment planning is bound by kernel launches (D-124 profile: 144 ms per contact rollout of 128
    balls in 90 compiled calls); a replay launches once."""
    if key not in _GRAPHS:
        static = [x.clone() for x in inputs]
        side = torch.cuda.Stream()
        side.wait_stream(torch.cuda.current_stream())
        with torch.cuda.stream(side):
            for _ in range(2):  # warm-up: compilation and the allocator
                fn(*static)
        torch.cuda.current_stream().wait_stream(side)
        graph = torch.cuda.CUDAGraph()
        with torch.cuda.graph(graph):
            out = fn(*static)
        _GRAPHS[key] = (graph, static, out)
    graph, static, out = _GRAPHS[key]
    for buf, x in zip(static, inputs):
        buf.copy_(x)
    graph.replay()
    return tuple(o.clone() for o in out)


_COMPILED_AIM: dict = {}


def _flight(p: BallParams, steps: int, x, vv, h):
    w = torch.zeros_like(x)
    for _ in range(steps):
        x, vv, w = flight_rk4(x, vv, w, h, p)
    return x


def aim_outgoing_fast(contact: torch.Tensor, target_xy: torch.Tensor, flight_s: torch.Tensor, iters: int = 4,
                      steps: int = 40) -> torch.Tensor:
    """aim_outgoing for in-environment planning: each correction's flight is one compiled graph, and the whole aim is
    replayed from a CUDA graph per batch shape. Same results as aim_outgoing."""
    if not contact.is_cuda:
        return aim_outgoing(contact, target_xy, flight_s, iters, steps)
    p = _DEFAULT_PARAMS
    key = (id(p), steps)
    if key not in _COMPILED_AIM:
        _COMPILED_AIM[key] = torch.compile(lambda *a: _flight(p, steps, *a), mode="default", dynamic=False,
                                           fullgraph=True)
    fly = _COMPILED_AIM[key]

    def aim(contact, target_xy, flight_s):
        g = 9.81
        T = flight_s.unsqueeze(-1)
        v = torch.cat([(target_xy - contact[:, :2]) / T, ((p.radius - contact[:, 2:3]) + 0.5 * g * T * T) / T], -1)
        h = T / steps
        for _ in range(iters):
            x = fly(contact.clone(), v.clone(), h)
            v = v + torch.cat([target_xy - x[:, :2], p.radius - x[:, 2:3]], -1) / T
        return (v,)

    return _graphed(("aim", key, iters, contact.shape[0]), aim, contact, target_xy, flight_s)[0]


def paddle_for(v_in: torch.Tensor, v_out: torch.Tensor, cor: float | None = None) -> tuple[torch.Tensor, torch.Tensor]:
    """Paddle face normal n (N, 3) and paddle velocity (N, 3) at contact that turn v_in into v_out (spin-blind).

    n is along v_out - v_in, so the ball's tangential velocity is unchanged; the paddle moves with the ball
    tangentially (no slip, so friction does nothing) and along n at u = (v_out.n + e v_in.n) / (1 + e), the normal
    restitution of `sphere_impulse` solved for the surface speed."""
    e = PADDLE_COR_DEFAULT if cor is None else cor
    d = v_out - v_in
    n = d / d.norm(dim=-1, keepdim=True).clamp(min=1e-6)
    vin_n = (v_in * n).sum(-1, keepdim=True)
    u = ((v_out * n).sum(-1, keepdim=True) + e * vin_n) / (1.0 + e)
    return n, u * n + (v_in - vin_n * n)


PADDLE_COR_DEFAULT = _DEFAULT_PARAMS.paddle_cor


def keep_alive_target(n: int, gen: torch.Generator | None = None, device="cpu") -> tuple[torch.Tensor, torch.Tensor]:
    """(landing xy (n, 2), flight time (n,)) drawn uniformly in KEEP_ALIVE_BOX and KEEP_ALIVE_FLIGHT_S."""
    u = torch.rand(n, 3, generator=gen, device=device)
    (x0, x1), (y0, y1) = KEEP_ALIVE_BOX
    f0, f1 = KEEP_ALIVE_FLIGHT_S
    xy = torch.stack([x0 + (x1 - x0) * u[:, 0], y0 + (y1 - y0) * u[:, 1]], -1)
    return xy, f0 + (f1 - f0) * u[:, 2]


CONTACT_BUCKET = 64  # planning batches padded to a multiple of this, so the compiled rollout keeps a few fixed shapes
_COMPILED_CONTACT: dict = {}


def _contact_chunk(p: BallParams, dt: float, k: int, *a):
    for _ in range(k):
        a = _contact_step(p, dt, *a)
    return a


def predict_contact_fast(pos: torch.Tensor, vel: torch.Tensor, spin: torch.Tensor, cfg: PlannerCfg = PlannerCfg(),
                         params: BallParams | None = None, dt: float = CONTACT_DT):
    """predict_contact for in-environment planning: the batch is padded to a multiple of CONTACT_BUCKET and the
    rollout runs as compiled chunks of CHUNK steps replayed from one CUDA graph per batch shape (eager costs ~720 small
    kernel launches per call on the CPU). Same
    results as predict_contact (a rollout may run up to CHUNK - 1 steps past the horizon; the capture is unchanged)."""
    if not pos.is_cuda:
        return predict_contact(pos, vel, spin, cfg, params, dt)
    p = params or _DEFAULT_PARAMS
    n = pos.shape[0]
    m = -(-n // CONTACT_BUCKET) * CONTACT_BUCKET
    pad = lambda x: torch.cat([x, x[-1:].expand(m - n, *x.shape[1:])]) if m > n else x  # noqa: E731
    key = (id(p), dt, CHUNK)
    if key not in _COMPILED_CONTACT:
        _COMPILED_CONTACT[key] = torch.compile(lambda *a: _contact_chunk(p, dt, CHUNK, *a), mode="default",
                                               dynamic=False, fullgraph=True)
    f = _COMPILED_CONTACT[key]
    chunks = -(-int(round(cfg.horizon_s / dt)) // CHUNK)

    def roll(x, v, w):
        t = torch.zeros(m, device=x.device)
        bounced = torch.zeros(m, dtype=torch.bool, device=x.device)
        found = torch.zeros_like(bounced)
        cx, cv, ct = x.clone(), v.clone(), torch.full((m,), cfg.horizon_s, device=x.device)
        for _ in range(chunks):
            x, v, w, t, bounced, found, cx, cv, ct = f(x, v, w, t, bounced, found, cx, cv, ct)
        return cx, cv, ct, found

    cx, cv, ct, found = _graphed(("contact", key, chunks, cfg.horizon_s, m), roll, pad(pos), pad(vel), pad(spin))
    return cx[:n], cv[:n], ct[:n], found[:n]


# --- Stage 5G E6 (D-125): let the ball come to you. ------------------------------------------------------------------
# The contact above is the first interception after the bounce. 35 % of live goals then need more than 1.5 m/s of
# walking (E3 and E5 reach almost none of them). The walkable contact takes the earliest point at or after that
# interception, while the ball is still inside the goal bank's contact heights [WALK_Z_MIN, HINT_TOP_Z], whose stance
# spot needs at most WALK_CAP m/s from the pelvis; if no point does, the point that needs the least.
WALK_CAP = 1.5  # m/s
WALK_Z_MIN = 0.50  # m: the goal bank's 10th-percentile contact height


def _walk_step(p: BallParams, dt: float, cap: float, x, v, w, t, bounced, found, cx, cv, ct, pel, chosen, bx, bv, bt,
               breq):
    x, v, w, t, bounced, found2, cx, cv, ct = _contact_step(p, dt, x, v, w, t, bounced, found, cx, cv, ct)
    hit = found2 & ~found  # the first interception, this step (its interpolated point)
    later = found & (x[:, 2] >= WALK_Z_MIN) & (x[:, 2] <= HINT_TOP_Z)  # later points still in the bank's heights
    h = hit.unsqueeze(-1)
    qx, qv, qt = torch.where(h, cx, x), torch.where(h, cv, v), torch.where(hit, ct, t)
    side = torch.where(qx[:, 1] <= pel[:, 1], qx[:, 1] + HINT_SIDE_FH, qx[:, 1] - HINT_SIDE_BH)
    stance = torch.stack([qx[:, 0] - HINT_BEHIND, side], -1)
    req = (stance - pel).norm(dim=-1) / qt.clamp(min=0.05)
    ok = (hit | later) & ~chosen
    take = ok & (req <= cap)
    upd = take | (ok & (req < breq))
    u = upd.unsqueeze(-1)
    bx, bv, bt, breq = torch.where(u, qx, bx), torch.where(u, qv, bv), torch.where(upd, qt, bt), torch.where(upd, req, breq)
    return x, v, w, t, bounced, found2, cx, cv, ct, pel, chosen | take, bx, bv, bt, breq


def _walk_chunk(p: BallParams, dt: float, cap: float, k: int, *a):
    for _ in range(k):
        a = _walk_step(p, dt, cap, *a)
    return a


_COMPILED_WALK: dict = {}


def predict_contact_walkable(pos: torch.Tensor, vel: torch.Tensor, spin: torch.Tensor, pelvis_xy: torch.Tensor,
                             cap: float = WALK_CAP, cfg: PlannerCfg = PlannerCfg(), params: BallParams | None = None,
                             dt: float = CONTACT_DT):
    """The walkable contact (see WALK_CAP): (point (N, 3), ball velocity there (N, 3), time from now (N,), found (N,)),
    found as predict_contact's. On CUDA the batch is padded to CONTACT_BUCKET and replayed from a CUDA graph."""
    p = params or _DEFAULT_PARAMS
    n = pos.shape[0]
    cuda = pos.is_cuda
    m = -(-n // CONTACT_BUCKET) * CONTACT_BUCKET if cuda else n
    pad = lambda x: torch.cat([x, x[-1:].expand(m - n, *x.shape[1:])]) if m > n else x  # noqa: E731
    k = CHUNK if cuda else 1
    key = (id(p), dt, cap, k)
    if cuda and key not in _COMPILED_WALK:
        _COMPILED_WALK[key] = torch.compile(lambda *a: _walk_chunk(p, dt, cap, k, *a), mode="default", dynamic=False,
                                            fullgraph=True)
    f = _COMPILED_WALK[key] if cuda else (lambda *a: _walk_chunk(p, dt, cap, 1, *a))
    chunks = -(-int(round(cfg.horizon_s / dt)) // k)

    def roll(x, v, w, pel):
        x, v, w = x.clone(), v.clone(), w.clone()
        mm = x.shape[0]
        t = torch.zeros(mm, device=x.device)
        bounced = torch.zeros(mm, dtype=torch.bool, device=x.device)
        found, chosen = torch.zeros_like(bounced), torch.zeros_like(bounced)
        cx, cv, ct = x.clone(), v.clone(), torch.full((mm,), cfg.horizon_s, device=x.device)
        bx, bv, bt = x.clone(), v.clone(), torch.full((mm,), cfg.horizon_s, device=x.device)
        breq = torch.full((mm,), 1e9, device=x.device)
        a = (x, v, w, t, bounced, found, cx, cv, ct, pel, chosen, bx, bv, bt, breq)
        for _ in range(chunks):
            a = f(*a)
        return a[11], a[12], a[13], a[5]

    if cuda:
        bx, bv, bt, found = _graphed(("walk", key, chunks, cfg.horizon_s, m), roll, pad(pos), pad(vel), pad(spin),
                                     pad(pelvis_xy))
    else:
        bx, bv, bt, found = roll(pos, vel, spin, pelvis_xy)
    return bx[:n], bv[:n], bt[:n], found[:n]
