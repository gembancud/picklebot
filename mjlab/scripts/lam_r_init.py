"""D-154: a lam_r-2 parent from a lam_r-1 residual checkpoint. The latent output rows (weights and bias) and their
action std are halved, so tanh(a/2) * 2 ~ tanh(a) for the mean and the latent noise stays the same size: the policy
starts close to the parent and may then move up to twice as far. Wrist rows unchanged; Adam state unchanged.

Usage: python scripts/lam_r_init.py --src CK --dst CK2 [--latent 32] [--factor 0.5]
"""

import argparse

import torch


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--dst", required=True)
    ap.add_argument("--latent", type=int, default=32)
    ap.add_argument("--factor", type=float, default=0.5)
    args = ap.parse_args()
    sd = torch.load(args.src, map_location="cpu", weights_only=False)
    a = sd["actor_state_dict"]
    L, f = args.latent, args.factor
    assert a["mlp.6.weight"].shape[0] == 35, "expects the 35-output residual executor"
    a["mlp.6.weight"][:L] *= f
    a["mlp.6.bias"][:L] *= f
    a["distribution.std_param"][:L] *= f
    torch.save(sd, args.dst)
    print("ok", args.dst, "latent std mean", round(float(a["distribution.std_param"][:L].mean()), 3))


if __name__ == "__main__":
    main()
