"""Rally drill v2 (Stage 5E, D-097): a feed mix, recovery rule and pacing closer to a real rally.

**Feed groups** (evenly weighted inside each group):
- neutral 60 %: easy_forehand, wide_forehand, backhand, deep, short, high, low, topspin;
- moderate 25 %: fast, backspin, reach_forehand, reach_backhand, reach_short;
- extreme 15 %: cross_forehand, cross_backhand, reach_deep, drop.

Never two extremes in a row. After an extreme feed the next one is drawn from neutral and moderate (renormalised),
so the long-run extreme share is 0.15 / 1.15 = 13.0 %. Lob and the volley families are not part of drill v2. They stay
in the court drill (h5c_eval) and its kill rules.

**Failure weighting** (training only): each family's weight is scaled by (FAIL_FLOOR + its EMA failure rate), and
the extreme share is capped at EXTREME_CAP. Evaluation always uses the fixed mix.

**Recovery** (where a player goes after the hit): at the first legal contact the recovery spot becomes
    x = clamp(x_pelvis, -5.6, -4.5),  y = clamp(0.4 y_pelvis, -1.2, 1.2)
from the pelvis at contact. Until the robot's first contact of an episode it is the baseline centre
(return_stand.RECOVERY_FIXED).

**Pacing:** the next feed comes REFEED_V2_S after the robot's return lands or the ball is ruled dead.

Feeds are court-anchored: every shot is aimed relative to the fixed start spot, as in the rally evaluation, so the
robot has to get to the ball.
"""

from __future__ import annotations

import torch

from picklebot_mj.feeds import FAMILY_NAMES

DRILL_V2_GROUPS: dict[str, tuple[str, ...]] = {
    "neutral": ("easy_forehand", "wide_forehand", "backhand", "deep", "short", "high", "low", "topspin"),
    "moderate": ("fast", "backspin", "reach_forehand", "reach_backhand", "reach_short"),
    "extreme": ("cross_forehand", "cross_backhand", "reach_deep", "drop"),
}
GROUP_NAMES: tuple[str, ...] = tuple(DRILL_V2_GROUPS)
GROUP_SHARES: dict[str, float] = {"neutral": 0.60, "moderate": 0.25, "extreme": 0.15}
REFEED_V2_S = 0.2
RECOVERY_X = (-5.6, -4.5)
RECOVERY_Y_GAIN, RECOVERY_Y_MAX = 0.4, 1.2
EXTREME_CAP = 0.25  # failure weighting may raise the extreme share up to this
FAIL_FLOOR = 0.05  # mastered families keep some weight
FAIL_EMA_RATE = 0.02  # per finished feed of a family, capped at 0.5 per update


def group_index() -> list[int]:
    """Group of every family in FAMILY_NAMES (0 neutral, 1 moderate, 2 extreme, -1 not in drill v2)."""
    g = [-1] * len(FAMILY_NAMES)
    for gi, name in enumerate(GROUP_NAMES):
        for f in DRILL_V2_GROUPS[name]:
            g[FAMILY_NAMES.index(f)] = gi
    return g


def base_weights() -> list[float]:
    """Fixed per-family weights (sum 1): group share / group size."""
    w = [0.0] * len(FAMILY_NAMES)
    for name in GROUP_NAMES:
        for f in DRILL_V2_GROUPS[name]:
            w[FAMILY_NAMES.index(f)] = GROUP_SHARES[name] / len(DRILL_V2_GROUPS[name])
    return w


def recovery_spot(pelvis_xy: torch.Tensor) -> torch.Tensor:
    """Recovery spot (N, 2) from the pelvis position at the first legal contact."""
    x = pelvis_xy[:, 0].clamp(*RECOVERY_X)
    y = (RECOVERY_Y_GAIN * pelvis_xy[:, 1]).clamp(-RECOVERY_Y_MAX, RECOVERY_Y_MAX)
    return torch.stack([x, y], -1)


class DrillV2Sampler:
    """Per-env family draws for drill v2 (no host syncs)."""

    def __init__(self, n: int, device, gen: torch.Generator, fail_weighting: bool = False):
        self.gen, self.device = gen, device
        self.fail_weighting = bool(fail_weighting)
        self.group = torch.tensor(group_index(), device=device)
        self.base = torch.tensor(base_weights(), device=device)
        self.is_ext = self.group == 2
        self.in_v2 = self.group >= 0
        self.last_ext = torch.zeros(n, dtype=torch.bool, device=device)
        self.fail_ema = torch.full((len(FAMILY_NAMES),), 0.5, device=device)

    def weights(self) -> torch.Tensor:
        """Current per-family weights (sum 1): fixed, or failure-weighted with the extreme share capped."""
        if not self.fail_weighting:
            return self.base
        w = self.base * (FAIL_FLOOR + self.fail_ema)
        e = (w * self.is_ext).sum()
        s = w.sum()
        # Scale the extremes down so that their share is at most EXTREME_CAP.
        k = torch.where(e / s > EXTREME_CAP, EXTREME_CAP * (s - e) / ((1.0 - EXTREME_CAP) * e).clamp(min=1e-12),
                        torch.ones_like(e))
        w = torch.where(self.is_ext, w * k, w)
        return w / w.sum()

    def sample(self, env_ids: torch.Tensor) -> torch.Tensor:
        """Families for env_ids; an env whose previous feed was extreme gets a neutral or moderate one."""
        w = self.weights()
        w_no = torch.where(self.is_ext, torch.zeros_like(w), w)
        W = torch.where(self.last_ext[env_ids].unsqueeze(-1), w_no.expand(len(env_ids), -1),
                        w.expand(len(env_ids), -1))
        fam = torch.multinomial(W, 1, replacement=True, generator=self.gen).squeeze(-1)
        self.last_ext[env_ids] = self.is_ext[fam]
        return fam

    def update(self, family: torch.Tensor, success: torch.Tensor, mask: torch.Tensor) -> None:
        """Finished feeds (mask) of each family update its EMA failure rate."""
        if not self.fail_weighting:
            return
        m = mask.float()
        n_f = torch.zeros_like(self.fail_ema).index_add_(0, family, m)
        f_f = torch.zeros_like(self.fail_ema).index_add_(0, family, (mask & ~success).float())
        a = (FAIL_EMA_RATE * n_f).clamp(max=0.5)
        self.fail_ema = torch.where(n_f > 0, self.fail_ema + a * (f_f / n_f.clamp(min=1) - self.fail_ema),
                                    self.fail_ema)
