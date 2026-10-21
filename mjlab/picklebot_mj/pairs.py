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


class PairCourts:
    def __init__(self, n: int, device, handoff: str = "crossing"):
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
        self._end(m)
        self.parked |= m

    def _end(self, env_mask: torch.Tensor) -> None:
        c = self.court(env_mask) & ~self.court_dead
        idx = self.rally_len.clamp(max=MAX_LEN)
        self.len_hist.index_add_(0, idx, (c & self.started).long())  # the initial reset is not a rally
        self.rally_len = torch.where(c, torch.zeros_like(self.rally_len), self.rally_len)
        self.rally_idx = self.rally_idx + c.long()
        self.court_dead |= c

    def step(self, over: torch.Tensor, legal: torch.Tensor, fell: torch.Tensor, crossing: torch.Tensor,
             dt: float, delay: float, contact: torch.Tensor | None = None) -> tuple[torch.Tensor, torch.Tensor]:
        """One physics step. over: this env's feed finished now; legal: it finished as a legal return; fell: it
        finished by a fall; crossing: this env's return crossed the net now; contact: this env's robot made its first
        legal contact now (used by the "contact" hand-off). Returns (feeder_fire, receive) masks."""
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
        self.side_stats_own += torch.stack([cnt(own), cnt(own & legal), cnt(own & fell)], -1)
        fed = over & ~self.handed
        per = torch.stack([own, own & legal, fed, fed & legal], -1) & live.unsqueeze(-1)
        self.court_counts.index_add_(0, torch.arange(self.n, device=over.device) % self.h, per.long())
        ok = (over & legal).long()
        self.rally_len += torch.where(self.court_dead, torch.zeros_like(self.rally_len), ok[: self.h] + ok[self.h:])
        self._end(over & ~legal)
        self.parked |= done  # a finished feed leaves no ball in play in this env
        trigger = contact if (self.handoff == "contact" and contact is not None) else crossing
        receive = trigger[self.partner] & ~self.court_dead.repeat(2)
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
        self.timer = torch.where(go, torch.full_like(self.timer, -1.0), self.timer)
        self.court_dead &= ~go
        self.started |= go
        pick_b = (self.rally_idx % 2).bool()  # alternate the side that receives the feeder ball
        fire = torch.cat([go & ~pick_b, go & pick_b])
        self.parked &= ~fire
        self.handed &= ~fire  # a feeder ball
        self.n_started[0] += fire.sum()
        self.waiting &= ~fire
        return fire, receive

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
        return {"rallies": n, "p_len_ge_4": ge(4), "p_len_ge_5": ge(5), "p_len_ge_10": ge(10), "mean_len": mean,
                "handoff": self.handoff, "sides": side, "started": {"feeder": int(self.n_started[0]),
                "handoffs": int(self.n_started[1])}, "court_counts": self.court_counts.tolist(),
                "sides_own_ball": side_own, "len_hist": h}
