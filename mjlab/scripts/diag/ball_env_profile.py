"""D-124 tooling (iv): where the E5 ball environment spends its step time. Builds the task at N envs, runs the E3
policy, and times env steps (CUDA-synchronised) as is, without the timed-goal planner, and without the ball term's own
stance planner (whose spot the timed controller does not use). Timing only; no metric is read (training seed).

Usage: python scripts/diag/ball_env_profile.py --checkpoint PATH [--envs 4096] [--steps 40]
"""

import argparse
import time
from dataclasses import asdict

import mjlab.tasks  # noqa: F401
import torch
from mjlab.envs import ManagerBasedRlEnv
from mjlab.rl import MjlabOnPolicyRunner, RslRlVecEnvWrapper
from mjlab.tasks.registry import load_env_cfg, load_rl_cfg

import picklebot_mj.tasks.return_stand as rs
import picklebot_mj.tasks.timed_reach as tr

ap = argparse.ArgumentParser()
ap.add_argument("--checkpoint", required=True)
ap.add_argument("--task", default="Picklebot-Latent-TimedBall-PPO-G1")
ap.add_argument("--envs", type=int, default=4096)
ap.add_argument("--steps", type=int, default=40)
a = ap.parse_args()
cfg = load_env_cfg(a.task)
cfg.scene.num_envs, cfg.seed = a.envs, 75
env = ManagerBasedRlEnv(cfg=cfg, device="cuda")
agent = load_rl_cfg(a.task)
venv = RslRlVecEnvWrapper(env, clip_actions=agent.clip_actions)
runner = MjlabOnPolicyRunner(venv, asdict(agent), device="cuda")
runner.load(a.checkpoint, load_cfg={"actor": True}, strict=True, map_location="cuda")
policy = runner.get_inference_policy(device="cuda")
env.reset()
obs = venv.get_observations()


def timed(label, n):
    global obs
    with torch.no_grad():
        for _ in range(10):
            obs, *_ = venv.step(policy(obs))
        torch.cuda.synchronize()
        t0 = time.perf_counter()
        for _ in range(n):
            obs, *_ = venv.step(policy(obs))
        torch.cuda.synchronize()
    dt = (time.perf_counter() - t0) / n
    print(f"{label}: {dt * 1000:.1f} ms per env step ({dt * 24:.2f} s per 24-step rollout)", flush=True)


timed("as is", a.steps)
orig_cmd = tr.TimedBallCommand._update_command
orig_plan = rs.BallPhysicsAction._plan_step


def no_goal_plan(self, env_ids):
    b = self._env.action_manager.get_term("ball")
    self._prev_pending = b.plan_pending.clone()


tr.TimedBallCommand._update_command = no_goal_plan
timed("without the timed-goal planner", a.steps)
tr.TimedBallCommand._update_command = orig_cmd
rs.BallPhysicsAction._plan_step = lambda self, dt, live: None
timed("without the ball term's stance planner", a.steps)
tr.TimedBallCommand._update_command = no_goal_plan
timed("without both", a.steps)
