"""Is the style-score drift from the wrist residual? (H4 diagnostic, D-071)

For each checkpoint: real-ball drill play (every family, no hint), records the mean |wrist residual| (rad) and the
style score (nearest-clip pose distance, style_score.py's features) computed twice: with all pose features, and
with the three right-wrist joint features masked out of both robot and clip poses.

Usage: python scripts/wrist_style_diag.py --runs RUN:CK:TASK ... [--envs 512] [--seconds 8] [--seed 4200540]
"""
import argparse
import copy
import json
from dataclasses import asdict
from pathlib import Path

import torch

import mjlab.tasks  # noqa: F401
from mjlab.envs import ManagerBasedRlEnv
from mjlab.rl import MjlabOnPolicyRunner, RslRlVecEnvWrapper
from mjlab.tasks.registry import load_env_cfg, load_rl_cfg

from picklebot_mj import seeds
from picklebot_mj.feeds import FAMILY_NAMES, FeedMix
from picklebot_mj.style import KEY_BODIES, expert_transitions, robot_features
from picklebot_mj.tasks.latent_reach import RIGHT_WRIST

MOTION = Path(__file__).resolve().parents[1] / "artifacts" / "motion" / "tracking"
POSE = list(range(0, 29)) + list(range(65, 80))
LOGS = "artifacts/train/logs/picklebot_return_stand"

ap = argparse.ArgumentParser()
ap.add_argument("--runs", nargs="+", required=True)
ap.add_argument("--envs", type=int, default=512)
ap.add_argument("--seconds", type=float, default=8.0)
ap.add_argument("--seed", type=int, default=4200540)
a = ap.parse_args()
assert a.seed in seeds.DEV_EVAL_SEEDS
for spec in a.runs:
    run, ck, task = spec.split(":")
    path = str(sorted(Path(LOGS).glob(f"*{run}"))[-1] / ck)
    cfg = load_env_cfg(task)
    b = cfg.actions["ball"]
    b.move_prob, b.swing_prob, b.hit_hint, b.adaptive_curriculum, b.reach_curriculum = 0.0, 0.0, False, False, False
    b.lp_curriculum = False
    b.feed_mix = FeedMix({f: 1.0 for f in FAMILY_NAMES})
    cfg.scene.num_envs, cfg.seed, b.seed = a.envs, a.seed, a.seed
    cfg.observations["actor"].enable_corruption = False
    env = ManagerBasedRlEnv(cfg=cfg, device="cuda")
    venv = RslRlVecEnvWrapper(env, clip_actions=load_rl_cfg(task).clip_actions)
    runner = MjlabOnPolicyRunner(venv, copy.deepcopy(asdict(load_rl_cfg(task))), device="cuda")
    runner.load(path, load_cfg={"actor": True}, strict=True, map_location="cuda")
    policy = runner.get_inference_policy(device="cuda")
    robot = env.scene["robot"]
    keys = [list(robot.body_names).index(k) for k in KEY_BODIES]
    term = env.action_manager.get_term("latent")
    names = list(robot.joint_names)
    wrist_cols = [names.index(j) for j in RIGHT_WRIST]  # joint-position features are the first 29 pose columns
    env.reset()
    obs = venv.get_observations()
    poses, wr = [], []
    with torch.no_grad():
        for t in range(int(round(a.seconds / env.step_dt))):
            act = policy(obs)
            wr.append((term.cfg.wrist_residual * torch.tanh(act[:, term.cfg.latent:])).abs().mean().item())
            obs, *_ = venv.step(act)
            if t % 5 == 0:
                poses.append(robot_features(robot, keys)[:, POSE].clone())
    ea, _ = expert_transitions([MOTION / "tennis-v5.npz", MOTION / "lafan-g1.npz"], list(robot.body_names), "cuda")
    ref = ea[:, POSE]
    mean, std = ref.mean(0), ref.std(0).clamp(min=1e-3)
    g = torch.Generator(device="cuda").manual_seed(0)
    ref = ((ref - mean) / std)[torch.randperm(len(ref), generator=g, device="cuda")[:60000]]
    x = (torch.cat(poses) - mean) / std
    keep = torch.ones(x.shape[1], dtype=torch.bool, device="cuda")
    keep[wrist_cols] = False
    def score(xx, rr):
        return float(torch.cat([torch.cdist(xx[i:i + 2048], rr).min(1).values for i in range(0, len(xx), 2048)]).median())
    out = {"run": run, "wrist_residual_mean_rad": sum(wr) / len(wr), "style_all": score(x, ref),
           "style_without_right_wrist": score(x[:, keep], ref[:, keep])}
    print(json.dumps({k: (round(v, 4) if isinstance(v, float) else v) for k, v in out.items()}), flush=True)
    env.close()
