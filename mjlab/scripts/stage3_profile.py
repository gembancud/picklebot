"""Stage 3: profile the env step of Picklebot-Return-Stand-G1 (where does collection time go?).

Wraps the ball action term, the MuJoCo physics step and the whole env.step with
CUDA-synchronised timers, runs random actions, and reports per-env-step milliseconds
and env steps/s. Synchronising adds a little overhead; it is the same for all parts.
Usage: python scripts/stage3_profile.py [--envs 4096] [--steps 60]
"""

from __future__ import annotations

import argparse
import json
import time
from collections import defaultdict

import torch

import mjlab.tasks  # noqa: F401
from mjlab.envs import ManagerBasedRlEnv
from mjlab.tasks.registry import load_env_cfg

from picklebot_mj.tasks import TASK_RETURN_STAND

T = defaultdict(float)


def timed(name, fn):
    def wrapper(*a, **k):
        torch.cuda.synchronize()
        t0 = time.perf_counter()
        r = fn(*a, **k)
        torch.cuda.synchronize()
        T[name] += time.perf_counter() - t0
        return r
    return wrapper


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--envs", type=int, default=4096)
    ap.add_argument("--steps", type=int, default=60)
    ap.add_argument("--json", default=None)
    args = ap.parse_args()
    cfg = load_env_cfg(TASK_RETURN_STAND)
    cfg.scene.num_envs = args.envs
    env = ManagerBasedRlEnv(cfg, device="cuda")
    env.reset()
    term = env.action_manager.get_term("ball")
    term.apply_actions = timed("ball_term", term.apply_actions)
    env.sim.step = timed("mujoco_step", env.sim.step)
    env.sim.forward = timed("mujoco_forward", env.sim.forward)
    act_dim = env.action_manager.total_action_dim
    for _ in range(10):  # warm-up
        env.step(torch.rand(args.envs, act_dim, device="cuda") * 2 - 1)
    T.clear()
    torch.cuda.synchronize()
    t0 = time.perf_counter()
    for _ in range(args.steps):
        env.step(torch.rand(args.envs, act_dim, device="cuda") * 2 - 1)
    torch.cuda.synchronize()
    total = time.perf_counter() - t0
    per = lambda s: round(1000 * s / args.steps, 2)
    other = total - T["ball_term"] - T["mujoco_step"] - T["mujoco_forward"]
    out = {
        "envs": args.envs, "env_steps": args.steps, "decimation": cfg.decimation,
        "ms_per_env_step": {"total": per(total), "ball_term": per(T["ball_term"]),
                            "mujoco_step": per(T["mujoco_step"]), "mujoco_forward": per(T["mujoco_forward"]),
                            "other_managers": per(other)},
        "share": {k: round(v / total, 3) for k, v in
                  (("ball_term", T["ball_term"]), ("mujoco_step", T["mujoco_step"]),
                   ("mujoco_forward", T["mujoco_forward"]), ("other_managers", other))},
        "env_steps_per_s": round(args.envs * args.steps / total),
    }
    print(json.dumps(out, indent=1))
    if args.json:
        json.dump(out, open(args.json, "w"), indent=1)


if __name__ == "__main__":
    main()
