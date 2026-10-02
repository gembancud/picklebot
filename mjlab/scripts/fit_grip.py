"""Fit the v2 handshake grip: slide the handle out along its (tilted) axis until the paddle
face clears every G1 right-hand mesh vertex by a margin. Prints the fitted handle centre.

Usage: python scripts/fit_grip.py [--tilt 35] [--margin 0.003] [--y 0.025] [--x0 0.09]
"""

import argparse

import mujoco
import numpy as np

from mjlab.asset_zoo.robots.unitree_g1 import g1_constants as g1
from picklebot_mj.ball_sim import PADDLE_HALF
from picklebot_mj.g1_paddle import WRIST_BODY, GripCfg, paddle_pose_in_wrist


def hand_vertices():
    m = g1.get_spec().compile()
    wid = m.body(WRIST_BODY).id
    out = []
    for g in range(m.ngeom):
        if m.geom_bodyid[g] == wid and m.geom_type[g] == mujoco.mjtGeom.mjGEOM_MESH:
            mid = m.geom_dataid[g]
            v = m.mesh_vert[m.mesh_vertadr[mid]: m.mesh_vertadr[mid] + m.mesh_vertnum[mid]]
            R = np.zeros(9)
            mujoco.mju_quat2Mat(R, m.geom_quat[g])
            out.append(v @ R.reshape(3, 3).T + m.geom_pos[g])
    return np.concatenate(out)


def face_intrusions(grip: GripCfg, verts, margin):
    c, q = paddle_pose_in_wrist(grip)
    R = np.zeros(9)
    mujoco.mju_quat2Mat(R, q)
    local = (verts - c) @ R.reshape(3, 3)
    half = np.array(PADDLE_HALF) + margin
    return int(np.all(np.abs(local) <= half, axis=1).sum())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tilt", type=float, default=35.0)
    ap.add_argument("--margin", type=float, default=0.003)
    ap.add_argument("--y", type=float, default=0.025)
    ap.add_argument("--x0", type=float, default=0.09)
    a = ap.parse_args()
    verts = hand_vertices()
    t = np.radians(a.tilt)
    axis = np.array([np.cos(t), 0.0, np.sin(t)])
    for s in np.arange(0.0, 0.15, 0.0025):
        h = np.array([a.x0, a.y, 0.0]) + s * axis
        grip = GripCfg("v2-handshake", a.tilt, tuple(np.round(h, 4)))
        n = face_intrusions(grip, verts, a.margin)
        if n == 0:
            print(f"fitted: slide={s:.4f} handle_centre={tuple(np.round(h, 4))} (hand verts {len(verts)})")
            break
    else:
        print("no clearance found")
