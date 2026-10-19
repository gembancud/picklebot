"""Joint-position action with a per-episode command delay (Stage 5F H0 delay fine-tune, D-108/D-109/D-111).

At each reset an env draws its command lag for the episode:
- 0 with probability p_zero (clean episodes keep the no-delay skill);
- otherwise uniform in 1..max_lag physics steps (5 ms each; the default 5 steps = 25 ms reaches past the 20 ms the
  evaluation uses).

Every physics step the joint targets applied are the command of `lag` physics steps ago (a per-env history), the
same mechanism as the latent action term's run-4 command delay. The policy is not told the lag. The critic may read
it through `cmd_lag_obs` (asymmetric actor-critic: the actor has to cope, and the value is still well estimated).
"""

from __future__ import annotations

from dataclasses import dataclass

import torch
from mjlab.envs.mdp.actions.actions import JointPositionAction, JointPositionActionCfg


@dataclass(kw_only=True)
class DelayedJointPositionActionCfg(JointPositionActionCfg):
    p_zero: float = 0.3
    max_lag: int = 5
    seed: int = 0

    def build(self, env):
        return DelayedJointPositionAction(self, env)


class DelayedJointPositionAction(JointPositionAction):
    cfg: DelayedJointPositionActionCfg

    def __init__(self, cfg, env):
        super().__init__(cfg, env)
        n = self.num_envs
        self.gen_lag = torch.Generator(device=self.device).manual_seed(int(cfg.seed) + 424243)
        self.cmd_lag = torch.zeros(n, dtype=torch.long, device=self.device)
        self._hist = None
        self._fresh = torch.ones(n, dtype=torch.bool, device=self.device)
        self._ar = torch.arange(n, device=self.device)

    def reset(self, env_ids=None):
        super().reset(env_ids)
        if env_ids is None or isinstance(env_ids, slice):
            env_ids = self._ar
        k = len(env_ids)
        if k == 0:
            return
        lag = torch.randint(1, int(self.cfg.max_lag) + 1, (k,), generator=self.gen_lag, device=self.device)
        zero = torch.rand(k, generator=self.gen_lag, device=self.device) < self.cfg.p_zero
        self.cmd_lag[env_ids] = torch.where(zero, torch.zeros_like(lag), lag)
        self._fresh[env_ids] = True

    def apply_actions(self) -> None:
        cur = self._processed_actions
        if self._hist is None:
            self._hist = cur.unsqueeze(0).repeat(int(self.cfg.max_lag) + 1, 1, 1)
        hist = torch.where(self._fresh.view(1, -1, 1), cur.unsqueeze(0), self._hist)  # no command from before a reset
        self._fresh = torch.zeros_like(self._fresh)
        self._hist = torch.cat([cur.unsqueeze(0), hist[:-1]], 0)
        self._processed_actions = self._hist[self.cmd_lag, self._ar]
        try:
            super().apply_actions()
        finally:
            self._processed_actions = cur


def cmd_lag_obs(env, action_name: str = "joint_pos") -> torch.Tensor:
    """The episode's command lag as a fraction of max_lag (critic only)."""
    t = env.action_manager.get_term(action_name)
    return (t.cmd_lag.float() / float(t.cfg.max_lag)).unsqueeze(-1)
