"""D-252 (panel round 110): the call-and-set footwork test (mjlab/results/footwork-target.md). New file: move_drill.py,
deadline_drill.py and footwork_specialist.py are unchanged; CallSetDrill is swapped in by FootworkBallAction when its cfg
sets call_set (evaluation first; no reward term reads it yet).

Every robot episode is a call episode (move_prob 1.0). A chain of CHAIN_LEN calls starts FIRST_CALL_S after the episode
starts and CHAIN_GAP_S after the previous chain. One call:
- a call type (wide forehand, wide backhand, deep, short; uniform) and a side (wide calls their natural side, deep and
  short forehand / backhand 50 / 50); a direction (right, left, back, forward in the court frame, +-30 deg jitter) and a
  distance d ~ U(1.0, 3.0) m from the pelvis to the stance spot S, MoveDrill's box rule (reverse when less than 1.0 m of
  room, then shrink; a reversed wide call swaps its side, a reversed deep / short call swaps type; counted);
- the spot input (recover_xy) is S, the coach's call; the contact point C = S + (0.3, -0.5) on the forehand (the robot's
  right, -y) or S + (0.3, +0.4) on the backhand, at CONTACT_Z (ShadowSwing's stance offsets);
- the ghost ball: a scripted (kinematic) path that the policy observes as the ball, launched from the far side, bouncing
  once and passing through C exactly at T = 0.5 s + d / 2.5 m/s after the call. The rally is closed in call episodes
  (MoveDrill's reset), so the ball is never simulated, tallied or touched; the drill writes its state every physics step.
- judged at T: SET (pelvis ground speed averaged over the last 0.1 s < 0.3 m/s, both ankle links below 0.12 m, trunk
  tilt < 20 deg), READY (MoveDrill's ready box with the paddle >= 0.10 m toward the called side in the pelvis frame),
  REACH (C within 0.8 m of the pelvis horizontally, on the called side); pass = all three. A fall before T fails the
  call (and ends the chain with the episode); an episode time-out before T censors it.
- the next call of the chain: one third are issued at T (early: change of direction under pressure), the rest
  NEXT_CALL_S after T.
Reported per cell (call type x side x early): issued, judged, passed, set, ready, reach, fell, censored; the pace
ladder (first time SET, READY and REACH all hold, observed until the next call, against 0.5 + d / p for p in PACES);
the start time (pelvis 0.10 m toward S); the reversed share.
"""

from __future__ import annotations

import math

import torch

from picklebot_mj.tasks import footwork_specialist as fs
from picklebot_mj.tasks import move_drill as md

CALL_TYPES = ("wide_forehand", "wide_backhand", "deep", "short")
DIST_RANGE = (1.0, 3.0)
JITTER_DEG = 30.0
REACT_S, PACE = 0.5, 2.5
PACES = (1.5, 2.0, 2.5)
CHAIN_LEN = 6
EARLY_SHARE = 1.0 / 3.0
NEXT_CALL_S = 1.5
CHAIN_GAP_S = 1.5
FIRST_CALL_S = 1.0
SET_SPEED, SET_WINDOW_S, FOOT_DOWN_Z, SET_TILT_DEG = 0.3, 0.1, 0.12, 20.0
READY_SIDE_M = 0.10
REACH_M = 0.8
CONTACT_Z = 0.9
OFF_FH, OFF_BH, OFF_BEHIND = 0.5, 0.4, 0.3
START_M = 0.10
# ghost-ball path: launched LAUNCH_BACK_M beyond C (not nearer the net than LAUNCH_X_MIN), LAUNCH_Z high; bounces
# AFTER_BOUNCE_S before T and reaches C with AFTER_BOUNCE_V horizontal speed
LAUNCH_BACK_M, LAUNCH_X_MIN, LAUNCH_Z, LAUNCH_Y_JITTER = 9.0, 1.0, 1.0, 1.5
AFTER_BOUNCE_S, AFTER_BOUNCE_V = 0.35, 5.0
PARK_AFTER_S = 0.4
G = 9.81
N_CELLS = len(CALL_TYPES) * 2 * 2  # type x side (forehand, backhand) x early
STAT_KEYS = ("issued", "judged", "passed", "set", "ready", "reach", "fell", "censored", "reversed", "start_n")


