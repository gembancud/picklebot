"""Prior quality of the latent controller (Stage 5B H2): roll out the prior alone, no reference.

Each env starts on a random clip frame (the tracking task's reset), then the controller acts with
z = mu_p + scale * sigma_p * eps, eps ~ N(0, 1) drawn every step: the prior's own random walk. The motion command
is frozen after the start (its observations are ignored by the prior and decoder), the reference-comparing
terminations and pushes are off, and episodes run their full length.

Reported:
- falls: the torso drops below 0.5 m or the body tilts more than 60 degrees, at any time;
- style score: median nearest-clip pose distance of the robot's poses (scripts/motion/style_score.py's measure and
  clip set, so it compares with S-D3b's 4.82 and the 0.94 human floor), over frames before any fall.
Optionally renders a few envs to a video.

Usage (picklebot-mj venv):
    python scripts/motion/prior_eval.py --checkpoint LATENT.pt [--envs 1000] [--seconds 10] [--scale 1.0]
        [--seed 4200400] [--json OUT] [--video OUT.mp4 --video-envs 1]
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import mjlab.tasks  # noqa: F401
import torch
from mjlab.envs import ManagerBasedRlEnv
from mjlab.rl import RslRlVecEnvWrapper
from mjlab.tasks.registry import load_env_cfg, load_rl_cfg

from picklebot_mj import seeds
from picklebot_mj.latent import LatentController
from picklebot_mj.style import KEY_BODIES, expert_transitions, robot_features

MOTION = Path(__file__).resolve().parents[2] / "artifacts" / "motion" / "tracking"
POSE = list(range(0, 29)) + list(range(65, 80))  # as style_score.py
FALL_Z, FALL_TILT = 0.5, math.radians(60)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--task", default="Picklebot-Tracking-TennisLafan2-Huge-G1")
    ap.add_argument("--envs", type=int, default=1000)
    ap.add_argument("--seconds", type=float, default=10.0)
    ap.add_argument("--scale", type=float, default=1.0)
    ap.add_argument("--seed", type=int, default=4200400)
    ap.add_argument("--json", default=None)
    ap.add_argument("--video", default=None)
    ap.add_argument("--every", type=int, default=5)
    args = ap.parse_args()
    assert args.seed in seeds.DEV_EVAL_SEEDS, "evaluation must use development seeds"

    cfg = load_env_cfg(args.task, play=False)
    for k in [k for k in cfg.terminations if k != "time_out"]:
        cfg.terminations.pop(k)
    cfg.events.pop("push_robot", None)
    cfg.observations["actor"].enable_corruption = False
    cfg.episode_length_s = args.seconds + 1.0
    cfg.scene.num_envs, cfg.seed = (2 if args.video else args.envs), args.seed
    if args.video:
        cfg.viewer.width, cfg.viewer.height = 960, 540
        cfg.viewer.distance, cfg.viewer.elevation, cfg.viewer.azimuth = 4.0, -8.0, 270.0
        cfg.viewer.max_extra_envs = 0
    env = ManagerBasedRlEnv(cfg=cfg, device="cuda", render_mode="rgb_array" if args.video else None)
    venv = RslRlVecEnvWrapper(env, clip_actions=load_rl_cfg(args.task).clip_actions)
    lat = LatentController().cuda()
    lat.load_state_dict(torch.load(args.checkpoint, map_location="cuda", weights_only=False)["model"])
    lat.eval()

    obs = venv.get_observations()
    cmd = env.command_manager.get_term("motion")
    cmd._update_command = lambda env_ids=None: None  # freeze the reference: no clip wraps or teleports
    robot = env.scene["robot"]
    keys = [list(robot.body_names).index(b) for b in KEY_BODIES]
    torso = list(robot.body_names).index("torso_link")
    n = env.num_envs
    fell = torch.zeros(n, dtype=torch.bool, device="cuda")
    poses, frames = [], []
    g = torch.Generator(device="cuda").manual_seed(args.seed)
    with torch.no_grad():
        for t in range(int(round(args.seconds / env.step_dt))):
            x = obs["actor"]
            eps = torch.randn(n, lat.latent, device="cuda", generator=g)
            obs, *_ = venv.step(lat.prior_action(x, eps=eps, scale=args.scale))
            d = robot.data
            up = d.projected_gravity_b[:, 2]  # -1 when upright
            tilt = torch.acos((-up).clamp(-1, 1))
            fell |= (d.body_link_pos_w[:, torso, 2] < FALL_Z) | (tilt > FALL_TILT)
            if t % args.every == 0:
                poses.append(robot_features(robot, keys)[~fell][:, POSE].clone())
            if args.video:
                frames.append(env.render())
    out = {"checkpoint": args.checkpoint, "seed": args.seed, "envs": n, "seconds": args.seconds, "scale": args.scale,
           "fall_rate": float(fell.float().mean())}
    if not args.video:
        ea, _ = expert_transitions([MOTION / "tennis-v5.npz", MOTION / "lafan-g1.npz"], list(robot.body_names), "cuda")
        pose = torch.tensor(POSE, device="cuda")
        mean, std = ea[:, pose].mean(0), ea[:, pose].std(0).clamp(min=1e-3)
        ref = ((ea[:, pose] - mean) / std)[torch.randperm(len(ea), device="cuda", generator=g)[:60_000]]
        xs = (torch.cat(poses) - mean) / std
        dist = torch.cat([torch.cdist(xs[i:i + 2048], ref).min(1).values for i in range(0, len(xs), 2048)])
        out.update(poses=len(xs), style_median=float(dist.median()), style_p90=float(dist.quantile(0.9)))
    print(json.dumps(out, indent=1))
    if args.json:
        json.dump(out, open(args.json, "w"), indent=1)
    if args.video:
        import imageio_ffmpeg
        import mediapy

        mediapy.set_ffmpeg(imageio_ffmpeg.get_ffmpeg_exe())
        mediapy.write_video(args.video, frames, fps=int(round(1 / env.step_dt)))
    env.close()


if __name__ == "__main__":
    main()
