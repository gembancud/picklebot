"""Distil the tracking teacher into the latent controller with DAgger (Stage 5B H1, D-050).

Rollouts run on the teacher's own task (multi-clip motion command, adaptive sampling, randomisation, terminations).
Each step the environment executes beta * a_teacher + (1 - beta) * a_student, where a_student = D(s, z), z ~ q(z|s,g)
(beta decays 1 -> 0 over the first --beta-frac of iterations); every visited state is labelled with the teacher's
deterministic action. The latent controller (picklebot_mj/latent.py) is trained on the last --buffer iterations with
    MSE(D(s, z_q), a_teacher) + w_smooth * |D(s_t, mu_t) - D(s_t-1, mu_t-1)|^2 + beta_kl * KL(q || p),
beta_kl annealed linearly from --kl-start to --kl-end over --iterations (PULSE: 0.01 -> 0.001).

Usage (picklebot-mj venv):
    python scripts/distill_latent.py --teacher CK --out DIR [--task Picklebot-Tracking-TennisLafan2-Huge-G1]
        [--iterations 2000] [--envs 4096] [--init PATH] [--start-it N] [--seed 1]
"""

from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import asdict

import torch

import mjlab.tasks  # noqa: F401
from mjlab.envs import ManagerBasedRlEnv
from mjlab.rl import RslRlVecEnvWrapper
from mjlab.tasks.registry import load_env_cfg, load_rl_cfg, load_runner_cls

from picklebot_mj import seeds
from picklebot_mj.latent import LatentController, kl_diag_gauss

