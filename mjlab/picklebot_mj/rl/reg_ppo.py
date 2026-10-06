"""PPO for fine-tuning a distilled student without forgetting (D-042).

`RegPPO` is rsl_rl's PPO plus two things, configured through environment variables so the stock
`train` CLI can select it with `--agent.algorithm.class-name picklebot_mj.rl.reg_ppo:RegPPO`:

- **Pull-back regulariser.** A frozen copy of a reference policy (the distilled student, which already
  encodes both teachers) anchors the fine-tune: loss += coef * 0.5 * sum(((mu - mu_ref) / sigma_ref)^2),
  i.e. the KL between Gaussians with the reference std. The coefficient decays linearly to
  `final_coef` over `decay_iters` updates. (D-042 named a routed-teacher pull-back; anchoring to the
  student is equivalent in intent and needs no routing.)
- **Critic warm-up.** The distilled student's critic was never trained, so for the first
  `warmup_iters` PPO updates the actor is frozen (and its adaptive learning rate held) while the
  critic learns the returns.

Env vars: PICKLEBOT_REF_CKPT (required to enable), PICKLEBOT_REF_COEF (default 1.0),
PICKLEBOT_REF_FINAL_COEF (0.1), PICKLEBOT_REF_DECAY_ITERS (1000), PICKLEBOT_CRITIC_WARMUP_ITERS (50).
Implemented through rsl_rl's symmetry hook (augment_batch before the forward pass, compute_loss added
to the loss), so the PPO update itself is unchanged.
"""

from __future__ import annotations

import copy
import os

import torch
from rsl_rl.algorithms import PPO


class _RefRegulariser:
    use_mirror_loss = True

    def __init__(self, alg: "RegPPO", ref_actor, coef: float, final_coef: float, decay_iters: int, warmup: int):
        self.alg, self.ref = alg, ref_actor
        self.coef0, self.coef1, self.decay, self.warmup = coef, final_coef, max(1, decay_iters), warmup
        self.updates = 0  # PPO update() calls seen
        self.mirror_loss_coeff = coef
        self._lr_hold = None

    def start_update(self):
        self.updates += 1
        frac = min(1.0, max(0, self.updates - self.warmup) / self.decay)
        self.mirror_loss_coeff = self.coef0 + (self.coef1 - self.coef0) * frac
        frozen = self.updates <= self.warmup
        for p in self.alg.actor.parameters():
            p.requires_grad_(not frozen)
        self._lr_hold = self.alg.learning_rate if frozen else None

    # rsl_rl symmetry hook API --------------------------------------------------------
    def augment_batch(self, batch, original_batch_size):
        pass

    def compute_loss(self, actor, batch, original_batch_size):
        if self._lr_hold is not None:  # warm-up: keep the adaptive lr from drifting while the actor is frozen
            self.alg.learning_rate = self._lr_hold
            for g in self.alg.optimizer.param_groups:
                g["lr"] = self._lr_hold
        mu = actor.output_mean[:original_batch_size]
        with torch.no_grad():
            self.ref(batch.observations[:original_batch_size], stochastic_output=True)
            mu_ref, sd_ref = self.ref.output_mean, self.ref.output_std
        return (0.5 * ((mu - mu_ref) / sd_ref) ** 2).sum(-1).mean()


class RegPPO(PPO):
    def __init__(self, actor, critic, storage, *args, **kwargs):
        super().__init__(actor, critic, storage, *args, **kwargs)
        self.reg = None
        ck = os.environ.get("PICKLEBOT_REF_CKPT")
        if ck:
            ref = copy.deepcopy(actor)
            sd = torch.load(ck, map_location=self.device, weights_only=False)["actor_state_dict"]
            ref.load_state_dict(sd, strict=True)
            ref.eval()
            for p in ref.parameters():
                p.requires_grad_(False)
            self.reg = _RefRegulariser(
                self, ref,
                coef=float(os.environ.get("PICKLEBOT_REF_COEF", "1.0")),
                final_coef=float(os.environ.get("PICKLEBOT_REF_FINAL_COEF", "0.1")),
                decay_iters=int(os.environ.get("PICKLEBOT_REF_DECAY_ITERS", "1000")),
                warmup=int(os.environ.get("PICKLEBOT_CRITIC_WARMUP_ITERS", "50")),
            )
            self.symmetry = self.reg

    def update(self):
        if self.reg is not None:
            self.reg.start_update()
        out = super().update()
        if self.reg is not None:
            out["pullback"] = out.pop("symmetry", None)
            out["pullback_coef"] = self.reg.mirror_loss_coeff
        return out
