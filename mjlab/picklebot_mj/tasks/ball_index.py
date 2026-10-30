"""Ball-index tally (logging only; ball-1 diagnostic, scripts/diag/ballidx51.sh). New file: nothing in pairs.py or
return_stand.py is changed; the tally is built by `AgilityBallAction` (tasks/agility.py) when its cfg sets
ball_index_tally, and it wraps the instance's PairCourts.step and PairCourts.on_reset, as DirectionTally does.

For every handed (robot-to-robot) ball an env receives on a live pair court it records, at the hand-off:
- k, the ball's index in the rally: the number of hand-offs on the court since its feeder ball (ball 0), this one
  included (1 = the first robot-to-robot ball). Binned 1, 2, 3+.
- the incoming speed |v| of the mirrored partner return (the ball installed as the receiver's feed) and its
  horizontal speed |v_xy|;
- the predicted interception of that ball (planner.predict_contact_fast from the stored hand-off state: the first
  interception after the bounce, 3 s horizon), its direction class relative to the receiver's pelvis at the hand-off
  in the pelvis heading frame (forward / left / back / right quadrants, DirectionTally's classes) and the pelvis
  distance to it (xy). A ball the predictor finds no interception for (or that ends before its batch came up) is
  class 4, "none".
Outcome when the receiver's feed ends: contact (its first legal paddle contact, hit_done), legal (return_done; a
return the partner volleyed back before it landed counts as legal, as the task's _credit_early does), fell (ended by
a fall). Not counted as the receiver's ball: a hand-off whose hitter's shot faulted (contact hand-off: both copies end
on the same step, D-135; or the court already dead) -> "void"; an open ball cut by a non-fall reset (time-out) ->
"censored".

Counters (masked tensor math, no host syncs in the step) per cell (court group 0 pair / 1 drill courts, k bin, direction
class 0-4): balls, contact, legal, fell, the sum of horizontal speed, histograms of |v| (0.5 m/s bins), |v_xy| (0.5 m/s)
and distance (0.25 m bins) for all balls and for the legal ones. Per (group, k bin): received, void, censored.
"""

from __future__ import annotations

import math

import torch

from picklebot_mj.tasks.latent_reach import _to_heading, _yaw_frame

N_GROUPS, N_KBINS, N_DIRS = 2, 3, 5  # direction 4: no predicted interception
DIR_NAMES = ("forward", "left", "back", "right", "none")
SPEED_BIN, SPEED_BINS = 0.5, 40  # m/s (last bin: >= 19.5 m/s)
DIST_BIN, DIST_BINS = 0.25, 40  # m (last bin: >= 9.75 m)
PRED_BATCH = 128  # hand-offs predicted per control step (due ones first; leftovers wait a step, from the stored state)
PRED_HORIZON_S = 3.0

# Split variables (opt-in, split=True; ballidx52): shot quality of the handed ball and the receiver's state at the hand-off.
# Each: (name, low edge, bin width, bins); a last extra bin holds "missing" (e.g. no bounce before the receiver's contact).
# Histograms per (group, k bin, distance bin, variable bin), for all balls and for the legal ones.
SPLIT_VARS = (
    ("spin", 0.0, 10.0, 50),  # |omega| at the hand-off, rad/s
    ("net_clear", -0.5, 0.05, 60),  # ball centre - radius - net centre height where it crosses x = 0, m (simulated)
    ("bounce_depth", 0.0, 0.25, 40),  # -x of its first bounce on the receiver's side, m from the net (simulated)
    ("angle", -60.0, 3.0, 40),  # incoming horizontal angle vs the court axis, deg (atan2(vy, -vx) at the hand-off)
    ("pelvis_speed", 0.0, 0.1, 40),  # receiver pelvis ground speed at the hand-off, m/s
    ("recover_dist", 0.0, 0.1, 50),  # receiver pelvis to its recover_xy at the hand-off, m
    ("yaw_err", 0.0, 4.5, 40),  # |receiver yaw| vs facing the net (+x), deg
    ("idle", 0.0, 0.1, 80),  # s since the receiver's own last paddle contact or its episode / rally start (later)
)
SHOT_VARS = ("spin", "net_clear", "bounce_depth", "angle")
STATE_VARS = ("pelvis_speed", "recover_dist", "yaw_err", "idle")
BOUNCE_Z = 0.5  # m: a vz sign change (down -> up) below this height, before the receiver's contact, is the bounce


