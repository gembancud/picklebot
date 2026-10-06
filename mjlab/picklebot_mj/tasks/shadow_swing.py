"""Stage 5 Drill 2 (D-041/D-042): move and shadow-swing at a ghost ball.

In *swing episodes* a real feed is launched (its family drawn from `swing_mix`, which includes the
reach families on both sides, short and deep), and the ball flies its real analytic path, but the
paddle cannot touch it (the paddle is moved out of the ball simulation for these envs) and its
outcome is never tallied. The robot must move, set its feet and swing the paddle through the ball's
path at the right moment, then recover to the commanded spot.

The hitting window opens at the ball's first bounce and closes at its second bounce, when it is lost
behind or beside the robot, or after WINDOW_MAX_S. Within the window the closest paddle-ball approach
is tracked, with the paddle's speed toward the net and the base speed at that moment. When the window
closes the one-shot swing reward is paid:
    exp(-(d_min / CONTACT_STD)^2) * (0.5 + 0.5 * clip(v_x / 3 m/s, 0, 1)) * (0.7 + 0.3 * feet_set)
`hit_done` is then set (so the recovery reward and metric apply) and the next feed follows
after RECOVER_S. The closest-approach distance includes timing: an early or late swing passes far
from the ball. Per-family metrics: swings, median d_min, share within CONTACT_TOL, mean v_x at d_min,
feet-set rate.
"""

from __future__ import annotations

import torch

from picklebot_mj.feeds import FAMILY_NAMES

CONTACT_STD = 0.15
CONTACT_TOL = 0.15
HIT_Z = (0.35, 1.25)
WINDOW_MAX_S = 3.5
RECOVER_S = 1.5
FEET_SET_SPEED = 0.3
FAR = 100.0
D_BIN, D_BINS = 0.025, 80


