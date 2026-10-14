"""Can the H3 reach policy (and so the latent controller) step in every direction? (Stage 5B H4 diagnostic, D-063)

Runs the H3 reach task with the root target forced, at every resample, to a fixed offset in the robot's heading frame
(left, right, forward, back; --dist m). The paddle target is resampled as usual. Reports, per direction, the share of
2 s windows in which the pelvis came within 10 / 25 cm of its target, the median closest approach, and falls.

Usage (picklebot-mj venv):
    python scripts/reach_direction_diag.py [--checkpoint reach-06/model_34700] [--dist 0.8] [--seed 4200470] [--json OUT]
"""

from __future__ import annotations

import argparse
import copy
import json
import math
from dataclasses import asdict

import torch

import mjlab.tasks  # noqa: F401
from mjlab.envs import ManagerBasedRlEnv
from mjlab.rl import MjlabOnPolicyRunner, RslRlVecEnvWrapper
from mjlab.tasks.registry import load_env_cfg, load_rl_cfg

from picklebot_mj import seeds
from picklebot_mj.tasks.latent_reach import _yaw_frame

TASK = "Picklebot-Latent-Reach-E2-G1"
CK = "artifacts/train/logs/picklebot_latent/2026-10-11_18-56-24_reach-06-more/model_34700.pt"
DIRS = {"left": (0.0, 1.0), "right": (0.0, -1.0), "forward": (1.0, 0.0), "back": (-1.0, 0.0)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", default=CK)
    ap.add_argument("--task", default=TASK, help="reach task (its latent controller is the one measured)")
    ap.add_argument("--dist", type=float, default=0.8)
    ap.add_argument("--envs", type=int, default=512)
    ap.add_argument("--seconds", type=float, default=10.0)
    ap.add_argument("--seed", type=int, default=4200470)
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    assert a.seed in seeds.DEV_EVAL_SEEDS, "evaluation must use development seeds"
    out = {"checkpoint": a.checkpoint, "dist_m": a.dist, "seed": a.seed}
    for name, (fx, fy) in DIRS.items():
        cfg = load_env_cfg(a.task)
        cfg.scene.num_envs, cfg.seed = a.envs, a.seed
        env = ManagerBasedRlEnv(cfg=cfg, device="cuda")
        venv = RslRlVecEnvWrapper(env, clip_actions=load_rl_cfg(a.task).clip_actions)
        runner = MjlabOnPolicyRunner(venv, copy.deepcopy(asdict(load_rl_cfg(a.task))), device="cuda")
        runner.load(a.checkpoint, load_cfg={"actor": True}, strict=True, map_location="cuda")
        policy = runner.get_inference_policy(device="cuda")
        cmd = env.command_manager.get_term("reach")
        orig = cmd._resample_command

        def forced(env_ids, orig=orig, cmd=cmd, fx=fx, fy=fy):
            orig(env_ids)
            d = cmd.robot.data
            c, s = _yaw_frame(d.root_link_quat_w[env_ids])
            off = torch.stack([c * fx - s * fy, s * fx + c * fy], -1) * a.dist
            cmd.root_target[env_ids] = d.root_link_pos_w[env_ids, :2] + off

        cmd._resample_command = forced
        env.reset()
        cmd.tally = {k: 0 for k in cmd.tally}
        obs = venv.get_observations()
        closest, falls, episodes = [], 0, 0
        with torch.no_grad():
            for _ in range(int(round(a.seconds / env.step_dt))):
                before = cmd.min_root.clone()
                obs, _, dones, _ = venv.step(policy(obs))
                reset = cmd.min_root > before + 1e-6  # window closed (min reset to 1e9)
                closest.append(before[reset & (before < 1e8)])
                d = dones.bool()
                episodes += int(d.sum())
                falls += int((d & env.termination_manager.terminated).sum())
        c = torch.cat(closest)
        t = cmd.tally
        out[name] = {"windows": t["windows"], "root_within_10cm": t["root_reached"] / max(1, t["windows"]),
                     "root_within_25cm": t["root_reached_25"] / max(1, t["windows"]),
                     "closest_median_m": float(c.median()) if len(c) else None,
                     "falls_per_episode": falls / max(1, episodes + a.envs)}
        print(name, json.dumps({k: (round(v, 3) if isinstance(v, float) else v) for k, v in out[name].items()}),
              flush=True)
        env.close()
    if a.json:
        json.dump(out, open(a.json, "w"), indent=1)


if __name__ == "__main__":
    main()
