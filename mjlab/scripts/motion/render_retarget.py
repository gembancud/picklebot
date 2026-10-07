"""Render a retargeted clip on the paddle G1, with the scaled human joints as red dots beside it (Stage 5B).

Kinematic playback only (no physics). Joints are matched by name between the GMR G1 and mjlab's G1.
Usage (picklebot-mj venv, MUJOCO_GL=egl):
    python scripts/motion/render_retarget.py CSV OUT.mp4 [--view side|behind|front] [--stills OUT_DIR]
"""

from __future__ import annotations

import argparse
from pathlib import Path

import mediapy
import mujoco
import numpy as np

from picklebot_mj.g1_paddle import PADDLE_BODY, get_spec

# GMR g1_mocap_29dof joint order (= CSV columns 7..35).
GMR_JOINTS = [
    "left_hip_pitch_joint", "left_hip_roll_joint", "left_hip_yaw_joint", "left_knee_joint", "left_ankle_pitch_joint",
    "left_ankle_roll_joint", "right_hip_pitch_joint", "right_hip_roll_joint", "right_hip_yaw_joint",
    "right_knee_joint", "right_ankle_pitch_joint", "right_ankle_roll_joint", "waist_yaw_joint", "waist_roll_joint",
    "waist_pitch_joint", "left_shoulder_pitch_joint", "left_shoulder_roll_joint", "left_shoulder_yaw_joint",
    "left_elbow_joint", "left_wrist_roll_joint", "left_wrist_pitch_joint", "left_wrist_yaw_joint",
    "right_shoulder_pitch_joint", "right_shoulder_roll_joint", "right_shoulder_yaw_joint", "right_elbow_joint",
    "right_wrist_roll_joint", "right_wrist_pitch_joint", "right_wrist_yaw_joint",
]
VIEWS = {"side": (90, -10), "behind": (0, -12), "front": (180, -10)}


def load_model():
    spec = get_spec()
    spec.worldbody.add_light(pos=[0, 0, 4], dir=[0, 0, -1], diffuse=[0.9, 0.9, 0.9])
    spec.worldbody.add_light(pos=[3, 3, 3], dir=[-1, -1, -1], diffuse=[0.5, 0.5, 0.5])
    spec.worldbody.add_geom(type=mujoco.mjtGeom.mjGEOM_PLANE, size=[20, 20, 0.1], rgba=[0.32, 0.42, 0.36, 1])
    spec.visual.global_.offwidth = 960
    spec.visual.global_.offheight = 540
    m = spec.compile()
    m.vis.headlight.ambient[:] = [0.45, 0.45, 0.45]
    m.vis.headlight.diffuse[:] = [0.6, 0.6, 0.6]
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("out")
    ap.add_argument("--view", default="side", choices=list(VIEWS))
    ap.add_argument("--stills", default=None, help="also write --n-stills evenly spaced PNG stills here")
    ap.add_argument("--fps", type=int, default=50)
    ap.add_argument("--n-stills", type=int, default=6)
    ap.add_argument("--start", type=float, default=0.0)
    ap.add_argument("--seconds", type=float, default=None)
    ap.add_argument("--around-swing", type=float, default=None,
                    help="render this many seconds centred on the fastest right-hand moment (overrides --start)")
    args = ap.parse_args()
    motion = np.loadtxt(args.csv, delimiter=",", ndmin=2)
    m = load_model()
    d = mujoco.MjData(m)
    adr = [m.jnt_qposadr[m.joint(n).id] for n in GMR_JOINTS]

    def pose(row):
        d.qpos[0:3] = row[0:3]
        d.qpos[3:7] = row[[6, 3, 4, 5]]  # xyzw -> wxyz
        d.qpos[adr] = row[7:36]
        mujoco.mj_kinematics(m, d)

    if args.around_swing:
        w = m.body("right_wrist_yaw_link").id
        hand = []
        for row in motion:
            pose(row)
            hand.append(d.xpos[w].copy())
        speed = np.linalg.norm(np.diff(np.array(hand), axis=0), axis=1)
        half = int(args.around_swing * args.fps / 2)
        c = int(np.clip(np.argmax(speed), half, max(half, len(motion) - half)))
        args.start, args.seconds = (c - half) / args.fps, args.around_swing
    s0 = int(args.start * args.fps)
    s1 = len(motion) if args.seconds is None else s0 + int(args.seconds * args.fps)
    motion = motion[s0:s1]
    hum_path = Path(args.csv).with_name(Path(args.csv).stem + "_human.npz")
    human = np.load(hum_path)["pos"][s0:s1] if hum_path.exists() else None

    r = mujoco.Renderer(m, 540, 960)
    cam = mujoco.MjvCamera()
    cam.azimuth, cam.elevation = VIEWS[args.view]
    cam.distance = 3.2
    az = np.radians(cam.azimuth)
    side = 0.9 * np.array([np.sin(az), -np.cos(az), 0.0])  # human dots beside the robot, across the view
    frames = []
    for i, row in enumerate(motion):
        pose(row)
        cam.lookat[:] = [d.qpos[0], d.qpos[1], 0.8]
        r.update_scene(d, cam)
        if human is not None:
            for p in human[i]:
                if r.scene.ngeom >= r.scene.maxgeom:
                    break
                g = r.scene.geoms[r.scene.ngeom]
                mujoco.mjv_initGeom(g, mujoco.mjtGeom.mjGEOM_SPHERE, [0.03, 0, 0], p + side,
                                    np.eye(3).ravel(), np.array([0.9, 0.15, 0.15, 1.0], dtype=np.float32))
                r.scene.ngeom += 1
        frames.append(r.render())
    mediapy.write_video(args.out, frames, fps=args.fps)
    if args.stills:
        Path(args.stills).mkdir(parents=True, exist_ok=True)
        for k, i in enumerate(np.linspace(0, len(frames) - 1, args.n_stills).astype(int)):
            mediapy.write_image(f"{args.stills}/{Path(args.out).stem}_{k}.png", frames[i])
    print("paddle body:", PADDLE_BODY, "frames:", len(frames), "->", args.out)


if __name__ == "__main__":
    main()
