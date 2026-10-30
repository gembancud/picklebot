"""Body-speed test (panel round 50, motion reviewer's option F; scripts/diag/bodyspeed54.sh). New file: move_drill.py is
unchanged; FastMoveDrill is swapped in by `AgilityBallAction` (tasks/agility.py) when its cfg sets move_cmd_max_speed.

FastMoveDrill (a MoveDrill) differs only in:
- the internal teacher command's speed cap (cmd_max_speed, e.g. 2.5 m/s instead of CMD_MAX_SPEED 1.0), with the gain
  scaled by the same factor (CMD_GAIN * cap / CMD_MAX_SPEED) so the braking radius stays CMD_MAX_SPEED / CMD_GAIN =
  0.83 m (as the deadline drill does); heading law unchanged (face the net);
- optionally the spot distance range and the spot box (MoveDrill's 0.5-3 m inside the 4 x 5.6 m half court are too
  short to cruise at 2-2.5 m/s);
- instrumentation (masked tensor math, no host syncs), per MoveDrill sector (world frame: 0 toward the net, CCW;
  2 left, 4 back, 6 right):
  * sustained speed: per spot, the best 1-s running mean (control-step samples) of the pelvis ground velocity component
    toward the spot (a window shorter than 1 s when the spot ends sooner), booked when the spot finishes (arrival or
    untimed time-out); histogram in 0.1 m/s bins;
  * the spot's peak pelvis ground speed (histogram, 0.1 m/s bins);
  * falls (a fell_over reset during a spot) and censored spots (any other reset during a spot: the episode limit).
Arrival, the arrival bonus and the untimed limit (1.5 s + 1.25 s/m) are MoveDrill's.
"""

from __future__ import annotations

import math

import torch

from picklebot_mj.tasks import move_drill as md

SPEED_BIN, SPEED_BINS = 0.1, 50  # m/s (last bin: >= 4.9 m/s)
WINDOW_S = 1.0


