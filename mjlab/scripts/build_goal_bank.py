"""Stage 5G goal bank (D-118): paddle-state goals for the timed reach controller, from real balls and the Stage 5G
planner. No robot is simulated; every goal is the planner's command for one incoming ball.

Sources, equal thirds: drill v2 families, court families (court-anchored launch geometry, as in the training feeds)
and the robot's own legal returns mirrored (recorded on development seeds; never the readiness recordings, D-118).
For each ball: the spin-blind contact (planner.predict_contact: point, ball velocity, time), a keep-it-alive outgoing
ball (planner.aim_outgoing to a target drawn in KEEP_ALIVE_BOX / KEEP_ALIVE_FLIGHT_S), the paddle state
(planner.paddle_for) and the stance spot (planner.stance_from_intercept's rule, without its baseline box). The goal is set PLAN_DELAY_S after the
launch, as the runtime planner's observation window; the pelvis is at the feed anchor (half) or anywhere in the court
start box (half). Kept: contact found, t* >= 0.35 s, root target within 2.5 m, paddle speed <= 12 m/s.

Rows (heading frame, the robot facing +x): p* - (pelvis x, y, 0) (3), paddle velocity v* (3), face normal n* (3),
t* (1), stance spot - pelvis (2).
Usage: python scripts/build_goal_bank.py --ownball FILE.pt --out BANK.pt [--n 60000] [--seed 4216004]
"""
import argparse
import json
import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from picklebot_mj import seeds  # noqa: E402
from picklebot_mj.ball import BALL_RADIUS  # noqa: E402
from picklebot_mj.drill_v2 import DRILL_V2_GROUPS  # noqa: E402
from picklebot_mj.feeds import BOUNCE_AIM_MIN, COURT_FAMILIES_CFG, FAMILIES  # noqa: E402
from picklebot_mj.planner import aim_outgoing, keep_alive_target, paddle_for, predict_contact  # noqa: E402
from picklebot_mj.tasks.shadow_swing import HINT_BEHIND, HINT_SIDE_BH, HINT_SIDE_FH  # noqa: E402
from picklebot_mj.tasks.return_stand import FEED_Y_MAX, ROBOT_START, mirror_ball_states  # noqa: E402

PLAN_DELAY_S = 0.10
COURT_START_X, COURT_START_Y = (-6.4, -2.4), (-2.6, 2.6)


def launches(fams, n, g):
    """Feed launch states as BallPhysicsAction._feed builds them, anchored at ROBOT_START (families uniform)."""
    idx = torch.randint(0, len(fams), (n,), generator=g)
    P, V, W = torch.zeros(n, 3), torch.zeros(n, 3), torch.zeros(n, 3)
    for i, f in enumerate(fams):
        m = idx == i
        k = int(m.sum())
        if not k:
            continue
        c = FAMILIES[f]
        u = lambda r: r[0] + (r[1] - r[0]) * torch.rand(k, generator=g)  # noqa: E731
        x0, z0, t = u(c.start_x), u(c.start_z), u(c.flight_time)
        y = (ROBOT_START[1] + u(c.lateral_y)).clamp(-FEED_Y_MAX, FEED_Y_MAX)
        bx = u(c.bounce_x).clamp(min=BOUNCE_AIM_MIN)
        P[m] = torch.stack([x0, y, z0], -1)
        V[m] = torch.stack([(bx - x0) / t, torch.zeros(k), (BALL_RADIUS - z0 + 0.5 * 9.81 * t * t) / t], -1)
        W[m] = torch.stack([torch.zeros(k), -u(c.spin_y), torch.zeros(k)], -1)
    return P, V, W


def stance_spot(xy, pelvis_xy):
    """planner.stance_from_intercept without its baseline box clamp (court-wide goals): beside and behind the
    contact, forehand side when the ball is on the robot's right."""
    fh = xy[:, 1] <= pelvis_xy[:, 1]
    return torch.stack([xy[:, 0] - HINT_BEHIND, torch.where(fh, xy[:, 1] + HINT_SIDE_FH, xy[:, 1] - HINT_SIDE_BH)], -1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ownball", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--n", type=int, default=60000)
    ap.add_argument("--seed", type=int, default=4216004)
    a = ap.parse_args()
    assert a.seed in seeds.DEV_EVAL_SEEDS
    g = torch.Generator().manual_seed(a.seed)
    k = a.n // 3
    v2 = sorted({f for fs in DRILL_V2_GROUPS.values() for f in fs})
    court = [f for f in COURT_FAMILIES_CFG if "volley" not in f]
    P1, V1, W1 = launches(v2, k, g)
    P2, V2, W2 = launches(court, k, g)
    own = mirror_ball_states(torch.load(a.ownball).float())
    j = torch.randint(0, own.shape[0], (k,), generator=g)
    P3, V3, W3 = own[j, :3], own[j, 3:6], own[j, 6:9]
    src = torch.cat([torch.zeros(k), torch.ones(k), 2 * torch.ones(k)]).long()
    P, V, W = torch.cat([P1, P2, P3]), torch.cat([V1, V2, V3]), torch.cat([W1, W2, W3])
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    P, V = P.to(dev), V.to(dev)
    cx, cv, ct, found = predict_contact(P, V, torch.zeros_like(P))  # spin-blind, as the runtime planner
    n = P.shape[0]
    anchor = torch.rand(n, generator=g) < 0.5
    pel = torch.stack([COURT_START_X[0] + (COURT_START_X[1] - COURT_START_X[0]) * torch.rand(n, generator=g),
                       COURT_START_Y[0] + (COURT_START_Y[1] - COURT_START_Y[0]) * torch.rand(n, generator=g)], -1)
    pel = torch.where((anchor & (src < 2)).unsqueeze(-1), torch.tensor(ROBOT_START).expand(n, 2), pel).to(dev)
    tgt, T = keep_alive_target(n, g)
    v_out = aim_outgoing(cx, tgt.to(dev), T.to(dev))
    nrm, vp = paddle_for(cv, v_out)
    stance = stance_spot(cx[:, :2], pel)
    t_star = ct - PLAN_DELAY_S
    p_rel = torch.cat([cx[:, :2] - pel, cx[:, 2:3]], -1)
    root_rel = stance - pel
    keep = found & (t_star >= 0.35) & (root_rel.norm(dim=-1) <= 2.5) & (vp.norm(dim=-1) <= 12.0)
    bank = torch.cat([p_rel, vp, nrm, t_star.unsqueeze(-1), root_rel], -1)[keep].cpu()
    torch.save(bank, a.out)
    s = src.to(dev)[keep].cpu()
    q = lambda x: [round(v, 3) for v in x.float().quantile(torch.tensor([0.1, 0.5, 0.9])).tolist()]  # noqa: E731
    info = {"out": a.out, "rows": int(bank.shape[0]), "kept_share": round(float(keep.float().mean()), 3),
            "per_source": {name: int((s == i).sum()) for i, name in enumerate(("drill_v2", "court", "own_ball"))},
            "t_star_q": q(bank[:, 9]), "paddle_speed_q": q(bank[:, 3:6].norm(dim=-1)),
            "contact_z_q": q(bank[:, 2]), "root_dist_q": q(bank[:, 10:12].norm(dim=-1)),
            "contact_dist_q": q(bank[:, 0:2].norm(dim=-1)), "seed": a.seed, "ownball": a.ownball}
    print(json.dumps(info, indent=1))
    json.dump(info, open(a.out.replace(".pt", ".json"), "w"), indent=1)


if __name__ == "__main__":
    main()
