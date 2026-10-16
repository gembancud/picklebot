"""Consolidate a residual executor into one lambda-3 executor (Stage 5D, D-092).

A residual executor (ResidualLatentAction) acts as the composite
    z = mu_p + lam sigma_p tanh(a_base) + lam_r sigma_p tanh(a_res),   wrist = wr tanh(a_base_w) + wr_r tanh(a_res_w),
the base and the residual each reading the actor observation with its own last action. Read in the plain lambda-3
action space, that composite is
    tanh(a) = clamp(tanh(a_base) + (lam_r / lam) tanh(a_res)),   tanh(a_w) = clamp(tanh(a_base_w) + (wr_r / wr) tanh(a_res_w)),
exact wherever the clamp (|tanh| < 1) is not hit. This script distils that composite into a single lambda-3 student by
DAgger on the student's own states (latent-space MSE in prior sigmas, as kickstart_h4.py --hit-loss latent), so the next
residual stage can start from it as its new base and its residual bound is reset.

Usage (picklebot-mj venv):
    python scripts/consolidate.py --run-name s5d-NN-consolidate --base BASE.pt --residual RES.pt --init INIT.pt
        [--task Picklebot-Latent-Court-Rally-L3-G1] [--lam-r 1.0] [--wrist-r 0.1] [--envs 4096] [--max-seconds 3600]
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


def actions_slice(env) -> slice:
    start = 0
    for n, d in zip(env.observation_manager.active_terms["actor"], env.observation_manager.group_obs_term_dim["actor"]):
        w = int(torch.tensor(d).prod())
        if n == "actions":
            return slice(start, start + w)
        start += w
    raise KeyError("actions")


class CompositeTeacher:
    """The residual executor read in the plain lambda-3 action space, each part with its own last action."""

    def __init__(self, base, res, n, dim, latent, lam, lam_r, wr, wr_r, sl, device):
        self.base, self.res, self.sl, self.L = base, res, sl, latent
        self.k_lat, self.k_w = lam_r / lam, wr_r / wr
        self.base_last = torch.zeros(n, dim, device=device)
        self.res_last = torch.zeros(n, dim, device=device)

    def __call__(self, x: torch.Tensor) -> torch.Tensor:
        xb, xr = x.clone(), x.clone()
        xb[:, self.sl], xr[:, self.sl] = self.base_last, self.res_last
        ab = self.base(TensorDict({"actor": xb}, batch_size=[len(x)]))
        ar = self.res(TensorDict({"actor": xr}, batch_size=[len(x)]))
        self.base_last, self.res_last = ab.clone(), ar.clone()
        t = torch.tanh(ab).clone()
        t[:, :self.L] = t[:, :self.L] + self.k_lat * torch.tanh(ar[:, :self.L])
        t[:, self.L:] = t[:, self.L:] + self.k_w * torch.tanh(ar[:, self.L:])
        return t.clamp(-0.999, 0.999)  # tanh of the equivalent lambda-3 action

    def reset(self, done: torch.Tensor):
        self.base_last[done] = 0.0
        self.res_last[done] = 0.0


def load_actor(path, venv, rl):
    r = MjlabOnPolicyRunner(venv, copy.deepcopy(rl), device="cuda")
    r.load(path, load_cfg={"actor": True}, strict=True, map_location="cuda")
    a = r.alg.actor.eval()
    for p in a.parameters():
        p.requires_grad_(False)
    return a


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-name", required=True)
    ap.add_argument("--base", required=True, help="the residual executor's frozen base (lambda-3 runner checkpoint)")
    ap.add_argument("--residual", required=True, help="the residual policy (runner checkpoint)")
    ap.add_argument("--init", required=True, help="student start (lambda-3 runner checkpoint; usually the base)")
    ap.add_argument("--task", default="Picklebot-Latent-Court-Rally-L3-G1")
    ap.add_argument("--lam-r", type=float, default=1.0)
    ap.add_argument("--wrist-r", type=float, default=0.1)
    ap.add_argument("--envs", type=int, default=4096)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--buffer", type=int, default=2)
    ap.add_argument("--epochs", type=int, default=2)
    ap.add_argument("--batch", type=int, default=16384)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--max-seconds", type=float, default=3600.0)
    ap.add_argument("--early-stop", type=float, default=0.03)
    ap.add_argument("--save-every", type=int, default=50)
    ap.add_argument("--log-root", default="artifacts/train/logs/picklebot_return_stand")
    a = ap.parse_args()
    assert a.seed in seeds.TRAIN_SEEDS, "training must use training seeds"
    cfg = load_env_cfg(a.task)
    cfg.scene.num_envs, cfg.seed = a.envs, a.seed
    env = ManagerBasedRlEnv(cfg=cfg, device="cuda")
    agent = load_rl_cfg(a.task)
    venv = RslRlVecEnvWrapper(env, clip_actions=agent.clip_actions)
    rl = asdict(agent)
    runner = MjlabOnPolicyRunner(venv, copy.deepcopy(rl), device="cuda")
    runner.load(a.init, load_cfg={"actor": True, "critic": True}, strict=True, map_location="cuda")
    actor = runner.alg.actor
    term = env.action_manager.get_term("latent")
    lam, L, wr = float(term.cfg.lam), int(term.cfg.latent), float(term.cfg.wrist_residual)
    dim = term._action_dim
    teacher = CompositeTeacher(load_actor(a.base, venv, rl), load_actor(a.residual, venv, rl), a.envs, dim, L, lam,
                               a.lam_r, wr, a.wrist_r, actions_slice(env), "cuda")
    scale = torch.cat([torch.full((L,), lam), torch.full((dim - L,), wr)]).cuda()
    opt = torch.optim.Adam(actor.parameters(), lr=a.lr)
    out = os.path.join(a.log_root, datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + "_" + a.run_name)
    os.makedirs(out, exist_ok=True)
    env.reset()
    obs = venv.get_observations()
    bufs, log, t0, it = [], [], time.time(), 0
    while True:
        O, Y, clip = [], [], 0.0
        with torch.no_grad():
            for _ in range(STEPS):
                actor.update_normalization(obs)
                y = teacher(obs["actor"])
                clip += float((y.abs() >= 0.999).float().mean())
                O.append(obs["actor"].clone())
                Y.append(y)
                obs, _, dones, _ = venv.step(actor(obs))
                teacher.reset(dones.bool())
        bufs = (bufs + [(torch.cat(O), torch.cat(Y))])[-a.buffer:]
        tot, n = torch.zeros((), device="cuda"), 0
        for _ in range(a.epochs):
            for o_, y_ in bufs:
                perm = torch.randperm(len(o_), device="cuda")
                for i in range(0, len(o_), a.batch):
                    idx = perm[i:i + a.batch]
                    act = actor(TensorDict({"actor": o_[idx]}, batch_size=[len(idx)]))
                    loss = (((torch.tanh(act) - y_[idx]) * scale) ** 2).mean()
                    opt.zero_grad()
                    loss.backward()
                    torch.nn.utils.clip_grad_norm_(actor.parameters(), 1.0)
                    opt.step()
                    tot += loss.detach()
                    n += 1
        it += 1
        row = {"it": it, "loss": round(float(tot) / max(n, 1), 6), "clamped_share": round(clip / STEPS, 4),
               "elapsed_s": round(time.time() - t0, 1)}
        log.append(row)
        print(json.dumps(row), flush=True)
        stop = time.time() - t0 > a.max_seconds
        if a.early_stop > 0 and len(log) > 100:
            old, new = log[-101]["loss"], row["loss"]
            if old > 0 and (old - new) / old < a.early_stop:
                stop = True
                print(json.dumps({"early_stop": "loss plateau", "it": it}), flush=True)
        if it % a.save_every == 0 or stop:
            torch.save({"actor_state_dict": actor.state_dict(), "critic_state_dict": runner.alg.critic.state_dict(),
                        "optimizer_state_dict": runner.alg.optimizer.state_dict(), "iter": it, "infos": None},
                       os.path.join(out, f"model_{it}.pt"))
        if stop:
            break
    json.dump({"args": vars(a), "log": log}, open(os.path.join(out, "consolidate_log.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
