"""Distil specialist teachers into one (larger) student with DAgger (Stage 5, D-042).

Each episode is routed to one teacher by its type: move-to-spot episodes (ball term `drill.move_ep`)
to the walking teacher, all others to the hitting teacher. Every step, the environment executes
beta * teacher + (1 - beta) * student actions (beta decays from 1 to 0 over the first `--beta-frac`
of iterations), and every visited state is labelled with the routed teacher's deterministic action.
The student actor is trained by MSE on its deterministic action to the label, on the last
`--buffer` iterations of data. Its exploration std is set to the teachers' mean std. The student
is saved as an ordinary rsl_rl checkpoint (actor trained, critic untouched) so PPO can resume it;
the fine-tune step warms the critic up first.

Usage:
  python scripts/distill.py --move-teacher CK --hit-teacher CK --out DIR [--hidden 1024,512,256]
      [--iterations 600] [--envs 4096] [--move-prob 0.5] [--seed 1]
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import time
from dataclasses import asdict

import torch

import mjlab.tasks  # noqa: F401
from mjlab.envs import ManagerBasedRlEnv
from mjlab.rl import MjlabOnPolicyRunner, RslRlVecEnvWrapper
from mjlab.tasks.registry import load_env_cfg, load_rl_cfg

from picklebot_mj import seeds
from picklebot_mj.tasks import HIT_TEACHER_MIX, TASK_DRILL_MOVE

STEPS_PER_ITER = 24


def make_runner(venv, agent_cfg, device, checkpoint=None, hidden=None):
    cfg = copy.deepcopy(asdict(agent_cfg))
    if hidden is not None:
        cfg["actor"]["hidden_dims"] = tuple(hidden)
        cfg["critic"]["hidden_dims"] = tuple(hidden)
    runner = MjlabOnPolicyRunner(venv, cfg, device=device)
    if checkpoint is not None:
        runner.load(checkpoint, load_cfg={"actor": True}, strict=True, map_location=device)
    return runner


def build(args, num_envs, seed):
    cfg = load_env_cfg(TASK_DRILL_MOVE)
    cfg.scene.num_envs = num_envs
    cfg.seed = seed
    ball = cfg.actions["ball"]
    ball.seed = seed
    ball.move_prob = args.move_prob
    ball.feed_mix = HIT_TEACHER_MIX  # hit episodes use the hitting teacher's own feed mix
    ball.compile_ball = not args.no_compile
    env = ManagerBasedRlEnv(cfg=cfg, device="cuda")
    agent_cfg = load_rl_cfg(TASK_DRILL_MOVE)
    return env, RslRlVecEnvWrapper(env, clip_actions=agent_cfg.clip_actions), agent_cfg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--move-teacher", required=True)
    ap.add_argument("--hit-teacher", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--hidden", default="1024,512,256")
    ap.add_argument("--iterations", type=int, default=600)
    ap.add_argument("--envs", type=int, default=4096)
    ap.add_argument("--move-prob", type=float, default=0.5)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--beta-frac", type=float, default=0.4)
    ap.add_argument("--buffer", type=int, default=4, help="iterations of data kept for training")
    ap.add_argument("--epochs", type=int, default=4)
    ap.add_argument("--batch", type=int, default=16384)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--max-seconds", type=float, default=6900.0, help="wall-clock cap (loop rule: <= 2 h)")
    ap.add_argument("--save-every", type=int, default=100)
    ap.add_argument("--no-compile", action="store_true", help="skip torch.compile of the ball (tests)")
    args = ap.parse_args()
    assert args.seed in seeds.TRAIN_SEEDS, "training must use training seeds"
    os.makedirs(args.out, exist_ok=True)
    hidden = [int(h) for h in args.hidden.split(",")]

    env, venv, agent_cfg = build(args, args.envs, args.seed)
    dev = "cuda"
    t_move = make_runner(venv, agent_cfg, dev, args.move_teacher).get_inference_policy(device=dev)
    t_hit = make_runner(venv, agent_cfg, dev, args.hit_teacher).get_inference_policy(device=dev)
    student_runner = make_runner(venv, agent_cfg, dev, hidden=hidden)
    student = student_runner.alg.actor
    # Exploration std: mean of the teachers' (scalar-per-action std parameters).
    stds = [torch.load(c, map_location=dev, weights_only=False)["actor_state_dict"]["distribution.std_param"]
            for c in (args.move_teacher, args.hit_teacher)]
    with torch.no_grad():
        student.distribution.std_param.copy_((stds[0] + stds[1]) / 2)
    params = [p for n, p in student.named_parameters() if not n.startswith("distribution")]
    opt = torch.optim.Adam(params, lr=args.lr)
    term = env.action_manager.get_term("ball")

    obs = venv.get_observations()
    buf_obs, buf_lab, buf_move = [], [], []
    log = []
    t0 = time.time()
    for it in range(args.iterations):
        beta = max(0.0, 1.0 - it / max(1.0, args.beta_frac * args.iterations))
        it_obs, it_lab, it_move = [], [], []
        with torch.no_grad():  # not inference_mode: buffers and stored obs are reused with autograd
            for _ in range(STEPS_PER_ITER):
                mv = term.drill.move_ep.clone()
                a_t = torch.where(mv.unsqueeze(-1), t_move(obs), t_hit(obs))
                student.update_normalization(obs)
                a_s = student(obs)
                it_obs.append(obs["actor"].clone())
                it_lab.append(a_t.clone())
                it_move.append(mv)
                act = beta * a_t + (1.0 - beta) * a_s
                obs, _, _, _ = venv.step(act)
        buf_obs.append(torch.cat(it_obs))
        buf_lab.append(torch.cat(it_lab))
        buf_move.append(torch.cat(it_move))
        buf_obs, buf_lab, buf_move = buf_obs[-args.buffer:], buf_lab[-args.buffer:], buf_move[-args.buffer:]
        X, Y, M = torch.cat(buf_obs), torch.cat(buf_lab), torch.cat(buf_move)
        losses = []
        for _ in range(args.epochs):
            perm = torch.randperm(X.shape[0], device=dev)
            for i in range(0, X.shape[0], args.batch):
                idx = perm[i:i + args.batch]
                pred = student({"actor": X[idx]})
                loss = ((pred - Y[idx]) ** 2).mean()
                opt.zero_grad()
                loss.backward()
                torch.nn.utils.clip_grad_norm_(params, 1.0)
                opt.step()
                losses.append(loss.item())
        with torch.no_grad():
            pred = torch.cat([student({"actor": X[i:i + args.batch]}) for i in range(0, X.shape[0], args.batch)])
            err = ((pred - Y) ** 2).mean(-1)
            row = {"it": it, "beta": round(beta, 3), "loss": round(sum(losses) / len(losses), 5),
                   "mse_move": round(float(err[M].mean()) if M.any() else float("nan"), 5),
                   "mse_hit": round(float(err[~M].mean()) if (~M).any() else float("nan"), 5),
                   "elapsed_s": round(time.time() - t0, 1)}
        log.append(row)
        print(json.dumps(row), flush=True)
        if (it + 1) % args.save_every == 0 or it + 1 == args.iterations:
            student_runner.save(os.path.join(args.out, f"model_{it + 1}.pt"))
        if time.time() - t0 > args.max_seconds:
            student_runner.save(os.path.join(args.out, f"model_{it + 1}.pt"))
            print(json.dumps({"stopped": "wall-clock cap", "it": it + 1}), flush=True)
            break
    json.dump({"args": vars(args), "log": log}, open(os.path.join(args.out, "distill_log.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