class FastMoveDrill(md.MoveDrill):
    def __init__(self, term, move_prob: float, seed: int, sector_weights=None, cmd_max_speed: float = 2.5,
                 dist_range=None, spot_box=None):
        super().__init__(term, move_prob, seed, sector_weights)
        n, dev = self.n, self.dev
        self.cap = float(cmd_max_speed)
        self.gain = md.CMD_GAIN * self.cap / md.CMD_MAX_SPEED
        self.dist_range = tuple(float(x) for x in (dist_range or md.DIST_RANGE))
        assert 0 < self.dist_range[0] <= self.dist_range[1]
        if spot_box is not None:
            self._lo = torch.tensor([spot_box[0][0], spot_box[1][0]], dtype=torch.float32, device=dev)
            self._hi = torch.tensor([spot_box[0][1], spot_box[1][1]], dtype=torch.float32, device=dev)
        env = getattr(term, "_env", None)
        self.decimation = int(getattr(getattr(env, "cfg", None), "decimation", 1)) if env is not None else 1
        dt = float(getattr(env, "physics_dt", 0.005)) if env is not None else 0.005
        self.K = max(1, int(round(WINDOW_S / (dt * self.decimation))))
        z = lambda *s: torch.zeros(*s, device=dev)  # noqa: E731
        zl = lambda *s: torch.zeros(*s, dtype=torch.long, device=dev)  # noqa: E731
        self.buf, self.wsum = z(n, self.K), z(n)
        self.cnt = zl(n)
        self.best, self.peak = torch.full((n,), -1e3, device=dev), z(n)
        self.live = torch.zeros(n, dtype=torch.bool, device=dev)  # a spot is in progress (booked at its end)
        for k in ("fell", "censored", "booked"):
            self.stats[k] = zl(md.N_SECTORS)
        self.best_hist = zl(md.N_SECTORS, SPEED_BINS)
        self.peak_hist = zl(md.N_SECTORS, SPEED_BINS)
        self.best_sum = z(md.N_SECTORS)
        self._ar = torch.arange(n, device=dev)
        self._calls = 0

    # ------------------------------------------------------------------------------
    def reset(self, env_ids: torch.Tensor) -> None:
        """Count the spot an episode end cut short (a fall, or any other reset: censored), then MoveDrill's reset."""
        env = getattr(self.t, "_env", None)
        if env is not None and env.common_step_counter > 0 and len(env_ids):
            fell = env.termination_manager.get_term("fell_over")[env_ids].bool()
            was = self.move_ep[env_ids] & self.live[env_ids]
            sec = self.sector[env_ids]
            self.stats["fell"].index_add_(0, sec, (was & fell).long())
            self.stats["censored"].index_add_(0, sec, (was & ~fell).long())
        self.live[env_ids] = False
        super().reset(env_ids)

    def _book(self, m: torch.Tensor) -> None:
        sec = self.sector
        self.stats["booked"].index_add_(0, sec, m.long())
        b = (self.best.clamp(min=0.0).nan_to_num(0.0) / SPEED_BIN).clamp(0, SPEED_BINS - 1).long()
        p = (self.peak.nan_to_num(0.0) / SPEED_BIN).clamp(0, SPEED_BINS - 1).long()
        self.best_hist.view(-1).index_add_(0, sec * SPEED_BINS + b, m.long())
        self.peak_hist.view(-1).index_add_(0, sec * SPEED_BINS + p, m.long())
        self.best_sum.index_add_(0, sec, self.best.clamp(min=0.0) * m.float())

    def _new_spot(self, mask: torch.Tensor) -> None:
        """Book the finished spot (update passes its done mask), then MoveDrill._new_spot with this drill's range."""
        self._book(mask & self.live & self.move_ep)
        t = self.t
        here = t.pelvis_xy()
        lo, hi = self.dist_range
        sec = torch.multinomial(self.sector_w, self.n, replacement=True, generator=self.gen)
        ang = (sec.float() + torch.rand(self.n, generator=self.gen, device=self.dev)) * (2 * math.pi / md.N_SECTORS) \
            - math.pi / md.N_SECTORS
        dist = lo + (hi - lo) * torch.rand(self.n, generator=self.gen, device=self.dev)
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
        self.limit = torch.where(mask, md.TIME_BASE_S + md.TIME_PER_M * d0, self.limit)
        self.elapsed = torch.where(mask, torch.zeros_like(self.elapsed), self.elapsed)
        self.hold = torch.where(mask, torch.zeros_like(self.hold), self.hold)
        self.stats["issued"].index_add_(0, self.sector, mask.long())
        # the speed instrument restarts for the new spot
        self.buf = torch.where(m, torch.zeros_like(self.buf), self.buf)
        self.wsum = torch.where(mask, torch.zeros_like(self.wsum), self.wsum)
        self.cnt = torch.where(mask, torch.zeros_like(self.cnt), self.cnt)
        self.best = torch.where(mask, torch.full_like(self.best, -1e3), self.best)
        self.peak = torch.where(mask, torch.zeros_like(self.peak), self.peak)
        self.live = self.live | (mask & self.move_ep)

    def _sample(self) -> None:
        """Per physics step: peak ground speed; once per control step the 1-s window of speed toward the spot."""
        t = self.t
        mv = self.move_ep & self.live
        v = t._entity.data.root_link_lin_vel_w[:, :2]
        self.peak = torch.where(mv, torch.maximum(self.peak, v.norm(dim=-1)), self.peak)
        if self._calls % self.decimation == 0:
            to = t.recover_xy - t.pelvis_xy()
            vt = (v * to / to.norm(dim=-1, keepdim=True).clamp(min=1e-6)).sum(-1)
            pos = self.cnt % self.K
            old = self.buf[self._ar, pos]
            new = torch.where(mv, vt, old)
            self.buf[self._ar, pos] = new
            self.wsum = self.wsum + torch.where(mv, vt - old, torch.zeros_like(vt))
            self.cnt = self.cnt + mv.long()
            mean = self.wsum / self.cnt.clamp(min=1, max=self.K).float()
            self.best = torch.where(mv, torch.maximum(self.best, mean), self.best)
        self._calls += 1

    def update(self, dt: float) -> None:
        self._sample()
        super().update(dt)

    def command(self):
        """MoveDrill's command with the raised cap and the scaled gain (braking radius unchanged)."""
        t, robot = self.t, self.t._entity
        yaw = md._yaw(robot.data.root_link_pose_w[:, 3:7])
        delta = t.recover_xy - t.pelvis_xy()
        d = delta.norm(dim=-1, keepdim=True)
        v_w = delta / d.clamp(min=1e-6) * (self.gain * d).clamp(max=self.cap)
        c, s = torch.cos(yaw), torch.sin(yaw)
        v_b = torch.stack([c * v_w[:, 0] + s * v_w[:, 1], -s * v_w[:, 0] + c * v_w[:, 1]], -1)
        heading_err = torch.atan2(torch.sin(-yaw), torch.cos(-yaw))
        wz = (md.HEADING_STIFFNESS * heading_err).clamp(-md.CMD_MAX_YAW_RATE, md.CMD_MAX_YAW_RATE)
        return v_b, wz

    def counters(self) -> dict:
        """Cumulative counters for the training log (one host sync per call)."""
        out = {k: v.tolist() for k, v in self.stats.items()}
        out["best_hist"] = self.best_hist.tolist()
        out["peak_hist"] = self.peak_hist.tolist()
        out["best_sum"] = [round(x, 4) for x in self.best_sum.tolist()]
        return out
