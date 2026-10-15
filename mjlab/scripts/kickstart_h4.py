"""Kickstart the H4 executor's footwork from the flat walking teacher (Stage 5C, D-082).

Two-teacher policy distillation through the frozen latent controller (as distill_h4.py, D-057):
- in move-to-spot episodes the target is the walking teacher's joint action (`Picklebot-Teacher-Move-G1`; its
  observation is the executor's with the 35-d last-action term replaced by the last executed joint action);
- in every other episode (real balls, ghost swings) the target is the starting executor itself (a frozen copy of
  --init), so hitting is kept. Its joint target is computed with its own barrier --lam-self, so the student may use a
  wider barrier (the task's lambda) and still be asked for the same motion.

Both targets are in joint space: q = D(s, mu_p + lam sigma_p tanh(a_lat)) (+ wrist residual), loss
    mean over states of |q_student - q_target|^2 + w_lat * mean((lam * tanh(a_lat))^2).
With --hit-loss latent (D-084), ball episodes instead match the hitting teacher's latent and wrist command exactly:
    |lam tanh(a_lat) - lam_self tanh(a_self_lat)|^2 (prior sigmas, mean over dims) + |tanh(a_w) - tanh(a_self_w)|^2,
which the wider barrier can represent exactly, so the hitting motion is copied rather than approximated through the
decoder's joint outputs. --hit-teacher sets the hitting teacher separately from --init (default: --init).
With --recover (D-085), a ball episode switches to the walking teacher --recover-delay seconds after the robot's
first legal contact (or once the rally is dead): the walking teacher sees the robot, its recovery spot and a ball
parked as in move-to-spot episodes (ball inputs recomputed for the parked ball, the move episodes' rally flags), so
the executor learns to walk back to its recovery spot after every hit.
Rollouts are DAgger-style on the student's own states. During the first --beta-frac of the wall-clock budget, a
share beta (1 -> 0) of envs instead executes the starting executor's action converted to the student's barrier
(a = atanh(tanh(a_self) * lam_self / lam), the same latent), so the switch to a wider barrier does not start from
falls.

The result is saved as a runner checkpoint (actor trained, critic copied) under the return-stand experiment, so
h5c_eval.sh evaluates it and a PPO run can warm-start from it.

Usage (picklebot-mj venv):
    python scripts/kickstart_h4.py --run-name s5c-12-kickstart --init CK [--task Picklebot-Latent-Court-L3-G1]
        [--move-prob 0.5] [--envs 4096] [--max-seconds 6900]
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import sys
import time
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

import torch
from tensordict import TensorDict

import mjlab.tasks  # noqa: F401
from mjlab.envs import ManagerBasedRlEnv
from mjlab.rl import MjlabOnPolicyRunner, RslRlVecEnvWrapper
from mjlab.tasks.registry import load_env_cfg, load_rl_cfg

from picklebot_mj import seeds

sys.path.insert(0, str(Path(__file__).resolve().parent))
from distill_h4 import LOG_ROOT, STEPS, actions_slice, build_teacher, executed_joint_action  # noqa: E402

TASK = "Picklebot-Latent-Court-L3-G1"
TEACHER = "artifacts/train/logs/picklebot_return_stand/2026-10-06_10-30-12_teacher-move-01/model_15900.pt"


def joint_target(term, a: torch.Tensor, ctrl_obs: torch.Tensor, lam: float) -> torch.Tensor:
    """The latent action term's mapping at barrier `lam`, differentiable in a (teacher units)."""
    lat = term.cfg.latent
    mu, logstd = term.model.prior_dist(ctrl_obs)
    z = mu + lam * logstd.exp() * torch.tanh(a[:, :lat])
    q = term.model.decode(ctrl_obs, z)
    scale = term._scale[0] if torch.is_tensor(term._scale) else torch.full_like(q[0], float(term._scale))
    scale = scale.expand_as(q)
    resid = torch.zeros_like(q)
    resid[:, term.wrist] = term.cfg.wrist_residual * torch.tanh(a[:, lat:]) / scale[:, term.wrist]
    return q + resid


