"""Check: how many evaluated feeds are cut off by the robot-episode time-out (still in flight, untouched)?

Wraps BallPhysicsAction.reset to count, at each episode reset, feeds that were neither finished
(not tallied) nor hit nor ended by a fall. Those are censored by the time limit, not missed.
"""
import sys
from dataclasses import asdict

import torch

import mjlab.tasks  # noqa
from mjlab.envs import ManagerBasedRlEnv
from mjlab.rl import MjlabOnPolicyRunner, RslRlVecEnvWrapper
from mjlab.tasks.registry import load_env_cfg, load_rl_cfg

from picklebot_mj.feeds import FeedMix, STAGE4_FAMILIES
from picklebot_mj.tasks.return_stand import BallPhysicsAction

task, ck, seed = sys.argv[1], sys.argv[2], int(sys.argv[3])
cfg = load_env_cfg(task)
cfg.scene.num_envs = 1024
cfg.seed = seed
cfg.actions["ball"].seed = seed
cfg.actions["ball"].feed_mix = FeedMix({f: 1.0 for f in STAGE4_FAMILIES})
cfg.actions["ball"].target_mode = "A"
cfg.observations["actor"].enable_corruption = False
if hasattr(cfg.actions["ball"], "move_prob"):
    cfg.actions["ball"].move_prob = 0.0
env = ManagerBasedRlEnv(cfg=cfg, device="cuda")
agent = load_rl_cfg(task)
venv = RslRlVecEnvWrapper(env, clip_actions=agent.clip_actions)
runner = MjlabOnPolicyRunner(venv, asdict(agent), device="cuda")
runner.load(ck, load_cfg={"actor": True}, strict=True, map_location="cuda")
policy = runner.get_inference_policy(device="cuda")
term = env.action_manager.get_term("ball")
cens = torch.zeros((), dtype=torch.long, device="cuda")
orig = BallPhysicsAction.reset


def reset(self, env_ids=None):
    global cens
    if env_ids is not None and not isinstance(env_ids, slice) and self._env.common_step_counter > 0:
        fell = self._env.termination_manager.get_term("fell_over")[env_ids]
        open_ = ~self.tallied[env_ids] & ~self.hit_done[env_ids] & ~fell
        cens = cens + open_.sum()
    return orig(self, env_ids)


BallPhysicsAction.reset = reset
for v in term.ep.values():
    v.zero_()
obs = venv.get_observations()
with torch.inference_mode():
    for _ in range(int(16.0 / env.step_dt)):
        obs, _, _, _ = venv.step(policy(obs))
n, c, r = int(term.ep["episodes"]), int(term.ep["contact"]), int(term.ep["legal_return"])
k = int(cens)
print({"task": task, "feeds": n, "contact": round(c / n, 4), "legal": round(r / n, 4), "censored_untouched": k,
       "censored_frac": round(k / n, 4),
       "contact_excl_censored": round(c / (n - k), 4), "legal_excl_censored": round(r / (n - k), 4)})
