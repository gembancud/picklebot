"""Mirror retargeted G1 motion CSVs left <-> right (Stage 5C controller retrain, D-077).

CSV rows: root position (3), root quaternion xyzw (4), the 29 G1 joint angles (mjlab order). Mirroring is about
the robot's sagittal (x-z) plane: y -> -y for the root position; the root rotation is reflected (w, x, y, z) ->
(w, -x, y, -z); left and right joints swap, and roll and yaw joints change sign (pitch, knee and elbow keep it).
Every derived quantity (body poses, velocities) is recomputed from these by csv_to_npz_local.py.

Usage: python scripts/motion/mirror_g1_csv.py IN_DIR OUT_DIR STEM [STEM ...]   (writes OUT_DIR/STEM_mirror.csv)
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

G1_JOINTS = (
    "left_hip_pitch_joint", "left_hip_roll_joint", "left_hip_yaw_joint", "left_knee_joint", "left_ankle_pitch_joint",
    "left_ankle_roll_joint", "right_hip_pitch_joint", "right_hip_roll_joint", "right_hip_yaw_joint", "right_knee_joint",
    "right_ankle_pitch_joint", "right_ankle_roll_joint", "waist_yaw_joint", "waist_roll_joint", "waist_pitch_joint",
    "left_shoulder_pitch_joint", "left_shoulder_roll_joint", "left_shoulder_yaw_joint", "left_elbow_joint",
    "left_wrist_roll_joint", "left_wrist_pitch_joint", "left_wrist_yaw_joint", "right_shoulder_pitch_joint",
    "right_shoulder_roll_joint", "right_shoulder_yaw_joint", "right_elbow_joint", "right_wrist_roll_joint",
    "right_wrist_pitch_joint", "right_wrist_yaw_joint")


def _partner(name: str) -> str:
    if name.startswith("left_"):
        return "right_" + name[5:]
    if name.startswith("right_"):
        return "left_" + name[6:]
    return name


PERM = np.array([G1_JOINTS.index(_partner(j)) for j in G1_JOINTS])
SIGN = np.array([-1.0 if ("_roll_" in j or "_yaw_" in j) else 1.0 for j in G1_JOINTS])


def mirror_rows(q: np.ndarray) -> np.ndarray:
    """q: [T, 36] = root pos (3), root quat xyzw (4), joints (29). Returns the mirrored motion."""
    out = q.copy()
    out[:, 1] = -q[:, 1]  # root y
    x, y, z, w = q[:, 3], q[:, 4], q[:, 5], q[:, 6]
    out[:, 3], out[:, 4], out[:, 5], out[:, 6] = -x, y, -z, w
    joints = q[:, 7:]
    out[:, 7:] = joints[:, PERM] * SIGN
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("in_dir")
    ap.add_argument("out_dir")
    ap.add_argument("stems", nargs="+")
    a = ap.parse_args()
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for s in a.stems:
        q = np.loadtxt(Path(a.in_dir) / f"{s}.csv", delimiter=",")
        np.savetxt(out / f"{s}_mirror.csv", mirror_rows(q), delimiter=",")
        print(f"{s}: {len(q)} frames -> {s}_mirror.csv")


if __name__ == "__main__":
    main()
