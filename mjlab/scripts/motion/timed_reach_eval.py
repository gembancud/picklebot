"""Stage 5G E1 gate evaluation (D-118): timed reach. Paddle error at t* (median, p90), relative paddle-speed error,
timing of the closest approach (share within 50 ms), root within 0.25 m at t*, falls per episode.

Usage (picklebot-mj venv): python scripts/motion/timed_reach_eval.py --checkpoint PATH [--envs 1024] [--seconds 10]
    [--seed 4216010] [--json OUT]
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

TASK = "Picklebot-Latent-TimedReach-G1"

ap = argparse.ArgumentParser()
ap.add_argument("--checkpoint", required=True)
ap.add_argument("--task", default=TASK, help="reach task variant (its lambda must match the trained policy)")
ap.add_argument("--envs", type=int, default=1024)
ap.add_argument("--seconds", type=float, default=10.0)
ap.add_argument("--seed", type=int, default=4216010)
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
for v in cmd.stats.values():
    v.zero_()
cmd.counts.zero_()
for name in ("counts_w", "root_by_speed"):  # D-122 counters
    getattr(cmd, name).zero_()
obs = venv.get_observations()
episodes = falls = 0
with torch.no_grad():
    for _ in range(int(round(a.seconds / env.step_dt))):
        obs, _, dones, _ = venv.step(policy(obs))
        d = dones.bool()
        episodes += int(d.sum())
        falls += int((d & env.termination_manager.terminated).sum())
episodes += env.num_envs  # episodes still running at the end
out = {"checkpoint": a.checkpoint, "task": a.task, "seed": a.seed, **cmd.summary(), "episodes": episodes,
       "fall_rate": falls / max(1, episodes)}
print(json.dumps(out, indent=1))
if a.json:
    json.dump(out, open(a.json, "w"), indent=1)
env.close()
