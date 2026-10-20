"""D-127 contact decomposition: why the robot's shots land short and wide.

Rows come from `stage2_eval.py --record-contacts` (one per first contact; court-local), columns:
  0-2 ball position before the contact step, 3-5 incoming velocity, 6-8 incoming spin,
  9-11 paddle position, 12-14 face normal (either face), 15-17 paddle velocity, 18-20 paddle angular velocity,
  21-23 outgoing velocity (simulated), 24-26 outgoing spin,
  27-29 commanded paddle velocity v*, 30-32 commanded face normal n*, 33-35 the planner's outgoing ball velocity,
  36-38 its landing target (x, y) and flight time, 39-41 the goal's contact point p*, 42 time to contact at the contact
  (tau), 43 legal return.

The landing error splits in two along the chain target -> planned ball -> commanded paddle state -> realized shot:
- planner gap: the commanded paddle state (n*, v*) applied by the simulator's own impact model (`sphere_impulse`, with
  the real incoming ball and spin and the paddle friction) and flown with spin, against the target;
- controller gap: the realized shot against that commanded-state shot.
"""

from __future__ import annotations

import torch

from picklebot_mj.ball_sim import BallParams, flight_rk4, sphere_impulse

COLS = 44


def orient(n: torch.Tensor, v_in: torch.Tensor, surf: torch.Tensor) -> torch.Tensor:
    """The face normal pointing at the incoming ball (either face may strike)."""
    s = torch.where(((v_in - surf) * n).sum(-1, keepdim=True) > 0, -1.0, 1.0)
    return n * s


def impact(v_in, w_in, n, surf, p: BallParams):
    """The simulator's paddle impact: outgoing (velocity, spin)."""
    vb, wb, _ = sphere_impulse(v_in, w_in, orient(n, v_in, surf), surf, p.paddle_cor, p.paddle_friction, p)
    return vb, wb


def land(x: torch.Tensor, v: torch.Tensor, w: torch.Tensor, p: BallParams, dt: float = 0.0025, horizon: float = 3.0):
    """First court landing (z = radius, interpolated) of balls in free flight (drag and Magnus, no net): (xy, time,
    landed)."""
    n = x.shape[0]
    t = torch.zeros(n, device=x.device)
    out = torch.zeros(n, 2, device=x.device)
    when = torch.full((n,), horizon, device=x.device)
    done = torch.zeros(n, dtype=torch.bool, device=x.device)
    for _ in range(int(round(horizon / dt))):
        x1, v1, w1 = flight_rk4(x, v, w, dt, p)
        cross = ~done & (x1[:, 2] <= p.radius) & (x[:, 2] > p.radius)
        f = ((x[:, 2] - p.radius) / (x[:, 2] - x1[:, 2]).clamp(min=1e-9)).unsqueeze(-1)
        out = torch.where(cross.unsqueeze(-1), (x + f * (x1 - x))[:, :2], out)
        when = torch.where(cross, t + f.squeeze(-1) * dt, when)
        done |= cross
        x, v, w, t = x1, v1, w1, t + dt
    return out, when, done


