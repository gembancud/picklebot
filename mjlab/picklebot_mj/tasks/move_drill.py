"""Stage 5 Drill 1 (D-041): move to a spot, no ball.

A fraction `move_prob` of robot episodes are *move episodes*: the ball is parked and its rally is
closed (no feeds, no tallies), and the robot is given a sequence of court spots through the same
`recovery` observation used for the recovery command. A new spot is issued after each arrival or
time-out. Spots are sampled in eight equal direction sectors around the robot (sector 0 = toward
the net, counter-clockwise; 4 = straight back) at 0.5-3 m, inside the robot's half court.

Walking is taught with mjlab's own velocity-tracking reward formulas, but the commanded velocity is
computed internally from the spot (toward it at min(1.0 m/s, 1.2 * distance), turning to face the
net). The robot never observes that command (the twist command stays zero), so the skill depends
only on the spot input, as it must during play. Arrival = within ARRIVE_RADIUS and slower than
ARRIVE_SPEED, held for ARRIVE_HOLD_S. It pays a one-shot bonus; near the spot a ready stance
(paddle up and in front) is rewarded.

All bookkeeping is masked tensor math (no host syncs); per-sector counters feed the evaluation.
"""

from __future__ import annotations

import math

import torch

from picklebot_mj.ball import BALL_RADIUS

N_SECTORS = 8
DIST_RANGE = (0.5, 3.0)
SPOT_BOX = ((-6.4, -2.4), (-2.8, 2.8))  # robot half court, clear of the kitchen and the sidelines
ARRIVE_RADIUS = 0.25
ARRIVE_SPEED = 0.2
ARRIVE_HOLD_S = 0.3
TIME_BASE_S, TIME_PER_M = 1.5, 1.25  # time limit = 1.5 s + 1.25 s/m of distance
CMD_MAX_SPEED, CMD_GAIN = 1.0, 1.2
HEADING_STIFFNESS, CMD_MAX_YAW_RATE = 0.5, 1.0
READY_FORWARD = (0.3, 0.5)  # paddle face centre ahead of the pelvis (pelvis yaw frame), m
READY_HEIGHT = (0.9, 1.2)  # paddle face centre height, m
READY_RADIUS = 0.4  # ready-stance reward active within this distance of the spot
PARK_POS = (5.5, 0.0, BALL_RADIUS)  # parked ball (far court) in move episodes
ERR_BIN, ERR_BINS = 0.05, 60


def _yaw(q: torch.Tensor) -> torch.Tensor:
    w, x, y, z = q.unbind(-1)
    return torch.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z))


