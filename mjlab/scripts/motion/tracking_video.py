"""Render a tracking teacher in physics on single-stroke segments (Stage 5B review videos).

Picks, for each requested stroke type, the segment ranked --rank by the segment table of a per-stroke evaluation
(`tracking_eval.py --per-stroke --json`), or the first segment of that type if no table is given. One env per video:
the robot starts on the reference at the segment start and runs to its end (no pushes, no noise). mjlab's ghost
(the reference motion) is drawn when the command's debug visualisation is on.

Usage (picklebot-mj venv, MUJOCO_GL=egl):
    python scripts/motion/tracking_video.py --checkpoint PATH --task Picklebot-Tracking-Tennis-Big-G1
        --strokes forehand,backhand,serve,smash --out artifacts/videos/stage5b/teacher [--view side|front]
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
from pathlib import Path

import mjlab.tasks  # noqa: F401
import numpy as np
import torch
from mjlab.envs import ManagerBasedRlEnv
from mjlab.rl import MjlabOnPolicyRunner, RslRlVecEnvWrapper
from mjlab.tasks.registry import load_env_cfg, load_rl_cfg, load_runner_cls

from picklebot_mj.tasks.tracking import stroke_segments

STROKE_TAGS = (("Servicio", "serve"), ("Remate", "smash"), ("VDerecha", "forehand_volley"),
               ("VReves", "backhand_volley"), ("Derecha", "forehand"), ("Reves", "backhand"))
VIEWS = {"side": (4.0, -8.0, 270.0), "front": (4.0, -8.0, 180.0)}


def stroke_of(name: str) -> str:
    tag = name.split("_", 1)[1]
    return next(s for k, s in STROKE_TAGS if tag.startswith(k))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--task", default="Picklebot-Tracking-Tennis-Big-G1")
    ap.add_argument("--strokes", default="forehand,backhand,serve,smash")
    ap.add_argument("--out", default="artifacts/videos/stage5b/teacher")
    ap.add_argument("--view", default="side", choices=list(VIEWS))
    ap.add_argument("--clip-player", default="jgacosta", help="prefer segments from this player's clips")
    args = ap.parse_args()

    cfg = load_env_cfg(args.task, play=True)
    mc = cfg.commands["motion"]
    motion = np.load(mc.motion_file)
    names = [str(n) for n in motion["clip_names"]]
    starts, total = motion["clip_starts"], len(motion["joint_pos"])
    cfg.scene.num_envs = 1
    cfg.viewer.width, cfg.viewer.height = 960, 540
    cfg.viewer.distance, cfg.viewer.elevation, cfg.viewer.azimuth = VIEWS[args.view]
    cfg.viewer.max_extra_envs = 0
    env = ManagerBasedRlEnv(cfg=cfg, device="cuda", render_mode="rgb_array")
    body = list(env.scene["robot"].body_names).index("right_wrist_yaw_link")
    speed = np.linalg.norm(motion["body_lin_vel_w"][:, body], axis=-1)
    segs = stroke_segments(speed, starts, total, float(motion["fps"][0]))
    agent = load_rl_cfg(args.task)
    venv = RslRlVecEnvWrapper(env, clip_actions=agent.clip_actions)
    runner = (load_runner_cls(args.task) or MjlabOnPolicyRunner)(venv, asdict(agent), device="cuda")
    runner.load(args.checkpoint, map_location="cuda")
    policy = runner.get_inference_policy(device="cuda")
    cmd = env.command_manager.get_term("motion")
    Path(args.out).mkdir(parents=True, exist_ok=True)
    import imageio_ffmpeg
    import mediapy

    mediapy.set_ffmpeg(imageio_ffmpeg.get_ffmpeg_exe())
    for stroke in args.strokes.split(","):
        cands = [s for s in segs if stroke_of(names[s[0]]) == stroke]
        pref = [s for s in cands if names[s[0]].startswith(args.clip_player)] or cands
        c, a, b, _ = pref[len(pref) // 2]  # a mid-take swing: the player is warmed up, the robot too
        env.reset()
        ids = torch.zeros(1, dtype=torch.long, device="cuda")
        cmd.start_at(ids, torch.tensor([a], device="cuda"))
        env.sim.forward()
        cmd.update_relative_body_poses()
        obs = venv.get_observations()
        frames, ok = [], True
        with torch.no_grad():
            for _ in range(b - a - 1):
                obs, _, dones, _ = venv.step(policy(obs))
                frames.append(env.render())
                if bool(env.termination_manager.terminated[0]):
                    ok = False
                    break
        out = f"{args.out}-{stroke}-{args.view}.mp4"
        mediapy.write_video(out, frames, fps=int(round(1 / env.step_dt)))
        print(f"{stroke}: {names[c]} {(a - starts[c]) / 50:.1f}-{(b - starts[c]) / 50:.1f}s {'completed' if ok else 'terminated'} -> {out}")
    env.close()


if __name__ == "__main__":
    main()
