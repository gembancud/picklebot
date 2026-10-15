"""Initial checkpoint for a residual executor (Stage 5C, D-086).

Copies a runner checkpoint (the frozen executor's own, so the observation normaliser and critic are warm) and zeroes
the actor's output layer, so the residual starts at exactly zero (tanh(0) = 0: the frozen executor's behaviour), with
the action-noise std set to --std on every output.

Usage: python scripts/residual_init.py BASE.pt OUT.pt [--std 0.1]
"""
import argparse

import torch

ap = argparse.ArgumentParser()
ap.add_argument("base")
ap.add_argument("out")
ap.add_argument("--std", type=float, default=0.1)
a = ap.parse_args()
sd = torch.load(a.base, map_location="cpu", weights_only=False)
act = sd["actor_state_dict"]
last = max(int(k.split(".")[1]) for k in act if k.startswith("mlp.") and k.endswith(".weight"))
act[f"mlp.{last}.weight"].zero_()
act[f"mlp.{last}.bias"].zero_()
act["distribution.std_param"].fill_(a.std)
sd["iter"] = 0
torch.save(sd, a.out)
print(f"zeroed mlp.{last}, std {a.std} -> {a.out}")