class ShadowSwing:
    def __init__(self, term, swing_prob: float, swing_mix, seed: int):
        n, dev = term.num_envs, term.device
        self.t, self.n, self.dev = term, n, dev
        self.swing_prob = float(swing_prob)
        self.gen = torch.Generator(device=dev).manual_seed(int(seed) + 314159)
        self.mix = torch.tensor(swing_mix.vector(), device=dev)
        b = lambda: torch.zeros(n, dtype=torch.bool, device=dev)
        z = lambda: torch.zeros(n, device=dev)
        self.swing_ep, self.bounced, self.open, self.closed = b(), b(), b(), b()
        self.elapsed, self.dmin, self.vx_at, self.speed_at = z(), torch.full((n,), FAR, device=dev), z(), z()
        self.swing_now = z()
        nf = len(FAMILY_NAMES)
        self.stats = {k: torch.zeros(nf, device=dev) for k in ("swings", "within", "vx_sum", "feet_set")}
        self.d_hist = torch.zeros(nf, D_BINS, dtype=torch.long, device=dev)

    # --- episode / feed hooks ---------------------------------------------------------
    def assign(self, env_ids: torch.Tensor, move_prob: float) -> None:
        """Choose swing episodes among env_ids (before the feed; move episodes override later)."""
        p = self.swing_prob / max(1e-6, 1.0 - move_prob)
        self.swing_ep[env_ids] = torch.rand(len(env_ids), generator=self.gen, device=self.dev) < p
        self._clear(env_ids)

    def drop_moves(self, move_ep: torch.Tensor) -> None:
        self.swing_ep &= ~move_ep

    def family(self, env_ids: torch.Tensor, fam: torch.Tensor) -> torch.Tensor:
        """Swing episodes draw their family from the swing mix."""
        alt = torch.multinomial(self.mix, len(env_ids), replacement=True, generator=self.gen)
        return torch.where(self.swing_ep[env_ids], alt, fam)

    def _clear(self, env_ids) -> None:
        for f in (self.bounced, self.open, self.closed):
            f[env_ids] = False
        self.elapsed[env_ids] = 0.0
        self.dmin[env_ids] = FAR

    def after_refeed(self, fire: torch.Tensor) -> None:
        idx = torch.nonzero(fire & self.swing_ep).squeeze(-1)
        self._clear(idx)
        self.t.tallied |= self.swing_ep  # swing feeds are never tallied as hitting outcomes

    def paddle_for_sim(self, paddle_pos: torch.Tensor) -> torch.Tensor:
        """Move the paddle out of the ball simulation for swing episodes (ghost ball)."""
        far = torch.tensor([0.0, 0.0, FAR], device=self.dev)
        return torch.where(self.swing_ep.unsqueeze(-1), paddle_pos + far, paddle_pos)

    # --- per physics step ---------------------------------------------------------------
    def step(self, dt: float, court_contact: torch.Tensor, paddle_pos: torch.Tensor, paddle_vel: torch.Tensor,
             base_speed: torch.Tensor) -> None:
        t, s = self.t, self.swing_ep
        ball = t.ball.pos
        active = s & ~self.closed
        self.elapsed = self.elapsed + dt * active.float()
        second = active & self.bounced & court_contact
        self.bounced |= active & court_contact
        in_band = (ball[:, 2] >= HIT_Z[0]) & (ball[:, 2] <= HIT_Z[1])
        window = active & self.bounced & ~second & in_band
        d = (ball - paddle_pos).norm(dim=-1)
        better = window & (d < self.dmin)
        self.dmin = torch.where(better, d, self.dmin)
        self.vx_at = torch.where(better, paddle_vel[:, 0], self.vx_at)
        self.speed_at = torch.where(better, base_speed, self.speed_at)
        pelvis = t.pelvis_xy()
        gone = (ball[:, 0] < pelvis[:, 0] - 1.5) | ((ball[:, 1] - pelvis[:, 1]).abs() > 4.0)
        close = active & (second | (self.bounced & gone) | (self.elapsed > WINDOW_MAX_S))
        feet = (self.speed_at < FEET_SET_SPEED).float()
        r = torch.exp(-(self.dmin / CONTACT_STD) ** 2) * (0.5 + 0.5 * (self.vx_at / 3.0).clamp(0, 1)) * (0.7 + 0.3 * feet)
        self.swing_now = self.swing_now + r * close.float()
        # Metrics.
        fam, c = t.family, close.float()
        self.stats["swings"].index_add_(0, fam, c)
        self.stats["within"].index_add_(0, fam, c * (self.dmin <= CONTACT_TOL).float())
        self.stats["vx_sum"].index_add_(0, fam, c * self.vx_at)
        self.stats["feet_set"].index_add_(0, fam, c * feet)
        b = (self.dmin / D_BIN).long().clamp(max=D_BINS - 1)
        self.d_hist.view(-1).index_add_(0, fam * D_BINS + b, close.long())
        # Close: recovery phase, then the next feed.
        self.closed |= close
        t.hit_done |= close
        t.refeed_timer = torch.where(close, torch.full_like(t.refeed_timer, RECOVER_S), t.refeed_timer)

    def consume(self) -> torch.Tensor:
        r = self.swing_now
        self.swing_now = torch.zeros_like(r)
        return r

    def summary(self) -> dict:
        out = {}
        for i, name in enumerate(FAMILY_NAMES):
            n = float(self.stats["swings"][i])
            if n == 0:
                continue
            h = self.d_hist[i].double()
            cdf = h.cumsum(0) / max(float(h.sum()), 1.0)
            out[name] = {"swings": int(n), "median_dmin_m": round(float(((cdf < 0.5).sum() + 0.5) * D_BIN), 3),
                         "within_tol": round(float(self.stats["within"][i]) / n, 4),
                         "mean_paddle_vx": round(float(self.stats["vx_sum"][i]) / n, 3),
                         "feet_set": round(float(self.stats["feet_set"][i]) / n, 4)}
        return out


def shadow_swing_reward(env) -> torch.Tensor:
    t = env.action_manager.get_term("ball")
    if t.shadow is None:
        return torch.zeros(env.num_envs, device=env.device)
    return t.shadow.consume()
