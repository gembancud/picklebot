"""Merge residual specialists into one residual executor by distillation in residual space (Stage 5C, D-088).

All policies here act as residuals around the same frozen executor (ResidualLatentAction, RES_BASE): a residual of
zero is the base. The student starts at zero (scripts/residual_init.py). In ball episodes of the listed families the
target is that specialist's residual; everywhere else (other families, move-to-spot episodes, ghost swings) the target
is zero, i.e. the base's own behaviour. Rollouts are DAgger on the student's states. Loss, per state:
    |lam_r tanh(a_lat) - lam_r tanh(a_t,lat)|^2 (prior sigmas) + |wrist_r tanh(a_w) - wrist_r tanh(a_t,w)|^2 (mean),
which the student can match exactly, so where no specialist applies it reproduces the base.

Usage (picklebot-mj venv):
    python scripts/residual_merge.py --run-name s5c-22-merge-volley --init INIT.pt --task Picklebot-Latent-Court-Res2-G1
        --specialist volley_forehand,volley_backhand=CK [--envs 4096] [--max-seconds 3600] [--early-stop 0.03]
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import time
from dataclasses import asdict
from datetime import datetime

import torch
from tensordict import TensorDict

import mjlab.tasks  # noqa: F401
from mjlab.envs import ManagerBasedRlEnv
from mjlab.rl import MjlabOnPolicyRunner, RslRlVecEnvWrapper
from mjlab.tasks.registry import load_env_cfg, load_rl_cfg

from picklebot_mj import seeds

STEPS = 24


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-name", required=True)
    ap.add_argument("--init", required=True, help="zero-residual start (scripts/residual_init.py)")
    ap.add_argument("--task", default="Picklebot-Latent-Court-Res2-G1")
    ap.add_argument("--specialist", action="append", default=[], help="FAMILIES=CK (same residual space)")
    ap.add_argument("--envs", type=int, default=4096)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--buffer", type=int, default=2)
    ap.add_argument("--epochs", type=int, default=2)
    ap.add_argument("--batch", type=int, default=16384)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--max-seconds", type=float, default=3600.0)
    ap.add_argument("--early-stop", type=float, default=0.03,
                    help="stop once the specialist-state loss improved by less than this fraction over 100 iterations")
    ap.add_argument("--save-every", type=int, default=50)
    ap.add_argument("--log-root", default="artifacts/train/logs/picklebot_return_stand")
    args = ap.parse_args()
    assert args.seed in seeds.TRAIN_SEEDS, "training must use training seeds"

    cfg = load_env_cfg(args.task)
    cfg.scene.num_envs, cfg.seed = args.envs, args.seed
    env = ManagerBasedRlEnv(cfg=cfg, device="cuda")
    agent = load_rl_cfg(args.task)
    venv = RslRlVecEnvWrapper(env, clip_actions=agent.clip_actions)
    rl = asdict(agent)
    runner = MjlabOnPolicyRunner(venv, copy.deepcopy(rl), device="cuda")
    runner.load(args.init, load_cfg={"actor": True, "critic": True}, strict=True, map_location="cuda")
    actor = runner.alg.actor
    term = env.action_manager.get_term("latent")
    ball = env.action_manager.get_term("ball")
    L, lam_r, wr = int(term.cfg.latent), float(term.cfg.lam_r), float(term.cfg.wrist_r)
    scale = torch.cat([torch.full((L,), lam_r), torch.full((term._action_dim - L,), wr)]).cuda()
    from picklebot_mj.feeds import FAMILY_NAMES
    specs = []
    for spec in args.specialist:
        fams, ck = spec.split("=", 1)
        r = MjlabOnPolicyRunner(venv, copy.deepcopy(rl), device="cuda")
        r.load(ck, load_cfg={"actor": True}, strict=True, map_location="cuda")
        t = r.alg.actor.eval()
        for p in t.parameters():
            p.requires_grad_(False)
        specs.append((torch.tensor([f in fams.split(",") for f in FAMILY_NAMES], device="cuda"), t))
    opt = torch.optim.Adam(actor.parameters(), lr=args.lr)
    out = os.path.join(args.log_root, datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + "_" + args.run_name)
    os.makedirs(out, exist_ok=True)
    env.reset()
    obs = venv.get_observations()
    bufs, log, t0, it = [], [], time.time(), 0
    while True:
        O, Y, S = [], [], []
        with torch.no_grad():
            for _ in range(STEPS):
                actor.update_normalization(obs)
                y = torch.zeros(args.envs, term._action_dim, device="cuda")  # tanh(target): zero = the base
                spec_m = torch.zeros(args.envs, dtype=torch.bool, device="cuda")
                move = ball.drill.move_ep if getattr(ball, "drill", None) is not None else torch.zeros_like(spec_m)
                for fmask, t in specs:
                    m = fmask[ball.family] & ~move
                    y = torch.where(m.unsqueeze(-1), torch.tanh(t(obs)), y)
                    spec_m |= m
                O.append(obs["actor"].clone())
                Y.append(y)
                S.append(spec_m)
                obs, _, _, _ = venv.step(actor(obs))
        bufs = (bufs + [(torch.cat(O), torch.cat(Y), torch.cat(S))])[-args.buffer:]
        tot = {"loss_spec": torch.zeros((), device="cuda"), "loss_base": torch.zeros((), device="cuda")}
        n = 0
        for _ in range(args.epochs):
            for o_, y_, s_ in bufs:
                perm = torch.randperm(len(o_), device="cuda")
                for i in range(0, len(o_), args.batch):
                    idx = perm[i:i + args.batch]
                    a = actor(TensorDict({"actor": o_[idx]}, batch_size=[len(idx)]))
                    err = (((torch.tanh(a) - y_[idx]) * scale) ** 2).mean(-1)
                    loss = err.mean()
                    opt.zero_grad()
                    loss.backward()
                    torch.nn.utils.clip_grad_norm_(actor.parameters(), 1.0)
                    opt.step()
                    sm = s_[idx].float()
                    with torch.no_grad():
                        tot["loss_spec"] += (err * sm).sum() / sm.sum().clamp(min=1)
                        tot["loss_base"] += (err * (1 - sm)).sum() / (1 - sm).sum().clamp(min=1)
                    n += 1
        it += 1
        row = {"it": it, **{k: round(float(v) / max(n, 1), 6) for k, v in tot.items()},
               "spec_share": round(float(torch.cat(S).float().mean()), 3), "elapsed_s": round(time.time() - t0, 1)}
        log.append(row)
        print(json.dumps(row), flush=True)
        stop = time.time() - t0 > args.max_seconds
        if args.early_stop > 0 and len(log) > 100:
            old, new = log[-101]["loss_spec"], row["loss_spec"]
            if old > 0 and (old - new) / old < args.early_stop:
                stop = True
                print(json.dumps({"early_stop": "specialist loss plateau", "it": it}), flush=True)
        if it % args.save_every == 0 or stop:
            torch.save({"actor_state_dict": actor.state_dict(), "critic_state_dict": runner.alg.critic.state_dict(),
                        "optimizer_state_dict": runner.alg.optimizer.state_dict(), "iter": it, "infos": None},
                       os.path.join(out, f"model_{it}.pt"))
        if stop:
            break
    json.dump({"args": vars(args), "log": log}, open(os.path.join(out, "merge_log.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
