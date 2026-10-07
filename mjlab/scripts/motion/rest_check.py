"""Retarget the BVH rest pose (T-pose) and print the G1 joint angles: a sanity check of tennis_retarget's offsets.

Expected: the G1 T-pose (tennis_retarget.TPOSE): shoulders rolled out 90 deg, elbows +90 deg (straight), rest ~0.
Usage (GMR venv): python scripts/motion/rest_check.py BVH
"""

import sys
import tempfile

import mujoco as mj
import numpy as np
from scipy.spatial.transform import Rotation as R

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import tennis_retarget as tr  # noqa: E402

m, q = tr.retarget_rest(sys.argv[1], tempfile.mktemp(suffix=".json"))
print("pelvis quat (wxyz):", np.round(q[3:7], 3), " yaw deg:",
      round(float(R.from_quat(q[3:7], scalar_first=True).as_euler("zyx", degrees=True)[0]), 1))
for j in range(1, m.njnt):
    print(f"  {mj.mj_id2name(m, mj.mjtObj.mjOBJ_JOINT, j):28s} {np.degrees(q[6 + j]):7.1f}")
