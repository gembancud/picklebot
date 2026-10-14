"""Record a trained policy's own motion as G1 motion CSVs (Stage 5C, footwork data from the walking teacher).

Rolls out a joint-space policy (default: the walking teacher, `Picklebot-Teacher-Move-G1`, move-to-spot episodes in
uniform directions) and writes each fall-free episode segment as one retargeted-style CSV: root position (3, relative
to the env origin), root quaternion xyzw (4), the 29 G1 joint angles in mjlab order (scripts/motion/mirror_g1_csv.py).
csv_to_npz_local.py then turns them into a tracking npz like any retargeted clip.

Recording produces training data, so it uses a training seed (picklebot_mj.seeds.TRAIN_SEEDS), never a dev or final
seed.

Usage (picklebot-mj venv):
    python scripts/motion/record_policy_clips.py --checkpoint CK --out DIR [--task Picklebot-Teacher-Move-G1]
        [--envs 64] [--seconds 40] [--min-seconds 6] [--seed 11] [--prefix footwork]
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import asdict
from pathlib import Path

import mjlab.tasks  # noqa: F401
import numpy as np
import torch
from mjlab.envs import ManagerBasedRlEnv
from mjlab.rl import MjlabOnPolicyRunner, RslRlVecEnvWrapper
from mjlab.tasks.registry import load_env_cfg, load_rl_cfg

from picklebot_mj import seeds

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mirror_g1_csv import G1_JOINTS  # noqa: E402

FALL_Z = 0.5  # torso height (m), as tracking_eval.py


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--task", default="Picklebot-Teacher-Move-G1")
    ap.add_argument("--envs", type=int, default=64)
    ap.add_argument("--seconds", type=float, default=40.0)
    ap.add_argument("--min-seconds", type=float, default=6.0, help="drop segments shorter than this")
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--prefix", default="footwork")
    args = ap.parse_args()
    assert args.seed in seeds.TRAIN_SEEDS, "recording makes training data: use a training seed"

    cfg = load_env_cfg(args.task)
    cfg.scene.num_envs, cfg.seed = args.envs, args.seed
    b = cfg.actions["ball"]
    b.seed = args.seed
    b.move_sector_weights = None  # uniform spot directions
    b.adaptive_curriculum = False
    cfg.observations["actor"].enable_corruption = False
    cfg.episode_length_s = max(cfg.episode_length_s, args.seconds + 1.0)  # one long episode per env if no fall
    env = ManagerBasedRlEnv(cfg=cfg, device="cuda")
    agent_cfg = load_rl_cfg(args.task)
    venv = RslRlVecEnvWrapper(env, clip_actions=agent_cfg.clip_actions)
    rl = asdict(agent_cfg)
    sd = torch.load(args.checkpoint, map_location="cpu", weights_only=False)
    for part in ("actor", "critic"):  # network sizes from the checkpoint (as stage2_eval.py)
        ws = sorted((int(k.split(".")[1]), v.shape[0]) for k, v in sd[f"{part}_state_dict"].items()
                    if k.startswith("mlp.") and k.endswith(".weight"))
        rl[part]["hidden_dims"] = tuple(n for _, n in ws[:-1])
    runner = MjlabOnPolicyRunner(venv, rl, device="cuda")
    runner.load(args.checkpoint, load_cfg={"actor": True}, strict=True, map_location="cuda")
    policy = runner.get_inference_policy(device="cuda")

    robot = env.scene["robot"]
    order = [list(robot.joint_names).index(j) for j in G1_JOINTS]
    torso = list(robot.body_names).index("torso_link")
    origins = env.scene.env_origins
    env.reset()
    obs = venv.get_observations()
    n, steps = env.num_envs, int(args.seconds / env.step_dt)
    rows = [[] for _ in range(n)]
    fell = torch.zeros(n, dtype=torch.bool, device="cuda")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    kept, frames, min_rows = 0, 0, int(args.min_seconds / env.step_dt)

    def flush(i):
        nonlocal kept, frames
        if len(rows[i]) >= min_rows:
            np.savetxt(out / f"{args.prefix}_s{args.seed}_e{i:03d}_{kept:04d}.csv", np.asarray(rows[i]), delimiter=",")
            kept += 1
            frames += len(rows[i])
        rows[i] = []

    for _ in range(steps):
        d = robot.data
        pos = (d.root_link_pos_w - origins).cpu().numpy()
        q = d.root_link_quat_w.cpu().numpy()  # wxyz
        jp = d.joint_pos[:, order].cpu().numpy()
        for i in range(n):
            rows[i].append(np.concatenate([pos[i], q[i, [1, 2, 3, 0]], jp[i]]))
        with torch.no_grad():
            obs, _, dones, _ = venv.step(policy(obs))
        # A termination (not a time-out) is a fall or another failure; reset happens inside the step, so the
        # torso height after it is already the new episode's.
        fell |= env.termination_manager.terminated | (d.body_link_pos_w[:, torso, 2] < FALL_Z)
        for i in torch.where(dones.bool())[0].tolist():
            if bool(fell[i]):
                rows[i] = []  # a fall: drop the whole segment
            else:
                flush(i)
            fell[i] = False
    for i in range(n):
        if not bool(fell[i]):
            flush(i)
    print(f"{kept} clips, {frames} frames ({frames * env.step_dt:.0f} s) -> {out}")
    env.close()


if __name__ == "__main__":
    main()
