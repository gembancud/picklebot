"""Where and when does an executor fall? (Stage 5D falls diagnosis, D-091)

Plays the court drill (every family, random court-wide recovery spots, no hint) like h5c_eval's court job, and for
every fall ("fell_over" termination) records the state one control step before it:
- phase:
  - move_episode;
  - waiting (rally over, next feed pending);
  - incoming (ball in flight towards the robot, no contact yet);
  - contact_window (ball within 0.6 m of the paddle, no contact yet);
  - after_hit (first legal contact made);
- family and court zone of the current feed;
- time since the feed;
- pelvis speed, torso tilt and angular speed;
- the residual's size |lam_r tanh(a)|, when the action term is a residual.
Reports shares by phase, family and zone, and fall vs. non-fall medians of the motion features.

Usage: python scripts/diag/falls_diag.py --checkpoint CK --task TASK [--envs 2048] [--seconds 40] [--seed S] [--json OUT]
"""
from __future__ import annotations

import argparse
import copy
import json
from collections import Counter
from dataclasses import asdict

import mjlab.tasks  # noqa: F401
import torch
from mjlab.envs import ManagerBasedRlEnv
from mjlab.rl import MjlabOnPolicyRunner, RslRlVecEnvWrapper
from mjlab.tasks.registry import load_env_cfg, load_rl_cfg

from picklebot_mj import seeds
from picklebot_mj.feeds import COURT_ZONES, FAMILY_NAMES, FeedMix


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--task", required=True)
    ap.add_argument("--envs", type=int, default=2048)
    ap.add_argument("--seconds", type=float, default=40.0)
    ap.add_argument("--seed", type=int, default=4200920)
    ap.add_argument("--move-prob", type=float, default=0.0)
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    assert a.seed in seeds.DEV_EVAL_SEEDS
    cfg = load_env_cfg(a.task)
    b = cfg.actions["ball"]
    b.move_prob, b.swing_prob, b.hit_hint, b.lp_curriculum = a.move_prob, 0.0, False, False
    b.adaptive_curriculum, b.reach_curriculum, b.move_sector_weights = False, False, None
    b.feed_mix = FeedMix({f: 1.0 for f in FAMILY_NAMES})
    b.recovery_mode = "random"
    b.seed = a.seed
    cfg.scene.num_envs, cfg.seed = a.envs, a.seed
    cfg.observations["actor"].enable_corruption = False
    env = ManagerBasedRlEnv(cfg=cfg, device="cuda")
    venv = RslRlVecEnvWrapper(env, clip_actions=load_rl_cfg(a.task).clip_actions)
    runner = MjlabOnPolicyRunner(venv, copy.deepcopy(asdict(load_rl_cfg(a.task))), device="cuda")
    runner.load(a.checkpoint, load_cfg={"actor": True}, strict=True, map_location="cuda")
    policy = runner.get_inference_policy(device="cuda")
    term = env.action_manager.get_term("ball")
    lat = env.action_manager.get_term("latent")
    robot = env.scene["robot"]
    torso = list(robot.body_names).index("torso_link")
    env.reset()
    obs = venv.get_observations()
    n = env.num_envs
    feed_t = torch.zeros(n, device="cuda")
    prev_tallied = term.tallied.clone()
    rows, base = [], {"speed": [], "tilt": [], "angvel": [], "res": []}
    steps = int(a.seconds / env.step_dt)
    with torch.inference_mode():
        for t in range(steps):
            d = robot.data
            paddle = d.body_link_pos_w[:, term.paddle_id, :3] - env.scene.env_origins
            ball_d = (term.ball.pos - paddle).norm(dim=-1)
            speed = d.root_link_lin_vel_w[:, :2].norm(dim=-1)
            tilt = torch.acos((-d.projected_gravity_b[:, 2]).clamp(-1, 1))
            angvel = d.body_link_ang_vel_w[:, torso].norm(dim=-1)
            move = term.drill.move_ep if getattr(term, "drill", None) is not None else torch.zeros(n, dtype=torch.bool, device="cuda")
            if hasattr(lat.cfg, "lam_r"):
                res = (lat.cfg.lam_r * torch.tanh(lat.raw_action[:, :lat.cfg.latent])).abs().mean(-1)
            else:
                res = torch.zeros(n, device="cuda")
            phase = torch.full((n,), 2, dtype=torch.long, device="cuda")  # incoming
            phase = torch.where(ball_d < 0.6, torch.full_like(phase, 3), phase)  # contact window
            phase = torch.where(term.hit_done, torch.full_like(phase, 4), phase)  # after hit
            phase = torch.where(term.tallied | term.rules.dead, torch.full_like(phase, 1), phase)  # waiting
            phase = torch.where(move, torch.zeros_like(phase), phase)  # move episode
            snap = (phase.clone(), term.family.clone(), term.zone.clone() if hasattr(term, "zone") else torch.zeros_like(phase),
                    feed_t.clone(), speed, tilt, angvel, res)
            if t % 10 == 0:  # non-fall reference sample
                for k, v in zip(("speed", "tilt", "angvel", "res"), snap[4:]):
                    base[k].append(v.cpu())
            obs, _, dones, _ = venv.step(policy(obs))
            fell = env.termination_manager.get_term("fell_over").clone()
            idx = torch.where(fell)[0]
            for i in idx.tolist():
                rows.append({"phase": int(snap[0][i]), "family": FAMILY_NAMES[int(snap[1][i])],
                             "zone": COURT_ZONES[int(snap[2][i])] if hasattr(term, "zone") else "-",
                             "t_feed": round(float(snap[3][i]), 2), "speed": float(snap[4][i]), "tilt": float(snap[5][i]),
                             "angvel": float(snap[6][i]), "res": float(snap[7][i])})
            newfeed = prev_tallied & ~term.tallied
            feed_t = torch.where(newfeed | dones.bool(), torch.zeros_like(feed_t), feed_t + env.step_dt)
            prev_tallied = term.tallied.clone()
    names = ["move_episode", "waiting", "incoming", "contact_window", "after_hit"]
    nf = len(rows)
    med = lambda xs: round(float(torch.tensor(xs).median()), 3) if xs else None
    out = {"checkpoint": a.checkpoint, "task": a.task, "seed": a.seed, "envs": n, "seconds": a.seconds, "falls": nf,
           "robot_episodes": int(term.ep["env_episodes"]), "falls_per_episode_tally": int(term.ep["env_falls"]),
           "by_phase": {names[k]: round(c / max(nf, 1), 3) for k, c in Counter(r["phase"] for r in rows).most_common()},
           "by_family": dict(Counter(r["family"] for r in rows).most_common()),
           "by_zone": dict(Counter(r["zone"] for r in rows).most_common()),
           "fall_median": {k: med([r[k] for r in rows]) for k in ("t_feed", "speed", "tilt", "angvel", "res")},
           "nonfall_median": {k: round(float(torch.cat(v).median()), 3) for k, v in base.items()}}
    print(json.dumps(out, indent=1))
    if a.json:
        json.dump({**out, "rows": rows}, open(a.json, "w"), indent=1)
    env.close()


if __name__ == "__main__":
    main()