def convert(a: torch.Tensor, lat: int, lam_from: float, lam_to: float) -> torch.Tensor:
    """An action at barrier lam_from re-expressed at barrier lam_to with the same latent (wrist part unchanged)."""
    out = a.clone()
    t = torch.tanh(a[:, :lat]) * (lam_from / lam_to)
    out[:, :lat] = torch.atanh(t.clamp(-0.999999, 0.999999))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-name", required=True)
    ap.add_argument("--init", required=True, help="starting executor (also the hitting teacher by default)")
    ap.add_argument("--hit-teacher", default=None, help="hitting teacher checkpoint (default: --init)")
    ap.add_argument("--hit-loss", choices=["joint", "latent"], default="joint")
    ap.add_argument("--hit-weight", type=float, default=1.0)
    ap.add_argument("--recover", action="store_true", help="walking teacher after the hit in ball episodes (D-085)")
    ap.add_argument("--recover-delay", type=float, default=0.2, help="seconds after first contact")
    ap.add_argument("--teacher", default=TEACHER, help="walking teacher (move-to-spot episodes)")
    ap.add_argument("--task", default=TASK)
    ap.add_argument("--lam-self", type=float, default=1.0, help="barrier the starting executor was trained with")
    ap.add_argument("--move-prob", type=float, default=0.5)
    ap.add_argument("--envs", type=int, default=4096)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--buffer", type=int, default=4)
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--batch", type=int, default=16384)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--w-lat", type=float, default=1e-3)
    ap.add_argument("--beta-frac", type=float, default=0.2)
    ap.add_argument("--max-seconds", type=float, default=6900.0)
    ap.add_argument("--save-every", type=int, default=100)
    ap.add_argument("--log-root", default=LOG_ROOT)
    args = ap.parse_args()
    assert args.seed in seeds.TRAIN_SEEDS, "training must use training seeds"

    cfg = load_env_cfg(args.task)
    cfg.scene.num_envs, cfg.seed = args.envs, args.seed
    cfg.actions["ball"].move_prob = args.move_prob
    env = ManagerBasedRlEnv(cfg=cfg, device="cuda")
    agent = load_rl_cfg(args.task)
    venv = RslRlVecEnvWrapper(env, clip_actions=agent.clip_actions)
    rl = asdict(agent)
    runner = MjlabOnPolicyRunner(venv, copy.deepcopy(rl), device="cuda")
    runner.load(args.init, load_cfg={"actor": True, "critic": True}, strict=True, map_location="cuda")
    start_it = int(torch.load(args.init, map_location="cpu", weights_only=False).get("iter", 0))
    actor = runner.alg.actor
    self_teacher = copy.deepcopy(actor).eval()
    if args.hit_teacher:
        r2 = MjlabOnPolicyRunner(venv, copy.deepcopy(rl), device="cuda")
        r2.load(args.hit_teacher, load_cfg={"actor": True}, strict=True, map_location="cuda")
        self_teacher = r2.alg.actor.eval()
    for p in self_teacher.parameters():
        p.requires_grad_(False)
    term = env.action_manager.get_term("latent")
    ball = env.action_manager.get_term("ball")
    lam, lat = float(term.cfg.lam), int(term.cfg.latent)
    sl = actions_slice(env)
    obs_dim = venv.get_observations()["actor"].shape[1]
    t_obs_dim = obs_dim - (sl.stop - sl.start) + term.n_joint
    walker = build_teacher(args.teacher, t_obs_dim, term.n_joint, rl["actor"], "cuda")
    # Teacher-layout column ranges of the ball terms (the student's 35-d last action becomes 29-d).
    cols, start = {}, 0
    for nm, dm in zip(env.observation_manager.active_terms["actor"], env.observation_manager.group_obs_term_dim["actor"]):
        w = term.n_joint if nm == "actions" else int(torch.tensor(dm).prod())
        cols[nm] = slice(start, start + w)
        start += w
    assert start == t_obs_dim
    from picklebot_mj.tasks.move_drill import PARK_POS
    from picklebot_mj.tasks.return_stand import _rotate_inv
    park = torch.tensor(PARK_POS, device="cuda")
    robot = env.scene["robot"]
    since_hit = torch.zeros(args.envs, device="cuda")
    flags_move = torch.zeros(2, device="cuda")

    def parked_view(tx: torch.Tensor) -> torch.Tensor:
        """The walking teacher's observation with the ball parked as in move-to-spot episodes."""
        root = robot.data.root_link_pose_w
        paddle = robot.data.body_link_pose_w[:, ball.paddle_id, :3]
        pw = park + env.scene.env_origins
        out = tx.clone()
        out[:, cols["ball_pos"]] = _rotate_inv(root[:, 3:7], pw - root[:, :3])
        out[:, cols["ball_vel"]] = 0.0
        out[:, cols["ball_from_paddle"]] = _rotate_inv(root[:, 3:7], pw - paddle)
        out[:, cols["rally_flags"]] = flags_move
        return out
    opt = torch.optim.Adam(actor.parameters(), lr=args.lr)

    out = os.path.join(args.log_root, datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + "_" + args.run_name)
    os.makedirs(out, exist_ok=True)
    env.reset()
    obs = venv.get_observations()
    last_exec = torch.zeros(args.envs, term.n_joint, device="cuda")
    gen = torch.Generator(device="cuda").manual_seed(args.seed + 9137)
    bufs, log, t0 = [], [], time.time()
    it = start_it
    while True:
        el = time.time() - t0
        beta = max(0.0, 1.0 - el / max(1e-6, args.beta_frac * args.max_seconds))
        O, C, Y, M, A, rew_sum, done_sum, n_move, n_rec = [], [], [], [], [], 0.0, 0, 0, 0
        with torch.no_grad():  # the actor stays in train mode so its observation normaliser updates
            for _ in range(STEPS):
                x = obs["actor"]
                actor.update_normalization(obs)
                ctrl = term.controller_obs()
                move = ball.drill.move_ep.clone()
                tx = torch.cat([x[:, :sl.start], last_exec, x[:, sl.stop:]], dim=-1)
                if args.recover:
                    if move.any():  # the rally flags a move episode shows (closed rally)
                        flags_move = tx[move][:, cols["rally_flags"]].mean(0).round()
                    since_hit = torch.where(ball.hit_done & ~move, since_hit + env.step_dt, torch.zeros_like(since_hit))
                    rec = ~move & ((since_hit >= args.recover_delay) | ball.rules.dead)
                    tx = torch.where(rec.unsqueeze(-1), parked_view(tx), tx)
                    n_rec += int(rec.sum())
                    move = move | rec  # imitate the walking teacher here too
                y_walk = walker(TensorDict({"actor": tx}, batch_size=[args.envs]))
                a_self = self_teacher(obs)
                y_self = joint_target(term, a_self, ctrl, args.lam_self)
                O.append(x.clone())
                C.append(ctrl.clone())
                Y.append(torch.where(move.unsqueeze(-1), y_walk, y_self))
                M.append(move)
                A.append(a_self.clone())
                a = actor(obs)
                if beta > 0.0:
                    use = torch.rand(args.envs, generator=gen, device="cuda") < beta
                    a = torch.where(use.unsqueeze(-1), convert(a_self, lat, args.lam_self, lam), a)
                obs, rew, dones, _ = venv.step(a)
                last_exec = executed_joint_action(term).clone()
                last_exec[dones.bool()] = 0.0  # the action term resets its last action at an episode end
                rew_sum += float(rew.mean())
                done_sum += int(dones.sum())
                n_move += int(move.sum())
        bufs.append((torch.cat(O), torch.cat(C), torch.cat(Y), torch.cat(M), torch.cat(A)))
        bufs = bufs[-args.buffer:]
        stats, n = {"mse_move": 0.0, "mse_hit": 0.0, "lat": 0.0}, 0
        for _ in range(args.epochs):
            for o_, c_, y_, m_, s_ in bufs:
                perm = torch.randperm(len(o_), device="cuda")
                for i in range(0, len(o_), args.batch):
                    idx = perm[i:i + args.batch]
                    a = actor(TensorDict({"actor": o_[idx]}, batch_size=[len(idx)]))
                    q = joint_target(term, a, c_[idx], lam)
                    err = ((q - y_[idx]) ** 2).mean(-1)
                    mv = m_[idx].float()
                    if args.hit_loss == "latent":  # ball episodes: match the hitting teacher's latent and wrist exactly
                        at = s_[idx]
                        e_lat = ((lam * torch.tanh(a[:, :lat]) - args.lam_self * torch.tanh(at[:, :lat])) ** 2).mean(-1)
                        e_w = ((torch.tanh(a[:, lat:]) - torch.tanh(at[:, lat:])) ** 2).mean(-1)
                        err = torch.where(mv > 0, err, args.hit_weight * (e_lat + e_w))
                    lat_pen = ((lam * torch.tanh(a[:, :lat])) ** 2).mean()
                    loss = err.mean() + args.w_lat * lat_pen
                    opt.zero_grad()
                    loss.backward()
                    torch.nn.utils.clip_grad_norm_(actor.parameters(), 1.0)
                    opt.step()
                    stats["mse_move"] += float((err * mv).sum() / mv.sum().clamp(min=1))
                    stats["mse_hit"] += float((err * (1 - mv)).sum() / (1 - mv).sum().clamp(min=1))
                    stats["lat"] += lat_pen.item()
                    n += 1
        it += 1
        row = {"it": it, "beta": round(beta, 3), **{k: round(v / max(1, n), 5) for k, v in stats.items()},
               "move_share": round(n_move / (STEPS * args.envs), 3), "recover_share": round(n_rec / (STEPS * args.envs), 3),
               "reward_per_step": round(rew_sum / STEPS, 4),
               "episode_ends": done_sum, "elapsed_s": round(time.time() - t0, 1)}
        log.append(row)
        print(json.dumps(row), flush=True)
        stop = time.time() - t0 > args.max_seconds
        if it % args.save_every == 0 or stop:
            torch.save({"actor_state_dict": actor.state_dict(), "critic_state_dict": runner.alg.critic.state_dict(),
                        "optimizer_state_dict": runner.alg.optimizer.state_dict(), "iter": it, "infos": None},
                       os.path.join(out, f"model_{it}.pt"))
        if stop:
            print(json.dumps({"stopped": "wall-clock cap", "it": it}), flush=True)
            break
    json.dump({"args": vars(args), "log": log}, open(os.path.join(out, f"kickstart_log_{start_it}.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
