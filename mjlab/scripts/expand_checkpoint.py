"""Expand an rsl_rl checkpoint's observation inputs for new trailing observation terms.

New input columns get zero first-layer weights and a (mean 0, var 1) normalizer prior, so
the expanded networks produce exactly the original outputs at first (the new inputs only
start to matter as training changes those weights). Adam moments for the first layer are
zero-padded the same way, so the optimizer state can be resumed. The iteration counter is kept.

Usage: python scripts/expand_checkpoint.py IN.pt OUT.pt --actor-dim 112 --critic-dim 127
"""

import argparse

import torch


def expand_net(sd, new_dim):
    w = sd["mlp.0.weight"]
    old = w.shape[1]
    extra = new_dim - old
    assert extra >= 0, (old, new_dim)
    sd["mlp.0.weight"] = torch.cat([w, torch.zeros(w.shape[0], extra, dtype=w.dtype)], 1)
    for k, fill in (("obs_normalizer._mean", 0.0), ("obs_normalizer._var", 1.0), ("obs_normalizer._std", 1.0)):
        v = sd[k]
        sd[k] = torch.cat([v, torch.full((v.shape[0], extra), fill, dtype=v.dtype)], 1)
    return old, extra


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--actor-dim", type=int, required=True)
    ap.add_argument("--critic-dim", type=int, required=True)
    a = ap.parse_args()
    ck = torch.load(a.src, map_location="cpu", weights_only=False)
    shapes = {}
    for key, dim in (("actor_state_dict", a.actor_dim), ("critic_state_dict", a.critic_dim)):
        old, extra = expand_net(ck[key], dim)
        shapes[(512, old)] = extra
    for st in ck["optimizer_state_dict"]["state"].values():
        for m in ("exp_avg", "exp_avg_sq"):
            t = st.get(m)
            if t is not None and t.dim() == 2 and tuple(t.shape) in shapes:
                st[m] = torch.cat([t, torch.zeros(t.shape[0], shapes[tuple(t.shape)], dtype=t.dtype)], 1)
    torch.save(ck, a.dst)
    print(f"expanded actor -> {a.actor_dim}, critic -> {a.critic_dim}: {a.dst}")


if __name__ == "__main__":
    main()