STEPS = 24


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--teacher", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--task", default="Picklebot-Tracking-TennisLafan2-Huge-G1")
    ap.add_argument("--iterations", type=int, default=2000, help="schedule length (beta, KL anneal)")
    ap.add_argument("--start-it", type=int, default=0, help="continue a schedule (chained runs)")
    ap.add_argument("--init", default=None, help="continue from a latent-controller checkpoint")
    ap.add_argument("--envs", type=int, default=4096)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--beta-frac", type=float, default=0.2)
    ap.add_argument("--buffer", type=int, default=4)
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--batch", type=int, default=16384)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--kl-start", type=float, default=0.01)
    ap.add_argument("--kl-end", type=float, default=0.001)
    ap.add_argument("--smooth", type=float, default=0.005)
    ap.add_argument("--prior-rollout-frac", type=float, default=0.0,
                    help="fraction of envs whose rollout action comes from the prior alone (z = mu_p + sigma_p*eps) "
                         "instead of the encoder, so the prior is trained on states it visits itself (H2 follow-up 2)")
    ap.add_argument("--prior-bc", type=float, default=0.0,
                    help="weight of MSE(D(s, mu_p), a_teacher): the prior's own mean latent must also reproduce the "
                         "teacher (H2 follow-up 1; makes prior-only control a usable default)")
    ap.add_argument("--max-seconds", type=float, default=6900.0)
    ap.add_argument("--save-every", type=int, default=100)
    args = ap.parse_args()
    assert args.seed in seeds.TRAIN_SEEDS, "training must use training seeds"
    os.makedirs(args.out, exist_ok=True)

    cfg = load_env_cfg(args.task)
    cfg.scene.num_envs, cfg.seed = args.envs, args.seed
    env = ManagerBasedRlEnv(cfg=cfg, device="cuda")
    agent = load_rl_cfg(args.task)
    venv = RslRlVecEnvWrapper(env, clip_actions=agent.clip_actions)
    runner = load_runner_cls(args.task)(venv, asdict(agent), device="cuda")
    runner.load(args.teacher, load_cfg={"actor": True}, strict=True, map_location="cuda")
    teacher = runner.get_inference_policy(device="cuda")

    model = LatentController().cuda()
    opt = torch.optim.Adam(model.parameters(), lr=args.lr)
    if args.init:
        ck = torch.load(args.init, map_location="cuda", weights_only=False)
        model.load_state_dict(ck["model"])
        if "opt" in ck:
            opt.load_state_dict(ck["opt"])
    obs = venv.get_observations()
    prior_envs = torch.rand(args.envs, device="cuda") < args.prior_rollout_frac
    bufs = []
    log, t0 = [], time.time()
    it = args.start_it
    while it < args.iterations:
        frac = it / max(1, args.iterations)
        beta = max(0.0, 1.0 - frac / args.beta_frac)
        kl_w = args.kl_start + (args.kl_end - args.kl_start) * frac
        O, Y, D = [], [], []
        with torch.no_grad():
            for _ in range(STEPS):
                x = obs["actor"]
                model.norm.update(x)
                a_t = teacher(obs)
                a_s = model(x, sample=True)
                if args.prior_rollout_frac > 0:
                    a_s = torch.where(prior_envs.unsqueeze(-1), model.prior_action(x), a_s)
                O.append(x.clone())
                Y.append(a_t.clone())
                obs, _, dones, _ = venv.step(beta * a_t + (1.0 - beta) * a_s)
                D.append(dones.bool().clone())
        bufs.append((torch.stack(O), torch.stack(Y), torch.stack(D)))  # [T, N, ...]
        bufs = bufs[-args.buffer:]
        stats = {"mse": 0.0, "smooth": 0.0, "kl": 0.0}
        if args.prior_bc > 0:
            stats["prior_mse"] = 0.0
        n_steps = 0
        for _ in range(args.epochs):
            for O_, Y_, D_ in bufs:
                T, N = O_.shape[:2]
                flat_o, flat_y = O_.reshape(T * N, -1), Y_.reshape(T * N, -1)
                perm = torch.randperm(T * N, device="cuda")
                for i in range(0, T * N, args.batch):
                    idx = perm[i:i + args.batch]
                    o, y = flat_o[idx], flat_y[idx]
                    mu_q, ls_q = model.encode(o)
                    z = mu_q + torch.randn_like(mu_q) * ls_q.exp()
                    mu_p, ls_p = model.prior_dist(o)
                    mse = ((model.decode(o, z) - y) ** 2).mean()
                    kl = kl_diag_gauss(mu_q, ls_q, mu_p, ls_p).mean()
                    # Smoothness on consecutive steps of the same env with no reset in between.
                    t_idx, n_idx = idx // N, idx % N
                    ok = (t_idx > 0) & ~D_[(t_idx - 1).clamp(min=0), n_idx]
                    if ok.any():
                        prev = O_[t_idx[ok] - 1, n_idx[ok]]
                        a_now = model.decode(o[ok], mu_q[ok])
                        a_prev = model.decode(prev, model.encode(prev)[0])
                        smooth = ((a_now - a_prev) ** 2).mean()
                    else:
                        smooth = torch.zeros((), device="cuda")
                    loss = mse + args.smooth * smooth + kl_w * kl
                    if args.prior_bc > 0:
                        prior_mse = ((model.decode(o, mu_p) - y) ** 2).mean()
                        loss = loss + args.prior_bc * prior_mse
                        stats["prior_mse"] = stats.get("prior_mse", 0.0) + prior_mse.item()
                    opt.zero_grad()
                    loss.backward()
                    torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                    opt.step()
                    stats["mse"] += mse.item()
                    stats["smooth"] += smooth.item()
                    stats["kl"] += kl.item()
                    n_steps += 1
        it += 1
        row = {"it": it, "beta": round(beta, 3), "kl_w": round(kl_w, 5),
               **{k: round(v / max(1, n_steps), 5) for k, v in stats.items()},
               "elapsed_s": round(time.time() - t0, 1)}
        log.append(row)
        print(json.dumps(row), flush=True)
        stop = time.time() - t0 > args.max_seconds
        if it % args.save_every == 0 or it == args.iterations or stop:
            torch.save({"model": model.state_dict(), "opt": opt.state_dict(), "it": it, "args": vars(args)},
                       os.path.join(args.out, f"latent_{it}.pt"))
        if stop:
            print(json.dumps({"stopped": "wall-clock cap", "it": it}), flush=True)
            break
    json.dump({"args": vars(args), "log": log}, open(os.path.join(args.out, f"distill_log_{args.start_it}.json"), "w"),
              indent=1)


if __name__ == "__main__":
    main()
