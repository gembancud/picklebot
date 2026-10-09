"""Keep or drop clips of a multi-clip tracking npz by name (Stage 5B, D-051).

Usage: python scripts/motion/select_clips.py IN.npz OUT.npz --drop PREFIX [PREFIX ...]
"""

import argparse

import numpy as np

FIELDS = ("joint_pos", "joint_vel", "body_pos_w", "body_quat_w", "body_lin_vel_w", "body_ang_vel_w")

ap = argparse.ArgumentParser()
ap.add_argument("src")
ap.add_argument("dst")
ap.add_argument("--drop", nargs="+", required=True, help="clip-name prefixes to remove")
a = ap.parse_args()
d = np.load(a.src)
names, starts = d["clip_names"], d["clip_starts"]
ends = np.r_[starts[1:], len(d["joint_pos"])]
keep = [i for i, n in enumerate(names) if not any(str(n).startswith(p) for p in a.drop)]
idx = np.concatenate([np.arange(starts[i], ends[i]) for i in keep])
out = {k: d[k][idx] for k in FIELDS}
lengths = [ends[i] - starts[i] for i in keep]
out.update(fps=d["fps"], clip_names=names[keep], clip_starts=np.r_[0, np.cumsum(lengths)[:-1]])
if "clip_source" in d:
    out["clip_source"] = d["clip_source"][keep]
np.savez(a.dst, **out)
print(f"kept {len(keep)}/{len(names)} clips, {len(idx)} frames ({len(idx) / float(d['fps'][0]) / 60:.1f} min) -> {a.dst}")
