"""Stage 5G timed reach (D-118): the H3 latent-reach controller made goal-conditioned in time.

A goal is the paddle state at a contact time t*: face-centre position p*, velocity v* and face normal n*, plus a root
(pelvis) target. Goals come from a goal bank built offline by the Stage 5G planner (scripts/build_goal_bank.py: real
feeds and the robot's own returns, contact by the spin-blind planner, a keep-it-alive outgoing ball, the paddle state
from the impact model). Bank entries are in the robot's heading frame at the time the goal is set (x forward, y left).

Command (15, heading frame): paddle target - paddle (3), paddle target - right shoulder (3), root target - pelvis (2),
time to contact tau (1), v* (3), n* (3). The first 9 have the layout of the H3 ReachCommand (the ninth is now the time
to contact), so an H3 checkpoint expands with zero-weight inputs for the last 6.

Rewards (D-118):
- `timed_contact`, one-shot at t*: exp(-(|dp| / 0.10)^2) * exp(-(|dv| / 1.0)^2) * (0.5 + 0.5 |n . n*|) (either paddle
  face may strike);
- `swing_guide`, dense: the paddle near the swing path p* - v* * min(tau, 0.3), so it arrives at p* moving at v*
  instead of parking at p*;
plus the H3 root, root-progress, prior, falls and action-rate terms.

Statistics per scored goal (no host syncs): paddle error at t* (1 cm bins), relative paddle-speed error (2 % bins),
timing error of the closest approach within the window (5 ms bins), root within 0.25 m at t*.
"""

from __future__ import annotations

from dataclasses import dataclass

import torch
from mjlab.managers.command_manager import CommandTerm, CommandTermCfg

from picklebot_mj.tasks.latent_reach import _to_heading, _yaw_frame

GAP_S = (0.3, 0.8)  # recovery time after t* before the next goal
TIMING_WINDOW = (0.25, 0.10)  # D-122: the closest approach counts only within [t* - 0.25 s, t* + 0.10 s]
SPEED_BIN, SPEED_BINS = 0.5, 6  # required root speed |root_rel| / t*, 0.5 m/s bins (the last bin is open)
REACHABLE = 1.5  # m/s: goals at or below it count as reachable in the paddle-error report (round 13b)
SWING_LEAD_S = 0.3
BINS = 100


@dataclass(kw_only=True)
class TimedReachCommandCfg(CommandTermCfg):
    entity_name: str = "robot"
    paddle_body: str = "paddle"
    shoulder_body: str = "right_shoulder_pitch_link"
    bank: str = ""  # goal bank .pt: [M, 12] = p*_rel (3, from the ground point under the pelvis), v* (3), n* (3), t* (1),
    #                root_rel (2); heading frame
    resampling_time_range: tuple[float, float] = (1.0, 1.0)  # overridden per goal: t* + gap
    debug_vis: bool = False

    def build(self, env):
        return TimedReachCommand(self, env)


def _rot(vec, c, s):
    """Heading-frame vectors (N, 3) or (N, 2) into the world frame."""
    out = vec.clone()
    out[..., 0] = c * vec[..., 0] - s * vec[..., 1]
    out[..., 1] = s * vec[..., 0] + c * vec[..., 1]
    return out


