"""H3 gate evaluation: share of paddle and root targets reached (within 10 cm in their 2 s window) and falls.

Usage (picklebot-mj venv): python scripts/motion/reach_eval.py --checkpoint PATH [--envs 1024] [--seconds 10]
    [--seed 4200410] [--json OUT]
"""

import argparse
import json
from dataclasses import asdict

import mjlab.tasks  # noqa: F401
import torch
from mjlab.envs import ManagerBasedRlEnv
from mjlab.rl import MjlabOnPolicyRunner, RslRlVecEnvWrapper
from mjlab.tasks.registry import load_env_cfg, load_rl_cfg

from picklebot_mj import seeds

TASK = "Picklebot-Latent-Reach-G1"  # the reach task (any variant: same env; rewards differ only)

ap = argparse.ArgumentParser()
ap.add_argument("--checkpoint", required=True)
ap.add_argument("--task", default=TASK, help="reach task variant (its lambda must match the trained policy)")
ap.add_argument("--envs", type=int, default=1024)
ap.add_argument("--seconds", type=float, default=10.0)
ap.add_argument("--seed", type=int, default=4200410)
ap.add_argument("--json", default=None)
a = ap.parse_args()
assert a.seed in seeds.DEV_EVAL_SEEDS, "evaluation must use development seeds"
cfg = load_env_cfg(a.task)
cfg.scene.num_envs, cfg.seed = a.envs, a.seed
env = ManagerBasedRlEnv(cfg=cfg, device="cuda")
agent = load_rl_cfg(a.task)
venv = RslRlVecEnvWrapper(env, clip_actions=agent.clip_actions)
runner = MjlabOnPolicyRunner(venv, asdict(agent), device="cuda")
runner.load(a.checkpoint, load_cfg={"actor": True}, strict=True, map_location="cuda")
policy = runner.get_inference_policy(device="cuda")
cmd = env.command_manager.get_term("reach")
# Without this reset the first episode starts without the reset events applied, and over
# half fall in the first 3 s; found 2026-10-11 (artifacts/eval/reach-fall-diag.json).
env.reset()
# The reset also closes the construction-time command window (measured at the uninitialised spawn, always a miss):
# start counting from here.
cmd.tally = {k: 0 for k in cmd.tally}
obs = venv.get_observations()
episodes = falls = 0
with torch.no_grad():
    for _ in range(int(round(a.seconds / env.step_dt))):
        obs, _, dones, _ = venv.step(policy(obs))
        d = dones.bool()
        episodes += int(d.sum())
        falls += int((d & env.termination_manager.terminated).sum())
episodes += env.num_envs  # episodes still running at the end
t = cmd.tally
out = {"checkpoint": a.checkpoint, "seed": a.seed, "windows": t["windows"],
       "paddle_reached": t["paddle_reached"] / max(1, t["windows"]),
       "root_reached": t["root_reached"] / max(1, t["windows"]),
       "paddle_reached_25cm": t["paddle_reached_25"] / max(1, t["windows"]),
       "root_reached_25cm": t["root_reached_25"] / max(1, t["windows"]), "episodes": episodes,
       "fall_rate": falls / max(1, episodes)}
print(json.dumps(out, indent=1))
if a.json:
    json.dump(out, open(a.json, "w"), indent=1)
env.close()