def decompose(rows: torch.Tensor, p: BallParams | None = None) -> dict:
    p = p or BallParams()
    r = rows.float()
    c, v_in, w_in = r[:, 0:3], r[:, 3:6], r[:, 6:9]
    ppos, n_r, pv, pw = r[:, 9:12], r[:, 12:15], r[:, 15:18], r[:, 18:21]
    v_real, w_real = r[:, 21:24], r[:, 24:27]
    v_star, n_star, v_plan, tgt = r[:, 27:30], r[:, 30:33], r[:, 33:36], r[:, 36:38]
    tau, legal = r[:, 42], r[:, 43] > 0.5
    zero = torch.zeros_like(c)
    v_cmd, w_cmd = impact(v_in, w_in, n_star, v_star, p)
    v_cmd0, w_cmd0 = impact(v_in, zero, n_star, v_star, p)  # without the incoming spin
    v_exec, _ = impact(v_in, w_in, n_r, pv + torch.cross(pw, c - ppos, dim=-1), p)  # sanity: should match v_real
    L_plan, _, ok_p = land(c, v_plan, zero, p)
    L_cmd, _, ok_c = land(c, v_cmd, w_cmd, p)
    L_cmd0, _, _ = land(c, v_cmd0, w_cmd0, p)
    L_cmd_nospin, _, _ = land(c, v_cmd, zero, p)
    L_real, _, ok_r = land(c, v_real, w_real, p)
    goal = tau.abs() <= 0.10  # the contact belongs to the goal set for it (within 100 ms of t*)
    use = goal & ok_p & ok_c & ok_r

    def ang(a, b):
        cos = (a * b).sum(-1) / (a.norm(dim=-1) * b.norm(dim=-1)).clamp(min=1e-9)
        return torch.rad2deg(torch.acos(cos.clamp(-1, 1)))

    face_err = torch.rad2deg(torch.acos((n_r * n_star).sum(-1).abs().clamp(max=1.0)))
    off = c - ppos
    off_plane = (off - (off * n_r).sum(-1, keepdim=True) * n_r).norm(dim=-1)

    def m(x):
        x = x[use]
        return round(float(x.mean()), 4) if x.numel() else None

    def med(x):
        x = x[use]
        return round(float(x.median()), 4) if x.numel() else None

    return {
        "contacts": int(r.shape[0]), "scored_with_their_goal": int(use.sum()),
        "landing_x": {"target": m(tgt[:, 0]), "planned_ball": m(L_plan[:, 0]), "commanded_paddle": m(L_cmd[:, 0]),
                      "realized": m(L_real[:, 0])},
        "landing_abs_y": {"target": m(tgt[:, 1].abs()), "planned_ball": m(L_plan[:, 1].abs()),
                          "commanded_paddle": m(L_cmd[:, 1].abs()), "realized": m(L_real[:, 1].abs())},
        "gap_x": {"planner (commanded - target)": m(L_cmd[:, 0] - tgt[:, 0]),
                  "controller (realized - commanded)": m(L_real[:, 0] - L_cmd[:, 0]),
                  "of which incoming spin (commanded - commanded without it)": m(L_cmd[:, 0] - L_cmd0[:, 0]),
                  "of which outgoing spin (commanded - flown without spin)": m(L_cmd[:, 0] - L_cmd_nospin[:, 0])},
        "gap_abs_dist": {"planner": m((L_cmd - tgt).norm(dim=-1)), "controller": m((L_real - L_cmd).norm(dim=-1)),
                         "total": m((L_real - tgt).norm(dim=-1))},
        "speed": {"planned": m(v_plan.norm(dim=-1)), "commanded_paddle": m(v_cmd.norm(dim=-1)),
                  "realized": m(v_real.norm(dim=-1))},
        "direction_error_deg_median": {"commanded vs planned": med(ang(v_cmd, v_plan)),
                                       "realized vs commanded": med(ang(v_real, v_cmd))},
        "face_normal_error_deg_median": med(face_err),
        "paddle_velocity_error_median": {"abs_m_s": med((pv - v_star).norm(dim=-1)), "angle_deg": med(ang(pv, v_star))},
        "contact_offset_from_face_centre_median_m": med(off_plane),
        "sanity_exec_vs_sim_speed_rel_median": med((v_exec - v_real).norm(dim=-1) / v_real.norm(dim=-1).clamp(min=0.1)),
    }


def face_factor_separation(rows: torch.Tensor, p: BallParams | None = None) -> dict:
    """D-128 pre-launch check: how far each face factor separates the contacts whose realized shot lands nearer its
    target (the better half, by landing distance) from the worse half. Rank statistics cannot tell monotone forms of
    the same angle apart, so the check is the difference of the factor's means (reward units)."""
    from picklebot_mj.tasks.timed_reach import face_factor
    p = p or BallParams()
    r = rows.float()
    c, n_r, n_star, tgt, tau = r[:, 0:3], r[:, 12:15], r[:, 30:33], r[:, 36:38], r[:, 42]
    L_real, _, ok = land(c, r[:, 21:24], r[:, 24:27], p)
    use = ok & (tau.abs() <= 0.10)
    err = (L_real - tgt).norm(dim=-1)[use]
    align = (n_r * n_star).sum(-1).abs()[use]
    good = err <= err.median()
    out = {"contacts": int(use.sum())}
    for name in ("half", "linear30"):
        fa = face_factor(align, name)
        out[name] = {"better_half_mean": round(float(fa[good].mean()), 4), "worse_half_mean": round(float(fa[~good].mean()), 4),
                     "separation": round(float(fa[good].mean() - fa[~good].mean()), 4)}
    return out