class TimedReachCommand(CommandTerm):
    cfg: TimedReachCommandCfg

    def __init__(self, cfg, env):
        super().__init__(cfg, env)
        self.robot = env.scene[cfg.entity_name]
        self.paddle = list(self.robot.body_names).index(cfg.paddle_body)
        self.shoulder = list(self.robot.body_names).index(cfg.shoulder_body)
        self.bank = torch.load(cfg.bank, map_location=self.device).float()
        assert self.bank.shape[1] == 12, self.bank.shape
        n, dev = self.num_envs, self.device
        z3 = lambda: torch.zeros(n, 3, device=dev)  # noqa: E731
        self.p_star, self.v_star, self.n_star = z3(), z3(), z3()
        self.root_target = torch.zeros(n, 2, device=dev)
        self.t_contact = torch.full((n,), 1e9, device=dev)  # contact time on the env's episode clock
        self.scored = torch.ones(n, dtype=torch.bool, device=dev)
        self.min_dp = torch.full((n,), 1e9, device=dev)
        self.t_min = torch.zeros(n, device=dev)
        self.gen = torch.Generator(device=dev).manual_seed(int(getattr(env.cfg, "seed", 0) or 0) + 777)
        self.stats = {k: torch.zeros(BINS + 1, dtype=torch.long, device=dev) for k in ("dp", "dv_rel", "dt")}
        self.counts = torch.zeros(3, dtype=torch.long, device=dev)  # goals scored, root within 0.25 m, timing <= 50 ms
        # D-122 timing: the closest approach only within [t* - 0.25, t* + 0.10] (the old whole-window metric kept
        # alongside); counts_w = (goals closed, timing <= 50 ms). Root hits by the speed the goal requires.
        self.min_dp_w = torch.full((n,), 1e9, device=dev)
        self.t_min_w = torch.full((n,), -1e9, device=dev)
        self.counts_w = torch.zeros(2, dtype=torch.long, device=dev)
        self.req_speed = torch.zeros(n, device=dev)
        self.root_by_speed = torch.zeros(SPEED_BINS, 2, dtype=torch.long, device=dev)  # goals, root within 0.25 m
        # D-124 round 13b (report only): legal returns and falls by the required speed of the env's current goal, and
        # the paddle error at t* of reachable goals (required speed <= REACHABLE m/s)
        self.ball_by_speed = torch.zeros(SPEED_BINS, 2, dtype=torch.long, device=dev)  # legal returns, falls
        self.stats["dp_reach"] = torch.zeros(BINS + 1, dtype=torch.long, device=dev)
        self.metrics["paddle_dist"] = torch.zeros(n, device=dev)

    def clock(self) -> torch.Tensor:
        return self._env.episode_length_buf.float() * self._env.step_dt

    @property
    def command(self):
        d = self.robot.data
        c, s = _yaw_frame(d.root_link_quat_w)
        pad = d.body_link_pos_w[:, self.paddle]
        sh = d.body_link_pos_w[:, self.shoulder]
        rel_r = torch.zeros(self.num_envs, 3, device=self.device)
        rel_r[:, :2] = self.root_target - d.root_link_pos_w[:, :2]
        tau = (self.t_contact - self.clock()).clamp(-1.0, 2.0)
        return torch.cat([_to_heading(self.p_star - pad, c, s), _to_heading(self.p_star - sh, c, s),
                          _to_heading(rel_r, c, s)[:, :2], tau.unsqueeze(-1), _to_heading(self.v_star, c, s),
                          _to_heading(self.n_star, c, s)], -1)

    def paddle_state(self):
        d = self.robot.data
        from picklebot_mj.tasks.return_stand import _quat_to_matrix  # noqa: PLC0415  (the ball term's helper)
        pose = d.body_link_pose_w[:, self.paddle]
        normal = _quat_to_matrix(pose[:, 3:7])[:, :, 2]
        return pose[:, :3], d.body_link_vel_w[:, self.paddle, :3], normal

    def distances(self):
        """(paddle to p*, pelvis to root target): the H3 reward terms read this."""
        d = self.robot.data
        return ((d.body_link_pos_w[:, self.paddle] - self.p_star).norm(dim=-1),
                (d.root_link_pos_w[:, :2] - self.root_target).norm(dim=-1))

    def _update_metrics(self):
        pos, _, _ = self.paddle_state()
        dp = (pos - self.p_star).norm(dim=-1)
        closer = dp < self.min_dp
        self.min_dp = torch.where(closer, dp, self.min_dp)
        self.t_min = torch.where(closer, self.clock(), self.t_min)
        now = self.clock()
        in_w = (now >= self.t_contact - TIMING_WINDOW[0] - 1e-6) & (now <= self.t_contact + TIMING_WINDOW[1] + 1e-6)
        closer_w = in_w & (dp < self.min_dp_w)
        self.min_dp_w = torch.where(closer_w, dp, self.min_dp_w)
        self.t_min_w = torch.where(closer_w, now, self.t_min_w)
        self.metrics["paddle_dist"] = dp

    def _resample_command(self, env_ids):
        # Close the previous goal of these envs: the timing error of the closest approach.
        done = env_ids[self.scored[env_ids] & (self.t_contact[env_ids] < 1e8)]
        if len(done):
            dt = (self.t_min[done] - self.t_contact[done]).abs()
            self.stats["dt"].index_add_(0, (dt / 0.005).clamp(max=BINS).long(), torch.ones_like(done))
            self.counts[2] += (dt <= 0.05).sum()
            dtw = (self.t_min_w[done] - self.t_contact[done]).abs()  # D-122; no window visit -> a huge error (fail)
            self.counts_w += torch.stack([torch.ones_like(dtw).sum().long(), (dtw <= 0.05).sum()])
        d = self.robot.data
        k = len(env_ids)
        g = self.bank[torch.randint(0, self.bank.shape[0], (k,), generator=self.gen, device=self.device)]
        c, s = _yaw_frame(d.root_link_quat_w[env_ids])
        pel = d.root_link_pos_w[env_ids].clone()
        pel[:, 2] = 0.0  # bank positions are relative to the ground point under the pelvis
        self.p_star[env_ids] = pel + _rot(g[:, 0:3], c, s)
        self.v_star[env_ids] = _rot(g[:, 3:6], c, s)
        self.n_star[env_ids] = _rot(g[:, 6:9], c, s)
        self.root_target[env_ids] = pel[:, :2] + _rot(g[:, 10:12], c, s)
        now = self.clock()[env_ids]
        t_star = (g[:, 9] / self._env.step_dt).round() * self._env.step_dt  # D-119 fix (b): on the control grid
        self.t_contact[env_ids] = now + t_star
        gap = GAP_S[0] + (GAP_S[1] - GAP_S[0]) * torch.rand(k, generator=self.gen, device=self.device)
        self.time_left[env_ids] = t_star + gap
        self.scored[env_ids] = False
        self.min_dp[env_ids] = 1e9
        self.min_dp_w[env_ids] = 1e9
        self.t_min_w[env_ids] = -1e9
        self.req_speed[env_ids] = g[:, 10:12].norm(dim=-1) / t_star.clamp(min=0.05)

    def _update_command(self, env_ids):
        pass

    def reset(self, env_ids):
        """D-119 fix (a): mjlab resamples at reset before the episode clock and the robot pose are reset, so that goal
        would use the old clock and pose. Zero its timer: the post-reset compute (dt = 0) resamples it on the new
        clock and pose. The stale goal is never scored."""
        extras = super().reset(env_ids)
        self.time_left[env_ids] = 0.0
        return extras

    def contact_now(self):
        """One-shot: goals whose contact time has come and that are not yet scored (marks them scored). t* sits on the
        control-step grid (D-119 fix b), so the step at clock >= t_contact - step_dt / 2 is the contact step."""
        ev = ~self.scored & (self.clock() >= self.t_contact - 0.5 * self._env.step_dt)
        self.scored |= ev
        return ev

    def summary(self) -> dict:
        n = int(self.counts[0])

        def q(name, w, f):
            h = self.stats[name].cpu()
            tot = int(h.sum())
            if not tot:
                return None
            c = h.cumsum(0)
            return round(float((c >= f * tot).nonzero()[0, 0]) * w, 4)

        return {"goals_scored": n,
                "paddle_err_median_m": q("dp", 0.01, 0.5), "paddle_err_p90_m": q("dp", 0.01, 0.9),
                "speed_err_rel_median": q("dv_rel", 0.02, 0.5),
                "timing_within_50ms": round(int(self.counts_w[1]) / max(int(self.counts_w[0]), 1), 4),  # D-122
                "timing_within_50ms_old_whole_window": round(int(self.counts[2]) / max(int(self.stats["dt"].sum()), 1), 4),
                "root_within_25cm_by_required_speed": {
                    f"{i * SPEED_BIN:.1f}-{(i + 1) * SPEED_BIN:.1f} m/s": [int(g), round(int(h) / max(int(g), 1), 4)]
                    for i, (g, h) in enumerate(self.root_by_speed.tolist()) if g},
                "legal_returns_and_falls_per_goal_by_required_speed": {
                    f"{i * SPEED_BIN:.1f}-{(i + 1) * SPEED_BIN:.1f} m/s": [round(lr / max(g, 1), 4), round(fl / max(g, 1), 4)]
                    for i, ((g, _), (lr, fl)) in enumerate(zip(self.root_by_speed.tolist(), self.ball_by_speed.tolist()))
                    if g},
                "paddle_err_p90_reachable_m": q("dp_reach", 0.01, 0.9),
                "paddle_err_over_50cm": round(int(self.stats["dp"][50:].sum()) / max(int(self.stats["dp"].sum()), 1), 4),
                "root_within_25cm": round(int(self.counts[1]) / max(n, 1), 4)}


