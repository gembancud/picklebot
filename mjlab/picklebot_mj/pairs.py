"""Two-robot courts from mirrored environment pairs (self-play readiness R4, D-116; panel round 8, architecture).

Env i and env i + n/2 form one court. Each robot stays in its own env and always sees itself on the near side, so
observations, actions, the controller and the runner are unchanged. One ball per court:
- when a robot's return crosses the net in its env, the partner env receives that ball, mirrored (a 180-degree turn
  about the court centre), as its next feed (rally phase);
- the returning env keeps simulating its own copy until it lands, which is how that return is judged in or out;
- any feed that ends without a legal return, or a robot reset (a fall), ends the court's rally. When both envs of
  the court have no ball in play, a feeder ball starts the next rally after the refeed delay, on alternating sides.

Counts (no host syncs): rallies by length in consecutive legal robot shots (the feeder ball is not a shot), and per
side feeds, legal returns and falls.
"""

from __future__ import annotations

import torch

MAX_LEN = 64
HO_BINS = 8  # D-223: receiver-distance bins for the hand-off outcome tally (the task's LAUNCH_D_EDGES + 1 <= 8)


class PairCourts:
    def __init__(self, n: int, device, handoff: str = "crossing", rally_cap: int = 0):
        assert n % 2 == 0, "pair mode needs an even number of envs"
        assert handoff in ("crossing", "contact"), handoff
        # D-135: "crossing" (D-116) hands a return to the partner when it crosses the net, so the receiver first sees it
        # mid-flight; "contact" hands it over at the hitter's legal contact, so the receiver sees it leave the paddle.
        self.handoff = handoff
        self.n, self.h = n, n // 2
        ids = torch.arange(n, device=device)
        self.partner = (ids + self.h) % n
        self.side = (ids >= self.h).long()  # 0 = side A, 1 = side B
        b = lambda: torch.zeros(n, dtype=torch.bool, device=device)  # noqa: E731
        self.court_dead = torch.zeros(self.h, dtype=torch.bool, device=device)  # rally over, waiting to restart
        self.rally_len = torch.zeros(self.h, dtype=torch.long, device=device)
        self.rally_idx = torch.zeros(self.h, dtype=torch.long, device=device)  # parity picks the restarting side
        self.timer = torch.full((self.h,), -1.0, device=device)
        self.started = torch.zeros(self.h, dtype=torch.bool, device=device)  # a feeder ball has started a rally
        self.parked = b()  # no ball in play in this env (waiting for the partner, or a parked reset)
        self.len_hist = torch.zeros(MAX_LEN + 1, dtype=torch.long, device=device)
        self.side_stats = torch.zeros(2, 3, dtype=torch.long, device=device)  # feeds, legal returns, falls
        # D-116 tightening: the same on own-ball shots only (feeds handed over by the partner; the feeder ball excluded)
        self.handed = torch.zeros(n, dtype=torch.bool, device=device)
        self.side_stats_own = torch.zeros(2, 3, dtype=torch.long, device=device)
        self.waiting = torch.zeros(n, dtype=torch.bool, device=device)  # D-135: holds the partner's ball, not yet touched
        # D-137: per-court counts for court-cluster bootstrap intervals: [own-ball feeds, own legal, feeder feeds, feeder
        # legal], and all feeds started (feeder balls, hand-offs, faulted hand-offs included) for the court share
        self.court_counts = torch.zeros(self.h, 4, dtype=torch.long, device=device)
        self.n_started = torch.zeros(2, dtype=torch.long, device=device)  # feeder balls, hand-offs
        # D-161 (training only; 0 = off, as in every read): a court's rally ends once its rally_cap-th shot is finished.
        # Shots are counted at the hitter's trigger (contact or crossing), so a volley cannot slip past the cap; the
        # capped shot is not handed over, it lands and is judged as usual, and a feeder ball starts the next rally.
        # It holds the feeder ball's share of play at >= 1 / rally_cap however long the policy can rally.
        self.rally_cap = int(rally_cap)
        self.shots = torch.zeros(self.h, dtype=torch.long, device=device)
        self.final = torch.zeros(n, dtype=torch.bool, device=device)
        # D-163 (logging only): an optional per-court group (0 or 1, e.g. pair vs drill courts) and the rally-length
        # histogram per group; None leaves len_hist the only histogram, as before.
        self.group = None
        self.len_hist_group = torch.zeros(2, MAX_LEN + 1, dtype=torch.long, device=device)
        # rally ends per group and reason: 0 the shot was not a legal return, 1 returned to a busy partner, 2 a robot
        # reset (fall or time-out), 3 the rally cap
        self.end_reasons = torch.zeros(2, 4, dtype=torch.long, device=device)
        self.last_len = torch.zeros(self.h, dtype=torch.long, device=device)  # D-165: the court's last finished rally
        # D-223 (logging only): hand-off outcomes by class (0 = the rally's first hand-off, 1 = later) and by the
        # receiver's distance bin at the hand-off (ho_dbin_now, set by the task each step; None = not tallied):
        # ho_out[class, bin] = [own-ball feeds finished, legal]; the same filtered feeds as court_counts' own columns.
        self.ho_dbin_now = None
        self.ho_count = torch.zeros(self.h, dtype=torch.long, device=device)
        self.ho_cls = torch.zeros(n, dtype=torch.long, device=device)
        self.ho_dbin = torch.zeros(n, dtype=torch.long, device=device)
        self.ho_out = torch.zeros(2, HO_BINS, 2, dtype=torch.long, device=device)
        # D-224 fix: the env holds a ball received in the court's current rally (set on receive; cleared for both envs
        # at a feeder ball and on reset, and once tallied). Only these are tallied: a reset (leak) ball on an env whose
        # `handed` survived on_reset carried a stale class (D-223 INVALID). `handed` itself is untouched.
        self.ho_live = torch.zeros(n, dtype=torch.bool, device=device)
        # reported only: own-ball feeds finished with no live received ball (stale `handed`), and class-0 feeds tallied
        # while the court's rally length is still 0 (the hitter's copy not yet judged: a receiver's early volley)
        self.ho_stale = torch.zeros(2, dtype=torch.long, device=device)

    def court(self, mask: torch.Tensor) -> torch.Tensor:
        """Per-env mask -> per-court mask (either env)."""
        return mask[: self.h] | mask[self.h:]

    def on_reset(self, env_ids: torch.Tensor, fell_open: torch.Tensor | None = None) -> None:
        """A robot reset (a fall or a time-out) ends its court's rally and parks the env. fell_open (per env): a feed
        was in play and ended by the fall (counted as that side's feed and fall)."""
        m = torch.zeros(self.n, dtype=torch.bool, device=self.partner.device)
        m[env_ids] = True
        if fell_open is not None:
            f = fell_open & m & ~self.court_dead.repeat(2)
            self.side_stats[:, 0] += torch.stack([(f & (self.side == k)).sum() for k in (0, 1)])
            self.side_stats[:, 2] += torch.stack([(f & (self.side == k)).sum() for k in (0, 1)])
            # D-138: a feed ended by a fall is a miss in the own-ball and per-court counts too (they used to leave it out)
            fo = f & self.handed
            self._ho_tally(fo, torch.zeros_like(fo))
            self.side_stats_own[:, 0] += torch.stack([(fo & (self.side == k)).sum() for k in (0, 1)])
            self.side_stats_own[:, 2] += torch.stack([(fo & (self.side == k)).sum() for k in (0, 1)])
            per = torch.stack([fo, torch.zeros_like(fo), f & ~self.handed, torch.zeros_like(fo)], -1)
            self.court_counts.index_add_(0, torch.arange(self.n, device=f.device) % self.h, per.long())
        self.ho_live &= ~m  # D-224: a reset ends what the env held
        self._end(m, reason=2)
        self.parked |= m
        self.final &= ~m

    def _end(self, env_mask: torch.Tensor, reason: int = 0) -> None:
        c = self.court(env_mask) & ~self.court_dead
        idx = self.rally_len.clamp(max=MAX_LEN)
        self.len_hist.index_add_(0, idx, (c & self.started).long())  # the initial reset is not a rally
        if self.group is not None:
            self.len_hist_group.view(-1).index_add_(0, self.group * (MAX_LEN + 1) + idx, (c & self.started).long())
            self.end_reasons[:, reason] += torch.stack([(c & self.started & (self.group == g)).sum() for g in (0, 1)])
        self.last_len = torch.where(c, self.rally_len, self.last_len)
        self.rally_len = torch.where(c, torch.zeros_like(self.rally_len), self.rally_len)
        self.shots = torch.where(c, torch.zeros_like(self.shots), self.shots)
        self.rally_idx = self.rally_idx + c.long()
        self.court_dead |= c

    def step(self, over: torch.Tensor, legal: torch.Tensor, fell: torch.Tensor, crossing: torch.Tensor,
             dt: float, delay: float, contact: torch.Tensor | None = None,
             busy: torch.Tensor | None = None) -> tuple[torch.Tensor, torch.Tensor]:
        """One physics step. over: this env's feed finished now; legal: it finished as a legal return; fell: it
        finished by a fall; crossing: this env's return crossed the net now; contact: this env's robot made its first
        legal contact now (used by the "contact" hand-off); busy: this env's robot is in a ball-free drill episode (a
        move-to-spot episode, D-140), so it gets no ball: a return to it ends the rally once it lands, and the feeder
        ball goes to the other side. Returns (feeder_fire, receive) masks."""
        if self.handoff == "contact":
            # D-135: the receiver's copy of a return that faulted (net, out) ends on the same step as the hitter's own
            # copy; that fault is the hitter's, so it is not counted as the receiver's feed or miss.
            # The copy still ends (the env is parked below), it is only left out of the counts.
            if contact is not None:
                self.waiting &= ~contact
            done = over
            over = over & ~(self.waiting & ~legal & (over & ~legal)[self.partner])
            self.waiting &= ~done
        else:
            done = over
        s = self.side
        live = ~self.court_dead.repeat(2)  # feeds of a court whose rally has ended are not counted
        cnt = lambda m: torch.stack([(m & live & (s == k)).sum() for k in (0, 1)])  # noqa: E731
        self.side_stats += torch.stack([cnt(over), cnt(over & legal), cnt(over & fell)], -1)
        own = over & self.handed
        self._ho_tally(own & live, own & live & legal)
        self.side_stats_own += torch.stack([cnt(own), cnt(own & legal), cnt(own & fell)], -1)
        fed = over & ~self.handed
        per = torch.stack([own, own & legal, fed, fed & legal], -1) & live.unsqueeze(-1)
        self.court_counts.index_add_(0, torch.arange(self.n, device=over.device) % self.h, per.long())
        ok = (over & legal).long()
        self.rally_len += torch.where(self.court_dead, torch.zeros_like(self.rally_len), ok[: self.h] + ok[self.h:])
        self._end(over & ~legal)
        if busy is not None:  # D-140: a legal return to a busy partner ends the rally (nobody can play it)
            self._end(over & legal & busy[self.partner], reason=1)
        if self.rally_cap > 0:  # D-161: the capped shot has finished (legal or not): the rally ends
            self._end(done & self.final, reason=3)
            self.final &= ~done
        self.parked |= done  # a finished feed leaves no ball in play in this env
        trigger = contact if (self.handoff == "contact" and contact is not None) else crossing
        receive = trigger[self.partner] & ~self.court_dead.repeat(2)
        if self.rally_cap > 0:  # D-161: count this step's shots; the rally_cap-th is not handed over
            t = trigger & ~self.court_dead.repeat(2)
            self.shots = self.shots + t[: self.h].long() + t[self.h:].long()
            self.final |= t & (self.shots >= self.rally_cap).repeat(2)
            receive = receive & ~self.final[self.partner]
        if busy is not None:
            receive = receive & ~busy
        if self.ho_dbin_now is not None:  # D-223: class and receiver distance at the hand-off
            self.ho_dbin = torch.where(receive, self.ho_dbin_now.clamp(max=HO_BINS - 1), self.ho_dbin)
            self.ho_cls = torch.where(receive, (self.ho_count > 0).long().repeat(2), self.ho_cls)
            self.ho_count = self.ho_count + self.court(receive).long()
            self.ho_live |= receive  # D-224
        self.parked &= ~receive
        self.handed = self.handed | receive  # the feed now in play is a partner's ball
        self.n_started[1] += receive.sum()
        self.waiting = (self.waiting & ~done) | receive
        both_idle = self.parked[: self.h] & self.parked[self.h:]
        start = self.court_dead & both_idle & (self.timer < 0)
        self.timer = torch.where(start, torch.full_like(self.timer, delay), self.timer)
        run = self.timer >= 0
        self.timer = torch.where(run, self.timer - dt, self.timer)
        go = run & (self.timer <= 0)
        if busy is not None:  # D-140: a court with both robots busy waits (its timer holds at 0)
            both_busy = busy[: self.h] & busy[self.h:]
            self.timer = torch.where(go & both_busy, torch.zeros_like(self.timer), self.timer)
            go = go & ~both_busy
        self.timer = torch.where(go, torch.full_like(self.timer, -1.0), self.timer)
        self.court_dead &= ~go
        self.ho_count = torch.where(go, torch.zeros_like(self.ho_count), self.ho_count)  # D-223
        self.ho_live &= ~go.repeat(2)  # D-224: a new rally; nothing held is from it yet
        self.started |= go
        pick_b = (self.rally_idx % 2).bool()  # alternate the side that receives the feeder ball
        if busy is not None:  # D-140: never to a busy robot
            pick_b = torch.where(busy[: self.h], torch.ones_like(pick_b), torch.where(busy[self.h:], torch.zeros_like(pick_b), pick_b))
        fire = torch.cat([go & ~pick_b, go & pick_b])
        self.parked &= ~fire
        self.handed &= ~fire  # a feeder ball
        self.n_started[0] += fire.sum()
        self.waiting &= ~fire
        return fire, receive

    def count_early(self, early: torch.Tensor, h0: torch.Tensor, live0: torch.Tensor) -> None:
        """Audit 2026-10-28 (pair_count_volleys): count returns volleyed back by the partner (the task's _credit_early,
        after step) as legal returns: feeds, legal returns, own-ball / feeder split and the court's rally length. h0 and
        live0 are the ball types and court liveness before this step's update."""
        e = early & live0
        s = self.side
        cnt = lambda m: torch.stack([(m & (s == k)).sum() for k in (0, 1)])  # noqa: E731
        z = torch.zeros(2, dtype=torch.long, device=e.device)
        self.side_stats += torch.stack([cnt(e), cnt(e), z], -1)
        own = e & h0
        self.side_stats_own += torch.stack([cnt(own), cnt(own), z], -1)
        self._ho_tally(own, own)
        fed = e & ~h0
        per = torch.stack([own, own, fed, fed], -1)
        self.court_counts.index_add_(0, torch.arange(self.n, device=e.device) % self.h, per.long())
        ok = e.long()
        self.rally_len += torch.where(self.court_dead, torch.zeros_like(self.rally_len), ok[: self.h] + ok[self.h:])

    def _ho_tally(self, done: torch.Tensor, legal: torch.Tensor) -> None:
        """D-223: finished own-ball feeds (and their legal returns) by hand-off class and receiver distance bin."""
        if self.ho_dbin_now is None:
            return
        self.ho_stale[0] += (done & ~self.ho_live).sum()
        self.ho_stale[1] += (done & self.ho_live & (self.ho_cls == 0) & (self.rally_len.repeat(2) == 0)).sum()
        k = (self.ho_cls * HO_BINS + self.ho_dbin) * 2
        self.ho_out.view(-1).index_add_(0, k, (done & self.ho_live).long())
        self.ho_out.view(-1).index_add_(0, k + 1, (legal & self.ho_live).long())
        self.ho_live &= ~done  # D-224: once per received ball

    def summary(self) -> dict:
        h = self.len_hist.tolist()
        n = sum(h)
        ge = lambda k: round(sum(h[k:]) / n, 4) if n else None  # noqa: E731
        st = self.side_stats.tolist()
        side = {name: {"feeds": f, "legal": round(l / f, 4) if f else None, "falls_per_shot": round(x / f, 4) if f else None}
                for name, (f, l, x) in zip(("A", "B"), st)}
        mean = round(sum(i * c for i, c in enumerate(h)) / n, 3) if n else None
        so = self.side_stats_own.tolist()
        side_own = {name: {"feeds": f, "legal": round(l / f, 4) if f else None} for name, (f, l, x) in zip(("A", "B"), so)}
        # Audit 2026-10-28: rallies still running when the read ends never reach len_hist (only _end fills it), so long
        # rallies are under-counted. Reported beside the old fields (unchanged): the open rallies' lengths, and P(k+)
        # counting an open rally that already has k or more shots as a success (open rallies below k are left out).
        op = (self.started & ~self.court_dead)
        oh = torch.zeros(MAX_LEN + 1, dtype=torch.long, device=op.device).index_add_(
            0, self.rally_len.clamp(max=MAX_LEN), op.long()).tolist()
        ge_open = lambda k: round((sum(h[k:]) + sum(oh[k:])) / (n + sum(oh[k:])), 4) if n else None  # noqa: E731
        return {"open_len_hist": oh, "p_len_ge_3_with_open": ge_open(3), "p_len_ge_5_with_open": ge_open(5),
                "rallies": n, "p_len_ge_4": ge(4), "p_len_ge_5": ge(5), "p_len_ge_10": ge(10), "mean_len": mean,
                "handoff": self.handoff, "sides": side, "started": {"feeder": int(self.n_started[0]),
                "handoffs": int(self.n_started[1])}, "court_counts": self.court_counts.tolist(),
                "sides_own_ball": side_own, "len_hist": h, "handoff_by_d": self.ho_out.tolist(),
                "handoff_stale": self.ho_stale.tolist()}
