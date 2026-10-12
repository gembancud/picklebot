"""Move-drill diagnostic for an H4 checkpoint (Stage 5B, D-061 follow-up): does the executor get to its spots, and is
the arrival test (within 0.25 m, pelvis speed < 0.2 m/s, held 0.3 s) reachable for it?

Runs move-to-spot episodes only (deterministic policy) and reports, per issued spot:
- the closest approach to the spot, and the fraction of spots approached within 0.25 / 0.5 m;
- the pelvis speed (body frame, xy) while within 0.25 m of the spot (median, p10);
- the drill's own arrival summary.

Usage (picklebot-mj venv):
    python scripts/move_diag.py --checkpoint CK --task TASK [--envs 512] [--seconds 16] [--seed 4200464] [--json OUT]
"""

from __future__ import annotations

import argparse
import copy
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
    ap.add_argument("--envs", type=int, default=512)
    ap.add_argument("--seconds", type=float, default=16.0)
    ap.add_argument("--seed", type=int, default=4200464)
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    assert a.seed in seeds.DEV_EVAL_SEEDS, "evaluation must use development seeds"

    cfg = load_env_cfg(a.task)
    b = cfg.actions["ball"]
    b.move_prob, b.swing_prob, b.move_sector_weights, b.adaptive_curriculum = 1.0, 0.0, None, False
    cfg.scene.num_envs, cfg.seed, b.seed = a.envs, a.seed, a.seed
    cfg.observations["actor"].enable_corruption = False
    env = ManagerBasedRlEnv(cfg=cfg, device="cuda")
    venv = RslRlVecEnvWrapper(env, clip_actions=load_rl_cfg(a.task).clip_actions)
    runner = MjlabOnPolicyRunner(venv, copy.deepcopy(asdict(load_rl_cfg(a.task))), device="cuda")
    runner.load(a.checkpoint, load_cfg={"actor": True}, strict=True, map_location="cuda")
    policy = runner.get_inference_policy(device="cuda")
    t = env.action_manager.get_term("ball")
    dr = t.drill
    env.reset()
    obs = venv.get_observations()
    spot = t.recover_xy.clone()
    dmin = torch.full((a.envs,), 1e9, device="cuda")
    closest, near_speed = [], []
    with torch.no_grad():
        for _ in range(int(round(a.seconds / env.step_dt))):
            obs, *_ = venv.step(policy(obs))
            here = t.pelvis_xy()
            changed = (t.recover_xy - spot).norm(dim=-1) > 1e-4  # a new spot was issued: close the old one
            closest.append(dmin[changed].clone())
            dmin[changed] = 1e9
            spot = t.recover_xy.clone()
            d = (spot - here).norm(dim=-1)
            dmin = torch.minimum(dmin, d)
            v = t._entity.data.root_link_lin_vel_b[:, :2].norm(dim=-1)
            near_speed.append(v[d < 0.25].clone())
    c = torch.cat(closest)
    c = c[c < 1e8]
    s = torch.cat(near_speed)
    out = {"checkpoint": a.checkpoint, "seed": a.seed, "spots_closed": int(len(c)),
           "closest_median_m": float(c.median()) if len(c) else None,
           "within_25cm": float((c < 0.25).float().mean()) if len(c) else None,
           "within_50cm": float((c < 0.5).float().mean()) if len(c) else None,
           "speed_near_spot_median": float(s.median()) if len(s) else None,
           "speed_near_spot_p10": float(s.quantile(0.1)) if len(s) else None,
           "frac_near_slower_than_0.2": float((s < 0.2).float().mean()) if len(s) else None,
           "drill": dr.summary()["all"]}
    print(json.dumps(out, indent=1))
    if a.json:
        json.dump(out, open(a.json, "w"), indent=1)
    env.close()


if __name__ == "__main__":
    main()
