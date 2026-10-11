"""Distil the flat Drill 3 student into the H4 executor through the frozen latent controller (Stage 5B H4, D-057).

Rollouts run on the H4 task (`Picklebot-Latent-Drill3-G1`) with the H4 policy's deterministic action (DAgger with
beta = 0: the executor visits its own states from the start). Every visited state is labelled by the flat teacher
(S-D3-style-c by default), whose observation is the H4 actor observation with the 35-d last-action term replaced by
the last executed joint action in the teacher's units ((joint target - default) / scale), i.e. what the teacher's
own last action would have been had it produced the executed motion.

The H4 policy's output a = [a_lat, a_wrist] is pushed through the frozen controller exactly as the action term does,
    z = mu_p(s) + lam * sigma_p(s) * tanh(a_lat),   q = D(s, z) (+ wrist_residual * tanh(a_wrist) / scale on the wrist),
and trained by MSE(q, a_teacher) + w_lat * mean(a_lat^2) on the last --buffer iterations. Gradients flow through the
frozen prior and decoder into the policy only. So the executor learns the closest motion the human-motion decoder can
make to the teacher's, and its outputs stay inside the controller's barrier.

The result is saved as a runner checkpoint (actor trained, critic untouched) under the return-stand experiment, so
stage2_eval.sh / h4_eval.sh evaluate it and a PPO run can warm-start from it.

Usage (picklebot-mj venv):
    python scripts/distill_h4.py --run-name h4-02-distill [--teacher CK] [--envs 4096] [--max-seconds 6900]
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
from rsl_rl.models.mlp_model import MLPModel

from picklebot_mj import seeds

TASK = "Picklebot-Latent-Drill3-G1"
TEACHER = ("artifacts/train/logs/picklebot_return_stand/2026-10-08_22-42-14_student-drill3-style-c/"
           "model_10400.pt")
LOG_ROOT = "artifacts/train/logs/picklebot_return_stand"
STEPS = 24


def actions_slice(env) -> slice:
    """Columns of the 'actions' (last action) term in the actor observation."""
    names = env.observation_manager.active_terms["actor"]
    dims = env.observation_manager.group_obs_term_dim["actor"]
    start = 0
    for n, d in zip(names, dims):
        width = int(torch.tensor(d).prod())
        if n == "actions":
            return slice(start, start + width)
        start += width
    raise KeyError("no 'actions' term in the actor observation")


def build_teacher(path: str, obs_dim: int, out_dim: int, actor_cfg: dict, device: str) -> MLPModel:
    sd = torch.load(path, map_location=device, weights_only=False)["actor_state_dict"]
    ws = sorted((int(k.split(".")[1]), v.shape[0]) for k, v in sd.items() if k.startswith("mlp.") and k.endswith(".weight"))
    keep = ("activation", "obs_normalization", "distribution_cfg")  # the MLPModel arguments (no RNN/CNN parts)
    cfg = {k: copy.deepcopy(actor_cfg[k]) for k in keep}
    cfg["hidden_dims"] = tuple(n for _, n in ws[:-1])
    teacher = MLPModel(TensorDict({"actor": torch.zeros(1, obs_dim)}, batch_size=[1]), {"actor": ["actor"]}, "actor",
                       out_dim, **cfg).to(device)
    teacher.load_state_dict(sd, strict=True)
    teacher.eval()
    return teacher


def executed_joint_action(term) -> torch.Tensor:
    """The applied joint targets in the teacher's action units: (target - default) / scale."""
    return (term._processed_actions - term._offset) / term._scale


