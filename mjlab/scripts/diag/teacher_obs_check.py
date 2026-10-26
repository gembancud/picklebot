"""D-156 smoke: is the e4 teacher's privileged input live? In the M1 pair read's environment (PICKLEBOT_TEACHER=1),
run a checkpoint for a few seconds and report the share of steps with the input on, the time-to-contact range, and
how well the time to contact counts down (it should fall by one control step per step while on). No selection.

Usage: PICKLEBOT_TEACHER=1 PICKLEBOT_LAM_R=2 python scripts/diag/teacher_obs_check.py --checkpoint CK --seed S
"""

from __future__ import annotations

import argparse
from dataclasses import asdict

import torch

import mjlab.tasks  # noqa: F401
from mjlab.envs import ManagerBasedRlEnv
from mjlab.rl import MjlabOnPolicyRunner, RslRlVecEnvWrapper
from mjlab.tasks.registry import load_env_cfg, load_rl_cfg

from picklebot_mj import seeds

TASK = "Picklebot-Latent-Court-Res-G1"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--envs", type=int, default=256)
    ap.add_argument("--steps", type=int, default=500)
    args = ap.parse_args()
    assert args.seed in seeds.DEV_EVAL_SEEDS, "development seeds only"
    cfg = load_env_cfg(TASK)
    assert "teacher_contact" in cfg.observations["actor"].terms, "set PICKLEBOT_TEACHER=1"
    b = cfg.actions["ball"]
    b.move_prob, b.swing_prob, b.target_mode, b.hit_hint = 0.0, 0.0, "A", False
    b.pair_mode, b.pair_handoff = True, "contact"
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
    obs = venv.get_observations()
    on_steps, prev, drops, starts = 0, None, [], 0
    for _ in range(args.steps):
        with torch.no_grad():
            obs, _, _, _ = venv.step(policy(obs))
        x = env.obs_buf["actor"][:, -5:]
        on = x[:, 4] > 0.5
        on_steps += int(on.sum())
        if prev is not None:
            both = on & prev[0]
            drops.append((prev[1] - x[:, 3])[both & (x[:, 3] > 0.05)])
            starts += int((on & ~prev[0]).sum())
        prev = (on, x[:, 3].clone())
    d = torch.cat(drops) if drops else torch.zeros(0)
    print(f"teacher input on in {on_steps / (args.steps * args.envs):.3f} of env-steps; {starts} feeds switched it on; "
          f"time-to-contact drop per step median {float(d.median()) if len(d) else float('nan'):.4f} s "
          f"(control step {env.step_dt:.4f} s); last obs range {x[on].amin(0).tolist() if on.any() else None} "
          f"to {x[on].amax(0).tolist() if on.any() else None}")


if __name__ == "__main__":
    main()
