"""List the source lines that force CUDA synchronisations during H4 environment steps (D-065 throughput work).

Uses torch.cuda.set_sync_debug_mode("warn"): every synchronising op warns; the warning's stack is attributed to the
innermost frame in picklebot_mj or mjlab, and counted per line.

Usage: python scripts/find_syncs.py [--task Picklebot-Latent-Drill3-Footwork-G1] [--envs 512] [--steps 10]
"""
import argparse
import collections
import traceback
import warnings

import torch

import mjlab.tasks  # noqa: F401
from mjlab.envs import ManagerBasedRlEnv
from mjlab.tasks.registry import load_env_cfg

ap = argparse.ArgumentParser()
ap.add_argument("--task", default="Picklebot-Latent-Drill3-Footwork-G1")
ap.add_argument("--envs", type=int, default=512)
ap.add_argument("--steps", type=int, default=10)
a = ap.parse_args()
cfg = load_env_cfg(a.task)
cfg.scene.num_envs = a.envs
env = ManagerBasedRlEnv(cfg, device="cuda")
env.reset()
act = torch.zeros(a.envs, env.action_manager.total_action_dim, device="cuda")
for _ in range(5):
    env.step(act)
counts = collections.Counter()


def hook(message, category, filename, lineno, file=None, line=None):
    stack = traceback.extract_stack()[:-1]
    for fr in reversed(stack):
        if ("picklebot_mj" in fr.filename or "/mjlab/" in fr.filename) and "warnings" not in fr.filename:
            counts[f"{fr.filename.split('site-packages/')[-1].split('mjlab/mjlab/')[-1]}:{fr.lineno}  {fr.line}"] += 1
            return
    counts["<other>"] += 1


warnings.showwarning = hook
warnings.simplefilter("always")
torch.cuda.set_sync_debug_mode("warn")
for _ in range(a.steps):
    env.step(act)
torch.cuda.set_sync_debug_mode(0)
total = sum(counts.values())
print(f"{total} syncs in {a.steps} steps ({total / a.steps:.0f} per step)")
for k, v in counts.most_common(40):
    print(f"{v / a.steps:7.1f}/step  {k}")
env.close()
