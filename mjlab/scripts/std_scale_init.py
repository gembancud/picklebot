"""Copy a checkpoint with its actor std scaled (panel round 45 screen, D-164).

The weights, normalizer, optimizer state and iteration count are kept; distribution.std_param is multiplied by
--scale. ScheduledPPO clamps the std up to PICKLEBOT_STD_MIN at start-up and after every step, so a run from the copy
must set PICKLEBOT_STD_MIN at or below the scaled values (round 45, architecture: else the cut is silently undone).
The training run's params/ directory is copied beside the result so the evaluation guard can check reads of it.

Usage: std_scale_init.py SRC DST --scale K
"""

import argparse
import os
import shutil

import torch

ap = argparse.ArgumentParser()
ap.add_argument("src")
ap.add_argument("dst")
ap.add_argument("--scale", type=float, required=True)
a = ap.parse_args()

sd = torch.load(a.src, map_location="cpu", weights_only=False)
std = sd["actor_state_dict"]["distribution.std_param"]
print(f"std min / median / max {float(std.min()):.4f} / {float(std.median()):.4f} / {float(std.max()):.4f} "
      f"-> x {a.scale}")
std.mul_(a.scale)
os.makedirs(os.path.dirname(a.dst) or ".", exist_ok=True)
torch.save(sd, a.dst)
src_p, dst_p = os.path.join(os.path.dirname(a.src), "params"), os.path.join(os.path.dirname(a.dst), "params")
if os.path.isdir(src_p) and not os.path.exists(dst_p):
    shutil.copytree(src_p, dst_p)