def _cmd(env, command_name="reach") -> TimedReachCommand:
    return env.command_manager.get_term(command_name)


def contact_factors(dp, dv, v_star_norm, align, speed: str = "kernel"):
    """(position, speed, alignment) factors of the one-shot contact reward; the reward is their product.
    speed "kernel" (E1): exp(-(|dv| / 1 m/s)^2); "linear" (E2, D-119): 0.5 + 0.5 clamp(1 - |dv| / |v*|, 0, 1), whose
    0.5 floor paid a parked paddle; "linear0" (E3, D-121): clamp(1 - |dv| / |v*|, 0, 1), 0 for a parked paddle."""
    kp = torch.exp(-(dp / 0.10) ** 2)
    lin = (1.0 - dv / v_star_norm.clamp(min=0.1)).clamp(0.0, 1.0)
    fv = {"linear": 0.5 + 0.5 * lin, "linear0": lin}.get(speed)
    if fv is None:
        fv = torch.exp(-(dv / 1.0) ** 2)
    return kp, fv, 0.5 + 0.5 * align


def timed_contact(env, command_name="reach", speed: str = "kernel"):
    """One-shot at t* (factors: contact_factors); also records the per-goal statistics."""
    cmd = _cmd(env, command_name)
    ev = cmd.contact_now()
    pos, vel, normal = cmd.paddle_state()
    dp = (pos - cmd.p_star).norm(dim=-1)
    dv = (vel - cmd.v_star).norm(dim=-1)
    align = (normal * cmd.n_star).sum(-1).abs()
    kp, fv, fa = contact_factors(dp, dv, cmd.v_star.norm(dim=-1), align, speed)
    r = kp * fv * fa
    cmd.last_factors = (kp, fv, fa, ev, (vel * cmd.v_star).sum(-1) / cmd.v_star.norm(dim=-1).clamp(min=0.1))
    e = ev.long()
    cmd.counts[0] += e.sum()
    rd = (env.scene["robot"].data.root_link_pos_w[:, :2] - cmd.root_target).norm(dim=-1)
    cmd.counts[1] += (ev & (rd <= 0.25)).sum()
    b = (cmd.req_speed / SPEED_BIN).clamp(max=SPEED_BINS - 1).long()
    cmd.root_by_speed.index_put_((b, torch.zeros_like(b)), e, accumulate=True)
    cmd.root_by_speed.index_put_((b, torch.ones_like(b)), (ev & (rd <= 0.25)).long(), accumulate=True)
    cmd.stats["dp"].index_add_(0, (dp / 0.01).clamp(max=BINS).long(), e)
    cmd.stats["dp_reach"].index_add_(0, (dp / 0.01).clamp(max=BINS).long(), e * (cmd.req_speed <= REACHABLE).long())
    ball = env.action_manager._terms.get("ball")
    if ball is not None and hasattr(ball, "return_now"):  # read before legal_return clears the step flags
        cmd.ball_by_speed.index_put_((b, torch.zeros_like(b)), ball.return_now.long(), accumulate=True)
        cmd.ball_by_speed.index_put_((b, torch.ones_like(b)), env.termination_manager.terminated.long(), accumulate=True)
    sp_rel = (vel.norm(dim=-1) - cmd.v_star.norm(dim=-1)).abs() / cmd.v_star.norm(dim=-1).clamp(min=0.1)
    cmd.stats["dv_rel"].index_add_(0, (sp_rel / 0.02).clamp(max=BINS).long(), e)
    return r * ev.float()


