"""Stage 1 integration run: GPU-batched driven-paddle rig with the analytic ball.

Usage (WSL):
  python scripts/stage1_rig.py --num-envs 4096 --steps 600          # outcomes + throughput
  python scripts/stage1_rig.py --num-envs 4 --steps 150 --video out.mp4
"""

from __future__ import annotations

import argparse
import json
import time

import torch

from picklebot_mj.rig_env import PickleballRigEnv, rig_env_cfg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--num-envs", type=int, default=4096)
    ap.add_argument("--steps", type=int, default=600)
    ap.add_argument("--video", type=str, default=None)
    ap.add_argument("--json", type=str, default=None)
    args = ap.parse_args()

    cfg = rig_env_cfg(num_envs=args.num_envs)
    env = PickleballRigEnv(cfg, device="cuda", render_mode="rgb_array" if args.video else None)
    env.reset()
    act = torch.zeros(args.num_envs, 0, device="cuda")
    frames = []
    # Warm-up (compilation, first allocations) excluded from timing; skipped when recording
    # so the video starts at the reset.
    for _ in range(0 if args.video else 10):
        env.step(act)
    torch.cuda.synchronize()
    t0 = time.time()
    for _ in range(args.steps):
        env.step(act)
        if args.video:
            frames.append(env.render())
    torch.cuda.synchronize()
    wall = time.time() - t0
    out = env.outcome_summary()
    out.update(num_envs=args.num_envs, env_steps=args.steps, wall_s=round(wall, 3),
               env_steps_per_s=round(args.num_envs * args.steps / wall),
               physics_steps_per_s=round(args.num_envs * args.steps * cfg.decimation / wall))
    print(json.dumps(out, indent=1))
    if args.json:
        json.dump(out, open(args.json, "w"), indent=1)
    if args.video:
        import imageio_ffmpeg
        import mediapy
        mediapy.set_ffmpeg(imageio_ffmpeg.get_ffmpeg_exe())  # bundled binary; no system ffmpeg needed
        mediapy.write_video(args.video, frames, fps=int(round(1 / env.step_dt)))
        stem = args.video.rsplit(".", 1)[0]
        for i in (0, 12, 15, 16, 18, 24, 40, 70):
            if i < len(frames):
                mediapy.write_image(f"{stem}_{i:03d}.png", frames[i])
        print("video:", args.video, len(frames), "frames", frames[0].shape)


if __name__ == "__main__":
    main()
