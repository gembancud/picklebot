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
from picklebot_mj.feeds import FAMILY_NAMES, FeedMix
from picklebot_mj.g1_paddle import GRIP_V1, get_g1_paddle_cfg
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
    ap.add_argument("--families", default="easy_forehand",
                    help="comma-separated feed families sampled uniformly, or 'all'")
    ap.add_argument("--task", default=None, help="task id (default: Picklebot-Return-Stand-G1)")
    ap.add_argument("--target", choices=["random", "A", "B"], default=None,
                    help="aiming tasks: force the landing target (paired A/B evaluation)")
    ap.add_argument("--grip", choices=["default", "v1"], default="default",
                    help="v1 = Stage 2 robot (inline grip, square face) for old checkpoints")
    ap.add_argument("--view", choices=["side", "behind"], default="side")
    ap.add_argument("--slowmo", type=float, default=1.0, help="playback slow-down factor for the video")
    ap.add_argument("--json", default=None)
    args = ap.parse_args()
    assert args.seed in seeds.DEV_EVAL_SEEDS, "evaluation must use development seeds"

    task = args.task or TASK_RETURN_STAND
    cfg = load_env_cfg(task)
    if args.target is not None:
        cfg.actions["ball"].target_mode = args.target
    cfg.scene.num_envs = args.envs
    cfg.seed = args.seed
    cfg.actions["ball"].seed = args.seed
    cfg.observations["actor"].enable_corruption = False
    fams = list(FAMILY_NAMES) if args.families == "all" else args.families.split(",")
    cfg.actions["ball"].feed_mix = FeedMix({f: 1.0 for f in fams})
    if args.grip == "v1":
        robot = cfg.scene.entities["robot"]
        robot.spec_fn = get_g1_paddle_cfg(GRIP_V1).spec_fn
        cfg.actions["ball"].paddle_corner_radius = 0.0
    if args.video:
        cfg.viewer.width, cfg.viewer.height = 960, 540
        # Side-on view from the robot's right, wide enough to follow the ball over the net.
        if args.view == "side":
            cfg.viewer.distance, cfg.viewer.elevation, cfg.viewer.azimuth = 6.5, -8.0, 270.0
        else:  # behind the robot, looking down the court toward the net
            cfg.viewer.distance, cfg.viewer.elevation, cfg.viewer.azimuth = 4.5, -14.0, 0.0
        cfg.viewer.geom_group = (1, 1, 1, 1, 0, 0)  # group 3 = court markings
        cfg.viewer.max_extra_envs = 0
    env = ManagerBasedRlEnv(cfg=cfg, device="cuda", render_mode="rgb_array" if args.video else None)
    agent_cfg = load_rl_cfg(task)
    venv = RslRlVecEnvWrapper(env, clip_actions=agent_cfg.clip_actions)
    runner = MjlabOnPolicyRunner(venv, asdict(agent_cfg), device="cuda")
    runner.load(args.checkpoint, load_cfg={"actor": True}, strict=True, map_location="cuda")
    policy = runner.get_inference_policy(device="cuda")

    term = env.action_manager.get_term("ball")
    term.fault_counts.zero_()
    term.ep_family.zero_()
    term.land_family.zero_()
    for v in term.ep.values():
        v.zero_()
    obs = venv.get_observations()
    frames = []
    steps = int(round(args.seconds / env.step_dt))
    with torch.inference_mode():
        for _ in range(steps):
            obs, _, dones, _ = venv.step(policy(obs))
            if args.video:
                frames.append(env.render())
    # Completed episodes only (outcomes tallied by the ball term at each episode end).
    episodes = int(term.ep["episodes"])
    hits, rets, falls = int(term.ep["contact"]), int(term.ep["legal_return"]), int(term.ep["fall"])
    endings = {Fault(i).name: int(c) for i, c in enumerate(term.fault_counts.tolist()) if c}
    out = {
        "checkpoint": args.checkpoint, "seed": args.seed, "envs": args.envs, "sim_seconds": args.seconds,
        "episodes": episodes,
        "contact_rate": round(hits / max(episodes, 1), 4), "contact_ci95": wilson(hits, episodes),
        "legal_return_rate": round(rets / max(episodes, 1), 4), "legal_return_ci95": wilson(rets, episodes),
        "fall_rate": round(falls / max(episodes, 1), 4), "fall_ci95": wilson(falls, episodes),
        "hits": hits, "legal_returns": rets, "falls": falls, "rally_endings": endings,
        "grip": args.grip, "families": fams, "task": task, "target": args.target,
        "robot_episodes": int(term.ep["env_episodes"]), "robot_falls": int(term.ep["env_falls"]),
        "robot_fall_rate_per_episode": round(int(term.ep["env_falls"]) / max(int(term.ep["env_episodes"]), 1), 4),
    }
    table = {}
    for i, name in enumerate(FAMILY_NAMES):
        n_ep, c, r, f = (int(v) for v in term.ep_family[i].tolist())
        if n_ep:
            table[name] = {"episodes": n_ep, "contact": round(c / n_ep, 4), "contact_ci95": wilson(c, n_ep),
                           "legal_return": round(r / n_ep, 4), "legal_return_ci95": wilson(r, n_ep),
                           "fall": round(f / n_ep, 4), "fall_ci95": wilson(f, n_ep)}
            la, lb, lt = (int(v) for v in term.land_family[i].tolist())
            table[name].update({"landings_in_A": la, "landings_in_B": lb, "target_hits": lt})
    out["per_family"] = table
    d = {k: float(v) for k, v in term.diag.items()}
    nc, nl = max(d["n_contact"], 1.0), max(d["n_land"], 1.0)
    out["contact_diagnostics"] = {
        "first_contacts": int(d["n_contact"]),
        "paddle_speed_mean": round(d["paddle_speed"] / nc, 3),
        "paddle_speed_std": round(math.sqrt(max(d["paddle_speed_sq"] / nc - (d["paddle_speed"] / nc) ** 2, 0)), 3),
        "ball_speed_in_mean": round(d["ball_in_speed"] / nc, 3),
        "ball_speed_out_mean": round(d["ball_out_speed"] / nc, 3),
        "contact_height_mean": round(d["contact_height"] / nc, 3),
        "net_crossings": int(d["n_cross"]),
        "net_clearance_mean_m": round(d["net_clear"] / max(d["n_cross"], 1.0), 3),
        "legal_landings": int(d["n_land"]),
        "landing_x_mean": round(d["land_x"] / nl, 3),
        "landing_x_std": round(math.sqrt(max(d["land_x_sq"] / nl - (d["land_x"] / nl) ** 2, 0)), 3),
        "landing_abs_y_mean": round(d["land_y_abs"] / nl, 3),
        "landings_in_A": int(d["land_in_A"]), "landings_in_B": int(d["land_in_B"]),
        "target_hits": int(d["target_hit"]),
    }
    print(json.dumps(out, indent=1))
    print(f"{'family':14s} {'episodes':>8s} {'contact':>8s} {'legal return [95% CI]':>24s} {'fall':>6s}")
    for name, r in table.items():
        ci = r['legal_return_ci95']
        print(f"{name:14s} {r['episodes']:8d} {r['contact']:8.3f} {r['legal_return']:8.3f} [{ci[0]:.3f}, {ci[1]:.3f}] {r['fall']:6.3f}")
    if args.json:
        json.dump(out, open(args.json, "w"), indent=1)
    if args.video:
        import imageio_ffmpeg
        import mediapy
        mediapy.set_ffmpeg(imageio_ffmpeg.get_ffmpeg_exe())
        mediapy.write_video(args.video, frames, fps=max(1, int(round(1 / env.step_dt / args.slowmo))))
        stem = args.video.rsplit(".", 1)[0]
        for i in range(0, len(frames), 25):
            mediapy.write_image(f"{stem}_{i:03d}.png", frames[i])
        print("video:", args.video, len(frames))


if __name__ == "__main__":
    main()
