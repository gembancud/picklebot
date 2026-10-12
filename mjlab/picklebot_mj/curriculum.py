"""Adaptive curriculum sampler (automatic curriculum learning; D-044, user request 2026-10-06).

Chooses which *unit* (feed family, move sector, later each command) to practise next from how the
learner is doing on each, in the spirit of learning-progress and prioritized-replay curricula
(Matiisen et al. 2017 Teacher-Student CL; Portelas et al. 2019 ALP-GMM, 2020 survey; Jiang et al.
2021 Prioritized Level Replay):

    score_k  = (1 - success_k) + LP_WEIGHT * |fast_k - slow_k|   (unmastered + still changing)
    weight_k = floor / K  +  (1 - floor) * score_k / sum(score)  over the active units

`success_k` is an exponential moving average of per-unit outcomes; the absolute learning progress
is the gap between a fast and a slow average. The floor keeps every active unit at >= floor/K of
the uniform share, so mastered skills are still rehearsed. Units with zero base weight are never
sampled. Updates are batched masked tensor ops (no host syncs). Evaluation never uses this sampler.
"""

from __future__ import annotations

import torch

LP_WEIGHT = 2.0


class AdaptiveSampler:
    def __init__(self, base_weights, floor: float = 0.25, fast: float = 0.05, slow: float = 0.01,
                 device="cpu"):
        b = torch.as_tensor(base_weights, dtype=torch.float32, device=device)
        self.active = b > 0
        self.k = int(self.active.sum())
        assert self.k > 0
        self.floor, self.fast_rate, self.slow_rate = float(floor), float(fast), float(slow)
        self.fast = torch.full_like(b, 0.5)
        self.slow = torch.full_like(b, 0.5)
        self.seen = torch.zeros_like(b)

    def update(self, unit: torch.Tensor, success: torch.Tensor, mask: torch.Tensor | None = None) -> None:
        """Fold in a batch of outcomes: unit[i] (long) succeeded or not (bool), for rows in mask."""
        m = torch.ones_like(success, dtype=torch.bool) if mask is None else mask
        n = torch.zeros_like(self.fast).index_add_(0, unit, m.float())
        s = torch.zeros_like(self.fast).index_add_(0, unit, (success & m).float())
        has = n > 0
        mean = s / n.clamp(min=1.0)
        # Weight the EMA step by how many outcomes arrived (capped), so busy units adapt faster.
        a_f = (self.fast_rate * n).clamp(max=0.5)
        a_s = (self.slow_rate * n).clamp(max=0.5)
        self.fast = torch.where(has, self.fast + a_f * (mean - self.fast), self.fast)
        self.slow = torch.where(has, self.slow + a_s * (mean - self.slow), self.slow)
        self.seen = self.seen + n

    def weights(self) -> torch.Tensor:
        score = (1.0 - self.fast) + LP_WEIGHT * (self.fast - self.slow).abs()
        score = torch.where(self.active, score.clamp(min=1e-6), torch.zeros_like(score))
        p = score / score.sum()
        w = torch.where(self.active, self.floor / self.k + (1.0 - self.floor) * p, torch.zeros_like(p))
        return w / w.sum()


class LPSampler:
    """Learning-progress sampler over (family x difficulty level) units (H4, D-066).

    Unlike AdaptiveSampler, whose (1 - success) term keeps feeding units that never succeed (backhand got 12 % of
    feeds and 0 contacts), this prioritises units that are *learnable now*: absolute learning progress plus a
    bonus for intermediate success (goals of intermediate difficulty, Florensa et al. 2018; ALP, Portelas et al.
    2019), with a floor so every active unit, full-range levels included, keeps being rehearsed:

        score_k  = LP_WEIGHT * |fast_k - slow_k| + (1 if BAND[0] < fast_k < BAND[1] else OUT_OF_BAND)
        weight_k = floor / K + (1 - floor) * score_k / sum(score)
    """

    BAND = (0.1, 0.9)
    OUT_OF_BAND = 0.2

    def __init__(self, base_weights, floor: float = 0.2, fast: float = 0.05, slow: float = 0.01, device="cpu"):
        self.inner = AdaptiveSampler(base_weights, floor=floor, fast=fast, slow=slow, device=device)

    @property
    def active(self):
        return self.inner.active

    @property
    def fast(self):
        return self.inner.fast

    def update(self, unit, success, mask=None) -> None:
        self.inner.update(unit, success, mask)

    def weights(self) -> torch.Tensor:
        s = self.inner
        inside = (s.fast > self.BAND[0]) & (s.fast < self.BAND[1])
        score = LP_WEIGHT * (s.fast - s.slow).abs() + torch.where(inside, torch.ones_like(s.fast),
                                                                   torch.full_like(s.fast, self.OUT_OF_BAND))
        score = torch.where(s.active, score, torch.zeros_like(score))
        p = score / score.sum()
        w = torch.where(s.active, s.floor / s.k + (1.0 - s.floor) * p, torch.zeros_like(p))
        return w / w.sum()
