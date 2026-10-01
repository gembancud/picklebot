"""Evaluate a Picklebot-Return-Stand-G1 checkpoint on development seeds (deterministic policy).

Runs `--envs` parallel envs for `--seconds` of sim time (every finished episode counts) and
reports per-episode rates with Wilson 95% intervals: paddle contact, legal return,
robot falls, plus the rally-ending fault breakdown. Optionally records a video.

Usage:
  python scripts/stage2_eval.py --checkpoint PATH [--envs 512] [--seconds 9] [--seed 4200000]
  python scripts/stage2_eval.py --checkpoint PATH --envs 4 --seconds 9 --video out.mp4
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict

import torch

import mjlab.tasks  # noqa: F401
from mjlab.envs import ManagerBasedRlEnv
from mjlab.rl import MjlabOnPolicyRunner, RslRlVecEnvWrapper
from mjlab.tasks.registry import load_env_cfg, load_rl_cfg

from picklebot_mj import seeds
from picklebot_mj.rules import Fault
from picklebot_mj.tasks import TASK_RETURN_STAND


def wilson(k: int, n: int, z: float = 1.96):
    if n == 0:
        return [None, None]
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(c - h, 4), round(c + h, 4)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--envs", type=int, default=512)
    ap.add_argument("--seconds", type=float, default=9.0)
    ap.add_argument("--seed", type=int, default=seeds.DEV_EVAL_SEEDS[0])
    ap.add_argument("--video", default=None)
    ap.add_argument("--json", default=None)
    args = ap.parse_args()
    assert args.seed in seeds.DEV_EVAL_SEEDS, "evaluation must use development seeds"

    cfg = load_env_cfg(TASK_RETURN_STAND)
    cfg.scene.num_envs = args.envs
    cfg.seed = args.seed
    cfg.actions["ball"].seed = args.seed
    cfg.observations["actor"].enable_corruption = False
    if args.video:
        cfg.viewer.width, cfg.viewer.height = 960, 540
        cfg.viewer.distance, cfg.viewer.elevation, cfg.viewer.azimuth = 4.0, -10.0, 135.0
    env = ManagerBasedRlEnv(cfg=cfg, device="cuda", render_mode="rgb_array" if args.video else None)
    agent_cfg = load_rl_cfg(TASK_RETURN_STAND)
    venv = RslRlVecEnvWrapper(env, clip_actions=agent_cfg.clip_actions)
    runner = MjlabOnPolicyRunner(venv, asdict(agent_cfg), device="cuda")
    runner.load(args.checkpoint, load_cfg={"actor": True}, strict=True, map_location="cuda")
    policy = runner.get_inference_policy(device="cuda")

    term = env.action_manager.get_term("ball")
    term.fault_counts.zero_(); term.hit_count.zero_(); term.return_count.zero_()
    obs = venv.get_observations()
    episodes = falls = 0
    frames = []
    steps = int(round(args.seconds / env.step_dt))
    with torch.inference_mode():
        for _ in range(steps):
            obs, _, dones, _ = venv.step(policy(obs))
            done = dones.bool()
            episodes += int(done.sum())
            falls += int((env.termination_manager.get_term("fell_over") & done).sum())
            if args.video:
                frames.append(env.render())
    hits, rets = int(term.hit_count), int(term.return_count)
    endings = {Fault(i).name: int(c) for i, c in enumerate(term.fault_counts.tolist()) if c}
    out = {
        "checkpoint": args.checkpoint, "seed": args.seed, "envs": args.envs, "sim_seconds": args.seconds,
        "episodes": episodes,
        "contact_rate": round(hits / max(episodes, 1), 4), "contact_ci95": wilson(hits, episodes),
        "legal_return_rate": round(rets / max(episodes, 1), 4), "legal_return_ci95": wilson(rets, episodes),
        "fall_rate": round(falls / max(episodes, 1), 4), "fall_ci95": wilson(falls, episodes),
        "hits": hits, "legal_returns": rets, "falls": falls, "rally_endings": endings,
    }
    print(json.dumps(out, indent=1))
    if args.json:
        json.dump(out, open(args.json, "w"), indent=1)
    if args.video:
        import imageio_ffmpeg
        import mediapy
        mediapy.set_ffmpeg(imageio_ffmpeg.get_ffmpeg_exe())
        mediapy.write_video(args.video, frames, fps=int(round(1 / env.step_dt)))
        stem = args.video.rsplit(".", 1)[0]
        for i in range(0, len(frames), 25):
            mediapy.write_image(f"{stem}_{i:03d}.png", frames[i])
        print("video:", args.video, len(frames))


if __name__ == "__main__":
    main()