def deadline(d: torch.Tensor, pace: float = PACE) -> torch.Tensor:
    return REACT_S + d / pace


def cell_index(ctype: torch.Tensor, forehand: torch.Tensor, early: torch.Tensor) -> torch.Tensor:
    return ctype * 4 + (~forehand).long() * 2 + early.long()


def contact_point(stance: torch.Tensor, forehand: torch.Tensor) -> torch.Tensor:
    """(x, y) of the contact point beside the stance spot: forehand on the robot's right (-y), backhand on its left."""
    dy = torch.where(forehand, torch.full_like(stance[:, 0], -OFF_FH), torch.full_like(stance[:, 0], OFF_BH))
    return torch.stack([stance[:, 0] + OFF_BEHIND, stance[:, 1] + dy], -1)


def ball_path(L: torch.Tensor, C: torch.Tensor, T: torch.Tensor, e: torch.Tensor):
    """Kinematic ghost ball: launched at L (xyz), one bounce, through C (xyz) at time T; state at elapsed e. Returns
    (pos, vel). Before the bounce: a free-flight parabola from L to the bounce point B (z = ball radius) in T - Ta;
    after it: a parabola from B through C in Ta = AFTER_BOUNCE_S at AFTER_BOUNCE_V horizontal speed."""
    from picklebot_mj.ball import BALL_RADIUS
    r = BALL_RADIUS
    ta = AFTER_BOUNCE_S
    tb = (T - ta).clamp(min=0.2)
    h = C[:, :2] - L[:, :2]
    u = h / h.norm(dim=-1, keepdim=True).clamp(min=1e-6)
    B = torch.cat([C[:, :2] - u * AFTER_BOUNCE_V * ta, torch.full_like(C[:, :1], r)], -1)
    vb_xy = (B[:, :2] - L[:, :2]) / tb.unsqueeze(-1)
    vb_z = (r - L[:, 2] + 0.5 * G * tb ** 2) / tb
    va_xy = u * AFTER_BOUNCE_V
    va_z = (C[:, 2] - r + 0.5 * G * ta ** 2) / ta
    pre = (e < tb).unsqueeze(-1)
    s1, s2 = e, (e - tb).clamp(min=0)
    p1 = torch.cat([L[:, :2] + vb_xy * s1.unsqueeze(-1), (L[:, 2] + vb_z * s1 - 0.5 * G * s1 ** 2).unsqueeze(-1)], -1)
    v1 = torch.cat([vb_xy, (vb_z - G * s1).unsqueeze(-1)], -1)
    p2 = torch.cat([B[:, :2] + va_xy * s2.unsqueeze(-1), (r + va_z * s2 - 0.5 * G * s2 ** 2).unsqueeze(-1)], -1)
    v2 = torch.cat([va_xy, (va_z - G * s2).unsqueeze(-1)], -1)
    return torch.where(pre, p1, p2), torch.where(pre, v1, v2)


def judge(speed_avg, feet_z, tilt, paddle_fwd, paddle_lat, paddle_z, ball_lat, ball_dist, forehand):
    """The rep's three conditions from pelvis-frame quantities (lat: left +). Returns (set, ready, reach)."""
    side = torch.where(forehand, -torch.ones_like(paddle_lat), torch.ones_like(paddle_lat))
    set_ok = (speed_avg < SET_SPEED) & (feet_z < FOOT_DOWN_Z).all(-1) & (tilt < math.radians(SET_TILT_DEG))
    ready = ((paddle_fwd >= md.READY_FORWARD[0]) & (paddle_fwd <= md.READY_FORWARD[1])
             & (paddle_z >= md.READY_HEIGHT[0]) & (paddle_z <= md.READY_HEIGHT[1]) & (side * paddle_lat >= READY_SIDE_M))
    reach = (ball_dist <= REACH_M) & (side * ball_lat > 0)
    return set_ok, ready, reach


