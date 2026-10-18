"""Style score of an executor checkpoint (Stage 5B gate): how close its poses stay to the human clips.

Plays the Stage 5 gate setting (real balls, every family, no stance hint, no move or ghost episodes, curricula off;
same as artifacts/eval/s5_gate_eval.sh) and records each robot's pose every step. For each pose, the distance to the
nearest pose in the retargeted clips (Tennis-MoCap v5 + LAFAN1), in the clips' standardised feature space, is the
"nearest-clip pose distance". It does not use the training discriminator, so it can compare any two checkpoints.

Pose features: joint positions (29), projected gravity (3), hands and feet relative to the pelvis in the pelvis
frame (12) -- the pose part of picklebot_mj.style.features (velocities excluded).

Usage (picklebot-mj venv):
    python scripts/motion/style_score.py --checkpoint PATH [--task Picklebot-Student-Drill3-G1] [--envs 512]
        [--seconds 16] [--seed 4200400] [--json OUT]
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

import mjlab.tasks  # noqa: F401
import numpy as np
import torch
from mjlab.envs import ManagerBasedRlEnv
from mjlab.rl import MjlabOnPolicyRunner, RslRlVecEnvWrapper
from mjlab.tasks.registry import load_env_cfg, load_rl_cfg

from picklebot_mj import seeds
from picklebot_mj.feeds import FAMILY_NAMES, FeedMix
from picklebot_mj.style import KEY_BODIES, expert_transitions, robot_features

MOTION = Path(__file__).resolve().parents[2] / "artifacts" / "motion" / "tracking"
POSE = np.r_[0:29, 65:68, 68:80]  # joint_pos, projected gravity, key bodies (see picklebot_mj.style.features)
EXPERT_SAMPLE = 60_000


# Stage 5E new reference (D-101, results/stage5e-style-reference.md): fixed source shares of the EXPERT_SAMPLE poses,
# standardised by the composed sample itself. The 100STYLE part is the held-out reference slice only.
NEW_REF_100STYLE = MOTION / "style100-ref.npz"
NEW_REF_SHARES = (("tennis-v5.npz", 0.50), ("lafan-g1.npz", 0.25), ("style100-ref.npz", 0.25))


def new_reference_score(raw: torch.Tensor, body_names: list[str]) -> dict:
    """Nearest-clip pose distance of raw robot pose features against the new composed reference."""
    pose = torch.tensor(POSE, device=raw.device)
    g = torch.Generator(device=raw.device).manual_seed(1)
    parts, held = [], []
    for name, share in NEW_REF_SHARES:
        ea, _ = expert_transitions([MOTION / name], body_names, raw.device)
        k = int(round(share * EXPERT_SAMPLE))
        perm = torch.randperm(len(ea), generator=g, device=raw.device)
        # A source with fewer poses than its share (the 100STYLE slice: 5,083) fills the share by repeating them: a
        # nearest-pose distance is unchanged by repeats, and they weight the standardisation as the share says.
        take = perm.repeat(-(-k // len(ea)))[:k]
        parts.append(ea[take][:, pose])
        held.append(ea[perm[k:k + int(round(share * 20_000))]][:, pose])  # empty for a source used up by its share
    sample = torch.cat(parts)
    mean, std = sample.mean(0), sample.std(0).clamp(min=1e-3)
    ref = (sample - mean) / std
    dist = nearest_distance((raw - mean) / std, ref)
    floor = nearest_distance((torch.cat(held) - mean) / std, ref)
    return {"shares": {n: s for n, s in NEW_REF_SHARES}, "nearest_clip_distance_median": float(dist.median()),
            "nearest_clip_distance_mean": float(dist.mean()), "nearest_clip_distance_p90": float(dist.quantile(0.9)),
            "human_floor_median": float(floor.median())}


def nearest_distance(x, ref, chunk=2048):
    out = []
    for i in range(0, len(x), chunk):
        out.append(torch.cdist(x[i:i + chunk], ref).min(dim=1).values)
    return torch.cat(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--task", default="Picklebot-Student-Drill3-G1")
    ap.add_argument("--envs", type=int, default=512)
    ap.add_argument("--seconds", type=float, default=16.0)
    ap.add_argument("--seed", type=int, default=4200400)
    ap.add_argument("--every", type=int, default=5, help="record every Nth step")
    ap.add_argument("--json", default=None)
    args = ap.parse_args()
    assert args.seed in seeds.DEV_EVAL_SEEDS, "evaluation must use development seeds"

    cfg = load_env_cfg(args.task)
    ball = cfg.actions["ball"]
    ball.move_prob, ball.swing_prob, ball.hit_hint = 0.0, 0.0, False
    ball.move_sector_weights, ball.adaptive_curriculum, ball.reach_curriculum = None, False, False
    ball.lp_curriculum = False
    if ball.recovery:
        ball.recovery_mode = "fixed"
    ball.feed_mix = FeedMix({f: 1.0 for f in FAMILY_NAMES})
    cfg.rewards.pop("style", None)  # the score must not depend on (or train) a discriminator
    cfg.scene.num_envs, cfg.seed, ball.seed = args.envs, args.seed, args.seed
    cfg.observations["actor"].enable_corruption = False
    env = ManagerBasedRlEnv(cfg=cfg, device="cuda")
    agent = load_rl_cfg(args.task)
    venv = RslRlVecEnvWrapper(env, clip_actions=agent.clip_actions)
    rl = asdict(agent)
    sd = torch.load(args.checkpoint, map_location="cpu", weights_only=False)
    for part in ("actor", "critic"):
        ws = sorted((int(k.split(".")[1]), v.shape[0]) for k, v in sd[f"{part}_state_dict"].items()
                    if k.startswith("mlp.") and k.endswith(".weight"))
        rl[part]["hidden_dims"] = tuple(n for _, n in ws[:-1])
    runner = MjlabOnPolicyRunner(venv, rl, device="cuda")
    runner.load(args.checkpoint, load_cfg={"actor": True}, strict=True, map_location="cuda")
    policy = runner.get_inference_policy(device="cuda")

    robot = env.scene["robot"]
    keys = [list(robot.body_names).index(b) for b in KEY_BODIES]
    ea, _ = expert_transitions([MOTION / "tennis-v5.npz", MOTION / "lafan-g1.npz"], list(robot.body_names), "cuda")
    pose = torch.tensor(POSE, device="cuda")
    mean, std = ea[:, pose].mean(0), ea[:, pose].std(0).clamp(min=1e-3)
    g = torch.Generator(device="cuda").manual_seed(0)
    ref = ((ea[:, pose] - mean) / std)[torch.randperm(len(ea), generator=g, device="cuda")[:EXPERT_SAMPLE]]
    env.reset()  # apply the reset events before the first step (see scripts/stage2_eval.py)
    obs = venv.get_observations()
    poses, raw = [], []
    with torch.inference_mode():
        for t in range(int(round(args.seconds / env.step_dt))):
            obs, *_ = venv.step(policy(obs))
            if t % args.every == 0:
                f = robot_features(robot, keys)[:, pose].clone()
                raw.append(f)
                poses.append((f - mean) / std)
    x = torch.cat(poses)
    dist = nearest_distance(x, ref)
    # Reference: the same distance for held-out clip frames (how close human poses are to other human poses).
    held = ((ea[:, pose] - mean) / std)[torch.randperm(len(ea), generator=g, device="cuda")[EXPERT_SAMPLE:
                                                                                              EXPERT_SAMPLE + 20_000]]
    floor = nearest_distance(held, ref)
    out = {"checkpoint": args.checkpoint, "seed": args.seed, "poses": len(x),
           "nearest_clip_distance_median": float(dist.median()), "nearest_clip_distance_mean": float(dist.mean()),
           "nearest_clip_distance_p90": float(dist.quantile(0.9)),
           "human_floor_median": float(floor.median())}
    if NEW_REF_100STYLE.exists():  # Stage 5E: the new reference, scored on the same robot poses (D-101)
        out["new_reference"] = new_reference_score(torch.cat(raw), list(robot.body_names))
    print(json.dumps(out, indent=1))
    if args.json:
        json.dump(out, open(args.json, "w"), indent=1)
    env.close()


if __name__ == "__main__":
    main()
