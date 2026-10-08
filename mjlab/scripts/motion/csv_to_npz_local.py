"""Convert retargeted clip CSVs to one mjlab tracking npz, locally (Stage 5B).

mjlab's scripts/csv_to_npz.py replays a CSV on the robot to log every body's world state, then uploads the result to
the Weights & Biases registry. This reuses its MotionLoader (interpolation, velocities) and the same replay, on the
paddle G1 tracking scene, and writes the npz locally only. Several clips are concatenated into one file, with
`clip_starts` (frame index of each clip's first frame) and `clip_names`, for the multi-clip motion command
(picklebot_mj/tasks/tracking.py), which never plays across a clip boundary.

Usage (picklebot-mj venv):
    python scripts/motion/csv_to_npz_local.py artifacts/motion/retargeted-v4 artifacts/motion/tracking/tennis-v4.npz
        [--clips a,b] [--input-fps 50] [--output-fps 50]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import mjlab.tasks  # noqa: F401  (registers tasks; import order avoids a circular import in picklebot_mj)
import numpy as np
import torch
from mjlab.scene import Scene
from mjlab.scripts.csv_to_npz import MotionLoader
from mjlab.sim.sim import Simulation, SimulationCfg

from picklebot_mj.tasks.tracking import GMR_JOINTS, paddle_tracking_env_cfg

FIELDS = ("joint_pos", "joint_vel", "body_pos_w", "body_quat_w", "body_lin_vel_w", "body_ang_vel_w")


def replay(sim, scene, csv: Path, input_fps: int, output_fps: int):
    motion = MotionLoader(motion_file=str(csv), input_fps=input_fps, output_fps=output_fps, device=sim.device)
    robot = scene["robot"]
    idx = robot.find_joints(GMR_JOINTS, preserve_order=True)[0]
    log = {k: [] for k in FIELDS}
    scene.reset()
    while True:
        (base_pos, base_rot, base_lin, base_ang, dof_pos, dof_vel), done = motion.get_next_state()
        root = robot.data.default_root_state.clone()
        root[:, 0:3] = base_pos
        root[:, :2] += scene.env_origins[:, :2]
        root[:, 3:7] = base_rot
        root[:, 7:10] = base_lin
        root[:, 10:] = base_ang
        robot.write_root_state_to_sim(root)
        jp, jv = robot.data.default_joint_pos.clone(), robot.data.default_joint_vel.clone()
        jp[:, idx], jv[:, idx] = dof_pos, dof_vel
        robot.write_joint_state_to_sim(jp, jv)
        sim.forward()
        scene.update(sim.mj_model.opt.timestep)
        d = robot.data
        for k, v in (("joint_pos", d.joint_pos), ("joint_vel", d.joint_vel), ("body_pos_w", d.body_link_pos_w),
                     ("body_quat_w", d.body_link_quat_w), ("body_lin_vel_w", d.body_link_lin_vel_w),
                     ("body_ang_vel_w", d.body_link_ang_vel_w)):
            log[k].append(v[0].cpu().numpy().copy())
        if done:
            return {k: np.stack(v) for k, v in log.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("out")
    ap.add_argument("--clips", default=None, help="comma-separated stems (default: DIR/accepted.json)")
    ap.add_argument("--clips-json", default=None, help="a JSON list of stems (overrides DIR/accepted.json)")
    ap.add_argument("--input-fps", type=int, default=50)
    ap.add_argument("--output-fps", type=int, default=50)
    ap.add_argument("--device", default="cuda:0")
    args = ap.parse_args()
    root = Path(args.dir)
    if args.clips:
        stems = args.clips.split(",")
    else:
        stems = json.loads(Path(args.clips_json or root / "accepted.json").read_text())
    sim_cfg = SimulationCfg()
    sim_cfg.mujoco.timestep = 1.0 / args.output_fps
    scene = Scene(paddle_tracking_env_cfg(motion_file="").scene, device=args.device)
    model = scene.compile()
    sim = Simulation(num_envs=1, cfg=sim_cfg, model=model, device=args.device)
    scene.initialize(sim.mj_model, sim.model, sim.data)
    parts, starts, n = [], [], 0
    with torch.no_grad():
        for s in stems:
            log = replay(sim, scene, root / f"{s}.csv", args.input_fps, args.output_fps)
            parts.append(log)
            starts.append(n)
            n += len(log["joint_pos"])
            print(f"{s}: {len(log['joint_pos'])} frames")
    out = {k: np.concatenate([p[k] for p in parts]) for k in FIELDS}
    out.update(fps=np.array([args.output_fps]), clip_starts=np.array(starts), clip_names=np.array(stems))
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    np.savez(args.out, **out)
    print(f"{len(stems)} clips, {n} frames ({n / args.output_fps / 60:.1f} min) -> {args.out}")


if __name__ == "__main__":
    main()