def paddle_track_open(env, command_name="reach", std=0.15):
    """E2 (D-119): reach-06's paddle_track to p* while the goal is open (not yet scored)."""
    cmd = _cmd(env, command_name)
    dp, _ = cmd.distances()
    return torch.exp(-(dp / std) ** 2) * (~cmd.scored).float()


def swing_guide(env, command_name="reach", std=0.15):
    """Dense: the paddle near p* - v* * min(tau, SWING_LEAD_S) while the goal is open (the swing path into p*)."""
    cmd = _cmd(env, command_name)
    tau = (cmd.t_contact - cmd.clock()).clamp(0.0, SWING_LEAD_S).unsqueeze(-1)
    lead = cmd.p_star - cmd.v_star * tau
    pos, _, _ = cmd.paddle_state()
    return torch.exp(-((pos - lead).norm(dim=-1) / std) ** 2) * (~cmd.scored).float()


# --- Stage 5G zero-shot with the ball (D-118 order: E-run with the ball after the ball-free controller) --------------
@dataclass(kw_only=True)
class TimedBallCommandCfg(TimedReachCommandCfg):
    """Goals from the live ball: when the ball term's planner window closes for a feed (plan_pending falls; the
    D-097 delay after the launch), the noisy spin-blind planner gives the contact (point, time, ball velocity), a
    keep-it-alive outgoing ball and the paddle state; the root target is the stance spot beside the contact."""
    resampling_time_range: tuple[float, float] = (1e6, 1e6)  # goals come from the ball, not a timer
    walk_cap: float | None = None  # D-125: the walkable contact (planner.WALK_CAP m/s) instead of the first interception

    def build(self, env):
        return TimedBallCommand(self, env)


