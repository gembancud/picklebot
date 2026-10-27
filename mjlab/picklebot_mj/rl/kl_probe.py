"""PPO that records the KL per action output (diagnostic only; 2026-10-27 KL check).

rsl_rl's adaptive schedule compares the KL summed over all outputs with `desired_kl`. `KLProbePPO` records each
output's share of that KL (and its mean-shift and std-change parts) on every mini-batch, and writes one JSON line per
PPO update to PICKLEBOT_KL_PROBE_OUT. Select it with `--agent.algorithm.class-name picklebot_mj.rl.kl_probe:KLProbePPO`.

PICKLEBOT_KL_FIXED_LR=<lr> holds the learning rate at <lr> while still measuring the real KL: the schedule is handed
a KL equal to `desired_kl`, which leaves the rate unchanged.
"""

from __future__ import annotations

import json
import os

import torch
from rsl_rl.algorithms import PPO


class KLProbePPO(PPO):
    def __init__(self, actor, critic, storage, *args, **kwargs):
        super().__init__(actor, critic, storage, *args, **kwargs)
        self._out = os.environ["PICKLEBOT_KL_PROBE_OUT"]
        fixed = os.environ.get("PICKLEBOT_KL_FIXED_LR")
        self._fixed = float(fixed) if fixed else None
        self._rows, self._updates = [], 0
        inner = self.actor.get_kl_divergence

        def probe(old, new):
            kl = inner(old, new)
            (m0, s0), (m1, s1) = old, new
            mean_part = ((m0 - m1) ** 2 / (2 * s1**2)).mean(0)
            std_part = (torch.log(s1 / s0) + s0**2 / (2 * s1**2) - 0.5).mean(0)
            self._rows.append((mean_part.float().cpu(), std_part.float().cpu(), float(kl.mean()), self.learning_rate))
            return torch.full_like(kl, self.desired_kl) if self._fixed is not None else kl

        self.actor.get_kl_divergence = probe

    def update(self):
        if self._fixed is not None:  # set here, not in __init__: a resume loads the optimizer (and its lr) afterwards
            self.learning_rate = self._fixed
            for g in self.optimizer.param_groups:
                g["lr"] = self._fixed
        out = super().update()
        self._updates += 1
        mean_part = torch.stack([r[0] for r in self._rows]).mean(0)
        std_part = torch.stack([r[1] for r in self._rows]).mean(0)
        row = {
            "update": self._updates,
            "kl_mean": sum(r[2] for r in self._rows) / len(self._rows),
            "lr_first": self._rows[0][3], "lr_last": self.learning_rate,
            "kl_mean_part": mean_part.tolist(), "kl_std_part": std_part.tolist(),
            "std": self.actor.output_std[0].detach().float().cpu().tolist(),
        }
        with open(self._out, "a") as f:
            f.write(json.dumps(row) + "\n")
        self._rows = []
        return out
