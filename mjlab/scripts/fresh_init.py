"""Copy a checkpoint with a fresh optimizer and a std floor (the restart after the KL check, 2026-10-28).

The weights, the normalizer and the iteration count are kept. Adam's moments and step counts are dropped (its state is
emptied; the parameter groups stay so the runner can load it), and every actor std below --std-min is raised to it.

Usage: fresh_init.py SRC DST [--std-min 0.1]
"""

import argparse

import torch

ap = argparse.ArgumentParser()
ap.add_argument("src")
ap.add_argument("dst")
ap.add_argument("--std-min", type=float, default=0.1)
a = ap.parse_args()

sd = torch.load(a.src, map_location="cpu", weights_only=False)
std = sd["actor_state_dict"]["distribution.std_param"]
low = (std < a.std_min).nonzero().flatten().tolist()
print(f"raising std of outputs {low} from {[round(float(std[i]), 4) for i in low]} to {a.std_min}")
std.clamp_(min=a.std_min)
opt = sd["optimizer_state_dict"]
print(f"dropping Adam state for {len(opt['state'])} tensors (lr was {opt['param_groups'][0]['lr']:.1e})")
opt["state"] = {}
torch.save(sd, a.dst)