GOAL_BATCH = 128  # envs planned per control step (a multiple of planner.CONTACT_BUCKET); about n * 0.02 / 1.6 fall due


def plan_goals(pos, vel, pel, gen, walk_cap=None):
    """Goals for balls at (pos, vel) (court-local, the planner's noisy view) and pelvis xy `pel`: the spin-blind
    contact (point, ball velocity, time, found), a keep-it-alive outgoing ball and the paddle state for it, and the
    stance spot beside the contact. walk_cap (m/s, D-125): the walkable contact instead of the first interception.
    Returns (cx, ct, found, normal, paddle velocity, stance)."""
    from picklebot_mj.planner import (aim_outgoing_fast, keep_alive_target, paddle_for, predict_contact_fast,
                                      predict_contact_walkable)
    from picklebot_mj.tasks.shadow_swing import HINT_BEHIND, HINT_SIDE_BH, HINT_SIDE_FH
    if walk_cap is None:
        cx, cv, ct, found = predict_contact_fast(pos, vel, torch.zeros_like(pos))
    else:
        cx, cv, ct, found = predict_contact_walkable(pos, vel, torch.zeros_like(pos), pel, cap=walk_cap)
    tgt, T = keep_alive_target(len(pos), gen, pos.device)
    nrm, vp = paddle_for(cv, aim_outgoing_fast(cx, tgt, T))
    fh = cx[:, 1] <= pel[:, 1]
    stance = torch.stack([cx[:, 0] - HINT_BEHIND, torch.where(fh, cx[:, 1] + HINT_SIDE_FH, cx[:, 1] - HINT_SIDE_BH)], -1)
    return cx, ct, found, nrm, vp, stance


