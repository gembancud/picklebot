"""How closely can the latent controller reproduce a flat policy's joint actions? (Stage 5B H4 diagnostic, D-057)

The flat policy (default S-D3-style-c) plays its own Drill 3 task (real balls, every family, no hint). Every --every
steps the visited states are recorded: the flat actor's action a_T, and the controller's 160-dim observation built as
the H4 action term builds it, with the flat policy's last executed action as the controller's "last action". For each
state, a in R^35 is then fitted by gradient descent to minimise |q(a) - a_T|^2, where q is the H4 action term's
mapping (z = mu_p + lam sigma_p tanh(a_lat), q = D(s, z) plus the wrist residual). The remaining error is the best any
H4 policy could do at that state: the expressiveness floor of the latent action space for that lambda.

Reports the mean squared error per joint group (legs, waist, left arm, right arm without wrist, right wrist) and
overall, against the variance of a_T (the error of predicting nothing), for each --lams value.

Usage (picklebot-mj venv):
    python scripts/latent_reach_floor.py [--envs 256] [--seconds 8] [--lams 1,2,3] [--seed 4200424] [--json OUT]
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
from picklebot_mj.feeds import FAMILY_NAMES, FeedMix
from picklebot_mj.latent import GOAL_DIM, LatentController
from picklebot_mj.tasks.latent_reach import RIGHT_WRIST, controller_proprio

FLAT_TASK = "Picklebot-Student-Drill3-Style-NoWrist-G1"
TEACHER = ("artifacts/train/logs/picklebot_return_stand/2026-10-08_22-42-14_student-drill3-style-c/"
           "model_10400.pt")
LATENT = "artifacts/train/latent/latent-07/latent_10651.pt"
GROUPS = {"legs": r"(hip|knee|ankle)", "waist": r"waist", "left_arm": r"left_(shoulder|elbow|wrist)",
          "right_arm": r"right_(shoulder|elbow)", "right_wrist": r"right_wrist"}


def main():
    import re

    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", default=TEACHER)
    ap.add_argument("--envs", type=int, default=256)
    ap.add_argument("--seconds", type=float, default=8.0)
    ap.add_argument("--every", type=int, default=5)
    ap.add_argument("--lams", default="1,2,3")
    ap.add_argument("--fit-steps", type=int, default=400)
    ap.add_argument("--seed", type=int, default=4200424)
    ap.add_argument("--json", default=None)
    args = ap.parse_args()
    assert args.seed in seeds.DEV_EVAL_SEEDS, "evaluation must use development seeds"

    cfg = load_env_cfg(FLAT_TASK)
    cfg.rewards.pop("style", None)
    ball = cfg.actions["ball"]
    ball.move_prob, ball.swing_prob, ball.hit_hint = 0.0, 0.0, False
    ball.adaptive_curriculum, ball.reach_curriculum = False, False
    ball.feed_mix = FeedMix({f: 1.0 for f in FAMILY_NAMES})
    cfg.scene.num_envs, cfg.seed, ball.seed = args.envs, args.seed, args.seed
    cfg.observations["actor"].enable_corruption = False
    env = ManagerBasedRlEnv(cfg=cfg, device="cuda")
    venv = RslRlVecEnvWrapper(env, clip_actions=load_rl_cfg(FLAT_TASK).clip_actions)
    runner = MjlabOnPolicyRunner(venv, copy.deepcopy(asdict(load_rl_cfg(FLAT_TASK))), device="cuda")
    runner.load(args.checkpoint, load_cfg={"actor": True}, strict=True, map_location="cuda")
    policy = runner.get_inference_policy(device="cuda")
    term = env.action_manager.get_term("joint_pos")
    robot = env.scene["robot"]
    lin, ang = env.scene["robot/imu_lin_vel"], env.scene["robot/imu_ang_vel"]
    names = list(term._target_names)
    wrist = torch.tensor([names.index(j) for j in RIGHT_WRIST], device="cuda")
    scale = term._scale[0] if torch.is_tensor(term._scale) else torch.full((len(names),), float(term._scale),
                                                                           device="cuda")

    env.reset()
    obs = venv.get_observations()
    C, Y = [], []
    with torch.no_grad():
        for t in range(int(round(args.seconds / env.step_dt))):
            a_t = policy(obs)
            if t % args.every == 0:
                prop = controller_proprio(robot, lin, ang, term._target_ids, env.action_manager.action)
                C.append(torch.cat([torch.zeros(args.envs, GOAL_DIM, device="cuda"), prop], -1))
                Y.append(a_t.clone())
            obs, *_ = venv.step(a_t)
    c, y = torch.cat(C), torch.cat(Y)
    env.close()

    model = LatentController().cuda()
    model.load_state_dict(torch.load(LATENT, map_location="cuda", weights_only=False)["model"])
    model.eval()
    for p in model.parameters():
        p.requires_grad_(False)
    with torch.no_grad():
        mu, logstd = model.prior_dist(c)
    out = {"checkpoint": args.checkpoint, "seed": args.seed, "states": len(y),
           "action_var": {g: float(y[:, [i for i, n in enumerate(names) if re.search(rx, n)]].var(0).mean())
                          for g, rx in GROUPS.items()},
           "action_var_all": float(y.var(0).mean()), "fits": {}}
    for lam in [float(v) for v in args.lams.split(",")]:
        a = torch.zeros(len(y), 35, device="cuda", requires_grad=True)
        opt = torch.optim.Adam([a], lr=0.05)
        for _ in range(args.fit_steps):
            z = mu + lam * logstd.exp() * torch.tanh(a[:, :32])
            q = model.decode(c, z)
            q = q + torch.zeros_like(q).index_add(1, wrist, 0.3 * torch.tanh(a[:, 32:]) / scale[wrist])
            err = (q - y) ** 2
            opt.zero_grad()
            err.mean().backward()
            opt.step()
        with torch.no_grad():
            err = err.detach()
            fit = {g: float(err[:, [i for i, n in enumerate(names) if re.search(rx, n)]].mean())
                   for g, rx in GROUPS.items()}
            fit["all"] = float(err.mean())
            fit["saturated_frac"] = float((a[:, :32].abs() > 2.0).float().mean())
        out["fits"][f"lambda_{lam:g}"] = fit
        print(f"lambda {lam:g}: " + json.dumps({k: round(v, 4) for k, v in fit.items()}), flush=True)
    print("action variance:", json.dumps({k: round(v, 4) for k, v in out["action_var"].items()}),
          "all", round(out["action_var_all"], 4))
    if args.json:
        json.dump(out, open(args.json, "w"), indent=1)


if __name__ == "__main__":
    main()
