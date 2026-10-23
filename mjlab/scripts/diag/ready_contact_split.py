"""Round 29 premise check (RL, coach, motion): in the M1 pair read (contact hand-off), is a receiver that is in the
ready stance at the ball's launch (for a partner ball: the partner's contact) more likely to reach the ball? Splits
finished feeds by ball type (partner hand-off or feeder ball) and by picklebot_mj/ready.py's ready flag at their
launch, and reports contact and legal rates. No training; development seeds only.

Usage: python scripts/diag/ready_contact_split.py --checkpoint CK --seed S [--envs 2048] [--seconds 60] --json OUT
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

TASK = "Picklebot-Latent-Court-Res-G1"  # the M1 read's task


def wilson(k, n, z=1.96):
    if n == 0:
        return [0.0, 0.0]
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(c - h, 4), round(c + h, 4)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--envs", type=int, default=2048)
    ap.add_argument("--seconds", type=float, default=60.0)
    ap.add_argument("--json", default=None)
    args = ap.parse_args()
    assert args.seed in seeds.DEV_EVAL_SEEDS, "development seeds only"
    cfg = load_env_cfg(TASK)
    b = cfg.actions["ball"]
    # as stage2_eval.py's M1 read: --move-prob 0 --swing-prob 0 --families every --target A --no-hint --rally --pairs
    # --pair-handoff contact (ready_track on, as stage2_eval always sets it)
    b.move_prob, b.swing_prob, b.target_mode, b.hit_hint = 0.0, 0.0, "A", False
    b.move_sector_weights, b.adaptive_curriculum, b.reach_curriculum, b.lp_curriculum = None, False, False, False
    b.feed_mix = FeedMix({f: 1.0 for f in FAMILY_NAMES})
    b.feed_anchor = "start"
    b.recovery_mode = "fixed"  # stage2_eval --recovery default
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
    pc, rd = t.pairs, t.ready
    assert pc is not None and rd is not None
    # counts[ball type (0 feeder, 1 partner), ready (0/1), (feeds, contact, legal)]
    counts = torch.zeros(2, 2, 3, dtype=torch.long, device=env.device)
    launch_speed = torch.zeros(env.num_envs, device=env.device)  # speed of each env's current ball at its launch
    recs = []  # (ball type, incoming speed, contact, legal) per finished feed
    step0 = pc.step

    def step(over, legal, fell, crossing, dt, delay, contact=None, busy=None):
        live = ~pc.court_dead.repeat(2)
        # as pairs.py counts them (D-135): a receiver's copy of a return the hitter faulted is not the receiver's feed
        if contact is not None:
            w = pc.waiting & ~contact
            over = over & ~(w & ~legal & (over & ~legal)[pc.partner])
        m = over & live
        typ, rdy = pc.handed.long(), rd.ready_ok.long()
        idx = (typ * 2 + rdy) * 3
        for j, v in enumerate((m, m & t.hit_done, m & legal)):
            counts.view(-1).index_add_(0, idx + j, v.long())
        recs.append(torch.stack([typ.float(), launch_speed, t.hit_done.float(), legal.float()], -1)[m])
        fire, recv = step0(over, legal, fell, crossing, dt, delay, contact=contact, busy=busy)
        # a received ball leaves the partner's paddle with the partner's post-contact speed; a feeder ball's speed is
        # read from the ball after the refeed (next step), so feeder speeds are not used below
        launch_speed.copy_(torch.where(recv, t.ball.vel[pc.partner].norm(dim=-1), launch_speed))
        return fire, recv

    pc.step = step
    obs = venv.get_observations()
    with torch.inference_mode():
        for _ in range(int(round(args.seconds / env.step_dt))):
            obs, _, _, _ = venv.step(policy(obs))
    c = counts.tolist()
    out = {"checkpoint": args.checkpoint, "seed": args.seed, "envs": args.envs, "seconds": args.seconds}
    for ti, tn in enumerate(("feeder", "partner")):
        for ri, rn in enumerate(("not_ready", "ready")):
            n, k_c, k_l = c[ti][ri]
            out[f"{tn}_{rn}"] = {"feeds": n, "contact": round(k_c / max(n, 1), 4), "contact_ci": wilson(k_c, n),
                                 "legal": round(k_l / max(n, 1), 4), "legal_ci": wilson(k_l, n)}
        a, b2 = c[ti][0], c[ti][1]
        out[f"{tn}_ready_share"] = round(b2[0] / max(a[0] + b2[0], 1), 4)
        out[f"{tn}_contact_gap_points"] = round(100 * (b2[1] / max(b2[0], 1) - a[1] / max(a[0], 1)), 2)
    r = torch.cat(recs).cpu()
    pr = r[r[:, 0] == 1]
    if len(pr) > 30:
        q = torch.quantile(pr[:, 1], torch.tensor([1 / 3, 2 / 3]))
        bins = {"slow": pr[pr[:, 1] <= q[0]], "mid": pr[(pr[:, 1] > q[0]) & (pr[:, 1] <= q[1])], "fast": pr[pr[:, 1] > q[1]]}
        out["partner_by_incoming_speed"] = {
            "cutpoints_mps": [round(float(x), 2) for x in q],
            **{k: {"feeds": len(v), "mean_speed": round(float(v[:, 1].mean()), 2), "contact": round(float(v[:, 2].mean()), 4),
                   "contact_ci": wilson(int(v[:, 2].sum()), len(v)), "legal": round(float(v[:, 3].mean()), 4)}
               for k, v in bins.items()}}
        out["partner_slow_minus_fast_contact_points"] = round(100 * float(bins["slow"][:, 2].mean() - bins["fast"][:, 2].mean()), 2)
    print(json.dumps(out, indent=1))
    if args.json:
        json.dump(out, open(args.json, "w"), indent=1)
    env.close()


if __name__ == "__main__":
    main()
