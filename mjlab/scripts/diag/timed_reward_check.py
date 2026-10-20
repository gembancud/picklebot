"""Stage 5G pre-launch check (D-119, panel round 10): the parent zero-shot on the E2 task, no training.

Pass rules (fixed before the check): every reward term pays; timed_contact > 0.01 on >= 20 % of scored goals with a
velocity factor that varies across envs; the first goal after a reset has the same p*-to-pelvis distance as later
goals. Also reported: the goal bank's commanded paddle speed split into its part along n* (sets the outgoing ball) and
its tangential part, and the parent's peak paddle speeds.
Usage: python scripts/diag/timed_reward_check.py --checkpoint CK [--task T] [--envs 256] [--seconds 10] [--seed 4216012]
"""
import argparse
import json
from dataclasses import asdict

import mjlab.tasks  # noqa: F401
import torch
from mjlab.envs import ManagerBasedRlEnv
from mjlab.rl import MjlabOnPolicyRunner, RslRlVecEnvWrapper
from mjlab.tasks.registry import load_env_cfg, load_rl_cfg

import picklebot_mj.tasks  # noqa: F401
from picklebot_mj import seeds

ap = argparse.ArgumentParser()
ap.add_argument("--checkpoint", required=True)
ap.add_argument("--task", default="Picklebot-Latent-TimedReach-V2-G1")
ap.add_argument("--envs", type=int, default=256)
ap.add_argument("--seconds", type=float, default=10.0)
ap.add_argument("--seed", type=int, default=4216012)
ap.add_argument("--json", default=None)
a = ap.parse_args()
assert a.seed in seeds.DEV_EVAL_SEEDS
cfg = load_env_cfg(a.task)
cfg.scene.num_envs, cfg.seed = a.envs, a.seed
env = ManagerBasedRlEnv(cfg=cfg, device="cuda")
agent = load_rl_cfg(a.task)
venv = RslRlVecEnvWrapper(env, clip_actions=agent.clip_actions)
runner = MjlabOnPolicyRunner(venv, asdict(agent), device="cuda")
runner.load(a.checkpoint, load_cfg={"actor": True}, strict=True, map_location="cuda")
policy = runner.get_inference_policy(device="cuda")
env.reset()
cmd = env.command_manager.get_term("reach")
rm = env.reward_manager
names = list(rm.active_terms)
sums = {n: 0.0 for n in names}
kp, fv, fa, rc = [], [], [], []
first_d, later_d = [], []
peak = torch.zeros(a.envs, device="cuda")
prev_tc = cmd.t_contact.clone()
obs = venv.get_observations()
with torch.no_grad():
    for _ in range(int(round(a.seconds / env.step_dt))):
        obs, _, _, _ = venv.step(policy(obs))
        for i, n in enumerate(names):
            sums[n] += float(rm._step_reward[:, i].sum())
        f = getattr(cmd, "last_factors", None)
        if f is not None and f[3].any():
            m = f[3]
            kp.append(f[0][m]); fv.append(f[1][m]); fa.append(f[2][m]); rc.append((f[0] * f[1] * f[2])[m])
        _, vel, _ = cmd.paddle_state()
        peak = torch.maximum(peak, vel.norm(dim=-1))
        new = cmd.t_contact != prev_tc
        if new.any():
            d = (cmd.p_star[:, :2] - env.scene["robot"].data.root_link_pos_w[:, :2]).norm(dim=-1)
            first = new & (env.episode_length_buf <= 2)
            first_d.append(d[first]); later_d.append(d[new & ~first])
        prev_tc = cmd.t_contact.clone()
cat = lambda xs: torch.cat(xs) if xs else torch.zeros(0, device="cuda")  # noqa: E731
kp, fv, fa, rc, first_d, later_d = map(cat, (kp, fv, fa, rc, first_d, later_d))
q = lambda x: [round(v, 3) for v in x.float().quantile(torch.tensor([0.1, 0.5, 0.9], device=x.device)).tolist()] if len(x) else None  # noqa: E731
bank = cmd.bank
vn = (bank[:, 3:6] * bank[:, 6:9]).sum(-1)
vt = (bank[:, 3:6] - vn.unsqueeze(-1) * bank[:, 6:9]).norm(dim=-1)
out = {"checkpoint": a.checkpoint, "task": a.task, "seed": a.seed,
       "reward_sums_per_env": {n: round(v / a.envs, 4) for n, v in sums.items()},
       "goals_scored": int(len(rc)), "contact_reward_q": q(rc), "share_contact_gt_0.01": round(float((rc > 0.01).float().mean()), 4) if len(rc) else None,
       "factor_pos_q": q(kp), "factor_speed_q": q(fv), "factor_speed_std": round(float(fv.std()), 4) if len(fv) > 1 else None, "factor_align_q": q(fa),
       "first_goal_dist_q": q(first_d), "later_goal_dist_q": q(later_d), "n_first": int(len(first_d)),
       "bank_speed_along_n_q": q(vn.abs()), "bank_speed_tangential_q": q(vt), "bank_speed_total_q": q(bank[:, 3:6].norm(dim=-1)),
       "parent_peak_paddle_speed_q": q(peak)}
rules = {"every term pays": all(abs(v) > 0 for v in sums.values()),
         "contact > 0.01 on >= 20 % of goals": bool(out["share_contact_gt_0.01"] is not None and out["share_contact_gt_0.01"] >= 0.20),
         "speed factor varies": bool(out["factor_speed_std"] is not None and out["factor_speed_std"] > 0.01),
         "first goal like later goals": bool(len(first_d) and abs(float(first_d.median()) - float(later_d.median())) < 0.25)}
out["pass_rules"] = rules
out["pass"] = all(rules.values())
print(json.dumps(out, indent=1))
if a.json:
    json.dump(out, open(a.json, "w"), indent=1)
env.close()
