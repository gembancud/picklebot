"""Render close-ups of the G1's right hand holding the paddle (standing keyframe pose).

Usage (WSL, MUJOCO_GL=egl): python scripts/render_grip.py OUT_DIR
"""

import re
import sys

import mediapy
import mujoco
import numpy as np

from mjlab.asset_zoo.robots.unitree_g1 import g1_constants as g1
from picklebot_mj.g1_paddle import PADDLE_BODY, WRIST_BODY, get_spec

out = sys.argv[1]
from picklebot_mj import g1_paddle
grip = {"v1": g1_paddle.GRIP_V1, "v2": g1_paddle.GRIP_V2}[sys.argv[2] if len(sys.argv) > 2 else "v1"]
spec = get_spec(grip)
spec.worldbody.add_light(pos=[0, 0, 3], dir=[0, 0, -1], diffuse=[0.8, 0.8, 0.8])
spec.worldbody.add_geom(type=mujoco.mjtGeom.mjGEOM_PLANE, size=[3, 3, 0.1], rgba=[0.3, 0.35, 0.45, 1])
spec.visual.global_.offwidth = 960
spec.visual.global_.offheight = 540
m = spec.compile()
d = mujoco.MjData(m)
d.qpos[0:3] = g1.KNEES_BENT_KEYFRAME.pos
d.qpos[3:7] = [1, 0, 0, 0]
for name_re, val in g1.KNEES_BENT_KEYFRAME.joint_pos.items():
    for j in range(m.njnt):
        if re.fullmatch(name_re, mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_JOINT, j) or ""):
            d.qpos[m.jnt_qposadr[j]] = val
mujoco.mj_forward(m, d)
hand = d.xpos[m.body(WRIST_BODY).id]
paddle = d.xpos[m.body(PADDLE_BODY).id]
look = (hand + paddle) / 2
r = mujoco.Renderer(m, 540, 960)
for name, az, el, dist in (("grip_side", 270, -10, 0.9), ("grip_front", 180, -15, 0.9),
                           ("grip_top", 270, -70, 0.8), ("full_body", 215, -12, 2.6)):
    cam = mujoco.MjvCamera()
    cam.lookat[:] = look if name != "full_body" else d.xpos[1]
    cam.azimuth, cam.elevation, cam.distance = az, el, dist
    r.update_scene(d, cam)
    mediapy.write_image(f"{out}/{grip.name}-{name}.png", r.render())
    print("wrote", name)
print("wrist->face centre (m):", np.round(paddle - hand, 3))
