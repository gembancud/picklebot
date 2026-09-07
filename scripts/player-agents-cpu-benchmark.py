#!/usr/bin/env python3
"""Measure a small local actor update. This is not an RL training run."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import time

import torch


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--updates", type=int, default=200)
    parser.add_argument("--batch", type=int, default=2048)
    args = parser.parse_args()
    if args.updates < 1 or args.batch < 1:
        parser.error("Updates and batch must be positive.")
    torch.manual_seed(1100000)
    torch.set_num_threads(2)
    model = torch.nn.Sequential(torch.nn.Linear(54, 64), torch.nn.Tanh(),
                                torch.nn.Linear(64, 64), torch.nn.Tanh(), torch.nn.Linear(64, 12))
    optimizer = torch.optim.Adam(model.parameters(), lr=3e-4)
    inputs = torch.randn(args.batch, 54)

    def update():
        optimizer.zero_grad(set_to_none=True)
        model(inputs).square().mean().backward()
        optimizer.step()

    for _ in range(20):
        update()
    start = time.perf_counter()
    for _ in range(args.updates):
        update()
    seconds = time.perf_counter() - start
    report = {
        "createdUtc": datetime.now(timezone.utc).isoformat(),
        "probe": "CPU actor-shaped MLP update; not PPO and not trained playing strength",
        "sourceHash": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "python": platform.python_version(), "torch": torch.__version__,
        "device": "cpu", "threads": 2, "layers": [54, 64, 64, 12],
        "updates": args.updates, "batch": args.batch, "seconds": seconds,
        "samplesPerSecond": args.updates * args.batch / seconds,
        "mpsAvailableInThisProcess": torch.backends.mps.is_available(),
    }
    folder = Path(__file__).resolve().parents[1] / "artifacts/player-agents"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / ("cpu-throughput-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S") + ".json")
    with path.open("x") as output:
        json.dump(report, output, indent=2)
        output.write("\n")
    print(json.dumps(report, indent=2))
    print(path)


if __name__ == "__main__":
    main()
