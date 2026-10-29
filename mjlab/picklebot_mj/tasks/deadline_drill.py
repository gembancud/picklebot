"""Agility screen drill and logging (docs/research/footwork-route-2026-10-29.md sections 5e and 6). New file: nothing in
move_drill.py or return_stand.py is changed; the classes here are swapped in by `AgilityBallAction` (tasks/agility.py).

DeadlineMoveDrill (a MoveDrill): time-pressured, direction-labelled move-to-spot episodes.
- Spots at DIST 1.0-3.0 m in the 8 MoveDrill sectors (world frame: 0 = toward the net, counter-clockwise; the robot is
  turned to face the net near every spot, so this is also the robot's frame at each spot's start), uniform weights.
- A required speed v_req ~ U(1.2, 2.0) m/s per spot; deadline = 0.3 s + d / v_req (d: start-to-spot distance).
- Internal teacher command (move_track_lin_vel): toward the spot at min(v_req, k d), k = 1.2 v_req / 1.0, i.e.
  MoveDrill's law with its cap raised to v_req and its gain scaled so the slow-down still starts 0.83 m out (with the
  old gain 1.2 a 2 m/s command would start braking 1.7 m out and could not make the deadline). Heading (route E):
  free beyond HEADING_FREE_M of the spot (agility_track_yaw drops the yaw-rate term), toward the net inside it.
- Arrival is MoveDrill's (within 0.25 m, slower than 0.2 m/s, held 0.3 s). The arrival bonus (move_arrival) is paid
  only for arrivals before the deadline. The spot then stays live until MoveDrill's untimed limit
  (1.5 s + 1.25 s/m), so untimed arrival is measured in the same episodes (deadline_ends_spot=True: the spot ends at
  the deadline instead).
- Counted per sector (masked tensor math, no host syncs): issued, arrivals (any time), arrivals before the deadline,
  untimed time-outs, falls (episode ended by fell_over during the spot), censored spots (episode time limit), the
  spot's peak pelvis ground speed (sum and histogram), and, on residual executors, the residual saturation share
  (physics steps with >= 4 latent dimensions at |tanh(a)| > 0.95, over move-episode steps).

DirectionTally: feeder balls in training split by the direction the robot had to move, ported from
scripts/diag/feeder_speed_envelope.py (pelvis at the feed's start to the ball at its closest approach to the paddle,
in the start heading frame; forward / left / back / right quadrants). Per direction: feeds, contact, legal, peak
pelvis speed, onset latency (the first control step after the feed's start at which pelvis velocity toward that
closest-approach point exceeds 0.5 m/s; histogram, a last bin for never) and the residual saturation share over the
approach (feed start to the first legal contact). It wraps the instance's PairCourts.step, as the envelope read does.
"""

from __future__ import annotations

import math

import torch

from picklebot_mj.tasks import move_drill as md
from picklebot_mj.tasks.latent_reach import _to_heading, _yaw_frame

DIST_RANGE = (1.0, 3.0)
V_REQ_RANGE = (1.2, 2.0)
DEADLINE_BASE_S = 0.3
HEADING_FREE_M = 1.0
SAT_TANH, SAT_DIMS = 0.95, 4
SPEED_BIN, SPEED_BINS = 0.1, 50  # peak speed histogram, m/s (last bin: >= 4.9 m/s)
ONSET_SPEED = 0.5  # m/s toward the closest-approach point
ONSET_WINDOW_S = 3.0
N_DIRS = 4


def residual_saturated(env) -> torch.Tensor | None:
    """Per env: at least SAT_DIMS residual latent dimensions at |tanh(a)| > SAT_TANH (None: no residual action term)."""
    am = env.action_manager
    try:
        term = am.get_term("latent")
    except Exception:  # noqa: BLE001 (flat joint-space policy: no latent term)
        return None
    if not hasattr(term, "a_ref") or not hasattr(term.cfg, "lam_r"):
        return None
    a = term.raw_action[:, :term.cfg.latent]
    return (torch.tanh(a).abs() > SAT_TANH).sum(-1) >= SAT_DIMS


