"""Where does an H4 environment step spend its time? (D-065 throughput work)

Steps TASK with zero actions (no policy, no PPO) and reports:
- env steps/s at the given env count;
- the top Python functions by cumulative and own time (cProfile);
- CUDA synchronisations triggered from Python (torch.cuda.synchronize / .item / host copies), counted by the
  torch profiler as cudaStreamSynchronize / cudaMemcpy calls per step.

Usage (picklebot-mj venv):
    python scripts/profile_env_step.py [--task Picklebot-Latent-Drill3-Footwork-G1] [--envs 4096] [--steps 60]
"""

from __future__ import annotations

import argparse
import cProfile
import io
import pstats
import time

import torch

import mjlab.tasks  # noqa: F401
from mjlab.envs import ManagerBasedRlEnv
from mjlab.tasks.registry import load_env_cfg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", default="Picklebot-Latent-Drill3-Footwork-G1")
    ap.add_argument("--envs", type=int, default=4096)
    ap.add_argument("--steps", type=int, default=60)
    ap.add_argument("--top", type=int, default=30)
    a = ap.parse_args()
    cfg = load_env_cfg(a.task)
    cfg.scene.num_envs = a.envs
    env = ManagerBasedRlEnv(cfg, device="cuda")
    env.reset()
    act = torch.zeros(a.envs, env.action_manager.total_action_dim, device="cuda")
    for _ in range(20):
        env.step(act)
    torch.cuda.synchronize()
    t0 = time.time()
    for _ in range(a.steps):
        env.step(act)
    torch.cuda.synchronize()
    dt = time.time() - t0
    print(f"envs {a.envs}: {a.envs * a.steps / dt:.0f} env-steps/s ({dt / a.steps * 1000:.1f} ms per step)")

    pr = cProfile.Profile()
    pr.enable()
    for _ in range(a.steps):
        env.step(act)
    torch.cuda.synchronize()
    pr.disable()
    for key in ("cumulative", "tottime"):
        s = io.StringIO()
        pstats.Stats(pr, stream=s).sort_stats(key).print_stats(a.top)
        print(f"==== cProfile by {key} ====")
        print("\n".join(line for line in s.getvalue().splitlines() if line.strip())[:6000])

    with torch.profiler.profile(activities=[torch.profiler.ProfilerActivity.CPU,
                                            torch.profiler.ProfilerActivity.CUDA]) as prof:
        for _ in range(10):
            env.step(act)
        torch.cuda.synchronize()
    ev = prof.key_averages()
    syncs = {e.key: e.count for e in ev if "Synchronize" in e.key or "Memcpy" in e.key or "item" in e.key}
    print("==== sync-like calls per 10 steps ====")
    for k, v in sorted(syncs.items(), key=lambda kv: -kv[1]):
        print(f"{v:6d}  {k}")
    print("==== top CUDA kernels by device time ====")
    print(ev.table(sort_by="self_cuda_time_total", row_limit=15))
    env.close()


if __name__ == "__main__":
    main()
