"""Copy a checkpoint with a fresh optimizer and a std floor (the restart after the KL check, 2026-10-28).

The weights, the normalizer and the iteration count are kept. Adam's moments and step counts are dropped (its state is
emptied; the parameter groups stay so the runner can load it), and every actor std below --std-min is raised to it.

--normalizer-count N (audit 2026-10-28, training loop C3): set the actor and critic observation normalizers' sample
count to N (their mean and variance are kept). The lineage's count is about 1.45e10, so a 4,000-iteration run moves
the statistics by only about 8 %; with N = 1e7 they track the current task within a few iterations. Off by default.

Usage: fresh_init.py SRC DST [--std-min 0.1] [--normalizer-count N]
"""

import argparse

import torch

ap = argparse.ArgumentParser()
ap.add_argument("src")
ap.add_argument("dst")
ap.add_argument("--std-min", type=float, default=0.1)
ap.add_argument("--normalizer-count", type=float, default=None)
a = ap.parse_args()

sd = torch.load(a.src, map_location="cpu", weights_only=False)
std = sd["actor_state_dict"]["distribution.std_param"]
low = (std < a.std_min).nonzero().flatten().tolist()
print(f"raising std of outputs {low} from {[round(float(std[i]), 4) for i in low]} to {a.std_min}")
std.clamp_(min=a.std_min)
opt = sd["optimizer_state_dict"]
print(f"dropping Adam state for {len(opt['state'])} tensors (lr was {opt['param_groups'][0]['lr']:.1e})")
opt["state"] = {}
if a.normalizer_count is not None:
    for part in ("actor_state_dict", "critic_state_dict"):
        c = sd[part].get("obs_normalizer.count")
        if c is not None:
            print(f"{part} normalizer count {float(c):.3g} -> {a.normalizer_count:.3g}")
            c.fill_(a.normalizer_count)
torch.save(sd, a.dst)
# audit 2026-10-28: keep the training run's params/ (env.yaml, agent.yaml) beside the copy, so evaluation's interface
# guard (picklebot_mj/eval_meta.py) can check reads of it
import os, shutil  # noqa: E401, E402
src_p, dst_p = os.path.join(os.path.dirname(a.src), "params"), os.path.join(os.path.dirname(a.dst), "params")
if os.path.isdir(src_p) and not os.path.exists(dst_p):
    shutil.copytree(src_p, dst_p)
    print(f"copied {src_p} -> {dst_p}")
