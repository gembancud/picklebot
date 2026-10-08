"""Merge multi-clip tracking npz files into one, recording each clip's source (Stage 5B H0).

Usage: python scripts/motion/merge_motions.py OUT.npz IN0.npz IN1.npz ...
Adds `clip_source` (index of the input file for each clip), keeps `clip_starts` (offset) and `clip_names`.
"""

import sys

import numpy as np

FIELDS = ("joint_pos", "joint_vel", "body_pos_w", "body_quat_w", "body_lin_vel_w", "body_ang_vel_w")

out, ins = sys.argv[1], sys.argv[2:]
parts = [np.load(f) for f in ins]
fps = {float(p["fps"][0]) for p in parts}
assert len(fps) == 1, f"mixed frame rates {fps}"
merged = {k: np.concatenate([p[k] for p in parts]) for k in FIELDS}
starts, names, source, offset = [], [], [], 0
for i, p in enumerate(parts):
    s = p["clip_starts"] if "clip_starts" in p else np.array([0])
    starts.append(s + offset)
    names.append(p["clip_names"] if "clip_names" in p else np.array([f"src{i}"]))
    source.append(np.full(len(s), i))
    offset += len(p["joint_pos"])
merged.update(fps=parts[0]["fps"], clip_starts=np.concatenate(starts), clip_names=np.concatenate(names),
              clip_source=np.concatenate(source))
np.savez(out, **merged)
print(f"{len(merged['clip_starts'])} clips from {len(ins)} files, {offset} frames -> {out}")
