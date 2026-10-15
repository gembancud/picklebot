"""Rescale a runner checkpoint's action-noise std on the latent dimensions (Stage 5C, D-083).

A policy moved to a wider latent barrier (lam_from -> lam_to) by kickstart distillation keeps the old std_param, so
PPO's exploration noise moves the latent lam_to / lam_from times further than before. This writes a copy with the
first --latent entries of distribution.std_param multiplied by lam_from / lam_to (wrist-residual entries unchanged).

Usage: python scripts/rescale_action_std.py IN.pt OUT.pt [--latent 32] [--lam-from 1] [--lam-to 3]
"""
import argparse

import torch

ap = argparse.ArgumentParser()
ap.add_argument("inp")
ap.add_argument("out")
ap.add_argument("--latent", type=int, default=32)
ap.add_argument("--lam-from", type=float, default=1.0)
ap.add_argument("--lam-to", type=float, default=3.0)
a = ap.parse_args()
sd = torch.load(a.inp, map_location="cpu", weights_only=False)
std = sd["actor_state_dict"]["distribution.std_param"]
before = std.clone()
std[:a.latent] *= a.lam_from / a.lam_to
torch.save(sd, a.out)
print(f"latent std mean {float(before[:a.latent].mean()):.3f} -> {float(std[:a.latent].mean()):.3f}; "
      f"wrist {float(std[a.latent:].mean()):.3f} unchanged -> {a.out}")