class MoveDrill:
    def __init__(self, term, move_prob: float, seed: int, sector_weights=None):
        n, dev = term.num_envs, term.device
        w = torch.ones(N_SECTORS) if sector_weights is None else torch.tensor(sector_weights, dtype=torch.float32)
        assert w.shape == (N_SECTORS,) and (w > 0).all()
        self.sector_w = (w / w.sum()).to(dev)
        self.t, self.n, self.dev, self.move_prob = term, n, dev, float(move_prob)
        self.gen = torch.Generator(device=dev).manual_seed(int(seed) + 271829)  # own stream
        self.move_ep = torch.zeros(n, dtype=torch.bool, device=dev)
        self.start_xy = torch.zeros(n, 2, device=dev)
        self.sector = torch.zeros(n, dtype=torch.long, device=dev)
        self.elapsed = torch.zeros(n, device=dev)
        self.limit = torch.ones(n, device=dev)
        self.hold = torch.zeros(n, device=dev)
        self.arrive_now = torch.zeros(n, dtype=torch.bool, device=dev)
        z = lambda *s: torch.zeros(*s, dtype=torch.long, device=dev)
        self.stats = {"issued": z(N_SECTORS), "arrived": z(N_SECTORS), "timed_out": z(N_SECTORS),
                      "ready": z(N_SECTORS)}
        self.time_sum = torch.zeros(N_SECTORS, device=dev)
        self.err_hist = z(N_SECTORS, ERR_BINS)  # final error (arrival or time-out), per sector
        self._lo = torch.tensor([SPOT_BOX[0][0], SPOT_BOX[1][0]], device=dev)
        self._hi = torch.tensor([SPOT_BOX[0][1], SPOT_BOX[1][1]], device=dev)

    # ------------------------------------------------------------------------------
    def reset(self, env_ids: torch.Tensor) -> None:
        """Choose the episode type and, for move episodes, park the ball and issue the first spot."""
        t = self.t
        k = len(env_ids)
        mv = torch.rand(k, generator=self.gen, device=self.dev) < self.move_prob
        self.move_ep[env_ids] = mv
        mask = torch.zeros(self.n, dtype=torch.bool, device=self.dev)
        mask[env_ids] = mv
        # Close the rally without a fault tally: no feeds, no outcome counting, frozen parked ball.
        t.rules.fail(mask, torch.zeros(self.n, dtype=torch.long, device=self.dev), _fault_none_like())
        t._prev_dead |= mask
        t.tallied |= mask
        park = torch.tensor(PARK_POS, device=self.dev)
        m3 = mask.unsqueeze(-1)
        t.ball.pos.copy_(torch.where(m3, park, t.ball.pos))
        t.ball.vel.copy_(torch.where(m3, torch.zeros_like(t.ball.vel), t.ball.vel))
        t.ball.spin.copy_(torch.where(m3, torch.zeros_like(t.ball.spin), t.ball.spin))
        self.arrive_now[env_ids] = False
        self._new_spot(mask)

    def _new_spot(self, mask: torch.Tensor) -> None:
        """Issue a spot (balanced sectors, 0.5-3 m, inside SPOT_BOX) for envs in mask."""
        t = self.t
        here = t.pelvis_xy()
        sec = torch.multinomial(self.sector_w, self.n, replacement=True, generator=self.gen)
        ang = (sec.float() + torch.rand(self.n, generator=self.gen, device=self.dev)) * (2 * math.pi / N_SECTORS) \
            - math.pi / N_SECTORS
        dist = DIST_RANGE[0] + (DIST_RANGE[1] - DIST_RANGE[0]) * torch.rand(self.n, generator=self.gen, device=self.dev)
        u = torch.stack([torch.cos(ang), torch.sin(ang)], -1)
        # Shrink along the direction to stay in the box; if even the minimum distance leaves it, reverse.
        room = self._room(here, u)
        flip = room < DIST_RANGE[0]
        u = torch.where(flip.unsqueeze(-1), -u, u)
        sec = torch.where(flip, (sec + N_SECTORS // 2) % N_SECTORS, sec)
        dist = torch.minimum(dist, self._room(here, u)).clamp(min=0.0)
        spot = (here + dist.unsqueeze(-1) * u).clamp(self._lo, self._hi)
        m = mask.unsqueeze(-1)
        t.recover_xy = torch.where(m, spot, t.recover_xy)
        self.start_xy = torch.where(m, here, self.start_xy)
        self.sector = torch.where(mask, sec, self.sector)
        d0 = (spot - here).norm(dim=-1)
        self.limit = torch.where(mask, TIME_BASE_S + TIME_PER_M * d0, self.limit)
        self.elapsed = torch.where(mask, torch.zeros_like(self.elapsed), self.elapsed)
        self.hold = torch.where(mask, torch.zeros_like(self.hold), self.hold)
        self.stats["issued"].index_add_(0, self.sector, mask.long())

    def _room(self, p: torch.Tensor, u: torch.Tensor) -> torch.Tensor:
        """Distance from p along unit u before leaving SPOT_BOX (inf along an axis with u = 0)."""
        big = torch.full_like(p, 1e6)
        to_hi = torch.where(u > 1e-6, (self._hi - p) / u.clamp(min=1e-6), big)
        to_lo = torch.where(u < -1e-6, (self._lo - p) / u.clamp(max=-1e-6), big)
        return torch.minimum(to_hi, to_lo).min(-1).values

    # ------------------------------------------------------------------------------
    def update(self, dt: float) -> None:
        """Per physics step: arrival / time-out bookkeeping and the next spot (move episodes only)."""
        t = self.t
        mv = self.move_ep
        here = t.pelvis_xy()
        d = (t.recover_xy - here).norm(dim=-1)
        speed = t._entity.data.root_link_lin_vel_b[:, :2].norm(dim=-1)
        inside = mv & (d < ARRIVE_RADIUS) & (speed < ARRIVE_SPEED)
        self.hold = torch.where(inside, self.hold + dt, torch.zeros_like(self.hold))
        self.elapsed = self.elapsed + dt * mv.float()
        arrived = mv & (self.hold >= ARRIVE_HOLD_S)
        timed_out = mv & ~arrived & (self.elapsed >= self.limit)
        done = arrived | timed_out
        self.arrive_now |= arrived
        sec = self.sector
        self.stats["arrived"].index_add_(0, sec, arrived.long())
        self.stats["timed_out"].index_add_(0, sec, timed_out.long())
        self.stats["ready"].index_add_(0, sec, (arrived & self.ready_mask()).long())
        self.time_sum.index_add_(0, sec, self.elapsed * arrived.float())
        b = (d / ERR_BIN).long().clamp(max=ERR_BINS - 1)
        self.err_hist.view(-1).index_add_(0, sec * ERR_BINS + b, done.long())
        self._new_spot(done)

    # ------------------------------------------------------------------------------
    def ready_error(self) -> torch.Tensor:
        """Distance of the paddle face centre from the ready-stance box (0 inside), m."""
        t, robot = self.t, self.t._entity
        root = robot.data.root_link_pose_w
        yaw = _yaw(root[:, 3:7])
        rel = robot.data.body_link_pose_w[:, t.paddle_id, :3] - root[:, :3]
        fwd = torch.cos(yaw) * rel[:, 0] + torch.sin(yaw) * rel[:, 1]
        height = robot.data.body_link_pose_w[:, t.paddle_id, 2]
        ex = (READY_FORWARD[0] - fwd).clamp(min=0) + (fwd - READY_FORWARD[1]).clamp(min=0)
        ez = (READY_HEIGHT[0] - height).clamp(min=0) + (height - READY_HEIGHT[1]).clamp(min=0)
        return torch.sqrt(ex * ex + ez * ez)

    def ready_mask(self) -> torch.Tensor:
        return self.ready_error() <= 1e-6

    def command(self):
        """Internal teacher command (body-frame vx, vy, wz) toward the spot, facing the net."""
        t, robot = self.t, self.t._entity
        q = robot.data.root_link_pose_w[:, 3:7]
        yaw = _yaw(q)
        delta = t.recover_xy - t.pelvis_xy()
        d = delta.norm(dim=-1, keepdim=True)
        v_w = delta / d.clamp(min=1e-6) * (CMD_GAIN * d).clamp(max=CMD_MAX_SPEED)
        c, s = torch.cos(yaw), torch.sin(yaw)
        v_b = torch.stack([c * v_w[:, 0] + s * v_w[:, 1], -s * v_w[:, 0] + c * v_w[:, 1]], -1)
        heading_err = torch.atan2(torch.sin(-yaw), torch.cos(-yaw))  # target yaw 0 = facing the net
        wz = (HEADING_STIFFNESS * heading_err).clamp(-CMD_MAX_YAW_RATE, CMD_MAX_YAW_RATE)
        return v_b, wz

    def summary(self) -> dict:
        s = {k: v.tolist() for k, v in self.stats.items()}
        out = {"sectors": []}
        hist = self.err_hist.double()
        for i in range(N_SECTORS):
            fin = s["arrived"][i] + s["timed_out"][i]
            h = hist[i]
            cdf = h.cumsum(0) / max(float(h.sum()), 1.0)
            med = round(float(((cdf < 0.5).sum() + 0.5) * ERR_BIN), 3) if fin else None
            out["sectors"].append({
                "sector": i, "issued": s["issued"][i], "finished": fin,
                "arrival_rate": round(s["arrived"][i] / fin, 4) if fin else None,
                "mean_time_s": round(float(self.time_sum[i]) / s["arrived"][i], 3) if s["arrived"][i] else None,
                "median_final_error_m": med,
                "ready_rate_of_arrivals": round(s["ready"][i] / s["arrived"][i], 4) if s["arrived"][i] else None,
            })
        h = hist.sum(0)
        cdf = h.cumsum(0) / max(float(h.sum()), 1.0)
        fin = sum(s["arrived"]) + sum(s["timed_out"])
        out["all"] = {"finished": fin, "arrival_rate": round(sum(s["arrived"]) / max(fin, 1), 4),
                      "median_final_error_m": round(float(((cdf < 0.5).sum() + 0.5) * ERR_BIN), 3),
                      "ready_rate_of_arrivals": round(sum(s["ready"]) / max(sum(s["arrived"]), 1), 4)}
        return out


def _fault_none_like():
    from picklebot_mj.rules import Fault
    return Fault.NONE


# ------------------------------------------------------------------------------------
# Rewards (zero outside move episodes)


def _drill(env) -> MoveDrill:
    return env.action_manager.get_term("ball").drill


def move_track_lin_vel(env, std: float = 0.5) -> torch.Tensor:
    """mjlab track_linear_velocity against the internal spot command (xy), move episodes only."""
    dr = _drill(env)
    if dr is None:  # move drill disabled (e.g. hitting-only evaluation)
        return torch.zeros(env.num_envs, device=env.device)
    v_cmd, _ = dr.command()
    v = dr.t._entity.data.root_link_lin_vel_b[:, :2]
    return torch.exp(-((v_cmd - v) ** 2).sum(-1) / std ** 2) * dr.move_ep.float()


def move_track_yaw(env, std: float = math.sqrt(0.5)) -> torch.Tensor:
    """mjlab track_angular_velocity against the internal heading command, move episodes only."""
    dr = _drill(env)
    if dr is None:  # move drill disabled (e.g. hitting-only evaluation)
        return torch.zeros(env.num_envs, device=env.device)
    _, wz = dr.command()
    w = dr.t._entity.data.root_link_ang_vel_b
    err = (wz - w[:, 2]) ** 2 + (w[:, :2] ** 2).sum(-1)
    return torch.exp(-err / std ** 2) * dr.move_ep.float()


def move_arrival(env) -> torch.Tensor:
    """One-shot bonus per arrival (read-and-clear)."""
    dr = _drill(env)
    if dr is None:  # move drill disabled (e.g. hitting-only evaluation)
        return torch.zeros(env.num_envs, device=env.device)
    r = dr.arrive_now.float()
    dr.arrive_now[:] = False
    return r


def ready_stance(env, std: float = 0.15) -> torch.Tensor:
    """Paddle up and in front near the spot, move episodes only."""
    dr = _drill(env)
    if dr is None:  # move drill disabled (e.g. hitting-only evaluation)
        return torch.zeros(env.num_envs, device=env.device)
    near = dr.move_ep & ((dr.t.recover_xy - dr.t.pelvis_xy()).norm(dim=-1) < READY_RADIUS)
    return torch.exp(-(dr.ready_error() / std) ** 2) * near.float()
