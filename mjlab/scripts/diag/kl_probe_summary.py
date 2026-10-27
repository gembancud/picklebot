"""Summarise the KL check (scripts/diag/kl_probe.sh): which action outputs carry the KL, and what the learning rate
would do without them. Outputs 0-31 are the latent, 32-34 the right wrist (roll, pitch, yaw)."""

import json
import sys

import numpy as np

DESIRED = 0.01


def load(path):
    return [json.loads(line) for line in open(path)]


def report(name, rows):
    mean = np.array([r["kl_mean_part"] for r in rows])
    std = np.array([r["kl_std_part"] for r in rows])
    per = mean + std
    tot = per.sum(1)
    share = per.mean(0) / per.mean(0).sum()
    order = np.argsort(-share)
    sd = np.array(rows[-1]["std"])
    print(f"== {name}: {len(rows)} updates, lr {rows[0]['lr_first']:.2e} -> {rows[-1]['lr_last']:.2e}")
    print(f"   KL per update (summed over outputs): median {np.median(tot):.4f}  (schedule cuts above {2 * DESIRED})")
    print(f"   rsl_rl's own kl_mean: median {np.median([r['kl_mean'] for r in rows]):.4f}")
    for i in order[:6]:
        print(f"   output {i:2d}: {100 * share[i]:5.1f} % of the KL (mean shift {mean[:, i].mean():.4f}, "
              f"std change {std[:, i].mean():.4f}), std {sd[i]:.4f}")
    rest = np.delete(per, order[:1], axis=1).sum(1)
    rest3 = np.delete(per, order[:3], axis=1).sum(1)
    print(f"   KL without the top output: median {np.median(rest):.4f}; without the top 3: {np.median(rest3):.4f}")
    return {"name": name, "updates": len(rows), "lr_first": rows[0]["lr_first"], "lr_last": rows[-1]["lr_last"],
            "kl_median": float(np.median(tot)), "share": share.tolist(), "std_last": sd.tolist(),
            "kl_median_without_top1": float(np.median(rest)), "kl_median_without_top3": float(np.median(rest3)),
            "top": [int(i) for i in order[:6]]}


if __name__ == "__main__":
    out = [report(p, load(p)) for p in sys.argv[1:-1]]
    json.dump(out, open(sys.argv[-1], "w"), indent=1)
