"""D-140 diagnostic: in pair-mode training conditions, how many balls (feeder balls and partner hand-offs) go to a robot
that is in a move-drill episode (walk to a spot, no ball)? Runs a training task's environment (not the play config)
with a checkpoint's policy and counts, per physics step, the pair logic's feeder fires and hand-offs, split by the
receiving env's move_ep flag. Also the partner-ball legal rate split by the receiver's flag.

Usage: python scripts/diag/pair_move_bug.py --checkpoint CK --task T [--envs 1024] [--seconds 40] --seed S --json OUT
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--task", required=True)
    ap.add_argument("--envs", type=int, default=1024)
    ap.add_argument("--seconds", type=float, default=40.0)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--respect-moves", action="store_true", help="turn the D-140 fix on")
    ap.add_argument("--json", default=None)
    args = ap.parse_args()
    assert args.seed in seeds.DEV_EVAL_SEEDS, "development seeds only"
    cfg = load_env_cfg(args.task)
    cfg.scene.num_envs, cfg.seed = args.envs, args.seed
    cfg.actions["ball"].seed = args.seed
    if args.respect_moves:
        cfg.actions["ball"].pair_respect_moves = True
    env = ManagerBasedRlEnv(cfg=cfg, device="cuda")
    agent_cfg = load_rl_cfg(args.task)
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
    term = env.action_manager.get_term("ball")
    pc, dr = term.pairs, term.drill
    assert pc is not None and dr is not None, "a pair-mode task with move drills"
    c = {k: torch.zeros((), dtype=torch.long, device=env.device) for k in
         ("fire_free", "fire_move", "recv_free", "recv_move", "own_free", "own_free_legal", "own_move", "own_move_legal")}
    step0 = pc.step

    sh = term.shadow

    def step(over, legal, fell, crossing, dt, delay, contact=None, busy=None):
        mv = dr.move_ep.clone() if sh is None else dr.move_ep | sh.swing_ep  # round 26: swing episodes are ball-free too
        own = over & pc.handed  # a partner ball finished in this env
        c["own_free"] += (own & ~mv).sum(); c["own_free_legal"] += (own & legal & ~mv).sum()
        c["own_move"] += (own & mv).sum(); c["own_move_legal"] += (own & legal & mv).sum()
        fire, recv = step0(over, legal, fell, crossing, dt, delay, contact=contact, busy=busy)
        c["fire_free"] += (fire & ~mv).sum(); c["fire_move"] += (fire & mv).sum()
        c["recv_free"] += (recv & ~mv).sum(); c["recv_move"] += (recv & mv).sum()
        return fire, recv

    pc.step = step
    obs = venv.get_observations()
    with torch.inference_mode():
        for _ in range(int(round(args.seconds / env.step_dt))):
            obs, _, _, _ = venv.step(policy(obs))
    r = {k: int(v) for k, v in c.items()}
    from picklebot_mj.feeds import FAMILY_NAMES  # D-141: realised feeder-ball family shares (ep_family: feeder balls only)
    fe = term.ep_family[:, 0].float()
    r["feeder_family_share"] = {n: round(float(fe[i] / fe.sum().clamp(min=1)), 4) for i, n in enumerate(FAMILY_NAMES)}
    r["move_share_of_envs"] = round(float(dr.move_ep.float().mean()), 4)
    r["swing_share_of_envs"] = round(float(sh.swing_ep.float().mean()), 4) if sh is not None else 0.0
    r["share_of_balls_to_move_episodes"] = round((r["fire_move"] + r["recv_move"]) / max(sum(r[k] for k in ("fire_free", "fire_move", "recv_free", "recv_move")), 1), 4)
    r["partner_legal_free"] = round(r["own_free_legal"] / max(r["own_free"], 1), 4)
    r["partner_legal_move"] = round(r["own_move_legal"] / max(r["own_move"], 1), 4)
    r.update(checkpoint=args.checkpoint, task=args.task, seed=args.seed, respect_moves=args.respect_moves)
    print(json.dumps(r))
    if args.json:
        json.dump(r, open(args.json, "w"), indent=1)
    env.close()


if __name__ == "__main__":
    main()
