"""Write TensorBoard events for distillation runs from their logs (they print one JSON line per iteration).

Usage: python scripts/distill_to_tb.py [RUN ...]   (default: every artifacts/train/student-*.log)
Events go to artifacts/train/logs/picklebot_return_stand/<RUN>/tb/ (rewritten each time, so it can be re-run
while a distillation is still going).
"""

import glob
import json
import os
import shutil
import sys

from torch.utils.tensorboard import SummaryWriter

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "artifacts", "train")


def convert(run: str) -> int:
    log = os.path.join(ROOT, f"{run}.log")
    out = os.path.join(ROOT, "logs", "picklebot_return_stand", run, "tb")
    shutil.rmtree(out, ignore_errors=True)
    w = SummaryWriter(out)
    n = 0
    for line in open(log, errors="ignore"):
        if not line.startswith('{"it"'):
            continue
        r = json.loads(line)
        for k in ("loss", "mse_move", "mse_hit", "beta"):
            if r.get(k) is not None and r[k] == r[k]:
                w.add_scalar(f"Distill/{k}", r[k], r["it"])
        n += 1
    w.close()
    return n


if __name__ == "__main__":
    runs = sys.argv[1:] or [os.path.basename(p)[:-4] for p in sorted(glob.glob(os.path.join(ROOT, "student-*.log")))]
    for r in runs:
        print(r, convert(r), "iterations")
