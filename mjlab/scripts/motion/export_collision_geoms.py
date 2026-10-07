"""Export the paddle G1's collision geoms (mjlab capsules/boxes/spheres, plus the paddle face) to JSON (Stage 5B).

tennis_retarget.py swaps them into GMR's G1 (whose collision geoms are meshes) so the IK's collision avoidance sees
the same shapes the physics will. Body frames are checked against GMR's model there.
Usage (picklebot-mj venv): python scripts/motion/export_collision_geoms.py artifacts/motion/g1_collision_geoms.json
"""

import json
import sys

import mjlab.tasks  # noqa: F401  (import order: avoids a circular import in picklebot_mj.g1_paddle)
import mujoco
import numpy as np

from picklebot_mj.g1_paddle import get_spec

m = get_spec().compile()
d = mujoco.MjData(m)
d.qpos[3] = 1.0
mujoco.mj_kinematics(m, d)
out = {"geoms": [], "body_pos_zero": {}}
for g in range(m.ngeom):
    name = mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_GEOM, g) or ""
    if not (m.geom_contype[g] or m.geom_conaffinity[g] or name == "paddle_face"):
        continue
    b = m.geom_bodyid[g]
    out["geoms"].append({"name": name, "body": mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_BODY, b),
                         "type": int(m.geom_type[g]), "size": m.geom_size[g].tolist(),
                         "pos": m.geom_pos[g].tolist(), "quat": m.geom_quat[g].tolist()})
for b in range(1, m.nbody):
    out["body_pos_zero"][mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_BODY, b)] = np.round(d.xpos[b], 5).tolist()
body = lambda i: mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_BODY, int(i))  # noqa: E731
out["exclude"] = [[body(sig // 65536), body(sig % 65536)] for sig in m.exclude_signature]  # body-pair exclusions
paddle = m.body("paddle").id
out["paddle"] = {"parent": mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_BODY, m.body_parentid[paddle]),
                 "pos": m.body_pos[paddle].tolist(), "quat": m.body_quat[paddle].tolist()}
open(sys.argv[1], "w").write(json.dumps(out, indent=1))
print(len(out["geoms"]), "geoms ->", sys.argv[1])
