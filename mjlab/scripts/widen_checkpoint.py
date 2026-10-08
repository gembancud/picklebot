"""Widen an rsl_rl MLP checkpoint's hidden layers, function-preserving (Net2WiderNet-style).

New hidden units get small random incoming weights and zero outgoing weights, so the widened actor and critic produce
exactly the original outputs at first; training then uses the new units. Adam moments are zero-padded the same way
so the optimizer state can be resumed. Observation normalizers, the action std and the iteration counter are kept.

Usage: python scripts/widen_checkpoint.py IN.pt OUT.pt --hidden 1024 512 256 [--seed 1]
"""

import argparse

import torch


def widen_mlp(sd, new_hidden, gen, init_std=1e-2):
    """sd: an actor/critic state dict with mlp.{0,2,4,...} Linear layers. Returns {old_shape: new_shape}."""
    idx = sorted(int(k.split(".")[1]) for k in sd if k.startswith("mlp.") and k.endswith(".weight"))
    assert len(idx) == len(new_hidden) + 1, (idx, new_hidden)
    shapes = {}
    for li, i in enumerate(idx):
        w, b = sd[f"mlp.{i}.weight"], sd[f"mlp.{i}.bias"]
        out_old, in_old = w.shape
        out_new = new_hidden[li] if li < len(new_hidden) else out_old
        in_new = new_hidden[li - 1] if li > 0 else in_old
        assert out_new >= out_old and in_new >= in_old
        nw = torch.zeros(out_new, in_new, dtype=w.dtype)
        nw[:out_old, :in_old] = w
        # New units' incoming weights: small random (so they carry signal); the old units ignore new inputs
        # (zero columns), and the new inputs' outgoing weights into the next layer stay zero below.
        nw[out_old:, :in_old] = torch.randn(out_new - out_old, in_old, generator=gen, dtype=w.dtype) * init_std
        nb = torch.zeros(out_new, dtype=b.dtype)
        nb[:out_old] = b
        sd[f"mlp.{i}.weight"], sd[f"mlp.{i}.bias"] = nw, nb
        shapes[tuple(w.shape)] = tuple(nw.shape)
        shapes[tuple(b.shape)] = tuple(nb.shape)
    return shapes


def pad(t, shape):
    out = torch.zeros(shape, dtype=t.dtype)
    out[tuple(slice(0, s) for s in t.shape)] = t
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--hidden", type=int, nargs="+", required=True)
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()
    gen = torch.Generator().manual_seed(a.seed)
    ck = torch.load(a.src, map_location="cpu", weights_only=False)
    shapes = {}
    for key in ("actor_state_dict", "critic_state_dict"):
        for old, new in widen_mlp(ck[key], a.hidden, gen).items():
            assert shapes.get(old, new) == new, ("ambiguous shape", old)
            shapes[old] = new
    for st in ck["optimizer_state_dict"]["state"].values():
        for k in ("exp_avg", "exp_avg_sq"):
            if k in st and tuple(st[k].shape) in shapes:
                st[k] = pad(st[k], shapes[tuple(st[k].shape)])
    torch.save(ck, a.dst)
    print("widened", {str(k): v for k, v in shapes.items()}, "->", a.dst)


if __name__ == "__main__":
    main()
