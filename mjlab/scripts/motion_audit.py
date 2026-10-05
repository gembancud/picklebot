"""Stage 5 motion audit: which task terms touch base motion, and how far a checkpoint's robot moves.

1. Dumps every reward (weight, function, params), termination, command and event of a task.
2. Rolls out a checkpoint (deterministic, dev seed) and measures per robot episode:
   pelvis xy displacement from the episode start (max), pelvis xy path length, and per-foot
   xy path length, plus the per-feed contact rate split by the lateral offset of the feed.

Usage: python scripts/motion_audit.py --checkpoint PATH [--task Picklebot-Aim-All-G1] [--envs 1024]
           [--seconds 16] [--seed 4200070] [--json out.json]
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict

import torch

import mjlab.tasks  # noqa: F401
from mjlab.envs import ManagerBasedRlEnv
from mjlab.rl import MjlabOnPolicyRunner, RslRlVecEnvWrapper
from mjlab.tasks.registry import load_env_cfg, load_rl_cfg

from picklebot_mj import seeds


def _name(f):
    return getattr(f, "__name__", None) or type(f).__name__


def _short(v):
    s = repr(v)
    return s if len(s) < 160 else s[:157] + "..."


def dump_terms(cfg) -> dict:
    out = {"rewards": {}, "terminations": {}, "commands": {}, "events": {}, "curriculum": {}}
    for k, t in cfg.rewards.items():
        out["rewards"][k] = {"weight": t.weight, "func": _name(t.func), "params": _short(t.params)}
    for k, t in cfg.terminations.items():
        out["terminations"][k] = {"func": _name(t.func), "time_out": t.time_out, "params": _short(t.params)}
    for k, c in cfg.commands.items():
        out["commands"][k] = _short(c)
    for k, e in cfg.events.items():
        out["events"][k] = {"func": _name(e.func), "mode": e.mode, "params": _short(e.params)}
    for k, c in (cfg.curriculum or {}).items():
        out["curriculum"][k] = _short(c)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--task", default="Picklebot-Aim-All-G1")
    ap.add_argument("--envs", type=int, default=1024)
    ap.add_argument("--seconds", type=float, default=16.0)
    ap.add_argument("--seed", type=int, default=4200070)
    ap.add_argument("--json", default=None)
    args = ap.parse_args()
    assert args.seed in seeds.DEV_EVAL_SEEDS, "evaluation must use development seeds"

    cfg = load_env_cfg(args.task)
    terms = dump_terms(cfg)
    cfg.scene.num_envs = args.envs
    cfg.seed = args.seed
    cfg.actions["ball"].seed = args.seed
    cfg.observations["actor"].enable_corruption = False
    env = ManagerBasedRlEnv(cfg=cfg, device="cuda")
    agent_cfg = load_rl_cfg(args.task)
    venv = RslRlVecEnvWrapper(env, clip_actions=agent_cfg.clip_actions)
    runner = MjlabOnPolicyRunner(venv, asdict(agent_cfg), device="cuda")
    runner.load(args.checkpoint, load_cfg={"actor": True}, strict=True, map_location="cuda")
    policy = runner.get_inference_policy(device="cuda")

    robot = env.scene["robot"]
    names = robot.body_names
    pelvis = names.index("pelvis")
    feet = [names.index(n) for n in ("left_ankle_roll_link", "right_ankle_roll_link")]
    origins = env.scene.env_origins[:, :2]
    term = env.action_manager.get_term("ball")

    def xy(i):
        return robot.data.body_link_pos_w[:, i, :2] - origins

    obs = venv.get_observations()
    start = xy(pelvis).clone()
    prev_p, prev_f = start.clone(), [xy(f).clone() for f in feet]
    max_disp = torch.zeros(args.envs, device="cuda")
    path_p = torch.zeros(args.envs, device="cuda")
    path_f = torch.zeros(args.envs, 2, device="cuda")
    done_disp, done_path, done_foot = [], [], []
    steps = int(round(args.seconds / env.step_dt))
    with torch.inference_mode():
        for _ in range(steps):
            obs, _, dones, _ = venv.step(policy(obs))
            p = xy(pelvis)
            fs = [xy(f) for f in feet]
            d = dones.bool()
            # On reset the new pose is already written; don't count the jump.
            step_p = torch.where(d, 0.0, (p - prev_p).norm(dim=-1))
            path_p += step_p
            for j in range(2):
                path_f[:, j] += torch.where(d, 0.0, (fs[j] - prev_f[j]).norm(dim=-1))
            max_disp = torch.maximum(max_disp, torch.where(d, 0.0, (p - start).norm(dim=-1)))
            if d.any():
                done_disp.append(max_disp[d].clone())
                done_path.append(path_p[d].clone())
                done_foot.append(path_f[d].clone())
                start[d], max_disp[d], path_p[d], path_f[d] = p[d], 0.0, 0.0, 0.0
            prev_p, prev_f = p.clone(), [f.clone() for f in fs]
    # Episodes still running count too (partial), so the whole rollout is represented.
    done_disp.append(max_disp)
    done_path.append(path_p)
    done_foot.append(path_f)
    disp, path, foot = torch.cat(done_disp), torch.cat(done_path), torch.cat(done_foot)
    q = lambda x, p: round(float(x.quantile(p)), 3)
    secs = args.seconds
    measured = {
        "robot_episodes": int(disp.numel()),
        "pelvis_max_displacement_m": {"p50": q(disp, 0.5), "p90": q(disp, 0.9), "p99": q(disp, 0.99),
                                      "max": round(float(disp.max()), 3)},
        "pelvis_path_m": {"p50": q(path, 0.5), "p90": q(path, 0.9)},
        "foot_path_m": {"p50": q(foot.flatten(), 0.5), "p90": q(foot.flatten(), 0.9),
                        "max": round(float(foot.max()), 3)},
        "feeds": int(term.ep["episodes"]), "contact_rate": round(int(term.ep["contact"]) / max(int(term.ep["episodes"]), 1), 4),
        "note": f"episodes are up to {cfg.episode_length_s} s; rollout {secs} s",
    }
    out = {"checkpoint": args.checkpoint, "task": args.task, "seed": args.seed, "terms": terms, "measured": measured}
    print(json.dumps(out, indent=1))
    if args.json:
        json.dump(out, open(args.json, "w"), indent=1)


if __name__ == "__main__":
    main()