class TimedBallCommand(TimedReachCommand):
    def __init__(self, cfg, env):
        super().__init__(cfg, env)
        self._prev_pending = None
        self.goal_due = torch.zeros(self.num_envs, dtype=torch.bool, device=self.device)
        self.goals_set = torch.zeros((), dtype=torch.long, device=self.device)

    def reset(self, env_ids):
        extras = CommandTerm.reset(self, env_ids)  # no bank resample: the next feed's plan sets the goal
        self.scored[env_ids] = True
        self.t_contact[env_ids] = 1e9
        self.goal_due[env_ids] = False
        if self._prev_pending is not None:  # no false window-closed edge across the reset
            self._prev_pending[env_ids] = False
        return extras

    def _resample_command(self, env_ids):
        pass

    def _update_command(self, env_ids):
        """When the ball term's planner window closes for a feed (plan_pending falls), the feed is due a goal. A fixed
        batch of envs, due ones first, is planned each step (no host sync, one compiled shape); an env left over waits
        for the next step. A feed touched before its goal is planned gets none."""
        b = self._env.action_manager.get_term("ball")
        pend = b.plan_pending.clone()
        if self._prev_pending is None:
            self._prev_pending = pend
            return
        self.goal_due = (self.goal_due | (self._prev_pending & ~pend)) & ~b.hit_done
        self._prev_pending = pend
        idx = torch.topk(self.goal_due.float(), min(GOAL_BATCH, self.num_envs)).indices
        due = self.goal_due[idx]
        c = b._plan_cfg
        g = b.gen_plan
        k = len(idx)
        pos = b.ball.pos[idx] + c.pos_noise * torch.randn(k, 3, generator=g, device=self.device)
        vel = b.ball.vel[idx] + c.vel_noise * torch.randn(k, 3, generator=g, device=self.device)
        pel = b.pelvis_xy(idx)
        cx, ct, found, nrm, vp, stance = plan_goals(pos, vel, pel, self.gen, self.cfg.walk_cap)
        ok = due & found
        m3, m1 = ok.unsqueeze(-1), ok
        org = self._env.scene.env_origins[idx]
        closing = m1 & self.scored[idx] & (self.t_contact[idx] < 1e8)  # D-122 timing of the goal this one replaces
        dtw = (self.t_min_w[idx] - self.t_contact[idx]).abs()
        self.counts_w += torch.stack([closing.sum(), (closing & (dtw <= 0.05)).sum()])
        t_star = (ct / self._env.step_dt).round() * self._env.step_dt
        self.p_star[idx] = torch.where(m3, cx + org, self.p_star[idx])
        self.v_star[idx] = torch.where(m3, vp, self.v_star[idx])
        self.n_star[idx] = torch.where(m3, nrm, self.n_star[idx])
        self.root_target[idx] = torch.where(m3[:, :2], stance + org[:, :2], self.root_target[idx])
        self.t_contact[idx] = torch.where(m1, self.clock()[idx] + t_star, self.t_contact[idx])
        self.req_speed[idx] = torch.where(m1, (stance - pel).norm(dim=-1) / t_star.clamp(min=0.05), self.req_speed[idx])
        self.scored[idx] = self.scored[idx] & ~m1
        self.min_dp[idx] = torch.where(m1, torch.full_like(ct, 1e9), self.min_dp[idx])
        self.min_dp_w[idx] = torch.where(m1, torch.full_like(ct, 1e9), self.min_dp_w[idx])
        self.t_min_w[idx] = torch.where(m1, torch.full_like(ct, -1e9), self.t_min_w[idx])
        self.goal_due[idx] = self.goal_due[idx] & ~due  # planned (found or not)
        self.goals_set += ok.sum()
