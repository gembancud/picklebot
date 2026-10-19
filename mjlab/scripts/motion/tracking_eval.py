"""Per-clip evaluation of a tracking teacher (Stage 5B gate), from a local checkpoint.

mjlab's tasks/tracking/scripts/evaluate.py fetches checkpoints from W&B and starts episodes at random times. This
plays every clip from its first frame to its last: env i plays clip i % n_clips. Pushes, start-state randomisation
and observation noise are off; the tracking terminations are on. An episode succeeds when it reaches the clip's last
frame without a termination. A fall is the torso dropping below FALL_Z at any time.

Metrics per clip (mjlab.tasks.tracking.mdp.metrics, averaged over the frames played): MPKPE, root-relative MPKPE,
end-effector position error, joint velocity error; plus success, fall and the termination causes.

With --per-stroke (D-048), the units are single-stroke segments (picklebot_mj.tasks.tracking.stroke_segments)
instead of whole clips: each env starts on the reference at a segment's first frame and succeeds by reaching its
last frame without a termination; per-stroke-type numbers average over segments.

Usage (picklebot-mj venv):
    python scripts/motion/tracking_eval.py --checkpoint PATH [--task Picklebot-Tracking-Tennis-G1] [--repeats 4]
        [--seed 4200300] [--per-stroke] [--json OUT]
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import asdict
from types import SimpleNamespace

import mjlab.tasks  # noqa: F401
import numpy as np
import torch
from mjlab.envs import ManagerBasedRlEnv
from mjlab.rl import MjlabOnPolicyRunner, RslRlVecEnvWrapper
from mjlab.tasks.registry import load_env_cfg, load_rl_cfg, load_runner_cls
from mjlab.tasks.tracking.mdp.metrics import (compute_ee_position_error, compute_joint_velocity_error,
                                              compute_mpkpe, compute_root_relative_mpkpe)

from picklebot_mj import seeds
from picklebot_mj.tasks.tracking import stroke_segments

FALL_Z = 0.5  # torso_link height (m)
# A fall must be unintended: the reference torso is still above FALL_Z + REF_MARGIN when the robot's drops below FALL_Z.
# (LAFAN1 walk3 clips crawl and lie down; the raw measure counted the robot following them as falls. 2026-10-09.)
REF_MARGIN = 0.1


def scene_body_names(cfg):
    """The robot entity's body order (as in the npz body arrays), from the compiled scene."""
    import mujoco
    from mjlab.scene import Scene

    m = Scene(cfg.scene, device="cpu").compile()
    names = [mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_BODY, i) for i in range(1, m.nbody)]
    return [x.split("/", 1)[1] for x in names if x and x.startswith("robot/")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--task", default="Picklebot-Tracking-Tennis-G1")
    ap.add_argument("--repeats", type=int, default=4, help="episodes per clip")
    ap.add_argument("--seed", type=int, default=4200300)
    ap.add_argument("--json", default=None)
    ap.add_argument("--window-s", type=float, default=4.0, help="per-stroke mode: window length for non-tennis clips")
    ap.add_argument("--cmd-delay-ms", type=int, default=0,
                    help="Stage 5F (D-111): fixed joint-command delay, a multiple of the 5 ms physics step")
    ap.add_argument("--latent", action="store_true",
                    help="--checkpoint is a latent controller (H1): act with encoder -> decoder (mean latent)")
    ap.add_argument("--per-stroke", action="store_true",
                    help="score single-stroke segments around right-hand speed peaks instead of whole clips (D-048)")
    args = ap.parse_args()
    assert args.seed in seeds.DEV_EVAL_SEEDS, "evaluation must use development seeds"

    cfg = load_env_cfg(args.task, play=False)
    mc = cfg.commands["motion"]
    mc.pose_range, mc.velocity_range, mc.joint_position_range = {}, {}, (0.0, 0.0)
    mc.sampling_mode = "start"
    cfg.events.pop("push_robot", None)
    cfg.observations["actor"].enable_corruption = False
    cfg.episode_length_s = 60.0  # longer than any clip: episodes end at the clip end or a termination
    if args.cmd_delay_ms:  # D-111: every joint command applied cmd_delay_ms late (fixed lag on every actuator)
        import dataclasses
        assert args.cmd_delay_ms % 5 == 0, "whole physics steps (5 ms)"
        k = args.cmd_delay_ms // 5
        robot = cfg.scene.entities["robot"]
        robot.articulation = dataclasses.replace(robot.articulation, actuators=tuple(
            dataclasses.replace(a, delay_min_lag=k, delay_max_lag=k) for a in robot.articulation.actuators))
    motion = np.load(mc.motion_file)
    clip_starts = motion["clip_starts"]
    n_clips, total = len(clip_starts), len(motion["joint_pos"])
    clip_ends = np.r_[clip_starts[1:], total]
    body_names = scene_body_names(cfg)
    if args.per_stroke:
        hand = body_names.index("right_wrist_yaw_link")
        speed = np.linalg.norm(motion["body_lin_vel_w"][:, hand], axis=-1)
        fps = float(motion["fps"][0])
        source = motion["clip_source"] if "clip_source" in motion else np.zeros(n_clips, dtype=int)
        tennis = [u for u in stroke_segments(speed, clip_starts, total, fps) if source[u[0]] == 0]
        # Non-tennis clips (LAFAN1 footwork, H0): fixed windows of --window-s seconds.
        win = int(args.window_s * fps)
        other = [(c, int(a), int(a) + win, -1) for c in range(n_clips) if source[c] != 0
                 for a in range(int(clip_starts[c]), int(clip_ends[c]) - win + 1, win)]
        units = tennis + other  # (clip, start, end, peak)
    else:
        units = [(c, int(clip_starts[c]), int(clip_ends[c]), -1) for c in range(n_clips)]
    n_units = len(units)
    cfg.scene.num_envs = n_units * args.repeats
    cfg.seed = args.seed
    env = ManagerBasedRlEnv(cfg=cfg, device="cuda")
    wrapped = RslRlVecEnvWrapper(env, clip_actions=load_rl_cfg(args.task).clip_actions)
    runner_cls = load_runner_cls(args.task) or MjlabOnPolicyRunner
    runner = runner_cls(wrapped, asdict(load_rl_cfg(args.task)), device="cuda")
    if args.latent:
        from picklebot_mj.latent import LatentController

        lat = LatentController().cuda()
        lat.load_state_dict(torch.load(args.checkpoint, map_location="cuda", weights_only=False)["model"])
        lat.eval()
        policy = lambda o: lat(o["actor"])  # noqa: E731
    else:
        # Actor only (Stage 5F C1: a delay-trained critic has an extra input the evaluation task does not build).
        runner.load(args.checkpoint, load_cfg={"actor": True}, strict=True, map_location="cuda")
        policy = runner.get_inference_policy(device="cuda")

    cmd = env.command_manager.get_term("motion")
    assert list(env.scene["robot"].body_names) == body_names, "body order differs from the compiled scene"
    n = env.num_envs
    ids = torch.arange(n, device="cuda")
    unit = ids % n_units
    u = torch.tensor(units, dtype=torch.long, device="cuda")
    clip = u[unit, 0]
    env.reset()
    cmd.start_at(ids, u[unit, 1])
    env.sim.forward()
    cmd.update_relative_body_poses()
    obs = wrapped.get_observations()
    ee = cfg.terminations["ee_body_pos"].params["body_names"]
    torso = env.scene["robot"].body_names.index("torso_link")
    done = torch.zeros(n, dtype=torch.bool, device="cuda")
    success, fell, fell_raw = torch.zeros_like(done), torch.zeros_like(done), torch.zeros_like(done)
    ref_torso = list(cmd.cfg.body_names).index("torso_link")
    cause = ["" for _ in range(n)]
    sums = defaultdict(lambda: torch.zeros(n, device="cuda"))
    frames = torch.zeros(n, device="cuda")
    end = u[unit, 2] - 1
    while not done.all():
        ref = SimpleNamespace(num_envs=n, device="cuda", cfg=cmd.cfg, body_pos_w=cmd.body_pos_w.clone(),
                              body_pos_relative_w=cmd.body_pos_relative_w.clone(),
                              body_quat_relative_w=cmd.body_quat_relative_w.clone(), joint_vel=cmd.joint_vel.clone())
        at_end = cmd.time_steps >= end  # the step that would wrap into a new clip: count as completed
        with torch.no_grad():
            obs, _, dones, _ = wrapped.step(policy(obs))
        ref.robot_body_pos_w, ref.robot_body_quat_w = cmd.robot_body_pos_w, cmd.robot_body_quat_w
        ref.robot_joint_vel = cmd.robot_joint_vel
        live = ~done
        for k, f in (("mpkpe", compute_mpkpe), ("r_mpkpe", compute_root_relative_mpkpe),
                     ("joint_vel_error", compute_joint_velocity_error)):
            sums[k] += torch.where(live, f(ref), 0.0)
        sums["ee_pos_error"] += torch.where(live, compute_ee_position_error(ref, ee), 0.0)
        frames += live.float()
        low = live & (env.scene["robot"].data.body_link_pos_w[:, torso, 2] < FALL_Z)
        fell_raw |= low
        fell |= low & (ref.body_pos_w[:, ref_torso, 2] > FALL_Z + REF_MARGIN)
        term = env.termination_manager.terminated & live
        for i in torch.where(term)[0].tolist():
            active = [name for name in env.termination_manager.active_terms
                      if bool(env.termination_manager.get_term(name)[i])]
            cause[i] = "+".join(active) or "terminated"
        success |= live & at_end & ~term
        done |= term | (live & at_end)
    names = [str(s) for s in np.load(mc.motion_file)["clip_names"]]
    per_clip = []
    for k in range(n_units):
        sel = (unit == k)
        f = frames[sel].clamp(min=1)
        per_clip.append({"clip": names[units[k][0]], "start_s": round(units[k][1] / 50.0, 2),
                         "success": float(success[sel].float().mean()),
                         "fall": float(fell[sel].float().mean()), "fall_raw": float(fell_raw[sel].float().mean()),
                         **{k: float((v[sel] / f).mean()) for k, v in sums.items()},
                         "causes": sorted({cause[i] for i in torch.where(sel)[0].tolist() if cause[i]})})
    f = frames.clamp(min=1)
    summary = {"checkpoint": args.checkpoint, "seed": args.seed, "cmd_delay_ms": args.cmd_delay_ms, "episodes": n,
               "clips": n_clips,
               "scoring": "per-stroke segments" if args.per_stroke else "whole clips", "units": n_units,
               "success_rate": float(success.float().mean()), "fall_rate": float(fell.float().mean()),
               "fall_rate_raw": float(fell_raw.float().mean()),
               **{k: float((v / f).mean()) for k, v in sums.items()},
               "units_all_success": int(sum(p["success"] == 1.0 for p in per_clip)),
               "termination_causes": dict(sorted(defaultdict(int, {c: cause.count(c) for c in set(cause) if c})
                                                 .items(), key=lambda x: -x[1]))}
    by_stroke = defaultdict(list)
    for p in per_clip:
        if p["clip"].startswith("footwork_"):  # walking-teacher footwork clips (D-081)
            by_stroke["footwork"].append(p)
            continue
        if p["clip"].startswith("Neutral_"):  # 100STYLE footwork (D-101): Neutral_FW_train -> style100_FW
            by_stroke["style100_" + p["clip"].split("_")[1]].append(p)
            continue
        tag = p["clip"].split("_", 1)[1]
        if tag.startswith("subject"):  # LAFAN1 clip: walk1_subject1 -> lafan_walk; mirrored (D-077) -> lafanmirror_walk
            pre = "lafanmirror_" if p["clip"].endswith("_mirror") else "lafan_"
            by_stroke[pre + p["clip"].split("_")[0].rstrip("0123456789")].append(p)
            continue
        stroke = next(s for k, s in (("Servicio", "serve"), ("Remate", "smash"), ("VDerecha", "forehand_volley"),
                                     ("VReves", "backhand_volley"), ("Derecha", "forehand"), ("Reves", "backhand"))
                      if tag.startswith(k))
        by_stroke[stroke].append(p)
    summary["by_stroke"] = {s: {"units": len(g), "success": float(np.mean([p["success"] for p in g])),
                                "fall": float(np.mean([p["fall"] for p in g])),
                                "mpkpe": float(np.mean([p["mpkpe"] for p in g]))} for s, g in by_stroke.items()}
    pooled = defaultdict(list)  # success pooled by source: tennis strokes, LAFAN1, mirrored LAFAN1, footwork
    for k, g in by_stroke.items():
        src = ("lafan_mirror" if k.startswith("lafanmirror_") else "lafan" if k.startswith("lafan_")
               else "style100" if k.startswith("style100_")
               else "footwork" if k == "footwork" else "tennis")
        pooled[src].extend(p["success"] for p in g)
    summary["by_source"] = {k: float(np.mean(v)) for k, v in pooled.items()}
    print(json.dumps({k: v for k, v in summary.items()}, indent=1))
    if args.json:
        json.dump({**summary, "per_clip": per_clip}, open(args.json, "w"), indent=1)
    env.close()


if __name__ == "__main__":
    main()
