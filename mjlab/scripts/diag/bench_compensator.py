"""Stage 5F step 0 (D-109 item 2): speed of the per-control-step ball compensator at training scale.

Times planner.compensate on N envs with ages drawn from the training support (ball lag 0-2 control steps = 0-8 substeps
of 5 ms; half the envs clean), after compile warm-up. Reports ms per call and the share of a control step's budget.
Usage: python scripts/diag/bench_compensator.py [--envs 12288] [--calls 200] [--json OUT]
"""
import argparse
import json
import time

import torch

from picklebot_mj.planner import compensate

ap = argparse.ArgumentParser()
ap.add_argument("--envs", type=int, default=12288)
ap.add_argument("--calls", type=int, default=200)
ap.add_argument("--json", default=None)
a = ap.parse_args()
g = torch.Generator(device="cuda").manual_seed(4210011)
n = a.envs
pos = torch.stack([torch.rand(n, device="cuda", generator=g) * 6 - 6, torch.rand(n, device="cuda", generator=g) * 6 - 3,
                   torch.rand(n, device="cuda", generator=g) * 1.5 + 0.2], -1)
vel = torch.randn(n, 3, device="cuda", generator=g) * torch.tensor([6.0, 2.0, 3.0], device="cuda")
lag = torch.randint(0, 3, (n,), device="cuda", generator=g) * 4
lag = torch.where(torch.rand(n, device="cuda", generator=g) < 0.5, torch.zeros_like(lag), lag)
for _ in range(20):
    compensate(pos, vel, lag, 8)
torch.cuda.synchronize()
t0 = time.perf_counter()
for _ in range(a.calls):
    compensate(pos, vel, lag, 8)
torch.cuda.synchronize()
ms = 1000 * (time.perf_counter() - t0) / a.calls
out = {"envs": n, "calls": a.calls, "max_substeps": 8, "ms_per_call": round(ms, 3), "seed": 4210011}
print(json.dumps(out))
if a.json:
    json.dump(out, open(a.json, "w"), indent=1)