class CallSetDrill(fs.FootworkDrill):
    def __init__(self, term, move_prob: float, seed: int, spot_box=None):
        super().__init__(term, move_prob, seed, spot_box=spot_box or fs.SPOT_BOX)  # FootworkDrill: its box, attributes
        n, dev = self.n, self.dev
        self.cgen = torch.Generator(device=dev).manual_seed(int(seed) + 161803)  # own stream
        env = getattr(term, "_env", None)
        dt = float(getattr(env, "physics_dt", 0.005)) if env is not None else 0.005
        self.KS = max(1, int(round(SET_WINDOW_S / dt)))
        self.spd = torch.zeros(n, self.KS, device=dev)
        self.spd_i = 0
        z = lambda: torch.zeros(n, device=dev)  # noqa: E731
        b = lambda: torch.zeros(n, dtype=torch.bool, device=dev)  # noqa: E731
        zl = lambda: torch.zeros(n, dtype=torch.long, device=dev)  # noqa: E731
        self.wait, self.e, self.T, self.d = z(), z(), torch.ones(n, device=dev), z()
        # pending: issued, not yet judged; has_prev: judged, its ladder still observed until the next call
        self.pending, self.has_prev, self.next_early, self.fh, self.started = b(), b(), b(), b(), b()
        self.ctype, self.chain_pos, self.cell = zl(), zl(), zl()
        self.t_all, self.t_start = torch.full((n,), -1.0, device=dev), torch.full((n,), -1.0, device=dev)
        self.start_xy, self.dirv = torch.zeros(n, 2, device=dev), torch.zeros(n, 2, device=dev)
        self.C, self.L = torch.zeros(n, 3, device=dev), torch.zeros(n, 3, device=dev)
        self.cs = {k: torch.zeros(N_CELLS, dtype=torch.long, device=dev) for k in STAT_KEYS}
        self.cs_ladder = torch.zeros(len(PACES), N_CELLS, dtype=torch.long, device=dev)
        self.cs_ladder_n = torch.zeros(N_CELLS, dtype=torch.long, device=dev)
        self.cs_start_sum = torch.zeros(N_CELLS, device=dev)
        self.chains = torch.zeros(2, dtype=torch.long, device=dev)  # started, completed (all CHAIN_LEN judged)
        self._paces = torch.tensor(PACES, device=dev)
        self._ladder_idx = torch.arange(len(PACES), device=dev).unsqueeze(-1) * N_CELLS
        self._ankles = None
        self._park = torch.tensor(md.PARK_POS, device=dev)

    # --- episode hooks -----------------------------------------------------------------
    def reset(self, env_ids: torch.Tensor) -> None:
        """A pending call is failed by a fall and censored by any other episode end; then FootworkDrill's reset."""
        env = getattr(self.t, "_env", None)
        if env is not None and env.common_step_counter > 0 and len(env_ids):
            fell = env.termination_manager.get_term("fell_over")[env_ids].bool()
            p = self.pending[env_ids]
            c = self.cell[env_ids]
            self.cs["fell"].index_add_(0, c, (p & fell).long())
            self.cs["judged"].index_add_(0, c, (p & fell).long())
            self.cs["censored"].index_add_(0, c, (p & ~fell).long())
        super().reset(env_ids)

    def _new_spot(self, mask: torch.Tensor) -> None:
        """Episode start (MoveDrill's reset): stand where the robot is; the first call follows FIRST_CALL_S later."""
        t = self.t
        t.recover_xy = torch.where(mask.unsqueeze(-1), t.pelvis_xy(), t.recover_xy)
        self.wait = torch.where(mask, torch.full_like(self.wait, FIRST_CALL_S), self.wait)
        self.chain_pos = torch.where(mask, torch.zeros_like(self.chain_pos), self.chain_pos)
        for f in (self.pending, self.has_prev, self.next_early):
            f.masked_fill_(mask, False)
        self.limit = torch.where(mask, torch.full_like(self.limit, 1e9), self.limit)  # MoveDrill's limit unused

    # --- calls ----------------------------------------------------------------------------
    def _issue(self, mask: torch.Tensor) -> None:
        """New calls for envs in mask (early = the previous call's draw); books the previous call's ladder first."""
        self._book_ladder(mask & self.has_prev)
        t, n, dev, g = self.t, self.n, self.dev, self.cgen
        here = t.pelvis_xy()
        ctype = torch.randint(0, len(CALL_TYPES), (n,), generator=g, device=dev)
        coin = torch.rand(n, generator=g, device=dev) < 0.5
        fh = torch.where(ctype == 0, torch.ones_like(coin), torch.where(ctype == 1, torch.zeros_like(coin), coin))
        base = torch.tensor([-math.pi / 2, math.pi / 2, math.pi, 0.0], device=dev)[ctype]  # right, left, back, forward
        ang = base + math.radians(JITTER_DEG) * (2 * torch.rand(n, generator=g, device=dev) - 1)
        d = DIST_RANGE[0] + (DIST_RANGE[1] - DIST_RANGE[0]) * torch.rand(n, generator=g, device=dev)
        u = torch.stack([torch.cos(ang), torch.sin(ang)], -1)
        rev = self._room(here, u) < DIST_RANGE[0]
        u = torch.where(rev.unsqueeze(-1), -u, u)
        ctype = torch.where(rev, torch.tensor([1, 0, 3, 2], device=dev)[ctype], ctype)
        fh = torch.where(rev & (ctype <= 1), ctype == 0, fh)
        d = torch.minimum(d, self._room(here, u)).clamp(min=0.0)
        S = (here + d.unsqueeze(-1) * u).clamp(self._lo, self._hi)
        d = (S - here).norm(dim=-1)
        C = torch.cat([contact_point(S, fh), torch.full_like(d.unsqueeze(-1), CONTACT_Z)], -1)
        ly = C[:, 1] + LAUNCH_Y_JITTER * (2 * torch.rand(n, generator=g, device=dev) - 1)
        L = torch.stack([(C[:, 0] + LAUNCH_BACK_M).clamp(min=LAUNCH_X_MIN), ly, torch.full_like(d, LAUNCH_Z)], -1)
        m, m2 = mask, mask.unsqueeze(-1)
        early = self.next_early
        self.ctype, self.fh = torch.where(m, ctype, self.ctype), torch.where(m, fh, self.fh)
        self.d, self.T = torch.where(m, d, self.d), torch.where(m, deadline(d), self.T)
        self.C, self.L = torch.where(m2, C, self.C), torch.where(m2, L, self.L)
        self.start_xy, self.dirv = torch.where(m2, here, self.start_xy), torch.where(m2, u, self.dirv)
        self.e = torch.where(m, torch.zeros_like(self.e), self.e)
        self.t_all = torch.where(m, torch.full_like(self.t_all, -1.0), self.t_all)
        self.t_start = torch.where(m, torch.full_like(self.t_start, -1.0), self.t_start)
        self.started = self.started & ~m
        self.cell = torch.where(m, cell_index(ctype, fh, early), self.cell)
        self.chains[0] += (m & (self.chain_pos == 0)).sum()
        self.pending |= m
        self.has_prev &= ~m
        t.recover_xy = torch.where(m2, S, t.recover_xy)
        self.cs["issued"].index_add_(0, self.cell, m.long())
        self.cs["reversed"].index_add_(0, self.cell, (m & rev).long())

    def _book_ladder(self, ok: torch.Tensor) -> None:
        """The pace ladder of a judged call: its first all-hold time against 0.5 + d / p, observed until now."""
        reached = (self.t_all >= 0).unsqueeze(0) & (self.t_all.unsqueeze(0) <= deadline(self.d.unsqueeze(0),
                                                                                     self._paces.unsqueeze(-1)))
        self.cs_ladder.view(-1).index_add_(0, (self._ladder_idx + self.cell.unsqueeze(0)).view(-1),
                                           (reached & ok.unsqueeze(0)).long().view(-1))
        self.cs_ladder_n.index_add_(0, self.cell, ok.long())

    # --- per physics step ---------------------------------------------------------------
    def _pose(self):
        t, robot = self.t, self.t._entity
        if self._ankles is None:
            self._ankles = [int(i) for i in robot.find_bodies(("left_ankle_roll_link", "right_ankle_roll_link"))[0]]
        root = robot.data.root_link_pose_w
        q = root[:, 3:7]
        yaw = md._yaw(q)
        c, s = torch.cos(yaw), torch.sin(yaw)
        _, x, y, _ = q.unbind(-1)
        tilt = torch.acos((1 - 2 * (x * x + y * y)).clamp(-1, 1))
        rel = robot.data.body_link_pose_w[:, t.paddle_id, :3] - root[:, :3]
        p_fwd, p_lat = c * rel[:, 0] + s * rel[:, 1], -s * rel[:, 0] + c * rel[:, 1]
        p_z = robot.data.body_link_pose_w[:, t.paddle_id, 2]
        feet_z = robot.data.body_link_pose_w[:, self._ankles, 2]
        pel = t.pelvis_xy()
        bd = self.C[:, :2] - pel
        b_lat = -s * bd[:, 0] + c * bd[:, 1]
        return pel, tilt, p_fwd, p_lat, p_z, feet_z, bd.norm(dim=-1), b_lat

    def update(self, dt: float) -> None:
        t, mv = self.t, self.move_ep
        self.spd[:, self.spd_i] = t._entity.data.root_link_lin_vel_w[:, :2].norm(dim=-1)
        self.spd_i = (self.spd_i + 1) % self.KS
        pel, tilt, p_fwd, p_lat, p_z, feet_z, b_dist, b_lat = self._pose()
        set_ok, ready, reach = judge(self.spd.mean(-1), feet_z, tilt, p_fwd, p_lat, p_z, b_lat, b_dist, self.fh)
        obs = mv & (self.pending | self.has_prev)  # a call between its issue and the next call
        self.e = self.e + dt * obs.float()
        self.wait = self.wait - dt * (mv & ~self.pending).float()
        st = obs & ~self.started & (((pel - self.start_xy) * self.dirv).sum(-1) >= START_M)
        self.t_start = torch.where(st, self.e, self.t_start)
        self.started |= st
        fa = obs & set_ok & ready & reach & (self.t_all < 0)
        self.t_all = torch.where(fa, self.e, self.t_all)
        # judge at T
        due = mv & self.pending & (self.e >= self.T)
        c = self.cell
        for k, x in (("judged", due), ("passed", due & set_ok & ready & reach), ("set", due & set_ok),
                     ("ready", due & ready), ("reach", due & reach), ("start_n", due & self.started)):
            self.cs[k].index_add_(0, c, x.long())
        self.cs_start_sum.index_add_(0, c, torch.where(due & self.started, self.t_start, torch.zeros_like(self.t_start)))
        self.pending &= ~due
        self.has_prev |= due
        last = due & (self.chain_pos >= CHAIN_LEN - 1)
        self.chains[1] += last.sum()
        early = torch.rand(self.n, generator=self.cgen, device=self.dev) < EARLY_SHARE
        self.next_early = torch.where(due, early & ~last, self.next_early)
        self.chain_pos = torch.where(due, (self.chain_pos + 1) % CHAIN_LEN, self.chain_pos)
        gap = torch.where(last, torch.full_like(self.wait, CHAIN_GAP_S),
                          torch.where(early, torch.zeros_like(self.wait), torch.full_like(self.wait, NEXT_CALL_S)))
        self.wait = torch.where(due, gap, self.wait)
        go = mv & ~self.pending & (self.wait <= 0)
        if bool(go.any()):  # one host sync per physics step; this drill is evaluation-only
            self._issue(go)
        self._write_ball(mv)

    def _write_ball(self, mv: torch.Tensor) -> None:
        from picklebot_mj.ball_sim import BallState
        t = self.t
        pos, vel = ball_path(self.L, self.C, self.T, self.e)
        fly = (mv & (self.pending | self.has_prev) & (self.e <= self.T + PARK_AFTER_S)).unsqueeze(-1)
        park = mv.unsqueeze(-1) & ~fly
        p = torch.where(fly, pos, torch.where(park, self._park.expand_as(pos), t.ball.pos))
        v_ = torch.where(fly, vel, torch.where(park, torch.zeros_like(vel), t.ball.vel))
        s = torch.where(mv.unsqueeze(-1), torch.zeros_like(t.ball.spin), t.ball.spin)
        t.ball = BallState(p, v_, s)

    # --- reporting --------------------------------------------------------------------------
    def counters(self) -> dict:
        out = {k: v.tolist() for k, v in self.cs.items()}
        out["ladder"] = self.cs_ladder.tolist()
        out["ladder_n"] = self.cs_ladder_n.tolist()
        out["start_sum"] = [round(x, 4) for x in self.cs_start_sum.tolist()]
        out["chains"] = self.chains.tolist()
        out["meta"] = {"call_types": list(CALL_TYPES), "cell": "type * 4 + backhand * 2 + early", "paces": list(PACES),
                       "deadline": f"{REACT_S} + d / {PACE}", "chain_len": CHAIN_LEN, "early_share": EARLY_SHARE}
        return out

    def summary(self) -> dict:
        return {"call_set": self.counters()}
