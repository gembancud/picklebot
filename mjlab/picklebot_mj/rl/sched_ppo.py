"""PPO with a fixed learning-rate schedule, a KL guard and a std floor (the restart after the KL check, 2026-10-28).

rsl_rl's adaptive schedule held the rate at its 1e-5 floor from rally run 2 on: one action output's std collapsed to
about 0.002 and supplied 95-99 % of the summed KL (results/selfplay.md, "KL check"). `ScheduledPPO` replaces the
adaptive rule; select it with `--agent.algorithm.class-name picklebot_mj.rl.sched_ppo:ScheduledPPO`.

- **Schedule** (warmup-stable-decay): linear warm-up 0 -> PICKLEBOT_LR_PEAK over PICKLEBOT_LR_WARMUP updates, then
  constant; if PICKLEBOT_LR_TOTAL > 0, a 1 - sqrt cooldown to PICKLEBOT_LR_FINAL over the last PICKLEBOT_LR_COOLDOWN
  fraction of the run's updates.
- **KL guard:** once a mini-batch's KL against the rollout policy exceeds PICKLEBOT_KL_GUARD, the remaining
  mini-batches of that update take no step (rate 0).
- **Std floor:** the actor's std parameter is clamped at PICKLEBOT_STD_MIN after every optimizer step. (The first
  version used rsl_rl's forward `std_range` clamp, which passes zero gradient at the floor: an output that reached it
  could never rise again. Audit 2026-10-28, docs/research/audit-2026-10-28-training-loop.md C1. The LR sweep and run
  18's smoke ran with that version; output 30 sat frozen at 0.1 in them.)
- **Log:** one JSON line per update to PICKLEBOT_SCHED_LOG (rate, KL, guard trips, the largest per-output KL shares,
  the smallest std and how many outputs sit at the floor).

The adaptive branch still computes the KL (the guard needs it); it is handed `desired_kl`, which leaves the rate alone.
"""

from __future__ import annotations

import json
import math
import os

import torch
from rsl_rl.algorithms import PPO


class ScheduledPPO(PPO):
    def __init__(self, actor, critic, storage, *args, **kwargs):
        super().__init__(actor, critic, storage, *args, **kwargs)
        env = os.environ.get
        self.peak = float(env("PICKLEBOT_LR_PEAK"))
        self.warmup = int(env("PICKLEBOT_LR_WARMUP", "50"))
        self.total = int(env("PICKLEBOT_LR_TOTAL", "0"))
        self.cool = float(env("PICKLEBOT_LR_COOLDOWN", "0.2"))
        self.final = float(env("PICKLEBOT_LR_FINAL", "1e-5"))
        self.guard = float(env("PICKLEBOT_KL_GUARD", "0.05"))
        self.log = env("PICKLEBOT_SCHED_LOG")
        self.floor = float(env("PICKLEBOT_STD_MIN", "0.1"))
        dist = self._raw_actor.distribution
        step = self.optimizer.step

        def floored_step(*a, **k):
            out = step(*a, **k)
            with torch.no_grad():
                if dist.std_type == "scalar":
                    dist.std_param.clamp_(min=self.floor)
                else:
                    dist.log_std_param.clamp_(min=math.log(self.floor))
            return out

        self.optimizer.step = floored_step
        floored_step.__wrapped__ = step
        with torch.no_grad():  # the parent may sit below the floor
            if dist.std_type == "scalar":
                dist.std_param.clamp_(min=self.floor)
            else:
                dist.log_std_param.clamp_(min=math.log(self.floor))
        self.schedule, self.updates, self._rows, self._lr, self._tripped = "adaptive", 0, [], 0.0, False
        inner = self.actor.get_kl_divergence

        def guarded(old, new):
            kl = inner(old, new)
            (m0, s0), (m1, s1) = old, new
            per = torch.distributions.kl_divergence(torch.distributions.Normal(m0, s0), torch.distributions.Normal(m1, s1)).mean(0)
            km = float(kl.mean())
            self._rows.append((km, per.float().cpu(), not self._tripped and km <= self.guard))
            if km > self.guard:
                self._tripped = True
            self.learning_rate = 0.0 if self._tripped else self._lr
            return torch.full_like(kl, self.desired_kl)

        self.actor.get_kl_divergence = guarded

    def rate(self, u: int) -> float:
        lr = self.peak * min(1.0, u / max(1, self.warmup))
        if self.total > 0:
            start = self.total * (1.0 - self.cool)
            if u > start:
                frac = min(1.0, (u - start) / max(1.0, self.total - start))
                lr = self.final + (self.peak - self.final) * (1.0 - math.sqrt(frac))
        return lr

    def update(self):
        self.updates += 1
        self._lr, self._tripped, self._rows = self.rate(self.updates), False, []
        self.learning_rate = self._lr
        for g in self.optimizer.param_groups:
            g["lr"] = self._lr
        out = super().update()
        if self.log and self._rows:
            per = torch.stack([r[1] for r in self._rows]).mean(0)
            share = per / per.sum().clamp_min(1e-12)
            top = torch.argsort(share, descending=True)[:3].tolist()
            row = {"update": self.updates, "lr": self._lr, "kl_mean": sum(r[0] for r in self._rows) / len(self._rows),
                   "kl_max": max(r[0] for r in self._rows), "guard_tripped": self._tripped,
                   "steps_taken": sum(1 for r in self._rows if r[2]),
                   "top_share": {str(i): round(float(share[i]), 4) for i in top},
                   "std_min": float(self._raw_actor.output_std[0].min()),
                   "at_floor": int((self._raw_actor.output_std[0] <= self.floor * 1.001).sum())}
            with open(self.log, "a") as f:
                f.write(json.dumps(row) + "\n")
        self.learning_rate = self._lr
        return out
