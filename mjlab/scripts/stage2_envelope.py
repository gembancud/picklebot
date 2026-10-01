"""Stage 2: reach and swing-speed envelope of the G1 with a wrist-mounted paddle.

Fixed pelvis at the knees-bent standing height (no balance), gravity on,
mjlab's G1 position actuators (PD gains, torque limits).
- Reach: uniform random right-arm + waist joint samples within limits, legs at the keyframe.
- Swing: settle at random pose A, then step targets to random pose B; record peak
  paddle face-centre speed (and the component along the face normal).

Usage: python scripts/stage2_envelope.py [--samples 20000] [--swings 400] [--json out.json]
"""

from __future__ import annotations

import argparse
import json
import re

import mujoco
import numpy as np

from mjlab.asset_zoo.robots.unitree_g1 import g1_constants as g1
from mjlab.entity import Entity

from picklebot_mj.g1_paddle import PADDLE_BODY, get_g1_paddle_cfg

ARM = ["right_shoulder_pitch_joint", "right_shoulder_roll_joint", "right_shoulder_yaw_joint",
       "right_elbow_joint", "right_wrist_roll_joint", "right_wrist_pitch_joint", "right_wrist_yaw_joint"]
WAIST = ["waist_yaw_joint", "waist_roll_joint", "waist_pitch_joint"]


def fixed_base_model():
    ent = Entity(get_g1_paddle_cfg())
    spec = ent.spec
    for k in list(spec.keys):
        spec.delete(k)
    for j in list(spec.joints):
        if j.type == mujoco.mjtJoint.mjJNT_FREE:
            spec.delete(j)
    spec.body("pelvis").pos = [0.0, 0.0, g1.KNEES_BENT_KEYFRAME.pos[2]]
    m = spec.compile()
    return m


def keyframe_qpos(m):
    q = np.zeros(m.nq)
    for name_re, val in g1.KNEES_BENT_KEYFRAME.joint_pos.items():
        for j in range(m.njnt):
            if re.fullmatch(name_re, mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_JOINT, j)):
                q[m.jnt_qposadr[j]] = val
    return q


def joint_ids(m, names):
    return [m.joint(n).id for n in names]


def actuator_for_joint(m):
    return {int(m.actuator_trnid[a, 0]): a for a in range(m.nu)}


def reach(m, samples, rng):
    d = mujoco.MjData(m)
    q0 = keyframe_qpos(m)
    ids = joint_ids(m, ARM + WAIST)
    lo, hi = m.jnt_range[ids, 0], m.jnt_range[ids, 1]
    pid = m.body(PADDLE_BODY).id
    pts = np.zeros((samples, 3))
    for i in range(samples):
        d.qpos[:] = q0
        d.qpos[m.jnt_qposadr[ids]] = rng.uniform(lo, hi)
        mujoco.mj_kinematics(m, d)
        pts[i] = d.xpos[pid]
    return pts


def swing_speeds(m, swings, rng, settle=0.8, swing=0.4):
    d = mujoco.MjData(m)
    q0 = keyframe_qpos(m)
    act = actuator_for_joint(m)
    arm = joint_ids(m, ARM)
    lo, hi = m.jnt_range[arm, 0] * 0.9, m.jnt_range[arm, 1] * 0.9
    pid = m.body(PADDLE_BODY).id
    res = np.zeros(6)
    out = []
    for _ in range(swings):
        a, b = rng.uniform(lo, hi), rng.uniform(lo, hi)
        mujoco.mj_resetData(m, d)
        d.qpos[:] = q0
        d.qpos[m.jnt_qposadr[arm]] = a
        for j in range(m.njnt):  # hold every actuated joint at its start position
            if j in act:
                d.ctrl[act[j]] = d.qpos[m.jnt_qposadr[j]]
        for _ in range(int(settle / m.opt.timestep)):
            mujoco.mj_step(m, d)
        for k, j in enumerate(arm):
            d.ctrl[act[j]] = b[k]
        vmax = vnmax = 0.0
        for _ in range(int(swing / m.opt.timestep)):
            mujoco.mj_step(m, d)
            mujoco.mj_objectVelocity(m, d, mujoco.mjtObj.mjOBJ_BODY, pid, res, 0)
            v = res[3:]
            n = d.xmat[pid].reshape(3, 3)[:, 2]
            vmax = max(vmax, float(np.linalg.norm(v)))
            vnmax = max(vnmax, float(abs(v @ n)))
        out.append((vmax, vnmax))
    return np.array(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", type=int, default=20000)
    ap.add_argument("--swings", type=int, default=400)
    ap.add_argument("--json", type=str, default=None)
    args = ap.parse_args()
    rng = np.random.default_rng(0)
    m = fixed_base_model()
    m.opt.timestep = 0.002
    pts = reach(m, args.samples, rng)
    pelvis = np.array([0.0, 0.0, g1.KNEES_BENT_KEYFRAME.pos[2]])
    rel = pts - pelvis
    horiz = np.linalg.norm(rel[:, :2], axis=1)
    sw = swing_speeds(m, args.swings, rng)
    pct = lambda x, p: float(np.percentile(x, p))
    out = {
        "pelvis_height": float(pelvis[2]),
        "paddle_mass_total_kg": float(m.body_subtreemass[m.body(PADDLE_BODY).id]),
        "robot_mass_kg": float(m.body_subtreemass[1]),
        "reach_horizontal_max_m": float(horiz.max()),
        "reach_horizontal_p95_m": pct(horiz, 95),
        "reach_forward_max_m": float(rel[:, 0].max()),
        "reach_right_max_m": float(-rel[:, 1].min()),
        "reach_left_max_m": float(rel[:, 1].max()),
        "face_height_min_m": float(pts[:, 2].min()),
        "face_height_max_m": float(pts[:, 2].max()),
        "face_height_p05_p95_m": [pct(pts[:, 2], 5), pct(pts[:, 2], 95)],
        "swing_samples": int(len(sw)),
        "swing_speed_max_mps": float(sw[:, 0].max()),
        "swing_speed_p95_mps": pct(sw[:, 0], 95),
        "swing_speed_median_mps": pct(sw[:, 0], 50),
        "swing_normal_speed_max_mps": float(sw[:, 1].max()),
        "swing_normal_speed_p95_mps": pct(sw[:, 1], 95),
        "timestep": m.opt.timestep,
    }
    print(json.dumps(out, indent=1))
    if args.json:
        json.dump(out, open(args.json, "w"), indent=1)


if __name__ == "__main__":
    main()
