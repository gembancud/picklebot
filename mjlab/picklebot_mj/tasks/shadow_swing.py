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
# Footwork hint (follow-up S-D2b): an approximate interception point for each ghost-ball feed, shown through
# the existing spot input (`recovery` observation) until the swing window closes. Drag-free flight with an
# empirical shortfall, COR 0.64 bounce, 0.75 horizontal speed retention after the bounce; aim the paddle at the
# point where the ball descends through HINT_Z (or its apex if lower). The robot should stand beside it.
HINT_Z = 0.8
HINT_SHORTFALL = 0.085  # bounce lands ~8.5 % of the horizontal flight distance short of the drag-free aim
HINT_BEHIND = 0.3  # pelvis this far behind the contact point (toward the robot's baseline)
HINT_SIDE_FH, HINT_SIDE_BH = 0.5, 0.4  # pelvis to the left of a forehand / right of a backhand contact
D_BIN, D_BINS = 0.025, 80
# v2 hint (Drill 3, stage5-sd2c-videos.md): take the ball near the top of its bounce, at most HINT_TOP_Z high (on the
# rise for high bounces), and allow stance spots behind the baseline, where players stand for deep balls.
HINT_TOP_Z = 1.1
VOLLEY_Z = 1.0  # volley interception height (D-076)
VOLLEY_SHORTFALL = 0.095  # drag: the ball reaches VOLLEY_Z about 9.5 % of its drag-free distance short
HINT_BOX_V2 = ((-8.5, -2.4), (-3.5, 3.5))


# Per-family (shortfall / drag-free flight distance, vx after bounce / launch vx, vz after bounce / drag-free vz at
# the bounce), medians over sampled feeds of the analytic ball (artifacts/eval/hint_calib2.py, 2026-10-07).
HINT_TABLE = {
    "easy_forehand": (0.0827, 0.5505, 0.6047), "wide_forehand": (0.0827, 0.5505, 0.6047),
    "backhand": (0.0827, 0.5505, 0.6047), "deep": (0.0926, 0.5286, 0.6019), "short": (0.074, 0.5368, 0.6011),
    "high": (0.0804, 0.5277, 0.5953), "low": (0.0844, 0.6259, 0.6066), "fast": (0.0747, 0.6582, 0.6068),
    "topspin": (0.1028, 0.701, 0.612), "backspin": (0.0515, 0.5547, 0.5942),
    "reach_forehand": (0.0954, 0.5282, 0.5954), "reach_backhand": (0.0954, 0.5282, 0.5954),
    "reach_short": (0.0632, 0.5692, 0.6086), "reach_deep": (0.1285, 0.4788, 0.5881),
}


_CONSTS: dict = {}


def _const(key, values, device) -> torch.Tensor:
    """A constant tensor built once per device (rebuilding it per call costs a synchronising host copy; D-065)."""
    k = (key, str(device))
    if k not in _CONSTS:
        _CONSTS[k] = torch.tensor(values(), device=device)
    return _CONSTS[k]


def predict_intercept(p: torch.Tensor, v: torch.Tensor, fam: torch.Tensor, mode: str = "descend"):
    """Approximate (x, y) of the interception point of a just-launched feed.

    mode "descend" (S-D2b/S-D2c): where it descends through HINT_Z after its bounce (or its apex if lower).
    mode "top" (v2, Drill 3): its apex after the bounce, or where it rises through HINT_TOP_Z if the apex is higher.
    """
    from picklebot_mj.ball import BALL_RADIUS
    g, r = 9.81, BALL_RADIUS
    k = _const("hint_table", lambda: [HINT_TABLE[f] for f in FAMILY_NAMES], p.device)[fam]
    tb = (v[:, 2] + torch.sqrt((v[:, 2] ** 2 + 2 * g * (p[:, 2] - r)).clamp(min=0))) / g
    dist = (v[:, 0] * tb).abs()
    xb = p[:, 0] + v[:, 0] * tb - torch.sign(v[:, 0]) * k[:, 0] * dist  # lands short of the drag-free aim
    vz1 = k[:, 2] * (g * tb - v[:, 2]).clamp(min=0)
    vx1 = k[:, 1] * v[:, 0]
    apex = r + vz1 ** 2 / (2 * g)
    if mode == "top":
        ti = torch.where(apex > HINT_TOP_Z, (vz1 - torch.sqrt((vz1 ** 2 - 2 * g * (HINT_TOP_Z - r)).clamp(min=0))) / g,
                         vz1 / g)
    else:
        ti = torch.where(apex >= HINT_Z, (vz1 + torch.sqrt((vz1 ** 2 - 2 * g * (HINT_Z - r)).clamp(min=0))) / g,
                         vz1 / g)
    x = xb + vx1 * ti
    from picklebot_mj.feeds import VOLLEY_FAMILIES
    vol = _const("volley_mask", lambda: [f in VOLLEY_FAMILIES for f in FAMILY_NAMES], p.device)[fam]
    # Volleys (D-076): where the ball descends through VOLLEY_Z before its bounce (drag-free).
    tv = (v[:, 2] + torch.sqrt((v[:, 2] ** 2 + 2 * g * (p[:, 2] - VOLLEY_Z)).clamp(min=0))) / g
    x = torch.where(vol, p[:, 0] + v[:, 0] * tv * (1.0 - VOLLEY_SHORTFALL), x)  # drag shortens the flight
    return x, p[:, 1]