def predict_joint_action(term, a: torch.Tensor, ctrl_obs: torch.Tensor) -> torch.Tensor:
    """The action term's mapping, differentiable in a: joint action (teacher units) from the H4 output."""
    lat = term.cfg.latent
    mu, logstd = term.model.prior_dist(ctrl_obs)
    z = mu + term.cfg.lam * logstd.exp() * torch.tanh(a[:, :lat])
    q = term.model.decode(ctrl_obs, z)
    scale = term._scale[0] if torch.is_tensor(term._scale) else torch.full_like(q[0], float(term._scale))
    scale = scale.expand_as(q)  # per-joint scale, identical for every env
    resid = torch.zeros_like(q)
    resid[:, term.wrist] = term.cfg.wrist_residual * torch.tanh(a[:, lat:]) / scale[:, term.wrist]
    return q + resid


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-name", required=True)
    ap.add_argument("--teacher", default=TEACHER)
    ap.add_argument("--task", default=TASK)
    ap.add_argument("--envs", type=int, default=4096)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--buffer", type=int, default=4)
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--batch", type=int, default=16384)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--w-lat", type=float, default=1e-3)
    ap.add_argument("--init", default=None, help="continue from an H4 runner checkpoint")
    ap.add_argument("--max-iterations", type=int, default=100000)
    ap.add_argument("--max-seconds", type=float, default=6900.0)
    ap.add_argument("--save-every", type=int, default=100)
    ap.add_argument("--log-root", default=LOG_ROOT)
    args = ap.parse_args()
    assert args.seed in seeds.TRAIN_SEEDS, "training must use training seeds"

    cfg = load_env_cfg(args.task)
    cfg.scene.num_envs, cfg.seed = args.envs, args.seed
    env = ManagerBasedRlEnv(cfg=cfg, device="cuda")
    agent = load_rl_cfg(args.task)
    venv = RslRlVecEnvWrapper(env, clip_actions=agent.clip_actions)
    rl = asdict(agent)
    runner = MjlabOnPolicyRunner(venv, copy.deepcopy(rl), device="cuda")
    start_it = 0
    if args.init:
        runner.load(args.init, load_cfg={"actor": True, "critic": True}, strict=True, map_location="cuda")
        start_it = int(torch.load(args.init, map_location="cpu", weights_only=False).get("iter", 0))
    actor = runner.alg.actor
    term = env.action_manager.get_term("latent")
    sl = actions_slice(env)
    obs_dim = venv.get_observations()["actor"].shape[1]
    t_obs_dim = obs_dim - (sl.stop - sl.start) + term.n_joint
    teacher = build_teacher(args.teacher, t_obs_dim, term.n_joint, rl["actor"], "cuda")
    opt = torch.optim.Adam(actor.parameters(), lr=args.lr)

    out = os.path.join(args.log_root, datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + "_" + args.run_name)
    os.makedirs(out, exist_ok=True)
    env.reset()
    obs = venv.get_observations()
    last_exec = torch.zeros(args.envs, term.n_joint, device="cuda")
    bufs, log, t0 = [], [], time.time()
    it = start_it
    while it < start_it + args.max_iterations:
        O, C, Y, rew_sum, done_sum = [], [], [], 0.0, 0
        with torch.no_grad():  # actor stays in train mode so its observation normaliser updates
            for _ in range(STEPS):
                x = obs["actor"]
                actor.update_normalization(obs)
                ctrl = term.controller_obs()
                tx = torch.cat([x[:, :sl.start], last_exec, x[:, sl.stop:]], dim=-1)
                y = teacher(TensorDict({"actor": tx}, batch_size=[args.envs]))
                O.append(x.clone())
                C.append(ctrl.clone())
                Y.append(y.clone())
                obs, rew, dones, _ = venv.step(actor(obs))
                last_exec = executed_joint_action(term).clone()
                last_exec[dones.bool()] = 0.0  # the action term resets its last action at an episode end
                rew_sum += float(rew.mean())
                done_sum += int(dones.sum())
        bufs.append((torch.cat(O), torch.cat(C), torch.cat(Y)))
        bufs = bufs[-args.buffer:]
        stats, n = {"mse": 0.0, "lat_l2": 0.0}, 0
        for _ in range(args.epochs):
            for o_, c_, y_ in bufs:
                perm = torch.randperm(len(o_), device="cuda")
                for i in range(0, len(o_), args.batch):
                    idx = perm[i:i + args.batch]
                    a = actor(TensorDict({"actor": o_[idx]}, batch_size=[len(idx)]))
                    q = predict_joint_action(term, a, c_[idx])
                    mse = ((q - y_[idx]) ** 2).mean()
                    lat_l2 = (a[:, :term.cfg.latent] ** 2).mean()
                    loss = mse + args.w_lat * lat_l2
                    opt.zero_grad()
                    loss.backward()
                    torch.nn.utils.clip_grad_norm_(actor.parameters(), 1.0)
                    opt.step()
                    stats["mse"] += mse.item()
                    stats["lat_l2"] += lat_l2.item()
                    n += 1
        it += 1
        row = {"it": it, **{k: round(v / max(1, n), 5) for k, v in stats.items()},
               "reward_per_step": round(rew_sum / STEPS, 4), "episode_ends": done_sum,
               "elapsed_s": round(time.time() - t0, 1)}
        log.append(row)
        print(json.dumps(row), flush=True)
        stop = time.time() - t0 > args.max_seconds
        if it % args.save_every == 0 or stop or it == start_it + args.max_iterations:
            torch.save({"actor_state_dict": actor.state_dict(), "critic_state_dict": runner.alg.critic.state_dict(),
                        "optimizer_state_dict": runner.alg.optimizer.state_dict(), "iter": it, "infos": None},
                       os.path.join(out, f"model_{it}.pt"))
        if stop:
            print(json.dumps({"stopped": "wall-clock cap", "it": it}), flush=True)
            break
    json.dump({"args": vars(args), "log": log}, open(os.path.join(out, f"distill_log_{start_it}.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
