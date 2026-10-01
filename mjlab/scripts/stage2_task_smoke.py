"""Smoke-check the Picklebot-Return-Stand-G1 task with zero actions (robot holds its stance).

Reports: env build, observation/action sizes, outcome counts by fault, robot falls,
and where the fed ball passes the robot (height/lateral offset at the robot's x).
"""

from __future__ import annotations

import argparse
import collections
import json

import torch

import mjlab.tasks  # noqa: F401  (registers built-ins; ours come via entry point)
from mjlab.envs import ManagerBasedRlEnv
from mjlab.tasks.registry import list_tasks, load_env_cfg

from picklebot_mj.rules import Fault
from picklebot_mj.tasks import TASK_RETURN_STAND
from picklebot_mj.tasks.return_stand import ROBOT_START


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--num-envs", type=int, default=64)
    ap.add_argument("--steps", type=int, default=400)
    args = ap.parse_args()
    assert TASK_RETURN_STAND in list_tasks(), list_tasks()
    cfg = load_env_cfg(TASK_RETURN_STAND)
    cfg.scene.num_envs = args.num_envs
    env = ManagerBasedRlEnv(cfg, device="cuda")
    obs, _ = env.reset()
    term = env.action_manager.get_term("ball")
    act = torch.zeros(args.num_envs, env.action_manager.total_action_dim, device="cuda")
    faults = collections.Counter()
    crossings = []
    prev_x = term.ball.pos[:, 0].clone()
    episodes = falls = 0
    for _ in range(args.steps):
        x_before = term.ball.pos.clone()
        obs, rew, terminated, truncated, info = env.step(act)
        # Ball passing the robot's x (court-local), measured on the step it crosses.
        cross = (x_before[:, 0] > ROBOT_START[0]) & (term.ball.pos[:, 0] <= ROBOT_START[0])
        for i in cross.nonzero().flatten().tolist():
            crossings.append((float(term.ball.pos[i, 2]), float(term.ball.pos[i, 1] - ROBOT_START[1])))
        done = (terminated | truncated).nonzero().flatten()
        episodes += len(done)
        fell = env.termination_manager.get_term("fell_over")[done] if len(done) else torch.zeros(0)
        falls += int(fell.sum()) if len(done) else 0
        # Faults of finished rallies are reset already; read from the termination log instead.
    # Final pass: classify via a fresh rollout of rule faults (fault codes are reset on reset).
    out = {
        "tasks_registered": TASK_RETURN_STAND in list_tasks(),
        "action_dim": env.action_manager.total_action_dim,
        "actor_obs_dim": int(obs["actor"].shape[-1]),
        "critic_obs_dim": int(obs["critic"].shape[-1]),
        "episodes_finished": episodes,
        "falls": falls,
        "ball_crossings": len(crossings),
        "rally_endings": {Fault(i).name: int(c) for i, c in enumerate(term.fault_counts.tolist()) if c},
        "hits": int(term.hit_count), "legal_returns": int(term.return_count),
    }
    if crossings:
        h = torch.tensor(crossings)
        out.update(cross_height_min=float(h[:, 0].min()), cross_height_mean=float(h[:, 0].mean()),
                   cross_height_max=float(h[:, 0].max()),
                   cross_lateral_min=float(h[:, 1].min()), cross_lateral_max=float(h[:, 1].max()))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
