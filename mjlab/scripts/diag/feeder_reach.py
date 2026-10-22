"""Training-free reach check (panel rounds 25-27, motion): for each feed family of the M1 protocol's feeder ball, the
share of feeds whose best contact needs at most a given walking speed. It uses the planner's walkable-contact rollout
(planner._walk_step: the earliest point at or after the first interception, inside the contact heights, whose stance
spot needs the least speed from the pelvis) and reports that least required speed per feed. No policy is run: the
feeds are launched at reset from the robot's start spot (feed anchor "start", as in the M1 read).

Usage: python scripts/diag/feeder_reach.py --seed S [--envs 8192] [--json OUT]
"""

from __future__ import annotations

import argparse
import json

import torch

import mjlab.tasks  # noqa: F401
from mjlab.envs import ManagerBasedRlEnv
from mjlab.tasks.registry import load_env_cfg

from picklebot_mj import planner, seeds
from picklebot_mj.feeds import FAMILY_NAMES, FeedMix


def required_speed(pos, vel, spin, pel, cfg=planner.PlannerCfg(), dt=planner.CONTACT_DT):
    """The least walking speed (m/s) that reaches a contact stance for each ball (planner._walk_step with cap 0, so
    nothing is 'taken' and the minimum over all candidate points is kept); 1e9 if no interception."""
    p = planner._DEFAULT_PARAMS
    m = pos.shape[0]
    x, v, w = pos.clone(), vel.clone(), spin.clone()
    t = torch.zeros(m, device=x.device)
    bounced = torch.zeros(m, dtype=torch.bool, device=x.device)
    found, chosen = torch.zeros_like(bounced), torch.zeros_like(bounced)
    cx, cv, ct = x.clone(), v.clone(), torch.full((m,), cfg.horizon_s, device=x.device)
    bx, bv, bt = x.clone(), v.clone(), torch.full((m,), cfg.horizon_s, device=x.device)
    breq = torch.full((m,), 1e9, device=x.device)
    a = (x, v, w, t, bounced, found, cx, cv, ct, pel, chosen, bx, bv, bt, breq)
    for _ in range(int(round(cfg.horizon_s / dt))):
        a = planner._walk_step(p, dt, 0.0, *a)
    return a[14]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--envs", type=int, default=8192)
    ap.add_argument("--json", default=None)
    args = ap.parse_args()
    assert args.seed in seeds.DEV_EVAL_SEEDS, "development seeds only"
    cfg = load_env_cfg("Picklebot-Latent-Court-Res-G1")  # the M1 read's task
    b = cfg.actions["ball"]
    b.move_prob, b.swing_prob, b.target_mode, b.hit_hint, b.feed_anchor = 0.0, 0.0, "A", False, "start"
    b.adaptive_curriculum, b.reach_curriculum, b.lp_curriculum, b.move_sector_weights = False, False, False, None
    b.feed_mix = FeedMix({f: 1.0 for f in FAMILY_NAMES})  # --families every
    cfg.scene.num_envs, cfg.seed, b.seed = args.envs, args.seed, args.seed
    env = ManagerBasedRlEnv(cfg=cfg, device="cuda")
    env.reset()
    t = env.action_manager.get_term("ball")
    with torch.inference_mode():
        req = required_speed(t.ball.pos, t.ball.vel, t.ball.spin, t.pelvis_xy())
    fam = t.family
    out = {"seed": args.seed, "envs": args.envs, "walk_cap": planner.WALK_CAP, "families": {}}
    for i, name in enumerate(FAMILY_NAMES):
        r = req[fam == i]
        if r.numel() == 0:
            continue
        out["families"][name] = {"feeds": int(r.numel()), "median_speed": round(float(r.median()), 3),
                                 **{f"share_le_{c}": round(float((r <= c).float().mean()), 4) for c in (1.0, 1.5, 2.0, 2.5)}}
    allr = req[(fam >= 0)]
    out["all"] = {f"share_le_{c}": round(float((allr <= c).float().mean()), 4) for c in (1.0, 1.5, 2.0, 2.5)}
    print(json.dumps(out, indent=1))
    if args.json:
        json.dump(out, open(args.json, "w"), indent=1)
    env.close()


if __name__ == "__main__":
    main()