def stance_spot(term, v2: bool) -> torch.Tensor:
    """Stance spot beside the predicted interception point of each env's current (just launched) ball."""
    from picklebot_mj.tasks.move_drill import SPOT_BOX
    xi, yi = predict_intercept(term.ball.pos, term.ball.vel, term.family, "top" if v2 else "descend")
    pel = term.pelvis_xy()
    forehand = yi <= pel[:, 1]  # ball on the robot's right (-y) -> forehand
    if getattr(term.cfg, "hint_forehand_only", False):  # H4 run 7 (D-059): every ball taken on the forehand side
        forehand = torch.ones_like(forehand)
    sy = torch.where(forehand, yi + HINT_SIDE_FH, yi - HINT_SIDE_BH)
    sx = xi - HINT_BEHIND
    box = HINT_BOX_V2 if v2 else SPOT_BOX
    lo = _const(("box_lo", v2), lambda: [box[0][0], box[1][0]], term.device)
    hi = _const(("box_hi", v2), lambda: [box[0][1], box[1][1]], term.device)
    return torch.stack([sx, sy], -1).clamp(lo, hi)


class ShadowSwing:
    def __init__(self, term, swing_prob: float, swing_mix, seed: int, hint: bool = False, hint_v2: bool = False):
        n, dev = term.num_envs, term.device
        self.hint, self.hint_v2 = bool(hint), bool(hint_v2)
        self.recover_true = term.recover_xy.clone()
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
        from picklebot_mj.rules import _fill
        for f in (self.bounced, self.open, self.closed):
            _fill(f, env_ids, False)
        _fill(self.elapsed, env_ids, 0.0)
        _fill(self.dmin, env_ids, FAR)

    def after_refeed(self, fire: torch.Tensor) -> None:
        m = fire & self.swing_ep  # mask form of _clear(nonzero(m)): no host sync
        for f in (self.bounced, self.open, self.closed):
            f.masked_fill_(m, False)
        self.elapsed.masked_fill_(m, 0.0)
        self.dmin.masked_fill_(m, FAR)
        self.t.tallied |= self.swing_ep  # swing feeds are never tallied as hitting outcomes
        self.after_feed(fire)

    def after_feed(self, mask: torch.Tensor) -> None:
        """New feeds in `mask`: remember the true recovery spot; show the interception hint for swing feeds."""
        t = self.t
        self.recover_true = torch.where(mask.unsqueeze(-1), t.recover_xy, self.recover_true)
        if not self.hint:
            return
        m = mask & self.swing_ep
        t.recover_xy = torch.where(m.unsqueeze(-1), self.intercept_spot(), t.recover_xy)

    def intercept_spot(self) -> torch.Tensor:
        """Approximate stance spot for intercepting each env's current (just launched) ball."""
        return stance_spot(self.t, self.hint_v2)

    def paddle_for_sim(self, paddle_pos: torch.Tensor) -> torch.Tensor:
        """Move the paddle out of the ball simulation for swing episodes (ghost ball)."""
        far = _const("far", lambda: [0.0, 0.0, FAR], self.dev)
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
        b = (self.dmin.nan_to_num(nan=1e3, posinf=1e3, neginf=0.0) / D_BIN).clamp(0, D_BINS - 1).long()  # NaN-safe
        self.d_hist.view(-1).index_add_(0, fam * D_BINS + b, close.long())
        # Close: recovery phase (the spot input returns to the true recovery spot), then the next feed.
        if self.hint:
            t.recover_xy = torch.where(close.unsqueeze(-1), self.recover_true, t.recover_xy)
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

# Stage 5C families (D-076): calibrated with artifacts/eval/hint_calib2.py. Volleys are intercepted before their
# bounce (predict_intercept, VOLLEY_Z).
HINT_TABLE.update({"drop": (0.0761, 0.4537, 0.6028), "lob": (0.144, 0.471, 0.5791),  # hint_calib2.py, 2026-10-14
                   "cross_forehand": (0.1027, 0.526, 0.5922), "cross_backhand": (0.1027, 0.526, 0.5922),
                   "volley_forehand": HINT_TABLE["easy_forehand"], "volley_backhand": HINT_TABLE["easy_forehand"]})
