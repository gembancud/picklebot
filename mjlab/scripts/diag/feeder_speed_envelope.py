"""Round 34 e1 (D-151, architecture's form): is the frozen latent controller the limit on feeder balls? In the M1 pair
read (contact hand-off), for every finished feed log the peak pelvis ground speed from the feed's start to its end,
the closest paddle-to-ball distance, and the direction the robot had to move (pelvis at the start to the ball at the
closest approach, in the start heading frame). Splits feeder balls by family and by hit or miss. No training;
development seeds only.

Pre-registered rule (D-151): if the reach_deep and fast feeder-ball misses reach a 90th-percentile peak pelvis speed
of at least 1.4 m/s and still end short (median closest distance > 0.20 m), the controller is the limit and the next
run gives the residual joint-space control of the 12 leg joints. Otherwise the limit is the policy (or backhand
skill), and the panel chooses again.

Usage: python scripts/diag/feeder_speed_envelope.py --checkpoint CK --seed S [--envs 2048] [--seconds 120] --json OUT
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict

import torch

import mjlab.tasks  # noqa: F401
from mjlab.envs import ManagerBasedRlEnv
from mjlab.rl import MjlabOnPolicyRunner, RslRlVecEnvWrapper
from mjlab.tasks.registry import load_env_cfg, load_rl_cfg

from picklebot_mj import seeds
from picklebot_mj.feeds import FAMILY_NAMES, FeedMix
from picklebot_mj.tasks.latent_reach import _to_heading, _yaw_frame

TASK = "Picklebot-Latent-Court-Res-G1"  # the M1 read's task
DIRS = ("forward", "left", "back", "right")
RULE_FAMILIES = ("reach_deep", "fast")


def q(x: torch.Tensor, p: float):
    return round(float(torch.quantile(x, p)), 3) if len(x) else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--envs", type=int, default=2048)
    ap.add_argument("--seconds", type=float, default=120.0)
    ap.add_argument("--json", default=None)
    ap.add_argument("--planner", choices=["task", "off", "clean", "noisy"], default="task")  # round 38 headroom read
    args = ap.parse_args()
    assert args.seed in seeds.DEV_EVAL_SEEDS, "development seeds only"
    cfg = load_env_cfg(TASK)
    b = cfg.actions["ball"]
    # as stage2_eval.py's M1 read: --move-prob 0 --swing-prob 0 --families every --target A --no-hint --rally --pairs
    # --pair-handoff contact (ready_track on, recovery fixed), as in scripts/diag/ready_contact_split.py
    b.move_prob, b.swing_prob, b.target_mode, b.hit_hint = 0.0, 0.0, "A", False
    b.move_sector_weights, b.adaptive_curriculum, b.reach_curriculum, b.lp_curriculum = None, False, False, False
    b.feed_mix = FeedMix({f: 1.0 for f in FAMILY_NAMES})
    b.feed_anchor = "start"
    b.recovery_mode = "fixed"
    if args.planner != "task":
        b.planner_mode = args.planner
    cfg.episode_length_s = max(cfg.episode_length_s, args.seconds + 1.0)
    b.pair_mode, b.pair_handoff, b.ready_track = True, "contact", True
    cfg.observations["actor"].enable_corruption = False
    cfg.scene.num_envs, cfg.seed, b.seed = args.envs, args.seed, args.seed
    env = ManagerBasedRlEnv(cfg=cfg, device="cuda")
    agent_cfg = load_rl_cfg(TASK)
    venv = RslRlVecEnvWrapper(env, clip_actions=agent_cfg.clip_actions)
    rl = asdict(agent_cfg)
    sd = torch.load(args.checkpoint, map_location="cpu", weights_only=False)
    for part in ("actor", "critic"):
        ws = sorted((int(k.split(".")[1]), v.shape[0]) for k, v in sd[f"{part}_state_dict"].items()
                    if k.startswith("mlp.") and k.endswith(".weight"))
        rl[part]["hidden_dims"] = tuple(n for _, n in ws[:-1])
    runner = MjlabOnPolicyRunner(venv, rl, device="cuda")
    runner.load(args.checkpoint, load_cfg={"actor": True}, strict=True, map_location="cuda")
    policy = runner.get_inference_policy(device="cuda")
    env.reset()
    t = env.action_manager.get_term("ball")
    pc = t.pairs
    assert pc is not None
    robot = env.scene["robot"]
    origins = env.scene.env_origins
    n = env.num_envs
    dev = env.device
    peak = torch.zeros(n, device=dev)  # peak pelvis ground speed since the feed started
    dmin = torch.full((n,), 1e3, device=dev)  # closest paddle-to-ball distance since the feed started
    ball_at = torch.zeros(n, 2, device=dev)  # ball xy (env-local) at the closest approach
    p0 = torch.zeros(n, 2, device=dev)  # pelvis xy (env-local) at the feed's start
    c0, s0 = torch.ones(n, device=dev), torch.zeros(n, device=dev)  # heading at the feed's start
    recs = []  # (handed, family, contact, legal, peak speed, closest distance, direction index)
    step0 = pc.step

    def start(mask):
        root = robot.data.root_link_pose_w
        c, s = _yaw_frame(root[:, 3:7])
        p0.copy_(torch.where(mask.unsqueeze(-1), root[:, :2] - origins[:, :2], p0))
        c0.copy_(torch.where(mask, c, c0))
        s0.copy_(torch.where(mask, s, s0))
        peak.masked_fill_(mask, 0.0)
        dmin.masked_fill_(mask, 1e3)

    start(torch.ones(n, dtype=torch.bool, device=dev))

    def step(over, legal, fell, crossing, dt, delay, contact=None, busy=None):
        root = robot.data.root_link_pose_w
        speed = robot.data.root_link_lin_vel_w[:, :2].norm(dim=-1)
        torch.maximum(peak, speed, out=peak)
        paddle = robot.data.body_link_pose_w[:, t.paddle_id, :3] - origins
        d = (t.ball.pos - paddle).norm(dim=-1)
        closer = d < dmin
        dmin.copy_(torch.where(closer, d, dmin))
        ball_at.copy_(torch.where(closer.unsqueeze(-1), t.ball.pos[:, :2], ball_at))
        live = ~pc.court_dead.repeat(2)
        if contact is not None:  # as pairs.py counts them (D-135)
            w = pc.waiting & ~contact
            over = over & ~(w & ~legal & (over & ~legal)[pc.partner])
        m = over & live
        rel = _to_heading(torch.cat([ball_at - p0, torch.zeros(n, 1, device=dev)], -1), c0, s0)[:, :2]
        ang = torch.atan2(rel[:, 1], rel[:, 0])  # 0 forward, +pi/2 left
        k = (((ang + math.pi / 4) % (2 * math.pi)) // (math.pi / 2)).long().clamp(0, 3)
        recs.append(torch.stack([pc.handed.float(), t.family.float(), t.hit_done.float(), legal.float(), peak, dmin,
                                 k.float()], -1)[m])
        fire, recv = step0(over, legal, fell, crossing, dt, delay, contact=contact, busy=busy)
        start(fire | recv)
        return fire, recv

    pc.step = step
    obs = venv.get_observations()
    with torch.inference_mode():
        for _ in range(int(round(args.seconds / env.step_dt))):
            obs, _, _, _ = venv.step(policy(obs))
    r = torch.cat(recs).cpu()
    fed = r[r[:, 0] == 0]
    out = {"checkpoint": args.checkpoint, "seed": args.seed, "envs": args.envs, "seconds": args.seconds,
           "feeder_feeds": len(fed), "families": {}, "directions": {}}
    for i, name in enumerate(FAMILY_NAMES):
        f = fed[fed[:, 1] == i]
        miss = f[f[:, 3] == 0]
        hit = f[f[:, 3] == 1]
        out["families"][name] = {
            "feeds": len(f), "legal": round(float(f[:, 3].mean()), 4) if len(f) else None,
            "contact": round(float(f[:, 2].mean()), 4) if len(f) else None, "misses": len(miss),
            "miss_peak_speed_p50": q(miss[:, 4], 0.5), "miss_peak_speed_p90": q(miss[:, 4], 0.9),
            "hit_peak_speed_p50": q(hit[:, 4], 0.5), "hit_peak_speed_p90": q(hit[:, 4], 0.9),
            "miss_closest_m_p50": q(miss[:, 5], 0.5), "miss_closest_m_p90": q(miss[:, 5], 0.9),
            "miss_direction_share": {dn: round(float((miss[:, 6] == j).float().mean()), 3) if len(miss) else None
                                     for j, dn in enumerate(DIRS)}}
    for j, dn in enumerate(DIRS):
        f = fed[fed[:, 6] == j]
        miss = f[f[:, 3] == 0]
        out["directions"][dn] = {"feeds": len(f), "legal": round(float(f[:, 3].mean()), 4) if len(f) else None,
                                 "contact": round(float(f[:, 2].mean()), 4) if len(f) else None,
                                 "peak_speed_p90": q(f[:, 4], 0.9), "miss_peak_speed_p90": q(miss[:, 4], 0.9),
                                 "miss_closest_m_p50": q(miss[:, 5], 0.5)}
    idx = [FAMILY_NAMES.index(f) for f in RULE_FAMILIES]
    sel = fed[(fed[:, 1] == idx[0]) | (fed[:, 1] == idx[1])]
    miss = sel[sel[:, 3] == 0]
    p90, d50 = q(miss[:, 4], 0.9), q(miss[:, 5], 0.5)
    out["rule"] = {"families": RULE_FAMILIES, "misses": len(miss), "miss_peak_speed_p90": p90, "miss_closest_m_p50": d50,
                   "controller_limit": bool(p90 is not None and p90 >= 1.4 and d50 is not None and d50 > 0.20)}
    out["all_feeder_peak_speed_p99"] = q(fed[:, 4], 0.99)
    print(json.dumps(out, indent=1))
    if args.json:
        json.dump(out, open(args.json, "w"), indent=1)
    env.close()


if __name__ == "__main__":
    main()