class DeadlineMoveDrill(md.MoveDrill):
    def __init__(self, term, move_prob: float, seed: int, sector_weights=None, dist_range=DIST_RANGE,
                 v_req_range=V_REQ_RANGE, deadline_ends_spot: bool = False, heading_free_m: float = HEADING_FREE_M):
        super().__init__(term, move_prob, seed, sector_weights)
        n, dev = self.n, self.dev
        self.dist_range = (float(dist_range[0]), float(dist_range[1]))
        self.v_range = (float(v_req_range[0]), float(v_req_range[1]))
        assert 0 < self.dist_range[0] <= self.dist_range[1] and 0 < self.v_range[0] <= self.v_range[1]
        self.deadline_ends_spot, self.heading_free_m = bool(deadline_ends_spot), float(heading_free_m)
        self.v_req = torch.full((n,), self.v_range[0], device=dev)
        self.deadline = torch.ones(n, device=dev)
        self.peak = torch.zeros(n, device=dev)
        z = lambda *s: torch.zeros(*s, dtype=torch.long, device=dev)
        for k in ("deadline", "fell", "censored", "sat_steps", "move_steps"):
            self.stats[k] = z(md.N_SECTORS)
        self.peak_sum = torch.zeros(md.N_SECTORS, device=dev)
        self.peak_hist = z(md.N_SECTORS, SPEED_BINS)
        self._sat_fn = None  # looked up on the first update (host-side, once)

    # ------------------------------------------------------------------------------
    def reset(self, env_ids: torch.Tensor) -> None:
        """Count the spot an episode end cut short (a fall, or the episode time limit), then MoveDrill's reset."""
        env = getattr(self.t, "_env", None)
        if env is not None and env.common_step_counter > 0 and len(env_ids):
            fell = env.termination_manager.get_term("fell_over")[env_ids].bool()
            was = self.move_ep[env_ids]
            sec = self.sector[env_ids]
            self.stats["fell"].index_add_(0, sec, (was & fell).long())
            self.stats["censored"].index_add_(0, sec, (was & ~fell).long())
        super().reset(env_ids)

    def _new_spot(self, mask: torch.Tensor) -> None:
        """MoveDrill._new_spot with this drill's distance range, plus v_req and the deadline."""
        t = self.t
        here = t.pelvis_xy()
        lo, hi = self.dist_range
        sec = torch.multinomial(self.sector_w, self.n, replacement=True, generator=self.gen)
        ang = (sec.float() + torch.rand(self.n, generator=self.gen, device=self.dev)) * (2 * math.pi / md.N_SECTORS) \
            - math.pi / md.N_SECTORS
        dist = lo + (hi - lo) * torch.rand(self.n, generator=self.gen, device=self.dev)
        v = self.v_range[0] + (self.v_range[1] - self.v_range[0]) * torch.rand(self.n, generator=self.gen,
                                                                               device=self.dev)
        u = torch.stack([torch.cos(ang), torch.sin(ang)], -1)
        room = self._room(here, u)
        flip = room < lo  # as MoveDrill: reverse when even the minimum distance leaves the box
        u = torch.where(flip.unsqueeze(-1), -u, u)
        sec = torch.where(flip, (sec + md.N_SECTORS // 2) % md.N_SECTORS, sec)
        dist = torch.minimum(dist, self._room(here, u)).clamp(min=0.0)
        spot = (here + dist.unsqueeze(-1) * u).clamp(self._lo, self._hi)
        m = mask.unsqueeze(-1)
        t.recover_xy = torch.where(m, spot, t.recover_xy)
        self.start_xy = torch.where(m, here, self.start_xy)
        self.sector = torch.where(mask, sec, self.sector)
        d0 = (spot - here).norm(dim=-1)
        dl = DEADLINE_BASE_S + d0 / v
        untimed = md.TIME_BASE_S + md.TIME_PER_M * d0
        self.limit = torch.where(mask, dl if self.deadline_ends_spot else torch.maximum(untimed, dl), self.limit)
        self.deadline = torch.where(mask, dl, self.deadline)
        self.v_req = torch.where(mask, v, self.v_req)
        self.elapsed = torch.where(mask, torch.zeros_like(self.elapsed), self.elapsed)
        self.hold = torch.where(mask, torch.zeros_like(self.hold), self.hold)
        self.peak = torch.where(mask, torch.zeros_like(self.peak), self.peak)
        self.stats["issued"].index_add_(0, self.sector, mask.long())

    # ------------------------------------------------------------------------------
    def update(self, dt: float) -> None:
        """MoveDrill.update with the deadline: the bonus only for arrivals before it, and the extra counters."""
        t = self.t
        mv = self.move_ep
        here = t.pelvis_xy()
        d = (t.recover_xy - here).norm(dim=-1)
        data = t._entity.data
        speed = data.root_link_lin_vel_b[:, :2].norm(dim=-1)
        ground = data.root_link_lin_vel_w[:, :2].norm(dim=-1)
        self.peak = torch.where(mv, torch.maximum(self.peak, ground), self.peak)
        inside = mv & (d < md.ARRIVE_RADIUS) & (speed < md.ARRIVE_SPEED)
        self.hold = torch.where(inside, self.hold + dt, torch.zeros_like(self.hold))
        self.elapsed = self.elapsed + dt * mv.float()
        arrived = mv & (self.hold >= md.ARRIVE_HOLD_S)
        in_time = arrived & (self.elapsed <= self.deadline + 1e-6)
        timed_out = mv & ~arrived & (self.elapsed >= self.limit)
        done = arrived | timed_out
        self.arrive_now |= in_time  # move_arrival pays only before the deadline
        sec = self.sector
        s = self.stats
        s["arrived"].index_add_(0, sec, arrived.long())
        s["deadline"].index_add_(0, sec, in_time.long())
        s["timed_out"].index_add_(0, sec, timed_out.long())
        s["ready"].index_add_(0, sec, (arrived & self.ready_mask()).long())
        self.time_sum.index_add_(0, sec, self.elapsed * arrived.float())
        self.peak_sum.index_add_(0, sec, self.peak * done.float())
        pb = (self.peak.nan_to_num(nan=0.0, posinf=1e3) / SPEED_BIN).clamp(0, SPEED_BINS - 1).long()
        self.peak_hist.view(-1).index_add_(0, sec * SPEED_BINS + pb, done.long())
        if self._sat_fn is None:
            env = getattr(t, "_env", None)
            self._sat_fn = (lambda: residual_saturated(env)) if env is not None and residual_saturated(env) is not None \
                else (lambda: None)
        sat = self._sat_fn()
        s["move_steps"].index_add_(0, sec, mv.long())
        if sat is not None:
            s["sat_steps"].index_add_(0, sec, (mv & sat).long())
        if self.sampler is not None:  # finished spots: success = arrival before the deadline
            self.sampler.update(sec, in_time, done)
            self.sector_w = self.sampler.weights()
        b = (d.nan_to_num(nan=1e3, posinf=1e3, neginf=0.0) / md.ERR_BIN).clamp(0, md.ERR_BINS - 1).long()
        self.err_hist.view(-1).index_add_(0, sec * md.ERR_BINS + b, done.long())
        self._new_spot(done)

    # ------------------------------------------------------------------------------
    def yaw_free(self) -> torch.Tensor:
        """Heading is free (no yaw-rate tracking) beyond heading_free_m of the spot."""
        return (self.t.recover_xy - self.t.pelvis_xy()).norm(dim=-1) > self.heading_free_m

    def command(self):
        """Teacher command (body-frame vx, vy, wz): toward the spot at min(v_req, k d), k = 1.2 v_req / 1.0; facing the
        net inside heading_free_m (wz is 0 and untracked beyond it)."""
        t, robot = self.t, self.t._entity
        yaw = md._yaw(robot.data.root_link_pose_w[:, 3:7])
        delta = t.recover_xy - t.pelvis_xy()
        d = delta.norm(dim=-1, keepdim=True)
        v_req = self.v_req.unsqueeze(-1)
        gain = md.CMD_GAIN * v_req / md.CMD_MAX_SPEED
        v_w = delta / d.clamp(min=1e-6) * torch.minimum(gain * d, v_req)
        c, s = torch.cos(yaw), torch.sin(yaw)
        v_b = torch.stack([c * v_w[:, 0] + s * v_w[:, 1], -s * v_w[:, 0] + c * v_w[:, 1]], -1)
        heading_err = torch.atan2(torch.sin(-yaw), torch.cos(-yaw))
        wz = (md.HEADING_STIFFNESS * heading_err).clamp(-md.CMD_MAX_YAW_RATE, md.CMD_MAX_YAW_RATE)
        wz = torch.where(d.squeeze(-1) > self.heading_free_m, torch.zeros_like(wz), wz)
        return v_b, wz

    def counters(self) -> dict:
        """Cumulative counters for the training log (one host sync per call)."""
        out = {k: v.tolist() for k, v in self.stats.items()}
        out["time_sum"] = [round(x, 4) for x in self.time_sum.tolist()]
        out["peak_sum"] = [round(x, 4) for x in self.peak_sum.tolist()]
        out["peak_hist"] = self.peak_hist.tolist()
        return out

    def summary(self) -> dict:
        from picklebot_mj import agility_rule
        out = super().summary()
        out["agility"] = agility_rule.arm_stats(self.counters())
        return out


def agility_track_yaw(env, std: float = math.sqrt(0.5)) -> torch.Tensor:
    """move_track_yaw with the deadline drill's free heading: beyond heading_free_m the yaw-rate error is dropped (the
    roll / pitch rate term stays). Falls back to move_track_yaw for any other drill."""
    dr = md._drill(env)
    if dr is None:
        return torch.zeros(env.num_envs, device=env.device)
    if not isinstance(dr, DeadlineMoveDrill):
        return md.move_track_yaw(env, std)
    _, wz = dr.command()
    w = dr.t._entity.data.root_link_ang_vel_b
    yaw_err = torch.where(dr.yaw_free(), torch.zeros_like(wz), (wz - w[:, 2]) ** 2)
    err = yaw_err + (w[:, :2] ** 2).sum(-1)
    return torch.exp(-err / std ** 2) * md._walk_mask(dr)


# ----------------------------------------------------------------------------------------
class DirectionTally:
    """Feeder-ball outcomes by direction in pair-mode training (logging only)."""

    def __init__(self, term, env):
        self.t, self.env = term, env
        pc = term.pairs
        assert pc is not None, "the direction tally hooks PairCourts.step (pair mode)"
        n, dev = term.num_envs, term.device
        self.n, self.dev = n, dev
        self.decimation = int(getattr(env.cfg, "decimation", 1))
        self.step_s = float(env.physics_dt) * self.decimation
        self.T = max(1, int(round(ONSET_WINDOW_S / self.step_s)))
        z = lambda *s: torch.zeros(*s, device=dev)
        zl = lambda *s: torch.zeros(*s, dtype=torch.long, device=dev)
        self.peak, self.dmin = z(n), torch.full((n,), 1e3, device=dev)
        self.ball_at, self.p0 = z(n, 2), z(n, 2)
        self.c0, self.s0 = torch.ones(n, device=dev), z(n)
        self.k = zl(n)  # control steps recorded since the feed's start
        self.pos_buf, self.vel_buf = z(n, self.T, 2), z(n, self.T, 2)
        self.appr, self.sat_n = zl(n), zl(n)
        self._ar = torch.arange(self.T, device=dev)
        self._calls = 0
        self.c = {k: zl(N_DIRS) for k in ("feeds", "contact", "legal", "approach_steps", "sat_steps")}
        self.c_hand = {k: zl(N_DIRS) for k in ("feeds", "contact", "legal")}  # partner balls (reported, not ruled)
        self.peak_sum = z(N_DIRS)
        self.onset_hist = zl(N_DIRS, self.T + 1)  # last bin: never within the feed (or the window)
        self._orig = pc.step
        pc.step = self.step
        self.start(torch.ones(n, dtype=torch.bool, device=dev))

    def _robot(self):
        return self.t._entity.data

    def start(self, mask: torch.Tensor) -> None:
        data = self._robot()
        root = data.root_link_pose_w
        origins = self.env.scene.env_origins
        c, s = _yaw_frame(root[:, 3:7])
        self.p0 = torch.where(mask.unsqueeze(-1), root[:, :2] - origins[:, :2], self.p0)
        self.c0 = torch.where(mask, c, self.c0)
        self.s0 = torch.where(mask, s, self.s0)
        self.peak = torch.where(mask, torch.zeros_like(self.peak), self.peak)
        self.dmin = torch.where(mask, torch.full_like(self.dmin, 1e3), self.dmin)
        for name in ("k", "appr", "sat_n"):
            v = getattr(self, name)
            setattr(self, name, torch.where(mask, torch.zeros_like(v), v))

    def direction(self) -> torch.Tensor:
        rel = _to_heading(torch.cat([self.ball_at - self.p0, torch.zeros(self.n, 1, device=self.dev)], -1),
                          self.c0, self.s0)[:, :2]
        ang = torch.atan2(rel[:, 1], rel[:, 0])  # 0 forward, +pi/2 left
        return (((ang + math.pi / 4) % (2 * math.pi)) // (math.pi / 2)).long().clamp(0, N_DIRS - 1)

    def onset_index(self) -> torch.Tensor:
        """Per env: the first recorded control step with pelvis velocity toward ball_at > ONSET_SPEED (T: never)."""
        to = self.ball_at.unsqueeze(1) - self.pos_buf
        u = to / to.norm(dim=-1, keepdim=True).clamp(min=1e-6)
        vt = (self.vel_buf * u).sum(-1)
        ok = (vt > ONSET_SPEED) & (self._ar.unsqueeze(0) < self.k.unsqueeze(1))
        first = torch.argmax(ok.int(), dim=1)
        return torch.where(ok.any(1), first, torch.full_like(first, self.T))

    def observe(self) -> None:
        """Per physics step: peak speed, closest approach, approach saturation; once per control step the onset sample."""
        t, data = self.t, self._robot()
        origins = self.env.scene.env_origins
        root = data.root_link_pose_w
        vel = data.root_link_lin_vel_w[:, :2]
        self.peak = torch.maximum(self.peak, vel.norm(dim=-1))
        paddle = data.body_link_pose_w[:, t.paddle_id, :3] - origins
        d = (t.ball.pos - paddle).norm(dim=-1)
        closer = d < self.dmin
        self.dmin = torch.where(closer, d, self.dmin)
        self.ball_at = torch.where(closer.unsqueeze(-1), t.ball.pos[:, :2], self.ball_at)
        appr = ~t.hit_done
        self.appr = self.appr + appr.long()
        sat = residual_saturated(self.env)
        if sat is not None:
            self.sat_n = self.sat_n + (appr & sat).long()
        if self._calls % self.decimation == 0:  # one sample per control step (host-side counter, no sync)
            rec = self.k < self.T
            idx = self.k.clamp(max=self.T - 1)
            ar = torch.arange(self.n, device=self.dev)
            pos = root[:, :2] - origins[:, :2]
            self.pos_buf[ar, idx] = torch.where(rec.unsqueeze(-1), pos, self.pos_buf[ar, idx])
            self.vel_buf[ar, idx] = torch.where(rec.unsqueeze(-1), vel, self.vel_buf[ar, idx])
            self.k = self.k + rec.long()
        self._calls += 1

    def record(self, m: torch.Tensor, legal: torch.Tensor) -> None:
        """Count the feeds ending in mask m (feeder balls by direction; partner balls apart)."""
        pc, t = self.t.pairs, self.t
        k = self.direction()
        feeder = m & ~pc.handed
        hand = m & pc.handed
        for cnt, mm in ((self.c, feeder), (self.c_hand, hand)):
            cnt["feeds"].index_add_(0, k, mm.long())
            cnt["contact"].index_add_(0, k, (mm & t.hit_done).long())
            cnt["legal"].index_add_(0, k, (mm & legal).long())
        self.c["approach_steps"].index_add_(0, k, self.appr * feeder.long())
        self.c["sat_steps"].index_add_(0, k, self.sat_n * feeder.long())
        self.peak_sum.index_add_(0, k, self.peak * feeder.float())
        o = self.onset_index()
        self.onset_hist.view(-1).index_add_(0, k * (self.T + 1) + o, feeder.long())

    def step(self, over, legal, fell, crossing, dt, delay, contact=None, busy=None):
        pc = self.t.pairs
        self.observe()
        live = ~pc.court_dead.repeat(2)
        o = over
        if contact is not None:  # as pairs.py counts them (D-135), as in feeder_speed_envelope.py
            w = pc.waiting & ~contact
            o = over & ~(w & ~legal & (over & ~legal)[pc.partner])
        self.record(o & live, legal)
        fire, recv = self._orig(over, legal, fell, crossing, dt, delay, contact=contact, busy=busy)
        self.start(fire | recv)
        return fire, recv

    def counters(self) -> dict:
        out = {k: v.tolist() for k, v in self.c.items()}
        out["handed"] = {k: v.tolist() for k, v in self.c_hand.items()}
        out["peak_sum"] = [round(x, 4) for x in self.peak_sum.tolist()]
        out["onset_hist"] = self.onset_hist.tolist()
        out["onset_bin_s"] = self.step_s
        return out