def default_predictor(pos: torch.Tensor, vel: torch.Tensor, spin: torch.Tensor):
    """(interception point (N, 3), found (N,)) from the planner's contact rollout."""
    from picklebot_mj.planner import PlannerCfg, predict_contact_fast
    cx, _, _, found = predict_contact_fast(pos, vel, spin, PlannerCfg(horizon_s=PRED_HORIZON_S))
    return cx, found


def direction_class(rel_xy_heading: torch.Tensor) -> torch.Tensor:
    """Quadrant of a heading-frame xy vector: 0 forward, 1 left, 2 back, 3 right (DirectionTally.direction)."""
    ang = torch.atan2(rel_xy_heading[:, 1], rel_xy_heading[:, 0])
    return (((ang + math.pi / 4) % (2 * math.pi)) // (math.pi / 2)).long().clamp(0, 3)


class BallIndexTally:
    def __init__(self, term, env, predictor=None, batch: int = PRED_BATCH, split: bool = False):
        self.t, self.env = term, env
        pc = term.pairs
        assert pc is not None, "the ball-index tally hooks PairCourts.step (pair mode)"
        n, dev = term.num_envs, term.device
        self.n, self.h, self.dev = n, n // 2, dev
        self.decimation = int(getattr(env.cfg, "decimation", 1))
        self.predict = predictor or default_predictor
        self.batch = min(int(batch), n)
        b = lambda: torch.zeros(n, dtype=torch.bool, device=dev)  # noqa: E731
        z = lambda *s: torch.zeros(*s, device=dev)  # noqa: E731
        self.open, self.pend = b(), b()
        self.kb = torch.zeros(n, dtype=torch.long, device=dev)
        self.dirc = torch.full((n,), N_DIRS - 1, dtype=torch.long, device=dev)
        self.spd, self.hspd, self.dist = z(n), z(n), z(n)
        self.st = z(n, 9)  # hand-off ball state (pos, vel, spin), court-local, receiver's frame
        self.pel0, self.c0, self.s0 = z(n, 2), torch.ones(n, device=dev), z(n)
        self.nh = torch.zeros(self.h, dtype=torch.long, device=dev)  # hand-offs since the court's feeder ball
        cells = N_GROUPS * N_KBINS * N_DIRS
        zl = lambda *s: torch.zeros(*s, dtype=torch.long, device=dev)  # noqa: E731
        self.c = {k: zl(cells) for k in ("balls", "contact", "legal", "fell", "early")}
        self.hspd_sum = z(cells)
        self.hist = {k: zl(cells, SPEED_BINS) for k in ("speed", "speed_legal", "hspeed", "hspeed_legal")}
        self.hist.update({k: zl(cells, DIST_BINS) for k in ("dist", "dist_legal")})
        self.gk = {k: zl(N_GROUPS * N_KBINS) for k in ("received", "void", "censored")}
        self._calls = 0
        self.split = bool(split)
        if self.split:
            nv = len(SPLIT_VARS)
            self.sv = torch.full((n, nv), float("nan"), device=dev)  # this ball's split variables (nan: missing)
            self.idle = z(n)
            self.prev = z(n, 3)  # the open ball's previous position and vz (net crossing / bounce detection)
            self.prev_vz = z(n)
            self.crossed, self.bounced = b(), b()
            sc = N_GROUPS * N_KBINS * DIST_BINS
            self.shist = {name: zl(sc, nb + 1) for name, _, _, nb in SPLIT_VARS}
            self.shist_legal = {name: zl(sc, nb + 1) for name, _, _, nb in SPLIT_VARS}
            self._vi = {name: i for i, (name, *_) in enumerate(SPLIT_VARS)}
        self._orig_step, self._orig_reset = pc.step, pc.on_reset
        pc.step = self.step
        pc.on_reset = self.on_reset

    # ------------------------------------------------------------------------------
    def _group(self) -> torch.Tensor:
        g = self.t.pairs.group
        return torch.zeros(self.n, dtype=torch.long, device=self.dev) if g is None else g.repeat(2).long()

    def _gk(self) -> torch.Tensor:
        return self._group() * N_KBINS + self.kb

    def _cell(self) -> torch.Tensor:
        return self._gk() * N_DIRS + self.dirc

    def _book(self, m: torch.Tensor, contact: torch.Tensor, legal: torch.Tensor, fell: torch.Tensor,
              early: torch.Tensor | None = None) -> None:
        """Count the open balls ending in mask m with these outcomes (per env tensors)."""
        cell = self._cell()
        ml = m.long()
        self.c["balls"].index_add_(0, cell, ml)
        self.c["contact"].index_add_(0, cell, (m & contact).long())
        self.c["legal"].index_add_(0, cell, (m & legal).long())
        self.c["fell"].index_add_(0, cell, (m & fell).long())
        if early is not None:
            self.c["early"].index_add_(0, cell, (m & early).long())
        self.hspd_sum.index_add_(0, cell, self.hspd * m.float())
        sb = (self.spd.nan_to_num(0.0) / SPEED_BIN).clamp(0, SPEED_BINS - 1).long()
        hb = (self.hspd.nan_to_num(0.0) / SPEED_BIN).clamp(0, SPEED_BINS - 1).long()
        db = (self.dist.nan_to_num(1e3) / DIST_BIN).clamp(0, DIST_BINS - 1).long()
        lg = (m & legal).long()
        for name, bins, nb in (("speed", sb, SPEED_BINS), ("hspeed", hb, SPEED_BINS), ("dist", db, DIST_BINS)):
            self.hist[name].view(-1).index_add_(0, cell * nb + bins, ml)
            self.hist[name + "_legal"].view(-1).index_add_(0, cell * nb + bins, lg)
        if self.split:
            sc = self._gk() * DIST_BINS + db
            for i, (name, lo, w, nb) in enumerate(SPLIT_VARS):
                v = self.sv[:, i]
                vb = torch.where(v.isnan(), torch.full_like(db, nb),
                                 ((v.nan_to_num(lo) - lo) / w).floor().clamp(0, nb - 1).long())
                self.shist[name].view(-1).index_add_(0, sc * (nb + 1) + vb, ml)
                self.shist_legal[name].view(-1).index_add_(0, sc * (nb + 1) + vb, lg)
        self.open &= ~m
        self.pend &= ~m

    def _predict_step(self) -> None:
        """Once per control step: a fixed batch of pending hand-offs (due first) gets its predicted interception."""
        if self._calls % self.decimation != 0:
            return
        idx = torch.topk(self.pend.float(), self.batch).indices
        sel = self.pend[idx]
        st = self.st[idx]
        cx, found = self.predict(st[:, :3], st[:, 3:6], st[:, 6:9])
        ok = sel & found
        rel = cx[:, :2] - self.pel0[idx]
        relh = _to_heading(torch.cat([rel, torch.zeros_like(rel[:, :1])], -1), self.c0[idx], self.s0[idx])[:, :2]
        d = torch.where(ok, direction_class(relh), torch.full_like(self.dirc[idx], N_DIRS - 1))
        dist = torch.where(ok, rel.norm(dim=-1), self.dist[idx])
        self.dirc = self.dirc.index_copy(0, idx, torch.where(sel, d, self.dirc[idx]))
        self.dist = self.dist.index_copy(0, idx, torch.where(sel, dist, self.dist[idx]))
        self.pend = self.pend & ~torch.zeros_like(self.pend).index_copy(0, idx, sel)

    # ------------------------------------------------------------------------------
    def _split_track(self, contact, dt: float) -> None:
        """Per physics step: the idle clock, and the open ball's simulated net crossing and first bounce (both only
        before the receiver's first contact: the flight the hitter gave it)."""
        from picklebot_mj import court
        from picklebot_mj.ball import BALL_RADIUS
        t = self.t
        self.idle = self.idle + dt
        if contact is not None:
            self.idle = torch.where(contact, torch.zeros_like(self.idle), self.idle)
        p, vz = t.ball.pos, t.ball.vel[:, 2]
        fl = self.open & ~t.hit_done
        cross = fl & ~self.crossed & (self.prev[:, 0] > 0) & (p[:, 0] <= 0)
        f = (self.prev[:, 0] / (self.prev[:, 0] - p[:, 0]).clamp(min=1e-9)).clamp(0, 1)
        z = self.prev[:, 2] + f * (p[:, 2] - self.prev[:, 2])
        i = self._vi["net_clear"]
        self.sv[:, i] = torch.where(cross, z - BALL_RADIUS - court.NET_CENTER_HEIGHT, self.sv[:, i])
        self.crossed |= cross
        bnc = fl & ~self.bounced & (p[:, 0] < 0) & (self.prev_vz < 0) & (vz >= 0) & (p[:, 2] < BOUNCE_Z)
        i = self._vi["bounce_depth"]
        self.sv[:, i] = torch.where(bnc, -p[:, 0], self.sv[:, i])
        self.bounced |= bnc
        self.prev, self.prev_vz = p.clone(), vz.clone()

    def _split_handoff(self, recv, handed, fire) -> None:
        """At the hand-off: the shot's spin and angle, the receiver's state; the flight trackers restart."""
        t, pc = self.t, self.t.pairs
        data = t._entity.data
        c, s = _yaw_frame(data.root_link_pose_w[:, 3:7])
        yaw = torch.atan2(s, c).abs() * (180.0 / math.pi)
        vals = {
            "spin": handed[:, 6:9].norm(dim=-1),
            "angle": torch.atan2(handed[:, 4], -handed[:, 3]) * (180.0 / math.pi),
            "pelvis_speed": data.root_link_lin_vel_w[:, :2].norm(dim=-1),
            "recover_dist": (t.pelvis_xy() - t.recover_xy).norm(dim=-1),
            "yaw_err": yaw,
            "idle": self.idle,
        }
        new = torch.full_like(self.sv, float("nan"))
        for name, v in vals.items():
            new[:, self._vi[name]] = v
        rm = recv.unsqueeze(-1)
        self.sv = torch.where(rm, new, self.sv)
        self.prev = torch.where(rm, handed[:, :3], self.prev)
        self.prev_vz = torch.where(recv, handed[:, 5], self.prev_vz)
        self.crossed &= ~recv
        self.bounced &= ~recv
        self.idle = torch.where(pc.court(fire).repeat(2), torch.zeros_like(self.idle), self.idle)  # rally start

    def step(self, over, legal, fell, crossing, dt, delay, contact=None, busy=None):
        pc, t = self.t.pairs, self.t
        self._predict_step()
        self._calls += 1
        if self.split:
            self._split_track(contact, dt)
        live0 = ~pc.court_dead.repeat(2)
        o = over
        if contact is not None:  # as pairs.py counts them (D-135): the hitter's fault is not the receiver's miss
            w = pc.waiting & ~contact
            o = over & ~(w & ~legal & (over & ~legal)[pc.partner])
        end = over & self.open
        counted = end & o & live0
        self.gk["void"].index_add_(0, self._gk(), (end & ~counted).long())
        self.open &= ~(end & ~counted)
        self.pend &= self.open
        self._book(counted, t.hit_done, legal, fell)
        fire, recv = self._orig_step(over, legal, fell, crossing, dt, delay, contact=contact, busy=busy)
        # the partner volleyed this env's return back before it landed: the open ball was returned (legal)
        early = recv & self.open & ~t.tallied & live0
        one = torch.ones_like(early)
        self._book(early, one, one, torch.zeros_like(early), early=one)
        self.open &= ~(fire | recv)  # defensive: a new feed replaces whatever was open
        # rally index: hand-offs on the court since its feeder ball
        cf, cr = pc.court(fire), pc.court(recv)
        self.nh = torch.where(cf, torch.zeros_like(self.nh), self.nh) + cr.long()
        k = self.nh.repeat(2)
        kb = (k.clamp(min=1, max=N_KBINS) - 1)
        st = torch.cat([t.ball.pos, t.ball.vel, t.ball.spin], -1)
        from picklebot_mj.tasks.return_stand import mirror_ball_states
        handed = mirror_ball_states(st)[pc.partner]  # what apply_actions installs as the receiver's feed
        data = t._entity.data
        c, s = _yaw_frame(data.root_link_pose_w[:, 3:7])
        r = recv
        rm = r.unsqueeze(-1)
        self.kb = torch.where(r, kb, self.kb)
        self.st = torch.where(rm, handed, self.st)
        self.spd = torch.where(r, handed[:, 3:6].norm(dim=-1), self.spd)
        self.hspd = torch.where(r, handed[:, 3:5].norm(dim=-1), self.hspd)
        self.pel0 = torch.where(rm, t.pelvis_xy(), self.pel0)
        self.c0, self.s0 = torch.where(r, c, self.c0), torch.where(r, s, self.s0)
        self.dirc = torch.where(r, torch.full_like(self.dirc, N_DIRS - 1), self.dirc)
        self.dist = torch.where(r, torch.full_like(self.dist, 1e3), self.dist)
        self.open |= r
        self.pend |= r
        self.gk["received"].index_add_(0, self._gk(), r.long())
        if self.split:
            self._split_handoff(recv, handed, fire)
        return fire, recv

    def on_reset(self, env_ids, fell_open=None):
        """A reset ends the env's open ball: a fall during it is a miss (fell); any other reset censors it (void if
        the court's rally had already ended)."""
        m = torch.zeros(self.n, dtype=torch.bool, device=self.dev)
        m[env_ids] = True
        mo = m & self.open
        live = ~self.t.pairs.court_dead.repeat(2)
        f = mo & live & (fell_open if fell_open is not None else torch.zeros_like(mo))
        self.gk["void"].index_add_(0, self._gk(), (mo & ~live).long())  # the court's rally had already ended
        self.gk["censored"].index_add_(0, self._gk(), (mo & live & ~f).long())
        self._book(f, self.t.hit_done, torch.zeros_like(f), f)
        self.open &= ~m
        self.pend &= ~m
        if self.split:  # a new episode starts the idle clock
            self.idle = torch.where(m, torch.zeros_like(self.idle), self.idle)
        return self._orig_reset(env_ids, fell_open)

    def counters(self) -> dict:
        """Cumulative counters for the training log (one host sync per call)."""
        out = {k: v.tolist() for k, v in self.c.items()}
        out["hspd_sum"] = [round(x, 4) for x in self.hspd_sum.tolist()]
        out.update({k: v.tolist() for k, v in self.hist.items()})
        out.update({k: v.tolist() for k, v in self.gk.items()})
        if self.split:
            out["split"] = {k: v.tolist() for k, v in self.shist.items()}
            out["split_legal"] = {k: v.tolist() for k, v in self.shist_legal.items()}
        return out


META = {"groups": ["pair", "drill"], "k_bins": ["1", "2", "3+"], "directions": list(DIR_NAMES),
        "speed_bin": SPEED_BIN, "dist_bin": DIST_BIN, "cell": "(group * 3 + k_bin) * 5 + direction",
        "split_vars": [list(v) for v in SPLIT_VARS], "split_cell": "(group * 3 + k_bin) * 40 + dist_bin; last var bin missing"}
