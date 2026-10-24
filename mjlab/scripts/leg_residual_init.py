"""D-152: a leg-residual parent from a 35-output residual checkpoint: 12 zero output rows (so the policy starts exactly
as the parent), their std set to the mean of the wrist dims' std, and the Adam moments padded with zeros.

Usage: python scripts/leg_residual_init.py --src CK --dst CK2
"""

import argparse

import torch

N_LEG = 12


def pad(t, n, value=0.0):
    extra = torch.full((n,) + tuple(t.shape[1:]), value, dtype=t.dtype)
    return torch.cat([t, extra], 0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--dst", required=True)
    args = ap.parse_args()
    sd = torch.load(args.src, map_location="cpu", weights_only=False)
    a = sd["actor_state_dict"]
    assert a["mlp.6.weight"].shape[0] == 35 and a["distribution.std_param"].shape == (35,), "expects 35 outputs"
    std = a["distribution.std_param"]
    a["distribution.std_param"] = torch.cat([std, std[32:35].mean().repeat(N_LEG)])
    a["mlp.6.weight"] = pad(a["mlp.6.weight"], N_LEG)
    a["mlp.6.bias"] = pad(a["mlp.6.bias"], N_LEG)
    st = sd["optimizer_state_dict"]["state"]
    for i in (0, 7, 8):  # Adam state of std_param, mlp.6.weight, mlp.6.bias (actor parameter order)
        for k in ("exp_avg", "exp_avg_sq"):
            assert st[i][k].shape[0] == 35, (i, k, st[i][k].shape)
            st[i][k] = pad(st[i][k], N_LEG)
    torch.save(sd, args.dst)
    print("ok", args.dst, tuple(a["mlp.6.weight"].shape), tuple(a["distribution.std_param"].shape))


if __name__ == "__main__":
    main()
